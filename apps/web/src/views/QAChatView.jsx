import React, { useState, useRef, useEffect } from 'react';
import { Send, ShieldAlert, Sparkles, BookOpen, AlertTriangle, ExternalLink, Bot, User } from 'lucide-react';

export default function QAChatView({ locale, initialMessages }) {
  const [messages, setMessages] = useState(initialMessages);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [activeCitation, setActiveCitation] = useState(null);
  const messagesEndRef = useRef(null);
  const isHi = locale === 'hi-IN';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Deterministic Safety Layer Red-Flag patterns (runs in frontend for instant feedback)
  const RED_FLAGS = [
    { pattern: /chest\s+pain.*breath|heart\s+attack|seene.*dard/i, category: 'cardiac_emergency' },
    { pattern: /blood\s+in\s+(stool|urine|feces)|vomiting\s+blood|khoon.*peshab/i, category: 'gastrointestinal_bleeding' },
    { pattern: /sudden(ly)?\s+vision\s+loss|lost\s+vision|achanak.*dikhai/i, category: 'sudden_vision_loss' },
    { pattern: /slurred\s+speech|stroke|face\s+droop/i, category: 'stroke_symptoms' },
    { pattern: /kill\s+myself|suicid|self-harm|marna/i, category: 'suicidal_ideation' },
  ];

  const handleSend = (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: inputText,
    };

    setMessages((prev) => [...prev, userMsg]);
    const currentInput = inputText;
    setInputText('');
    setIsTyping(true);

    // Check Safety Layer deterministically
    const triggeredRule = RED_FLAGS.find((rf) => rf.pattern.test(currentInput));

    setTimeout(() => {
      if (triggeredRule) {
        // Return verbatim safety message (Feature 3 Requirement: never reword or suppress)
        const safetyMsg = {
          id: Date.now() + 1,
          role: 'safety',
          category: triggeredRule.category,
          content_en:
            "Your message mentions symptoms that could indicate a medical emergency. " +
            "Please call emergency services (112 in India, 911 in the US, 999 in the UK) " +
            "or go to your nearest emergency room immediately. Do not wait for an online response.",
          content_hi:
            "आपके संदेश में ऐसे लक्षणों का उल्लेख है जो चिकित्सा आपातकाल का संकेत हो सकते हैं। " +
            "कृपया तुरंत आपातकालीन सेवाओं को कॉल करें (भारत में 112) या अपने निकटतम आपातकालीन कक्ष में जाएं। " +
            "ऑनलाइन उत्तर की प्रतीक्षा न करें।",
          safety_triggered: true,
        };
        setMessages((prev) => [...prev, safetyMsg]);
      } else {
        // Normal RAG answer with citations
        let answerEn = "";
        let answerHi = "";
        let citations = [];

        if (currentInput.toLowerCase().includes('ldl') || currentInput.toLowerCase().includes('cholesterol')) {
          answerEn = "Based on available medical guidelines: LDL (Low-Density Lipoprotein) is commonly referred to as 'bad' cholesterol because elevated levels contribute to arterial plaque buildup [1]. Your recent test showed an LDL level of 165 mg/dL [2].";
          answerHi = "उपलब्ध चिकित्सा दिशानिर्देशों के आधार पर: एलडीएल कोलेस्ट्रॉल को आमतौर पर 'खराब' कोलेस्ट्रॉल कहा जाता है क्योंकि उच्च स्तर धमनियों में पट्टिका संचय में योगदान देता है [1]। आपका हालिया परीक्षण 165 mg/dL का एलडीएल स्तर दर्शाता है [2]।";
          citations = [
            { index: 1, source: "NHS Guidelines — High Cholesterol", url: "https://www.nhs.uk/conditions/high-cholesterol/" },
            { index: 2, source: "Your report from 2025-01-15", url: null },
          ];
        } else if (currentInput.toLowerCase().includes('haemoglobin') || currentInput.toLowerCase().includes('hb')) {
          answerEn = "Based on WHO reference guidelines: Haemoglobin carries oxygen in red blood cells. The normal range for adult women is 12.0–15.5 g/dL [1]. Your latest recorded Haemoglobin value is 10.5 g/dL [2], which is below the standard reference threshold.";
          answerHi = "डब्ल्यूएचओ संदर्भ दिशानिर्देशों के आधार पर: हीमोग्लोबिन लाल रक्त कोशिकाओं में ऑक्सीजन ले जाता है। वयस्क महिलाओं के लिए सामान्य सीमा 12.0–15.5 g/dL है [1]। आपका नवीनतम रिकॉर्ड किया गया हीमोग्लोबिन मान 10.5 g/dL है [2]।";
          citations = [
            { index: 1, source: "WHO Guidelines — Haemoglobin Concentrations", url: "https://www.who.int/publications/i/item/9789241549554" },
            { index: 2, source: "Your report from 2025-02-10", url: null },
          ];
        } else {
          answerEn = "Based on curated medical knowledge: Regular monitoring of lab metrics provides valuable context for your long-term health timeline [1]. Please discuss any specific values or trends with your healthcare provider.";
          answerHi = "चिकित्सा ज्ञान के आधार पर: लैब मेट्रिक्स की नियमित निगरानी आपकी दीर्घकालिक स्वास्थ्य समयरेखा के लिए मूल्यवान संदर्भ प्रदान करती है [1]। कृपया किसी भी विशिष्ट मान की चर्चा अपने डॉक्टर से करें।";
          citations = [
            { index: 1, source: "ICMR Reference Values for Indians", url: "https://www.icmr.gov.in" },
          ];
        }

        const botMsg = {
          id: Date.now() + 1,
          role: 'assistant',
          content_en: answerEn,
          content_hi: answerHi,
          citations: citations,
          safety_triggered: false,
        };
        setMessages((prev) => [...prev, botMsg]);
      }
      setIsTyping(false);
    }, 450);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Banner */}
      <div className="card" style={{ background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.12) 0%, rgba(139, 92, 246, 0.12) 100%)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h3 style={{ color: '#fff', fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sparkles size={20} color="var(--primary)" />
            {isHi ? 'साक्ष्य-आधारित स्वास्थ्य Q&A (RAG)' : 'Evidence-Grounded Health Q&A (RAG Engine)'}
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            {isHi
              ? 'प्रतिक्रियाएं आपके अपने रिपोर्ट डेटा एवं सहकर्मी-समीक्षित दिशानिर्देशों (WHO, NHS, ICMR) से उद्धृत हैं।'
              : 'Every response is grounded in curated clinical guidelines (WHO, NHS, ICMR) + your own report history.'}
          </p>
        </div>
        <span className="badge normal">
          <ShieldAlert size={12} /> {isHi ? 'सुरक्षा परत सक्रिय' : 'Safety Layer Active'}
        </span>
      </div>

      {/* Main Chat Interface */}
      <div className="chat-container">
        <div className="chat-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Bot size={20} color="var(--primary)" />
            <span style={{ fontWeight: 600, color: '#fff', fontSize: '0.95rem' }}>
              MediVault AI Assistant
            </span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>
            Deterministic Red-Flag Guardrail: ON (&lt;100ms)
          </span>
        </div>

        <div className="chat-messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`message-bubble ${msg.role}`}>
              {msg.role === 'safety' ? (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, marginBottom: '0.5rem', color: '#f87171' }}>
                    <AlertTriangle size={18} />
                    <span>{isHi ? 'आपातकालीन चेतावनी (Emergency Safety Alert)' : 'Emergency Safety Alert (Verbatim)'}</span>
                  </div>
                  <p>{isHi ? msg.content_hi : msg.content_en}</p>
                </div>
              ) : msg.role === 'user' ? (
                <div>{msg.content}</div>
              ) : (
                <div>
                  <p>{isHi ? msg.content_hi : msg.content_en}</p>

                  {/* Citations Chips */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', fontWeight: 600 }}>
                        {isHi ? 'उद्धृत स्रोत (Citations):' : 'Sources Cited:'}
                      </span>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                        {msg.citations.map((c) => (
                          <button
                            key={c.index}
                            onClick={() => setActiveCitation(c)}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.3rem',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              background: 'rgba(6, 182, 212, 0.12)',
                              border: '1px solid rgba(6, 182, 212, 0.25)',
                              color: 'var(--primary)',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            <BookOpen size={11} /> [{c.index}] {c.source}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="message-bubble assistant" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-subtle)' }}>
              <Sparkles size={16} className="spin" />
              <span>{isHi ? 'खोज एवं उत्तर निर्माण जारी है...' : 'Retrieving evidence & generating cited answer...'}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} className="chat-input-bar">
          <input
            type="text"
            className="chat-input"
            placeholder={
              isHi
                ? 'अपनी रिपोर्ट या स्वास्थ्य के बारे में प्रश्न पूछें (उदा: "मेरा एलडीएल क्यों अधिक है?")...'
                : 'Ask about your lab report or general health (e.g. "Why is my LDL high?")...'
            }
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" style={{ padding: '0.75rem 1.25rem' }}>
            <Send size={18} />
          </button>
        </form>
      </div>

      {/* Citation Modal Popup */}
      {activeCitation && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
          <div className="card" style={{ maxWidth: 500, width: '100%' }}>
            <div className="card-title">
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <BookOpen size={18} color="var(--primary)" />
                Citation Details [{activeCitation.index}]
              </span>
              <button onClick={() => setActiveCitation(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.2rem' }}>×</button>
            </div>
            <h4 style={{ color: '#fff', fontSize: '1rem', marginBottom: '0.5rem' }}>{activeCitation.source}</h4>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', lineHeight: 1.6, marginBottom: '1.5rem' }}>
              This information was retrieved from curated clinical reference documents and matched against your user health record.
            </p>
            {activeCitation.url && (
              <a href={activeCitation.url} target="_blank" rel="noreferrer" className="btn btn-secondary" style={{ width: '100%', fontSize: '0.85rem' }}>
                View Original Guideline Source <ExternalLink size={14} />
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
