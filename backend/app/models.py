from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


ACTIVE_STATUSES = ("queued", "planning", "generating")


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(200))
    duration: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(20))
    hours_per_day: Mapped[float] = mapped_column(Float)
    # queued | planning | generating | done | failed
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    done_steps: Mapped[int] = mapped_column(Integer, default=0)
    # Where to send the finished handbook, if the user asked for it at creation.
    email_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    days: Mapped[list["Day"]] = relationship(
        back_populates="roadmap", cascade="all, delete-orphan", order_by="Day.day_number"
    )
    quizzes: Mapped[list["Quiz"]] = relationship(
        back_populates="roadmap", cascade="all, delete-orphan", order_by="Quiz.module_number"
    )


class Day(Base):
    __tablename__ = "days"

    id: Mapped[int] = mapped_column(primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(ForeignKey("roadmaps.id"), index=True)
    day_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    topic_focus: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)

    roadmap: Mapped[Roadmap] = relationship(back_populates="days")


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(ForeignKey("roadmaps.id"), index=True)
    module_number: Mapped[int] = mapped_column(Integer)
    day_range: Mapped[str] = mapped_column(String(20))
    questions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    last_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_total: Mapped[int | None] = mapped_column(Integer, nullable=True)

    roadmap: Mapped[Roadmap] = relationship(back_populates="quizzes")
