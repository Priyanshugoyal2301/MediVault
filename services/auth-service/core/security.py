"""
auth-service/core/security.py

Password hashing and JWT creation/verification.

IMPORTANT: jwt_secret_key comes from the caller (injected from Settings) —
this module never reads env vars directly, making it unit-testable.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT utilities
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: UUID,
    secret_key: str,
    algorithm: str,
    expires_minutes: int,
) -> str:
    """Create a signed JWT with sub=user_id and an expiry claim."""
    expire = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(
    token: str,
    secret_key: str,
    algorithm: str,
) -> UUID | None:
    """
    Decode and verify a JWT. Returns the user_id UUID on success, None on failure.
    Never raises — all failures return None so callers can return 401 uniformly.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        sub: str | None = payload.get("sub")
        if sub is None:
            return None
        return UUID(sub)
    except (JWTError, ValueError):
        return None
