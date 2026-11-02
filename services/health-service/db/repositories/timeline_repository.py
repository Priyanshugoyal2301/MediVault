"""
health-service/db/repositories/timeline_repository.py

TimelineRepository — stores and retrieves per-user health metric history.

Subclasses ScopedRepository: every query REQUIRES owner_id (query-layer
privacy enforcement per 02_ARCHITECTURE.md §4).
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..base_repository import ScopedRepository
from ..models import Report, TimelineEvent


class TimelineRepository(ScopedRepository[TimelineEvent]):
    model = TimelineEvent

    def __init__(self, session, scope=None):
        super().__init__(session)
        self.scope = scope

    def predicate(self, owner_id):
        from .report_repository import ReportRepository
        reports = select(Report.id).where(ReportRepository(self._session, self.scope).predicate(owner_id))
        return TimelineEvent.source_report_id.in_(reports)

    async def create_event(
        self,
        owner_id: uuid.UUID,
        source_report_id: uuid.UUID,
        test_name: str,
        date_of_test: date,
        value_numeric: Decimal | None = None,
        value_text: str | None = None,
        unit: str | None = None,
        analyte_canonical: str | None = None,
        concept_id: str | None = None,
        loinc_code: str | None = None,
        reference_range_low: Decimal | None = None,
        reference_range_high: Decimal | None = None,
        flag: str | None = None,
        date_type: str | None = None,
        date_confidence: str | None = None,
        source_provenance: str | None = None,
    ) -> TimelineEvent:
        """
        Insert a single timeline event for a given metric+date.
        Always stamps owner_id from the caller — never from request body.

        CP-04: canonical clinical concept fields (analyte_canonical, concept_id,
        loinc_code, reference ranges, flag, date_type, date_confidence,
        source_provenance) are accepted and persisted when provided.
        """
        return await self.create(
            owner_id=owner_id,
            source_report_id=source_report_id,
            test_name=test_name,
            date_of_test=date_of_test,
            value_numeric=value_numeric,
            value_text=value_text,
            unit=unit,
            analyte_canonical=analyte_canonical,
            concept_id=concept_id,
            loinc_code=loinc_code,
            reference_range_low=reference_range_low,
            reference_range_high=reference_range_high,
            flag=flag,
            date_type=date_type,
            date_confidence=date_confidence,
            source_provenance=source_provenance,
            created_at=datetime.now(UTC),
        )

    async def bulk_create_events(
        self,
        owner_id: uuid.UUID,
        source_report_id: uuid.UUID,
        events: list[dict],
    ) -> list[TimelineEvent]:
        """
        Bulk-insert timeline events from a parsed report.
        Each dict in `events` must contain: test_name, date_of_test.
        Optional keys: value_numeric, value_text, unit.

        CP-04: The following optional canonical concept keys are also accepted
        and persisted when present:
          analyte_canonical, concept_id, loinc_code,
          reference_range_low, reference_range_high, flag,
          date_type, date_confidence, source_provenance.
        """
        from ..models import TimelineEvent as TE

        records = [
            TE(
                owner_id=owner_id,
                source_report_id=source_report_id,
                test_name=e["test_name"],
                date_of_test=e["date_of_test"],
                value_numeric=e.get("value_numeric"),
                value_text=e.get("value_text"),
                unit=e.get("unit"),
                analyte_canonical=e.get("analyte_canonical"),
                concept_id=e.get("concept_id"),
                loinc_code=e.get("loinc_code"),
                reference_range_low=e.get("reference_range_low"),
                reference_range_high=e.get("reference_range_high"),
                flag=e.get("flag"),
                date_type=e.get("date_type"),
                date_confidence=e.get("date_confidence"),
                source_provenance=e.get("source_provenance"),
                created_at=datetime.now(UTC),
            )
            for e in events
            if e.get("date_of_test") is not None  # only store events with a known date
        ]
        if records:
            self._session.add_all(records)
            await self._session.flush()
        return records


    async def list_events_for_test(
        self,
        owner_id: uuid.UUID,
        test_name: str,
        *,
        limit: int = 200,
    ) -> Sequence[TimelineEvent]:
        """
        Chronological history for a single lab metric, scoped to owner.
        Returns oldest-first so callers can directly pass to trend detector.
        """
        result = await self._session.execute(
            select(TimelineEvent)
            .where(
                self.predicate(owner_id),
                TimelineEvent.test_name == test_name,
            )
            .order_by(TimelineEvent.date_of_test.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_timeline_summary(
        self,
        owner_id: uuid.UUID,
    ) -> list[dict]:
        """
        Returns one entry per distinct test_name with the latest value and
        date, grouped by test_name. Used by GET /timeline to render the
        full health timeline overview for a user.

        Scoped to owner_id — cannot return cross-user data.
        """
        # Fetch all events for the owner, then group in Python (avoids
        # database-specific window-function syntax that may not work on SQLite in tests).
        result = await self._session.execute(
            select(TimelineEvent)
            .where(self.predicate(owner_id))
            .order_by(TimelineEvent.test_name, TimelineEvent.date_of_test.desc())
        )
        rows = result.scalars().all()

        summary: dict[str, dict] = {}
        for row in rows:
            if row.test_name not in summary:
                summary[row.test_name] = {
                    "test_name": row.test_name,
                    "unit": row.unit,
                    "latest_date": row.date_of_test.isoformat() if row.date_of_test else None,
                    "latest_value_numeric": (
                        float(row.value_numeric) if row.value_numeric is not None else None
                    ),
                    "latest_value_text": row.value_text,
                    "data_point_count": 0,
                }
            summary[row.test_name]["data_point_count"] += 1

        return list(summary.values())
