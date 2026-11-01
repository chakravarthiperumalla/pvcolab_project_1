import os
import tempfile

# Must be set before the app is imported.
_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_db.name}"
os.environ["SECRET_KEY"] = "test-secret"
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
        yield c


def _register(client, email="a@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_auth_flow(client):
    headers = _register(client, "auth@example.com")
    assert client.get("/api/auth/me", headers=headers).json()["email"] == "auth@example.com"
    assert client.post("/api/auth/register", json={"email": "auth@example.com", "password": "password123"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "auth@example.com", "password": "wrong-pass"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "auth@example.com", "password": "password123"}).status_code == 200
    assert client.get("/api/roadmaps").status_code == 401


def test_generate_progress_quiz_pdf(client):
    headers = _register(client, "gen@example.com")
    r = client.post(
        "/api/roadmaps",
        headers=headers,
        json={"topic": "Python", "duration": 5, "level": "Beginner", "hours_per_day": 2},
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    # TestClient runs background tasks before returning, so the roadmap is already finished.
    detail = client.get(f"/api/roadmaps/{rid}", headers=headers).json()
    assert detail["status"] == "done", detail
    assert len(detail["days"]) == 5
    assert len(detail["quizzes"]) == 3  # 5 days at 2 per module
    assert detail["done_steps"] == detail["total_steps"] == 8

    assert client.patch(f"/api/roadmaps/{rid}/days/1", headers=headers, json={"completed": True}).status_code == 200
    assert client.post(f"/api/roadmaps/{rid}/quizzes/1/score", headers=headers, json={"score": 1, "total": 1}).status_code == 200
    assert client.post(f"/api/roadmaps/{rid}/quizzes/1/score", headers=headers, json={"score": 5, "total": 1}).status_code == 422
    detail = client.get(f"/api/roadmaps/{rid}", headers=headers).json()
    assert detail["days"][0]["completed"] is True
    assert detail["quizzes"][0]["last_score"] == 1

    pdf = client.get(f"/api/roadmaps/{rid}/pdf", headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_isolation_and_validation(client):
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    rid = client.post(
        "/api/roadmaps", headers=owner, json={"topic": "Rust", "duration": 2, "level": "Advanced", "hours_per_day": 1}
    ).json()["id"]
    assert client.get(f"/api/roadmaps/{rid}", headers=other).status_code == 404
    assert client.delete(f"/api/roadmaps/{rid}", headers=other).status_code == 404
    assert client.post(
        "/api/roadmaps", headers=owner, json={"topic": "Rust", "duration": 999, "level": "Advanced", "hours_per_day": 1}
    ).status_code == 422
    assert client.post(
        "/api/roadmaps", headers=owner, json={"topic": "Rust", "duration": 2, "level": "Advanced", "hours_per_day": 1, "email_when_done": True}
    ).status_code == 400  # SMTP not configured in tests
    assert client.delete(f"/api/roadmaps/{rid}", headers=owner).status_code == 204


def test_failure_then_resume(client, monkeypatch):
    headers = _register(client, "retry@example.com")
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom")
        return llm.normalize_day(FAKE_DAY)

    monkeypatch.setattr(llm, "generate_day", flaky)
    rid = client.post(
        "/api/roadmaps", headers=headers, json={"topic": "Go", "duration": 3, "level": "Beginner", "hours_per_day": 1}
    ).json()["id"]
    detail = client.get(f"/api/roadmaps/{rid}", headers=headers).json()
    assert detail["status"] == "failed" and "boom" in detail["error"]
    assert sum(1 for d in detail["days"] if d["content"]) == 2

    monkeypatch.setattr(llm, "generate_day", lambda *a, **k: llm.normalize_day(FAKE_DAY))
    assert client.post(f"/api/roadmaps/{rid}/retry", headers=headers).status_code == 200
    assert client.get(f"/api/roadmaps/{rid}", headers=headers).json()["status"] == "done"


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
