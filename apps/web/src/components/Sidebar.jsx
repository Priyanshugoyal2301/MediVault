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
          <ShieldAlert size={22} color="#fff" />
        </div>
        <span>MediVault<span style={{ color: 'var(--primary)' }}>.ai</span></span>
        <span className="brand-badge">MVP</span>
      </div>

      <nav className="nav-menu">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="user-profile">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ width: 34, height: 34, borderRadius: '50%', background: 'rgba(6, 182, 212, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}>
            <UserCheck size={18} />
          </div>
          <div className="user-info">
            <span className="user-name">{user ? user.email : 'Priyanshu Goyal'}</span>
            <span className="user-role">ID: {user ? user.id.slice(0, 8) : 'demo-user'}</span>
          </div>
        </div>
        <button onClick={onLogout} style={{ background: 'transparent', border: 'none', color: 'var(--text-subtle)', cursor: 'pointer', padding: 4 }}>
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
