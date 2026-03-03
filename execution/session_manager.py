# execution/session_manager.py
from __future__ import annotations

import logging
import shlex
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

        self._tmux.send_keys(pane_id, f"{self._claude_cmd} {shlex.quote(prompt)}")

        await self._db.save_session(session)
        await self._bus.publish(Event(
            event_type=EventType.SESSION_START,
            payload={"session_id": session.id, "task_id": task.id, "pane": pane_id},
        ))
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
