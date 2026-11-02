"""PostgreSQL-backed document queue. Leases recover work after process restarts."""
import asyncio
import uuid
from datetime import timedelta
from sqlalchemy import and_, or_, select
from ..db.models import Report
from ..db.session import _SessionLocal
from ..core.config import get_settings
from .models import StorageDeletion, now


async def run_once():
    from ..routers.reports import _trigger_parse
    from ..storage.local_storage import LocalStorage
    settings = get_settings()
    async with _SessionLocal() as db:
        deletion = await db.scalar(select(StorageDeletion).order_by(StorageDeletion.created_at).with_for_update(skip_locked=True).limit(1))
        if deletion:
            await LocalStorage(settings.storage_local_path, settings.file_encryption_key).delete(deletion.storage_path)
            await db.delete(deletion)
            await db.commit()
            return True
    async with _SessionLocal() as db:
        row = await db.scalar(select(Report).where(or_(Report.parsed_status == "pending", and_(
            Report.parsed_status == "processing", Report.processing_started_at < now() - timedelta(minutes=5)
        ))).order_by(Report.uploaded_at).with_for_update(skip_locked=True).limit(1))
        if row is None:
            return False
        row.parsed_status = "processing"
        row.processing_started_at = now()
        row.processing_token = uuid.uuid4()
        args = dict(report_id=str(row.id), owner_id=str(row.owner_id), storage_path=row.storage_path,
                    mime_type=row.mime_type, locale="en-IN", document_kind=row.document_kind,
                    processing_token=str(row.processing_token),expected_sha256=row.content_sha256)
        await db.commit()
    await _trigger_parse(**args, ai_service_url=settings.ai_service_url, db_url=settings.async_db_url)
    return True


async def worker_loop():
    from packages.shared_utils import get_logger
    logger = get_logger(__name__)
    while True:
        try:
            if not await run_once():
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.error("Document worker unavailable: %s", type(error).__name__)
            await asyncio.sleep(5)
