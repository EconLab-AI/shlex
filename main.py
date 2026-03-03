# main.py
from __future__ import annotations

import asyncio
import logging
import signal
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
            claude_command=self._config.get("tmux", {}).get(
                "claude_command", "claude --dangerously-skip-permissions"
            ),
        )
        self._event_logger = EventLogger(self._db, self._bus)
        self._running = False

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

        # Start Telegram if configured
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
        if dash_cfg.get("host"):
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

        if voice_path:
            from input.voice_processor import VoiceProcessor
            vp = VoiceProcessor()
            raw_input = await vp.transcribe(voice_path)

        if not raw_input:
            return

        plan = self._planner.analyze(raw_input)
        context = await self._context_engine.load_context()

        prompt = self._prompt_gen.generate(
            task_type=plan.task_type,
            user_input=raw_input,
            context=context,
            complexity=plan.complexity,
        )

        task = Task(
            title=raw_input[:80],
            raw_input=raw_input,
            ultra_prompt=prompt,
            strategy=plan.strategy,
            status=TaskStatus.RUNNING,
        )
        await self._db.save_task(task)

        session = await self._session_mgr.start_session(task, prompt)

        asyncio.create_task(self._monitor_session(task, session))

    async def _monitor_session(self, task: Task, session) -> None:
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


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    orch = Orchestrator()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(orch.stop()))
    await orch.start()


if __name__ == "__main__":
    asyncio.run(main())
