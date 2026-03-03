# Coding Automation Loop — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Meta-Orchestrator that automates the human operator role at the Claude Code terminal — from Telegram input to autonomous multi-agent execution with live monitoring.

**Architecture:** Event-driven asyncio pipeline with 4 layers (Input, Brain, Execution, Monitoring) connected via asyncio Queue event bus. Python controls Claude Code CLI through libtmux. SQLite for persistence.

**Tech Stack:** Python 3.12+, asyncio, libtmux, python-telegram-bot, whisper.cpp, FastAPI, HTMX, Tailwind, aiosqlite, Pydantic v2, Jinja2

**Design Doc:** `docs/plans/2026-03-03-coding-automation-loop-design.md`

---

## Task 1: Project Setup & Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `config.yaml`
- Create: `.gitignore`
- Create: `core/__init__.py`
- Create: `input/__init__.py`
- Create: `brain/__init__.py`
- Create: `execution/__init__.py`
- Create: `monitoring/__init__.py`
- Create: `tests/__init__.py`
- Create: `data/.gitkeep`
- Create: `brain/templates/.gitkeep`
- Create: `monitoring/templates/.gitkeep`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "coding-automation-loop"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "libtmux>=0.37.0",
    "python-telegram-bot[webhooks]>=21.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "aiosqlite>=0.20.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "jinja2>=3.1.0",
    "pyyaml>=6.0",
    "websockets>=13.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0",
    "ruff>=0.8.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

**Step 2: Create config.yaml**

```yaml
telegram:
  token: ""  # Set via TELEGRAM_TOKEN env var
  allowed_users: []  # Telegram user IDs allowed to interact

whisper:
  model: "base"
  language: "de"

dashboard:
  host: "0.0.0.0"
  port: 8080

database:
  path: "data/loop.db"

tmux:
  session_prefix: "loop"
  claude_command: "claude --dangerously-skip-permissions"

orchestrator:
  poll_interval_ms: 500
  max_parallel_sessions: 4
  auto_approve_permissions: true
```

**Step 3: Create .gitignore**

```
__pycache__/
*.pyc
.venv/
venv/
data/loop.db
.env
*.egg-info/
dist/
.ruff_cache/
.pytest_cache/
```

**Step 4: Create all __init__.py and placeholder files**

Create empty `__init__.py` in: `core/`, `input/`, `brain/`, `execution/`, `monitoring/`, `tests/`
Create empty `.gitkeep` in: `data/`, `brain/templates/`, `monitoring/templates/`

**Step 5: Create virtual environment and install**

```bash
cd "/Users/giulianofalco/Desktop/coding automation loop"
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Step 6: Verify setup**

```bash
python -c "import libtmux; import pydantic; import fastapi; print('All imports OK')"
pytest --co  # Should find 0 tests, no errors
```

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: project setup with dependencies and config"
```

---

## Task 2: Core Models (Pydantic)

**Files:**
- Create: `core/models.py`
- Create: `tests/test_models.py`

**Step 1: Write failing tests**

```python
# tests/test_models.py
import pytest
from datetime import datetime

from core.models import (
    Task, TaskStatus, TaskStrategy,
    Session, SessionStatus,
    Event, EventType,
    ErrorMemory, Reflection,
)


def test_task_creation_defaults():
    task = Task(title="Fix login bug", raw_input="fix the login")
    assert task.status == TaskStatus.PENDING
    assert task.strategy is None
    assert task.parent_id is None
    assert task.id is not None
    assert isinstance(task.created_at, datetime)


def test_task_strategy_enum():
    assert TaskStrategy.SERIAL.value == "serial"
    assert TaskStrategy.PARALLEL.value == "parallel"
    assert TaskStrategy.HIERARCHICAL.value == "hierarchical"


def test_session_creation():
    session = Session(task_id="task-1", tmux_pane="loop:0.1")
    assert session.status == SessionStatus.STARTING
    assert session.output_log == ""


def test_event_creation():
    event = Event(event_type=EventType.TASK_NEW, payload={"task_id": "1"})
    assert event.event_type == EventType.TASK_NEW
    assert isinstance(event.timestamp, datetime)


def test_error_memory_creation():
    err = ErrorMemory(
        project="myproject",
        error_desc="Auth middleware missing",
        root_cause="Route added without middleware",
        prevention="Always add auth middleware to new routes",
    )
    assert err.project == "myproject"


def test_reflection_creation():
    ref = Reflection(
        session_id="sess-1",
        achieved="Implemented login",
        issues="Test flaky",
        learnings="Need retry logic",
        next_steps="Add retry",
    )
    assert ref.session_id == "sess-1"
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_models.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'core.models'`

**Step 3: Implement models**

```python
# core/models.py
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
```

**Step 4: Run tests**

```bash
pytest tests/test_models.py -v
```
Expected: All 6 PASS

**Step 5: Commit**

```bash
git add core/models.py tests/test_models.py
git commit -m "feat: core Pydantic models for tasks, sessions, events"
```

---

## Task 3: Event Bus

**Files:**
- Create: `core/event_bus.py`
- Create: `tests/test_event_bus.py`

**Step 1: Write failing tests**

```python
# tests/test_event_bus.py
import asyncio
import pytest

from core.event_bus import EventBus
from core.models import Event, EventType


@pytest.fixture
def bus():
    return EventBus()


async def test_subscribe_and_publish(bus):
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe(EventType.TASK_NEW, handler)
    event = Event(event_type=EventType.TASK_NEW, payload={"title": "test"})
    await bus.publish(event)
    await asyncio.sleep(0.05)
    assert len(received) == 1
    assert received[0].payload["title"] == "test"


async def test_multiple_subscribers(bus):
    count = {"a": 0, "b": 0}

    async def handler_a(event: Event):
        count["a"] += 1

    async def handler_b(event: Event):
        count["b"] += 1

    bus.subscribe(EventType.TASK_NEW, handler_a)
    bus.subscribe(EventType.TASK_NEW, handler_b)
    await bus.publish(Event(event_type=EventType.TASK_NEW))
    await asyncio.sleep(0.05)
    assert count["a"] == 1
    assert count["b"] == 1


async def test_wildcard_subscriber(bus):
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe_all(handler)
    await bus.publish(Event(event_type=EventType.TASK_NEW))
    await bus.publish(Event(event_type=EventType.ERROR))
    await asyncio.sleep(0.05)
    assert len(received) == 2


async def test_no_crosstalk(bus):
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe(EventType.TASK_NEW, handler)
    await bus.publish(Event(event_type=EventType.ERROR))
    await asyncio.sleep(0.05)
    assert len(received) == 0
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_event_bus.py -v
```

**Step 3: Implement event bus**

```python
# core/event_bus.py
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Awaitable

from core.models import Event, EventType

logger = logging.getLogger(__name__)

Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Handler]] = defaultdict(list)
        self._global_handlers: list[Handler] = []

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        self._global_handlers.append(handler)

    async def publish(self, event: Event) -> None:
        handlers = list(self._handlers.get(event.event_type, []))
        handlers.extend(self._global_handlers)
        for handler in handlers:
            try:
                asyncio.create_task(handler(event))
            except Exception:
                logger.exception("Handler failed for event %s", event.event_type)
```

**Step 4: Run tests**

```bash
pytest tests/test_event_bus.py -v
```
Expected: All 4 PASS

**Step 5: Commit**

```bash
git add core/event_bus.py tests/test_event_bus.py
git commit -m "feat: asyncio event bus with subscribe, publish, wildcard"
```

---

## Task 4: Database Layer

**Files:**
- Create: `core/database.py`
- Create: `tests/test_database.py`

**Step 1: Write failing tests**

```python
# tests/test_database.py
import pytest

from core.database import Database
from core.models import Task, TaskStatus, Session, Event, EventType, ErrorMemory, Reflection


@pytest.fixture
async def db(tmp_path):
    d = Database(str(tmp_path / "test.db"))
    await d.init()
    yield d
    await d.close()


async def test_init_creates_tables(db):
    tables = await db.list_tables()
    assert "tasks" in tables
    assert "sessions" in tables
    assert "events" in tables
    assert "error_memory" in tables
    assert "reflections" in tables


async def test_save_and_get_task(db):
    task = Task(title="Test task", raw_input="do something")
    await db.save_task(task)
    loaded = await db.get_task(task.id)
    assert loaded is not None
    assert loaded.title == "Test task"


async def test_update_task_status(db):
    task = Task(title="Test")
    await db.save_task(task)
    task.status = TaskStatus.RUNNING
    await db.save_task(task)
    loaded = await db.get_task(task.id)
    assert loaded.status == TaskStatus.RUNNING


async def test_list_tasks_by_status(db):
    await db.save_task(Task(title="A", status=TaskStatus.PENDING))
    await db.save_task(Task(title="B", status=TaskStatus.RUNNING))
    await db.save_task(Task(title="C", status=TaskStatus.PENDING))
    pending = await db.list_tasks(status=TaskStatus.PENDING)
    assert len(pending) == 2


async def test_save_and_get_session(db):
    session = Session(task_id="t1", tmux_pane="loop:0.1")
    await db.save_session(session)
    loaded = await db.get_session(session.id)
    assert loaded.tmux_pane == "loop:0.1"


async def test_save_event(db):
    event = Event(event_type=EventType.TASK_NEW, payload={"x": 1})
    await db.save_event(event)
    events = await db.list_events(limit=10)
    assert len(events) == 1
    assert events[0].payload == {"x": 1}


async def test_save_error_memory(db):
    err = ErrorMemory(project="p", error_desc="e", root_cause="r", prevention="p")
    await db.save_error_memory(err)
    errors = await db.list_error_memories(project="p")
    assert len(errors) == 1


async def test_save_reflection(db):
    ref = Reflection(session_id="s1", achieved="did stuff")
    await db.save_reflection(ref)
    refs = await db.list_reflections(session_id="s1")
    assert len(refs) == 1
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_database.py -v
```

**Step 3: Implement database**

