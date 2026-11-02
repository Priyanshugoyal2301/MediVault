"""Evaluate actual upload -> queue -> extraction -> private retrieval, per fixture."""
import json
import mimetypes
from pathlib import Path
import re
import time
import uuid
import httpx

from smoke_local import BASE, ORIGIN, check, stored_original

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT/'apps/web/public/test-documents'


def main():
    results = []
    with httpx.Client(base_url=BASE, headers={'Origin':ORIGIN}, timeout=60, trust_env=False) as client:
        tag = uuid.uuid4().hex
        check(client.post('/auth/register', json={'email':f'acceptance-{tag}@example.com','password':'Synthetic-only-'+tag}),201)
        patient = check(client.post('/care/patients',json={'display_name':'Synthetic acceptance profile','birth_date':'1990-01-01','relationship':'self'}),201)['id']
        for case in json.loads((FIXTURES/'manifest.json').read_text()):
            started = time.monotonic()
            errors = []
            original = (FIXTURES/case['file']).read_bytes()
            report = check(client.post('/reports',params={'patient_id':patient},
                files={'file':(case['file'],original,mimetypes.guess_type(case['file'])[0])},
                data={'document_kind':case['kind']}),202)
            deadline = time.monotonic()+180
            while True:
                detail = check(client.get(f"/reports/{report['id']}",params={'patient_id':patient}),200)
                if detail['parsed_status'] in ('complete','failed') or time.monotonic()>deadline: break
                time.sleep(.5)
            if detail['parsed_status'] != case['expected']: errors.append('unexpected processing status')
            normalize = lambda s: ' '.join(re.findall(r'[a-z0-9]+',s.lower()))
            for fragment in case.get('fragments',[]):
                if normalize(fragment) not in normalize(detail.get('extracted_text') or ''): errors.append('missing expected fragment: '+fragment)
            for name,value in case.get('values',{}).items():
                if not any(v['test_name']==name and v['value_numeric']==value for v in detail['values']): errors.append('incorrect laboratory value: '+name)
            download = client.get(f"/reports/{report['id']}/file",params={'patient_id':patient})
            if download.status_code != 200 or download.content != original: errors.append('original download mismatch')
            stored_original(report['id'],original)
            results.append(dict(file=case['file'],kind=case['kind'],passed=not errors,
                status=detail['parsed_status'],seconds=round(time.monotonic()-started,2),errors=errors))
            print(('PASS' if not errors else 'FAIL')+f": {case['file']} ({case['kind']})",flush=True)
        check(client.post('/auth/logout'),204)
    target = ROOT/'validation/document_acceptance_latest.json'
    target.write_text(json.dumps({'synthetic_only':True,'cases':results},indent=2),encoding='utf-8')
    print(f'{sum(r["passed"] for r in results)}/{len(results)} cases passed; results: {target}',flush=True)
    if any(not r['passed'] for r in results): raise SystemExit(1)


if __name__ == '__main__':
    main()
