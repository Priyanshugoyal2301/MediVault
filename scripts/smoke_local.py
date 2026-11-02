"""Exercise the running local stack using synthetic accounts and documents.

No browser automation, external messages, patient data, or production service calls.
Synthetic accounts remain in the isolated development database for inspection.
"""
import asyncio
import io
from pathlib import Path
import time
import uuid
import re

import fitz
import httpx
from PIL import Image, ImageDraw, ImageFont

BASE="http://127.0.0.1:8000"
ORIGIN="http://127.0.0.1:3000"


def database_connection():
    import psycopg2
    from dotenv import dotenv_values
    config = dotenv_values(Path(__file__).resolve().parents[1] / '.env.local')
    return psycopg2.connect(host=config['POSTGRES_HOST'], port=config['POSTGRES_PORT'],
        dbname=config['POSTGRES_DB'], user=config['POSTGRES_USER'], password=config['POSTGRES_PASSWORD'])


def stored_original(report_id, original):
    with database_connection() as connection, connection.cursor() as cursor:
        cursor.execute('SELECT storage_path, extracted_text, patient_id FROM reports WHERE id = %s', (report_id,))
        path, extracted, patient = cursor.fetchone()
    stored = Path(path).read_bytes()
    assert stored.startswith(b'MEDIVAULT-ENC-1\n') and stored != original
    assert original[:40] not in stored
    assert patient is not None
    return Path(path), extracted


def check(response, status):
    assert response.status_code==status, f"{response.request.method} {response.request.url.path}: expected {status}, received {response.status_code}: {response.text[:300]}"
    return response.json() if response.content else None


def pdf_bytes():
    document=fitz.open()
    page=document.new_page()
    page.insert_text((72,72),"SYNTHETIC TEST REPORT - NOT A REAL PATIENT\nCollection Date: 14/01/2024\nHaemoglobin 13.5 g/dL 12.0 - 15.5\nTotal Cholesterol 215 mg/dL <200\nLDL Cholesterol 138 mg/dL <100\nFor software verification only.",fontsize=12)
    data=document.tobytes()
    document.close()
    return data


def prescription_image():
    image=Image.new("RGB",(1600,900),"white")
    draw=ImageDraw.Draw(image)
    font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",36)
    draw.multiline_text((60,70),"SYNTHETIC PRESCRIPTION - SOFTWARE TEST ONLY\n\nDate: 14 January 2024\nMedication: Example medicine\nDose: verify from original\nThis is not a clinical prescription.",fill="black",font=font,spacing=20)
    stream=io.BytesIO();image.save(stream,format="PNG")
    return stream.getvalue()


def wait_report(client, patient, report):
    deadline=time.monotonic()+100
    while time.monotonic()<deadline:
        detail=check(client.get(f"/reports/{report}?patient_id={patient}"),200)
        if detail['parsed_status'] in ('complete','failed'):
            assert detail['parsed_status']=='complete', "Document extraction failed"
            return detail
        time.sleep(1)
    raise AssertionError("Document worker did not complete in 100 seconds")


