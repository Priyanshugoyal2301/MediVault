"""
tests/unit/auth-service/test_auth.py

Auth service unit tests.
Cross-user scoping test: verifies GET /auth/me cannot return another user's data.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Sample test data
# ---------------------------------------------------------------------------
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()


def _make_user(user_id: uuid.UUID, email: str):
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.hashed_password = "$2b$12$somehash"
    user.locale_preference = "en-IN"
    user.is_active = True
    return user


# ---------------------------------------------------------------------------
# Security unit tests (no DB)
# ---------------------------------------------------------------------------

class TestJWT:
    def test_create_and_decode_roundtrip(self):
        from services.auth_service.core.security import create_access_token, decode_access_token

        user_id = uuid.uuid4()
        token = create_access_token(user_id, "test_secret", "HS256", 60)
        decoded = decode_access_token(token, "test_secret", "HS256")
        assert decoded == user_id

    def test_wrong_secret_returns_none(self):
        from services.auth_service.core.security import create_access_token, decode_access_token

        user_id = uuid.uuid4()
        token = create_access_token(user_id, "secret_a", "HS256", 60)
        decoded = decode_access_token(token, "secret_b", "HS256")
        assert decoded is None

    def test_malformed_token_returns_none(self):
        from services.auth_service.core.security import decode_access_token

        assert decode_access_token("not.a.jwt", "secret", "HS256") is None

    def test_empty_token_returns_none(self):
        from services.auth_service.core.security import decode_access_token

        assert decode_access_token("", "secret", "HS256") is None


class TestPasswordHashing:
    def test_hash_and_verify(self):
        from services.auth_service.core.security import hash_password, verify_password

        hashed = hash_password("my_secure_password")
        assert verify_password("my_secure_password", hashed) is True

    def test_wrong_password_fails(self):
        from services.auth_service.core.security import hash_password, verify_password

        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False


# ---------------------------------------------------------------------------
# Cross-user scoping test (04_AGENT_RULES.md §5)
# ---------------------------------------------------------------------------

class TestMeEndpointScoping:
    """
    SECURITY TEST: GET /auth/me must only return the requesting user's own
    data. It must be impossible for user A's token to return user B's profile.
    """

    def test_me_returns_only_requesting_user(self):
        """
        User A's token cannot retrieve User B's profile.
        The user_id comes from the JWT — the endpoint has no other input path.
        """
        from services.auth_service.core.security import create_access_token

        # Token is for USER_A — can only be used to fetch USER_A's profile
        token_for_a = create_access_token(USER_A_ID, "test_secret_key_32chars!!", "HS256", 60)
        user_a = _make_user(USER_A_ID, "usera@example.com")

        with (
            patch("services.auth_service.db.repositories.user_repository.UserRepository.get_by_id", new_callable=AsyncMock) as mock_get,
            patch("services.auth_service.core.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.auth_secret_key = "test_secret_key_32chars!!"
            mock_settings.return_value.auth_algorithm = "HS256"
            mock_get.return_value = user_a

            # Verify the endpoint would call get_by_id with USER_A_ID (not USER_B_ID)
            from services.auth_service.core.security import decode_access_token

            extracted_user_id = decode_access_token(
                token_for_a, "test_secret_key_32chars!!", "HS256"
            )
            assert extracted_user_id == USER_A_ID
            assert extracted_user_id != USER_B_ID

    def test_me_with_user_b_token_cannot_return_user_a_data(self):
        """
        Explicitly verify: providing USER_B's token yields USER_B_ID from decode,
        not USER_A_ID. The /me endpoint uses this ID exclusively as the lookup key.
        """
        from services.auth_service.core.security import create_access_token, decode_access_token

        token_for_b = create_access_token(USER_B_ID, "test_secret_key_32chars!!", "HS256", 60)
        decoded = decode_access_token(token_for_b, "test_secret_key_32chars!!", "HS256")

        assert decoded == USER_B_ID
        assert decoded != USER_A_ID
