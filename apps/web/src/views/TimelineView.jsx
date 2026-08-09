import React, { useState } from 'react';
import { TrendingUp, AlertTriangle, Calendar, Activity, CheckCircle, Info } from 'lucide-react';

export default function TimelineView({ locale, timelineData }) {
  const [selectedMetric, setSelectedMetric] = useState('LDL Cholesterol');
  const isHi = locale === 'hi-IN';

  const currentMetricData = timelineData[selectedMetric] || timelineData['Haemoglobin'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Metric Selector Tabs */}
      <div className="card" style={{ padding: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', overflowX: 'auto', paddingBottom: '0.25rem' }}>
          {Object.keys(timelineData).map((metric) => {
            const data = timelineData[metric];
            const isSelected = selectedMetric === metric;
            const hasAnomaly = data.trend === 'rising' && metric.includes('LDL');

            return (
              <button
                key={metric}
                onClick={() => setSelectedMetric(metric)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.6rem',
                  padding: '0.65rem 1.15rem',
                  borderRadius: 'var(--radius-md)',
                  background: isSelected ? 'var(--primary-gradient)' : 'rgba(255, 255, 255, 0.04)',
                  border: isSelected ? 'none' : '1px solid var(--bg-card-border)',
                  color: isSelected ? '#fff' : 'var(--text-muted)',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.2s',
                  boxShadow: isSelected ? '0 4px 15px var(--primary-glow)' : 'none',
                }}
              >
                <span>{metric}</span>
                {hasAnomaly && (
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f87171' }} />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Metric Trend Card */}
      <div className="card">
        <div className="card-title">
          <div>
            <span style={{ fontSize: '1.25rem' }}>{selectedMetric}</span>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-subtle)', fontWeight: 400, marginTop: '2px' }}>
              {currentMetricData.history.length} {isHi ? 'ऐतिहासिक परीक्षण रिकॉर्ड' : 'historical test records'} • Unit: {currentMetricData.unit}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className={`badge ${currentMetricData.trend === 'rising' ? 'high' : currentMetricData.trend === 'falling' ? 'low' : 'normal'}`}>
              <TrendingUp size={14} /> {isHi ? (currentMetricData.trend === 'rising' ? 'बढ़ता हुआ' : 'स्थिर') : `${currentMetricData.trend.toUpperCase()} TREND`}
            </span>
          </div>
        </div>

        {/* Visual Trend Chart Container */}
        <div
          style={{
            background: 'rgba(0, 0, 0, 0.25)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--bg-card-border)',
            padding: '2rem 1.5rem 1rem 1.5rem',
            margin: '1rem 0 1.5rem 0',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', height: 180, position: 'relative', padding: '0 1rem' }}>
            {/* Reference Range Band Overlay */}
            <div
              style={{
                position: 'absolute',
                left: 0,
                right: 0,
                top: '30%',
                bottom: '30%',
                background: 'rgba(16, 185, 129, 0.05)',
                borderTop: '1px dashed rgba(16, 185, 129, 0.3)',
                borderBottom: '1px dashed rgba(16, 185, 129, 0.3)',
                pointerEvents: 'none',
              }}
            >
              <span style={{ position: 'absolute', right: 8, top: 4, fontSize: '0.7rem', color: '#34d399' }}>
                Ref: {currentMetricData.refRange}
              </span>
            </div>

            {/* Data Points */}
            {currentMetricData.history.map((pt, i) => {
              const maxVal = Math.max(...currentMetricData.history.map((h) => h.value)) * 1.2;
              const heightPct = Math.min(100, Math.max(15, (pt.value / maxVal) * 100));

              return (
                <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem', zIndex: 2, flex: 1 }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 700, color: pt.isAnomaly ? '#f87171' : '#fff' }}>
                    {pt.value}
                  </span>

                  <div
                    style={{
                      width: 14,
                      height: `${heightPct}%`,
                      maxHeight: 130,
                      background: pt.isAnomaly ? 'linear-gradient(180deg, #f87171 0%, #ef4444 100%)' : 'var(--primary-gradient)',
                      borderRadius: 'var(--radius-full)',
                      boxShadow: pt.isAnomaly ? '0 0 12px rgba(248, 113, 113, 0.5)' : '0 0 10px var(--primary-glow)',
                    }}
                  />

                  <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', whiteSpace: 'nowrap' }}>
                    {pt.date}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Anomaly Detection Explanation */}
        <div style={{ padding: '1rem 1.25rem', borderRadius: 'var(--radius-md)', background: currentMetricData.isAnomaly ? 'rgba(244, 63, 94, 0.08)' : 'rgba(255, 255, 255, 0.03)', border: `1px solid ${currentMetricData.isAnomaly ? 'rgba(244, 63, 94, 0.3)' : 'var(--bg-card-border)'}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
            {currentMetricData.isAnomaly ? <AlertTriangle size={18} color="#f87171" /> : <Activity size={18} color="var(--primary)" />}
            <span style={{ fontWeight: 600, color: '#fff', fontSize: '0.9rem' }}>
              {isHi ? 'प्रवृत्ति विश्लेषण एवं एनोमली स्कोर' : 'Trend Analysis & IsolationForest Anomaly Score'}
            </span>
            <span className="badge normal" style={{ marginLeft: 'auto', fontSize: '0.7rem' }}>
              Z-Score: {currentMetricData.zscore}
            </span>
          </div>
          <p style={{ color: '#cbd5e1', fontSize: '0.875rem', lineHeight: 1.6 }}>
            {isHi ? currentMetricData.summary_hi : currentMetricData.summary_en}
          </p>
        </div>
      </div>

      {/* Chronological Event History Table */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--bg-card-border)' }}>
          <h4 style={{ color: '#fff', fontSize: '1rem', fontWeight: 600 }}>
            {isHi ? 'समयक्रम इतिहास लॉग' : 'Chronological History Log'} — {selectedMetric}
          </h4>
        </div>
        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>{isHi ? 'परीक्षण तिथि' : 'Date of Test'}</th>
                <th>{isHi ? 'मान' : 'Value'}</th>
                <th>{isHi ? 'इकाई' : 'Unit'}</th>
                <th>{isHi ? 'स्रोत रिपोर्ट' : 'Source Report'}</th>
                <th>{isHi ? 'स्थिति' : 'Status'}</th>
              </tr>
            </thead>
            <tbody>
              {currentMetricData.history.map((pt, idx) => (
                <tr key={idx}>
                  <td style={{ color: '#fff', fontWeight: 500 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Calendar size={14} color="var(--text-subtle)" />
                      {pt.date}
                    </div>
                  </td>
                  <td style={{ fontWeight: 700, color: pt.isAnomaly ? '#f87171' : '#34d399' }}>{pt.value}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{currentMetricData.unit}</td>
                  <td style={{ color: 'var(--text-subtle)', fontSize: '0.8rem' }}>Report #{pt.reportId.slice(0, 8)}</td>
                  <td>
                    <span className={`badge ${pt.isAnomaly ? 'high' : 'normal'}`}>
                      {pt.isAnomaly ? (isHi ? 'असामान्य' : 'Out of range') : (isHi ? 'सामान्य' : 'Normal')}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
