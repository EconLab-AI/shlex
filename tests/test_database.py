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
