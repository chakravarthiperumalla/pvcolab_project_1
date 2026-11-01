"""LLM calls: the planner, day-content and module-quiz prompts ported from the n8n workflow.

Each function returns validated, normalized Python data. Every call retries on
malformed JSON, which was the main failure mode of the original n8n version.
"""
import json
import logging
import re

from anthropic import Anthropic

from .config import settings

log = logging.getLogger(__name__)
_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured on the server")
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def extract_json(text: str):
    """Parse JSON from model output, tolerating code fences and stray prose."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        starts = [i for i in (text.find("["), text.find("{")) if i != -1]
        if not starts:
            raise
        start = min(starts)
        end = max(text.rfind("]"), text.rfind("}"))
        return json.loads(text[start : end + 1])


def complete_json(model: str, system: str, user: str, max_tokens: int, temperature: float, attempts: int = 3):
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            # Streaming avoids SDK timeouts on long generations.
            with _get_client().messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            ) as stream:
                text = stream.get_final_text()
            return extract_json(text)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            log.warning("Model returned invalid JSON (attempt %s/%s): %s", attempt, attempts, e)
    raise RuntimeError(f"Model did not return valid JSON after {attempts} attempts: {last_error}")


# ---------------------------------------------------------------- planner

PLANNER_SYSTEM = """You are an expert curriculum designer who builds practical, progressive learning roadmaps.

Given a topic, a number of days, a learner level and the hours available per day, design a day-by-day plan.

Rules:
- Return EXACTLY the requested number of days, numbered 1..N with no gaps.
- Progress logically: fundamentals first, then applied work, then a capstone/review at the end.
- Scale scope per day to the hours available and the learner level.
- Include periodic review/revision days for longer plans.
- "title" is a short human-readable day title (max 12 words).
- "topic_focus" is 1-2 sentences describing precisely what that day covers.

Respond with ONLY a JSON array, no commentary and no code fences:
[{"day": 1, "title": "...", "topic_focus": "..."}, ...]"""


def plan_roadmap(topic: str, duration: int, level: str, hours_per_day: float) -> list[dict]:
    user = (
        f"Topic: {topic}\nDuration: {duration} days\nLevel: {level}\n"
        f"Hours per day: {hours_per_day:g}\n\nReturn exactly {duration} days."
    )
    # ~60 tokens per day plus headroom
    max_tokens = min(32000, 2000 + duration * 120)
    for _ in range(2):
        raw = complete_json(settings.planner_model, PLANNER_SYSTEM, user, max_tokens, 0.35)
        if isinstance(raw, dict):  # some models wrap the array
            raw = next((v for v in raw.values() if isinstance(v, list)), [])
        plan = _normalize_plan(raw)
        if len(plan) >= duration:
            return plan[:duration]
        log.warning("Planner returned %s of %s days, retrying", len(plan), duration)
    raise RuntimeError(f"Planner returned only {len(plan)} of {duration} days")


def _normalize_plan(raw) -> list[dict]:
    plan = []
    for i, item in enumerate(raw if isinstance(raw, list) else [], start=1):
        if not isinstance(item, dict):
            continue
        plan.append(
            {
                "day": i,  # renumber to guarantee a gapless sequence
                "title": str(item.get("title") or f"Day {i}")[:300],
                "topic_focus": str(item.get("topic_focus") or item.get("focus") or ""),
            }
        )
    return plan


# ---------------------------------------------------------------- day content

DAY_SYSTEM = """You are an expert teacher writing one day of a structured course.

Write rich, accurate, practical content for the given day. Strings may contain Markdown
(including fenced code blocks). Keep JSON valid: escape newlines and quotes inside strings.

