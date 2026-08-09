import React from 'react';
import { Globe } from 'lucide-react';

export default function Header({ title, subtitle, locale, setLocale }) {
  return (
    <header className="top-header">
      <div className="header-title">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>

      <div className="locale-toggle">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', paddingLeft: '0.75rem', color: 'var(--text-subtle)', fontSize: '0.8rem' }}>
          <Globe size={14} />
          <span>Language:</span>
        </div>
        <button
          className={`locale-btn ${locale === 'en-IN' ? 'active' : ''}`}
          onClick={() => setLocale('en-IN')}
        >
          English
        </button>
        <button
          className={`locale-btn ${locale === 'hi-IN' ? 'active' : ''}`}
          onClick={() => setLocale('hi-IN')}
        >
          हिन्दी
        </button>
      </div>
    </header>
  );
}
