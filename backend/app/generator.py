"""Background generation job (replaces the n8n loops).

The job is resumable: it skips days and quizzes that already have content, so a
failed or interrupted roadmap can be retried without paying for finished work.
"""
import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import emailer, llm, pdf, render
from .config import settings
from .database import SessionLocal
from .models import Day, Quiz, Roadmap, User

log = logging.getLogger(__name__)


def run_generation(roadmap_id: int) -> None:
    db = SessionLocal()
    try:
        roadmap = db.get(Roadmap, roadmap_id)
        if roadmap is None:
            return
        try:
            _generate(db, roadmap)
        except Exception as e:  # noqa: BLE001 - surface any failure to the user
            log.exception("Roadmap %s failed", roadmap_id)
            db.rollback()
            roadmap = db.get(Roadmap, roadmap_id)
            roadmap.status = "failed"
            roadmap.error = str(e)[:1000]
            db.commit()
    finally:
        db.close()


def _generate(db, roadmap: Roadmap) -> None:
    roadmap.error = None

    # 1. Plan (skipped when resuming)
    if not roadmap.days:
        roadmap.status = "planning"
        db.commit()
        plan = llm.plan_roadmap(roadmap.topic, roadmap.duration, roadmap.level, roadmap.hours_per_day)
        for item in plan:
            db.add(
                Day(
                    roadmap_id=roadmap.id,
                    day_number=item["day"],
                    title=item["title"],
                    topic_focus=item["topic_focus"],
                )
            )
        db.commit()
        db.refresh(roadmap)

    days = list(roadmap.days)
    per_module = settings.days_per_module
    module_count = math.ceil(len(days) / per_module)
    existing_quizzes = {q.module_number: q for q in roadmap.quizzes}

    roadmap.total_steps = len(days) + module_count
    roadmap.done_steps = sum(1 for d in days if d.content) + sum(1 for q in existing_quizzes.values() if q.questions)
    roadmap.status = "generating"
    db.commit()

    # 2. Day content, a few at a time
    errors: list[str] = []
    pending = [d for d in days if not d.content]
    with ThreadPoolExecutor(max_workers=settings.llm_workers) as pool:
        futures = {
            pool.submit(
                llm.generate_day,
                roadmap.topic,
                roadmap.level,
                roadmap.hours_per_day,
                roadmap.duration,
                d.day_number,
                d.title,
                d.topic_focus,
            ): d
            for d in pending
        }
        for future in as_completed(futures):
            day = futures[future]
            try:
                day.content = future.result()
                roadmap.done_steps += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"Day {day.day_number}: {e}")
            db.commit()
    if errors:
        raise RuntimeError(f"{len(errors)} day(s) failed to generate. First error: {errors[0]}")

    # 3. Module quizzes
    jobs = []
    for m in range(module_count):
        number = m + 1
        chunk = days[m * per_module : (m + 1) * per_module]
        quiz = existing_quizzes.get(number)
        if quiz and quiz.questions:
            continue
        if quiz is None:
            quiz = Quiz(
                roadmap_id=roadmap.id,
                module_number=number,
                day_range=f"{chunk[0].day_number}-{chunk[-1].day_number}",
            )
            db.add(quiz)
            db.commit()
        text = "\n\n".join(render.day_to_markdown(d.day_number, d.title, d.content) for d in chunk)
        jobs.append((quiz, text))

    with ThreadPoolExecutor(max_workers=settings.llm_workers) as pool:
        futures = {pool.submit(llm.generate_quiz, text): quiz for quiz, text in jobs}
        for future in as_completed(futures):
            quiz = futures[future]
            try:
                quiz.questions = future.result()
                roadmap.done_steps += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"Module {quiz.module_number} quiz: {e}")
            db.commit()
    if errors:
        raise RuntimeError(f"{len(errors)} quiz(zes) failed to generate. First error: {errors[0]}")

    roadmap.status = "done"
    roadmap.done_steps = roadmap.total_steps
    db.commit()

    # 4. Optional email (never fails the roadmap)
    if roadmap.email_when_done:
        try:
            send_pdf_email(db, roadmap)
        except Exception:  # noqa: BLE001
            log.exception("Could not email roadmap %s", roadmap.id)


def build_pdf(roadmap: Roadmap) -> bytes:
    md = render.roadmap_to_markdown(roadmap, list(roadmap.days), list(roadmap.quizzes))
    return pdf.markdown_to_pdf(md)


def send_pdf_email(db, roadmap: Roadmap) -> None:
    user = db.get(User, roadmap.user_id)
    emailer.send_roadmap_email(user.email, roadmap.topic, roadmap.duration, roadmap.id, build_pdf(roadmap))
