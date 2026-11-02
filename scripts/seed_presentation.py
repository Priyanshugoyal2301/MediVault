"""Resumable synthetic presentation accounts. Uses real local APIs, never mock UI data.

Private credentials and resume IDs are kept under .local-logs. Re-running preserves
existing records and creates only missing fixtures. The backup is an independent
account, not a replacement for database/disaster-recovery backups.
"""
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from dotenv import dotenv_values
from prototype_walkthrough import verify_fixture
from smoke_local import ORIGIN, check, wait_report, stored_original

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.local-logs/presentation-state.json'
DOCS=ROOT/'output/pdf/presentation'
BASE=ORIGIN  # Exercise the web server's real API proxy too.
NOTE='Fictional presentation record; not a real medical event or instruction.'
state={}


def save():
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')


def account(role):
    a=state.setdefault(role,{'email':f"presentation-{role}-{state['tag']}@example.com",
                             'password':'Demo-'+secrets.token_urlsafe(18),'items':{}})
    save()
    c=httpx.Client(base_url=BASE,headers={'Origin':ORIGIN},timeout=130,trust_env=False)
    login=c.post('/auth/login',json={k:a[k] for k in ('email','password')})
    if login.status_code==401:
        check(c.post('/auth/register',json={k:a[k] for k in ('email','password')}),201)
    else: check(login,200)
    a['account_id']=check(c.get('/auth/me'),200)['id'];save()
    return c,a


def once(a,key,fn):
    if key not in a['items']:
        a['items'][key]=fn();save()
    return a['items'][key]


def profile(c,a,key,body):
    return once(a,key,lambda:check(c.post('/care/patients',json=body),201)['id'])


def upload(c,a,key,pid,filename,kind):
    file=DOCS/filename
    rid=once(a,key,lambda:check(c.post('/reports',params={'patient_id':pid},
        files={'file':(filename,file.read_bytes(),'image/png' if file.suffix=='.png' else 'application/pdf')},
        data={'document_kind':kind}),202)['id'])
    detail=wait_report(c,pid,rid)
    downloaded=c.get(f'/reports/{rid}/file',params={'patient_id':pid})
    assert downloaded.status_code==200 and downloaded.content==file.read_bytes()
    stored_original(rid,file.read_bytes())
    return rid,detail


def review(c,pid,rid,names,date,status):
    path=f'/reports/{rid}/prescription-review?patient_id={pid}'
    draft=check(c.get(path),200)
    assert [r['name'] for r in draft['candidates']]==names, draft['candidates']
    schedules={'Examplemed Alpha 250 mg tablet':'one tablet daily for 5 days (fictional)',
        'Examplemed Beta 10 mg tablet':'one tablet at night for 3 days (fictional)',
        'Examplemed Delta 5 mg tablet':'one tablet in the evening for 3 days (fictional)'}
    assert all(r['schedule']==schedules[r['name']] for r in draft['candidates']), draft['candidates']
    if not draft['reviewed']:
        body={'confirm_review':True,'document_date':date,'medications':[
            {'name':r['name'],'schedule':r['schedule'],'dose':'one tablet (fictional)',
             'status':status,'start_date':date,'notes':NOTE} for r in draft['candidates']]}
        assert check(c.post(path,json=body),201)['saved_count']==len(names)
        check(c.post(path,json=body),409)


def record(c,a,pid,scope,key,body):
    return once(a,key,lambda:check(c.post(f'/care/patients/{pid}/{scope}',json=body),201)['id'])


