"""
tests/unit/health-service/test_qa.py

Tests for the health-service Q&A proxy endpoint.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _stub_env_and_db(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "testpassword")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_DB", "medivault_test")
    monkeypatch.setenv("AI_SERVICE_URL", "http://127.0.0.1:9")  # force local fallback

    if "asyncpg" not in sys.modules:
        monkeypatch.setitem(sys.modules, "asyncpg", types.ModuleType("asyncpg"))

    fake_embedder = types.ModuleType("services.ai_service.rag.embedder")
    fake_embedder.embed_text = lambda text: [0.1] * 384
    fake_embedder.embed_batch = lambda texts: [[0.1] * 384 for _ in texts]
    fake_embedder.get_embedding_dim = lambda: 384
    monkeypatch.setitem(sys.modules, "services.ai_service.rag.embedder", fake_embedder)


@pytest.fixture
def client(_stub_env_and_db):
    from fastapi.testclient import TestClient
    from services.health_service.main import app
    from services.health_service.db.session import get_db

    async def _fake_db():
        session = MagicMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result)
        yield session

    app.dependency_overrides[get_db] = _fake_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


VALID_HEADERS = {"X-User-Id": "00000000-0000-0000-0000-000000000001"}


class TestQAEndpoint:
    def test_qa_returns_200_with_valid_request(self, client):
        response = client.post(
            "/qa",
            json={"question": "What is haemoglobin?", "locale": "en-IN"},
            headers=VALID_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "answer" in data
        assert "answer_hi" in data
        assert "citations" in data
        assert "safety_triggered" in data

    def test_qa_missing_header_returns_401_or_422(self, client):
        response = client.post(
            "/qa",
            json={"question": "What is cholesterol?"},
        )
        assert response.status_code in (401, 422)

    def test_qa_safety_trigger_through_proxy(self, client):
        response = client.post(
            "/qa",
            json={"question": "I have chest pain and breathing difficulty"},
            headers=VALID_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["safety_triggered"] is True
        assert "emergency" in data["answer"].lower() or "112" in data["answer"]

    def test_qa_empty_question_returns_422(self, client):
        response = client.post(
            "/qa",
            json={"question": "", "locale": "en-IN"},
            headers=VALID_HEADERS,
        )
        assert response.status_code == 422

    def test_qa_hindi_locale_accepted(self, client):
        response = client.post(
            "/qa",
            json={"question": "Haemoglobin kya hota hai?", "locale": "hi-IN"},
            headers=VALID_HEADERS,
        )
        assert response.status_code == 200

    def test_qa_session_id_preserved(self, client):
        session_id = "test-session-123"
        response = client.post(
            "/qa",
            json={"question": "What is TSH?", "session_id": session_id},
            headers=VALID_HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

    def test_qa_auto_generates_session_id(self, client):
        response = client.post(
            "/qa",
            json={"question": "What is cholesterol?"},
            headers=VALID_HEADERS,
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        assert session_id is not None
        assert len(session_id) > 0
