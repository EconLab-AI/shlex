# tests/test_session_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock

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
