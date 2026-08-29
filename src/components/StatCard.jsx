import React from 'react';

export default function StatCard({ title, value, icon, trend, trendUp = true }) {
  return (
    <div className="bg-surface rounded-xl p-6 shadow-sm border border-surface-variant flex flex-col gap-4 relative overflow-hidden group hover:shadow-md transition-all">
      <div className="w-12 h-12 rounded-lg bg-surface-container-high flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
        <span className="material-symbols-outlined">{icon}</span>
      </div>
      <div>
        <h3 className="text-on-surface-variant text-sm font-semibold">{title}</h3>
        <div className="flex items-end gap-3 mt-1">
          <span className="text-3xl font-bold text-on-surface">{value}</span>
          {trend && (
            <span className={`text-sm font-bold flex items-center ${trendUp ? 'text-primary' : 'text-error'}`}>
              <span className="material-symbols-outlined text-[16px]">{trendUp ? 'trending_up' : 'trending_down'}</span>
              {trend}
            </span>
          )}
        </div>
      </div>
      <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full -mr-12 -mt-12 group-hover:scale-150 transition-transform duration-500"></div>
    </div>
  );
}
