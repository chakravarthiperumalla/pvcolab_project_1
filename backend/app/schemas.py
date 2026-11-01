from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RoadmapCreate(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    duration: int = Field(ge=1, le=180)
    level: Literal["Beginner", "Intermediate", "Advanced"]
    hours_per_day: float = Field(gt=0, le=12)
    email_when_done: bool = False


class RoadmapSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    topic: str
    duration: int
    level: str
    hours_per_day: float
    status: str
    error: str | None
    total_steps: int
    done_steps: int
    created_at: datetime


class DayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    day_number: int
    title: str
    topic_focus: str
    completed: bool
    content: dict | None


class QuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    module_number: int
    day_range: str
    questions: list | None
    last_score: int | None
    last_total: int | None


class RoadmapDetail(RoadmapSummary):
    days: list[DayOut]
    quizzes: list[QuizOut]


class DayProgress(BaseModel):
    completed: bool


class QuizScore(BaseModel):
    score: int = Field(ge=0)
    total: int = Field(ge=1)