def main():
    tag=uuid.uuid4().hex[:12]
    password="Synthetic-local-only-"+tag
    with httpx.Client(base_url=BASE,headers={"Origin":ORIGIN},timeout=130) as owner, httpx.Client(base_url=BASE,headers={"Origin":ORIGIN},timeout=30) as other:
        for client,role in ((owner,'patient'),(other,'caregiver')):
            response=client.post('/auth/register',json={'email':f'smoke-{role}-{tag}@example.com','password':password})
            body=check(response,201)
            assert 'access_token' not in body
            cookie=response.headers.get('set-cookie','').lower()
            assert 'httponly' in cookie and 'samesite=strict' in cookie
            check(client.get('/auth/me'),200)
        print('PASS: registration, HttpOnly session and account lookup',flush=True)
        patient=check(owner.post('/care/patients',json={'display_name':'Synthetic smoke patient','birth_date':'1990-01-01','relationship':'self'}),201)['id']
        path=f'/care/patients/{patient}'
        check(other.get(path+'/medications'),404)
        check(owner.post(path+'/medications',headers={'Origin':'https://untrusted.example'},json={'name':'Test'}),403)
        assert httpx.get(BASE+'/reports',headers={'X-User-ID':patient,'X-Internal-Key':'forged'}).status_code in (401,403)
        print('PASS: cross-account denial, origin enforcement and forged identity denial',flush=True)
        original=pdf_bytes()
        report=check(owner.post('/reports',params={'patient_id':patient},files={'file':('synthetic-report.pdf',original,'application/pdf')},data={'document_kind':'report','document_date':'2024-01-14'}),202)
        detail=wait_report(owner,patient,report['id'])
        haemoglobin = next(value for value in detail['values'] if value['test_name']=='Haemoglobin')
        assert haemoglobin['value_numeric'] == 13.5 and haemoglobin['unit'] == 'g/dL'
        assert haemoglobin['explanation_en'] and haemoglobin['explanation_hi']
        original_path, _ = stored_original(report['id'], original)
        assert owner.get(f"/reports/{report['id']}/file?patient_id={patient}").content==original
        check(other.get(f"/reports/{report['id']}?patient_id={patient}"),404)
        history=check(owner.get('/timeline',params={'patient_id':patient}),200)
        assert any(item['latest_date']=='2024-01-14' for item in history)
        print('PASS: real PDF extraction, persisted test dates, private original download',flush=True)
        image=prescription_image()
        prescription=check(owner.post('/reports',params={'patient_id':patient},files={'file':('synthetic-prescription.png',image,'image/png')},data={'document_kind':'prescription'}),202)
        text=wait_report(owner,patient,prescription['id'])['extracted_text']
        expected = 'SYNTHETIC PRESCRIPTION SOFTWARE TEST ONLY Date 14 January 2024 Medication Example medicine Dose verify from original This is not a clinical prescription'
        words = lambda value: re.findall(r'[a-z0-9]+', value.lower())
        assert words(text) == words(expected), 'Prescription text differs from the known synthetic source'
        _, persisted_text = stored_original(prescription['id'], image)
        assert persisted_text == text
        medication=check(owner.post(path+'/medications',json={'name':'Example medicine','source':'prescription','source_report_id':prescription['id'],'status':'unknown'}),201)
        assert medication['status']=='unknown'
        print('PASS: image OCR and source-linked medication review without assuming current use',flush=True)
        expires=__import__('datetime').datetime.now(__import__('datetime').UTC)+__import__('datetime').timedelta(hours=1)
        grant=check(owner.post(path+'/grants',json={'label':'Synthetic recipient','recipient_kind':'caregiver','scopes':['documents'],'expires_at':expires.isoformat()}),201)
        check(other.post('/care/grants/accept',json={'token':grant['token']}),200)
        check(other.get(f"/reports/{report['id']}?patient_id={patient}"),200)
        check(other.get(path+'/medications'),404)
        check(owner.delete(path+f"/grants/{grant['id']}"),204)
        check(other.get(f"/reports/{report['id']}/file?patient_id={patient}"),404)
        check(owner.get(path+'/summary'),200)
        print('PASS: limited consent, download revocation and consultation summary',flush=True)
        answer=check(owner.post('/qa',params={'patient_id':patient},json={'question':'What is haemoglobin?','locale':'en-IN'}),200)
        assert answer['answer'] and not answer['safety_triggered']
        emergency=check(owner.post('/qa',params={'patient_id':patient},json={'question':'I have chest pain and difficulty breathing','locale':'en-IN'}),200)
        assert emergency['safety_triggered']
        check(owner.delete(f"/reports/{report['id']}?patient_id={patient}"),204)
        check(owner.get(f"/reports/{report['id']}?patient_id={patient}"),404)
        deadline = time.monotonic() + 15
        while original_path.exists() and time.monotonic() < deadline:
            time.sleep(0.25)
        assert not original_path.exists(), 'Deleted document original was not removed by the cleanup worker'
        print('PASS: grounded explanation, safety response and document deletion',flush=True)
        session=owner.cookies.get('medivault_session')
        check(owner.post('/auth/logout'),204)
        check(httpx.get(BASE+'/care/patients',headers={'Cookie':f'medivault_session={session}'}),401)
        print('PASS: logout invalidates captured session replay',flush=True)
    print('Local full-stack smoke checks passed. Only synthetic data was used.',flush=True)


if __name__=='__main__':
    main()
