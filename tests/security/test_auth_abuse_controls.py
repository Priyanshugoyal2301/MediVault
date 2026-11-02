"""Regression coverage for authentication disclosure and lockout boundaries."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from services.auth_service.routers import auth


@pytest.mark.asyncio
async def test_registration_returns_same_generic_result_for_existing_and_new_email():
    results = []
    for is_existing in (False, True):
        db = MagicMock()
        db.rollback = AsyncMock()
        repository = MagicMock()
        repository.get_by_email = AsyncMock(return_value=object() if is_existing else None)
        repository.create = AsyncMock(return_value=SimpleNamespace(id="new-id", locale_preference="en-IN"))
        with patch.object(auth, "UserRepository", return_value=repository), patch.object(auth, "hash_password", return_value="hash"):
            results.append(await auth._registration_response(db, "person@example.test", "correct horse battery staple", "hi-IN"))

    assert [result.model_dump() for result in results] == [results[0].model_dump()] * 2
    assert all(result.detail == results[0].detail for result in results)


@pytest.mark.asyncio
async def test_registration_duplicate_race_returns_generic_result():
    db = MagicMock()
    db.rollback = AsyncMock()
    repository = MagicMock()
    repository.get_by_email = AsyncMock(return_value=None)
    repository.create = AsyncMock(side_effect=IntegrityError(
        "insert", {}, SimpleNamespace(diag=SimpleNamespace(constraint_name="users_email_key")),
    ))
    with patch.object(auth, "UserRepository", return_value=repository), patch.object(auth, "hash_password", return_value="hash"):
        result = await auth._registration_response(db, "person@example.test", "correct horse battery staple", "en-IN")

    assert result == auth.RegistrationResponse()
    db.rollback.assert_awaited_once()


def test_registration_route_uses_generic_accepted_contract():
    route = next(route for route in auth.router.routes if getattr(route, "path", None) == "/auth/register")
    assert route.status_code == 202
    assert route.response_model is auth.RegistrationResponse


def test_login_rate_keys_are_opaque_and_normalize_email_and_ip():
    lower = auth._login_rate_keys("198.51.100.8", "User@example.test", "secret")
    upper = auth._login_rate_keys("198.51.100.8", "user@EXAMPLE.TEST", "secret")
    other_source = auth._login_rate_keys("198.51.100.9", "user@example.test", "secret")

    assert lower == upper
    assert lower != other_source
    assert all("198.51.100.8" not in value and "user@example.test" not in value for value in lower.values())


def test_login_rate_keys_reject_malformed_client_ip():
    with pytest.raises(HTTPException) as error:
        auth._login_rate_keys("not-an-ip", "user@example.test", "secret")
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_rate_limit_blocks_only_the_exhausted_source_account_pair():
    keys = auth._login_rate_keys("198.51.100.8", "user@example.test", "secret")
    now = datetime.now(UTC)
    row = SimpleNamespace(key_hash=keys["source_email"], failures=8, window_started_at=now - timedelta(seconds=2))
    db = MagicMock()
    db.execute = AsyncMock()
    db.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: [row]))

    with pytest.raises(HTTPException) as error:
        await auth.check_login_rate_limit(db, "198.51.100.8", "user@example.test", "secret")
    assert error.value.status_code == 429
    assert int(error.value.headers["Retry-After"]) > 0


@pytest.mark.asyncio
async def test_rate_limit_does_not_lock_account_from_another_source():
    db = MagicMock()
    db.execute = AsyncMock()
    db.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: []))

    await auth.check_login_rate_limit(db, "198.51.100.9", "user@example.test", "secret")

    db.scalars.assert_awaited_once()
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_failed_login_state_is_upserted_and_committed_for_all_scopes():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await auth.record_failed_login(db, "198.51.100.8", "user@example.test", "secret")

    assert db.execute.await_count == 3  # source bucket, source/email bucket, expiry cleanup
    db.commit.assert_awaited_once()
