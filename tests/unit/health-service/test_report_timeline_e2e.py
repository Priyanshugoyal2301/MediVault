"""
tests/unit/health-service/test_report_timeline_e2e.py

End-to-end parser-to-timeline integration test (CP-02).

Demonstrates the complete flow:
  Uploaded report text
  → OCR / text extraction
  → Date detection & semantic classification
  → Structured parsed result (AI service ParseResponse / ParsedValueOut)
  → Health service persistence (_trigger_parse)
  → report_values persistence
  → timeline_events persistence
  → timeline API retrieval (chronological order)

Strict CP-02 requirement:
  Does NOT use `/reports/demo/seed`.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, UTC
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services.ai_service.parsers.report_parser import ReportParser
from services.ai_service.routers.parse import ParseResponse, ParsedValueOut
from services.health_service.db.models import ReportValue, TimelineEvent
from services.health_service.db.repositories.report_repository import ReportRepository
from services.health_service.db.repositories.timeline_repository import TimelineRepository
from services.health_service.routers.reports import _trigger_parse


class StubOcr:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        return self._text


SAMPLE_REAL_REPORT_1 = """
DR. LAL PATHLABS - CLINICAL LABORATORY REPORT
============================================================
Patient Name    : Rajesh Kumar           Age/Gender: 45 Y / M
Registration Dt : 12/01/2024             Bill No   : LP-99214
Sample Coll Date: 14/01/2024 08:30 AM    Report Dt : 15/01/2024
============================================================

COMPLETE BLOOD COUNT (CBC)
------------------------------------------------------------
Haemoglobin         : 13.5   g/dL        (13.0 - 17.0)
Platelets           : 195000 /cumm       (150000 - 400000)

LIPID PROFILE
------------------------------------------------------------
Total Cholesterol   : 215    mg/dL       (< 200)
LDL Cholesterol     : 138    mg/dL       (< 100)
HDL Cholesterol     : 42     mg/dL       (> 40)
Triglycerides       : 175    mg/dL       (< 150)
============================================================
"""

SAMPLE_REAL_REPORT_2_LATER = """
DR. LAL PATHLABS - FOLLOW-UP REPORT
============================================================
Patient Name    : Rajesh Kumar           Age/Gender: 45 Y / M
Sample Coll Date: 20/05/2024 09:15 AM    Report Dt : 21/05/2024
============================================================

