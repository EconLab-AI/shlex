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
    from datetime import datetime
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
