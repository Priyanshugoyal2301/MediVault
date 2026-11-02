import React, {useEffect, useId, useRef} from 'react';
import {ArrowRight, ShieldCheck, X} from 'lucide-react';

export function Brand() { return <span className="brand"><span className="brand-mark"><ShieldCheck size={23}/></span>MediVault<span className="brand-dot">.</span></span>; }
export function Badge({children, tone = 'neutral'}) { return <span className={`badge ${tone}`}>{children}</span>; }
export function Empty({icon: Icon = ShieldCheck, title, children, action}) { return <div className="empty"><span className="empty-icon"><Icon size={26}/></span><h3>{title}</h3><p>{children}</p>{action}</div>; }
export function ErrorNotice({error}) { return error ? <div className="notice error" role="alert">{error.message || error}</div> : null; }
export function SectionTitle({eyebrow, title, children, action}) { return <div className="section-title"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2>{children && <p>{children}</p>}</div>{action}</div>; }
export function Field({label, help, children, ...props}) {
  const id = useId();
  return <div className="field"><label htmlFor={id}>{label}</label>{children ? React.cloneElement(children, {id, 'aria-describedby':help ? `${id}-help` : undefined}) : <input id={id} {...props} aria-describedby={help ? `${id}-help` : undefined}/>}{help && <small id={`${id}-help`}>{help}</small>}</div>;
}
export function Modal({title, children, onClose, wide = false}) {
  const dialog = useRef(); const id = useId(); const priorFocus = useRef(document.activeElement);
  useEffect(() => { const el = dialog.current; el.showModal(); return () => { el.close(); priorFocus.current?.focus(); }; }, []);
  return <dialog ref={dialog} className={`modal${wide ? ' modal-wide' : ''}`} aria-labelledby={id} onCancel={e => {e.preventDefault(); onClose();}}>
    <div className="modal-heading"><h2 id={id}>{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={22}/></button></div>{children}</dialog>;
}
export function TextAction({children, onClick}) {return <button className="text-action" onClick={onClick}>{children}<ArrowRight size={16}/></button>;}
export const dateText = value => value ? new Intl.DateTimeFormat('en-IN', {day:'numeric', month:'short', year:'numeric'}).format(new Date(value.length === 10 ? `${value}T12:00:00` : value)) : 'Date not recorded';
export const initials = name => name?.split(' ').filter(Boolean).slice(0,2).map(x => x[0]).join('').toUpperCase() || 'MV';

export class ErrorBoundary extends React.Component {
  state = {failed: false};
  static getDerivedStateFromError() { return {failed:true}; }
  render() { return this.state.failed ? <main className="startup"><Brand/><h1>Something interrupted this screen.</h1><p>Your saved records are still in your vault.</p><button className="button" onClick={() => location.reload()}>Reload application</button></main> : this.props.children; }
}
