"""Clinic-style fictional documents; run with a Python environment with reportlab."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/presentation'
INK = HexColor('#213d38')
MUTED = HexColor('#667974')
TEAL = HexColor('#287666')


def text(c, x, y, value, size=11, bold=False, color=INK):
    c.setFillColor(color)
    c.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
    c.drawString(x, y, value)


def page(filename, title, date, ref, child=False):
    OUT.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT/filename), pagesize=(595,842))
    c.setTitle(title+' | Fictional MediVault demonstration')
    c.setFillColor(TEAL); c.rect(0,827,595,15,fill=1,stroke=0)
    text(c,44,784,'CEDAR GROVE',24,True)
    text(c,44,763,'Demonstration clinic & diagnostics',12)
    text(c,44,743,'Imaginary facility | No real registration or accreditation',9,color=MUTED)
    c.setFillColor(HexColor('#edf5f1')); c.rect(44,687,507,35,fill=1,stroke=0)
    text(c,55,700,'FICTIONAL DEMONSTRATION - NOT VALID FOR CLINICAL USE',10,True)
    text(c,44,659,title,18,True)
    text(c,44,629,'Patient: '+('Mira Sharma' if child else 'Aarav Sharma')+' (fictional)',11,True)
    text(c,44,609,'Date of birth: '+('02/03/2020' if child else '18/04/1990')+' | '+('Female' if child else 'Male'))
    text(c,44,589,'Collection Date: '+date if 'Laboratory' in title else 'Document date: '+date)
    text(c,350,589,'Reference: '+ref,10)
    c.setStrokeColor(HexColor('#cedbd5')); c.line(44,574,551,574)
    text(c,44,68,'All identities, results and instructions are invented for software testing.',9,color=MUTED)
    text(c,44,53,'Do not use this document for treatment, insurance or identity verification.',9,color=MUTED)
    text(c,44,35,'MediVault presentation fixture | 1 / 1',8,color=MUTED)
    return c


def prescription(filename, date, ref, followup=False):
    c=page(filename,'Outpatient prescription',date,ref)
    text(c,44,548,'Consulting clinician: Dr Kavya Mehta (fictional)',11,True)
    text(c,44,526,'Visit: '+('Follow-up and medication reconciliation' if followup else 'Routine review and recorded symptom history'))
    text(c,44,496,'Rx / Demonstration instructions only',12,True)
    rows = [('Examplemed Delta 5 mg tablet','one tablet in the evening for 3 days (fictional)')] if followup else [
        ('Examplemed Alpha 250 mg tablet','one tablet daily for 5 days (fictional)'),
        ('Examplemed Beta 10 mg tablet','one tablet at night for 3 days (fictional)')]
    for i,(name,schedule) in enumerate(rows):
        y=460-i*75
        text(c,54,y,f'{i+1}. {name}',13,True)
        text(c,65,y-23,'Instruction: '+schedule,10)
    text(c,44,292,'Reported reaction: Examplemed Gamma - rash (fictional)',10)
    text(c,44,265,'Follow-up: '+('04 November 2026' if followup else '22 October 2026'),11,True)
    text(c,44,227,'The example medicines do not represent actual products or treatment.',10)
    text(c,44,207,'Current use must be confirmed with the patient; never infer it from this page.',10)
    text(c,44,151,'Author: Demo fixture generator | No clinical signature',10,color=MUTED)
    c.save()


def laboratory(filename,date,ref,values):
    c=page(filename,'Laboratory report - wellness panel',date,ref)
    text(c,44,547,'Specimen: blood (fictional) | Status: demonstration results',10)
    c.setFillColor(HexColor('#edf5f1'));c.rect(44,500,507,28,fill=1,stroke=0)
    text(c,54,510,'Investigation',11,True);text(c,254,510,'Result',11,True)
    text(c,333,510,'Unit',11,True);text(c,422,510,'Demo range',11,True)
    rows=[('Haemoglobin',values[0],'g/dL','13.0 - 17.0'),
          ('WBC',values[1],'/uL','4000 - 11000'),
          ('Platelets',values[2],'/uL','150000 - 450000'),
          ('Total Cholesterol',values[3],'mg/dL','125 - 200'),
          ('LDL Cholesterol',values[4],'mg/dL','0 - 100'),
          ('HDL Cholesterol',values[5],'mg/dL','40 - 80'),
          ('HbA1c',values[6],'%','4.0 - 5.6'),
          ('TSH',values[7],'mIU/L','0.4 - 4.0')]
    for i,(name,result,unit,ref_range) in enumerate(rows):
        y=479-i*32
        text(c,54,y,name,11);text(c,254,y,str(result),11,True)
        text(c,333,y,unit,10);text(c,422,y,ref_range,10)
        c.line(44,y-10,551,y-10)
    text(c,44,180,'Demo ranges are fixture values, not personalized clinical guidance.',10)
    text(c,44,158,'Compare with previous records; interpretation belongs with a clinician.',10)
    text(c,44,125,'Reviewed by: Demonstration laboratory | No clinical authorization',9,color=MUTED)
    c.save()


def main():
    prescription('aarav-prescription-2026-10-15.pdf','15/10/2026','DEMO-RX-1015')
    prescription('aarav-followup-2026-10-22.pdf','22/10/2026','DEMO-RX-1022',True)
    laboratory('aarav-labs-2026-09-15.pdf','15/09/2026','DEMO-LAB-0915',[13.2,7200,245000,218,139,46,5.8,2.1])
    laboratory('aarav-labs-2026-10-20.pdf','20/10/2026','DEMO-LAB-1020',[13.6,6800,252000,202,121,49,5.6,2.0])
    c=page('mira-child-visit-2026-10-18.pdf','Child visit record','18/10/2026','DEMO-CH-1018',True)
    for i,line in enumerate(['Guardian: Aarav Sharma (fictional)',
        'Visit reason: routine record review for a demonstration child',
        'Existing vaccination card reviewed; no clinical conclusions recorded.',
        'No medication prescribed in this demonstration record.',
        'Follow-up: discuss actual care with a qualified pediatric clinician.',
        'Clinician: Dr Kavya Mehta (fictional) | No clinical signature']):
        text(c,44,539-i*32,line,10)
    c.save()
    print('Created five fictional clinic-style PDFs in',OUT)


if __name__=='__main__': main()
