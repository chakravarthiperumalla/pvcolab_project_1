# Roadmap Studio

A full-stack SaaS version of the n8n "AI Learning Roadmap Generator" workflow.
Users sign up, describe a topic, and get a day-by-day learning handbook (lessons, practice,
assignments, module quizzes) they can read in the app, track progress on, download as a PDF, or
receive by email.

- **Frontend:** React + Vite (`frontend/`)
- **Backend:** FastAPI + SQLAlchemy + JWT auth (`backend/`)
- **AI:** Claude via the Anthropic API (planner → per-day lessons → per-module quizzes)
- **Database:** SQLite by default, Postgres via `DATABASE_URL`

## How the n8n workflow maps to the app

| n8n node(s) | App equivalent |
|---|---|
| Form Trigger, Edit Fields, Validate Duration | `NewRoadmap.jsx` form + `RoadmapCreate` validation (1–180 days) |
| Course Planner, Parse Planner JSON | `llm.plan_roadmap` |
| Loop Over Days, Day Content Generator, Day JSON to Markdown | `generator._generate` (parallel workers) + `llm.generate_day` + `render.day_to_markdown` |
| Group Into Modules, Loop Over Modules, Module Quiz Generator | module grouping + `llm.generate_quiz` (interactive quizzes, scored in-app) |
| Final Assembly, Markdown to HTML, HTML to PDF | `render.roadmap_to_markdown` + `pdf.markdown_to_pdf` (no external PDF API) |
| Upload to Drive, Send Email | PDF download endpoint + optional SMTP email (`emailer.py`) |

Improvements over the workflow: system prompts are explicit, JSON parsing retries, days generate in
parallel instead of sequentially with waits, the output-format field is replaced by an in-app reader
plus PDF, the roadmap table shows real day titles, and failed runs resume without redoing finished work.

## Run it locally

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then set ANTHROPIC_API_KEY and a long random SECRET_KEY
uvicorn app.main:app --reload --port 8000
```

Run the tests (the LLM is mocked, no API key needed):

```bash
pytest
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173, proxies /api to localhost:8000
```

## Configuration (`backend/.env`)

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required for generation |
| `SECRET_KEY` | JWT signing key — set a long random value in production |
| `DATABASE_URL` | e.g. `postgresql+psycopg://user:pass@host/db` (install `psycopg[binary]`) |
| `PLANNER_MODEL`, `DAY_MODEL`, `QUIZ_MODEL` | Model per stage (defaults match the n8n workflow) |
| `MAX_ACTIVE_ROADMAPS_PER_USER` | Cost guard: concurrent generations per user (default 2) |
| `LLM_WORKERS` | Parallel LLM calls per roadmap (default 4) |
| `SMTP_*` | Enables "email me my handbook". Leave `SMTP_HOST` empty to disable |
| `FRONTEND_URL` | CORS origin and link target in emails |

## API

| Method | Path | |
|---|---|---|
| POST | `/api/auth/register`, `/api/auth/login` | returns a JWT |
| GET | `/api/auth/me` | |
| POST / GET | `/api/roadmaps` | create (starts background generation) / list |
| GET / DELETE | `/api/roadmaps/{id}` | detail with days and quizzes / delete |
| POST | `/api/roadmaps/{id}/retry` | resume a failed roadmap |
| PATCH | `/api/roadmaps/{id}/days/{n}` | mark a day complete |
| POST | `/api/roadmaps/{id}/quizzes/{module}/score` | save a quiz score |
| GET | `/api/roadmaps/{id}/pdf` | download the handbook |
| POST | `/api/roadmaps/{id}/email` | email the PDF to the account address |

## Before you deploy

- Generation runs in-process (FastAPI background tasks). That's fine for one server; interrupted jobs
  are marked failed on restart and can be resumed with Retry. For multiple workers or heavier
  traffic, move `generator.run_generation` onto a queue (Celery/RQ/Arq).
- Add rate limiting on the auth endpoints and consider email verification and payments/credits —
  each 30-day roadmap costs real API money.
- Serve the built frontend (`npm run build` → `dist/`) from a static host or reverse proxy that
  forwards `/api` to the backend, and use Postgres plus HTTPS.
