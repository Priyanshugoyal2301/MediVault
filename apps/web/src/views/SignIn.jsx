import React, {useState} from 'react';
import {ArrowRight, Files, HeartHandshake, History, LockKeyhole} from 'lucide-react';
import {request} from '../api';
import {Brand, ErrorNotice, Field} from '../components/UI';

export default function SignIn({onLogin}) {
  const [register, setRegister] = useState(false);
  const [mfaRequired,setMfaRequired] = useState(false);
  const [busy,setBusy] = useState(false); const [error,setError] = useState('');
  const [notice,setNotice] = useState('');
  async function submit(e) {
    e.preventDefault(); const data = Object.fromEntries(new FormData(e.currentTarget)); setBusy(true); setError('');
    try {
      if(register) {
        await request('/auth/register', {method:'POST',body:{...data,locale_preference:'en-IN'}});
        setRegister(false); setMfaRequired(false);
        setNotice('Request received. Continue to sign in. If an account already exists, use its current password.');
        return;
      }
      setNotice('');
      await request('/auth/login', {method:'POST',body:data});
      onLogin(await request('/auth/me'));
    }
    catch(e) {if(e.mfaRequired)setMfaRequired(true);setError(e);} finally {setBusy(false);}
  }
  return <main className="auth-page"><section className="auth-story"><Brand/><div><p className="eyebrow">A LITTLE MORE CLARITY. A LOT MORE CARE.</p><h1>Your health story.<br/><em>All together.</em></h1><p className="lead">Keep the records that matter close, and the people who care for you connected.</p><div className="story-features">{[[Files,'One place for your records','Reports, prescriptions and the details between visits.'],[History,'A history you can take with you','Remember what happened, when, and what came next.'],[HeartHandshake,'Care that includes your family','Choose who can see your records, and for how long.']].map(([Icon,title,copy]) => <div key={title}><Icon size={22}/><div><h3>{title}</h3><p>{copy}</p></div></div>)}</div></div><p className="auth-foot">Designed around people. Built for continuity of care.</p></section>
    <section className="auth-form"><div className="auth-form-inner"><span className="eyebrow">YOUR PERSONAL HEALTH SPACE</span><h2>{register ? 'Start your health vault' : 'Welcome back'}</h2><p>{register ? 'Create your adult account. You can add your family after signing in.' : 'Sign in to pick up where you left off.'}</p>{notice&&<p role="status">{notice}</p>}<form onSubmit={submit}><Field label="Email address" name="email" type="email" required autoComplete="email" maxLength={255}/><Field label="Password" name="password" type="password" required minLength={8} maxLength={72} autoComplete={register ? 'new-password' : 'current-password'} help={register ? 'Use at least 8 characters and a password you do not use elsewhere.' : undefined}/>{!register&&mfaRequired&&<Field label="Two-step verification code" name="verification_code" required autoComplete="one-time-code" maxLength={80} help="Your account has two-step verification enabled. Use your authenticator app or a saved recovery code. This is not an API key."/>}<ErrorNotice error={error}/><button className="button primary full" disabled={busy}>{busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'}<ArrowRight size={18}/></button></form><p className="auth-switch">{register ? 'Already have an account?' : 'New to MediVault?'} <button onClick={() => {setRegister(!register);setMfaRequired(false);setError('');setNotice('');}}>{register ? 'Sign in' : 'Create an account'}</button></p><div className="privacy-note"><LockKeyhole size={18}/><p>Your medical records are personal. Sharing is always an explicit choice.</p></div></div></section>
  </main>;
}
