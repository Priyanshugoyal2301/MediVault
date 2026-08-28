import React, { useState } from 'react';
import { ShieldCheck, Mail, Lock, UserPlus, LogIn, ArrowRight } from 'lucide-react';
import { login, me, register } from '../api';

export default function AuthView({ onLogin }) {
  // Default to Register for first-time demo; switch to Sign In if email already exists
  const [isRegister, setIsRegister] = useState(true);
  const [email, setEmail] = useState('judge@example.com');
  const [password, setPassword] = useState('password123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const tokenRes = isRegister
        ? await register(email, password, 'en-IN')
        : await login(email, password);
      const profile = await me(tokenRes.access_token);
      const user = {
        id: profile.id,
        email: profile.email,
        locale: profile.locale_preference,
        token: tokenRes.access_token,
      };
      localStorage.setItem('medivault_user', JSON.stringify(user));
      onLogin(user);
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', background: 'var(--bg-dark)' }}>
      <div className="card" style={{ maxWidth: 420, width: '100%', padding: '2.5rem 2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div className="brand-icon" style={{ margin: '0 auto 1rem auto', width: 50, height: 50 }}>
            <ShieldCheck size={28} color="#fff" />
          </div>
          <h2 style={{ fontFamily: 'var(--font-display)', color: '#fff', fontSize: '1.6rem', fontWeight: 700 }}>
            MediVault<span style={{ color: 'var(--primary)' }}>.ai</span>
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            {isRegister ? 'Create your private health vault' : 'Sign in to access your health record'}
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <label htmlFor="email" style={{ display: 'block', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.4rem' }}>
              EMAIL ADDRESS
            </label>
            <div style={{ position: 'relative' }}>
              <Mail size={18} color="var(--text-subtle)" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} aria-hidden="true" />
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                className="chat-input"
                style={{ paddingLeft: '2.5rem' }}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" style={{ display: 'block', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.4rem' }}>
              PASSWORD
            </label>
            <div style={{ position: 'relative' }}>
              <Lock size={18} color="var(--text-subtle)" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} aria-hidden="true" />
              <input
                id="password"
                type="password"
                required
                minLength={8}
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                className="chat-input"
                style={{ paddingLeft: '2.5rem' }}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <div role="alert" style={{ color: '#f87171', fontSize: '0.85rem' }}>
              {error}
            </div>
          )}

          <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%', marginTop: '0.5rem', padding: '0.85rem' }}>
            {loading ? 'Please wait…' : isRegister ? (
              <>
                <UserPlus size={18} /> Register Vault Account
              </>
            ) : (
              <>
                <LogIn size={18} /> Sign In
              </>
            )}{' '}
            {!loading && <ArrowRight size={16} />}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '1.75rem', paddingTop: '1.25rem', borderTop: '1px solid var(--bg-card-border)', fontSize: '0.85rem', color: 'var(--text-subtle)' }}>
          {isRegister ? 'Already have an account?' : "Don't have a vault account yet?"}{' '}
          <button
            type="button"
            onClick={() => setIsRegister(!isRegister)}
            style={{ background: 'none', border: 'none', color: 'var(--primary)', fontWeight: 600, cursor: 'pointer' }}
          >
            {isRegister ? 'Sign In' : 'Register Now'}
          </button>
        </div>
      </div>
    </div>
  );
}