```python
# core/database.py
from __future__ import annotations

import json
import logging

import aiosqlite

from core.models import (
    Task, TaskStatus, Session, Event, EventType,
    ErrorMemory, Reflection,
)

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    raw_input TEXT DEFAULT '',
    ultra_prompt TEXT DEFAULT '',
    strategy TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    parent_id TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    tmux_pane TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'starting',
    prompt_sent TEXT DEFAULT '',
    output_log TEXT DEFAULT '',
    started_at TEXT NOT NULL,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    payload TEXT DEFAULT '{}',
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS error_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    error_desc TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    prevention TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    achieved TEXT DEFAULT '',
    issues TEXT DEFAULT '',
    learnings TEXT DEFAULT '',
    next_steps TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS context_cache (
    project TEXT,
    key TEXT,
    value TEXT,
    updated_at TEXT,
    PRIMARY KEY (project, key)
);
"""


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def list_tables(self) -> list[str]:
        cursor = await self._db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        rows = await cursor.fetchall()
        return [r["name"] for r in rows]

    # --- Tasks ---
    async def save_task(self, task: Task) -> None:
        await self._db.execute(
            """INSERT OR REPLACE INTO tasks
               (id, title, raw_input, ultra_prompt, strategy, status, parent_id, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task.id, task.title, task.raw_input, task.ultra_prompt,
             task.strategy.value if task.strategy else None,
             task.status.value, task.parent_id,
             task.created_at.isoformat(),
             task.completed_at.isoformat() if task.completed_at else None),
        )
        await self._db.commit()

    async def get_task(self, task_id: str) -> Task | None:
        cursor = await self._db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_task(row)

    async def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        if status:
            cursor = await self._db.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at", (status.value,)
            )
        else:
            cursor = await self._db.execute("SELECT * FROM tasks ORDER BY created_at")
        return [_row_to_task(r) for r in await cursor.fetchall()]

    # --- Sessions ---
    async def save_session(self, session: Session) -> None:
        await self._db.execute(
            """INSERT OR REPLACE INTO sessions
               (id, task_id, tmux_pane, status, prompt_sent, output_log, started_at, ended_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session.id, session.task_id, session.tmux_pane, session.status.value,
             session.prompt_sent, session.output_log, session.started_at.isoformat(),
             session.ended_at.isoformat() if session.ended_at else None),
        )
        await self._db.commit()

    async def get_session(self, session_id: str) -> Session | None:
        cursor = await self._db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_session(row)

    async def list_sessions(self, task_id: str | None = None) -> list[Session]:
        if task_id:
            cursor = await self._db.execute(
                "SELECT * FROM sessions WHERE task_id = ? ORDER BY started_at", (task_id,)
            )
        else:
            cursor = await self._db.execute("SELECT * FROM sessions ORDER BY started_at")
        return [_row_to_session(r) for r in await cursor.fetchall()]

    # --- Events ---
    async def save_event(self, event: Event) -> None:
        await self._db.execute(
            "INSERT INTO events (event_type, payload, timestamp) VALUES (?, ?, ?)",
            (event.event_type.value, json.dumps(event.payload), event.timestamp.isoformat()),
        )
        await self._db.commit()

    async def list_events(self, limit: int = 50) -> list[Event]:
        cursor = await self._db.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [_row_to_event(r) for r in await cursor.fetchall()]

    # --- Error Memory ---
    async def save_error_memory(self, err: ErrorMemory) -> None:
        await self._db.execute(
            """INSERT INTO error_memory (project, error_desc, root_cause, prevention, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (err.project, err.error_desc, err.root_cause, err.prevention, err.created_at.isoformat()),
        )
        await self._db.commit()

    async def list_error_memories(self, project: str) -> list[ErrorMemory]:
        cursor = await self._db.execute(
            "SELECT * FROM error_memory WHERE project = ? ORDER BY created_at DESC", (project,)
        )
        return [_row_to_error(r) for r in await cursor.fetchall()]

    # --- Reflections ---
    async def save_reflection(self, ref: Reflection) -> None:
        await self._db.execute(
            """INSERT INTO reflections (session_id, achieved, issues, learnings, next_steps, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (ref.session_id, ref.achieved, ref.issues, ref.learnings,
             ref.next_steps, ref.created_at.isoformat()),
        )
        await self._db.commit()

    async def list_reflections(self, session_id: str) -> list[Reflection]:
        cursor = await self._db.execute(
            "SELECT * FROM reflections WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        )
        return [_row_to_reflection(r) for r in await cursor.fetchall()]


# --- Row mappers ---

def _row_to_task(row) -> Task:
    from datetime import datetime, timezone
    return Task(
        id=row["id"], title=row["title"], raw_input=row["raw_input"],
        ultra_prompt=row["ultra_prompt"],
        strategy=row["strategy"] if row["strategy"] else None,
        status=row["status"], parent_id=row["parent_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
    )


def _row_to_session(row) -> Session:
    from datetime import datetime
    return Session(
        id=row["id"], task_id=row["task_id"], tmux_pane=row["tmux_pane"],
        status=row["status"], prompt_sent=row["prompt_sent"],
        output_log=row["output_log"],
        started_at=datetime.fromisoformat(row["started_at"]),
        ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
    )


def _row_to_event(row) -> Event:
    from datetime import datetime
    return Event(
        id=row["id"], event_type=row["event_type"],
        payload=json.loads(row["payload"]),
        timestamp=datetime.fromisoformat(row["timestamp"]),
    )


def _row_to_error(row) -> ErrorMemory:
    from datetime import datetime
    return ErrorMemory(
        id=row["id"], project=row["project"], error_desc=row["error_desc"],
        root_cause=row["root_cause"], prevention=row["prevention"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_reflection(row) -> Reflection:
    from datetime import datetime
    return Reflection(
        id=row["id"], session_id=row["session_id"], achieved=row["achieved"],
        issues=row["issues"], learnings=row["learnings"], next_steps=row["next_steps"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
```

**Step 4: Run tests**

```bash
pytest tests/test_database.py -v
```
Expected: All 9 PASS

**Step 5: Commit**

```bash
git add core/database.py tests/test_database.py
git commit -m "feat: SQLite database layer with all CRUD operations"
```

---

## Task 5: tmux Controller

**Files:**
- Create: `execution/tmux_controller.py`
- Create: `tests/test_tmux_controller.py`

**Step 1: Write failing tests**

```python
# tests/test_tmux_controller.py
import pytest

from execution.tmux_controller import TmuxController


@pytest.fixture
def ctrl():
    """Real tmux — tests need tmux installed and running."""
    c = TmuxController(session_prefix="test-loop")
    yield c
    c.cleanup_all()


def test_create_session(ctrl):
    pane = ctrl.create_session("worker-1")
    assert pane is not None
    assert "test-loop" in pane


def test_send_keys_and_capture(ctrl):
    pane = ctrl.create_session("echo-test")
    ctrl.send_keys(pane, "echo HELLO_LOOP")
    import time; time.sleep(0.5)
    output = ctrl.capture_output(pane)
    assert "HELLO_LOOP" in output


def test_list_sessions(ctrl):
    ctrl.create_session("list-1")
    ctrl.create_session("list-2")
    sessions = ctrl.list_sessions()
    assert len(sessions) >= 2


def test_kill_session(ctrl):
    pane = ctrl.create_session("kill-me")
    session_name = pane.split(":")[0]
    ctrl.kill_session(session_name)
    sessions = ctrl.list_sessions()
    assert session_name not in [s["name"] for s in sessions]
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_tmux_controller.py -v
```

**Step 3: Implement tmux controller**

```python
# execution/tmux_controller.py
from __future__ import annotations

import logging
import time

import libtmux

logger = logging.getLogger(__name__)


class TmuxController:
    def __init__(self, session_prefix: str = "loop") -> None:
        self._prefix = session_prefix
        self._server = libtmux.Server()

    def create_session(self, name: str) -> str:
        """Create a tmux session and return pane identifier like 'loop-name:0.0'."""
        session_name = f"{self._prefix}-{name}"
        try:
            session = self._server.new_session(
                session_name=session_name, detach=True
            )
        except libtmux.exc.TmuxSessionExists:
            session = self._server.sessions.get(session_name=session_name)
        window = session.active_window
        pane = window.active_pane
        return f"{session_name}:{window.index}.{pane.index}"

    def send_keys(self, pane_id: str, text: str, enter: bool = True) -> None:
        """Send keystrokes to a tmux pane."""
        pane = self._resolve_pane(pane_id)
        pane.send_keys(text, enter=enter)

    def capture_output(self, pane_id: str, lines: int = 200) -> str:
        """Capture visible output from a pane."""
        pane = self._resolve_pane(pane_id)
        return "\n".join(pane.capture_pane())

    def list_sessions(self) -> list[dict]:
        """List all sessions with our prefix."""
        result = []
        for s in self._server.sessions:
            if s.name.startswith(self._prefix):
                result.append({
                    "name": s.name,
                    "windows": len(s.windows),
                    "created": s.get("session_created", ""),
                })
        return result

    def kill_session(self, session_name: str) -> None:
        """Kill a tmux session by name."""
        try:
            session = self._server.sessions.get(session_name=session_name)
            if session:
                session.kill()
        except Exception:
            logger.warning("Could not kill session %s", session_name)

    def cleanup_all(self) -> None:
        """Kill all sessions with our prefix."""
        for s in list(self._server.sessions):
            if s.name.startswith(self._prefix):
                try:
                    s.kill()
                except Exception:
                    pass

    def _resolve_pane(self, pane_id: str) -> libtmux.Pane:
        """Resolve 'session:window.pane' to a libtmux Pane object."""
        parts = pane_id.split(":")
        session_name = parts[0]
        win_pane = parts[1] if len(parts) > 1 else "0.0"
        win_idx, pane_idx = win_pane.split(".")

        session = self._server.sessions.get(session_name=session_name)
        window = session.windows.get(window_index=win_idx)
        pane = window.panes.get(pane_index=pane_idx)
        return pane
```

**Step 4: Run tests** (requires tmux server running)

```bash
pytest tests/test_tmux_controller.py -v
```
Expected: All 4 PASS

**Step 5: Commit**

```bash
git add execution/tmux_controller.py tests/test_tmux_controller.py
git commit -m "feat: libtmux controller for session management"
```

---

## Task 6: Output Parser

**Files:**
- Create: `execution/output_parser.py`
- Create: `tests/test_output_parser.py`

**Step 1: Write failing tests**

```python
# tests/test_output_parser.py
import pytest

from execution.output_parser import OutputParser, OutputSignal


def test_detect_question():
    parser = OutputParser()
    result = parser.parse("Which approach do you prefer?\n1. Option A\n2. Option B")
    assert OutputSignal.QUESTION in result.signals


def test_detect_error():
    parser = OutputParser()
    result = parser.parse("Error: ModuleNotFoundError: No module named 'foo'")
    assert OutputSignal.ERROR in result.signals


def test_detect_task_complete():
    parser = OutputParser()
    result = parser.parse("All tests passed. The feature is now complete and committed.")
    assert OutputSignal.TASK_DONE in result.signals


def test_detect_permission_request():
    parser = OutputParser()
    result = parser.parse("Do you want to allow this action? (y/n)")
    assert OutputSignal.PERMISSION in result.signals


def test_detect_idle():
    parser = OutputParser()
    result = parser.parse("$ ")  # Just a prompt
    assert OutputSignal.IDLE in result.signals


def test_extract_last_message():
    parser = OutputParser()
    output = "Some earlier output\n\nHere is my final answer about the implementation."
    result = parser.parse(output)
    assert "final answer" in result.last_message


def test_no_false_positives():
    parser = OutputParser()
    result = parser.parse("Writing the function to handle errors gracefully")
    assert OutputSignal.ERROR not in result.signals
    assert OutputSignal.QUESTION not in result.signals
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_output_parser.py -v
```

