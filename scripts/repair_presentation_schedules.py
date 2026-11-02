"""Repair only missing schedules in the named synthetic presentation fixtures.

Uses normal versioned record updates so the original approval and correction
history remain visible. Existing nonempty user edits are never overwritten.
"""
import json
from dotenv import dotenv_values
from seed_presentation import ROOT, STATE, BASE, ORIGIN
from smoke_local import check
import httpx


def main():
    cfg=dotenv_values(ROOT/'.env.local')
    assert (cfg.get('POSTGRES_HOST'),cfg.get('POSTGRES_PORT'))==('127.0.0.1','54329')
    state=json.loads(STATE.read_text())
    updates=0
    fields=('name','dose','schedule','status','source','start_date','end_date','notes','source_report_id')
    for role in ['patient','backup']:
        account=state[role];pid=account['items']['patient'];rid=account['items']['prescription']
        with httpx.Client(base_url=BASE,headers={'Origin':ORIGIN},trust_env=False,timeout=45) as c:
            check(c.post('/auth/login',json={k:account[k] for k in ('email','password')}),200)
            draft=check(c.get(f'/reports/{rid}/prescription-review',params={'patient_id':pid}),200)
            expected={r['name']:r['schedule'] for r in draft['candidates']}
            assert expected=={'Examplemed Alpha 250 mg tablet':'one tablet daily for 5 days (fictional)',
                              'Examplemed Beta 10 mg tablet':'one tablet at night for 3 days (fictional)'}
            prefix=f'/care/patients/{pid}/medications'
            for row in check(c.get(prefix),200):
                if row['source_report_id']!=rid or row['name'] not in expected or row['schedule']:
                    continue
                body={k:row[k] for k in fields}
                body['schedule']=expected[row['name']]
                body['notes']+='\nInstruction restored from the reviewed original after OCR paragraph-spacing correction.'
                revised=check(c.put(prefix+'/'+row['id'],headers={'If-Match':str(row['version'])},json=body),200)
                assert revised['schedule']==expected[row['name']] and revised['version']==row['version']+1
                assert check(c.get(prefix+'/'+row['id']+'/history'),200)['previous']
                updates+=1
            check(c.post('/auth/logout'),204)
    print(f'PASS: {updates} missing fixture schedules corrected through audited, versioned API updates.')


if __name__=='__main__':main()
