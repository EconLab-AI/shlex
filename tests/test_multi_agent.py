# tests/test_multi_agent.py
import pytest
from unittest.mock import AsyncMock

from execution.multi_agent import MultiAgentOrchestrator
from core.models import Task, TaskStrategy, Session, SessionStatus


@pytest.fixture
def mock_session_mgr():
    sm = AsyncMock()
    sm.start_session = AsyncMock(return_value=Session(
        task_id="t1", tmux_pane="loop:0.0", status=SessionStatus.RUNNING
    ))
    return sm


@pytest.fixture
def orchestrator(mock_session_mgr):
    return MultiAgentOrchestrator(session_manager=mock_session_mgr)


async def test_serial_execution(orchestrator, mock_session_mgr):
    task = Task(title="Simple task", strategy=TaskStrategy.SERIAL)
    sessions = await orchestrator.execute(task, ["Do thing"], ["Prompt"])
    assert len(sessions) == 1
    mock_session_mgr.start_session.assert_called_once()


async def test_parallel_execution(orchestrator, mock_session_mgr):
    task = Task(title="Parallel task", strategy=TaskStrategy.PARALLEL)
    sessions = await orchestrator.execute(task, ["Frontend", "Backend"], ["Build FE", "Build BE"])
    assert len(sessions) == 2
    assert mock_session_mgr.start_session.call_count == 2


async def test_hierarchical_creates_lead(orchestrator, mock_session_mgr):
    task = Task(title="Complex task", strategy=TaskStrategy.HIERARCHICAL)
    sessions = await orchestrator.execute(task, ["API", "DB", "Tests"], ["a", "b", "c"])
    assert len(sessions) >= 1
