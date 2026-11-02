"""
health-service/db/repositories/report_repository.py

ReportRepository subclasses ScopedRepository — owner_id scoping is
structurally enforced at the query layer per 02_ARCHITECTURE.md §4.
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select, update, delete, and_
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

    def __init__(self, session, scope=None):
        super().__init__(session)
        self.scope = scope

    def predicate(self, owner_id):
        return self.scope.predicate() if self.scope else and_(Report.owner_id == owner_id, Report.patient_id.is_(None))

    async def get_by_id(self, record_id, owner_id):
        return await self._session.scalar(select(Report).where(Report.id == record_id, self.predicate(owner_id)))

    async def list_for_owner(self, owner_id, *, limit=100, offset=0):
        rows = await self._session.scalars(select(Report).where(self.predicate(owner_id))
                                          .order_by(Report.uploaded_at.desc(), Report.id).offset(offset).limit(limit))
        return rows.all()

    async def delete_for_owner(self, record_id, owner_id):
        result = await self._session.execute(delete(Report).where(Report.id == record_id, self.predicate(owner_id)))
        return result.rowcount > 0

    async def create_report(
        self,
        owner_id: uuid.UUID,
        original_filename: str,
        storage_path: str,
        mime_type: str,
        document_kind: str = "report",
        document_date: date | None = None,
        original_size_bytes: int | None = None,
        stored_size_bytes: int | None = None,
        content_sha256: str | None = None,
    ) -> Report:
        return await self.create(
            owner_id=owner_id,
            original_filename=original_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            patient_id=self.scope.patient_id if self.scope else None,
            document_kind=document_kind,
            document_date=document_date,
            original_size_bytes=original_size_bytes,
            stored_size_bytes=stored_size_bytes,
            content_sha256=content_sha256,
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
                analyte_canonical=v.get("analyte_canonical"),
                concept_id=v.get("concept_id"),
                loinc_code=v.get("loinc_code"),
                date_type=v.get("date_type"),
                date_confidence=str(v["date_confidence"]) if v.get("date_confidence") is not None else None,
                source_provenance=v.get("source_provenance"),
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
            .where(ReportValue.report_id == report_id)
            .order_by(ReportValue.test_name)
        )
        return list(result.scalars().all())
