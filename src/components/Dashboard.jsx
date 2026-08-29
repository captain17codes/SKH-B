/**
 * Municipal Dashboard Component - Block 2 (Assistant 1)
 * Live view for municipal staff: tickets, priorities, dispatch manifest
 */
import React, { useState, useEffect } from 'react';
import { ticketsAPI, triageAPI } from '../api/client';
import TicketList from './TicketList';
import ManifestView from './ManifestView';
import TriagePanel from './TriagePanel';

export default function Dashboard() {
  const [tickets, setTickets] = useState([]);
  const [manifest, setManifest] = useState(null);
  const [priorities, setPriorities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState({
    total: 0,
    open: 0,
    scheduled: 0,
    deferred: 0,
    resolved: 0
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch tickets
      const ticketsRes = await ticketsAPI.list({ limit: 100 });
      setTickets(ticketsRes.tickets || []);

      // Calculate stats
      const ticketList = ticketsRes.tickets || [];
      setStats({
        total: ticketList.length,
        open: ticketList.filter(t => t.status === 'open').length,
        scheduled: ticketList.filter(t => t.status === 'scheduled').length,
        deferred: ticketList.filter(t => t.status === 'deferred').length,
        resolved: ticketList.filter(t => t.status === 'resolved').length
      });

      // Fetch priorities
      const prioritiesRes = await triageAPI.getPriorities({ limit: 20 });
      setPriorities(prioritiesRes.tickets || []);

      // Fetch today's manifest
      try {
        const manifestRes = await triageAPI.getToday();
        setManifest(manifestRes);
      } catch {
        // No manifest for today yet
        setManifest(null);
      }

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTriageComplete = () => {
    loadData(); // Refresh all data after triage run
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Municipal Dashboard</h1>
          <p className="text-gray-600 mt-1">Kopargaon Civic Resource Prioritization Platform</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={loadData}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center"
          >
            <svg className="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4">
          <p className="text-red-700">{error}</p>
          <button onClick={loadData} className="text-red-600 text-sm underline mt-1">
            Retry
          </button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard title="Total Tickets" value={stats.total} icon="📊" color="blue" />
        <StatCard title="Open" value={stats.open} icon="📥" color="yellow" />
        <StatCard title="Scheduled" value={stats.scheduled} icon="📅" color="green" />
        <StatCard title="Deferred" value={stats.deferred} icon="⏸️" color="orange" />
        <StatCard title="Resolved" value={stats.resolved} icon="✅" color="gray" />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {[
            { id: 'overview', label: 'Overview', icon: '📋' },
            { id: 'triage', label: 'Run Triage', icon: '⚡' },
            { id: 'manifest', label: 'Dispatch Manifest', icon: '📋' },
            { id: 'tickets', label: 'All Tickets', icon: '🎫' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-4 px-1 inline-flex items-center border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="py-4">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Priority Board */}
            <div className="grid grid-cols-2 gap-6">
              {/* High Priority Tickets */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  🔥 High Priority (Top 10)
                </h3>
                <PriorityList priorities={priorities.slice(0, 10)} />
              </div>

              {/* Scheduled for Today */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  📅 Today's Schedule
                </h3>
                {manifest?.scheduled?.length > 0 ? (
                  <ul className="space-y-2">
                    {manifest.scheduled.slice(0, 5).map(item => (
                      <li key={item.ticket_id} className="flex items-center justify-between p-2 bg-green-50 rounded">
                        <span className="text-sm font-medium">{item.category}</span>
                        <span className="text-xs text-green-700">CCI: {item.cci_score?.toFixed(3)}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 text-center py-8">No dispatch manifest for today.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'triage' && (
          <TriagePanel onTriageComplete={handleTriageComplete} />
        )}

        {activeTab === 'manifest' && (
          <ManifestView manifest={manifest} onRefresh={loadData} />
        )}

        {activeTab === 'tickets' && (
          <TicketList tickets={tickets} onRefresh={loadData} />
        )}
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color }) {
  const colors = {
    blue: 'bg-blue-50 border-blue-200',
    yellow: 'bg-yellow-50 border-yellow-200',
    green: 'bg-green-50 border-green-200',
    orange: 'bg-orange-50 border-orange-200',
    gray: 'bg-gray-50 border-gray-200',
  };

  return (
    <div className={`rounded-lg border p-4 ${colors[color]}`}>
      <div className="flex items-center">
        <span className="text-2xl mr-3">{icon}</span>
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </div>
    </div>
  );
}

function PriorityList({ priorities }) {
  if (!priorities?.length) {
    return <p className="text-gray-500 text-center py-8">No tickets scored yet. Run triage first.</p>;
  }

  return (
    <ul className="space-y-2">
      {priorities.map((ticket, index) => (
        <li key={ticket.id} className="flex items-center p-2 border-b last:border-b-0">
          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold mr-3 ${
            index === 0 ? 'bg-red-500 text-white' :
            index < 3 ? 'bg-orange-500 text-white' :
            'bg-gray-200 text-gray-700'
          }`}>
            {index + 1}
          </span>
          <div className="flex-1">
            <p className="text-sm font-medium capitalize">{ticket.category}</p>
            <p className="text-xs text-gray-500">{ticket.ward_id || 'Unknown ward'}</p>
          </div>
          <div className="text-right">
            <p className="text-sm font-semibold text-blue-600">
              {(ticket.cci_score * 100).toFixed(1)}%
            </p>
            <p className="text-xs text-gray-500">
              ×{ticket.community_multiplier?.toFixed(1)}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
