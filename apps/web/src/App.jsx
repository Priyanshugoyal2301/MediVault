import React, {useCallback, useEffect, useRef, useState} from 'react';
import {ArrowRight, CalendarDays, ClipboardList, FileText, HeartHandshake, Home, LogOut, Menu, MessageCircle, Pill, Plus, RefreshCw, ShieldCheck, ShieldAlert, Stethoscope, Users, X} from 'lucide-react';
import {request, patientPath, scoped, listAll} from './api';
import {Badge, Brand, dateText, Empty, ErrorNotice, initials, SectionTitle} from './components/UI';
import SignIn from './views/SignIn';
import CareRecords, {RECORDS} from './views/CareRecords';
import Family, {ProfileForm, Sharing} from './views/Family';
import Documents from './views/Documents';
import Explain from './views/Explain';
import Doctor from './views/Doctor';
import LabHistory from './views/LabHistory';
import Consultation from './views/Consultation';
import AccountSecurity from './views/AccountSecurity';

const NAV = [
  ['overview','Overview',Home],['documents','Documents',FileText],['encounters','Visit timeline',ClipboardList],
  ['labs','Lab history',ClipboardList],['medications','Medications',Pill],['allergies','Allergies & reactions',ShieldAlert],['appointments','Appointments',CalendarDays],
  ['vaccinations','Vaccinations',ShieldCheck],['referrals','Referrals',ClipboardList],['claims','Bills & claims',ClipboardList],['benefits','Benefits wallet',ClipboardList],['summary','Consultation summary',ClipboardList],['family','Family circle',Users],['sharing','Sharing & privacy',ShieldCheck],['explain','Understand reports',MessageCircle],['doctor','Doctor workspace',Stethoscope],['settings','Account security',ShieldCheck]
];
const emptyData = () => Object.fromEntries(['documents',...Object.keys(RECORDS)].map(key=>[key,[]]));
export default function App() {
  const [user,setUser]=useState(null);const [booting,setBooting]=useState(true);const [bootError,setBootError]=useState('');
  const [profiles,setProfiles]=useState([]);const [selected,setSelected]=useState('');const [tab,setTab]=useState('overview');
  const [data,setData]=useState(emptyData);const [loadedPatient,setLoadedPatient]=useState('');const [error,setError]=useState('');const [loading,setLoading]=useState(false);
  const [menu,setMenu]=useState(false);const [adding,setAdding]=useState(false);const requestVersion=useRef(0);
  const patient=profiles.find(p=>p.id===selected);
  const clearSession=useCallback(()=>{requestVersion.current++;setUser(null);setProfiles([]);setSelected('');setData(emptyData());setLoadedPatient('');setLoading(false);setError('');setMenu(false);setAdding(false);setTab('overview');},[]);
  useEffect(()=>{window.addEventListener('medivault:session-expired',clearSession);return()=>window.removeEventListener('medivault:session-expired',clearSession);},[clearSession]);
  const boot=useCallback(async()=>{setBooting(true);setBootError('');try{setUser(await request('/auth/me'));}catch(e){if([401,403,404].includes(e.status))setUser(null);else setBootError(e);}finally{setBooting(false);}},[]);
  useEffect(()=>{localStorage.removeItem('medivault_user');boot();},[boot]);
  const loadProfiles=useCallback(async()=>{const result=await request('/care/patients');setProfiles(result);setSelected(id=>result.some(p=>p.id===id)?id:result[0]?.id||'');return result;},[]);
  useEffect(()=>{if(user)loadProfiles().catch(setError);},[user,loadProfiles]);
  const reload=useCallback(async()=>{
    const version=++requestVersion.current;
    if(!patient?.scopes.length){setData(emptyData());return;}
    setLoading(true);setError('');
    try {
      const next=emptyData();
      await Promise.all(patient.scopes.map(async scope=>{next[scope]=await listAll(scope==='documents'?scoped('/reports',patient.id):patientPath(patient.id,scope));}));
      if(version===requestVersion.current){setData(next);setLoadedPatient(patient.id);}
    } catch(e){if(version===requestVersion.current){setData(emptyData());setError(e);}}
    finally{if(version===requestVersion.current)setLoading(false);}
  },[patient]);
  useEffect(()=>{setData(emptyData());reload();return()=>{requestVersion.current++;};},[reload]);
  function navigate(next){setTab(next);setMenu(false);window.scrollTo({top:0,behavior:'instant'});}
  function select(id){setSelected(id);setTab('overview');setMenu(false);}
  async function logout(){try{await request('/auth/logout',{method:'POST'});clearSession();}catch(e){if(e.status===401)clearSession();else setError(e);}}
  if(booting)return <main className="startup"><Brand/><p role="status">Opening your health space…</p></main>;
  if(bootError)return <main className="startup"><Brand/><h1>We could not reach your vault.</h1><p>Please check your connection and try again.</p><ErrorNotice error={bootError}/><button className="button primary" onClick={boot}>Try again</button></main>;
  if(!user)return <SignIn onLogin={setUser}/>;
  const canOpen = key => ['overview','family','doctor','settings'].includes(key) || (key==='summary'?patient?.scopes.some(s=>['medications','allergies','encounters','appointments'].includes(s)):key==='sharing'?patient?.can_manage:patient?.scopes.includes(['explain','labs'].includes(key)?'documents':key));
  const currentAccessible=canOpen(tab);
  const visibleData=loadedPatient===patient?.id?data:emptyData();
  return <div className="app-shell"><a className="skip-link" href="#main">Skip to content</a>{menu && <button className="nav-scrim" aria-label="Close navigation" onClick={()=>setMenu(false)}/>}
    <aside className={`sidebar ${menu?'open':''}`}><div className="sidebar-brand"><Brand/><button className="icon-button mobile-only" aria-label="Close navigation" onClick={()=>setMenu(false)}><X size={20}/></button></div><p className="nav-caption">YOUR HEALTH SPACE</p><nav aria-label="Main navigation">{NAV.filter(([key])=>canOpen(key)).map(([key,label,Icon])=><button key={key} onClick={()=>navigate(key)} className={`nav-item ${tab===key?'active':''}`} aria-current={tab===key?'page':undefined}><Icon size={19}/><span>{label}</span>{tab===key&&<span className="nav-dot"/>}</button>)}</nav><div className="sidebar-bottom"><div className="care-note"><HeartHandshake size={23}/><strong>Care starts with clarity.</strong><p>Your history helps you have better conversations with your doctor.</p></div><button className="account-button" onClick={logout}><span className="avatar">{initials(user.email)}</span><span><strong>My account</strong><small>{user.email}</small></span><LogOut size={17}/></button></div></aside>
    <div className="workspace"><header className="topbar"><div className="topbar-title"><button className="icon-button mobile-only" aria-label="Open navigation" onClick={()=>setMenu(true)}><Menu size={22}/></button><span className="breadcrumb">My health <span>/</span> <strong>{NAV.find(n=>n[0]===tab)?.[1]}</strong></span></div><div className="profile-switch"><span className="avatar small">{initials(patient?.display_name)}</span><label className="sr-only" htmlFor="patient-switch">Active patient record</label><select id="patient-switch" value={selected} onChange={e=>select(e.target.value)}>{!profiles.length&&<option value="">No patient profile</option>}{profiles.map(p=><option key={p.id} value={p.id}>{p.display_name}{p.relationship==='child'?' · Child':''}</option>)}</select></div></header>
    <main id="main" className="main-content" tabIndex={-1}><ErrorNotice error={error}/>{error&&<button className="button" onClick={()=>{loadProfiles().then(reload).catch(setError);}}>Try again</button>}
      {tab==='settings'?<AccountSecurity user={user} onUpdated={setUser} onSignedOut={()=>{setUser(null);setProfiles([]);setData(emptyData());}}/>:tab==='family'?<Family profiles={profiles} selected={patient} select={select} reload={loadProfiles}/>:tab==='doctor'?<Doctor reload={loadProfiles}/>:!patient?<section className="welcome-panel"><span className="eyebrow">WELCOME TO MEDIVAULT</span><h1>Make room for your health story.</h1><p>Create your patient profile to start collecting records, tracking visits, and connecting your family.</p><button className="button primary" onClick={()=>setAdding(true)}><Plus size={18}/>Create my profile</button><button className="text-action" onClick={()=>navigate('doctor')}>I am here as a doctor <ArrowRight size={16}/></button></section>:!patient.scopes.length?<Empty icon={ShieldCheck} title="This profile is awaiting verification">Medical records stay locked until guardian verification is complete. If this person has turned 18, their record needs to transition to an adult account.</Empty>:!currentAccessible?<Empty title="This category is not shared with you">Select an available category from the navigation.</Empty>:<div key={patient.id + tab} className="view-enter">
        {loading&&<div className="loading-strip" role="status">Updating records…</div>}
        {tab==='overview'&&<Overview patient={patient} data={visibleData} navigate={navigate} loading={loading}/>}
        {tab==='documents'&&<Documents patient={patient} rows={visibleData.documents} reload={reload}/>}
        {Object.hasOwn(RECORDS,tab)&&<CareRecords kind={tab} patient={patient} rows={visibleData[tab]} reload={reload}/>}
        {tab==='summary'&&<Consultation patient={patient}/>}
        {tab==='labs'&&<LabHistory patient={patient}/>}
        {tab==='sharing'&&<Sharing patient={patient}/>}{tab==='explain'&&<Explain patient={patient}/>}
      </div>}
      <footer className="page-footer"><span>MediVault · Your records. Your choices.</span><span>Medical decisions belong with your clinician.</span></footer>
    </main><nav className="bottom-nav" aria-label="Quick navigation">{[['overview','Home',Home],['documents','Records',FileText],['family','Family',Users]].filter(([key])=>canOpen(key)).map(([key,label,Icon])=><button key={key} onClick={()=>navigate(key)} aria-current={tab===key?'page':undefined}><Icon size={21}/><span>{label}</span></button>)}<button onClick={()=>setMenu(true)}><Menu size={21}/><span>More</span></button></nav></div>
    {adding&&<ProfileForm first onClose={()=>setAdding(false)} onSaved={loadProfiles}/>}
  </div>;
}
function Overview({patient,data,navigate,loading}) {
  const taking=data.medications.filter(m=>m.status==='taking');
  const next=data.appointments.filter(a=>!['cancelled','completed'].includes(a.status)&&new Date(a.scheduled_at)>new Date()).sort((a,b)=>a.scheduled_at.localeCompare(b.scheduled_at))[0];
  const metrics=[['documents','Documents',FileText,data.documents.length],['medications','Reported taking',Pill,taking.length],['encounters','Recorded visits',ClipboardList,data.encounters.length]];
  return <><div className="greeting"><div><p className="eyebrow">A CLEARER PICTURE OF YOUR HEALTH</p><h1>{patient.can_manage&&patient.relationship==='self'?`Hello, ${patient.display_name.split(' ')[0]}.`:`${patient.display_name}’s health space`}</h1><p>Your records, your care, and the people beside you.</p></div><span className="today">{dateText(new Date().toISOString())}</span></div>
    <div className="overview-grid"><section className="health-hero"><div><span className="hero-label"><ShieldCheck size={15}/>YOUR PERSONAL HEALTH VAULT</span><h2>Every chapter of your health.<br/><em>In one place.</em></h2><p>Keep a clear record today, for a better conversation at your next appointment.</p>{patient.scopes.includes('documents')&&<button className="button primary" onClick={()=>navigate('documents')}><FileText size={18}/>{patient.writable_scopes.includes('documents')?'Add a health document':'View health documents'}</button>}</div><div className="hero-art" aria-hidden="true"><div className="art-orbit"/><div className="art-card"><span className="art-cross">+</span><span className="art-line long"/><span className="art-line"/><span className="art-line long"/><div className="art-check"><ShieldCheck size={32}/></div></div><span className="art-pill"><HeartHandshake size={17}/>Care, connected</span></div></section>
    <section className="panel next-visit"><div className="panel-heading"><h3>Next appointment</h3><CalendarDays size={20}/></div>{next?<><div className="appointment-date">{dateText(next.scheduled_at)}</div><h3>{next.facility}</h3><p>{next.clinician || next.purpose}</p><Badge>{next.status}</Badge><button className="text-action" onClick={()=>navigate('appointments')}>View appointment<ArrowRight size={16}/></button></>:<><span className="calendar-illustration"><CalendarDays size={33}/></span><h3>{patient.scopes.includes('appointments')?'No upcoming visits':'Appointments are not shared'}</h3><p>{patient.scopes.includes('appointments')?'Keep your next appointment and preparation notes close.':'The patient controls which categories are available.'}</p>{patient.scopes.includes('appointments')&&<button className="text-action" onClick={()=>navigate('appointments')}>Plan a visit<ArrowRight size={16}/></button>}</>}</section></div>
    <div className="stat-grid">{metrics.filter(([key])=>patient.scopes.includes(key)).map(([key,label,Icon,count])=><button className="stat-card" onClick={()=>navigate(key)} key={key}><span className="stat-icon"><Icon size={22}/></span><span><strong>{loading?'—':count}</strong><small>{label}</small></span><ArrowRight size={17}/></button>)}</div>
    <div className="overview-grid"><section className="panel"><div className="panel-heading"><div><h3>Recent documents</h3><p>The latest additions to your story</p></div>{patient.scopes.includes('documents')&&<button className="text-action" onClick={()=>navigate('documents')}>View all<ArrowRight size={16}/></button>}</div>{data.documents.length?data.documents.slice(0,4).map(doc=><button className="document-preview" key={doc.id} onClick={()=>navigate('documents')}><span className="record-icon"><FileText size={20}/></span><span><strong>{doc.original_filename}</strong><small>{doc.document_date?dateText(doc.document_date):`Uploaded ${dateText(doc.uploaded_at)}`} · {doc.document_kind}</small></span><Badge tone={doc.parsed_status==='complete'?'success':'neutral'}>{doc.parsed_status==='complete'?'Review ready':doc.parsed_status}</Badge></button>):<Empty icon={FileText} title={patient.scopes.includes('documents')?'Your first record starts here':'Documents are not shared'}>{patient.scopes.includes('documents')?'Add a report or prescription. Your history will grow with you.':'The patient controls which categories are available.'}</Empty>}</section>
    <section className="safety-card"><span className="safety-icon"><ShieldAlert size={24}/></span><p className="eyebrow">BEFORE YOUR NEXT VISIT</p><h3>Small details.<br/>Important conversations.</h3><p>Review medication use and any suspected reactions with your doctor.</p><div className="safety-status">{!patient.scopes.includes('allergies')?'Allergy records are not shared':data.allergies.length?`${data.allergies.filter(a=>a.status!=='refuted').length} reported or confirmed reactions`:'Allergy status: unknown'}</div>{patient.scopes.includes('allergies')&&<button className="text-action" onClick={()=>navigate('allergies')}>Review allergy history<ArrowRight size={16}/></button>}</section></div></>;
}
