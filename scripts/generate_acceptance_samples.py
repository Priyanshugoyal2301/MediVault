"""Generate reproducible, visibly synthetic upload fixtures and expected results."""
import io
import json
from pathlib import Path
import zipfile

import fitz
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'apps/web/public/test-documents'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    image = Image.new('RGB', (1654, 2339), 'white')
    draw = ImageDraw.Draw(image)
    regular = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 34)
    bold = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 44)
    draw.text((90, 80), 'MEDIVAULT SOFTWARE TEST CLINIC', fill='black', font=bold)
    lines = [
        'SYNTHETIC SAMPLE - NOT A VALID PRESCRIPTION',
        'No real patient, clinician or medical advice.',
        'Patient: Sample Adult     Age: 35 years',
        'Prescription date: 14 January 2024',
        'Clinician: Example Reviewer (fictional)',
        '', 'Rx: software extraction test only',
        '1. Examplemed Alpha 250 mg tablet',
        '   Instruction: one tablet daily for 5 days (fictional)',
        '2. Examplemed Beta 10 mg tablet',
        '   Instruction: one tablet at night for 3 days (fictional)',
        '', 'Reported reaction: Examplemed Gamma - rash',
        'Follow-up: 21 January 2024',
        '', 'Do not purchase or take medicines from this sample.',
        'All medicine names and instructions are fictional.',
    ]
    draw.multiline_text((90, 200), '\n'.join(lines), fill='black', font=regular, spacing=22)
    image.save(OUT/'prescription-clear.png')
    image.save(OUT/'prescription-photo.jpg', quality=65)
    image.rotate(90, expand=True).save(OUT/'prescription-sideways.png')
    png = io.BytesIO(); image.save(png, format='PNG')
    with fitz.open() as pdf:
        p = pdf.new_page(); p.insert_image(p.rect, stream=png.getvalue())
        pdf.save(OUT/'prescription-scanned.pdf')
    with fitz.open() as pdf:
        p = pdf.new_page()
        p.insert_text((50,70), 'SYNTHETIC LAB REPORT - NOT A REAL PATIENT\nCollection Date: 14/01/2024\nHaemoglobin 13.5 g/dL 12.0 - 15.5\nTotal Cholesterol 215 mg/dL <200\nLDL Cholesterol 138 mg/dL <100\nSoftware verification only.', fontsize=12)
        pdf.save(OUT/'lab-report.pdf')
    with fitz.open() as pdf:
        pdf.new_page(); pdf.save(OUT/'blank.pdf')
    (OUT/'invalid.pdf').write_bytes(b'%PDF-this is deliberately not a valid PDF')
    fragments = ['Examplemed Alpha 250 mg', 'Examplemed Beta 10 mg', 'Examplemed Gamma', '14 January 2024', '21 January 2024']
    cases = [dict(file=name, kind='prescription', expected='complete', fragments=fragments)
             for name in ('prescription-clear.png','prescription-photo.jpg','prescription-sideways.png','prescription-scanned.pdf')]
    cases += [dict(file='lab-report.pdf', kind='report', expected='complete', values={'Haemoglobin':13.5}),
              dict(file='blank.pdf', kind='prescription', expected='failed'),
              dict(file='invalid.pdf', kind='prescription', expected='failed'),
              dict(file='prescription-clear.png', kind='report', expected='complete', fragments=fragments)]
    (OUT/'manifest.json').write_text(json.dumps(cases, indent=2), encoding='utf-8')
    (OUT/'README.txt').write_text(
        'SYNTHETIC SOFTWARE FIXTURES ONLY. No real medical advice.\n'
        'Upload prescription-* as Prescription; lab-report.pdf as Lab report.\n'
        'Blank and invalid PDFs MUST fail with a useful message.\n'
        'Compare every name, strength and date with the original; do not infer current medication use.\n'
        'Sideways is a challenge case. This collection does NOT validate handwriting accuracy.\n'
        'manifest.json records expected results for the automated API check.\n', encoding='utf-8')
    with zipfile.ZipFile(OUT/'medivault-test-documents.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.iterdir()):
            if path.is_file() and path.suffix != '.zip': archive.write(path, path.name)
    print(f'Generated synthetic acceptance files in {OUT}')


if __name__ == '__main__':
    main()