**Step 3: Implement output parser**

```python
# execution/output_parser.py
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class OutputSignal(str, Enum):
    QUESTION = "question"
    ERROR = "error"
    TASK_DONE = "task_done"
    PERMISSION = "permission"
    IDLE = "idle"
    WORKING = "working"


@dataclass
class ParseResult:
    signals: list[OutputSignal] = field(default_factory=list)
    last_message: str = ""
    raw: str = ""


# Patterns that indicate Claude is asking a question
_QUESTION_PATTERNS = [
    r"which .+ (?:do you|should|would you)",
    r"\?\s*$",
    r"(?:choose|select|pick) (?:one|an option|from)",
    r"(?:option [a-d]|1\.|2\.|3\.)",
]

# Real errors vs. talking about errors
_ERROR_PATTERNS = [
    r"^Error:",
    r"(?:ModuleNotFoundError|ImportError|TypeError|ValueError|SyntaxError|RuntimeError):",
    r"Traceback \(most recent call last\)",
    r"^FAILED ",
    r"panic:",
]

_DONE_PATTERNS = [
    r"(?:feature|task|implementation) (?:is )?(?:now )?(?:complete|done|finished)",
    r"all tests pass",
    r"successfully committed",
    r"committed as [a-f0-9]",
]

_PERMISSION_PATTERNS = [
    r"(?:do you )?want to allow",
    r"\(y/n\)",
    r"allow this (?:action|tool|operation)",
]

_IDLE_PATTERNS = [
    r"^\$\s*$",
    r"^>\s*$",
    r"^claude\s*>\s*$",
]


class OutputParser:
    def parse(self, raw_output: str) -> ParseResult:
        result = ParseResult(raw=raw_output)
        lines = raw_output.strip().split("\n")
        result.last_message = lines[-1].strip() if lines else ""
        lower = raw_output.lower()

        if _any_match(_IDLE_PATTERNS, raw_output.strip()):
            result.signals.append(OutputSignal.IDLE)
            return result

        if _any_match(_PERMISSION_PATTERNS, lower):
            result.signals.append(OutputSignal.PERMISSION)

        if _any_match(_ERROR_PATTERNS, raw_output):
            result.signals.append(OutputSignal.ERROR)

        if _any_match(_QUESTION_PATTERNS, lower):
            result.signals.append(OutputSignal.QUESTION)

        if _any_match(_DONE_PATTERNS, lower):
            result.signals.append(OutputSignal.TASK_DONE)

        if not result.signals:
            result.signals.append(OutputSignal.WORKING)

        return result


def _any_match(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.MULTILINE | re.IGNORECASE) for p in patterns)
```

**Step 4: Run tests**

```bash
pytest tests/test_output_parser.py -v
```
Expected: All 7 PASS

**Step 5: Commit**

```bash
git add execution/output_parser.py tests/test_output_parser.py
git commit -m "feat: output parser with signal detection for Claude Code output"
```

---

## Task 7: Context Engine

**Files:**
- Create: `brain/context_engine.py`
- Create: `tests/test_context_engine.py`

**Step 1: Write failing tests**

```python
# tests/test_context_engine.py
import pytest
import os

from brain.context_engine import ContextEngine


@pytest.fixture
def project_dir(tmp_path):
    """Create a fake project directory."""
    (tmp_path / "CLAUDE.md").write_text("# Rules\n- Use pytest\n- No console.log")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / ".git").mkdir()
    return str(tmp_path)


@pytest.fixture
def engine(project_dir):
    return ContextEngine(project_dir)


async def test_load_claude_md(engine, project_dir):
    ctx = await engine.load_context()
    assert "Use pytest" in ctx.claude_md


async def test_load_file_structure(engine):
    ctx = await engine.load_context()
    assert any("main.py" in f for f in ctx.file_structure)


async def test_context_to_string(engine):
    ctx = await engine.load_context()
    text = ctx.to_prompt_section()
    assert "# Projektkontext" in text
    assert "CLAUDE.md" in text


async def test_no_claude_md_still_works(tmp_path):
    engine = ContextEngine(str(tmp_path))
    ctx = await engine.load_context()
    assert ctx.claude_md == ""
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_context_engine.py -v
```

**Step 3: Implement context engine**

```python
# brain/context_engine.py
from __future__ import annotations

import asyncio
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProjectContext:
    claude_md: str = ""
    git_log: str = ""
    git_status: str = ""
    git_diff: str = ""
    file_structure: list[str] = field(default_factory=list)
    memory_files: dict[str, str] = field(default_factory=dict)
    active_tmux_sessions: list[str] = field(default_factory=list)
    error_memories: list[str] = field(default_factory=list)

    def to_prompt_section(self) -> str:
        parts = ["# Projektkontext"]
        if self.claude_md:
            parts.append(f"\n## CLAUDE.md Regeln\n{self.claude_md}")
        if self.git_status:
            parts.append(f"\n## Git Status\n```\n{self.git_status}\n```")
        if self.git_log:
            parts.append(f"\n## Letzte Commits\n```\n{self.git_log}\n```")
        if self.git_diff:
            parts.append(f"\n## Unstaged Changes\n```\n{self.git_diff[:2000]}\n```")
        if self.file_structure:
            tree = "\n".join(self.file_structure[:100])
            parts.append(f"\n## Dateistruktur\n```\n{tree}\n```")
        if self.error_memories:
            errs = "\n".join(f"- {e}" for e in self.error_memories)
            parts.append(f"\n## Fehler-History (NICHT WIEDERHOLEN!)\n{errs}")
        return "\n".join(parts)


class ContextEngine:
    def __init__(self, project_path: str) -> None:
        self._path = Path(project_path)

    async def load_context(self) -> ProjectContext:
        ctx = ProjectContext()
        ctx.claude_md = self._read_file("CLAUDE.md")
        ctx.file_structure = self._scan_files()
        if (self._path / ".git").exists():
            ctx.git_log = await self._run_git("log", "--oneline", "-20")
            ctx.git_status = await self._run_git("status", "--short")
            ctx.git_diff = await self._run_git("diff")
        ctx.memory_files = self._load_memory_files()
        ctx.active_tmux_sessions = await self._list_tmux()
        return ctx

    def _read_file(self, name: str) -> str:
        path = self._path / name
        if path.exists():
            return path.read_text(errors="replace")[:5000]
        return ""

    def _scan_files(self) -> list[str]:
        result = []
        for root, dirs, files in os.walk(self._path):
            dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "__pycache__", "node_modules", ".next"}]
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), self._path)
                result.append(rel)
            if len(result) > 200:
                break
        return sorted(result)

    def _load_memory_files(self) -> dict[str, str]:
        memory_dir = self._path / ".claude" / "memory"
        if not memory_dir.exists():
            return {}
        result = {}
        for f in memory_dir.glob("*.md"):
            result[f.name] = f.read_text(errors="replace")[:3000]
        return result

    async def _run_git(self, *args: str) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", *args,
                cwd=str(self._path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return stdout.decode(errors="replace").strip()
        except Exception:
            return ""

    async def _list_tmux(self) -> list[str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "tmux", "list-sessions", "-F", "#{session_name}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return [l for l in stdout.decode().strip().split("\n") if l]
        except Exception:
            return []
```

**Step 4: Run tests**

```bash
pytest tests/test_context_engine.py -v
```
Expected: All 4 PASS

**Step 5: Commit**

```bash
git add brain/context_engine.py tests/test_context_engine.py
git commit -m "feat: context engine loads project state for prompt generation"
```

---

## Task 8: Prompt Generator

**Files:**
- Create: `brain/prompt_generator.py`
- Create: `brain/templates/feature.j2`
- Create: `brain/templates/bugfix.j2`
- Create: `brain/templates/base.j2`
- Create: `tests/test_prompt_generator.py`

**Step 1: Write failing tests**

```python
# tests/test_prompt_generator.py
import pytest

from brain.prompt_generator import PromptGenerator
from brain.context_engine import ProjectContext


@pytest.fixture
def generator():
    return PromptGenerator()


@pytest.fixture
def sample_context():
    return ProjectContext(
        claude_md="# Rules\n- Use pytest",
        git_log="abc123 last commit",
        git_status="M src/main.py",
        file_structure=["src/main.py", "tests/test_main.py"],
        error_memories=["Route /users missing auth middleware"],
    )


def test_generate_feature_prompt(generator, sample_context):
    prompt = generator.generate(
        task_type="feature",
        user_input="Add user login",
        context=sample_context,
        complexity="medium",
    )
    assert "Add user login" in prompt
    assert "Projektkontext" in prompt
    assert "Use pytest" in prompt
    assert "NICHT WIEDERHOLEN" in prompt


def test_generate_bugfix_prompt(generator, sample_context):
    prompt = generator.generate(
        task_type="bugfix",
        user_input="Fix login crash",
        context=sample_context,
        complexity="simple",
    )
    assert "Fix login crash" in prompt
    assert "Root-Cause" in prompt


def test_ultrathink_for_complex(generator, sample_context):
    prompt = generator.generate(
        task_type="feature",
        user_input="Refactor auth system",
        context=sample_context,
        complexity="complex",
    )
    assert "ultrathink" in prompt.lower() or "Ultrathink" in prompt


def test_team_mode_for_complex(generator, sample_context):
    prompt = generator.generate(
        task_type="feature",
        user_input="Build full stack feature",
        context=sample_context,
        complexity="complex",
    )
    assert "Team" in prompt or "tmux" in prompt


def test_quality_gates_always_present(generator, sample_context):
    prompt = generator.generate(
        task_type="feature",
        user_input="Simple thing",
        context=sample_context,
        complexity="simple",
    )
    assert "Checkpoint" in prompt or "checkpoint" in prompt


def test_reflection_always_present(generator, sample_context):
    prompt = generator.generate(
        task_type="feature",
        user_input="Simple thing",
        context=sample_context,
        complexity="simple",
    )
    assert "Reflexion" in prompt or "reflekt" in prompt.lower()
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_prompt_generator.py -v
```

**Step 3: Create Jinja2 templates**

