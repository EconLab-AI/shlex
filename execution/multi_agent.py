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
        self, task: Task, subtasks: list[str], prompts: list[str],
    ) -> list[Session]:
        strategy = task.strategy or TaskStrategy.SERIAL
        if strategy == TaskStrategy.SERIAL:
            return await self._execute_serial(task, subtasks, prompts)
        elif strategy == TaskStrategy.PARALLEL:
            return await self._execute_parallel(task, subtasks, prompts)
        elif strategy == TaskStrategy.HIERARCHICAL:
            return await self._execute_hierarchical(task, subtasks, prompts)
        return []

    async def _execute_serial(self, task, subtasks, prompts) -> list[Session]:
        sessions = []
        for i, prompt in enumerate(prompts):
            sub = Task(
                title=subtasks[i] if i < len(subtasks) else f"Step {i+1}",
                parent_id=task.id,
            )
            session = await self._sm.start_session(sub, prompt)
            sessions.append(session)
        return sessions

    async def _execute_parallel(self, task, subtasks, prompts) -> list[Session]:
        async def start_one(i, prompt):
            sub = Task(
                title=subtasks[i] if i < len(subtasks) else f"Worker {i+1}",
                parent_id=task.id,
            )
            return await self._sm.start_session(sub, prompt)

        coros = [start_one(i, p) for i, p in enumerate(prompts)]
        return list(await asyncio.gather(*coros))

    async def _execute_hierarchical(self, task, subtasks, prompts) -> list[Session]:
        lead_prompt = (
            f"Du bist der Lead-Agent fuer: {task.title}\n"
            f"Teilaufgaben:\n" + "\n".join(f"- {s}" for s in subtasks) +
            f"\n\nKoordiniere die Ausfuehrung."
        )
        lead_task = Task(title=f"Lead: {task.title}", parent_id=task.id)
        lead_session = await self._sm.start_session(lead_task, lead_prompt)
        return [lead_session]
