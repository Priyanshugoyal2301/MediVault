"""Account-scoped counters. Never expose other patients' names or file paths."""
from typing import Annotated
from uuid import UUID
import hashlib
from fastapi import APIRouter,Depends,Header,HTTPException
from sqlalchemy import func,select
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.config import Settings,get_settings
from ..db.models import Report,User
from ..db.session import get_db
from ..storage.local_storage import encrypted_size

router=APIRouter(prefix='/care',tags=['storage'])
MAX_DOCUMENT_BYTES=20*1024*1024
UNKNOWN_FILE_BYTES=encrypted_size(MAX_DOCUMENT_BYTES)


async def account_usage(db,actor,settings):
    real=~Report.storage_path.startswith('demo://')
    size,count,unknown= (await db.execute(select(
        func.coalesce(func.sum(func.coalesce(Report.stored_size_bytes,UNKNOWN_FILE_BYTES)),0),
        func.count(Report.id),func.count(Report.id).filter(Report.stored_size_bytes.is_(None))
    ).where(Report.owner_id==actor,real))).one()
    return dict(used_bytes=int(size),file_count=count,unmeasured_files=unknown,
        quota_bytes=settings.storage_account_quota_bytes,file_limit=settings.storage_account_file_limit,
        remaining_bytes=max(0,settings.storage_account_quota_bytes-int(size)),
        max_file_bytes=MAX_DOCUMENT_BYTES,scope='uploads_by_your_account_across_profiles',
        storage_location='local_server',encryption='Fernet authenticated encryption')


async def reserve_upload(db,actor,settings,required_bytes):
    # A transaction-scoped advisory lock serializes quotas without granting the
    # health role UPDATE access to auth-owned user records.
    lock_id = int.from_bytes(hashlib.sha256(actor.bytes).digest()[:8], "big") & ((1 << 63) - 1)
    await db.execute(select(func.pg_advisory_xact_lock(lock_id)))
    if await db.scalar(select(User.id).where(User.id==actor)) is None:
        raise HTTPException(401,'Account not available')
    usage=await account_usage(db,actor,settings)
    if usage['file_count']>=usage['file_limit'] or usage['used_bytes']+required_bytes>usage['quota_bytes']:
        raise HTTPException(413,'Your upload storage limit has been reached. Remove unneeded documents or contact the administrator.')


@router.get('/storage')
async def storage_usage(db:Annotated[AsyncSession,Depends(get_db)],settings:Annotated[Settings,Depends(get_settings)],
                        x_user_id:Annotated[str,Header()]):
    try:actor=UUID(x_user_id)
    except ValueError:raise HTTPException(401,'Invalid identity') from None
    if await db.get(User,actor) is None:raise HTTPException(401,'Account not available')
    return await account_usage(db,actor,settings)