```jinja2
{# brain/templates/base.j2 #}
# Aufgabe
{{ user_input }}
{% if complexity == "complex" %}

# Denktiefe
Nutze Ultrathink fuer diese komplexe Aufgabe. Denke gruendlich nach bevor du handelst.
{% endif %}
{% if complexity in ["complex", "medium"] %}

# Team-Modus
- Arbeite im tmux Team-Modus
- Nutze TeamCreate fuer parallele Agents wo sinnvoll
- Modell-Strategie: Haiku=Research, Sonnet=Code, Opus=Architektur
- Maximiere Parallelitaet wo moeglich
{% endif %}

{{ context_section }}
{% if error_memories %}

# Fehler-History (NICHT WIEDERHOLEN!)
{% for err in error_memories %}
- {{ err }}
{% endfor %}
{% endif %}

# Qualitaets-Gates (PFLICHT)
- Nach Design-Phase: Checkpoint erstellen
- Nach Core-Implementation: Tests laufen lassen
- Bei Fehler: Root-Cause-Analyse, NICHT quick-fix
- Vor Commit: Tests gruen

# Selbst-Reflexion (AM ENDE DER SESSION)
Beantworte und in Memory speichern:
1. Was wurde erreicht? (konkrete Deliverables)
2. Was lief nicht wie geplant?
3. Welche Fehler wurden gemacht?
4. Was muss die naechste Session wissen?
5. Offene Fragen/Blocker?
```

```jinja2
{# brain/templates/feature.j2 #}
{% extends "base.j2" %}
{% block task_type %}
# Ausfuehrung
- Nutze den Brainstorming-Skill fuer Design-Phase
- Dann Writing-Plans fuer Implementation
- TDD: Tests zuerst, dann Implementation
- Frequent Commits nach jedem logischen Schritt
{% endblock %}
```

```jinja2
{# brain/templates/bugfix.j2 #}
{% extends "base.j2" %}
{% block task_type %}
# Ausfuehrung
- Root-Cause-Analyse ZUERST — kein Quick-Fix
- Reproduziere den Bug mit einem Test
- Fix implementieren
- Verify: Test muss gruen werden
- Regression-Test hinzufuegen
{% endblock %}
```

**Step 4: Implement prompt generator**

```python
# brain/prompt_generator.py
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from brain.context_engine import ProjectContext

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Inline templates as fallback (and primary for simplicity)
_BASE_TEMPLATE = """# Aufgabe
{{ user_input }}
{% if complexity == "complex" %}

# Denktiefe
Nutze Ultrathink fuer diese komplexe Aufgabe. Denke gruendlich nach bevor du handelst.
{% endif %}
{% if complexity in ["complex", "medium"] %}

# Team-Modus
- Arbeite im tmux Team-Modus
- Nutze TeamCreate fuer parallele Agents wo sinnvoll
- Modell-Strategie: Haiku=Research, Sonnet=Code, Opus=Architektur
- Maximiere Parallelitaet wo moeglich
{% endif %}

{{ context_section }}
{% if error_memories %}

# Fehler-History (NICHT WIEDERHOLEN!)
{% for err in error_memories %}
- {{ err }}
{% endfor %}
{% endif %}

{{ task_type_section }}

# Qualitaets-Gates (PFLICHT)
- Nach Design-Phase: Checkpoint erstellen
- Nach Core-Implementation: Tests laufen lassen
- Bei Fehler: Root-Cause-Analyse, NICHT quick-fix
- Vor Commit: Tests gruen

# Selbst-Reflexion (AM ENDE DER SESSION)
Beantworte und in Memory speichern:
1. Was wurde erreicht? (konkrete Deliverables)
2. Was lief nicht wie geplant?
3. Welche Fehler wurden gemacht?
4. Was muss die naechste Session wissen?
5. Offene Fragen/Blocker?
"""

_TASK_TYPE_SECTIONS = {
    "feature": """# Ausfuehrung
- Nutze den Brainstorming-Skill fuer Design-Phase
- Dann Writing-Plans fuer Implementation
- TDD: Tests zuerst, dann Implementation
- Frequent Commits nach jedem logischen Schritt""",
    "bugfix": """# Ausfuehrung — Root-Cause-Analyse
- Root-Cause-Analyse ZUERST — kein Quick-Fix
- Reproduziere den Bug mit einem Test
- Fix implementieren
- Verify: Test muss gruen werden
- Regression-Test hinzufuegen""",
    "refactor": """# Ausfuehrung — Refactoring
- Tests muessen vorher gruen sein
- Refactoring in kleinen Schritten
- Nach jedem Schritt: Tests laufen lassen
- Keine Verhaltensaenderung — nur Struktur""",
    "research": """# Ausfuehrung — Recherche
- Ergebnisse strukturiert zusammenfassen
- Quellen und Referenzen angeben
- Pro/Contra bei Alternativen
- Empfehlung mit Begruendung""",
}


class PromptGenerator:
    def __init__(self) -> None:
        self._env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))

    def generate(
        self,
        task_type: str,
        user_input: str,
        context: ProjectContext,
        complexity: str = "simple",
    ) -> str:
        task_type_section = _TASK_TYPE_SECTIONS.get(task_type, _TASK_TYPE_SECTIONS["feature"])
        from jinja2 import Template
        template = Template(_BASE_TEMPLATE)
        return template.render(
            user_input=user_input,
            complexity=complexity,
            context_section=context.to_prompt_section(),
            error_memories=context.error_memories,
            task_type_section=task_type_section,
        )
```

**Step 5: Run tests**

```bash
pytest tests/test_prompt_generator.py -v
```
Expected: All 6 PASS

**Step 6: Commit**

```bash
git add brain/prompt_generator.py brain/templates/ tests/test_prompt_generator.py
git commit -m "feat: ultra-prompt generator with templates and context injection"
```

---

## Task 9: Task Planner

**Files:**
- Create: `brain/task_planner.py`
- Create: `tests/test_task_planner.py`

**Step 1: Write failing tests**

```python
# tests/test_task_planner.py
import pytest

from brain.task_planner import TaskPlanner
from core.models import TaskStrategy


@pytest.fixture
def planner():
    return TaskPlanner()


def test_simple_task_serial(planner):
    result = planner.analyze("Fix the typo in README")
    assert result.strategy == TaskStrategy.SERIAL
    assert result.complexity == "simple"


def test_medium_task_parallel(planner):
    result = planner.analyze("Build login page with frontend and backend API")
    assert result.strategy == TaskStrategy.PARALLEL
    assert result.complexity == "medium"


def test_complex_task_hierarchical(planner):
    result = planner.analyze(
        "Refactor the entire authentication system: update database schema, "
        "migrate API endpoints, rebuild frontend components, update all tests, "
        "and add monitoring"
    )
    assert result.strategy == TaskStrategy.HIERARCHICAL
    assert result.complexity == "complex"


def test_subtask_generation(planner):
    result = planner.analyze("Build login with frontend form and backend API")
    assert len(result.subtasks) >= 2


def test_task_type_detection_bugfix(planner):
    result = planner.analyze("Fix the crash when user clicks login button")
    assert result.task_type == "bugfix"


def test_task_type_detection_feature(planner):
    result = planner.analyze("Add a dark mode toggle to the settings page")
    assert result.task_type == "feature"
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_task_planner.py -v
```

**Step 3: Implement task planner**

```python
# brain/task_planner.py
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.models import TaskStrategy

_BUGFIX_KEYWORDS = ["fix", "bug", "crash", "error", "broken", "failing", "issue"]
_REFACTOR_KEYWORDS = ["refactor", "restructure", "reorganize", "clean up", "migrate"]
_RESEARCH_KEYWORDS = ["research", "investigate", "explore", "compare", "evaluate"]

_COMPLEXITY_MARKERS_HIGH = [
    "entire", "all", "complete", "full", "system", "architecture",
    "migrate", "rebuild",
]
_COMPLEXITY_MARKERS_MEDIUM = [
    "frontend and backend", "with api", "multiple", "both", "and backend",
    "with tests", "and tests",
]
_PARALLEL_INDICATORS = [
    "frontend and backend", "client and server", "ui and api",
    "with tests",
]


@dataclass
class PlanResult:
    strategy: TaskStrategy
    complexity: str  # simple, medium, complex
    task_type: str  # feature, bugfix, refactor, research
    subtasks: list[str] = field(default_factory=list)
    recommended_skills: list[str] = field(default_factory=list)


class TaskPlanner:
    def analyze(self, user_input: str) -> PlanResult:
        lower = user_input.lower()
        task_type = self._detect_type(lower)
        complexity = self._assess_complexity(lower)
        strategy = self._choose_strategy(lower, complexity)
        subtasks = self._extract_subtasks(lower, strategy)
        skills = self._recommend_skills(task_type)

        return PlanResult(
            strategy=strategy,
            complexity=complexity,
            task_type=task_type,
            subtasks=subtasks,
            recommended_skills=skills,
        )

    def _detect_type(self, text: str) -> str:
        if any(kw in text for kw in _BUGFIX_KEYWORDS):
            return "bugfix"
        if any(kw in text for kw in _REFACTOR_KEYWORDS):
            return "refactor"
        if any(kw in text for kw in _RESEARCH_KEYWORDS):
            return "research"
        return "feature"

    def _assess_complexity(self, text: str) -> str:
        word_count = len(text.split())
        high_markers = sum(1 for m in _COMPLEXITY_MARKERS_HIGH if m in text)
        med_markers = sum(1 for m in _COMPLEXITY_MARKERS_MEDIUM if m in text)

        if high_markers >= 2 or word_count > 40:
            return "complex"
        if med_markers >= 1 or word_count > 15:
            return "medium"
        return "simple"

    def _choose_strategy(self, text: str, complexity: str) -> TaskStrategy:
        if complexity == "complex":
            return TaskStrategy.HIERARCHICAL
        if any(ind in text for ind in _PARALLEL_INDICATORS):
            return TaskStrategy.PARALLEL
        if complexity == "medium":
            return TaskStrategy.PARALLEL
        return TaskStrategy.SERIAL

    def _extract_subtasks(self, text: str, strategy: TaskStrategy) -> list[str]:
        if strategy == TaskStrategy.SERIAL:
            return []
        parts = re.split(r",\s*(?:and\s+)?|(?:\s+and\s+)", text)
        return [p.strip() for p in parts if len(p.strip()) > 5]

    def _recommend_skills(self, task_type: str) -> list[str]:
        mapping = {
            "feature": ["brainstorming", "writing-plans", "test-driven-development"],
            "bugfix": ["systematic-debugging", "root-cause-tracing"],
            "refactor": ["test-driven-development", "writing-plans"],
            "research": [],
        }
        return mapping.get(task_type, [])
```

**Step 4: Run tests**

```bash
pytest tests/test_task_planner.py -v
```
Expected: All 6 PASS

**Step 5: Commit**

```bash
git add brain/task_planner.py tests/test_task_planner.py
git commit -m "feat: task planner with adaptive strategy selection"
```

