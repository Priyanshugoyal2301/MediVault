from services.health_service.care.prescription_candidates import candidates_from_text


def test_candidate_preserves_strength_without_inventing_dose_or_current_use():
    text = 'Patient: Synthetic\n1. Examplemed Alpha 250 mg tablet\nInstruction: one tablet daily for 5 days\nReported reaction: Examplemed Beta 10 mg tablet - rash'
    rows = candidates_from_text(text)
    assert len(rows) == 1
    assert rows[0]['name'] == 'Examplemed Alpha 250 mg tablet'
    assert rows[0]['dose'] == ''
    assert rows[0]['schedule'] == 'one tablet daily for 5 days'
    assert rows[0]['status'] == 'unknown'
    assert rows[0]['source_line'] == 2


def test_no_inference_from_blank_lab_or_negated_medicine_lines():
    assert candidates_from_text('') == []
    assert candidates_from_text('Glucose 100 mg/dL\nStop Examplemed 10 mg tablet\nPrevious: Examplemed 5 mg tablet') == []


def test_unlabelled_instructions_are_not_guessed_and_duplicates_stay_visible():
    rows = candidates_from_text('1. Examplemed 10 mg tablet\nMaybe take more?\n2. Examplemed 10 mg tablet')
    assert len(rows) == 2
    assert all(row['schedule'] == '' for row in rows)


def test_ocr_paragraph_gaps_keep_instructions_with_their_own_medicine():
    text='1. Examplemed Alpha 250 mg tablet\n\nInstruction: one tablet daily for 5 days\n\n2. Examplemed Beta 10 mg tablet\n \n\nInstruction: one tablet at night for 3 days'
    rows=candidates_from_text(text)
    assert [r['schedule'] for r in rows]==['one tablet daily for 5 days','one tablet at night for 3 days']
    assert rows[0]['source_line']==1 and rows[1]['source_line']==5
    assert rows[0]['source_text']=='1. Examplemed Alpha 250 mg tablet\n\nInstruction: one tablet daily for 5 days'


def test_instruction_search_never_crosses_another_medicine_or_note():
    rows=candidates_from_text('1. Examplemed Alpha 250 mg tablet\n\n2. Examplemed Beta 10 mg tablet\nInstruction: explicit beta schedule')
    assert [r['schedule'] for r in rows]==['','explicit beta schedule']
    rows=candidates_from_text('1. Examplemed Alpha 250 mg tablet\n\nClinical note: verify original\nInstruction: not adjacent')
    assert rows[0]['schedule']==''
