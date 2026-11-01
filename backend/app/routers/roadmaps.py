import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import emailer, generator
from ..config import settings
from ..database import get_db
from ..models import ACTIVE_STATUSES, Roadmap, User
from ..schemas import DayProgress, QuizScore, RoadmapCreate, RoadmapDetail, RoadmapSummary
from ..security import get_current_user

router = APIRouter(prefix="/api/roadmaps", tags=["roadmaps"])


def _owned(db: Session, user: User, roadmap_id: int) -> Roadmap:
    roadmap = db.get(Roadmap, roadmap_id)
    if roadmap is None or roadmap.user_id != user.id:
        raise HTTPException(404, "Roadmap not found")
    return roadmap


def _check_capacity(db: Session, user: User) -> None:
    active = db.scalar(
        select(func.count(Roadmap.id)).where(Roadmap.user_id == user.id, Roadmap.status.in_(ACTIVE_STATUSES))
    )
    if active >= settings.max_active_roadmaps_per_user:
        raise HTTPException(
            429,
            f"You can generate up to {settings.max_active_roadmaps_per_user} roadmaps at a time. "
            "Please wait for one to finish.",
        )


@router.post("", response_model=RoadmapSummary, status_code=201)
def create_roadmap(
    body: RoadmapCreate,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.duration > settings.max_days:
        raise HTTPException(422, f"Duration cannot exceed {settings.max_days} days")
    if body.email_when_done and not emailer.email_enabled():
        raise HTTPException(400, "Email delivery is not configured on this server")
    _check_capacity(db, user)
    roadmap = Roadmap(
        user_id=user.id,
        topic=body.topic.strip(),
        duration=body.duration,
        level=body.level,
        hours_per_day=body.hours_per_day,
        email_when_done=body.email_when_done,
    )
    db.add(roadmap)
    db.commit()
    background.add_task(generator.run_generation, roadmap.id)
    return roadmap


@router.get("", response_model=list[RoadmapSummary])
def list_roadmaps(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Roadmap).where(Roadmap.user_id == user.id).order_by(Roadmap.created_at.desc())).all()


@router.get("/{roadmap_id}", response_model=RoadmapDetail)
def get_roadmap(roadmap_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _owned(db, user, roadmap_id)


@router.delete("/{roadmap_id}", status_code=204)
def delete_roadmap(roadmap_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    roadmap = _owned(db, user, roadmap_id)
    if roadmap.status in ACTIVE_STATUSES:
        raise HTTPException(409, "Wait for generation to finish (or fail) before deleting")
    db.delete(roadmap)
    db.commit()
    return Response(status_code=204)


@router.post("/{roadmap_id}/retry", response_model=RoadmapSummary)
def retry_roadmap(
    roadmap_id: int,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roadmap = _owned(db, user, roadmap_id)
    if roadmap.status != "failed":
        raise HTTPException(409, "Only failed roadmaps can be retried")
    _check_capacity(db, user)
    roadmap.status = "queued"
    roadmap.error = None
    db.commit()
    background.add_task(generator.run_generation, roadmap.id)
    return roadmap


@router.patch("/{roadmap_id}/days/{day_number}")
def set_day_progress(
    roadmap_id: int,
    day_number: int,
    body: DayProgress,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roadmap = _owned(db, user, roadmap_id)
    day = next((d for d in roadmap.days if d.day_number == day_number), None)
    if day is None:
        raise HTTPException(404, "Day not found")
    day.completed = body.completed
    db.commit()
    return {"day_number": day.day_number, "completed": day.completed}


@router.post("/{roadmap_id}/quizzes/{module_number}/score")
def save_quiz_score(
    roadmap_id: int,
    module_number: int,
    body: QuizScore,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roadmap = _owned(db, user, roadmap_id)
    quiz = next((q for q in roadmap.quizzes if q.module_number == module_number), None)
    if quiz is None or not quiz.questions:
        raise HTTPException(404, "Quiz not found")
    if body.score > body.total or body.total != len(quiz.questions):
        raise HTTPException(422, "Invalid score")
    quiz.last_score, quiz.last_total = body.score, body.total
    db.commit()
    return {"module_number": module_number, "score": quiz.last_score, "total": quiz.last_total}


@router.get("/{roadmap_id}/pdf")
def download_pdf(roadmap_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    roadmap = _owned(db, user, roadmap_id)
    if roadmap.status != "done":
        raise HTTPException(409, "The handbook is not finished yet")
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", roadmap.topic).strip("_") or "roadmap"
    return Response(
        content=generator.build_pdf(roadmap),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )


@router.post("/{roadmap_id}/email", status_code=202)
def email_roadmap(
    roadmap_id: int,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roadmap = _owned(db, user, roadmap_id)
    if roadmap.status != "done":
        raise HTTPException(409, "The handbook is not finished yet")
    if not emailer.email_enabled():
        raise HTTPException(400, "Email delivery is not configured on this server")

    def job():
        from ..database import SessionLocal

        session = SessionLocal()
        try:
            generator.send_pdf_email(session, session.get(Roadmap, roadmap_id))
        finally:
            session.close()

    background.add_task(job)
    return {"detail": f"Sending to {user.email}"}
