import React from 'react';
import StatusBadge from '../StatusBadge';

export default function RecentSubmissionsTable() {
  return (
    <div className="bg-surface rounded-xl border border-surface-variant p-6 shadow-sm">
      <h2 className="text-xl font-bold text-on-surface mb-6">Your Recent Submissions</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-surface-variant">
              <th className="py-4 font-bold font-label text-on-surface-variant text-sm uppercase tracking-wider pr-4">Ticket ID</th>
              <th className="py-4 font-bold font-label text-on-surface-variant text-sm uppercase tracking-wider pr-4">Category</th>
              <th className="py-4 font-bold font-label text-on-surface-variant text-sm uppercase tracking-wider pr-4">Date</th>
              <th className="py-4 font-bold font-label text-on-surface-variant text-sm uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-surface-variant/50 last:border-0">
              <td className="py-4 font-bold text-on-surface pr-4">#KPG-2048</td>
              <td className="py-4 text-on-surface-variant pr-4">Road Maintenance</td>
              <td className="py-4 text-on-surface-variant pr-4">Oct 24, 2026</td>
              <td className="py-4"><StatusBadge status="In Progress" /></td>
            </tr>
            <tr>
              <td className="py-4 font-bold text-on-surface pr-4">#KPG-1933</td>
              <td className="py-4 text-on-surface-variant pr-4">Water Supply</td>
              <td className="py-4 text-on-surface-variant pr-4">Sep 12, 2026</td>
              <td className="py-4"><StatusBadge status="Completed" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
