"""
auth-service/routers/auth.py

Endpoints: register, login, me, logout.

Cross-user scoping: GET /auth/me returns only the requesting user's own
record — it uses the user_id from the validated JWT, never from the
request body. The UserRepository.get_by_id() requires the exact UUID;
there's no way for user A to retrieve user B's profile through this endpoint.
"""

from typing import Annotated
import hashlib
import hmac
import ipaddress
from urllib.parse import quote
from sqlalchemy import case, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared_utils import get_logger

from ..core.config import Settings, get_settings
from ..core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from ..db.repositories.user_repository import UserRepository
from ..db.session import get_db
from ..db.models import AuthLoginAttempt, AuthSession, User
from ..core.mfa import new_secret, verify_code, recovery_codes, consume_recovery
from packages.shared_utils.vault_crypto import encrypt_document, decrypt_document

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()


def check_attempt_limit(user):
    """Limit authenticated password proofs (for example MFA changes)."""
    now = datetime.now(UTC)
    if not user.auth_window_started or now - user.auth_window_started >= timedelta(minutes=15):
        user.auth_window_started = now
        user.auth_failures = 0
    if user.auth_failures >= 8:
        raise HTTPException(429, "Too many authentication attempts. Try again later.", headers={"Retry-After": "900"})


async def reject_attempt(db, user, detail="Invalid credentials", status_code=401):
    user.auth_failures += 1
    # Persist the failure before raising: the request dependency rolls back errors.
    await db.commit()
    raise HTTPException(status_code, detail)


LOGIN_RATE_WINDOW = timedelta(minutes=15)
LOGIN_RATE_LIMITS = {"source": 60, "source_email": 8}


def _login_rate_keys(client_ip: str, email: str, secret: str) -> dict[str, str]:
    """Build opaque, HMAC-keyed rate-limit identifiers without storing PII."""
    try:
        normalized_ip = str(ipaddress.ip_address(client_ip))
    except ValueError:
        raise HTTPException(400, "Invalid client address") from None
    normalized_email = email.strip().lower()
    return {
        scope: hmac.new(secret.encode(), f"{scope}:{value}".encode(), hashlib.sha256).hexdigest()
        for scope, value in (
            ("source", normalized_ip),
            ("source_email", f"{normalized_ip}\0{normalized_email}"),
        )
    }


async def check_login_rate_limit(db, client_ip: str, email: str, secret: str) -> None:
    """Reject abusive sources, not accounts; state is shared across workers.

    Transaction-scoped advisory locks serialize the check and subsequent result
    update for the same source, including when the account does not exist.
    """
    now = datetime.now(UTC)
    keys = _login_rate_keys(client_ip, email, secret)
    for key_hash in keys.values():
        lock_id = int.from_bytes(bytes.fromhex(key_hash)[:8], "big") & ((1 << 63) - 1)
        await db.execute(select(func.pg_advisory_xact_lock(lock_id)))
    rows = (await db.scalars(select(AuthLoginAttempt).where(AuthLoginAttempt.key_hash.in_(keys.values())))).all()
    by_key = {row.key_hash: row for row in rows}
    for scope, key_hash in keys.items():
        row = by_key.get(key_hash)
        if row and row.window_started_at + LOGIN_RATE_WINDOW > now and row.failures >= LOGIN_RATE_LIMITS[scope]:
            retry_after = max(1, int((row.window_started_at + LOGIN_RATE_WINDOW - now).total_seconds()))
            raise HTTPException(429, "Too many sign-in attempts. Try again later.", headers={"Retry-After": str(retry_after)})


async def record_failed_login(db, client_ip: str, email: str, secret: str) -> None:
    """Atomically count bad attempts by source and source/account pair."""
    now = datetime.now(UTC)
    expired_before = now - LOGIN_RATE_WINDOW
    for key_hash in _login_rate_keys(client_ip, email, secret).values():
        statement = pg_insert(AuthLoginAttempt).values(
            key_hash=key_hash, failures=1, window_started_at=now,
        ).on_conflict_do_update(
            index_elements=[AuthLoginAttempt.key_hash],
            set_={
                "failures": case(
                    (AuthLoginAttempt.window_started_at <= expired_before, 1),
                    else_=AuthLoginAttempt.failures + 1,
                ),
                "window_started_at": case(
                    (AuthLoginAttempt.window_started_at <= expired_before, now),
                    else_=AuthLoginAttempt.window_started_at,
                ),
            },
        )
        await db.execute(statement)
    # Keep only one day of rate-limit state. The indexed delete also bounds rows
    # created by callers that rotate addresses over time.
    await db.execute(delete(AuthLoginAttempt).where(AuthLoginAttempt.window_started_at < now - timedelta(days=1)))
    await db.commit()


