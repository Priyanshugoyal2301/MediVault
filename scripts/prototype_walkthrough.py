"""Create a local, fictional demonstration and verify the central patient journey.

Uses normal APIs for accounts, uploads, review, records and sharing. The only
operator action is clearly labelled synthetic doctor/guardian verification in
the isolated development database. Never run this against real patient data.
Credentials are written only to the ignored .local-logs directory.
"""
import json
from pathlib import Path
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from dotenv import dotenv_values
from smoke_local import BASE, ORIGIN, check, database_connection, wait_report

ROOT = Path(__file__).resolve().parents[1]


def verify_fixture(kind, subject, actor):
    with database_connection() as connection, connection.cursor() as cursor:
        if kind == 'clinician':
            cursor.execute('UPDATE clinicians SET verified = true WHERE account_id = %s', (subject,))
        else:
            cursor.execute('UPDATE patients SET guardian_verified = true WHERE id = %s AND created_by = %s', (subject,actor))
        assert cursor.rowcount == 1
        cursor.execute('INSERT INTO verification_decisions (id,subject_id,subject_kind,operator,evidence_reference,approved,occurred_at) VALUES (%s,%s,%s,%s,%s,true,%s)',
            (str(uuid.uuid4()),subject,kind,'local-prototype-fixture','FICTIONAL SOFTWARE DEMO ONLY; not real identity verification',datetime.now(UTC)))


def main():
    settings = dotenv_values(ROOT/'.env.local')
    if settings.get('POSTGRES_HOST') != '127.0.0.1' or settings.get('POSTGRES_PORT') != '54329' or settings.get('POSTGRES_DB') != 'medivault':
        raise SystemExit('This script only supports the documented isolated local prototype database.')
    tag = uuid.uuid4().hex[:8]
    password = 'Demo-only-'+secrets.token_urlsafe(18)
    credentials = []
    with httpx.Client(base_url=BASE,headers={'Origin':ORIGIN},timeout=130,trust_env=False) as patient_client, httpx.Client(base_url=BASE,headers={'Origin':ORIGIN},timeout=30,trust_env=False) as doctor:
        for role,client in [('patient',patient_client),('doctor',doctor)]:
            email = f'prototype-{role}-{tag}@example.com'
            check(client.post('/auth/register',json={'email':email,'password':password}),201)
            identity = check(client.get('/auth/me'),200)
            credentials.append(dict(role=role,email=email,password=password,id=identity['id']))
        owner = patient_client
        patient = check(owner.post('/care/patients',json={'display_name':'Aarav Demo (fictional)','birth_date':'1990-01-01','relationship':'self'}),201)['id']
        child = check(owner.post('/care/patients',json={'display_name':'Mira Demo (fictional child)','birth_date':'2020-01-01','relationship':'child'}),201)['id']
        verify_fixture('guardian',child,credentials[0]['id'])
        check(doctor.post('/care/clinician',json={'display_name':'Dr Demo (fictional)','registration_number':'DEMO-NOT-A-REAL-LICENCE','council':'Fictional demo only','specialty':'Prototype reviewer'}),201)
        verify_fixture('clinician',credentials[1]['id'],credentials[1]['id'])
        file = ROOT/'apps/web/public/test-documents/prescription-clear.png'
        prescription = check(owner.post('/reports',params={'patient_id':patient},files={'file':(file.name,file.read_bytes(),'image/png')},data={'document_kind':'prescription'}),202)
        wait_report(owner,patient,prescription['id'])
        path = f"/reports/{prescription['id']}/prescription-review?patient_id={patient}"
        draft = check(owner.get(path),200)
        assert len(draft['candidates']) == 2
        assert all(c['status']=='unknown' and c['dose']=='' for c in draft['candidates'])
        # This script knows the fictional ground truth; an end user uses the review UI.
        expected = ['Examplemed Alpha 250 mg tablet','Examplemed Beta 10 mg tablet']
        assert [c['name'] for c in draft['candidates']] == expected
        body = {'confirm_review':True,'document_date':'2024-01-14','medications':[
            {'name':c['name'],'schedule':c['schedule'],'status':'unknown'} for c in draft['candidates']]}
        review = check(owner.post(path,json=body),201)
        assert review['saved_count'] == 2
        check(owner.post(path,json=body),409)
        prefix = f'/care/patients/{patient}'
        saved = check(owner.get(prefix+'/medications'),200)
        assert len(saved)==2 and all(m['source_report_id']==prescription['id'] for m in saved)
        check(owner.post(prefix+'/allergies',json={'substance':'Examplemed Gamma (fictional)','reaction':'Reported fictional rash','severity':'unknown','status':'reported'}),201)
        check(owner.post(prefix+'/encounters',json={'occurred_on':'2024-01-14','facility':'Fictional Demo Clinic','clinician':'Dr Demo (fictional)','reason':'Demonstration visit; not a real medical encounter','notes':'Use original documents to verify every detail.'}),201)
        lab = ROOT/'apps/web/public/test-documents/lab-report.pdf'
        report = check(owner.post('/reports',params={'patient_id':patient},files={'file':(lab.name,lab.read_bytes(),'application/pdf')},data={'document_kind':'report'}),202)
        wait_report(owner,patient,report['id'])
        summary = check(owner.get(prefix+'/summary'),200)
        assert len(summary['sections']['medications'])==2 and len(summary['sections']['allergies'])==1
        check(doctor.get(prefix+'/summary'),404)
        grant = check(owner.post(prefix+'/grants',json={'label':'Dr Demo consultation (fictional)','recipient_kind':'doctor','scopes':['documents','medications','allergies','encounters'],'can_write':False,'expires_at':(datetime.now(UTC)+timedelta(days=7)).isoformat()}),201)
        check(doctor.post('/care/grants/accept',json={'token':grant['token']}),200)
        assert len(check(doctor.get(prefix+'/summary'),200)['sections']['medications'])==2
        check(doctor.post(path,json=body),404)
        child_profiles = check(owner.get('/care/patients'),200)
        assert any(p['id']==child and 'documents' in p['scopes'] for p in child_profiles)
        for client in (owner,doctor): check(client.post('/auth/logout'),204)
    output = ROOT/'.local-logs/PROTOTYPE_ACCESS.md'
    output.parent.mkdir(exist_ok=True)
    lines = ['# Local fictional prototype accounts','',
             'These accounts contain synthetic information only. Do not use these credentials elsewhere.',
             'Open http://127.0.0.1:3000. MFA is not enabled on these demonstration accounts.','']
    for account in credentials:
        lines += [f"## {account['role'].title()}",f"Email: {account['email']}",f"Password: {account['password']}",'']
    lines += ['Patient account: inspect Documents, Medications, Allergies, Visit timeline and Consultation summary.',
              'Upload the downloadable sample prescription to demonstrate review yourself; do not save duplicate medicines unless intentionally demonstrating a new course.',
              'Doctor account: the fictional adult profile is shared read-only. Child records are not shared.',
              'Guardian and clinician verification were seeded by this local operator script for fictional identities only.']
    output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    results = {'synthetic_only':True,'checks':['real image OCR','draft candidates','explicit approval','duplicate submission rejected',
        'source-linked medicine persistence','consultation summary','doctor denial before consent','doctor read-only access after consent','child isolation'],
        'saved_medications':2,'result':'passed'}
    (ROOT/'validation/prototype_walkthrough_latest.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print('PASS: upload -> OCR -> review -> saved medicines -> consultation -> scoped doctor access',flush=True)
    print(f'Local demonstration login details saved privately to {output}',flush=True)


if __name__ == '__main__':
    main()
