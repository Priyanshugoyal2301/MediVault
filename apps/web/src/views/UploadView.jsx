import React, { useState } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Info, Sparkles, RefreshCw } from 'lucide-react';

export default function UploadView({ locale, sampleReports }) {
  const [selectedPanel, setSelectedPanel] = useState('cbc');
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeReport, setActiveReport] = useState(sampleReports.cbc);
  const isHi = locale === 'hi-IN';

  const handleSelectSample = (panelKey) => {
    setSelectedPanel(panelKey);
    setIsProcessing(true);
    setTimeout(() => {
      setActiveReport(sampleReports[panelKey]);
      setIsProcessing(false);
    }, 600);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Upload card / Quick sample selector */}
      <div className="card">
        <div className="card-title">
          <span>{isHi ? 'चिकित्सा रिपोर्ट अपलोड करें (PDF/छवि)' : 'Upload Medical Report (PDF or Image)'}</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-subtle)', fontWeight: 400 }}>
            Tesseract OCR + Regex Parser
          </span>
        </div>

        <div className="dropzone">
          <UploadCloud size={48} color="var(--primary)" style={{ marginBottom: '1rem' }} />
          <h3 style={{ color: '#fff', fontSize: '1.1rem', marginBottom: '0.5rem' }}>
            {isHi ? 'अपनी लैब रिपोर्ट फ़ाइल यहां खींचें और छोड़ें' : 'Drag & drop your lab report here'}
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
            {isHi ? 'समर्थित प्रारूप: PDF, PNG, JPEG (CBC, लिपीड, थायराइड, HbA1c)' : 'Supports PDF, PNG, JPEG (CBC, Lipid, Thyroid, HbA1c panels)'}
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-subtle)', alignSelf: 'center', width: '100%', marginBottom: '0.5rem' }}>
              {isHi ? 'या परीक्षण के लिए एक नमूना पैनल चुनें:' : 'Or test with a pre-parsed sample panel:'}
            </span>

            {['cbc', 'lipid', 'thyroid', 'hba1c'].map((key) => (
              <button
                key={key}
                className={`btn ${selectedPanel === key ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => handleSelectSample(key)}
                style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
              >
                {key.toUpperCase()} {isHi ? 'पैनल' : 'Panel'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Processing Loader */}
      {isProcessing && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <RefreshCw className="spin" size={36} color="var(--primary)" style={{ marginBottom: '1rem' }} />
          <h4 style={{ color: '#fff' }}>{isHi ? 'रिपोर्ट का विश्लेषण किया जा रहा है...' : 'Extracting & Explaining Lab Values...'}</h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
            Running Tesseract OCR engine + Indian lab reference range matching
          </p>
        </div>
      )}

      {/* Parsed Output Table & Explanations */}
      {!isProcessing && activeReport && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Metadata Card */}
          <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ color: '#fff', fontSize: '1.2rem', fontWeight: 600 }}>
                {activeReport.title}
              </h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                {isHi ? 'परीक्षण तिथि:' : 'Test Date:'} {activeReport.date} • {isHi ? 'स्थिति:' : 'Status:'} <span style={{ color: '#34d399', fontWeight: 600 }}>Parsed (Complete)</span>
              </p>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <span className="badge normal">
                <CheckCircle2 size={12} /> {activeReport.values.length} {isHi ? 'मान' : 'Values'}
              </span>
            </div>
          </div>

          {/* Extracted Values Table */}
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
                  {activeReport.values.map((v, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600, color: '#fff' }}>{v.test_name}</td>
                      <td style={{ fontWeight: 700, color: v.status === 'high' ? '#f87171' : v.status === 'low' ? '#fbbf24' : '#34d399' }}>
                        {v.value_numeric ?? v.value_text}
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{v.unit}</td>
                      <td style={{ color: 'var(--text-subtle)' }}>{v.reference_range_text || `${v.reference_range_low} - ${v.reference_range_high}`}</td>
                      <td>
                        <span className={`badge ${v.status}`}>
                          {v.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Plain Language Explanations */}
          <div className="card">
            <div className="card-title">
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={20} color="var(--primary)" />
                {isHi ? 'सरल भाषा में व्याख्या (Non-Diagnostic Tone)' : 'Plain-Language Explanations (Non-Diagnostic)'}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', border: '1px solid var(--bg-card-border)', padding: '2px 8px', borderRadius: '4px' }}>
                {isHi ? 'भाषा:' : 'Language:'} {isHi ? 'हिन्दी' : 'English'}
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {activeReport.values.map((v, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '1rem 1.25rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.02)',
                    borderLeft: `4px solid ${v.status === 'high' ? '#f87171' : v.status === 'low' ? '#fbbf24' : '#10b981'}`,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                    <span style={{ fontWeight: 600, color: '#fff', fontSize: '0.95rem' }}>{v.test_name}</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>{v.value_numeric} {v.unit}</span>
                  </div>
                  <p style={{ color: '#cbd5e1', fontSize: '0.875rem', lineHeight: 1.6 }}>
                    {isHi ? v.explanation_hi : v.explanation_en}
                  </p>
                </div>
              ))}
            </div>

            <div style={{ marginTop: '1.5rem', padding: '0.85rem 1rem', borderRadius: 'var(--radius-md)', background: 'rgba(6, 182, 212, 0.08)', border: '1px solid rgba(6, 182, 212, 0.2)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Info size={18} color="var(--primary)" />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {isHi
                  ? 'सुरक्षा नोट: यह प्रणाली कभी भी कोई निदान नहीं देती है। कृपया अपने परिणामों की चर्चा अपने डॉक्टर से करें।'
                  : 'Safety Note: This system never state a diagnosis. Always consult a qualified medical professional to review your lab results.'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
