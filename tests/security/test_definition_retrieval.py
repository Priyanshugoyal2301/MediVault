from services.ai_service.rag.ingester import load_documents
from services.ai_service.rag.retriever import load_knowledge_base, retrieve
from services.ai_service.rag.synthesizer import synthesize


def test_haemoglobin_definition_uses_whole_relevant_sentence_and_patient_results():
    load_knowledge_base(load_documents(),mode='bm25')
    rows=retrieve('What does haemoglobin mean?',user_report_values=[
        {'test_name':'Haemoglobin','value_numeric':13.6,'unit':'g/dL','date_of_test':'2026-10-20'}])
    references=[r for r in rows if not r.is_user_data]
    assert len(references)==1
    assert references[0].text.startswith('Haemoglobin is the protein')
    assert 'oxygen' in references[0].text
    answer=synthesize('What does haemoglobin mean?',rows)['answer_en']
    assert '13.6 g/dL' in answer and 'platelets' not in answer and 'HbA1c' not in answer


def test_definition_route_honors_limit_and_does_not_invent_an_unknown_definition():
    load_knowledge_base([{'chunk_text':'Example term is a fictional reference sentence.',
                         'source_title':'Fixture','source_url':None}],mode='bm25')
    assert retrieve('What is example term?',top_k=0)==[]
    assert retrieve('What is zebracorn?',top_k=5)==[]
    assert retrieve('What is example term?',top_k=1)[0].text=='Example term is a fictional reference sentence.'
