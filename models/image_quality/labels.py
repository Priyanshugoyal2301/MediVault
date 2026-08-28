"""Quality problem labels for pre-OCR assessment."""

from __future__ import annotations

# Multi-label problem taxonomy (charter)
PROBLEM_LABELS: list[str] = [
    "blurry",
    "motion_blur",
    "out_of_focus",
    "low_resolution",
    "skewed",
    "rotated",
    "poor_lighting",
    "low_contrast",
    "cropped",
    "incomplete_page",
    "heavy_noise",
    "shadowed",
    "multiple_pages_detected",
]

# Ready is derived from score / absence of severe issues
READY_LABEL = "ready_for_ocr"

ALL_LABELS: list[str] = [READY_LABEL] + PROBLEM_LABELS

DISCLAIMER = (
    "Document image quality estimate only. This does not diagnose content "
    "of the report. Failures recommend re-upload for better OCR."
)

LABEL_DISPLAY: dict[str, str] = {
    READY_LABEL: "Ready for OCR",
    "blurry": "Blurry",
    "motion_blur": "Motion Blur",
    "out_of_focus": "Out of Focus",
    "low_resolution": "Low Resolution",
    "skewed": "Skewed",
    "rotated": "Rotated",
    "poor_lighting": "Poor Lighting",
    "low_contrast": "Low Contrast",
    "cropped": "Cropped",
    "incomplete_page": "Incomplete Page",
    "heavy_noise": "Heavy Noise",
    "shadowed": "Shadowed",
    "multiple_pages_detected": "Multiple Pages Detected",
}


def display_label(lab: str) -> str:
    return LABEL_DISPLAY.get(lab, lab.replace("_", " ").title())


def category_from_score(score_100: float) -> str:
    if score_100 >= 80:
        return "Ready for OCR"
    if score_100 >= 60:
        return "Acceptable"
    if score_100 >= 40:
        return "Poor"
    return "Unusable"


def recommendation(score_100: float, problems: list[str]) -> str:
    if score_100 >= 75 and not problems:
        return "Proceed with OCR"
    if score_100 >= 75 and problems:
        return "Proceed with OCR (minor issues noted)"
    if score_100 >= 50:
        return "Proceed with caution — OCR accuracy may be reduced"
    return "Please upload a clearer image"
