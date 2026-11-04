import os
import tempfile

# Must be set before the app is imported.
_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_db.name}"
os.environ["DAYS_PER_MODULE"] = "2"

import pytest
from fastapi.testclient import TestClient

from app import llm
from app.main import app

FAKE_DAY = {
    "goal": "g",
    "theory": "t",
    "examples": "e",
    "real_world_use_case": "r",
    "common_mistakes": "m",
    "summary": "s",
    "practice": {"mcqs": ["q"], "coding_questions": ["c"], "debugging_questions": ["d"], "interview_questions": ["i"]},
    "assignment": {"mini_assignment": "a", "homework": "h", "challenge": "c", "hints": "hi", "expected_output": "o"},
}
FAKE_QUIZ = [{"question": "Q?", "options": ["a", "b", "c", "d"], "answer_index": 1, "explanation": "because"}]


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(
        llm,
        "plan_roadmap",
        lambda topic, duration, level, hours: [
            {"day": i, "title": f"Title {i}", "topic_focus": "focus"} for i in range(1, duration + 1)
        ],
    )
    monkeypatch.setattr(llm, "generate_day", lambda *a, **k: llm.normalize_day(FAKE_DAY))
    monkeypatch.setattr(llm, "generate_quiz", lambda text: FAKE_QUIZ)
    with TestClient(app) as c:
        # Each test starts from an empty board; there are no accounts to isolate by.
        for r in c.get("/api/roadmaps").json():
            c.delete(f"/api/roadmaps/{r['id']}")
        yield c


def _create(client, **over):
    body = {"topic": "Python", "duration": 5, "level": "Beginner", "hours_per_day": 2} | over
    return client.post("/api/roadmaps", json=body)


def test_no_auth_required(client):
    """Every endpoint is open: there is no login in this build."""
    assert client.get("/api/roadmaps").status_code == 200
    assert client.get("/api/health").json() == {"status": "ok"}
    # The auth routes are gone entirely, not merely unguarded.
    assert client.post("/api/auth/login", json={"email": "a@b.com", "password": "x" * 8}).status_code == 404
    assert client.get("/api/auth/me").status_code == 404


def test_generate_progress_quiz_pdf(client):
    r = _create(client)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    # TestClient runs background tasks before returning, so the roadmap is already finished.
    detail = client.get(f"/api/roadmaps/{rid}").json()
    assert detail["status"] == "done", detail
    assert len(detail["days"]) == 5
    assert len(detail["quizzes"]) == 3  # 5 days at 2 per module
    assert detail["done_steps"] == detail["total_steps"] == 8

    assert client.patch(f"/api/roadmaps/{rid}/days/1", json={"completed": True}).status_code == 200
    assert client.post(f"/api/roadmaps/{rid}/quizzes/1/score", json={"score": 1, "total": 1}).status_code == 200
    assert client.post(f"/api/roadmaps/{rid}/quizzes/1/score", json={"score": 5, "total": 1}).status_code == 422
    detail = client.get(f"/api/roadmaps/{rid}").json()
    assert detail["days"][0]["completed"] is True
    assert detail["quizzes"][0]["last_score"] == 1

    pdf = client.get(f"/api/roadmaps/{rid}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_everyone_sees_every_roadmap(client):
    """Without accounts the board is shared - this is the documented trade-off."""
    rid = _create(client, topic="Rust", duration=2).json()["id"]
    assert rid in [r["id"] for r in client.get("/api/roadmaps").json()]
    assert client.get(f"/api/roadmaps/{rid}").status_code == 200
    assert client.get("/api/roadmaps/999999").status_code == 404
    assert client.delete(f"/api/roadmaps/{rid}").status_code == 204


def test_validation_and_email_guard(client):
    assert _create(client, duration=999).status_code == 422
    assert _create(client, topic="x").status_code == 422
    assert _create(client, level="beginner").status_code == 422
    # SMTP is not configured in tests, so asking for delivery is rejected up front.
    assert _create(client, email_to="me@example.com").status_code == 400


def test_capacity_guard(client, monkeypatch):
    """The concurrency cap is global now that it cannot be per-user."""
    from app.routers import roadmaps as router

    monkeypatch.setattr(router.settings, "max_active_roadmaps", 0)
    assert _create(client).status_code == 429


def test_failure_then_resume(client, monkeypatch):
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom")
        return llm.normalize_day(FAKE_DAY)

    monkeypatch.setattr(llm, "generate_day", flaky)
    rid = _create(client, topic="Go", duration=3).json()["id"]
    detail = client.get(f"/api/roadmaps/{rid}").json()
    assert detail["status"] == "failed" and "boom" in detail["error"]
    assert sum(1 for d in detail["days"] if d["content"]) == 2

    monkeypatch.setattr(llm, "generate_day", lambda *a, **k: llm.normalize_day(FAKE_DAY))
    assert client.post(f"/api/roadmaps/{rid}/retry").status_code == 200
    assert client.get(f"/api/roadmaps/{rid}").json()["status"] == "done"


def test_llm_helpers():
    assert llm.extract_json('```json\n[{"a": 1}]\n```') == [{"a": 1}]
    assert llm.extract_json('Here you go: {"a": 2} thanks') == {"a": 2}
    quiz = llm.normalize_quiz(
        {"quiz": [
            {"question": "x", "options": ["one", "two", "three", "four"], "answer": "B", "explanation": "e"},
            {"question": "y", "options": ["one", "two"], "answer": "nonsense", "explanation": "e"},
        ]}
    )
    assert len(quiz) == 1 and quiz[0]["answer_index"] == 1
