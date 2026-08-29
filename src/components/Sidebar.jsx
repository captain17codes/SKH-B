import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Sidebar() {
  const location = useLocation();
  const navItems = [
    { name: 'Admin Dashboard', path: '/admin', icon: 'dashboard' },
    { name: 'Citizen Portal', path: '/submit', icon: 'support_agent' },
    { name: 'Resource Allocation', path: '/allocation', icon: 'engineering' },
    { name: 'System Explanations', path: '/explanations', icon: 'data_info_alert' },
  ];

  return (
    <aside className="w-64 bg-surface border-r border-surface-variant min-h-[calc(100vh-80px)] flex flex-col p-4 hidden md:flex shrink-0">
      <div className="flex flex-col gap-2 mt-4">
        <div className="text-xs font-bold text-outline tracking-wider mb-2 px-4 uppercase font-label">Navigation</div>
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                isActive 
                  ? 'bg-primary-container text-on-primary-container font-bold shadow-sm' 
                  : 'text-on-surface-variant hover:bg-surface-variant hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
              <span>{item.name}</span>
            </Link>
          );
        })}
      </div>
    </aside>
  );
}
