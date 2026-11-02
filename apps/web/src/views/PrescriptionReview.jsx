import React, {useEffect, useState} from 'react';
import {Download, Plus, Trash2} from 'lucide-react';
import {documentBlob, downloadDocument, request, scoped} from '../api';
import {ErrorNotice, Field, Modal} from '../components/UI';

const emptyMedicine = () => ({key:crypto.randomUUID(), selected:true, name:'', dose:'',
  schedule:'', status:'unknown', start_date:'', end_date:'', notes:'', source_text:''});

export default function PrescriptionReview({report, patient, onClose, onSaved}) {
  const [draft,setDraft] = useState(null);
  const [medicines,setMedicines] = useState([]);
  const [documentDate,setDocumentDate] = useState(report.document_date || '');
  const [original,setOriginal] = useState(null);
  const [error,setError] = useState('');
  const [previewError,setPreviewError] = useState('');
  const [busy,setBusy] = useState(false);
  const [confirmed,setConfirmed] = useState(false);
  const path = scoped(`/reports/${report.id}/prescription-review`,patient.id);

  useEffect(()=>{
    let cancelled=false;
    request(path).then(result=>{
      if(cancelled)return;
      setDraft(result);
      setMedicines(result.candidates.map(candidate=>({...emptyMedicine(), ...candidate, selected:false})));
    }).catch(e=>{if(!cancelled)setError(e);});
    return()=>{cancelled=true;};
  },[path]);

  useEffect(()=>{
    let cancelled=false, url;
    documentBlob(report.id,patient.id).then(blob=>{
      if(cancelled)return;
      url=URL.createObjectURL(blob);
      setOriginal({url,type:blob.type});
    }).catch(e=>{if(!cancelled)setPreviewError(e);});
    return()=>{cancelled=true;if(url)URL.revokeObjectURL(url);};
  },[report.id,patient.id]);

  function change(key,field,value) {
    setMedicines(rows=>rows.map(row=>row.key===key?{...row,[field]:value}:row));
    setConfirmed(false);
  }

  async function submit(event) {
    event.preventDefault();
    const selected=medicines.filter(m=>m.selected);
    if(!selected.length){setError('Select at least one reviewed medicine, or add a missing medicine.');return;}
    setBusy(true);setError('');
    try {
      const result=await request(path,{method:'POST',body:{confirm_review:confirmed,
        document_date:documentDate||null,
        medications:selected.map(m=>({name:m.name,dose:m.dose,schedule:m.schedule,status:m.status,
          start_date:m.start_date||null,end_date:m.end_date||null,notes:m.notes}))}});
      await onSaved(result);
    } catch(e) {
      setError(e);
      // A response can be lost after a successful commit. Refresh review state so
      // retries do not encourage duplicate entry or claim that nothing was saved.
      try{const latest=await request(path);if(latest.reviewed)setDraft(latest);}catch{}
    } finally {setBusy(false);}
  }

  return <Modal wide title="Review prescription medicines" onClose={()=>{if(!busy)onClose();}}>
    <p className="muted">For <strong>{patient.display_name}</strong> · {report.original_filename}</p>
    <div className="notice">Compare each field with the original. Draft rows may be incomplete or wrong. Nothing is saved until you select the medicines and confirm your review. This records information; it does not prescribe treatment.</div>
    <ErrorNotice error={error}/>
    {draft?.reviewed ? <section className="notice success"><h3>This document has already been reviewed</h3><p>{draft.medication_ids.length} medicine records were saved. Open Medications to inspect or correct them. Re-submitting this document will not create duplicates.</p><button className="button" onClick={onClose}>Back to document</button></section> : <div className="prescription-review-grid">
      <section className="review-source">
        <div className="button-row"><h3>Original document</h3><button className="button small" onClick={async()=>{try{await downloadDocument(report.id,patient.id,report.original_filename);}catch(e){setPreviewError(e);}}}><Download size={15}/>Download</button></div>
        <ErrorNotice error={previewError}/>
        {original?.type.startsWith('image/') ? <img className="original-document" src={original.url} alt="Original uploaded prescription for comparison"/> : original?.type==='application/pdf' ? <><iframe className="original-document" src={original.url} title="Original prescription PDF" sandbox=""/><p className="form-help">If your browser cannot preview the PDF, download the original to compare it.</p></> : !previewError&&<p>Loading original…</p>}
        <details><summary>Extracted text · may contain errors</summary><pre className="ocr-text">{report.extracted_text || 'No extracted text available.'}</pre></details>
      </section>
      <form className="review-fields" onSubmit={submit}>
        {!draft ? <p role="status">Preparing review…</p> : <>
          <Field label="Date written on the prescription" type="date" value={documentDate} onChange={e=>{setDocumentDate(e.target.value);setConfirmed(false);}} help="Leave blank if unknown. This is not the date you started taking a medicine."/>
          {!medicines.length&&<div className="notice">No confident medicine-shaped lines were found. Add details manually from the original; do not guess unreadable names or instructions.</div>}
          {medicines.map((medicine,index)=><fieldset className="medicine-review" key={medicine.key} disabled={busy}>
            <legend>Medicine {index+1}</legend>
            <label className="check"><input type="checkbox" checked={medicine.selected} onChange={e=>change(medicine.key,'selected',e.target.checked)}/>Include this medicine</label>
            {medicine.source_text&&<blockquote className="source-excerpt">Source line {medicine.source_line}: {medicine.source_text}</blockquote>}
            <Field label="Medicine name and strength as written" value={medicine.name} required={medicine.selected} maxLength={200} onChange={e=>change(medicine.key,'name',e.target.value)}/>
            <Field label="Dose taken, if explicitly written" value={medicine.dose} maxLength={100} onChange={e=>change(medicine.key,'dose',e.target.value)} help="A tablet strength such as 250 mg is not automatically the dose taken."/>
            <Field label="Schedule and duration as written" value={medicine.schedule} maxLength={200} onChange={e=>change(medicine.key,'schedule',e.target.value)} help="Copy instructions without expanding abbreviations or inventing missing details."/>
            <Field label="Reported current use"><select value={medicine.status} onChange={e=>change(medicine.key,'status',e.target.value)}><option value="unknown">Unknown / not confirmed</option><option value="taking">Patient reports taking</option><option value="stopped">Patient reports stopped</option></select></Field>
            <div className="form-grid"><Field label="Actual start date, if known" type="date" value={medicine.start_date} onChange={e=>change(medicine.key,'start_date',e.target.value)}/><Field label="Actual end date, if known" type="date" value={medicine.end_date} onChange={e=>change(medicine.key,'end_date',e.target.value)}/></div>
            <Field label="Review notes"><textarea value={medicine.notes} maxLength={3000} onChange={e=>change(medicine.key,'notes',e.target.value)} rows={2}/></Field>
            <button type="button" className="button small" onClick={()=>{setMedicines(rows=>rows.filter(row=>row.key!==medicine.key));setConfirmed(false);}}><Trash2 size={14}/>Remove row</button>
          </fieldset>)}
          <button type="button" className="button" disabled={busy||medicines.length>=30} onClick={()=>{setMedicines(rows=>[...rows,emptyMedicine()]);setConfirmed(false);}}><Plus size={16}/>Add a missing medicine</button>
          <label className="check review-confirm"><input type="checkbox" required checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>I compared the selected medicines with the original and checked the reported use. Unclear details are left blank.</label>
          <button className="button primary full" disabled={busy||!confirmed||!medicines.some(m=>m.selected)}>{busy?'Saving reviewed medicines…':`Save ${medicines.filter(m=>m.selected).length} reviewed medicines`}</button>
        </>}
      </form>
    </div>}
  </Modal>;
}
