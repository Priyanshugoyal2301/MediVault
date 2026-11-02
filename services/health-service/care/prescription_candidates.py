"""Conservative transcription helpers, never prescribing or drug-name correction.

Only explicit medicine-shaped source lines become draft candidates. Strength stays
in the name; it is not treated as the dose taken. Instructions are copied verbatim.
Everything is unconfirmed until an authorized person reviews the original.
"""
import re

STRENGTH = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|ml|iu|units?)\b", re.I)
FORM = re.compile(r"\b(?:tab(?:let)?s?|cap(?:sule)?s?|syrup|ointment|cream|drops|injection)\b", re.I)
EXCLUDE = re.compile(r"\b(?:allerg\w*|reaction|avoid|stop|discontinu\w*|not taking|history|previous|follow.?up|patient|age|weight|pressure|cholesterol|glucose|haemoglobin|hemoglobin|creatinine|result|reference|range)\b", re.I)
INSTRUCTION = re.compile(r"^(?:instruction|dose|dosage|schedule|directions?|sig)\s*:\s*", re.I)


def candidates_from_text(text):
    lines = (text or '').splitlines()
    result = []
    for index, raw in enumerate(lines):
        line = raw.strip()
        if not line or len(line) > 350 or EXCLUDE.search(line) or INSTRUCTION.match(line):
            continue
        numbered = bool(re.match(r'^\s*\d+[.)]\s+', line))
        labelled = bool(re.match(r'^(?:medication|medicine)\s*:', line, re.I))
        if not (STRENGTH.search(line) and (numbered or labelled or FORM.search(line))):
            continue
        name = re.sub(r'^\s*\d+[.)]\s*', '', line)
        name = re.sub(r'^(?:medication|medicine)\s*:\s*', '', name, flags=re.I)
        if len(name) > 200:
            continue
        schedule = ''
        evidence = line
        next_line = index + 1
        # OCR often inserts paragraph gaps. Cross only blank lines, never another
        # medicine, a clinical note, or a page of unrelated text.
        while next_line < min(len(lines), index + 5) and not lines[next_line].strip():
            next_line += 1
        if next_line < min(len(lines), index + 5) and INSTRUCTION.match(lines[next_line].strip()):
            instruction = lines[next_line].strip()
            schedule = INSTRUCTION.sub('', instruction)
            if len(schedule) > 200:
                schedule = ''  # Never silently truncate an instruction into a different one.
            else:
                evidence += '\n' + '\n'.join(lines[index+1:next_line+1]).rstrip()
        result.append(dict(name=name, dose='', schedule=schedule, status='unknown',
                           source_line=index+1, source_text=evidence))
        if len(result) == 30:
            break
    return result
