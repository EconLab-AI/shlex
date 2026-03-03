# tests/test_tmux_controller.py
import pytest
import time

from execution.tmux_controller import TmuxController

pytestmark = pytest.mark.skipif(
    not __import__("shutil").which("tmux"), reason="tmux not installed"
)


@pytest.fixture
def ctrl():
    """Real tmux controller with test prefix."""
    c = TmuxController(session_prefix="test-loop")
    yield c
    c.cleanup_all()


def test_create_session(ctrl):
    pane = ctrl.create_session("worker-1")
    assert pane is not None
    assert "test-loop" in pane


def test_send_keys_and_capture(ctrl):
    pane = ctrl.create_session("echo-test")
    ctrl.send_keys(pane, "echo HELLO_LOOP")
    time.sleep(0.5)
    output = ctrl.capture_output(pane)
    assert "HELLO_LOOP" in output


def test_list_sessions(ctrl):
    ctrl.create_session("list-1")
    ctrl.create_session("list-2")
    sessions = ctrl.list_sessions()
    assert len(sessions) >= 2


def test_kill_session(ctrl):
    pane = ctrl.create_session("kill-me")
    session_name = pane.split(":")[0]
    ctrl.kill_session(session_name)
    sessions = ctrl.list_sessions()
    assert session_name not in [s["name"] for s in sessions]
