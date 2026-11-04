import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update

from .config import settings
from .database import Base, SessionLocal, engine
from .models import ACTIVE_STATUSES, Roadmap
from .routers import roadmaps

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    # Jobs run in-process, so anything still "active" at startup was interrupted by a restart.
    with SessionLocal() as db:
        db.execute(
            update(Roadmap)
            .where(Roadmap.status.in_(ACTIVE_STATUSES))
            .values(status="failed", error="Generation was interrupted by a server restart. Press Retry to resume.")
        )
        db.commit()
    yield


app = FastAPI(title="AI Learning Roadmap Generator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roadmaps.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
