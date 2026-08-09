import React from 'react';
import { FileText, TrendingUp, AlertTriangle, MessageSquare, ArrowRight, ShieldCheck } from 'lucide-react';

export default function DashboardView({ locale, setActiveTab, mockData }) {
  const isHi = locale === 'hi-IN';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Anomaly alert banner if anomalies exist */}
      {mockData.anomalies && mockData.anomalies.length > 0 && (
        <div className="anomaly-banner">
          <AlertTriangle className="anomaly-banner-icon" size={24} />
          <div style={{ flex: 1 }}>
            <h4 style={{ color: '#fff', fontSize: '1rem', fontWeight: 600 }}>
              {isHi ? 'ध्यान देने योग्य प्रवृत्ति पाई गई' : 'Health Trend Alert Detected'}
            </h4>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              {isHi
                ? 'आपके एलडीएल कोलेस्ट्रॉल का मान पिछले 3 परीक्षणों में लगातार बढ़ रहा है।'
                : 'Your LDL Cholesterol shows a consistent upward trend over the last 3 reports.'}
            </p>
          </div>
          <button className="btn btn-secondary" onClick={() => setActiveTab('timeline')} style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}>
            {isHi ? 'प्रवृत्ति देखें' : 'View Trend'} <ArrowRight size={14} />
          </button>
        </div>
      )}

      {/* Overview stats grid */}
      <div className="grid-3">
        <div className="card stat-card">
          <div className="stat-icon cyan">
            <FileText size={24} />
          </div>
          <div>
            <div className="stat-number">4</div>
            <div className="stat-label">{isHi ? 'अपलोड की गई रिपोर्ट' : 'Reports Parsed'}</div>
          </div>
        </div>

        <div className="card stat-card">
          <div className="stat-icon purple">
            <TrendingUp size={24} />
          </div>
          <div>
            <div className="stat-number">12</div>
            <div className="stat-label">{isHi ? 'ट्रैक किए गए लैब मान' : 'Tracked Lab Values'}</div>
          </div>
        </div>

        <div className="card stat-card">
          <div className="stat-icon emerald">
            <ShieldCheck size={24} />
          </div>
          <div>
            <div className="stat-number">100%</div>
            <div className="stat-label">{isHi ? 'गोपनीयता संरक्षित' : 'Privacy Enforced'}</div>
          </div>
        </div>
      </div>

      {/* Main dashboard sections */}
      <div className="grid-2">
        {/* Recent Reports */}
        <div className="card">
          <div className="card-title">
            <span>{isHi ? 'हाल की लैब रिपोर्ट' : 'Recent Lab Reports'}</span>
            <button className="btn btn-secondary" onClick={() => setActiveTab('upload')} style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}>
              {isHi ? '+ नया रिपोर्ट जोड़ें' : '+ Upload New'}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {mockData.recentReports.map((report) => (
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
                  <FileText size={20} color="var(--primary)" />
                  <div>
                    <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.9rem' }}>{report.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>{report.date} • {report.panel}</div>
                  </div>
                </div>
                <span className={`badge ${report.status === 'complete' ? 'normal' : 'low'}`}>
                  {report.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Q&A Prompt Card */}
        <div className="card" style={{ background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)' }}>
          <div className="card-title">
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <MessageSquare size={20} color="var(--primary)" />
              {isHi ? 'साक्ष्य-आधारित स्वास्थ्य Q&A' : 'Evidence-Based Q&A'}
            </span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
            {isHi
              ? 'अपनी रिपोर्ट या सामान्य स्वास्थ्य के बारे में प्रश्न पूछें। सभी उत्तर उद्धृत स्रोतों द्वारा समर्थित हैं।'
              : 'Ask questions about your lab report values or general health. Answers include citations from medical guidelines.'}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.5rem' }}>
            <div
              style={{ padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--bg-card-border)', fontSize: '0.85rem', color: '#cbd5e1', cursor: 'pointer' }}
              onClick={() => setActiveTab('chat')}
            >
              "{isHi ? 'मेरा एलडीएल कोलेस्ट्रॉल मान क्या दर्शाता है?' : 'What does my high LDL cholesterol value mean?'}"
            </div>
            <div
              style={{ padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--bg-card-border)', fontSize: '0.85rem', color: '#cbd5e1', cursor: 'pointer' }}
              onClick={() => setActiveTab('chat')}
            >
              "{isHi ? 'क्या 10.5 g/dL हीमोग्लोबिन कम है?' : 'Is haemoglobin of 10.5 g/dL low for an adult?'}"
            </div>
          </div>

          <button className="btn btn-primary" onClick={() => setActiveTab('chat')} style={{ width: '100%' }}>
            {isHi ? 'Q&A चैट शुरू करें' : 'Start Q&A Chat'} <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
