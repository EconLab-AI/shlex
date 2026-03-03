# tests/test_main.py
from unittest.mock import AsyncMock, MagicMock

from main import Orchestrator


async def test_orchestrator_init():
    """Orchestrator can be created without config file."""
    orch = Orchestrator(config_path=None)
    assert orch is not None


async def test_handle_new_task_event(tmp_path):
    """When a TASK_NEW event arrives, orchestrator creates task and starts session."""
    orch = Orchestrator(config_path=None)

    # Mock dependencies
    orch._db = AsyncMock()
    orch._context_engine = AsyncMock()

    from brain.context_engine import ProjectContext
    orch._context_engine.load_context = AsyncMock(return_value=ProjectContext(
        claude_md="test rules",
        git_log="abc123 test",
    ))

    orch._prompt_gen = MagicMock()
    orch._prompt_gen.generate.return_value = "Ultra prompt here"

    from brain.task_planner import PlanResult
    from core.models import TaskStrategy
    orch._planner = MagicMock()
    orch._planner.analyze.return_value = PlanResult(
        strategy=TaskStrategy.SERIAL, complexity="simple", task_type="feature",
    )

    from core.models import Session, SessionStatus
    orch._session_mgr = AsyncMock()
    orch._session_mgr.start_session = AsyncMock(return_value=Session(
        task_id="t1", tmux_pane="loop:0.0", status=SessionStatus.RUNNING,
    ))

    from core.models import Event, EventType
    event = Event(event_type=EventType.TASK_NEW, payload={"raw_input": "Build login"})
    await orch._handle_new_task(event)

    orch._db.save_task.assert_called()
    orch._session_mgr.start_session.assert_called()
