# tests/test_integration.py
import pytest
import asyncio

from core.event_bus import EventBus
from core.database import Database
from core.models import Event, EventType
from monitoring.event_logger import EventLogger


async def test_event_flows_through_system(tmp_path):
    """Verify that an event published on the bus reaches the DB via EventLogger."""
    bus = EventBus()
    db = Database(str(tmp_path / "test.db"))
    await db.init()

    logger = EventLogger(db, bus)
    logger.start()

    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe(EventType.TASK_NEW, handler)

    await bus.publish(Event(event_type=EventType.TASK_NEW, payload={"raw_input": "test"}))
    await asyncio.sleep(0.1)

    assert len(received) == 1
    events = await db.list_events()
    assert len(events) == 1
    assert events[0].payload["raw_input"] == "test"
    await db.close()


async def test_full_pipeline_mock(tmp_path):
    """Verify that Orchestrator can process a task end-to-end with mocks."""
    from unittest.mock import AsyncMock, MagicMock
    from main import Orchestrator
    from core.models import Session, SessionStatus, TaskStrategy
    from brain.context_engine import ProjectContext
    from brain.task_planner import PlanResult

    orch = Orchestrator(config_path=None)
    orch._db = AsyncMock()
    orch._context_engine = AsyncMock()
    orch._context_engine.load_context = AsyncMock(return_value=ProjectContext())
    orch._prompt_gen = MagicMock()
    orch._prompt_gen.generate.return_value = "test prompt"
    orch._planner = MagicMock()
    orch._planner.analyze.return_value = PlanResult(
        strategy=TaskStrategy.SERIAL, complexity="simple", task_type="feature",
    )
    orch._session_mgr = AsyncMock()
    orch._session_mgr.start_session = AsyncMock(return_value=Session(
        task_id="t1", tmux_pane="loop:0.0", status=SessionStatus.RUNNING,
    ))

    event = Event(event_type=EventType.TASK_NEW, payload={"raw_input": "Build login"})
    await orch._handle_new_task(event)

    orch._planner.analyze.assert_called_with("Build login")
    orch._prompt_gen.generate.assert_called_once()
    orch._session_mgr.start_session.assert_called_once()
    orch._db.save_task.assert_called()
