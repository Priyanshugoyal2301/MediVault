import React from 'react';
import { LayoutDashboard, UploadCloud, TrendingUp, MessageSquare, ShieldAlert, LogOut, UserCheck } from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, user, onLogout }) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'upload', label: 'Upload Report', icon: UploadCloud },
    { id: 'timeline', label: 'Health Timeline', icon: TrendingUp },
    { id: 'chat', label: 'Evidence Q&A', icon: MessageSquare },
  ];

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">
          <ShieldAlert size={22} color="#fff" aria-hidden="true" />
        </div>
        <span>MediVault<span style={{ color: 'var(--primary)' }}>.ai</span></span>
        <span className="brand-badge">Demo</span>
      </div>

      <nav className="nav-menu" aria-label="Main">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon size={18} aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="user-profile">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: 0 }}>
          <div style={{ width: 34, height: 34, borderRadius: '50%', background: 'rgba(6, 182, 212, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)', flexShrink: 0 }}>
            <UserCheck size={18} aria-hidden="true" />
          </div>
          <div className="user-info" style={{ minWidth: 0 }}>
            <span className="user-name" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block' }}>
              {user?.email || 'Signed in'}
            </span>
            <span className="user-role">
              {user?.id ? `ID ${user.id.slice(0, 8)}…` : ''}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onLogout}
          aria-label="Log out"
          title="Log out"
          style={{ background: 'transparent', border: 'none', color: 'var(--text-subtle)', cursor: 'pointer', padding: 4 }}
        >
          <LogOut size={16} aria-hidden="true" />
        </button>
      </div>
    </aside>
  );
}