---

## Task 10: Session Manager

**Files:**
- Create: `execution/session_manager.py`
- Create: `tests/test_session_manager.py`

**Step 1: Write failing tests**

```python
# tests/test_session_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from execution.session_manager import SessionManager
from core.models import Task, Session, SessionStatus


@pytest.fixture
def mock_tmux():
    ctrl = MagicMock()
    ctrl.create_session.return_value = "loop-test:0.0"
    ctrl.capture_output.return_value = "Some claude output"
    ctrl.send_keys = MagicMock()
    ctrl.kill_session = MagicMock()
    return ctrl


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.save_session = AsyncMock()
    db.get_session = AsyncMock(return_value=None)
    return db


@pytest.fixture
def mock_bus():
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def manager(mock_tmux, mock_db, mock_bus):
    return SessionManager(tmux=mock_tmux, db=mock_db, event_bus=mock_bus)


async def test_start_session(manager, mock_tmux, mock_db):
    task = Task(title="Test", raw_input="do something")
    session = await manager.start_session(task, prompt="Hello Claude")
    assert session.status == SessionStatus.RUNNING
    mock_tmux.create_session.assert_called_once()
    mock_tmux.send_keys.assert_called_once()
    mock_db.save_session.assert_called()


async def test_capture_output(manager, mock_tmux):
    session = Session(task_id="t1", tmux_pane="loop-test:0.0", status=SessionStatus.RUNNING)
    output = manager.capture_output(session)
    assert output == "Some claude output"
    mock_tmux.capture_output.assert_called_with("loop-test:0.0")


async def test_send_followup(manager, mock_tmux):
    session = Session(task_id="t1", tmux_pane="loop-test:0.0", status=SessionStatus.RUNNING)
    manager.send_followup(session, "Continue with tests")
    mock_tmux.send_keys.assert_called_with("loop-test:0.0", "Continue with tests")


async def test_end_session(manager, mock_tmux, mock_db):
    session = Session(task_id="t1", tmux_pane="loop-test:0.0", status=SessionStatus.RUNNING)
    await manager.end_session(session)
    assert session.status == SessionStatus.DONE
    mock_db.save_session.assert_called()
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_session_manager.py -v
```

**Step 3: Implement session manager**

```python
# execution/session_manager.py
from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.models import Task, Session, SessionStatus, Event, EventType
from core.event_bus import EventBus
from core.database import Database
from execution.tmux_controller import TmuxController

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(
        self,
        tmux: TmuxController,
        db: Database,
        event_bus: EventBus,
        claude_command: str = "claude --dangerously-skip-permissions",
    ) -> None:
        self._tmux = tmux
        self._db = db
        self._bus = event_bus
        self._claude_cmd = claude_command

    async def start_session(self, task: Task, prompt: str) -> Session:
        session = Session(task_id=task.id)
        pane_id = self._tmux.create_session(f"task-{task.id[:8]}")
        session.tmux_pane = pane_id
        session.prompt_sent = prompt
        session.status = SessionStatus.RUNNING

        # Start claude in the pane
        self._tmux.send_keys(pane_id, f"{self._claude_cmd} '{prompt}'")

        await self._db.save_session(session)
        await self._bus.publish(Event(
            event_type=EventType.SESSION_START,
            payload={"session_id": session.id, "task_id": task.id, "pane": pane_id},
        ))
        logger.info("Session %s started in %s", session.id, pane_id)
        return session

    def capture_output(self, session: Session) -> str:
        return self._tmux.capture_output(session.tmux_pane)

    def send_followup(self, session: Session, text: str) -> None:
        self._tmux.send_keys(session.tmux_pane, text)

    async def end_session(self, session: Session) -> None:
        session.status = SessionStatus.DONE
        session.ended_at = datetime.now(timezone.utc)
        session_name = session.tmux_pane.split(":")[0]
        self._tmux.kill_session(session_name)
        await self._db.save_session(session)
        await self._bus.publish(Event(
            event_type=EventType.SESSION_DONE,
            payload={"session_id": session.id, "task_id": session.task_id},
        ))
        logger.info("Session %s ended", session.id)
```

**Step 4: Run tests**

```bash
pytest tests/test_session_manager.py -v
```
Expected: All 4 PASS

**Step 5: Commit**

```bash
git add execution/session_manager.py tests/test_session_manager.py
git commit -m "feat: session manager for Claude Code lifecycle in tmux"
```

---

## Task 11: Decision Engine

**Files:**
- Create: `execution/decision_engine.py`
- Create: `tests/test_decision_engine.py`

**Step 1: Write failing tests**

```python
# tests/test_decision_engine.py
import pytest

from execution.decision_engine import DecisionEngine, Decision, DecisionType
from execution.output_parser import ParseResult, OutputSignal


@pytest.fixture
def engine():
    return DecisionEngine()


def test_working_continues(engine):
    parse = ParseResult(signals=[OutputSignal.WORKING])
    decision = engine.decide(parse)
    assert decision.type == DecisionType.CONTINUE


def test_error_retries(engine):
    parse = ParseResult(signals=[OutputSignal.ERROR], raw="Error: test failure")
    decision = engine.decide(parse)
    assert decision.type == DecisionType.RETRY


def test_permission_auto_approves(engine):
    parse = ParseResult(signals=[OutputSignal.PERMISSION])
    decision = engine.decide(parse)
    assert decision.type == DecisionType.AUTO_APPROVE


def test_question_escalates(engine):
    parse = ParseResult(signals=[OutputSignal.QUESTION], raw="Which approach?")
    decision = engine.decide(parse)
    assert decision.type == DecisionType.ESCALATE


def test_done_completes(engine):
    parse = ParseResult(signals=[OutputSignal.TASK_DONE])
    decision = engine.decide(parse)
    assert decision.type == DecisionType.COMPLETE


def test_repeated_errors_escalate(engine):
    parse = ParseResult(signals=[OutputSignal.ERROR], raw="Same error again")
    engine.decide(parse)  # First error: retry
    engine.decide(parse)  # Second: retry
    decision = engine.decide(parse)  # Third: escalate
    assert decision.type == DecisionType.ESCALATE
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_decision_engine.py -v
```

**Step 3: Implement decision engine**

```python
# execution/decision_engine.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from execution.output_parser import ParseResult, OutputSignal


class DecisionType(str, Enum):
    CONTINUE = "continue"
    RETRY = "retry"
    AUTO_APPROVE = "auto_approve"
    ESCALATE = "escalate"
    COMPLETE = "complete"


@dataclass
class Decision:
    type: DecisionType
    message: str = ""
    followup_prompt: str = ""


class DecisionEngine:
    def __init__(self, max_retries: int = 2) -> None:
        self._max_retries = max_retries
        self._error_count = 0

    def decide(self, parse_result: ParseResult) -> Decision:
        signals = parse_result.signals

        if OutputSignal.TASK_DONE in signals:
            self._error_count = 0
            return Decision(type=DecisionType.COMPLETE, message="Task completed")

        if OutputSignal.PERMISSION in signals:
            return Decision(
                type=DecisionType.AUTO_APPROVE,
                message="Auto-approving permission",
                followup_prompt="y",
            )

        if OutputSignal.ERROR in signals:
            self._error_count += 1
            if self._error_count > self._max_retries:
                return Decision(
                    type=DecisionType.ESCALATE,
                    message=f"Error repeated {self._error_count} times, escalating",
                )
            return Decision(
                type=DecisionType.RETRY,
                message=f"Error detected (attempt {self._error_count}), retrying",
                followup_prompt="The previous attempt had an error. Please analyze the root cause and try again.",
            )

        if OutputSignal.QUESTION in signals:
            return Decision(
                type=DecisionType.ESCALATE,
                message="Claude is asking a question",
            )

        if OutputSignal.IDLE in signals:
            return Decision(type=DecisionType.CONTINUE, message="Session idle")

        return Decision(type=DecisionType.CONTINUE, message="Working...")

    def reset(self) -> None:
        self._error_count = 0
```

**Step 4: Run tests**

```bash
pytest tests/test_decision_engine.py -v
```
Expected: All 6 PASS

**Step 5: Commit**

```bash
git add execution/decision_engine.py tests/test_decision_engine.py
git commit -m "feat: decision engine with auto-approve, retry, and escalation"
```

---

## Task 12: Telegram Bot (Input)

**Files:**
- Create: `input/telegram_bot.py`
- Create: `tests/test_telegram_bot.py`

**Step 1: Write failing tests**

```python
# tests/test_telegram_bot.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from input.telegram_bot import TelegramInput, parse_command


def test_parse_status_command():
    cmd, args = parse_command("/status")
    assert cmd == "status"
    assert args == ""


def test_parse_stop_command_with_args():
    cmd, args = parse_command("/stop task-123")
    assert cmd == "stop"
    assert args == "task-123"


def test_parse_regular_text():
    cmd, args = parse_command("Build me a login page")
    assert cmd is None
    assert args == "Build me a login page"


def test_parse_approve():
    cmd, args = parse_command("/approve")
    assert cmd == "approve"


def test_allowed_user_check():
    bot = TelegramInput(token="fake", allowed_users=[123, 456])
    assert bot.is_allowed(123) is True
    assert bot.is_allowed(789) is False


def test_empty_allowed_users_allows_all():
    bot = TelegramInput(token="fake", allowed_users=[])
    assert bot.is_allowed(999) is True
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_telegram_bot.py -v
```

**Step 3: Implement telegram bot**

