import React, { useRef, useState } from 'react';
import { UploadCloud, CheckCircle2, Info, Sparkles, RefreshCw, AlertCircle } from 'lucide-react';
import { pollReportUntilDone, seedDemoReport, uploadReport } from '../api';

function statusFromValue(v) {
  if (v.status) return v.status;
  const n = v.value_numeric;
  const lo = v.reference_range_low;
  const hi = v.reference_range_high;
  if (n == null || (lo == null && hi == null)) return 'unknown';
  if (hi != null && n > hi) return 'high';
  if (lo != null && n < lo) return 'low';
  return 'normal';
}

export default function UploadView({ locale, token, onReportReady }) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeReport, setActiveReport] = useState(null);
  const [error, setError] = useState('');
  const [selectedPanel, setSelectedPanel] = useState('cbc');
  const fileRef = useRef(null);
  const isHi = locale === 'hi-IN';

  const showReport = (detail) => {
    const values = (detail.values || []).map((v) => ({
      ...v,
      status: statusFromValue(v),
    }));
    setActiveReport({
      title: detail.original_filename || 'Lab Report',
      date: values[0]?.date_of_test || detail.uploaded_at?.slice(0, 10) || '—',
      parsed_status: detail.parsed_status,
      values,
    });
    onReportReady?.(detail);
  };

  const handleSeed = async (panelKey) => {
    setSelectedPanel(panelKey);
    setError('');
    setIsProcessing(true);
    try {
      const detail = await seedDemoReport(token, panelKey);
      showReport(detail);
    } catch (err) {
      setError(err.message || 'Demo seed failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFile = async (file) => {
    if (!file) return;
    setError('');
    setIsProcessing(true);
    try {
      const created = await uploadReport(token, file);
      const detail = await pollReportUntilDone(token, created.id);
      if (detail.parsed_status === 'failed') {
        throw new Error('Parsing failed. Try a clearer PDF/image or use a demo panel.');
      }
      showReport(detail);
    } catch (err) {
      setError(err.message || 'Upload failed');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="card">
        <div className="card-title">
          <span>{isHi ? 'चिकित्सा रिपोर्ट अपलोड करें (PDF/छवि)' : 'Upload Medical Report (PDF or Image)'}</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-subtle)', fontWeight: 400 }}>
            Live API · Tesseract OCR + Regex Parser
          </span>
        </div>

        <div
          className="dropzone"
          role="button"
          tabIndex={0}
          onClick={() => fileRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') fileRef.current?.click();
          }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files?.[0];
            if (f) handleFile(f);
          }}
        >
          <UploadCloud size={48} color="var(--primary)" style={{ marginBottom: '1rem' }} aria-hidden="true" />
          <h3 style={{ color: '#fff', fontSize: '1.1rem', marginBottom: '0.5rem' }}>
            {isHi ? 'अपनी लैब रिपोर्ट फ़ाइल यहां खींचें और छोड़ें' : 'Drag & drop your lab report here'}
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
            {isHi ? 'समर्थित: PDF, PNG, JPEG' : 'Supports PDF, PNG, JPEG · magic-byte validated'}
          </p>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,image/png,image/jpeg,image/tiff,image/webp"
            style={{ display: 'none' }}
            onChange={(e) => handleFile(e.target.files?.[0])}
          />

          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-subtle)', alignSelf: 'center', width: '100%', marginBottom: '0.5rem' }}>
              {isHi ? 'या डेमो पैनल लोड करें (OCR की आवश्यकता नहीं):' : 'Or load a deterministic demo panel (no OCR):'}
            </span>
            {['cbc', 'lipid'].map((key) => (
              <button
                key={key}
                type="button"
                className={`btn ${selectedPanel === key ? 'btn-primary' : 'btn-secondary'}`}
                onClick={(e) => {
                  e.stopPropagation();
                  handleSeed(key);
                }}
                style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
              >
                {key.toUpperCase()} {isHi ? 'डेमो' : 'Demo'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="card" role="alert" style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', color: '#f87171' }}>
          <AlertCircle size={18} />
          <span style={{ fontSize: '0.9rem' }}>{error}</span>
        </div>
      )}

      {isProcessing && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <RefreshCw className="spin" size={36} color="var(--primary)" style={{ marginBottom: '1rem' }} />
          <h4 style={{ color: '#fff' }}>{isHi ? 'रिपोर्ट का विश्लेषण किया जा रहा है...' : 'Extracting & Explaining Lab Values...'}</h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
            Calling health-service → AI parse pipeline
          </p>
        </div>
      )}

      {!isProcessing && activeReport && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ color: '#fff', fontSize: '1.2rem', fontWeight: 600 }}>{activeReport.title}</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                {isHi ? 'परीक्षण तिथि:' : 'Test Date:'} {activeReport.date} •{' '}
                <span style={{ color: '#34d399', fontWeight: 600 }}>{activeReport.parsed_status}</span>
              </p>
            </div>
            <span className="badge normal">
              <CheckCircle2 size={12} /> {activeReport.values.length} {isHi ? 'मान' : 'Values'}
            </span>
          </div>

          <div className="card" style={{ padding: 0 }}>
            <div className="table-container">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>{isHi ? 'परीक्षण नाम' : 'Test Name'}</th>
                    <th>{isHi ? 'परिणाम मान' : 'Result Value'}</th>
                    <th>{isHi ? 'इकाई' : 'Unit'}</th>
                    <th>{isHi ? 'संदर्भ सीमा' : 'Reference Range'}</th>
                    <th>{isHi ? 'स्थिति' : 'Status'}</th>
                  </tr>
                </thead>
                <tbody>
                  {activeReport.values.map((v) => (
                    <tr key={v.id || v.test_name}>
                      <td style={{ fontWeight: 600, color: '#fff' }}>{v.test_name}</td>
                      <td style={{ fontWeight: 700, color: v.status === 'high' ? '#f87171' : v.status === 'low' ? '#fbbf24' : '#34d399' }}>
                        {v.value_numeric ?? v.value_text}
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{v.unit}</td>
                      <td style={{ color: 'var(--text-subtle)' }}>
                        {v.reference_range_text || `${v.reference_range_low ?? '—'} - ${v.reference_range_high ?? '—'}`}
                      </td>
                      <td>
                        <span className={`badge ${v.status}`}>{v.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="card-title">
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={20} color="var(--primary)" />
                {isHi ? 'सरल भाषा में व्याख्या' : 'Plain-Language Explanations (Non-Diagnostic)'}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {activeReport.values.map((v) => (
                <div
                  key={`exp-${v.id || v.test_name}`}
                  style={{
                    padding: '1rem 1.25rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.02)',
                    borderLeft: `4px solid ${v.status === 'high' ? '#f87171' : v.status === 'low' ? '#fbbf24' : '#10b981'}`,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                    <span style={{ fontWeight: 600, color: '#fff' }}>{v.test_name}</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>{v.value_numeric} {v.unit}</span>
                  </div>
                  <p style={{ color: '#cbd5e1', fontSize: '0.875rem', lineHeight: 1.6 }}>
                    {isHi ? (v.explanation_hi || v.explanation_en) : (v.explanation_en || v.explanation_hi || '—')}
                  </p>
                </div>
              ))}
            </div>
            <div style={{ marginTop: '1.5rem', padding: '0.85rem 1rem', borderRadius: 'var(--radius-md)', background: 'rgba(6, 182, 212, 0.08)', border: '1px solid rgba(6, 182, 212, 0.2)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Info size={18} color="var(--primary)" />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {isHi
                  ? 'सुरक्षा नोट: यह प्रणाली निदान नहीं देती। अपने डॉक्टर से चर्चा करें।'
                  : 'Safety note: This system never issues a diagnosis. Discuss results with a qualified clinician.'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
