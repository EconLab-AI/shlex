# execution/tmux_controller.py
"""Tmux session controller wrapping libtmux for managing Claude Code sessions."""

from __future__ import annotations

import logging

import libtmux
import libtmux.exc

logger = logging.getLogger(__name__)


class TmuxController:
    """Manage tmux sessions for the coding automation loop.

    Creates, controls, and monitors tmux sessions that run Claude Code
    or other shell processes. All sessions are prefixed for easy identification
    and cleanup.
    """

    def __init__(self, session_prefix: str = "loop") -> None:
        self._prefix = session_prefix
        self._server = libtmux.Server()

    def create_session(self, name: str) -> str:
        """Create a tmux session and return pane identifier like 'prefix-name:0.0'.

        If a session with the same name already exists, returns a reference
        to its active pane instead of raising an error.
        """
        session_name = f"{self._prefix}-{name}"
        try:
            session = self._server.new_session(
                session_name=session_name, detach=True
            )
        except libtmux.exc.TmuxSessionExists:
            session = self._server.sessions.get(session_name=session_name)
        window = session.active_window
        pane = window.active_pane
        return f"{session_name}:{window.window_index}.{pane.pane_index}"

    def send_keys(self, pane_id: str, text: str, enter: bool = True) -> None:
        """Send keystrokes to a tmux pane."""
        pane = self._resolve_pane(pane_id)
        pane.send_keys(text, enter=enter)

    def capture_output(self, pane_id: str, lines: int = 200) -> str:
        """Capture visible output from a pane."""
        pane = self._resolve_pane(pane_id)
        return "\n".join(pane.capture_pane())

    def list_sessions(self) -> list[dict]:
        """List all sessions with our prefix."""
        result = []
        for s in self._server.sessions:
            if s.session_name.startswith(self._prefix):
                result.append(
                    {
                        "name": s.session_name,
                        "windows": len(s.windows),
                        "created": s.session_created,
                    }
                )
        return result

    def kill_session(self, session_name: str) -> None:
        """Kill a tmux session by name."""
        try:
            session = self._server.sessions.get(session_name=session_name)
            if session:
                session.kill()
        except Exception:
            logger.warning("Could not kill session %s", session_name)

    def cleanup_all(self) -> None:
        """Kill all sessions with our prefix."""
        for s in list(self._server.sessions):
            if s.session_name.startswith(self._prefix):
                try:
                    s.kill()
                except Exception:
                    pass

    def _resolve_pane(self, pane_id: str) -> libtmux.Pane:
        """Resolve 'session:window.pane' to a libtmux Pane object."""
        parts = pane_id.split(":")
        session_name = parts[0]
        win_pane = parts[1] if len(parts) > 1 else "0.0"
        win_idx, pane_idx = win_pane.split(".")

        session = self._server.sessions.get(session_name=session_name)
        window = session.windows.get(window_index=win_idx)
        pane = window.panes.get(pane_index=pane_idx)
        return pane
