"""
tests/unit/health-service/test_timeline.py

Unit tests for TimelineRepository and GET /timeline endpoints.

Tests:
  1. bulk_create_events creates events with correct field values.
  2. list_events_for_test returns chronological order.
  3. get_timeline_summary groups by test_name with latest values.
  4. Cross-user scoping: User A cannot see User B's timeline events.
  5. Events without date_of_test are silently skipped by bulk_create_events.
  6. GET /timeline/{test_name} raises 404 when no events exist.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, UTC
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers to build in-memory mock objects
# ---------------------------------------------------------------------------

def _make_event(
    owner_id: uuid.UUID,
    test_name: str,
    date_of_test: date,
    value_numeric: float | None = None,
    unit: str | None = None,
) -> MagicMock:
    """Return a mock TimelineEvent ORM object."""
    m = MagicMock()
    m.id = uuid.uuid4()
    m.owner_id = owner_id
    m.test_name = test_name
    m.date_of_test = date_of_test
    m.value_numeric = Decimal(str(value_numeric)) if value_numeric is not None else None
    m.value_text = None
    m.unit = unit
    m.source_report_id = uuid.uuid4()
    m.created_at = datetime.now(UTC)
    return m


# ---------------------------------------------------------------------------
# TimelineRepository unit tests (no DB — mocked session)
# ---------------------------------------------------------------------------

class TestTimelineRepository:
    """Direct repository tests with a mocked AsyncSession."""

    def test_bulk_create_events_skips_missing_dates(self):
        """Events without date_of_test must be silently skipped."""
        async def _run():
            from services.health_service.db.repositories.timeline_repository import (  # type: ignore
                TimelineRepository,
            )

            session = MagicMock()
            session.add_all = MagicMock()
            session.flush = AsyncMock()
            repo = TimelineRepository(session)

            events_with_missing_date = [
                {"test_name": "Haemoglobin", "date_of_test": date(2025, 1, 1), "value_numeric": Decimal("12.5")},
                {"test_name": "WBC", "date_of_test": None, "value_numeric": Decimal("6.0")},  # no date → skip
            ]

            owner_id = uuid.uuid4()
            report_id = uuid.uuid4()
            created = await repo.bulk_create_events(owner_id, report_id, events_with_missing_date)

            assert len(created) == 1
            assert created[0].test_name == "Haemoglobin"

        asyncio.run(_run())

    def test_list_events_for_test_returns_chronological_order(self):
        """list_events_for_test should return events oldest-first."""
        async def _run():
            from services.health_service.db.repositories.timeline_repository import (  # type: ignore
                TimelineRepository,
            )

            owner_id = uuid.uuid4()
            event_old = _make_event(owner_id, "Haemoglobin", date(2024, 6, 1), 12.0)
            event_new = _make_event(owner_id, "Haemoglobin", date(2025, 1, 1), 13.5)

            result_mock = MagicMock()
            result_mock.scalars.return_value.all.return_value = [event_old, event_new]

            session = MagicMock()
            session.execute = AsyncMock(return_value=result_mock)
            repo = TimelineRepository(session)

            events = await repo.list_events_for_test(owner_id, "Haemoglobin")
            assert len(events) == 2
            assert events[0].date_of_test < events[1].date_of_test

        asyncio.run(_run())

    def test_get_timeline_summary_groups_by_test_name(self):
        """get_timeline_summary should return one entry per distinct test_name."""
        async def _run():
            from services.health_service.db.repositories.timeline_repository import (  # type: ignore
                TimelineRepository,
            )

            owner_id = uuid.uuid4()
            events = [
                _make_event(owner_id, "Haemoglobin", date(2025, 1, 1), 13.5, "g/dL"),
                _make_event(owner_id, "Haemoglobin", date(2024, 6, 1), 12.0, "g/dL"),
                _make_event(owner_id, "WBC", date(2025, 1, 1), 7.5, "10³/µL"),
            ]

            result_mock = MagicMock()
            result_mock.scalars.return_value.all.return_value = events

            session = MagicMock()
            session.execute = AsyncMock(return_value=result_mock)
            repo = TimelineRepository(session)

            summary = await repo.get_timeline_summary(owner_id)
            test_names = {s["test_name"] for s in summary}
            assert "Haemoglobin" in test_names
            assert "WBC" in test_names
            assert len(test_names) == 2

            hb_entry = next(s for s in summary if s["test_name"] == "Haemoglobin")
            assert hb_entry["data_point_count"] == 2

        asyncio.run(_run())

    def test_cross_user_scoping_list(self):
        """
        User A's query MUST NOT return User B's events.
        Verified by checking owner_id appears in the compiled WHERE clause.
        """
        async def _run():
            from services.health_service.db.repositories.timeline_repository import (  # type: ignore
                TimelineRepository,
            )

            user_a = uuid.uuid4()

            empty_result = MagicMock()
            empty_result.scalars.return_value.all.return_value = []

            session = MagicMock()
            session.execute = AsyncMock(return_value=empty_result)
            repo = TimelineRepository(session)

            events_for_a = await repo.list_events_for_test(user_a, "Haemoglobin")
            assert events_for_a == []

            session.execute.assert_called_once()
            call_args = session.execute.call_args[0][0]
            compiled = str(call_args.compile())
            assert "owner_id" in compiled

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Router endpoint tests (TestClient with dependency overrides)
# ---------------------------------------------------------------------------

# Stub get_db so the session module never calls create_async_engine (asyncpg absent)
async def _stub_get_db():
    session = MagicMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)
    yield session


@pytest.fixture
def timeline_app(monkeypatch):
    """Provide a minimal FastAPI test app with timeline router mounted.

    Stubs the DB session and Settings so no real DB / env vars are required.
    """
    import sys
    import types

    # Stub packages.shared_utils (already handled by conftest finder, but guard here too)
    # Stub the db.session module so create_async_engine is never called
    stub_session = types.ModuleType("stub_session")
    stub_session.get_db = _stub_get_db  # type: ignore

    # Register stubs under the names the router will import
    # (health-service uses relative imports, so we patch the resolved absolute names)
    monkeypatch.setitem(sys.modules, "services.health_service.db.session", stub_session)

    # Minimal env vars for Settings (may be needed for other transitive imports)
    monkeypatch.setenv("POSTGRES_PASSWORD", "testpw")
    monkeypatch.setenv("JWT_SECRET_KEY", "testsecret")
    monkeypatch.setenv("AI_SERVICE_URL", "http://localhost:8001")

    from fastapi import FastAPI
    from services.health_service.routers.timeline import get_db as timeline_get_db, router as timeline_router  # type: ignore

    app = FastAPI()
    app.include_router(timeline_router)
    app.dependency_overrides[timeline_get_db] = _stub_get_db
    return app


@pytest.fixture
def timeline_client(timeline_app):
    return TestClient(timeline_app)


class TestTimelineEndpoints:
    def test_get_timeline_returns_200_with_valid_header(self, timeline_app):
        owner_id = uuid.uuid4()
        with TestClient(timeline_app) as client:
            resp = client.get("/timeline", headers={"x-user-id": str(owner_id)})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_timeline_missing_header_returns_401(self, timeline_app):
        with TestClient(timeline_app) as client:
            resp = client.get("/timeline")
        assert resp.status_code == 401

    def test_get_test_history_not_found_returns_404(self, timeline_app):
        owner_id = uuid.uuid4()
        with TestClient(timeline_app) as client:
            resp = client.get(
                "/timeline/NonExistentTest",
                headers={"x-user-id": str(owner_id)},
            )
        assert resp.status_code == 404
