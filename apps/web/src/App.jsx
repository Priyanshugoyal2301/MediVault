import React, { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardView from './views/DashboardView';
import UploadView from './views/UploadView';
import TimelineView from './views/TimelineView';
import QAChatView from './views/QAChatView';
import AuthView from './views/AuthView';
import { getTimelineSummary, listReports, me } from './api';

const WELCOME = [
  {
    id: 1,
    role: 'assistant',
    content_en:
      'Hello! I am your MediVault assistant. Ask about your uploaded lab values or general guideline topics. Answers are template-based with citations — never a diagnosis.',
    content_hi:
      'नमस्ते! मैं आपका मेडीवॉल्ट सहायक हूं। अपनी अपलोड की गई लैब वैल्यूज़ या दिशानिर्देशों के बारे में पूछें। उत्तर उद्धरणों के साथ हैं — निदान नहीं।',
    citations: [],
    safety_triggered: false,
  },
];

export default function App() {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('medivault_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [activeTab, setActiveTab] = useState('dashboard');
  const [locale, setLocale] = useState('en-IN');
  const [dashboardData, setDashboardData] = useState({ anomalies: [], recentReports: [] });
  const [bootError, setBootError] = useState('');

  const handleLogout = () => {
    localStorage.removeItem('medivault_user');
    setUser(null);
  };

  const refreshDashboard = async (token) => {
    try {
      const [reports, timeline] = await Promise.all([
        listReports(token),
        getTimelineSummary(token).catch(() => []),
      ]);
      setDashboardData({
        reportCount: reports.length,
        metricCount: timeline.length,
        anomalies: timeline
          .filter((t) => t.data_point_count >= 3)
          .slice(0, 5)
          .map((t) => ({
            metric: t.test_name,
            text: `Latest ${t.latest_value_numeric ?? t.latest_value_text ?? '—'} ${t.unit || ''}`.trim(),
          })),
        recentReports: reports.slice(0, 8).map((r) => ({
          id: r.id,
          name: r.original_filename,
          date: r.uploaded_at?.slice(0, 10),
          panel: r.parsed_status,
          status: r.parsed_status,
        })),
      });
      setBootError('');
    } catch (err) {
      setBootError(err.message || 'Failed to load dashboard');
    }
  };

  useEffect(() => {
    if (!user?.token) return;
    let cancelled = false;
    (async () => {
      try {
        const profile = await me(user.token);
        if (cancelled) return;
        if (profile.locale_preference) setLocale(profile.locale_preference);
        await refreshDashboard(user.token);
      } catch {
        if (!cancelled) handleLogout();
      }
    })();
    return () => { cancelled = true; };
  }, [user?.token]);

  if (!user?.token) {
    return <AuthView onLogin={setUser} />;
  }

  const titles = {
    dashboard: { en: 'Health Vault Dashboard', subtitle_en: 'Live reports from your authenticated vault' },
    upload: { en: 'Upload & Parse Lab Report', subtitle_en: 'Real API upload or deterministic demo panels' },
    timeline: {
      en: 'Health Timeline & Trend Detection',
      subtitle_en: 'Owner-scoped history · z-score trend · causal statistical monitor (z / %Δ / CUSUM)',
    },
    chat: {
      en: 'Evidence-Grounded Q&A',
      subtitle_en: 'Safety-first BM25+intent RAG (template answers, not a free-form LLM)',
    },
  };

  return (
    <div className="app-container">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} user={user} onLogout={handleLogout} />

      <main className="main-content">
        <Header
          title={titles[activeTab].en}
          subtitle={titles[activeTab].subtitle_en}
          locale={locale}
          setLocale={setLocale}
        />

        {bootError && activeTab === 'dashboard' && (
          <div className="card" role="alert" style={{ color: '#f87171', marginBottom: '1rem' }}>
            {bootError}. Is the API gateway running on port 8000?
          </div>
        )}

        {activeTab === 'dashboard' && (
          <DashboardView locale={locale} setActiveTab={setActiveTab} data={dashboardData} />
        )}

        {activeTab === 'upload' && (
          <UploadView
            locale={locale}
            token={user.token}
            onReportReady={() => refreshDashboard(user.token)}
          />
        )}

        {activeTab === 'timeline' && (
          <TimelineView locale={locale} token={user.token} />
        )}

        {activeTab === 'chat' && (
          <QAChatView locale={locale} token={user.token} initialMessages={WELCOME} />
        )}
      </main>
    </div>
  );
}
