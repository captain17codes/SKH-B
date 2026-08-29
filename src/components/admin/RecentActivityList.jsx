import React from 'react';
import StatusBadge from '../StatusBadge';

export default function RecentActivityList() {
  const activities = [
    { title: 'Water Pipe Leak fixed', time: '2 hours ago', status: 'Completed' },
    { title: 'Road maintenance started', time: '5 hours ago', status: 'In Progress' },
    { title: 'Traffic signal failure', time: '1 day ago', status: 'Delayed' },
    { title: 'New park construction', time: '2 days ago', status: 'In Progress' }
  ];

  return (
    <div className="bg-surface rounded-xl border border-surface-variant p-6 shadow-sm">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold text-on-surface">Recent Activity</h2>
      </div>
      <div className="flex flex-col gap-4">
        {activities.map((item, idx) => (
          <div key={idx} className="flex flex-col gap-2 pb-4 border-b border-surface-variant last:border-0">
            <div className="flex justify-between items-start gap-4">
              <h4 className="font-bold text-on-surface text-sm">{item.title}</h4>
              <StatusBadge status={item.status} />
            </div>
            <span className="text-xs text-on-surface-variant">{item.time}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
