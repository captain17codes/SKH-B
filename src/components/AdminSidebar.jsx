import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function AdminSidebar() {
  const location = useLocation();
  const path = location.pathname;

  const links = [
    { to: '/admin', icon: 'dashboard', label: 'Dashboard' },
    { to: '/ticket-pool', icon: 'confirmation_number', label: 'Ticket Pool' },
    { to: '/allocation', icon: 'event_note', label: 'Daily Allocation' },
    { to: '/staff-allocation', icon: 'group_add', label: 'Staff Allocation' },
    { to: '/citizen-insights', icon: 'analytics', label: 'Citizen Insights' },
    { to: '/compliance', icon: 'terminal', label: 'System Logs' },
    { to: '/explanations', icon: 'psychology', label: 'System Explanations' },
  ];

  return (
    <aside className="bg-surface-container-low dark:bg-surface-container-lowest h-screen w-64 fixed left-0 top-0 border-r border-outline-variant/10 flex flex-col py-8 px-4 gap-2 z-40 hidden md:flex">
      <div className="flex items-center gap-3 mb-8 px-2">
        <span className="material-symbols-outlined text-primary text-3xl icon-filled">account_balance</span>
        <div>
          <h2 className="text-headline-md font-headline-md font-bold text-primary">Admin Panel</h2>
          <p className="text-label-sm font-label-sm text-on-surface-variant">Kopargaon Civic</p>
        </div>
      </div>
      
      <Link to="/submit" className="bg-primary text-on-primary font-label-sm text-label-sm rounded-lg py-3 px-4 mb-6 hover:opacity-90 transition-opacity shadow-sm w-full text-center flex items-center justify-center gap-2 font-bold">
        <span className="material-symbols-outlined text-[20px]">add</span> Report Emergency
      </Link>
      
      <nav className="flex-1 space-y-1 overflow-y-auto pr-2 pb-4">
        {links.map(link => {
          const isActive = path === link.to;
          return (
            <Link 
              key={link.to} 
              to={link.to} 
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300 group cursor-pointer ${
                isActive 
                  ? 'bg-primary-container text-on-primary-container font-bold shadow-sm' 
                  : 'text-on-surface-variant hover:text-primary hover:bg-surface-container-high'
              }`}
            >
              <span className={`material-symbols-outlined group-hover:translate-x-1 transition-transform ${isActive ? 'icon-filled' : ''}`} style={isActive ? {fontVariationSettings: "'FILL' 1"} : {}}>
                {link.icon}
              </span>
              <span className="font-label-sm text-label-sm">{link.label}</span>
            </Link>
          );
        })}
      </nav>
      
      <div className="mt-auto border-t border-outline-variant/20 pt-4 space-y-1">
        <Link className="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary hover:bg-surface-container-high rounded-lg transition-all duration-300 group cursor-pointer" to="/explanations">
          <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">help</span>
          <span className="font-label-sm text-label-sm">Support</span>
        </Link>
        <Link className="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary hover:bg-surface-container-high rounded-lg transition-all duration-300 group cursor-pointer" to="/">
          <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">logout</span>
          <span className="font-label-sm text-label-sm">Logout</span>
        </Link>
      </div>
    </aside>
  );
}
