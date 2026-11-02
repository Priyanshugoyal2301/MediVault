"""Real PostgreSQL authorization and persistence tests.

Set CARE_TEST_DATABASE_URL to an isolated, migrated database. Each test runs
inside a rolled-back transaction, including endpoints which explicitly commit.
"""
import hashlib
import os
import uuid
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.health_service.care.models import Clinician, Grant, Patient, PrescriptionReview
from services.health_service.core.internal_auth import require_internal_key
from services.health_service.db.models import Report, ReportValue, TimelineEvent
from services.health_service.db.session import get_db
from services.health_service.main import app

pytestmark = pytest.mark.asyncio
DATABASE = os.environ.get("CARE_TEST_DATABASE_URL")
ACTORS = [uuid.uuid4() for _ in range(4)]
MED = {"name": "Synthetic medicine", "dose": "As recorded", "status": "taking"}
PAYLOADS = {
    "medications": MED,
    "allergies": {"substance": "Synthetic substance", "reaction": "Reported rash"},
    "encounters": {"facility": "Test clinic", "occurred_on": "2026-01-01", "reason": "Review"},
    "appointments": {"facility": "Test clinic", "scheduled_at": "2027-01-01T10:00:00+05:30", "purpose": "Review"},
    "referrals": {"facility":"Test clinic","reason":"Review","issued_on":"2026-01-01"},
    "claims": {"facility":"Test clinic","scheme":"Test scheme","amount_rupees":"100.00"},
    "benefits": {"scheme":"Test scheme"},
    "vaccinations": {"name":"Test vaccine","administered_on":"2026-01-01"},
}


