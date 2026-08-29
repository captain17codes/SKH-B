/**
 * Ticket List Component - Block 2 (Assistant 1)
 */
import React, { useState } from 'react';

export default function TicketList({ tickets, onRefresh }) {
  const [filter, setFilter] = useState('all');

  const filteredTickets = filter === 'all'
    ? tickets
    : tickets.filter(t => t.status === filter);

  const statusColors = {
    open: 'bg-yellow-100 text-yellow-800',
    scored: 'bg-blue-100 text-blue-800',
    scheduled: 'bg-green-100 text-green-800',
    deferred: 'bg-orange-100 text-orange-800',
    dispatched: 'bg-purple-100 text-purple-800',
    resolved: 'bg-gray-100 text-gray-800',
    deduped: 'bg-indigo-100 text-indigo-800',
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">All Tickets</h3>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="border rounded-lg px-3 py-1"
        >
          <option value="all">All Status</option>
          <option value="open">Open</option>
          <option value="scored">Scored</option>
          <option value="scheduled">Scheduled</option>
          <option value="deferred">Deferred</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Ward</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">CCi Score</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Phone</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredTickets.map(ticket => (
              <tr key={ticket.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-sm">{ticket.id?.substring(0, 8)}...</td>
                <td className="px-4 py-2 capitalize">{ticket.category}</td>
                <td className="px-4 py-2">{ticket.ward_id || '-'}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-1 rounded text-xs ${statusColors[ticket.status] || 'bg-gray-100'}`}>
                    {ticket.status}
                  </span>
                </td>
                <td className="px-4 py-2">
                  {ticket.cci_score ? ticket.cci_score.toFixed(3) : '-'}
                </td>
                <td className="px-4 py-2 text-sm">{ticket.citizen_phone}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredTickets.length === 0 && (
        <p className="text-center text-gray-500 py-8">No tickets found.</p>
      )}
    </div>
  );
}