```python
# input/telegram_bot.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Awaitable

from core.event_bus import EventBus
from core.models import Event, EventType

logger = logging.getLogger(__name__)


def parse_command(text: str) -> tuple[str | None, str]:
    """Parse a message into (command, args). Returns (None, text) for non-commands."""
    text = text.strip()
    if text.startswith("/"):
        parts = text[1:].split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        return cmd, args
    return None, text


class TelegramInput:
    def __init__(
        self,
        token: str,
        allowed_users: list[int] | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._token = token
        self._allowed_users = allowed_users or []
        self._bus = event_bus
        self._pending_decisions: dict[str, Callable] = {}

    def is_allowed(self, user_id: int) -> bool:
        if not self._allowed_users:
            return True
        return user_id in self._allowed_users

    async def start(self) -> None:
        """Start the Telegram bot. Requires python-telegram-bot."""
        from telegram.ext import (
            ApplicationBuilder, MessageHandler, CommandHandler, filters,
        )

        app = ApplicationBuilder().token(self._token).build()
        app.add_handler(CommandHandler("status", self._handle_status))
        app.add_handler(CommandHandler("sessions", self._handle_sessions))
        app.add_handler(CommandHandler("stop", self._handle_stop))
        app.add_handler(CommandHandler("pause", self._handle_pause))
        app.add_handler(CommandHandler("resume", self._handle_resume))
        app.add_handler(CommandHandler("approve", self._handle_approve))
        app.add_handler(CommandHandler("reject", self._handle_reject))
        app.add_handler(CommandHandler("logs", self._handle_logs))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        app.add_handler(MessageHandler(filters.VOICE, self._handle_voice))
        app.add_handler(MessageHandler(filters.Document.ALL, self._handle_document))

        logger.info("Telegram bot starting...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        self._app = app

    async def stop(self) -> None:
        if hasattr(self, "_app"):
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def _check_auth(self, update) -> bool:
        user_id = update.effective_user.id
        if not self.is_allowed(user_id):
            await update.message.reply_text("Unauthorized.")
            return False
        return True

    async def _handle_text(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        text = update.message.text
        if self._bus:
            await self._bus.publish(Event(
                event_type=EventType.TASK_NEW,
                payload={"raw_input": text, "source": "telegram", "chat_id": update.effective_chat.id},
            ))
        await update.message.reply_text("Task received. Processing...")

    async def _handle_voice(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        path = f"/tmp/voice_{voice.file_id}.ogg"
        await file.download_to_drive(path)
        if self._bus:
            await self._bus.publish(Event(
                event_type=EventType.TASK_NEW,
                payload={"voice_path": path, "source": "telegram_voice", "chat_id": update.effective_chat.id},
            ))
        await update.message.reply_text("Voice message received. Transcribing...")

    async def _handle_document(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        doc = update.message.document
        file = await context.bot.get_file(doc.file_id)
        path = f"/tmp/doc_{doc.file_id}_{doc.file_name}"
        await file.download_to_drive(path)
        caption = update.message.caption or ""
        if self._bus:
            await self._bus.publish(Event(
                event_type=EventType.TASK_NEW,
                payload={"file_path": path, "caption": caption, "source": "telegram_file",
                         "chat_id": update.effective_chat.id},
            ))
        await update.message.reply_text(f"File '{doc.file_name}' received.")

    async def _handle_status(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        await update.message.reply_text("Fetching status... (TODO: connect to orchestrator)")

    async def _handle_sessions(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        await update.message.reply_text("Fetching sessions... (TODO)")

    async def _handle_stop(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        args = " ".join(context.args) if context.args else ""
        await update.message.reply_text(f"Stopping: {args} (TODO)")

    async def _handle_pause(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        await update.message.reply_text("Pausing all sessions... (TODO)")

    async def _handle_resume(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        await update.message.reply_text("Resuming... (TODO)")

    async def _handle_approve(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        if self._bus:
            await self._bus.publish(Event(
                event_type=EventType.DECISION_MADE,
                payload={"decision": "approve", "source": "telegram"},
            ))
        await update.message.reply_text("Approved.")

    async def _handle_reject(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        reason = " ".join(context.args) if context.args else "No reason given"
        if self._bus:
            await self._bus.publish(Event(
                event_type=EventType.DECISION_MADE,
                payload={"decision": "reject", "reason": reason, "source": "telegram"},
            ))
        await update.message.reply_text(f"Rejected: {reason}")

    async def _handle_logs(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        await update.message.reply_text("Fetching logs... (TODO)")
```

**Step 4: Run tests**

```bash
pytest tests/test_telegram_bot.py -v
```
Expected: All 6 PASS

**Step 5: Commit**

```bash
git add input/telegram_bot.py tests/test_telegram_bot.py
git commit -m "feat: Telegram bot with text/voice/file input and command handling"
```

---

## Task 13: Voice Processor (Whisper)

**Files:**
- Create: `input/voice_processor.py`
- Create: `tests/test_voice_processor.py`

**Step 1: Write failing tests**

```python
# tests/test_voice_processor.py
import pytest
from unittest.mock import patch, AsyncMock

from input.voice_processor import VoiceProcessor


@pytest.fixture
def processor():
    return VoiceProcessor()


async def test_transcribe_returns_string(processor):
    with patch("input.voice_processor.VoiceProcessor._run_whisper") as mock:
        mock.return_value = "Baue mir ein Login Feature"
        result = await processor.transcribe("/tmp/test.ogg")
        assert result == "Baue mir ein Login Feature"


async def test_transcribe_empty_audio(processor):
    with patch("input.voice_processor.VoiceProcessor._run_whisper") as mock:
        mock.return_value = ""
        result = await processor.transcribe("/tmp/empty.ogg")
        assert result == ""
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_voice_processor.py -v
```

**Step 3: Implement voice processor**

```python
# input/voice_processor.py
from __future__ import annotations

import asyncio
import logging
import shutil

logger = logging.getLogger(__name__)


class VoiceProcessor:
    def __init__(self, model: str = "base", language: str = "de") -> None:
        self._model = model
        self._language = language

    async def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text using whisper."""
        return await self._run_whisper(audio_path)

    async def _run_whisper(self, audio_path: str) -> str:
        """Run whisper CLI for transcription. Falls back to whisper Python package."""
        # Try whisper CLI first (whisper.cpp)
        whisper_bin = shutil.which("whisper")
        if whisper_bin:
            proc = await asyncio.create_subprocess_exec(
                whisper_bin, audio_path,
                "--model", self._model,
                "--language", self._language,
                "--output_format", "txt",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode().strip()
            logger.warning("Whisper CLI failed: %s", stderr.decode())

        # Fallback: try Python whisper package
        try:
            import whisper
            model = whisper.load_model(self._model)
            result = model.transcribe(audio_path, language=self._language)
            return result["text"].strip()
        except ImportError:
            logger.error("Neither whisper CLI nor Python whisper package available")
            return ""
        except Exception as e:
            logger.error("Whisper transcription failed: %s", e)
            return ""
```

**Step 4: Run tests**

```bash
pytest tests/test_voice_processor.py -v
```
Expected: All 2 PASS

**Step 5: Commit**

```bash
git add input/voice_processor.py tests/test_voice_processor.py
git commit -m "feat: voice processor with whisper transcription"
```

---

## Task 14: Telegram Reporter (Monitoring)

**Files:**
- Create: `monitoring/telegram_reporter.py`
- Create: `monitoring/event_logger.py`
- Create: `tests/test_telegram_reporter.py`

**Step 1: Write failing tests**

```python
# tests/test_telegram_reporter.py
import pytest
from unittest.mock import AsyncMock

from monitoring.telegram_reporter import TelegramReporter


@pytest.fixture
def reporter():
    bot = AsyncMock()
    return TelegramReporter(bot=bot, chat_id=12345)


async def test_send_task_started(reporter):
    await reporter.send_task_started("Login Feature", "parallel", "~15min")
    reporter._bot.send_message.assert_called_once()
    msg = reporter._bot.send_message.call_args[1]["text"]
    assert "Login Feature" in msg


async def test_send_progress(reporter):
    await reporter.send_progress("Login Feature", "Frontend done, Backend 70%")
    reporter._bot.send_message.assert_called_once()


async def test_send_error(reporter):
    await reporter.send_error("test_auth failed", "Backend Session")
    reporter._bot.send_message.assert_called_once()
    msg = reporter._bot.send_message.call_args[1]["text"]
    assert "test_auth" in msg


async def test_send_decision_request(reporter):
    await reporter.send_decision_request(
        "Auth-Strategie: JWT oder Session-based?",
        options=["JWT", "Session-based"],
    )
    reporter._bot.send_message.assert_called_once()


async def test_send_task_complete(reporter):
    await reporter.send_task_complete("Login Feature", "6 Files, Tests gruen, abc123")
    reporter._bot.send_message.assert_called_once()
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_telegram_reporter.py -v
```

**Step 3: Implement reporter and event logger**

```python
# monitoring/telegram_reporter.py
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class TelegramReporter:
    def __init__(self, bot, chat_id: int) -> None:
        self._bot = bot
        self._chat_id = chat_id

    async def send_task_started(self, title: str, strategy: str, estimate: str = "") -> None:
        est = f", ~{estimate}" if estimate else ""
        await self._send(f"Task gestartet: {title} ({strategy.upper()}{est})")

    async def send_progress(self, title: str, details: str) -> None:
        await self._send(f"Fortschritt: {title}\n{details}")

    async def send_error(self, error: str, session: str = "") -> None:
        ctx = f" in {session}" if session else ""
        await self._send(f"FEHLER{ctx}:\n{error}")

    async def send_decision_request(self, question: str, options: list[str] | None = None) -> None:
        msg = f"Entscheidung noetig:\n{question}"
        if options:
            opts = " | ".join(f"[{o}]" for o in options)
            msg += f"\n\nOptionen: {opts}"
        msg += "\n\n/approve oder /reject <grund>"
        await self._send(msg)

    async def send_task_complete(self, title: str, summary: str) -> None:
        await self._send(f"FERTIG: {title}\n{summary}")

    async def send_reflection(self, summary: str) -> None:
        await self._send(f"Session-Reflexion:\n{summary}")

    async def _send(self, text: str) -> None:
        try:
            await self._bot.send_message(chat_id=self._chat_id, text=text)
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)
```

```python
# monitoring/event_logger.py
from __future__ import annotations

import logging

from core.database import Database
from core.event_bus import EventBus
from core.models import Event

logger = logging.getLogger(__name__)


class EventLogger:
    def __init__(self, db: Database, event_bus: EventBus) -> None:
        self._db = db
        self._bus = event_bus

    def start(self) -> None:
        """Subscribe to all events and log them."""
        self._bus.subscribe_all(self._log_event)

    async def _log_event(self, event: Event) -> None:
        try:
            await self._db.save_event(event)
            logger.debug("Event logged: %s", event.event_type.value)
        except Exception:
            logger.exception("Failed to log event")
```

**Step 4: Run tests**

```bash
pytest tests/test_telegram_reporter.py -v
```
Expected: All 5 PASS

**Step 5: Commit**

```bash
git add monitoring/telegram_reporter.py monitoring/event_logger.py tests/test_telegram_reporter.py
git commit -m "feat: Telegram reporter and event logger for monitoring"
```

---

## Task 15: Web Dashboard

**Files:**
- Create: `monitoring/dashboard.py`
- Create: `monitoring/templates/index.html`
- Create: `tests/test_dashboard.py`

**Step 1: Write failing tests**

```python
# tests/test_dashboard.py
import pytest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from monitoring.dashboard import create_app


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.list_tasks.return_value = []
    db.list_sessions.return_value = []
    db.list_events.return_value = []
    return db


@pytest.fixture
def client(mock_db):
    app = create_app(db=mock_db)
    return TestClient(app)


def test_index_returns_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_api_tasks(client):
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_api_sessions(client):
    response = client.get("/api/sessions")
    assert response.status_code == 200


def test_api_events(client):
    response = client.get("/api/events")
    assert response.status_code == 200
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_dashboard.py -v
```

