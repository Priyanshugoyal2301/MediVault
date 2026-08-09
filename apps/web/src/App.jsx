import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardView from './views/DashboardView';
import UploadView from './views/UploadView';
import TimelineView from './views/TimelineView';
import QAChatView from './views/QAChatView';
import AuthView from './views/AuthView';

export default function App() {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('medivault_user');
    return saved ? JSON.parse(saved) : { id: '00000000-0000-0000-0000-000000000001', email: 'user@example.com' };
  });

  const [activeTab, setActiveTab] = useState('dashboard');
  const [locale, setLocale] = useState('en-IN');

  const handleLogout = () => {
    localStorage.removeItem('medivault_user');
    setUser(null);
  };

  // Mock data for initial render
  const sampleReports = {
    cbc: {
      title: 'Complete Blood Count (CBC) Panel',
      date: '2025-02-10',
      panel: 'CBC',
      values: [
        { test_name: 'Haemoglobin', value_numeric: 10.5, unit: 'g/dL', reference_range_low: 12.0, reference_range_high: 15.5, status: 'low', explanation_en: 'Your Haemoglobin is 10.5 g/dL, which is below the normal reference range (12.0 - 15.5 g/dL). Lower haemoglobin is commonly associated with iron deficiency anaemia. Please consult your doctor.', explanation_hi: 'आपका हीमोग्लोबिन 10.5 g/dL है, जो सामान्य संदर्भ सीमा (12.0 - 15.5 g/dL) से कम है। कम हीमोग्लोबिन आमतौर पर आयरन की कमी से होने वाले एनीमिया से जुड़ा होता है। कृपया अपने डॉक्टर से परामर्श करें।' },
        { test_name: 'Total Leucocyte Count (WBC)', value_numeric: 7200, unit: 'cells/µL', reference_range_low: 4000, reference_range_high: 11000, status: 'normal', explanation_en: 'Your Total Leucocyte Count is 7,200 cells/µL, which is within the normal reference range (4,000 - 11,000 cells/µL). This indicates normal white blood cell levels.', explanation_hi: 'आपका कुल ल्यूकोसाइट काउंट 7,200 कोशिकाएं/µL है, जो सामान्य संदर्भ सीमा (4,000 - 11,000) के भीतर है।' },
        { test_name: 'Platelet Count', value_numeric: 240000, unit: '/µL', reference_range_low: 150000, reference_range_high: 400000, status: 'normal', explanation_en: 'Your Platelet Count is 240,000 /µL, which falls within the normal reference range (150,000 - 400,000 /µL).', explanation_hi: 'आपका प्लेटलेट काउंट 240,000 /µL है, जो सामान्य सीमा के भीतर है।' },
      ]
    },
    lipid: {
      title: 'Lipid Profile Panel',
      date: '2025-01-15',
      panel: 'Lipid',
      values: [
        { test_name: 'LDL Cholesterol', value_numeric: 165, unit: 'mg/dL', reference_range_low: 0, reference_range_high: 130, status: 'high', explanation_en: 'Your LDL Cholesterol is 165 mg/dL, which is above the optimal reference threshold (< 130 mg/dL). Elevated LDL is associated with increased cardiovascular risk.', explanation_hi: 'आपका एलडीएल कोलेस्ट्रॉल 165 mg/dL है, जो इष्टतम सीमा (< 130 mg/dL) से अधिक है।' },
        { test_name: 'HDL Cholesterol', value_numeric: 45, unit: 'mg/dL', reference_range_low: 40, reference_range_high: 60, status: 'normal', explanation_en: 'Your HDL Cholesterol is 45 mg/dL, which is within the acceptable reference range (> 40 mg/dL).', explanation_hi: 'आपका एचडीएल कोलेस्ट्रॉल 45 mg/dL है, जो सामान्य सीमा में है।' },
        { test_name: 'Triglycerides', value_numeric: 180, unit: 'mg/dL', reference_range_low: 0, reference_range_high: 150, status: 'high', explanation_en: 'Your Triglycerides level is 180 mg/dL, which is mildly elevated (borderline high range 150-199 mg/dL).', explanation_hi: 'आपका ट्राइग्लीसराइड स्तर 180 mg/dL है, जो सीमा रेखा से थोड़ा अधिक है।' },
      ]
    },
    thyroid: {
      title: 'Thyroid Function Panel',
      date: '2024-11-20',
      panel: 'Thyroid',
      values: [
        { test_name: 'TSH', value_numeric: 5.8, unit: 'mIU/L', reference_range_low: 0.4, reference_range_high: 4.0, status: 'high', explanation_en: 'Your TSH is 5.8 mIU/L, which is elevated above the normal reference range (0.4 - 4.0 mIU/L). Elevated TSH suggests your thyroid gland may be underactive (subclinical hypothyroidism).', explanation_hi: 'आपका टीएसएच 5.8 mIU/L है, जो सामान्य सीमा (0.4 - 4.0 mIU/L) से अधिक है। बढ़ा हुआ टीएसएच थकावट और धीमी चयापचय से जुड़ा हो सकता है।' },
        { test_name: 'Free T4', value_numeric: 1.2, unit: 'ng/dL', reference_range_low: 0.8, reference_range_high: 1.8, status: 'normal', explanation_en: 'Your Free T4 is 1.2 ng/dL, which is within normal limits (0.8 - 1.8 ng/dL).', explanation_hi: 'आपका फ्री T4 1.2 ng/dL है, जो सामान्य सीमा में है।' },
      ]
    },
    hba1c: {
      title: 'HbA1c Glycated Haemoglobin Panel',
      date: '2024-09-05',
      panel: 'HbA1c',
      values: [
        { test_name: 'HbA1c', value_numeric: 6.2, unit: '%', reference_range_low: 4.0, reference_range_high: 5.7, status: 'high', explanation_en: 'Your HbA1c is 6.2%, which falls in the pre-diabetes reference category (5.7% - 6.4%). It reflects your average blood sugar over the last 2-3 months.', explanation_hi: 'आपका HbA1c 6.2% है, जो प्री-डायबिटीज श्रेणी (5.7% - 6.4%) में आता है। यह पिछले 2-3 महीनों के औसत रक्त शर्करा को दर्शाता है।' },
      ]
    }
  };

  const timelineData = {
    'LDL Cholesterol': {
      unit: 'mg/dL',
      refRange: '< 130 mg/dL',
      trend: 'rising',
      zscore: 2.15,
      isAnomaly: true,
      summary_en: 'IsolationForest model flagged an anomalous persistent upward trend over 4 consecutive test points (125 → 138 → 152 → 165 mg/dL).',
      summary_hi: 'आइसोलेशन फ़ॉरेस्ट मॉडल ने 4 लगातार परीक्षण बिंदुओं पर लगातार बढ़ती प्रवृत्ति (125 → 138 → 152 → 165 mg/dL) को चिह्नित किया।',
      history: [
        { date: '2023-11-10', value: 125, reportId: 'rep-001', isAnomaly: false },
        { date: '2024-04-15', value: 138, reportId: 'rep-002', isAnomaly: false },
        { date: '2024-09-05', value: 152, reportId: 'rep-003', isAnomaly: false },
        { date: '2025-01-15', value: 165, reportId: 'rep-004', isAnomaly: true },
      ]
    },
    'Haemoglobin': {
      unit: 'g/dL',
      refRange: '12.0 - 15.5 g/dL',
      trend: 'stable',
      zscore: -0.85,
      isAnomaly: false,
      summary_en: 'Haemoglobin values remain stable with minor fluctuations (10.2 - 10.8 g/dL), slightly below lower reference limit.',
      summary_hi: 'हीमोग्लोबिन के मान मामूली उतार-चढ़ाव (10.2 - 10.8 g/dL) के साथ स्थिर बने हुए हैं।',
      history: [
        { date: '2023-10-01', value: 10.8, reportId: 'rep-101', isAnomaly: false },
        { date: '2024-03-12', value: 10.2, reportId: 'rep-102', isAnomaly: false },
        { date: '2024-08-20', value: 10.6, reportId: 'rep-103', isAnomaly: false },
        { date: '2025-02-10', value: 10.5, reportId: 'rep-104', isAnomaly: false },
      ]
    },
    'TSH': {
      unit: 'mIU/L',
      refRange: '0.4 - 4.0 mIU/L',
      trend: 'rising',
      zscore: 1.45,
      isAnomaly: false,
      summary_en: 'TSH shows a mild upward trend across 3 tests (3.2 → 4.5 → 5.8 mIU/L). Baseline Z-score remains within normal model variance.',
      summary_hi: 'टीएसएच 3 परीक्षणों (3.2 → 4.5 → 5.8 mIU/L) में हल्की बढ़ती प्रवृत्ति दर्शाता है।',
      history: [
        { date: '2023-09-15', value: 3.2, reportId: 'rep-201', isAnomaly: false },
        { date: '2024-02-10', value: 4.5, reportId: 'rep-202', isAnomaly: false },
        { date: '2024-11-20', value: 5.8, reportId: 'rep-203', isAnomaly: false },
      ]
    },
    'HbA1c': {
      unit: '%',
      refRange: '< 5.7%',
      trend: 'stable',
      zscore: 0.35,
      isAnomaly: false,
      summary_en: 'HbA1c is stable around 6.0% - 6.2% across historical reports.',
      summary_hi: 'HbA1c ऐतिहासिक रिपोर्टों में 6.0% - 6.2% के आसपास स्थिर है।',
      history: [
        { date: '2023-08-01', value: 6.0, reportId: 'rep-301', isAnomaly: false },
        { date: '2024-01-10', value: 6.1, reportId: 'rep-302', isAnomaly: false },
        { date: '2024-09-05', value: 6.2, reportId: 'rep-303', isAnomaly: false },
      ]
    }
  };

  const initialChatMessages = [
    {
      id: 1,
      role: 'assistant',
      content_en: 'Hello! I am your MediVault AI Assistant. Ask me any question about your medical reports, lab metrics, or health guidelines. All answers are backed by citations.',
      content_hi: 'नमस्ते! मैं आपका मेडीवॉल्ट एआई सहायक हूं। अपनी रिपोर्ट, लैब मेट्रिक्स या स्वास्थ्य दिशानिर्देशों के बारे में कोई भी प्रश्न पूछें।',
      citations: [],
      safety_triggered: false,
    }
  ];

  const dashboardMockData = {
    anomalies: [
      { metric: 'LDL Cholesterol', text: 'Persistent rising trend' }
    ],
    recentReports: [
      { id: 'rep-001', name: 'Complete Blood Count (CBC)', date: '2025-02-10', panel: 'CBC', status: 'complete' },
      { id: 'rep-002', name: 'Lipid Profile Panel', date: '2025-01-15', panel: 'Lipid', status: 'complete' },
      { id: 'rep-003', name: 'Thyroid Function Test', date: '2024-11-20', panel: 'Thyroid', status: 'complete' },
      { id: 'rep-004', name: 'HbA1c Glycated Sugar', date: '2024-09-05', panel: 'HbA1c', status: 'complete' },
    ]
  };

  if (!user) {
    return <AuthView onLogin={setUser} />;
  }

  const titles = {
    dashboard: { en: 'Health Vault Dashboard', subtitle_en: 'Overview of parsed reports, tracked metrics, and anomaly alerts' },
    upload: { en: 'Upload & Parse Lab Report', subtitle_en: 'OCR extraction & plain-language bilingual explainer' },
    timeline: { en: 'Health Timeline & Trend Detection', subtitle_en: 'Longitudinal metric curves & IsolationForest anomaly scores' },
    chat: { en: 'Evidence-Grounded Q&A', subtitle_en: 'Curated knowledge retrieval + patient history with visible citations' },
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

        {activeTab === 'dashboard' && (
          <DashboardView locale={locale} setActiveTab={setActiveTab} mockData={dashboardMockData} />
        )}

        {activeTab === 'upload' && (
          <UploadView locale={locale} sampleReports={sampleReports} />
        )}

        {activeTab === 'timeline' && (
          <TimelineView locale={locale} timelineData={timelineData} />
        )}

        {activeTab === 'chat' && (
          <QAChatView locale={locale} initialMessages={initialChatMessages} />
        )}
      </main>
    </div>
  );
}
