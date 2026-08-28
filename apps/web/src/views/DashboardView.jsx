import React from 'react';
import { FileText, TrendingUp, AlertTriangle, MessageSquare, ArrowRight, ShieldCheck } from 'lucide-react';

export default function DashboardView({ locale, setActiveTab, data }) {
  const isHi = locale === 'hi-IN';
  const reports = data?.recentReports || [];
  const trends = data?.anomalies || [];
  const reportCount = data?.reportCount ?? reports.length;
  const metricCount = data?.metricCount ?? trends.length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {reportCount === 0 && (
        <div className="card" style={{ border: '1px solid rgba(6,182,212,0.35)' }}>
          <h3 style={{ color: '#fff', marginBottom: '0.5rem' }}>
            {isHi ? 'अपना वॉल्ट शुरू करें' : 'Start your vault'}
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            {isHi
              ? 'अपलोड टैब से LIPID Demo पैनल लोड करें — OCR की आवश्यकता नहीं।'
              : 'Load the LIPID Demo panel from Upload — deterministic, no OCR required for judging.'}
          </p>
          <button type="button" className="btn btn-primary" onClick={() => setActiveTab('upload')}>
            {isHi ? 'डेमो पैनल लोड करें' : 'Load demo panel'} <ArrowRight size={16} />
          </button>
        </div>
      )}

      {trends.length > 0 && (
        <div className="anomaly-banner">
          <AlertTriangle className="anomaly-banner-icon" size={24} aria-hidden="true" />
          <div style={{ flex: 1 }}>
            <h4 style={{ color: '#fff', fontSize: '1rem', fontWeight: 600 }}>
              {isHi ? 'ट्रैक की गई मेट्रिक्स उपलब्ध' : 'Tracked metrics ready for trend review'}
            </h4>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              {trends.map((t) => t.metric).join(' · ')}
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setActiveTab('timeline')}
            style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
          >
            {isHi ? 'टाइमलाइन देखें' : 'Open Timeline'} <ArrowRight size={14} />
          </button>
        </div>
      )}

      <div className="grid-3">
        <div className="card stat-card">
          <div className="stat-icon cyan">
            <FileText size={24} aria-hidden="true" />
          </div>
          <div>
            <div className="stat-number">{reportCount}</div>
            <div className="stat-label">{isHi ? 'रिपोर्ट' : 'Reports in vault'}</div>
          </div>
        </div>

        <div className="card stat-card">
          <div className="stat-icon purple">
            <TrendingUp size={24} aria-hidden="true" />
          </div>
          <div>
            <div className="stat-number">{metricCount}</div>
            <div className="stat-label">{isHi ? 'ट्रैक की गई मेट्रिक्स' : 'Tracked metrics'}</div>
          </div>
        </div>

        <div className="card stat-card">
          <div className="stat-icon emerald">
            <ShieldCheck size={24} aria-hidden="true" />
          </div>
          <div>
            <div className="stat-number">JWT</div>
            <div className="stat-label">{isHi ? 'BFF पहचान' : 'BFF-authenticated'}</div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">
            <span>{isHi ? 'हाल की लैब रिपोर्ट' : 'Recent lab reports'}</span>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setActiveTab('upload')}
              style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
            >
              {isHi ? '+ जोड़ें' : '+ Add'}
            </button>
          </div>

          {reports.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              {isHi ? 'अभी कोई रिपोर्ट नहीं।' : 'No reports yet. Use Upload → LIPID Demo.'}
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {reports.map((report) => (
                <div
                  key={report.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.85rem 1rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--bg-card-border)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <FileText size={20} color="var(--primary)" aria-hidden="true" />
                    <div>
                      <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.9rem' }}>{report.name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>
                        {report.date} · {report.status}
                      </div>
                    </div>
                  </div>
                  <span className={`badge ${report.status === 'complete' ? 'normal' : 'low'}`}>
                    {report.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <MessageSquare size={20} color="var(--primary)" aria-hidden="true" />
              {isHi ? 'उद्धृत Q&A' : 'Cited Q&A'}
            </span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
            {isHi
              ? 'टेम्पलेट-आधारित उत्तर + सुरक्षा परत। निदान नहीं।'
              : 'Template-based answers with citations. Safety layer runs first. Never a diagnosis.'}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.5rem' }}>
            {[
              isHi ? 'उच्च LDL का क्या अर्थ है?' : 'What does high LDL mean?',
              isHi ? 'मेरा LDL क्या था?' : 'What was my LDL?',
            ].map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => setActiveTab('chat')}
                style={{
                  textAlign: 'left',
                  padding: '0.65rem 0.85rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(0,0,0,0.2)',
                  border: '1px solid var(--bg-card-border)',
                  fontSize: '0.85rem',
                  color: '#cbd5e1',
                  cursor: 'pointer',
                }}
              >
                “{q}”
              </button>
            ))}
          </div>

          <button type="button" className="btn btn-primary" onClick={() => setActiveTab('chat')} style={{ width: '100%' }}>
            {isHi ? 'Q&A खोलें' : 'Open Q&A'} <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
