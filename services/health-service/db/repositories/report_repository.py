"""
health-service/db/repositories/report_repository.py

ReportRepository subclasses ScopedRepository — owner_id scoping is
structurally enforced at the query layer per 02_ARCHITECTURE.md §4.
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..base_repository import ScopedRepository
from ..models import Report, ReportValue


def _coerce_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


class ReportRepository(ScopedRepository[Report]):
    model = Report

    async def create_report(
        self,
        owner_id: uuid.UUID,
        original_filename: str,
        storage_path: str,
        mime_type: str,
    ) -> Report:
        return await self.create(
            owner_id=owner_id,
            original_filename=original_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            parsed_status="pending",
            uploaded_at=datetime.now(UTC),
        )

    async def set_parsing_status(
        self,
        report_id: uuid.UUID,
        owner_id: uuid.UUID,
        status: str,
    ) -> None:
        values: dict = {"parsed_status": status}
        if status == "complete":
            values["parsed_at"] = datetime.now(UTC)
        await self._session.execute(
            update(Report)
            .where(Report.id == report_id, Report.owner_id == owner_id)
            .values(**values)
        )

    async def save_report_values(
        self,
        owner_id: uuid.UUID,
        report_id: uuid.UUID,
        parsed_values: list[dict],
    ) -> list[ReportValue]:
        """Bulk-insert structured values from a parsed report."""
        records = [
            ReportValue(
                owner_id=owner_id,
                report_id=report_id,
                test_name=v["test_name"],
                panel=v.get("panel"),
                value_numeric=v.get("value_numeric"),
                value_text=v.get("value_text"),
                unit=v.get("unit"),
                reference_range_low=v.get("reference_range_low"),
                reference_range_high=v.get("reference_range_high"),
                reference_range_text=v.get("reference_range_text"),
                date_of_test=_coerce_date(v.get("date_of_test")),
                explanation_en=v.get("explanation_en"),
                explanation_hi=v.get("explanation_hi"),
                created_at=datetime.now(UTC),
            )
            for v in parsed_values
        ]
        self._session.add_all(records)
        await self._session.flush()
        return records

    async def get_values_for_report(
        self,
        report_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> list[ReportValue]:
        """Fetch all extracted values for a report, scoped to owner."""
        # Verify report ownership first
        report = await self.get_by_id(report_id, owner_id)
        if report is None:
            return []
        result = await self._session.execute(
            select(ReportValue)
            .where(ReportValue.report_id == report_id, ReportValue.owner_id == owner_id)
            .order_by(ReportValue.test_name)
        )
        return list(result.scalars().all())
