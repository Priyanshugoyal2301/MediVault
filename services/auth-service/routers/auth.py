"""
auth-service/routers/auth.py

Endpoints: register, login, me, logout.

Cross-user scoping: GET /auth/me returns only the requesting user's own
record — it uses the user_id from the validated JWT, never from the
request body. The UserRepository.get_by_id() requires the exact UUID;
there's no way for user A to retrieve user B's profile through this endpoint.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
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

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()


# ---------------------------------------------------------------------------
# Request / Response schemas (service-local; shared across services go in
# packages/shared-types/schemas.py)
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    locale_preference: str = "en-IN"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    locale_preference: str


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

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    if body.locale_preference not in ("en-IN", "hi-IN"):
        raise HTTPException(status_code=400, detail="locale_preference must be 'en-IN' or 'hi-IN'")

    repo = UserRepository(db)
    if await repo.get_by_email(body.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = await repo.create(
        email=body.email,
        hashed_password=hash_password(body.password),
        locale_preference=body.locale_preference,
    )
    # Log user creation WITHOUT the password or email (health-data rule applies
    # to health data; email is PII so we redact it the same way)
    logger.info("User created: user_id=%s locale=%s", user.id, user.locale_preference)

    token = create_access_token(
        user_id=user.id,
        secret_key=settings.auth_secret_key,
        algorithm=settings.auth_algorithm,
        expires_minutes=settings.auth_access_token_expire_minutes,
    )
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    repo = UserRepository(db)
    user = await repo.get_by_email(body.email)
    # Return 401 for both "user not found" and "wrong password"
    # to prevent email enumeration.
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    logger.info("User login: user_id=%s", user.id)
    token = create_access_token(
        user_id=user.id,
        secret_key=settings.auth_secret_key,
        algorithm=settings.auth_algorithm,
        expires_minutes=settings.auth_access_token_expire_minutes,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(
    user_id: Annotated[object, Depends(_get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Returns the authenticated user's own profile.
    Cross-user scoping: user_id comes exclusively from the validated JWT —
    the endpoint cannot return any other user's data.
    """
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(id=str(user.id), email=user.email, locale_preference=user.locale_preference)