@pytest_asyncio.fixture
async def context(tmp_path):
    if not DATABASE:
        pytest.skip("Set CARE_TEST_DATABASE_URL to a migrated isolated PostgreSQL database")
    engine = create_async_engine(DATABASE)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        factory = async_sessionmaker(connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        async with factory() as db:
            for actor in ACTORS:
                await db.execute(text("INSERT INTO users(id,email,hashed_password) VALUES(:id,:email,'test-only')"),
                                 {"id": actor, "email": f"{actor}@example.test"})
            await db.commit()

        async def database():
            async with factory() as db:
                try:
                    yield db
                    await db.commit()
                except Exception:
                    await db.rollback()
                    raise

        app.dependency_overrides[get_db] = database
        app.dependency_overrides[require_internal_key] = lambda: None
        from cryptography.fernet import Fernet
        from services.health_service.routers.reports import _get_storage
        from services.health_service.storage.local_storage import LocalStorage
        storage=LocalStorage(str(tmp_path),Fernet.generate_key().decode())
        app.dependency_overrides[_get_storage] = lambda: storage
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            yield client, factory
        app.dependency_overrides.clear()
        await transaction.rollback()
    await engine.dispose()


def headers(actor=0):
    return {"X-User-ID": str(ACTORS[actor])}


async def profile(client, actor=0, child=False):
    response = await client.post("/care/patients", headers=headers(actor), json={
        "display_name": "Synthetic child" if child else "Synthetic adult",
        "birth_date": "2020-01-01" if child else "1990-01-01", "relationship": "child" if child else "self"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def share(client, patient, scope, *, write=False, doctor=False):
    response = await client.post(f"/care/patients/{patient}/grants", headers=headers(), json={
        "label": "Test recipient", "recipient_kind": "doctor" if doctor else "caregiver",
        "scopes": [scope], "can_write": write, "expires_at": (datetime.now(UTC)+timedelta(days=1)).isoformat()})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("scope", list(PAYLOADS))
async def test_record_crud_is_scoped_versioned_and_audited(context, scope):
    client, _ = context
    patient = await profile(client)
    other = await profile(client, 1)
    path = f"/care/patients/{patient}/{scope}"
    created = await client.post(path, headers=headers(), json=PAYLOADS[scope])
    assert created.status_code == 201, created.text
    record = created.json()
    assert record["recorded_by"] == str(ACTORS[0])
    assert (await client.get(path, headers=headers(1))).status_code == 404
    assert (await client.post(path, headers=headers(1), json=PAYLOADS[scope])).status_code == 404
    assert (await client.put(path+f"/{record['id']}", headers={**headers(1),"If-Match":"1"}, json=PAYLOADS[scope])).status_code == 404
    assert (await client.put(f"/care/patients/{other}/{scope}/{record['id']}", headers={**headers(1),"If-Match":"1"}, json=PAYLOADS[scope])).status_code == 404
    changed = await client.put(path+f"/{record['id']}", headers={**headers(),"If-Match":"1"}, json={**PAYLOADS[scope],"notes":"Correction"})
    assert changed.status_code == 200
    assert changed.json()["version"] == 2
    history=await client.get(path+f"/{record['id']}/history",headers=headers())
    assert history.status_code==200
    assert history.json()['previous'][0]['snapshot']['version']==1
    assert (await client.get(path+f"/{record['id']}/history",headers=headers(1))).status_code==404
    assert (await client.put(path+f"/{record['id']}", headers={**headers(),"If-Match":"1"}, json=PAYLOADS[scope])).status_code == 409
    events = (await client.get(f"/care/patients/{patient}/audit", headers=headers())).json()
    assert f"{scope}.updated" in [event["action"] for event in events]
    assert (await client.get(f"/care/patients/{patient}/audit", headers=headers(1))).status_code == 404


@pytest.mark.parametrize("scope", list(PAYLOADS))
async def test_grant_scopes_readonly_replay_and_revocation(context, scope):
    client, _ = context
    patient = await profile(client)
    grant = await share(client, patient, scope)
    accepted = await client.post("/care/grants/accept", headers=headers(1), json={"token":grant["token"]})
    assert accepted.status_code == 200
    assert (await client.post("/care/grants/accept", headers=headers(2), json={"token":grant["token"]})).status_code == 404
    path = f"/care/patients/{patient}/{scope}"
    assert (await client.get(path, headers=headers(1))).status_code == 200
    assert (await client.post(path, headers=headers(1), json=PAYLOADS[scope])).status_code == 404
    for other_scope in set(PAYLOADS)-{scope}:
        assert (await client.get(f"/care/patients/{patient}/{other_scope}",headers=headers(1))).status_code == 404
    assert (await client.get(f"/care/patients/{patient}/grants",headers=headers(1))).status_code == 404
    assert (await client.delete(f"/care/patients/{patient}/grants/{grant['id']}",headers=headers(1))).status_code == 404
    assert (await client.delete(f"/care/patients/{patient}/grants/{grant['id']}",headers=headers())).status_code == 204
    assert (await client.get(path,headers=headers(1))).status_code == 404
    assert (await client.get("/care/patients",headers=headers(1))).json() == []


async def test_expiry_and_clinician_suspension(context):
    client, factory = context
    patient = await profile(client)
    grant = await share(client,patient,"allergies",write=True,doctor=True)
    body = {"token":grant["token"]}
    assert (await client.post("/care/grants/accept",headers=headers(1),json=body)).status_code == 403
    application = await client.post("/care/clinician",headers=headers(1),json={"display_name":"Test doctor","registration_number":"TEST-ONLY","council":"Synthetic council","specialty":"General medicine"})
    assert application.status_code == 201 and application.json()["verified"] is False
    assert (await client.post("/care/grants/accept",headers=headers(1),json=body)).status_code == 403
    async with factory() as db:
        await db.execute(update(Clinician).where(Clinician.account_id==ACTORS[1]).values(verified=True));await db.commit()
    assert (await client.post("/care/grants/accept",headers=headers(1),json=body)).status_code == 200
    path=f"/care/patients/{patient}/allergies"
    assert (await client.post(path,headers=headers(1),json={**PAYLOADS['allergies'],"status":"confirmed"})).status_code == 201
    async with factory() as db:
        await db.execute(update(Clinician).where(Clinician.account_id==ACTORS[1]).values(verified=False));await db.commit()
    assert (await client.get(path,headers=headers(1))).status_code == 404
    ordinary = await share(client,patient,"medications")
    assert (await client.post("/care/grants/accept",headers=headers(2),json={"token":ordinary['token']})).status_code == 200
    async with factory() as db:
        await db.execute(update(Grant).where(Grant.id==uuid.UUID(ordinary['id'])).values(expires_at=datetime.now(UTC)-timedelta(seconds=1)));await db.commit()
    assert (await client.get(f"/care/patients/{patient}/medications",headers=headers(2))).status_code == 404


async def test_child_authority_and_adulthood(context):
    client, factory=context
    patient=await profile(client,child=True)
    path=f"/care/patients/{patient}/medications"
    assert (await client.get(path,headers=headers())).status_code == 404
    async with factory() as db:
        await db.execute(update(Patient).where(Patient.id==uuid.UUID(patient)).values(guardian_verified=True));await db.commit()
    assert (await client.post(path,headers=headers(),json=MED)).status_code == 201
    assert (await client.get(path,headers=headers(1))).status_code == 404
    async with factory() as db:
        await db.execute(update(Patient).where(Patient.id==uuid.UUID(patient)).values(birth_date=date(2000,1,1)));await db.commit()
    assert (await client.get(path,headers=headers())).status_code == 404


async def test_document_scope_cannot_leak_uploaded_child_files(context, tmp_path):
    client,factory=context
    adult=await profile(client)
    child=await profile(client,child=True)
    rid=uuid.uuid4()
    async with factory() as db:
        db.add(Report(id=rid,owner_id=ACTORS[0],patient_id=uuid.UUID(child),original_filename="child.pdf",storage_path=str(tmp_path/'file'),mime_type="application/pdf",parsed_status="complete",uploaded_at=datetime.now(UTC)))
        await db.flush()
        db.add(ReportValue(owner_id=ACTORS[0],report_id=rid,test_name="Private child result",value_numeric=10,created_at=datetime.now(UTC)))
        db.add(TimelineEvent(owner_id=ACTORS[0],source_report_id=rid,test_name="Private child result",value_numeric=10,date_of_test=date.today(),created_at=datetime.now(UTC)))
        await db.commit()
    assert (await client.get('/reports',headers=headers())).json()==[]
    assert (await client.get('/timeline',headers=headers())).json()==[]
    assert (await client.get(f'/reports/{rid}?patient_id={adult}',headers=headers())).status_code==404
    for suffix in ('','/file'):
        assert (await client.get(f'/reports/{rid}{suffix}?patient_id={child}',headers=headers())).status_code==404
    assert (await client.delete(f'/reports/{rid}?patient_id={child}',headers=headers())).status_code==404
    assert (await client.post(f'/reports/{rid}/retry?patient_id={child}',headers=headers())).status_code==404
    assert (await client.post(f'/qa?patient_id={child}',headers=headers(),json={"question":"Explain the result"})).status_code==404
    async with factory() as db:
        await db.execute(update(Patient).where(Patient.id==uuid.UUID(child)).values(guardian_verified=True));await db.commit()
    assert len((await client.get(f'/reports?patient_id={child}',headers=headers())).json())==1
    assert len((await client.get(f'/timeline?patient_id={child}',headers=headers())).json())==1
    grant=await share(client,child,'documents')
    assert (await client.post('/care/grants/accept',headers=headers(1),json={'token':grant['token']})).status_code==200
    assert (await client.get(f'/reports/{rid}?patient_id={child}',headers=headers(1))).status_code==200
    await client.delete(f"/care/patients/{child}/grants/{grant['id']}",headers=headers())
    assert (await client.get(f'/reports/{rid}?patient_id={child}',headers=headers(1))).status_code==404


async def test_server_does_not_accept_self_asserted_authority(context):
    client,_=context
    response=await client.post('/care/patients',headers=headers(),json={'display_name':'Test','birth_date':'2020-01-01','relationship':'child','guardian_verified':True})
    assert response.status_code==422
    response=await client.post('/care/clinician',headers=headers(),json={'display_name':'Test','registration_number':'Test','council':'Test','specialty':'Test','verified':True})
    assert response.status_code==422
    patient=await profile(client)
    response=await client.post(f'/care/patients/{patient}/allergies',headers=headers(),json={**PAYLOADS['allergies'],'status':'confirmed'})
    assert response.status_code==403


async def test_recipient_revocation_is_patient_scoped_and_audited(context):
    client, _ = context
    patient = await profile(client)
    # A second patient has a different owner and shares with the same recipient.
    response = await client.post('/care/patients', headers=headers(3), json={
        'display_name': 'Other synthetic patient', 'birth_date': '1990-01-01', 'relationship': 'self'})
    assert response.status_code == 201
    other_patient = response.json()['id']
    response = await client.post(f'/care/patients/{other_patient}/grants', headers=headers(3), json={
        'label': 'Separate patient', 'recipient_kind': 'caregiver', 'scopes': ['documents'],
        'expires_at': (datetime.now(UTC) + timedelta(days=1)).isoformat()})
    assert response.status_code == 201
    assert (await client.post('/care/grants/accept', headers=headers(1), json={
        'token': response.json()['token']})).status_code == 200

    selected = []
    for scope in ('documents', 'medications'):
        grant = await share(client, patient, scope)
        selected.append(grant['id'])
        assert (await client.post('/care/grants/accept', headers=headers(1), json={
            'token': grant['token']})).status_code == 200
    remaining = await share(client, patient, 'documents')
    assert (await client.post('/care/grants/accept', headers=headers(2), json={
        'token': remaining['token']})).status_code == 200
    pending = await share(client, patient, 'documents')

    path = f'/care/patients/{patient}/recipients/{ACTORS[1]}/grants'
    # A recipient cannot revoke another person's permissions or manage their own grant.
    assert (await client.delete(path, headers=headers(1))).status_code == 404
    assert (await client.delete(path, headers=headers(2))).status_code == 404
    assert (await client.delete(
        f'/care/patients/{other_patient}/recipients/{ACTORS[1]}/grants', headers=headers())).status_code == 404
    response = await client.delete(path, headers=headers())
    assert response.status_code == 200 and response.json()['revoked_count'] == 2
    assert (await client.get(f'/reports?patient_id={patient}', headers=headers(1))).status_code == 404
    assert (await client.get(f'/care/patients/{patient}/medications', headers=headers(1))).status_code == 404
    assert (await client.get(f'/reports?patient_id={patient}', headers=headers(2))).status_code == 200
    assert (await client.get(f'/reports?patient_id={other_patient}', headers=headers(1))).status_code == 200
    grants = (await client.get(f'/care/patients/{patient}/grants', headers=headers())).json()
    assert next(g for g in grants if g['id'] == pending['id'])['revoked_at'] is None
    events = (await client.get(f'/care/patients/{patient}/audit', headers=headers())).json()
    assert {e['resource_id'] for e in events if e['action'] == 'consent.revoked'} == set(selected)
    assert (await client.delete(path, headers=headers())).json()['revoked_count'] == 0


async def prescription_fixture(client, factory):
    patient = await profile(client)
    report_id = uuid.uuid4()
    async with factory() as db:
        db.add(Report(id=report_id, owner_id=ACTORS[0], patient_id=uuid.UUID(patient),
            original_filename='fictional-prescription.png', storage_path='synthetic-test-only',
            mime_type='image/png', document_kind='prescription', parsed_status='complete',
            extracted_text='1. Examplemed Alpha 250 mg tablet\nInstruction: one tablet daily for 5 days',
            uploaded_at=datetime.now(UTC)))
        await db.commit()
    path = f'/reports/{report_id}/prescription-review?patient_id={patient}'
    body = {'confirm_review':True, 'document_date':'2024-01-14',
        'medications':[{'name':'Reviewed Examplemed 250 mg tablet','schedule':'as on original'}]}
    return patient, report_id, path, body


async def test_prescription_review_atomic_source_linked_and_repeat_safe(context):
    client, factory = context
    patient, report_id, path, body = await prescription_fixture(client, factory)
    assert (await client.get(path, headers=headers(1))).status_code == 404
    assert (await client.post(path, headers=headers(1), json=body)).status_code == 404
    draft = (await client.get(path, headers=headers())).json()
    assert len(draft['candidates']) == 1 and draft['reviewed'] is False
    assert draft['candidates'][0]['dose'] == ''
    assert (await client.post(path, headers=headers(), json={**body,'confirm_review':False})).status_code == 422
    assert (await client.post(path, headers=headers(), json={**body,'medications':body['medications']*2})).status_code == 422
    response = await client.post(path, headers=headers(), json=body)
    assert response.status_code == 201, response.text
    assert response.json()['saved_count'] == 1
    assert (await client.post(path, headers=headers(), json=body)).status_code == 409
    medicines = (await client.get(f'/care/patients/{patient}/medications', headers=headers())).json()
    assert len(medicines) == 1
    assert medicines[0]['source_report_id'] == str(report_id)
    assert medicines[0]['source'] == 'prescription' and medicines[0]['status'] == 'unknown'
    assert medicines[0]['name'] == body['medications'][0]['name']
    async with factory() as db:
        review = await db.get(PrescriptionReview, report_id)
        assert review.reviewed_by == ACTORS[0] and len(review.approved_fields) == 1
        report = await db.get(Report, report_id)
        assert report.document_date == date(2024,1,14)
    summary = (await client.get(f'/care/patients/{patient}/summary',headers=headers())).json()
    assert summary['sections']['medications'][0]['id'] == medicines[0]['id']


async def test_prescription_review_needs_both_document_and_medication_permissions(context):
    client, factory = context
    patient, report_id, path, body = await prescription_fixture(client, factory)
    async def accept(scope, write):
        grant = await share(client,patient,scope,write=write)
        assert (await client.post('/care/grants/accept',headers=headers(1),json={'token':grant['token']})).status_code == 200
        return grant
    docs = await accept('documents',False)
    assert (await client.get(path,headers=headers(1))).status_code == 404
    await accept('medications',True)
    assert (await client.get(path,headers=headers(1))).status_code == 200
    assert (await client.post(path,headers=headers(1),json=body)).status_code == 404
    writable = await accept('documents',True)
    assert (await client.delete(f"/care/patients/{patient}/grants/{writable['id']}",headers=headers())).status_code == 204
    assert (await client.post(path,headers=headers(1),json=body)).status_code == 404
    await accept('documents',True)
    assert (await client.post(path,headers=headers(1),json=body)).status_code == 201


async def test_prescription_review_validates_all_rows_before_saving(context):
    client, factory = context
    patient, report_id, path, body = await prescription_fixture(client, factory)
    invalid = {**body, 'medications':body['medications']+[{'name':'','start_date':'2024-02-01','end_date':'2024-01-01'}]}
    assert (await client.post(path, headers=headers(),json=invalid)).status_code == 422
    assert (await client.get(f'/care/patients/{patient}/medications',headers=headers())).json() == []
    async with factory() as db:
        assert await db.get(PrescriptionReview,report_id) is None
        await db.execute(update(Report).where(Report.id==report_id).values(parsed_status='processing'))
        await db.commit()
    assert (await client.post(path,headers=headers(),json=body)).status_code == 409
