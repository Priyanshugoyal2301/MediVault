"""Exercise deployed routers: knowing an owner UUID must not authorize access."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.shared_utils.service_auth import service_key_matches

KEY = "test-only-service-secret-with-more-than-32-characters"
OWNER = "00000000-0000-0000-0000-000000000001"


@pytest.mark.parametrize("configured", ["", "short", "CHANGE_ME_LONG_RANDOM_STRING_AT_LEAST_32_CHARS"])
def test_unconfigured_secret_never_authorizes(configured):
    assert not service_key_matches(configured, configured)


def test_service_key_comparison_handles_untrusted_unicode():
    assert not service_key_matches(KEY, "अमान्य")
    assert service_key_matches(KEY, KEY)


@pytest.fixture
def health_client(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-only-password")
    from services.health_service.main import app
    from services.health_service.core.config import get_settings
    from services.health_service.db.session import get_db

    async def database_must_not_run():
        raise AssertionError("Unauthorized request reached the database")
        yield  # make a dependency generator

    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(internal_service_key=KEY)
    app.dependency_overrides[get_db] = database_must_not_run
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.parametrize("path", ["/reports", f"/reports/{OWNER}", "/timeline", "/timeline/LDL"])
@pytest.mark.parametrize("secret", [None, "attacker-key"])
def test_forged_owner_cannot_read_health_records(health_client, path, secret):
    headers = {"X-User-ID": OWNER}
    if secret:
        headers["X-Internal-Key"] = secret
    assert health_client.get(path, headers=headers).status_code == 401


def test_forged_owner_cannot_mutate_or_query(health_client):
    headers = {"X-User-ID": OWNER}
    assert health_client.delete(f"/reports/{OWNER}", headers=headers).status_code == 401
    assert health_client.post("/reports/demo/seed", headers=headers).status_code == 401
    assert health_client.post("/qa", headers=headers, json={"question": "my records"}).status_code == 401


def test_health_missing_configuration_denies_access(health_client):
    from services.health_service.main import app
    from services.health_service.core.config import get_settings
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(internal_service_key="")
    response = health_client.get("/reports", headers={"X-User-ID": OWNER, "X-Internal-Key": KEY})
    assert response.status_code == 503


def test_health_liveness_does_not_require_patient_access(health_client):
    assert health_client.get("/health").status_code == 200


@pytest.fixture
def ai_client():
    from services.ai_service.routers.embed_report import router as embeddings
    from services.ai_service.routers.qa import router as qa
    from services.ai_service.core.config import get_settings
    app = FastAPI()
    app.include_router(embeddings)
    app.include_router(qa)
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(internal_service_key=KEY)
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("path,payload", [
    ("/qa", {"question": "my records"}),
    ("/embeddings/embed-report", {"report_id": OWNER, "values": []}),
])
def test_ai_qa_and_embedding_routes_reject_spoofed_identity(ai_client, path, payload):
    response = ai_client.post(path, json=payload, headers={"X-User-Id": OWNER})
    assert response.status_code == 401


def test_ai_embedding_delete_requires_internal_auth(ai_client):
    assert ai_client.delete(f"/embeddings/{OWNER}/{OWNER}", headers={"X-User-Id": OWNER}).status_code == 401


def test_authenticated_service_can_reach_embedding_contract(ai_client):
    response = ai_client.post("/embeddings/embed-report", json={"report_id": OWNER, "values": []},
                              headers={"X-User-Id": OWNER, "X-Internal-Key": KEY})
    assert response.status_code == 200


def test_ai_missing_configuration_denies_access():
    from services.ai_service.core.internal_auth import require_internal_key
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        require_internal_key(x_internal_key=KEY, settings=SimpleNamespace(internal_service_key=""))
    assert error.value.status_code == 503
