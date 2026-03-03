from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"


class TaskStrategy(str, Enum):
    SERIAL = "serial"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"


class SessionStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"


class EventType(str, Enum):
    TASK_NEW = "task.new"
    TASK_PLANNED = "task.planned"
    SESSION_START = "session.start"
    SESSION_DONE = "session.done"
    OUTPUT_RECEIVED = "output.received"
    DECISION_NEEDED = "decision.needed"
    DECISION_MADE = "decision.made"
    TASK_COMPLETE = "task.complete"
    ERROR = "error"


class Task(BaseModel):
    id: str = Field(default_factory=_new_id)
    title: str
    raw_input: str = ""
    ultra_prompt: str = ""
    strategy: TaskStrategy | None = None
    status: TaskStatus = TaskStatus.PENDING
    parent_id: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    completed_at: datetime | None = None


class Session(BaseModel):
    id: str = Field(default_factory=_new_id)
    task_id: str
    tmux_pane: str = ""
    status: SessionStatus = SessionStatus.STARTING
    prompt_sent: str = ""
    output_log: str = ""
    started_at: datetime = Field(default_factory=_utcnow)
    ended_at: datetime | None = None


class Event(BaseModel):
    id: int | None = None
    event_type: EventType
    payload: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utcnow)


class ErrorMemory(BaseModel):
    id: int | None = None
    project: str
    error_desc: str
    root_cause: str
    prevention: str
    created_at: datetime = Field(default_factory=_utcnow)


class Reflection(BaseModel):
    id: int | None = None
    session_id: str
    achieved: str = ""
    issues: str = ""
    learnings: str = ""
    next_steps: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
