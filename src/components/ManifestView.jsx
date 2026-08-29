/**
 * Dispatch Manifest View - Block 2 (Assistant 1)
 */
import React, { useState } from 'react';

export default function ManifestView({ manifest, onRefresh }) {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);

  if (!manifest) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <p className="text-gray-500 mb-4">No dispatch manifest for today.</p>
        <button
          onClick={onRefresh}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Check for Updates
        </button>
      </div>
    );
  }

  const { summary, scheduled, deferred, solver_status, budget_cap, workforce_cap_hours } = manifest;

  return (
    <div className="space-y-6">
      {/* Manifest Summary */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold">Dispatch Manifest</h3>
            <p className="text-sm text-gray-600">{date}</p>
          </div>
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded text-sm">
            {solver_status}
          </span>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="bg-blue-50 p-3 rounded">
            <p className="text-sm text-gray-600">Total Tickets</p>
            <p className="text-xl font-bold">{summary.total_tickets}</p>
          </div>
          <div className="bg-green-50 p-3 rounded">
            <p className="text-sm text-gray-600">Scheduled</p>
            <p className="text-xl font-bold">{summary.scheduled}</p>
          </div>
          <div className="bg-orange-50 p-3 rounded">
            <p className="text-sm text-gray-600">Deferred</p>
            <p className="text-xl font-bold">{summary.deferred}</p>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <p className="text-sm text-gray-600">Budget Used</p>
            <p className="text-xl font-bold">
              ₹{((budget_cap * (summary.scheduled / summary.total_tickets)) || 0).toFixed(0)}
            </p>
          </div>
        </div>

        <p className="text-sm text-gray-600">
          Daily Budget: ₹{budget_cap} | Workforce Hours: {workforce_cap_hours}h
        </p>
      </div>

      {/* Scheduled Tickets */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 text-green-700">Scheduled for Today</h3>
        {scheduled?.length > 0 ? (
          <ul className="space-y-2">
            {scheduled.map(item => (
              <li key={item.ticket_id} className="flex items-center justify-between p-3 bg-green-50 rounded border-l-4 border-green-500">
                <div>
                  <p className="font-medium capitalize">{item.category}</p>
                  <p className="text-sm text-gray-600">{item.ward_id || 'Unknown Ward'}</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-blue-600">CCi: {(item.cci_score * 100).toFixed(1)}%</p>
                  <p className="text-sm text-gray-500">₹{item.cost_estimate} | {item.hours_estimate}h</p>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-500 text-center py-4">No tickets scheduled.</p>
        )}
      </div>

      {/* Deferred Tickets */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 text-orange-700">Deferred</h3>
        {deferred?.length > 0 ? (
          <ul className="space-y-2">
            {deferred.map(item => (
              <li key={item.ticket_id} className="flex items-center justify-between p-3 bg-orange-50 rounded border-l-4 border-orange-500">
                <div>
                  <p className="font-medium capitalize">{item.category}</p>
                  <p className="text-sm text-gray-600">{item.ward_id || 'Unknown Ward'}</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-blue-600">CCi: {(item.cci_score * 100).toFixed(1)}%</p>
                  <p className="text-sm text-gray-500">₹{item.cost_estimate} | {item.hours_estimate}h</p>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-500 text-center py-4">No tickets deferred.</p>
        )}
      </div>
    </div>
  );
}
