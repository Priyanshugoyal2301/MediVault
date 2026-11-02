"""Gateway identity, active account checks and service credential isolation."""

import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from starlette.requests import Request

SECRET = "test-only-jwt-secret-with-more-than-32-characters"
SERVICE_KEY = "test-only-service-key-with-more-than-32-characters"
USER = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def gateway(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "apps" / "api"))
    auth = importlib.import_module("core.auth")
    proxy = importlib.import_module("routers.proxy")
    return auth, proxy


def token(**changes):
    payload = {"sub": USER, "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    payload.update(changes)
    return jwt.encode(payload, SECRET, "HS256")


def settings():
    return SimpleNamespace(auth_secret_key=SECRET, auth_algorithm="HS256", auth_service_url="http://auth")


def mock_client(monkeypatch, module, response=None, error=None):
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.get.return_value = response
    client.get.side_effect = error
    client.request.return_value = response
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: client)
    return client


@pytest.mark.asyncio
@pytest.mark.parametrize("status,body,expected", [
    (404, {}, 401), (401, {}, 401), (500, {}, 503),
    (200, {"id": "someone-else"}, 401), (200, [], 401),
])
async def test_inactive_or_mismatched_identity_is_denied(gateway, monkeypatch, status, body, expected):
    auth, _ = gateway
    mock_client(monkeypatch, auth, httpx.Response(status, json=body))
    with pytest.raises(HTTPException) as error:
        await auth.require_user_id(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token()), settings())
    assert error.value.status_code == expected


@pytest.mark.asyncio
async def test_active_account_authorizes_only_token_owner(gateway, monkeypatch):
    auth, _ = gateway
    client = mock_client(monkeypatch, auth, httpx.Response(200, json={"id": USER}))
    signed = token()
    assert await auth.require_user_id(HTTPAuthorizationCredentials(scheme="Bearer", credentials=signed), settings()) == USER
    client.get.assert_awaited_once_with("http://auth/auth/me", headers={"Authorization": f"Bearer {signed}"})


@pytest.mark.asyncio
async def test_auth_service_outage_fails_closed(gateway, monkeypatch):
    auth, _ = gateway
    mock_client(monkeypatch, auth, error=httpx.ConnectError("offline"))
    with pytest.raises(HTTPException) as error:
        await auth.require_user_id(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token()), settings())
    assert error.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["sub", "exp", "iat"])
async def test_gateway_rejects_tokens_without_required_claims(gateway, monkeypatch, missing):
    auth, _ = gateway
    payload = {"sub": USER, "iat": 1, "exp": 9999999999}
    del payload[missing]
    client = mock_client(monkeypatch, auth)
    with pytest.raises(HTTPException) as error:
        await auth.require_user_id(HTTPAuthorizationCredentials(scheme="Bearer", credentials=jwt.encode(payload, SECRET, "HS256")), settings())
    assert error.value.status_code == 401
    client.get.assert_not_awaited()


@pytest.mark.parametrize("missing", ["sub", "exp", "iat"])
def test_auth_service_also_requires_claims(missing):
    from services.auth_service.core.security import decode_access_token
    payload = {"sub": USER, "iat": 1, "exp": 9999999999}
    del payload[missing]
    assert decode_access_token(jwt.encode(payload, SECRET, "HS256"), SECRET, "HS256") is None


def request(method="GET", path="/reports"):
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}
    return Request({"type": "http", "method": method, "path": path, "query_string": b"", "client": ("198.51.100.23", 12345),
                    "headers": [(b"x-user-id", b"victim"), (b"x-internal-key", b"attacker"),
                                (b"x-user-role", b"doctor"), (b"x-doctor-verified", b"true"),
                                (b"x-auth-client-ip", b"203.0.113.99"),
                                (b"cf-connecting-ip", b"203.0.113.99")]}, receive)


@pytest.mark.asyncio
async def test_proxy_replaces_untrusted_headers(gateway, monkeypatch):
    _, proxy = gateway
    client = mock_client(monkeypatch, proxy, httpx.Response(200, json=[]))
    response = await proxy._forward(request(), "http://health", "/reports", user_id=USER,
                                    internal_service_key=SERVICE_KEY, auth_client_ip="198.51.100.23")
    sent = client.request.call_args.kwargs["headers"]
    assert sent == {"X-Auth-Client-IP": "198.51.100.23", "X-User-ID": USER, "X-Internal-Key": SERVICE_KEY}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_proxy_never_forwards_without_service_configuration(gateway, monkeypatch):
    _, proxy = gateway
    client = mock_client(monkeypatch, proxy)
    assert (await proxy._forward(request(), "http://health", "/reports", user_id=USER)).status_code == 503
    client.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_auth_proxy_uses_socket_ip_and_ignores_spoofed_ip_headers(gateway, monkeypatch):
    _, proxy = gateway
    captured = {}

    async def forward(request, upstream_base, path, **kwargs):
        captured.update(kwargs)
        return httpx.Response(401, json={"detail": "Invalid credentials"})

    monkeypatch.setattr(proxy, "_forward", forward)
    response = await proxy.proxy_auth(
        "login", request("POST", "/auth/login"),
        SimpleNamespace(cors_origin_list=[], trust_cf_connecting_ip=False, auth_service_url="http://auth"),
    )
    assert response.status_code == 401
    assert captured["auth_client_ip"] == "198.51.100.23"


@pytest.mark.asyncio
async def test_public_auth_proxy_uses_cloudflare_ip_only_when_explicitly_trusted(gateway, monkeypatch):
    _, proxy = gateway
    captured = {}

    async def forward(request, upstream_base, path, **kwargs):
        captured.update(kwargs)
        return httpx.Response(401, json={"detail": "Invalid credentials"})

    monkeypatch.setattr(proxy, "_forward", forward)
    response = await proxy.proxy_auth(
        "login", request("POST", "/auth/login"),
        SimpleNamespace(cors_origin_list=[], trust_cf_connecting_ip=True, auth_service_url="http://auth"),
    )
    assert response.status_code == 401
    assert captured["auth_client_ip"] == "203.0.113.99"