def populate(role):
    c,a=account(role)
    pid=profile(c,a,'patient',{'display_name':'Aarav Sharma (demo)','birth_date':'1990-04-18','relationship':'self'})
    child=profile(c,a,'child',{'display_name':'Mira Sharma (demo)','birth_date':'2020-03-02','relationship':'child'})
    once(a,'guardian_verified',lambda:(verify_fixture('guardian',child,a['account_id']) or True))
    for key,file,names,day,status in [
        ('prescription','aarav-prescription-2026-10-15.png',['Examplemed Alpha 250 mg tablet','Examplemed Beta 10 mg tablet'],'2026-10-15','stopped'),
        ('followup','aarav-followup-2026-10-22.pdf',['Examplemed Delta 5 mg tablet'],'2026-10-22','unknown')]:
        rid,detail=upload(c,a,key,pid,file,'prescription')
        review(c,pid,rid,names,day,status)
    for key,file in [('lab_september','aarav-labs-2026-09-15.pdf'),('lab_october','aarav-labs-2026-10-20.pdf')]:
        upload(c,a,key,pid,file,'report')
    upload(c,a,'child_visit_document',child,'mira-child-visit-2026-10-18.pdf','other')
    record(c,a,pid,'allergies','reaction',{'substance':'Examplemed Gamma (fictional)',
        'reaction':'Patient-reported itchy rash after an earlier fictional course','severity':'mild','status':'reported','occurred_on':'2026-09-01','notes':NOTE+' Not clinician-confirmed.'})
    for day,reason in [('2026-09-15','Routine wellness review'),('2026-10-15','Review of previous reports and reported reaction'),('2026-10-22','Follow-up and medication reconciliation')]:
        record(c,a,pid,'encounters','visit_'+day,{'occurred_on':day,'facility':'Cedar Grove Demonstration Clinic',
            'clinician':'Dr Kavya Mehta (fictional)','reason':reason,'notes':NOTE,'follow_up':'2026-11-04'})
    record(c,a,pid,'appointments','appointment',{'scheduled_at':(datetime.now(UTC)+timedelta(days=9)).isoformat(),
        'facility':'Cedar Grove Demonstration Clinic','clinician':'Dr Kavya Mehta (fictional)',
        'purpose':'Bring the consultation summary and original reports','status':'planned','notes':NOTE+' Not booked with a real clinic.'})
    record(c,a,pid,'referrals','referral',{'facility':'Cedar Grove Nutrition Desk (fictional)',
        'reason':'Example referral to demonstrate care coordination','issued_on':'2026-10-22','valid_until':'2026-12-31','status':'issued','notes':NOTE})
    record(c,a,pid,'claims','claim',{'facility':'Cedar Grove Demonstration Clinic','scheme':'Demo Employee Health Plan',
        'reference':'DEMO-CLAIM-1020','amount_rupees':'1450.00','submitted_on':'2026-10-22','status':'preparing','notes':NOTE+' Not submitted to an insurer.'})
    record(c,a,pid,'benefits','benefit',{'scheme':'Demo Employee Health Plan','member_reference':'DEMO-MEMBER-001',
        'valid_until':'2027-03-31','contact':'Demonstration help desk - no real contact','notes':NOTE+' Not a CGHS entitlement or valid insurance card.'})
    record(c,a,pid,'vaccinations','adult_vaccine',{'name':'Demo adult vaccination entry','dose':'Historical fixture entry',
        'administered_on':'2025-10-01','facility':'Cedar Grove Demonstration Clinic','notes':NOTE})
    record(c,a,child,'vaccinations','child_vaccine',{'name':'Demo childhood vaccination entry','dose':'Historical fixture entry',
        'administered_on':'2025-03-02','facility':'Cedar Grove Demonstration Clinic','notes':NOTE+' Not a vaccination schedule recommendation.'})
    record(c,a,child,'encounters','child_encounter',{'occurred_on':'2026-10-18','facility':'Cedar Grove Demonstration Clinic',
        'clinician':'Dr Kavya Mehta (fictional)','reason':'Routine child record review','notes':NOTE})
    # Verify every organizer reads back from the API and the two panels form a real trend.
    counts={}
    for scope in ['medications','allergies','encounters','appointments','referrals','claims','benefits','vaccinations']:
        rows=check(c.get(f'/care/patients/{pid}/{scope}'),200);assert rows
        counts[scope]=len(rows)
    timeline=check(c.get('/timeline',params={'patient_id':pid}),200)
    assert len(timeline)==8 and all(r['data_point_count']==2 for r in timeline),timeline
    history=check(c.get('/timeline/Haemoglobin',params={'patient_id':pid}),200)
    assert sorted(r['value_numeric'] for r in history)==[13.2,13.6],history
    answer=check(c.post('/qa',params={'patient_id':pid},json={'question':'What does haemoglobin mean?','locale':'en-IN'}),200)
    assert answer['answer'] and answer['citations']
    summary=check(c.get(f'/care/patients/{pid}/summary'),200)
    assert len(summary['sections']['medications'])==3
    assert check(c.get(f'/care/patients/{pid}/audit'),200)
    print(f'PASS {role}: five uploads, OCR/review, eight care sections, eight two-point lab trends, explanations, summary and audit',flush=True)
    return c,a,counts