**Step 3: Implement dashboard**

```python
# monitoring/dashboard.py
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from core.database import Database

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(db: Database) -> FastAPI:
    app = FastAPI(title="Coding Automation Loop")
    connections: list[WebSocket] = []

    @app.get("/", response_class=HTMLResponse)
    async def index():
        html_path = _TEMPLATES_DIR / "index.html"
        return HTMLResponse(content=html_path.read_text())

    @app.get("/api/tasks")
    async def api_tasks():
        tasks = await db.list_tasks()
        return [t.model_dump(mode="json") for t in tasks]

    @app.get("/api/sessions")
    async def api_sessions():
        sessions = await db.list_sessions()
        return [s.model_dump(mode="json") for s in sessions]

    @app.get("/api/events")
    async def api_events():
        events = await db.list_events(limit=100)
        return [e.model_dump(mode="json") for e in events]

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        connections.append(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            connections.remove(ws)

    app.state.connections = connections
    return app


async def broadcast_event(app: FastAPI, data: dict) -> None:
    for ws in list(app.state.connections):
        try:
            await ws.send_json(data)
        except Exception:
            app.state.connections.remove(ws)
```

**Step 4: Create dashboard HTML**

```html
<!-- monitoring/templates/index.html -->
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coding Automation Loop</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@2.0.0"></script>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
    <header class="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <h1 class="text-xl font-bold">Coding Automation Loop</h1>
        <p class="text-gray-400 text-sm">Live Dashboard</p>
    </header>

    <main class="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Active Tasks -->
        <section class="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h2 class="text-lg font-semibold mb-3">Active Tasks</h2>
            <div id="tasks" class="space-y-2">
                <p class="text-gray-500">Loading...</p>
            </div>
        </section>

        <!-- Live Sessions -->
        <section class="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h2 class="text-lg font-semibold mb-3">Live Sessions</h2>
            <div id="sessions" class="space-y-2">
                <p class="text-gray-500">Loading...</p>
            </div>
        </section>

        <!-- Event Log -->
        <section class="bg-gray-800 rounded-lg p-4 border border-gray-700 lg:col-span-2">
            <h2 class="text-lg font-semibold mb-3">Event Log</h2>
            <div id="events" class="space-y-1 font-mono text-sm max-h-96 overflow-y-auto">
                <p class="text-gray-500">Loading...</p>
            </div>
        </section>
    </main>

    <script>
        async function refresh() {
            const [tasks, sessions, events] = await Promise.all([
                fetch('/api/tasks').then(r => r.json()),
                fetch('/api/sessions').then(r => r.json()),
                fetch('/api/events').then(r => r.json()),
            ]);

            document.getElementById('tasks').innerHTML = tasks.length
                ? tasks.map(t => `<div class="bg-gray-700 rounded p-2">
                    <span class="font-medium">${t.title}</span>
                    <span class="text-xs ml-2 px-2 py-0.5 rounded ${
                        t.status === 'running' ? 'bg-blue-600' :
                        t.status === 'done' ? 'bg-green-600' : 'bg-gray-600'
                    }">${t.status}</span>
                    ${t.strategy ? `<span class="text-xs text-gray-400 ml-1">${t.strategy}</span>` : ''}
                  </div>`).join('')
                : '<p class="text-gray-500">No active tasks</p>';

            document.getElementById('sessions').innerHTML = sessions.length
                ? sessions.map(s => `<div class="bg-gray-700 rounded p-2">
                    <span class="font-mono text-sm">${s.tmux_pane}</span>
                    <span class="text-xs ml-2 px-2 py-0.5 rounded ${
                        s.status === 'running' ? 'bg-blue-600' : 'bg-gray-600'
                    }">${s.status}</span>
                  </div>`).join('')
                : '<p class="text-gray-500">No active sessions</p>';

            document.getElementById('events').innerHTML = events.length
                ? events.map(e => `<div class="text-gray-300">
                    <span class="text-gray-500">${new Date(e.timestamp).toLocaleTimeString()}</span>
                    <span class="text-blue-400 ml-2">${e.event_type}</span>
                    <span class="text-gray-400 ml-2">${JSON.stringify(e.payload).slice(0, 80)}</span>
                  </div>`).join('')
                : '<p class="text-gray-500">No events yet</p>';
        }

        // Initial load
        refresh();

        // WebSocket for live updates
        const ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onmessage = () => refresh();
        ws.onclose = () => setTimeout(() => location.reload(), 3000);

        // Fallback polling
        setInterval(refresh, 5000);
    </script>
</body>
</html>
```

**Step 5: Run tests**

```bash
pytest tests/test_dashboard.py -v
```
Expected: All 4 PASS

**Step 6: Commit**

```bash
git add monitoring/dashboard.py monitoring/templates/index.html tests/test_dashboard.py
git commit -m "feat: FastAPI web dashboard with live WebSocket updates"
```

---

## Task 16: Main Orchestrator Loop

**Files:**
- Create: `main.py`
- Create: `tests/test_main.py`

**Step 1: Write failing test**

```python
# tests/test_main.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from main import Orchestrator


async def test_orchestrator_creates_components():
    with patch("main.Database") as MockDB, \
         patch("main.EventBus") as MockBus, \
         patch("main.TmuxController") as MockTmux:
        MockDB.return_value = AsyncMock()
        orch = Orchestrator(config_path=None)
        assert orch is not None


async def test_handle_new_task_event():
    with patch("main.Database") as MockDB, \
         patch("main.EventBus") as MockBus, \
         patch("main.TmuxController") as MockTmux, \
         patch("main.SessionManager") as MockSM, \
         patch("main.PromptGenerator") as MockPG, \
         patch("main.TaskPlanner") as MockTP, \
         patch("main.ContextEngine") as MockCE:

        mock_db = AsyncMock()
        MockDB.return_value = mock_db

        mock_ce = AsyncMock()
        MockCE.return_value = mock_ce

        mock_pg = MagicMock()
        mock_pg.generate.return_value = "Ultra prompt here"
        MockPG.return_value = mock_pg

        mock_tp = MagicMock()
        from core.models import TaskStrategy
        from brain.task_planner import PlanResult
        mock_tp.analyze.return_value = PlanResult(
            strategy=TaskStrategy.SERIAL, complexity="simple",
            task_type="feature",
        )
        MockTP.return_value = mock_tp

        mock_sm = AsyncMock()
        MockSM.return_value = mock_sm

        orch = Orchestrator(config_path=None)
        orch._db = mock_db
        orch._context_engine = mock_ce
        orch._prompt_gen = mock_pg
        orch._planner = mock_tp
        orch._session_mgr = mock_sm

        from core.models import Event, EventType
        event = Event(event_type=EventType.TASK_NEW, payload={"raw_input": "Build login"})
        await orch._handle_new_task(event)

        mock_db.save_task.assert_called()
        mock_sm.start_session.assert_called()
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_main.py -v
```

**Step 3: Implement main orchestrator**

```python
# main.py
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

import yaml

from core.event_bus import EventBus
from core.database import Database
from core.models import Task, TaskStatus, Event, EventType
from brain.context_engine import ContextEngine
from brain.prompt_generator import PromptGenerator
from brain.task_planner import TaskPlanner
from execution.tmux_controller import TmuxController
from execution.session_manager import SessionManager
from execution.output_parser import OutputParser
from execution.decision_engine import DecisionEngine, DecisionType
from monitoring.event_logger import EventLogger

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, config_path: str | None = "config.yaml") -> None:
        self._config = self._load_config(config_path)
        self._bus = EventBus()
        self._db = Database(self._config.get("database", {}).get("path", "data/loop.db"))
        self._tmux = TmuxController(
            session_prefix=self._config.get("tmux", {}).get("session_prefix", "loop")
        )
        self._context_engine = ContextEngine(str(Path.cwd()))
        self._prompt_gen = PromptGenerator()
        self._planner = TaskPlanner()
        self._output_parser = OutputParser()
        self._decision_engine = DecisionEngine()
        self._session_mgr = SessionManager(
            tmux=self._tmux, db=self._db, event_bus=self._bus,
            claude_command=self._config.get("tmux", {}).get("claude_command", "claude --dangerously-skip-permissions"),
        )
        self._event_logger = EventLogger(self._db, self._bus)
        self._running = False
        self._active_sessions: dict[str, asyncio.Task] = {}

    def _load_config(self, path: str | None) -> dict:
        if path and Path(path).exists():
            return yaml.safe_load(Path(path).read_text()) or {}
        return {}

    async def start(self) -> None:
        logger.info("Orchestrator starting...")
        await self._db.init()
        self._event_logger.start()
        self._bus.subscribe(EventType.TASK_NEW, self._handle_new_task)
        self._running = True

        # Start Telegram bot if configured
        token = self._config.get("telegram", {}).get("token", "")
        if token:
            from input.telegram_bot import TelegramInput
            self._telegram = TelegramInput(
                token=token,
                allowed_users=self._config.get("telegram", {}).get("allowed_users", []),
                event_bus=self._bus,
            )
            asyncio.create_task(self._telegram.start())

        # Start dashboard
        dash_cfg = self._config.get("dashboard", {})
        if dash_cfg:
            from monitoring.dashboard import create_app
            import uvicorn
            app = create_app(db=self._db)
            config = uvicorn.Config(
                app, host=dash_cfg.get("host", "0.0.0.0"),
                port=dash_cfg.get("port", 8080), log_level="warning",
            )
            server = uvicorn.Server(config)
            asyncio.create_task(server.serve())

        logger.info("Orchestrator running. Waiting for tasks...")

        # Keep running
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        self._running = False
        self._tmux.cleanup_all()
        await self._db.close()
        logger.info("Orchestrator stopped.")

    async def _handle_new_task(self, event: Event) -> None:
        raw_input = event.payload.get("raw_input", "")
        voice_path = event.payload.get("voice_path")

        # Transcribe voice if needed
        if voice_path:
            from input.voice_processor import VoiceProcessor
            vp = VoiceProcessor()
            raw_input = await vp.transcribe(voice_path)

        if not raw_input:
            logger.warning("Empty task input, skipping")
            return

        # Analyze task
        plan = self._planner.analyze(raw_input)

        # Load context
        context = await self._context_engine.load_context()

        # Generate ultra-prompt
        prompt = self._prompt_gen.generate(
            task_type=plan.task_type,
            user_input=raw_input,
            context=context,
            complexity=plan.complexity,
        )

        # Create task
        task = Task(
            title=raw_input[:80],
            raw_input=raw_input,
            ultra_prompt=prompt,
            strategy=plan.strategy,
            status=TaskStatus.RUNNING,
        )
        await self._db.save_task(task)

        # Start session
        session = await self._session_mgr.start_session(task, prompt)

        # Start monitoring loop for this session
        monitor_task = asyncio.create_task(self._monitor_session(task, session))
        self._active_sessions[session.id] = monitor_task

    async def _monitor_session(self, task: Task, session) -> None:
        """Poll session output and make decisions."""
        poll_ms = self._config.get("orchestrator", {}).get("poll_interval_ms", 500)
        poll_s = poll_ms / 1000
        self._decision_engine.reset()

        while self._running:
            await asyncio.sleep(poll_s)
            output = self._session_mgr.capture_output(session)
            parse_result = self._output_parser.parse(output)
            decision = self._decision_engine.decide(parse_result)

            if decision.type == DecisionType.COMPLETE:
                task.status = TaskStatus.DONE
                await self._db.save_task(task)
                await self._session_mgr.end_session(session)
                await self._bus.publish(Event(
                    event_type=EventType.TASK_COMPLETE,
                    payload={"task_id": task.id, "title": task.title},
                ))
                break

            elif decision.type == DecisionType.AUTO_APPROVE:
                self._session_mgr.send_followup(session, decision.followup_prompt)

            elif decision.type == DecisionType.RETRY:
                self._session_mgr.send_followup(session, decision.followup_prompt)

            elif decision.type == DecisionType.ESCALATE:
                await self._bus.publish(Event(
                    event_type=EventType.DECISION_NEEDED,
                    payload={
                        "task_id": task.id,
                        "message": decision.message,
                        "output": output[-500:],
                    },
                ))
                # Wait for human decision
                # TODO: implement decision waiting mechanism

            # DecisionType.CONTINUE — just keep polling


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    orch = Orchestrator()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(orch.stop()))

    await orch.start()


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 4: Run tests**

```bash
pytest tests/test_main.py -v
```
Expected: All 2 PASS

**Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: main orchestrator loop wiring all components together"
```