Respond with ONLY a JSON object, no commentary and no code fences, with exactly this shape:
{
  "goal": "one sentence learning goal",
  "theory": "clear explanation in Markdown",
  "examples": "worked examples in Markdown, with code where relevant",
  "real_world_use_case": "a concrete real-world scenario",
  "common_mistakes": "Markdown bullet list of frequent mistakes and how to avoid them",
  "summary": "short recap",
  "practice": {
    "mcqs": ["question text with options A-D inline", "..."],
    "coding_questions": ["..."],
    "debugging_questions": ["..."],
    "interview_questions": ["..."]
  },
  "assignment": {
    "mini_assignment": "...",
    "homework": "...",
    "challenge": "...",
    "hints": "...",
    "expected_output": "..."
  }
}
Provide 3-5 items in each practice list. Match depth to the learner level and the hours available."""


def generate_day(
    topic: str, level: str, hours_per_day: float, duration: int, day: int, title: str, topic_focus: str
) -> dict:
    user = (
        f"Course topic: {topic}\nDay: {day} of {duration}\nDay title: {title}\n"
        f"Day focus: {topic_focus}\nLevel: {level}\nHours available today: {hours_per_day:g}"
    )
    raw = complete_json(settings.day_model, DAY_SYSTEM, user, 8000, 0.4)
    return normalize_day(raw)


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(f"- {_text(v)}" for v in value)
    if isinstance(value, dict):
        return "\n".join(f"**{k}:** {_text(v)}" for k, v in value.items())
    return str(value)


def _str_list(value) -> list[str]:
    if isinstance(value, list):
        return [_text(v) for v in value]
    return [_text(value)] if value else []


def normalize_day(raw) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Day content is not a JSON object")
    practice = raw.get("practice") if isinstance(raw.get("practice"), dict) else {}
    assignment = raw.get("assignment") if isinstance(raw.get("assignment"), dict) else {}
    return {
        "goal": _text(raw.get("goal")),
        "theory": _text(raw.get("theory")),
        "examples": _text(raw.get("examples")),
        "real_world_use_case": _text(raw.get("real_world_use_case")),
        "common_mistakes": _text(raw.get("common_mistakes")),
        "summary": _text(raw.get("summary")),
        "practice": {
            "mcqs": _str_list(practice.get("mcqs")),
            "coding_questions": _str_list(practice.get("coding_questions")),
            "debugging_questions": _str_list(practice.get("debugging_questions")),
            "interview_questions": _str_list(practice.get("interview_questions")),
        },
        "assignment": {
            "mini_assignment": _text(assignment.get("mini_assignment")),
            "homework": _text(assignment.get("homework")),
            "challenge": _text(assignment.get("challenge")),
            "hints": _text(assignment.get("hints")),
            "expected_output": _text(assignment.get("expected_output")),
        },
    }


# ---------------------------------------------------------------- module quiz

QUIZ_SYSTEM = """You write assessment quizzes for a learning module.

Create 8 multiple-choice questions that test understanding (not trivia) of the module content.
Each question has exactly 4 options. "answer" must be EXACTLY equal to one of the option strings.
Vary difficulty and cover every day in the module.

Respond with ONLY a JSON object, no commentary and no code fences:
{"quiz": [{"question": "...", "options": ["...", "...", "...", "..."], "answer": "...", "explanation": "..."}]}"""


def generate_quiz(module_markdown: str) -> list[dict]:
    raw = complete_json(settings.quiz_model, QUIZ_SYSTEM, f"Module content:\n{module_markdown}", 6000, 0.4)
    questions = normalize_quiz(raw)
    if not questions:
        raise RuntimeError("Quiz generator returned no valid questions")
    return questions


def normalize_quiz(raw) -> list[dict]:
    items = raw.get("quiz") if isinstance(raw, dict) else raw
    out = []
    for q in items if isinstance(items, list) else []:
        if not isinstance(q, dict):
            continue
        options = [_text(o) for o in (q.get("options") or [])]
        if len(options) < 2:
            continue
        answer = _text(q.get("answer")).strip()
        idx = _answer_index(answer, options)
        if idx is None:
            continue
        out.append(
            {
                "question": _text(q.get("question")),
                "options": options,
                "answer_index": idx,
                "explanation": _text(q.get("explanation")),
            }
        )
    return out


def _answer_index(answer: str, options: list[str]) -> int | None:
    if answer in options:
        return options.index(answer)
    lowered = [o.strip().lower() for o in options]
    if answer.lower() in lowered:
        return lowered.index(answer.lower())
    # "B" or "B) text" style answers
    m = re.match(r"^\(?([A-Da-d])[\).:]?(\s|$)", answer)
    if m:
        i = ord(m.group(1).upper()) - ord("A")
        if i < len(options):
            return i
    for i, o in enumerate(lowered):
        if answer and (o.startswith(answer.lower()) or answer.lower().startswith(o)):
            return i
    return None
