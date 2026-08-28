import React, { useEffect, useRef, useState } from 'react';
import { Send, ShieldAlert, BookOpen, Bot, User } from 'lucide-react';
import { askQuestion } from '../api';

export default function QAChatView({ locale, token, initialMessages }) {
  const [messages, setMessages] = useState(initialMessages);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [activeCitation, setActiveCitation] = useState(null);
  const messagesEndRef = useRef(null);
  const isHi = locale === 'hi-IN';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const SUGGESTIONS = [
    'What does high LDL mean?',
    'What was my LDL?',
    'I have chest pain and trouble breathing',
  ];

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || isTyping) return;

    const userMsg = { id: Date.now(), role: 'user', content: inputText };
    setMessages((prev) => [...prev, userMsg]);
    const question = inputText;
    setInputText('');
    setIsTyping(true);

    try {
      const data = await askQuestion(token, question, locale, sessionId);
      setSessionId(data.session_id);
      if (data.safety_triggered) {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            role: 'safety',
            content_en: data.answer,
            content_hi: data.answer_hi,
            safety_triggered: true,
            citations: [],
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            role: 'assistant',
            content_en: data.answer,
            content_hi: data.answer_hi,
            citations: data.citations || [],
            safety_triggered: false,
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content_en: `Sorry — Q&A failed: ${err.message}`,
          content_hi: `क्षमा करें — प्रश्न विफल: ${err.message}`,
          citations: [],
          safety_triggered: false,
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 180px)', minHeight: 480, padding: 0 }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {messages.map((msg) => {
          if (msg.role === 'user') {
            return (
              <div key={msg.id} style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <div style={{ maxWidth: '75%', background: 'var(--primary-gradient)', color: '#fff', padding: '0.85rem 1rem', borderRadius: 12 }}>
                  {msg.content}
                </div>
                <User size={20} color="var(--text-muted)" aria-hidden="true" />
              </div>
            );
          }

          const text = isHi ? (msg.content_hi || msg.content_en) : (msg.content_en || msg.content_hi);
          const isSafety = msg.role === 'safety' || msg.safety_triggered;

          return (
            <div key={msg.id} style={{ display: 'flex', gap: '0.5rem' }}>
              {isSafety ? <ShieldAlert size={20} color="#f87171" /> : <Bot size={20} color="var(--primary)" />}
              <div
                style={{
                  maxWidth: '85%',
                  background: isSafety ? 'rgba(248,113,113,0.12)' : 'rgba(255,255,255,0.04)',
                  border: `1px solid ${isSafety ? 'rgba(248,113,113,0.4)' : 'var(--bg-card-border)'}`,
                  padding: '0.85rem 1rem',
                  borderRadius: 12,
                  color: '#e2e8f0',
                  fontSize: '0.9rem',
                  lineHeight: 1.55,
                }}
              >
                <p>{text}</p>
                {!!msg.citations?.length && (
                  <div style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                    {msg.citations.map((c) => (
                      <button
                        key={`${msg.id}-${c.index}`}
                        type="button"
                        className="btn btn-secondary"
                        style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
                        onClick={() => setActiveCitation(c)}
                      >
                        <BookOpen size={12} /> [{c.index}] {c.source}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {isTyping && (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Retrieving cited knowledge…</div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', padding: '0.75rem 1rem 0' }}>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
            disabled={isTyping}
            onClick={() => setInputText(s)}
          >
            {s}
          </button>
        ))}
      </div>

      <form onSubmit={handleSend} style={{ display: 'flex', gap: '0.75rem', padding: '1rem', borderTop: '1px solid var(--bg-card-border)' }}>
        <label htmlFor="qa-input" className="sr-only" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden' }}>
          Ask a health question
        </label>
        <input
          id="qa-input"
          className="chat-input"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={isHi ? 'अपनी रिपोर्ट के बारे में पूछें…' : 'Ask about your labs or guidelines…'}
          disabled={isTyping}
        />
        <button type="submit" className="btn btn-primary" disabled={isTyping || !inputText.trim()} aria-label="Send message">
          <Send size={18} />
        </button>
      </form>

      {activeCitation && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Citation details"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.55)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
          }}
          onClick={() => setActiveCitation(null)}
          onKeyDown={(e) => e.key === 'Escape' && setActiveCitation(null)}
        >
          <div className="card" style={{ maxWidth: 420, width: '90%' }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ color: '#fff', marginBottom: '0.5rem' }}>Citation [{activeCitation.index}]</h3>
            <p style={{ color: 'var(--text-muted)' }}>{activeCitation.source}</p>
            {activeCitation.url && (
              <a href={activeCitation.url} target="_blank" rel="noreferrer" style={{ color: 'var(--primary)' }}>
                Open source
              </a>
            )}
            <button type="button" className="btn btn-secondary" style={{ marginTop: '1rem' }} onClick={() => setActiveCitation(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