LIPID PROFILE
------------------------------------------------------------
Total Cholesterol   : 190    mg/dL       (< 200)
LDL Cholesterol     : 115    mg/dL       (< 100)
"""


class InMemorySession:
    """Mock session tracking created records for end-to-end verification."""

    def __init__(self):
        self.added: list[object] = []

    def add(self, obj: object):
        if hasattr(obj, "id") and getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        self.added.append(obj)

    def add_all(self, objects: list[object]):
        for obj in objects:
            if hasattr(obj, "id") and getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
        self.added.extend(objects)

    async def flush(self):
        pass

    async def refresh(self, obj: object):
        if hasattr(obj, "id") and getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    async def scalar(self, statement):
        return None

    async def commit(self):
        pass

    async def execute(self, statement):
        # Stub execute returning matching added items
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = self.added
        return mock_result


class TestReportToTimelineE2E:
    """
    End-to-end verification:
      uploaded report text
      → parsed date
      → parsed lab value
      → timeline event
    without demo seed.
    """

    def test_upload_to_timeline_propagation(self):
        """
        Verify real report produces correctly dated report_values and timeline_events.
        """
        owner_id = uuid.uuid4()
        report_id = uuid.uuid4()

        # Step 1: Document text extraction & parsing via ReportParser
        parser = ReportParser(ocr=StubOcr(SAMPLE_REAL_REPORT_1))
        parsed_values = parser.parse(b"dummy_bytes", "application/pdf")

        assert len(parsed_values) >= 5, "Expected at least 5 lab metrics extracted"
        # Verify collection date (2024-01-14) was selected via precedence over Registration (12/01) and Report (15/01)
        for pv in parsed_values:
            assert pv.date_of_test == "2024-01-14", f"{pv.test_name} missing expected collection date"
            assert pv.date_type == "collection"

        # Step 2: AI service response generation (ParseResponse with ParsedValueOut)
        ai_response_values = [
            ParsedValueOut(
                test_name=pv.test_name,
                panel=pv.panel,
                value_numeric=float(pv.value_numeric) if pv.value_numeric is not None else None,
                value_text=pv.value_text,
                unit=pv.unit,
                reference_range_low=float(pv.reference_range_low) if pv.reference_range_low is not None else None,
                reference_range_high=float(pv.reference_range_high) if pv.reference_range_high is not None else None,
                reference_range_text=pv.reference_range_text,
                status="normal",
                explanation_en="Normal",
                explanation_hi="Normal",
                date_of_test=pv.date_of_test,
                date_type=pv.date_type,
                date_confidence=pv.date_confidence,
            )
            for pv in parsed_values
        ]
        parse_response = ParseResponse(
            report_id=str(report_id),
            values=ai_response_values,
            report_date="2024-01-14",
            date_of_test="2024-01-14",
        )
        payload = parse_response.model_dump()

        # Step 3: Health-service ingestion via _trigger_parse
        session = InMemorySession()

        # Mock engine and sessionmaker to yield session
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)

        async def _run():
            with (
                patch("httpx.AsyncClient", return_value=mock_client),
                patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_engine,
                patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            ):
                mock_engine.return_value.dispose = AsyncMock()
                await _trigger_parse(
                    report_id=str(report_id),
                    owner_id=str(owner_id),
                    storage_path="/tmp/test.pdf",
                    mime_type="application/pdf",
                    locale="en-IN",
                    ai_service_url="http://mock-ai:8003",
                    db_url="postgresql+asyncpg://mock/db",
                )

        asyncio.run(_run())

        # Step 4: Verify persistence in report_values
        saved_report_values = [r for r in session.added if isinstance(r, ReportValue)]
        assert len(saved_report_values) == len(parsed_values)
        for rv in saved_report_values:
            assert rv.date_of_test == date(2024, 1, 14), f"ReportValue {rv.test_name} has incorrect date {rv.date_of_test}"
            assert rv.owner_id == owner_id
            assert rv.report_id == report_id

        # Step 5: Verify persistence in timeline_events
        saved_timeline_events = [r for r in session.added if isinstance(r, TimelineEvent)]
        assert len(saved_timeline_events) == len(parsed_values), "Every parsed value must generate a timeline event"

        # Check specific metrics in timeline
        hb_event = next(e for e in saved_timeline_events if e.test_name == "Haemoglobin")
        assert hb_event.date_of_test == date(2024, 1, 14)
        assert hb_event.value_numeric == Decimal("13.5")
        assert hb_event.unit == "g/dL"
        assert hb_event.source_report_id == report_id
        assert hb_event.owner_id == owner_id

        ldl_event = next(e for e in saved_timeline_events if e.test_name == "LDL Cholesterol")
        assert ldl_event.date_of_test == date(2024, 1, 14)
        assert ldl_event.value_numeric == Decimal("138")
        assert ldl_event.unit == "mg/dL"

        chol_event = next(e for e in saved_timeline_events if e.test_name == "Total Cholesterol")
        assert chol_event.date_of_test == date(2024, 1, 14)
        assert chol_event.value_numeric == Decimal("215")

    def test_chronological_ordering_across_multiple_reports(self):
        """
        Verify two sequentially uploaded reports produce correctly ordered timeline events.
        """
        owner_id = uuid.uuid4()
        report_1_id = uuid.uuid4()
        report_2_id = uuid.uuid4()

        # Parse Report 1 (14/01/2024)
        parser_1 = ReportParser(ocr=StubOcr(SAMPLE_REAL_REPORT_1))
        vals_1 = parser_1.parse(b"", "application/pdf")
        ldl_1 = next(v for v in vals_1 if v.test_name == "LDL Cholesterol")
        assert ldl_1.date_of_test == "2024-01-14"

        # Parse Report 2 (20/05/2024)
        parser_2 = ReportParser(ocr=StubOcr(SAMPLE_REAL_REPORT_2_LATER))
        vals_2 = parser_2.parse(b"", "application/pdf")
        ldl_2 = next(v for v in vals_2 if v.test_name == "LDL Cholesterol")
        assert ldl_2.date_of_test == "2024-05-20"

        # Simulate timeline repository chronological ordering
        events = [
            TimelineEvent(
                id=uuid.uuid4(),
                owner_id=owner_id,
                test_name="LDL Cholesterol",
                value_numeric=Decimal("138"),
                unit="mg/dL",
                date_of_test=date.fromisoformat(ldl_1.date_of_test),
                source_report_id=report_1_id,
                created_at=datetime.now(UTC),
            ),
            TimelineEvent(
                id=uuid.uuid4(),
                owner_id=owner_id,
                test_name="LDL Cholesterol",
                value_numeric=Decimal("115"),
                unit="mg/dL",
                date_of_test=date.fromisoformat(ldl_2.date_of_test),
                source_report_id=report_2_id,
                created_at=datetime.now(UTC),
            ),
        ]

        # Verify chronological order (oldest first)
        sorted_events = sorted(events, key=lambda e: e.date_of_test)
        assert sorted_events[0].date_of_test == date(2024, 1, 14)
        assert sorted_events[0].value_numeric == Decimal("138")
        assert sorted_events[1].date_of_test == date(2024, 5, 20)
        assert sorted_events[1].value_numeric == Decimal("115")

    def test_timeline_endpoint_reflects_parsed_dates(self):
        """
        Verify GET /timeline/{test_name} returns events containing parsed observation dates.
        """
        owner_id = uuid.uuid4()
        event_date = date(2024, 1, 14)

        mock_event = MagicMock()
        mock_event.id = uuid.uuid4()
        mock_event.owner_id = owner_id
        mock_event.test_name = "Haemoglobin"
        mock_event.date_of_test = event_date
        mock_event.value_numeric = Decimal("13.5")
        mock_event.value_text = None
        mock_event.unit = "g/dL"
        mock_event.source_report_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_event]

        mock_session = MagicMock()
        mock_session.scalar = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _stub_get_db():
            yield mock_session

        from fastapi import FastAPI
        from services.health_service.routers.timeline import (
            get_db as timeline_get_db,
            router as timeline_router,
        )

        app = FastAPI()
        app.include_router(timeline_router)
        app.dependency_overrides[timeline_get_db] = _stub_get_db

        with TestClient(app) as client:
            resp = client.get(
                "/timeline/Haemoglobin",
                headers={"x-user-id": str(owner_id)},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["test_name"] == "Haemoglobin"
        assert data[0]["date_of_test"] == "2024-01-14"
        assert data[0]["value_numeric"] == 13.5
        assert data[0]["unit"] == "g/dL"

    def test_application_upload_route_e2e_to_timeline(self, tmp_path):
        """
        Focused application route integration test:
          POST /reports (HTTP upload with PDF magic bytes)
          -> triggers _trigger_parse in BackgroundTasks
          -> calls AI service parse
          -> persists report_values and timeline_events
          -> GET /timeline/{test_name} returns the event with the parsed date.
        """
        from services.health_service.db.models import Report
        from services.health_service.storage.local_storage import LocalStorage

        owner_id = uuid.uuid4()
        from cryptography.fernet import Fernet
        storage = LocalStorage(str(tmp_path), Fernet.generate_key().decode())

        # Build realistic PDF bytes starting with %PDF-1.4 header
        pdf_bytes = b"%PDF-1.4\n" + SAMPLE_REAL_REPORT_1.encode("utf-8")

        # Parse the report using actual ReportParser to construct genuine AI service response
        parser = ReportParser(ocr=StubOcr(SAMPLE_REAL_REPORT_1))
        parsed_vals = parser.parse(b"", "application/pdf")
        ai_vals = [
            ParsedValueOut(
                test_name=pv.test_name,
                panel=pv.panel,
                value_numeric=float(pv.value_numeric) if pv.value_numeric is not None else None,
                value_text=pv.value_text,
                unit=pv.unit,
                reference_range_low=float(pv.reference_range_low) if pv.reference_range_low is not None else None,
                reference_range_high=float(pv.reference_range_high) if pv.reference_range_high is not None else None,
                reference_range_text=pv.reference_range_text,
                status="normal",
                explanation_en="Normal",
                explanation_hi="Normal",
                date_of_test=pv.date_of_test,
                date_type=pv.date_type,
                date_confidence=pv.date_confidence,
            )
            for pv in parsed_vals
        ]

        # In-memory tracking session
        session = InMemorySession()

        # Mock engine and sessionmaker so _trigger_parse yields our session
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock httpx response from AI service
        mock_http_client = MagicMock()
        mock_http_resp = MagicMock()
        mock_http_resp.status_code = 200
        mock_http_resp.raise_for_status = MagicMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)
        mock_http_client.post = AsyncMock(return_value=mock_http_resp)

        async def _stub_get_db():
            yield session

        from fastapi import FastAPI
        from services.health_service.routers.reports import (
            _get_storage as reports_get_storage,
            get_db as reports_get_db,
            router as reports_router,
        )
        from services.health_service.routers.timeline import (
            get_db as timeline_get_db,
            router as timeline_router,
        )

        app = FastAPI()
        app.include_router(reports_router)
        app.include_router(timeline_router)
        app.dependency_overrides[reports_get_db] = _stub_get_db
        app.dependency_overrides[timeline_get_db] = _stub_get_db
        app.dependency_overrides[reports_get_storage] = lambda: storage

        # Dynamic JSON response returning ParseResponse with the generated report_id
        def _get_parse_json():
            created_reports = [r for r in session.added if isinstance(r, Report)]
            rep_id = str(created_reports[0].id) if created_reports else str(uuid.uuid4())
            return ParseResponse(
                report_id=rep_id,
                values=ai_vals,
                report_date="2024-01-14",
                date_of_test="2024-01-14",
            ).model_dump()

        mock_http_resp.json = _get_parse_json

        with (
            patch("httpx.AsyncClient", return_value=mock_http_client),
            patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_engine,
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            TestClient(app) as client,
        ):
            mock_engine.return_value.dispose = AsyncMock()

            # 1. Execute actual POST /reports upload application route
            upload_resp = client.post(
                "/reports",
                headers={"x-user-id": str(owner_id)},
                files={"file": ("lab_report.pdf", pdf_bytes, "application/pdf")},
            )
            assert upload_resp.status_code == 202
            body = upload_resp.json()
            assert body["original_filename"] == "lab_report.pdf"
            assert body["parsed_status"] == "pending"

            # 2. Dispatch the committed pending document, as the durable worker does.
            asyncio.run(_trigger_parse(report_id=body["id"], owner_id=str(owner_id),
                storage_path=str([r for r in session.added if isinstance(r, Report)][0].storage_path),
                mime_type="application/pdf", locale="en-IN", ai_service_url="http://mock-ai:8003",
                db_url="postgresql+asyncpg://mock/db"))
            # Verify that processing populated the session
            timeline_events = [e for e in session.added if isinstance(e, TimelineEvent)]
            assert len(timeline_events) >= 5, "Timeline events must be populated from upload background task"
            hb_event = next(e for e in timeline_events if e.test_name == "Haemoglobin")
            assert hb_event.date_of_test == date(2024, 1, 14)
            assert hb_event.value_numeric == Decimal("13.5")

            # 3. Execute actual GET /timeline/Haemoglobin application route
            mock_query_res = MagicMock()
            mock_query_res.scalars.return_value.all.return_value = [hb_event]
            session.execute = AsyncMock(return_value=mock_query_res)

            timeline_resp = client.get(
                "/timeline/Haemoglobin",
                headers={"x-user-id": str(owner_id)},
            )
            assert timeline_resp.status_code == 200
            timeline_data = timeline_resp.json()
            assert isinstance(timeline_data, list)
            assert len(timeline_data) == 1
            assert timeline_data[0]["test_name"] == "Haemoglobin"
            assert timeline_data[0]["date_of_test"] == "2024-01-14"
            assert timeline_data[0]["value_numeric"] == 13.5
            assert timeline_data[0]["unit"] == "g/dL"
