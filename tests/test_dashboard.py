# tests/test_dashboard.py
import pytest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from monitoring.dashboard import create_app


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.list_tasks.return_value = []
    db.list_sessions.return_value = []
    db.list_events.return_value = []
    return db


@pytest.fixture
def client(mock_db):
    app = create_app(db=mock_db)
    return TestClient(app)


def test_index_returns_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_api_tasks(client):
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_api_sessions(client):
    response = client.get("/api/sessions")
    assert response.status_code == 200


def test_api_events(client):
    response = client.get("/api/events")
    assert response.status_code == 200
