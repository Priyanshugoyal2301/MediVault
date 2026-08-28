import React, { useEffect, useState } from 'react';
import { TrendingUp, AlertTriangle, Info, RefreshCw } from 'lucide-react';
import { getTimelineAnomaly, getTimelineSummary } from '../api';

export default function TimelineView({ locale, token }) {
  const [summary, setSummary] = useState([]);
  const [selectedMetric, setSelectedMetric] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const isHi = locale === 'hi-IN';

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const items = await getTimelineSummary(token);
        if (cancelled) return;
        setSummary(items);
        if (items.length && !selectedMetric) {
          const prefer = items.find((i) => i.test_name.toLowerCase().includes('ldl')) || items[0];
          setSelectedMetric(prefer.test_name);
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load timeline');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [token]);

  useEffect(() => {
    if (!selectedMetric) return;
    let cancelled = false;
    (async () => {
      setAnalysis(null);
      setError('');
      try {
        const data = await getTimelineAnomaly(token, selectedMetric);
        if (!cancelled) setAnalysis(data);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load anomaly analysis');
      }
    })();
    return () => { cancelled = true; };
  }, [token, selectedMetric]);

  if (loading) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
        <RefreshCw className="spin" size={32} color="var(--primary)" />
        <p style={{ color: 'var(--text-muted)', marginTop: '1rem' }}>Loading timeline…</p>
      </div>
    );
  }

  if (!summary.length) {
    return (
      <div className="card">
        <h3 style={{ color: '#fff' }}>{isHi ? 'अभी कोई टाइमलाइन डेटा नहीं' : 'No timeline data yet'}</h3>
        <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          {isHi
            ? 'अपलोड टैब से CBC या Lipid डेमो पैनल लोड करें।'
            : 'Load a CBC or Lipid demo panel from the Upload tab to populate trends.'}
        </p>
      </div>
    );
  }

  const history = analysis?.history || [];
  const values = history.map((h) => h.value_numeric).filter((v) => v != null);
  const minV = values.length ? Math.min(...values) : 0;
  const maxV = values.length ? Math.max(...values) : 1;
  const span = maxV - minV || 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="card" style={{ padding: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', overflowX: 'auto' }} role="tablist" aria-label="Lab metrics">
          {summary.map((item) => {
            const isSelected = selectedMetric === item.test_name;
            return (
              <button
                key={item.test_name}
                type="button"
                role="tab"
                aria-selected={isSelected}
                onClick={() => setSelectedMetric(item.test_name)}
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
                }}
              >
                <span>{item.test_name}</span>
                <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>{item.data_point_count} pts</span>
              </button>
            );
          })}
        </div>
      </div>

      {error && (
        <div className="card" role="alert" style={{ color: '#f87171' }}>{error}</div>
      )}

      {analysis && (
        <div className="card">
          <div className="card-title">
            <div>
              <span style={{ fontSize: '1.25rem' }}>{analysis.test_name}</span>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-subtle)', marginTop: 2 }}>
                {history.length} records · scoring: {analysis.method}
                {analysis.method?.toLowerCase?.().includes('isolation')
                  ? ' (fit on this series at request time)'
                  : ''}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <span className={`badge ${analysis.trend === 'rising' ? 'high' : analysis.trend === 'falling' ? 'low' : 'normal'}`}>
                <TrendingUp size={14} /> {analysis.trend}
              </span>
              {analysis.is_anomaly && (
                <span className="badge high">
                  <AlertTriangle size={14} /> anomaly
                </span>
              )}
            </div>
          </div>

          <div
            style={{
              background: 'rgba(0, 0, 0, 0.25)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--bg-card-border)',
              padding: '2rem 1.5rem 1rem',
              margin: '1rem 0 1.5rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', height: 180, gap: '0.5rem' }}>
              {history.map((h) => {
                const height = 20 + ((h.value_numeric - minV) / span) * 140;
                return (
                  <div key={h.id} style={{ flex: 1, textAlign: 'center' }}>
                    <div
                      title={`${h.date_of_test}: ${h.value_numeric}`}
                      style={{
                        height,
                        margin: '0 auto',
                        width: '70%',
                        maxWidth: 48,
                        borderRadius: 6,
                        background: analysis.is_anomaly && h.id === history[history.length - 1]?.id
                          ? '#f87171'
                          : 'var(--primary)',
                      }}
                    />
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-subtle)', marginTop: 6 }}>
                      {h.date_of_test.slice(5)}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#fff' }}>{h.value_numeric}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--bg-card-border)' }}>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--primary)' }}>
              <Info size={16} />
              <strong style={{ color: '#fff', fontSize: '0.9rem' }}>
                {isHi ? 'प्रवृत्ति सारांश' : 'Trend summary (non-diagnostic)'}
              </strong>
            </div>
            <p style={{ color: '#cbd5e1', fontSize: '0.9rem', lineHeight: 1.6 }}>
              {isHi ? analysis.summary_hi : analysis.summary_en}
            </p>
            <p style={{ color: 'var(--text-subtle)', fontSize: '0.75rem', marginTop: '0.75rem' }}>
              z-score: {analysis.z_score ?? '—'} · anomaly score: {analysis.anomaly_score?.toFixed?.(3) ?? analysis.anomaly_score}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