def main():
    global state
    cfg=dotenv_values(ROOT/'.env.local')
    if (cfg.get('POSTGRES_HOST'),cfg.get('POSTGRES_PORT'),cfg.get('POSTGRES_DB'))!=('127.0.0.1','54329','medivault'):
        raise SystemExit('Only the isolated local prototype database is supported.')
    state=json.loads(STATE.read_text()) if STATE.exists() else {'tag':uuid.uuid4().hex[:8]}
    patient,a,counts=populate('patient')
    backup,b,backup_counts=populate('backup')
    doctor,d=account('doctor')
    once(d,'clinician',lambda:check(doctor.post('/care/clinician',json={'display_name':'Dr Kavya Mehta (demo)',
        'registration_number':'FICTIONAL-NOT-A-LICENCE','council':'Demo verification only','specialty':'General care demonstration'}),201))
    once(d,'verified',lambda:(verify_fixture('clinician',d['account_id'],d['account_id']) or True))
    pid=a['items']['patient'];prefix=f'/care/patients/{pid}'
    if 'doctor_grant' not in a['items']:
        check(doctor.get(prefix+'/summary'),404)
        grant=check(patient.post(prefix+'/grants',json={'label':'Dr Kavya - presentation read-only',
            'recipient_kind':'doctor','scopes':['documents','medications','allergies','encounters'],
            'can_write':False,'expires_at':(datetime.now(UTC)+timedelta(days=89)).isoformat()}),201)
        check(doctor.post('/care/grants/accept',json={'token':grant['token']}),200)
        a['items']['doctor_grant']=grant['id'];save()
    check(doctor.get(prefix+'/summary'),200)
    check(doctor.post(prefix+'/medications',json={'name':'Unauthorized test'}),404)
    check(doctor.get(f"/care/patients/{a['items']['child']}/summary"),404)
    check(backup.get(prefix+'/summary'),404)
    with httpx.Client(base_url=BASE,trust_env=False) as anonymous: check(anonymous.get(prefix+'/summary'),401)
    lines=['# MediVault presentation accounts','',f'Application: {ORIGIN}/','',
        'All records are fictional. MFA is intentionally not enrolled on these demo accounts.',
        'Use Patient for the presentation. Backup contains its own independent copy of the scenario.',
        'The backup is not shared with the doctor; keep it untouched until needed.','']
    for role in ['patient','backup','doctor']:
        v=state[role];lines += [f'## {role.title()}',f"Email: {v['email']}",f"Password: {v['password']}",'']
    lines += ['Doctor consent lasts 89 days from creation. Renew explicitly through Sharing & privacy if needed.',
        'Local operator approvals cover these fictional identities only.',
        'Re-run scripts/seed_presentation.py to resume missing fixture setup; it does not reset edited records.',
        'Do not publish this file or reuse its passwords. Preserve .env.local and the Docker volume.',
        'This independent backup account does not protect against database or encryption-key loss.']
    (ROOT/'.local-logs/PRESENTATION_ACCOUNTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    for c in [patient,backup,doctor]: check(c.post('/auth/logout'),204);c.close()
    result={'date':datetime.now(UTC).isoformat(),'synthetic_only':True,'result':'passed',
        'patient_record_counts':counts,'backup_record_counts':backup_counts,'documents_per_account':5,
        'checks':['real image OCR','PDF lab extraction','editable draft source accuracy','explicit approval',
            'duplicate review rejection','download byte equality','encrypted original storage','all care section persistence',
            'two-point lab history','cited plain-language answer','consultation summary','access audit',
            'doctor consent','doctor write denial','child isolation','backup isolation','anonymous denial'],
        'browser_checks':'recorded separately; not implied by API success'}
    (ROOT/'validation/presentation_acceptance_latest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PASS: presentation, independent backup and read-only doctor ready. Credentials: .local-logs/PRESENTATION_ACCOUNTS.md',flush=True)


if __name__=='__main__': main()
