"""Real local OCR checks with synthetic documents; no browser or remote AI."""
import io
import os
from pathlib import Path
import sys
import bootstrap_imports  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('TESSERACT_CMD', 'C:/Program Files/Tesseract-OCR/tesseract.exe')

import fitz
from PIL import Image, ImageDraw, ImageFont
from services.ai_service.ocr.tesseract_backend import TesseractBackend


def page(text):
    image = Image.new('RGB', (1400, 500), 'white')
    ImageDraw.Draw(image).text((60, 80), text, font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 36), fill='black')
    return image


def main():
    backend = TesseractBackend()
    first = page('SYNTHETIC PAGE ONE: Example medicine 250 mg')
    second = page('SYNTHETIC PAGE TWO: Follow up 14 January 2024')
    tiff = io.BytesIO()
    first.save(tiff, format='TIFF', save_all=True, append_images=[second])
    text = backend.extract_text(tiff.getvalue(), 'image/tiff')
    assert '250 mg' in text and '14 January 2024' in text
    print('PASS: both TIFF pages extracted, including dose and date')
    png = io.BytesIO()
    second.save(png, format='PNG')
    with fitz.open() as document:
        cover = document.new_page()
        cover.insert_text((72, 72), 'SYNTHETIC COVER PAGE WITH SELECTABLE TEXT.\nScanned prescription information is on the next page.')
        scanned = document.new_page(width=700, height=250)
        scanned.insert_image(scanned.rect, stream=png.getvalue())
        text = backend.extract_text(document.tobytes(), 'application/pdf')
    assert 'SELECTABLE TEXT' in text and '14 January 2024' in text
    print('PASS: mixed PDF preserves cover text and scans the image page')
    blank = io.BytesIO()
    Image.new('RGB', (800, 600), 'white').save(blank, format='PNG')
    assert not backend.extract_text(blank.getvalue(), 'image/png').strip()
    print('PASS: blank image produces no invented text')


if __name__ == '__main__':
    main()