---

## Task 17: Multi-Agent Orchestrator

**Files:**
- Create: `execution/multi_agent.py`
- Create: `tests/test_multi_agent.py`

**Step 1: Write failing tests**

```python
# tests/test_multi_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from execution.multi_agent import MultiAgentOrchestrator
from core.models import Task, TaskStrategy, TaskStatus


@pytest.fixture
def mock_session_mgr():
    sm = AsyncMock()
    from core.models import Session, SessionStatus
    sm.start_session.return_value = Session(task_id="t1", tmux_pane="loop:0.0", status=SessionStatus.RUNNING)
    sm.capture_output.return_value = "Task completed successfully"
    return sm


@pytest.fixture
def orchestrator(mock_session_mgr):
    return MultiAgentOrchestrator(session_manager=mock_session_mgr)


async def test_serial_execution(orchestrator, mock_session_mgr):
    task = Task(title="Simple task", strategy=TaskStrategy.SERIAL)
    subtasks = ["Do the thing"]
    prompts = ["Prompt for doing the thing"]
    sessions = await orchestrator.execute(task, subtasks, prompts)
    assert len(sessions) == 1
    mock_session_mgr.start_session.assert_called_once()


async def test_parallel_execution(orchestrator, mock_session_mgr):
    task = Task(title="Parallel task", strategy=TaskStrategy.PARALLEL)
    subtasks = ["Frontend", "Backend"]
    prompts = ["Build frontend", "Build backend"]
    sessions = await orchestrator.execute(task, subtasks, prompts)
    assert len(sessions) == 2
    assert mock_session_mgr.start_session.call_count == 2


async def test_hierarchical_creates_lead(orchestrator, mock_session_mgr):
    task = Task(title="Complex task", strategy=TaskStrategy.HIERARCHICAL)
    subtasks = ["API", "DB", "Tests"]
    prompts = ["Build API", "Setup DB", "Write tests"]
    sessions = await orchestrator.execute(task, subtasks, prompts)
    assert len(sessions) >= 1  # At least the lead session
```

**Step 2: Run tests — should fail**

```bash
pytest tests/test_multi_agent.py -v
```

**Step 3: Implement multi-agent orchestrator**

```python
# execution/multi_agent.py
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from core.models import Task, TaskStrategy, Session

if TYPE_CHECKING:
    from execution.session_manager import SessionManager

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    def __init__(self, session_manager: SessionManager) -> None:
        self._sm = session_manager

    async def execute(
        self,
        task: Task,
        subtasks: list[str],
        prompts: list[str],
    ) -> list[Session]:
        strategy = task.strategy or TaskStrategy.SERIAL

        if strategy == TaskStrategy.SERIAL:
            return await self._execute_serial(task, subtasks, prompts)
        elif strategy == TaskStrategy.PARALLEL:
            return await self._execute_parallel(task, subtasks, prompts)
        elif strategy == TaskStrategy.HIERARCHICAL:
            return await self._execute_hierarchical(task, subtasks, prompts)
        return []

    async def _execute_serial(
        self, task: Task, subtasks: list[str], prompts: list[str],
    ) -> list[Session]:
        sessions = []
        for i, prompt in enumerate(prompts):
            sub = Task(title=subtasks[i] if i < len(subtasks) else f"Step {i+1}", parent_id=task.id)
            session = await self._sm.start_session(sub, prompt)
            sessions.append(session)
        return sessions

    async def _execute_parallel(
        self, task: Task, subtasks: list[str], prompts: list[str],
    ) -> list[Session]:
        async def start_one(i: int, prompt: str) -> Session:
            sub = Task(title=subtasks[i] if i < len(subtasks) else f"Worker {i+1}", parent_id=task.id)
            return await self._sm.start_session(sub, prompt)

        coros = [start_one(i, p) for i, p in enumerate(prompts)]
        sessions = await asyncio.gather(*coros)
        return list(sessions)

    async def _execute_hierarchical(
        self, task: Task, subtasks: list[str], prompts: list[str],
    ) -> list[Session]:
        # Lead session that coordinates
        lead_prompt = (
            f"Du bist der Lead-Agent fuer: {task.title}\n"
            f"Teilaufgaben:\n" + "\n".join(f"- {s}" for s in subtasks) +
            f"\n\nKoordiniere die Ausfuehrung. Starte mit der Planung."
        )
        lead_task = Task(title=f"Lead: {task.title}", parent_id=task.id)
        lead_session = await self._sm.start_session(lead_task, lead_prompt)
        return [lead_session]
```

**Step 4: Run tests**

```bash
pytest tests/test_multi_agent.py -v
```
Expected: All 3 PASS

**Step 5: Commit**

```bash
git add execution/multi_agent.py tests/test_multi_agent.py
git commit -m "feat: multi-agent orchestrator with serial/parallel/hierarchical execution"
```

---

## Task 18: Integration Test & CLI Entry Point

**Files:**
- Create: `input/cli.py`
- Create: `tests/test_integration.py`

**Step 1: Write failing tests**

```python
# tests/test_integration.py
import pytest
from unittest.mock import AsyncMock, patch

from core.event_bus import EventBus
from core.database import Database
from core.models import Event, EventType


async def test_event_flows_through_system(tmp_path):
    """Verify that an event published on the bus reaches a subscriber."""
    bus = EventBus()
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe(EventType.TASK_NEW, handler)

    db = Database(str(tmp_path / "test.db"))
    await db.init()

    from monitoring.event_logger import EventLogger
    logger = EventLogger(db, bus)
    logger.start()

    await bus.publish(Event(event_type=EventType.TASK_NEW, payload={"raw_input": "test"}))
    import asyncio
    await asyncio.sleep(0.1)

    assert len(received) == 1
    events = await db.list_events()
    assert len(events) == 1
    await db.close()
```

**Step 2: Run test — should fail**

```bash
pytest tests/test_integration.py -v
```

**Step 3: Implement CLI**

```python
# input/cli.py
from __future__ import annotations

import asyncio
import sys


async def cli_main():
    """CLI entry point for local task submission."""
    if len(sys.argv) < 2:
        print("Usage: python -m input.cli 'Your task description'")
        print("       python -m input.cli --status")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--status":
        from core.database import Database
        db = Database("data/loop.db")
        await db.init()
        tasks = await db.list_tasks()
        if not tasks:
            print("No tasks.")
        for t in tasks:
            print(f"  [{t.status.value:8}] {t.title}")
        await db.close()
        return

    # Submit task
    from core.event_bus import EventBus
    from core.models import Event, EventType
    from main import Orchestrator

    print(f"Submitting task: {arg}")
    orch = Orchestrator()
    await orch._db.init()
    event = Event(event_type=EventType.TASK_NEW, payload={"raw_input": arg})
    await orch._handle_new_task(event)
    print("Task submitted and session started.")


if __name__ == "__main__":
    asyncio.run(cli_main())
```

**Step 4: Run tests**

```bash
pytest tests/test_integration.py -v
```
Expected: PASS

**Step 5: Final commit**

```bash
git add input/cli.py tests/test_integration.py
git commit -m "feat: CLI entry point and integration test"
```

---

## Task 19: Final Wiring & Smoke Test

**Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```
Expected: All tests PASS

**Step 2: Smoke test — start orchestrator**

```bash
# In one terminal
python main.py

# In another terminal (or via CLI)
python -m input.cli "Create a hello world Python script"
```

Verify:
- tmux session created
- Claude Code started
- Output visible in dashboard (localhost:8080)

**Step 3: Commit any fixes**

```bash
git add -A
git commit -m "chore: final wiring and smoke test fixes"
```

---

## Summary: 19 Tasks, ~45 Commits

| # | Task | Key Files |
|---|---|---|
| 1 | Project Setup | pyproject.toml, config.yaml |
| 2 | Core Models | core/models.py |
| 3 | Event Bus | core/event_bus.py |
| 4 | Database Layer | core/database.py |
| 5 | tmux Controller | execution/tmux_controller.py |
| 6 | Output Parser | execution/output_parser.py |
| 7 | Context Engine | brain/context_engine.py |
| 8 | Prompt Generator | brain/prompt_generator.py |
| 9 | Task Planner | brain/task_planner.py |
| 10 | Session Manager | execution/session_manager.py |
| 11 | Decision Engine | execution/decision_engine.py |
| 12 | Telegram Bot | input/telegram_bot.py |
| 13 | Voice Processor | input/voice_processor.py |
| 14 | Telegram Reporter | monitoring/telegram_reporter.py |
| 15 | Web Dashboard | monitoring/dashboard.py |
| 16 | Main Orchestrator | main.py |
| 17 | Multi-Agent | execution/multi_agent.py |
| 18 | CLI + Integration | input/cli.py |
| 19 | Final Wiring | Smoke test |
