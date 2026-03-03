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
