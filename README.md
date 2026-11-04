# Roadmap Studio

Describe a topic, get a day-by-day learning handbook. Roadmap Studio plans a course with
Claude, writes every day's lesson (theory, examples, common mistakes, practice, an assignment),
builds a quiz after every module, and gives you a reader with progress tracking, scored quizzes
and a PDF export.

Not just Anthropic API free gemini api also will be very help full to generate the skill set and total sylabus of the skill

It started as an n8n workflow and became a small self-hosted app.

- **Frontend:** React + Vite (`frontend/`)
- **Backend:** FastAPI + SQLAlchemy (`backend/`)
- **AI:** Claude via the Anthropic API — planner → per-day lessons → per-module quizzes
- **Database:** SQLite by default, Postgres via `DATABASE_URL`

## ⚠️ There is no login — read this before you deploy

This app has **no authentication**. Anyone who can reach it can read every roadmap, create new
ones, and delete them. That is deliberate: it is built to be run by one person on their own
machine.

Generating a roadmap spends **your** money on the Anthropic API — roughly one model call per day
of the plan, so a 30-day roadmap is ~35 calls. If you expose this to the internet with your API
key in `.env`, strangers can run up your bill.

Run it on `localhost` (the default), or put it behind a reverse proxy with your own auth
(basic auth, Tailscale, an SSO proxy) before it leaves your machine. `MAX_ACTIVE_ROADMAPS`
caps concurrent generations but does **not** cap how many someone can run in a day.

## Run it locally

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then set ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173, proxies /api to localhost:8000
```

Open http://localhost:5173 and create a roadmap. Start with a short one (3 days) to check your
API key works before paying for a 30-day plan.

### Tests

```bash
cd backend && pytest        # the LLM is mocked, so no API key is needed
```

## Configuration (`backend/.env`)

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required for generation |
| `DATABASE_URL` | e.g. `postgresql+psycopg://user:pass@host/db` (install `psycopg[binary]`) |
| `PLANNER_MODEL`, `DAY_MODEL`, `QUIZ_MODEL` | Model per stage |
| `MAX_DAYS` | Hard cap on roadmap length (default 180) |
| `DAYS_PER_MODULE` | Days per quiz module (default 6) |
| `LLM_WORKERS` | Parallel LLM calls per roadmap (default 4) |
| `MAX_ACTIVE_ROADMAPS` | Cost guard: concurrent generations (default 2) |
| `SMTP_*` | Enables emailing the PDF. Leave `SMTP_HOST` empty to disable |
| `FRONTEND_URL` | CORS origin and link target in emails |

## API

No authentication headers are needed on any endpoint.

| Method | Path | |
|---|---|---|
| GET | `/api/health` | liveness |
| POST / GET | `/api/roadmaps` | create (starts background generation) / list |
| GET / DELETE | `/api/roadmaps/{id}` | detail with days and quizzes / delete |
| POST | `/api/roadmaps/{id}/retry` | resume a failed roadmap |
| PATCH | `/api/roadmaps/{id}/days/{n}` | mark a day complete |
| POST | `/api/roadmaps/{id}/quizzes/{module}/score` | save a quiz score |
| GET | `/api/roadmaps/{id}/pdf` | download the handbook |
| POST | `/api/roadmaps/{id}/email` | email the PDF (`{"to": "..."}`, or the address saved at creation) |

Interactive docs are at http://localhost:8000/docs while the backend runs.

## How it works

Generation runs as a FastAPI background task and is **resumable**: each day and quiz is saved as
soon as it is written, so a failed run picks up where it stopped instead of re-paying for
finished work. Press Retry on a failed roadmap.

| n8n node(s) | App equivalent |
|---|---|
| Form Trigger, Validate Duration | `NewRoadmap.jsx` + `RoadmapCreate` validation (1–180 days) |
| Course Planner, Parse Planner JSON | `llm.plan_roadmap` |
| Loop Over Days, Day Content Generator | `generator._generate` (thread pool) + `llm.generate_day` |
| Group Into Modules, Module Quiz Generator | module grouping + `llm.generate_quiz` |
| Final Assembly, Markdown to HTML, HTML to PDF | `render.roadmap_to_markdown` + `pdf.markdown_to_pdf` |
| Upload to Drive, Send Email | PDF download endpoint + optional SMTP (`emailer.py`) |

## Known limits

- Jobs run in-process. Fine for one server; anything interrupted by a restart is marked failed
  and can be resumed with Retry. For multiple workers, move `generator.run_generation` onto a
  queue (Celery/RQ/Arq).
- No rate limiting. See the warning above.
- Quality depends entirely on the model. Long roadmaps drift; the planner is the piece worth
  tuning first.

## License

MIT — see [LICENSE](LICENSE).
