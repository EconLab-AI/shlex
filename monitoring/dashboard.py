from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from core.database import Database

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(db: Database) -> FastAPI:
    app = FastAPI(title="Coding Automation Loop")
    connections: list[WebSocket] = []

    @app.get("/", response_class=HTMLResponse)
    async def index():
        html_path = _TEMPLATES_DIR / "index.html"
        return HTMLResponse(content=html_path.read_text())

    @app.get("/api/tasks")
    async def api_tasks():
        tasks = await db.list_tasks()
        return [t.model_dump(mode="json") for t in tasks]

    @app.get("/api/sessions")
    async def api_sessions():
        sessions = await db.list_sessions()
        return [s.model_dump(mode="json") for s in sessions]

    @app.get("/api/events")
    async def api_events():
        events = await db.list_events(limit=100)
        return [e.model_dump(mode="json") for e in events]

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        connections.append(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            connections.remove(ws)

    app.state.connections = connections
    return app