async def clear_successful_login_pair(db, client_ip: str, email: str, secret: str) -> None:
    key_hash = _login_rate_keys(client_ip, email, secret)["source_email"]
    await db.execute(delete(AuthLoginAttempt).where(AuthLoginAttempt.key_hash == key_hash))


async def _registration_response(db, email: str, password: str, locale_preference: str):
    """Create an account when available but never disclose address existence."""
    password_hash = hash_password(password)
    repo = UserRepository(db)
    existing = await repo.get_by_email(email)
    if existing is None:
        try:
            user = await repo.create(
                email=email,
                hashed_password=password_hash,
                locale_preference=locale_preference,
            )
            logger.info("User created: user_id=%s locale=%s", user.id, user.locale_preference)
        except IntegrityError as exc:
            await db.rollback()
            constraint = (
                getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
                or getattr(exc.orig, "constraint_name", None)
            )
            if constraint != "users_email_key":
                raise
    return RegistrationResponse()


# ---------------------------------------------------------------------------
# Request / Response schemas (service-local; shared across services go in
# packages/shared-types/schemas.py)
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    locale_preference: str = "en-IN"

    @field_validator("password")
    @classmethod
    def bcrypt_limit(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must fit within 72 UTF-8 bytes")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)
    verification_code: str = Field(default="", max_length=80)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegistrationResponse(BaseModel):
    detail: str = "Request received. Continue to sign in. If an account already exists, use its current password."


class UserOut(BaseModel):
    id: str
    email: str
    locale_preference: str
    mfa_enabled: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    user_id = decode_access_token(
        credentials.credentials,
        settings.auth_secret_key,
        settings.auth_algorithm,
    )
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user_id


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_202_ACCEPTED)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Generic result for both existing and new addresses. Registration no
    # longer signs the user in; they use the normal login flow afterward.
    if body.locale_preference not in ("en-IN", "hi-IN"):
        raise HTTPException(status_code=400, detail="locale_preference must be 'en-IN' or 'hi-IN'")
    return await _registration_response(db, body.email, body.password, body.locale_preference)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    client_ip = request.headers.get("x-auth-client-ip") or (request.client.host if request.client else "")
    if not client_ip:
        raise HTTPException(503, "Sign-in rate limiting is unavailable")
    await check_login_rate_limit(db, client_ip, body.email, settings.auth_secret_key)

    repo = UserRepository(db)
    user = await repo.get_by_email(body.email, lock=True)
    # Return 401 for both "user not found" and "wrong password"
    # to prevent email enumeration.
    if user is None:
        await record_failed_login(db, client_ip, body.email, settings.auth_secret_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(body.password, user.hashed_password):
        await record_failed_login(db, client_ip, body.email, settings.auth_secret_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.otp_enabled:
        if not body.verification_code:
            await record_failed_login(db, client_ip, body.email, settings.auth_secret_key)
            raise HTTPException(401, "Enter the code from your authenticator app, or an unused recovery code.",
                                headers={"X-MFA-Required": "true"})
        secret = decrypt_document(user.otp_secret.encode(), settings.file_encryption_key).decode()
        counter = verify_code(secret, body.verification_code, user.otp_last_counter)
        if counter is not None:
            user.otp_last_counter = counter
        else:
            remaining = consume_recovery(user.otp_recovery or [], body.verification_code)
            if remaining is None:
                await record_failed_login(db, client_ip, body.email, settings.auth_secret_key)
                raise HTTPException(401, "Invalid credentials")
            user.otp_recovery = remaining

    user.auth_failures = 0
    await clear_successful_login_pair(db, client_ip, body.email, settings.auth_secret_key)
    logger.info("User login: user_id=%s", user.id)
    token = create_access_token(
        user_id=user.id,
        secret_key=settings.auth_secret_key,
        algorithm=settings.auth_algorithm,
        expires_minutes=settings.auth_access_token_expire_minutes,
    )
    db.add(AuthSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id,
                       expires_at=datetime.now(UTC) + timedelta(minutes=settings.auth_access_token_expire_minutes)))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(
    user_id: Annotated[object, Depends(_get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
):
    """
    Returns the authenticated user's own profile.
    Cross-user scoping: user_id comes exclusively from the validated JWT —
    the endpoint cannot return any other user's data.
    """
    session = await db.get(AuthSession, hashlib.sha256(credentials.credentials.encode()).hexdigest())
    if not session or session.revoked or session.user_id != user_id or session.expires_at <= datetime.now(UTC):
        raise HTTPException(401, "Session expired or revoked")
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(id=str(user.id), email=user.email, locale_preference=user.locale_preference, mfa_enabled=user.otp_enabled)


class MFAProof(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    code: str = Field(default="", max_length=80)


async def mfa_user(db, credentials, settings, password):
    user_id = decode_access_token(credentials.credentials, settings.auth_secret_key, settings.auth_algorithm)
    session = await db.get(AuthSession, hashlib.sha256(credentials.credentials.encode()).hexdigest())
    if not user_id or not session or session.revoked or session.user_id != user_id or session.expires_at <= datetime.now(UTC):
        raise HTTPException(401, "Session expired or revoked")
    user = await db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)).with_for_update())
    if not user:
        raise HTTPException(401, "Invalid credentials")
    check_attempt_limit(user)
    if not verify_password(password, user.hashed_password):
        await reject_attempt(db, user)
    return user


@router.post("/mfa/setup")
async def setup_mfa(body: MFAProof, credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
                    db: Annotated[AsyncSession, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    user = await mfa_user(db, credentials, settings, body.password)
    if user.otp_enabled:
        raise HTTPException(409, "Two-step verification is already enabled")
    secret = new_secret()
    try:
        user.otp_secret = encrypt_document(secret.encode(), settings.file_encryption_key).decode()
    except (ValueError, UnicodeError):
        raise HTTPException(503, "Authenticator encryption is not configured") from None
    return {"secret": secret, "uri": f"otpauth://totp/{quote('MediVault:' + user.email)}?secret={secret}&issuer=MediVault&algorithm=SHA1&digits=6&period=30"}


@router.post("/mfa/enable")
async def enable_mfa(body: MFAProof, credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
                     db: Annotated[AsyncSession, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    user = await mfa_user(db, credentials, settings, body.password)
    if user.otp_enabled or not user.otp_secret:
        raise HTTPException(409, "Start authenticator setup first")
    counter = verify_code(decrypt_document(user.otp_secret.encode(), settings.file_encryption_key).decode(), body.code)
    if counter is None:
        await reject_attempt(db, user, "Authenticator code was not accepted", 400)
    codes, hashes = recovery_codes()
    user.otp_enabled = True
    user.auth_failures = 0
    user.otp_last_counter = counter
    user.otp_recovery = hashes
    await db.execute(update(AuthSession).where(AuthSession.user_id == user.id,
        AuthSession.token_hash != hashlib.sha256(credentials.credentials.encode()).hexdigest()).values(revoked=True))
    return {"enabled": True, "recovery_codes": codes}


@router.post("/mfa/disable", status_code=204)
async def disable_mfa(body: MFAProof, credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
                      db: Annotated[AsyncSession, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    user = await mfa_user(db, credentials, settings, body.password)
    if not user.otp_enabled:
        raise HTTPException(409, "Two-step verification is not enabled")
    counter = verify_code(decrypt_document(user.otp_secret.encode(), settings.file_encryption_key).decode(), body.code, user.otp_last_counter)
    if counter is None and consume_recovery(user.otp_recovery or [], body.code) is None:
        await reject_attempt(db, user, "Enter a fresh authenticator or unused recovery code", 400)
    user.otp_enabled = False
    user.auth_failures = 0
    user.otp_secret = None
    user.otp_recovery = None
    await db.execute(update(AuthSession).where(AuthSession.user_id == user.id).values(revoked=True))


@router.post("/logout", status_code=204)
async def logout(user_id: Annotated[object, Depends(_get_current_user_id)],
                 credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
                 db: Annotated[AsyncSession, Depends(get_db)]):
    session = await db.get(AuthSession, hashlib.sha256(credentials.credentials.encode()).hexdigest())
    if session and session.user_id == user_id:
        session.revoked = True
