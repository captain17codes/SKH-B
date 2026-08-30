import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import DiagnosticChecks from '../components/DiagnosticChecks';
import { auditAPI } from '../api/client';
import { titleCase } from '../components/categoryIcon';

function fmtTime(ts) {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleString('en-IN', { hour12: false });
  } catch {
    return String(ts);
  }
}

function entryHash(e) {
  return (e.entry_hash || '').toString();
}

function entryTime(e) {
  return e.ts || null;
}

function entryDetail(e) {
  return e.payload ?? null;
}

export default function CompliancePage() {
  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState(null);
  const [verify, setVerify] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [actionFilter, setActionFilter] = useState('All Event Types');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [recentRes, statsRes, verifyRes] = await Promise.all([
        auditAPI.recent({ limit: 100 }),
        auditAPI.stats().catch(() => null),
        auditAPI.verify().catch(() => null),
      ]);
      const list = recentRes?.entries || [];
      setEntries(list);
      setStats(statsRes);
      setVerify(verifyRes);
      setSelected(list[0] || null);
    } catch (err) {
      setError(err.message || 'Failed to load audit log');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const distinctActions = stats?.actions_recorded?.length
    ? stats.actions_recorded
    : [...new Set(entries.map(e => e.action).filter(Boolean))].sort();

  const filteredEntries = entries.filter(e => {
    if (actionFilter !== 'All Event Types' && e.action !== actionFilter) return false;
    if (search) {
      const hay = `${e.action || ''} ${e.entity_id || ''} ${e.entity_type || ''} ${e.actor || ''} ${entryHash(e)}`.toLowerCase();
      if (!hay.includes(search.toLowerCase())) return false;
    }
    return true;
  });

  const exportReport = () => {
    if (!entries.length) return;
    const header = ['seq', 'ts', 'actor', 'action', 'entity_type', 'entity_id', 'entry_hash'].join(',');
    const rows = entries.map(e => [e.seq ?? '', entryTime(e) ?? '', e.actor ?? 'system', e.action ?? '', e.entity_type ?? '', e.entity_id ?? '', entryHash(e)].join(','));
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rts-audit-export-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      {/* SideNavBar */}
      <nav className="bg-surface-container-low text-primary font-label-sm text-label-sm h-screen w-64 fixed left-0 top-0 border-r border-outline-variant/10 flex flex-col py-unit px-4 gap-2 z-40 hidden md:flex">
        <div className="flex items-center gap-3 px-2 py-4 mb-4">
          <div className="w-10 h-10 rounded-lg overflow-hidden bg-primary-container flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-on-primary-container">location_city</span>
          </div>
          <div>
            <h1 className="text-headline-md font-headline-md text-primary truncate">Kopargaon Civic</h1>
            <p className="text-on-surface-variant font-label-sm text-label-sm opacity-80">Administrative Suite</p>
          </div>
        </div>
        <button className="w-full bg-error text-on-error py-2 px-4 rounded-lg font-bold mb-6 hover:bg-error/90 transition-colors flex items-center justify-center gap-2 group">
          <span className="material-symbols-outlined text-on-error group-hover:scale-110 transition-transform">emergency</span>
          Report Emergency
        </button>
        <div className="flex-1 overflow-y-auto space-y-1">
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/admin">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">dashboard</span>
            <span>Dashboard</span>
          </Link>
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/ticket-pool">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">confirmation_number</span>
            <span>Ticket Pool</span>
          </Link>
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/staff-allocation">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">group_add</span>
            <span>Staff Allocation</span>
          </Link>
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/citizen-insights">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">analytics</span>
            <span>Citizen Insights</span>
          </Link>
          <Link className="flex items-center gap-3 px-3 py-2 bg-primary-container text-on-primary-container rounded-lg font-bold transition-all duration-300 group" to="/compliance">
            <span className="material-symbols-outlined icon-filled">terminal</span>
            <span>System Logs</span>
          </Link>
        </div>
        <div className="mt-auto pt-4 border-t border-outline-variant/20 space-y-1">
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/explanations">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">help</span>
            <span>Support</span>
          </Link>
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">logout</span>
            <span>Logout</span>
          </Link>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="md:ml-64 flex-1 flex flex-col min-h-screen bg-surface-bright relative">
        <header className="bg-surface/80 backdrop-blur-xl border-b border-outline-variant/10 px-4 md:px-margin-desktop py-4 md:h-20 flex flex-col md:flex-row gap-3 md:items-center md:justify-between shrink-0 sticky top-0 z-30">
          <div>
            <h2 className="font-headline-lg text-headline-lg text-primary">RTS Compliance &amp; Audit Trail</h2>
            <p className="font-body-md text-body-md text-on-surface-variant mt-1">
              Real-time system actions, algorithmic decisions, and SLA compliance logs.
              {verify && (verify.ok
                ? <span className="ml-2 text-tertiary font-semibold">· chain verified ({verify.entries ?? entries.length} entries)</span>
                : <span className="ml-2 text-error font-semibold">· chain integrity FAILED at seq {verify.first_broken_seq} ({verify.break_type})</span>)}
            </p>
            {verify?.truncation_caveat && (
              <p className="text-xs text-on-surface-variant mt-2 max-w-2xl italic">{verify.truncation_caveat}</p>
            )}
          </div>
          <button onClick={exportReport} disabled={!entries.length} className="bg-primary text-on-primary font-body-md text-body-md font-bold py-2 px-6 rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50">
            <span className="material-symbols-outlined">picture_as_pdf</span>
            Export RTS Defense Report (CSV)
          </button>
        </header>

        <div className="flex-1 flex flex-col xl:flex-row overflow-hidden">
          {/* Left Side: Filters and Log Feed */}
          <div className="flex-1 flex flex-col p-4 md:p-8 overflow-hidden">
            <DiagnosticChecks />

            {stats && (
              <div className="flex flex-wrap gap-2 mb-4">
                {(stats.by_action || []).slice(0, 6).map(({ action, count }) => (
                  <span key={action} className="px-3 py-1 bg-surface-container-high rounded-full text-xs font-label-sm text-on-surface">
                    {titleCase(action)}: <span className="font-bold">{count}</span>
                  </span>
                ))}
              </div>
            )}

            {/* Filters Bar */}
            <div className="flex flex-col md:flex-row items-stretch md:items-center gap-4 mb-6 shrink-0 bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/20 shadow-sm">
              <div className="relative flex-1 max-w-xs">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">filter_list</span>
                <select
                  value={actionFilter}
                  onChange={e => setActionFilter(e.target.value)}
                  className="w-full pl-10 pr-8 py-2 bg-surface-bright border border-secondary-container rounded-lg focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-fixed/50 font-body-md text-body-md text-on-surface appearance-none transition-all"
                >
                  <option>All Event Types</option>
                  {distinctActions.map(a => <option key={a} value={a}>{titleCase(a)}</option>)}
                </select>
                <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-outline pointer-events-none">expand_more</span>
              </div>
              <div className="relative flex-1">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">search</span>
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-surface-bright border border-secondary-container rounded-lg focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-fixed/50 font-body-md text-body-md text-on-surface transition-all"
                  placeholder="Search hash, ticket ID or action..."
                  type="text"
                />
              </div>
              <button onClick={load} className="p-2 bg-surface-container hover:bg-surface-variant text-on-surface rounded-lg transition-colors border border-outline-variant/20 shrink-0">
                <span className="material-symbols-outlined">refresh</span>
              </button>
            </div>

            {/* Log Table Container */}
            <div className="flex-1 bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm overflow-hidden flex flex-col">
              <div className="grid grid-cols-[140px_100px_160px_minmax(200px,1fr)_110px] gap-4 p-4 border-b border-outline-variant/20 bg-surface-container-low font-label-sm text-label-sm text-on-surface-variant sticky top-0 uppercase tracking-wider">
                <div>Timestamp</div>
                <div>Seq</div>
                <div>Action</div>
                <div>Entity</div>
                <div>Hash</div>
              </div>
              <div className="overflow-y-auto flex-1 font-mono text-xs text-on-surface">
                {error ? (
                  <div className="p-6 text-error">{error}</div>
                ) : loading ? (
                  <div className="p-6 space-y-3 animate-pulse">
                    {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-8 bg-surface-container rounded" />)}
                  </div>
                ) : filteredEntries.length === 0 ? (
                  <div className="p-6 text-on-surface-variant font-body-md">No audit entries match the current filters.</div>
                ) : filteredEntries.map((e, idx) => (
                  <div
                    key={e.seq ?? e.id ?? idx}
                    onClick={() => setSelected(e)}
                    className={`grid grid-cols-[140px_100px_160px_minmax(200px,1fr)_110px] gap-4 p-4 border-b border-outline-variant/10 hover:bg-surface-variant/30 cursor-pointer transition-colors ${selected === e ? 'bg-primary-fixed/10' : ''}`}
                  >
                    <div className="text-outline">{fmtTime(entryTime(e))}</div>
                    <div className="text-tertiary">#{e.seq ?? e.id ?? '—'}</div>
                    <div className="font-sans font-medium">{titleCase(e.action || 'event')}</div>
                    <div className="truncate text-on-surface-variant font-sans">
                      {e.entity_type ? `${titleCase(e.entity_type)} ${e.entity_id ?? ''}` : (e.entity_id || '—')}
                    </div>
                    <div className="truncate">{entryHash(e).slice(0, 10) || '—'}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Side: Detail Drawer */}
          <div className="w-full xl:w-[400px] border-t xl:border-t-0 xl:border-l border-outline-variant/20 bg-surface-container-lowest flex flex-col shadow-[-10px_0_20px_rgba(22,52,34,0.02)]">
            <div className="p-6 border-b border-outline-variant/20 flex justify-between items-center bg-surface-bright">
              <div>
                <h3 className="font-headline-md text-headline-md text-primary">Log Details</h3>
                <p className="font-mono text-xs text-outline mt-1">Hash: {selected ? (entryHash(selected).slice(0, 16) || '—') : '—'}</p>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {!selected ? (
                <p className="text-on-surface-variant font-body-md text-body-md">Select an entry from the log to see its full context.</p>
              ) : (
                <>
                  <div className="bg-surface-container p-4 rounded-lg border border-outline-variant/10">
                    <div className="font-label-sm text-label-sm text-on-surface-variant mb-2">Event Context</div>
                    <div className="grid grid-cols-2 gap-4 font-mono text-xs">
                      <div>
                        <div className="text-outline">Entity</div>
                        <div className="text-on-surface font-medium">{selected.entity_type ? `${selected.entity_type}:` : ''}{selected.entity_id ?? '—'}</div>
                      </div>
                      <div>
                        <div className="text-outline">Action</div>
                        <div className="text-on-surface font-medium">{titleCase(selected.action || '')}</div>
                      </div>
                      <div>
                        <div className="text-outline">Sequence</div>
                        <div className="text-on-surface font-medium">{selected.seq ?? '—'}</div>
                      </div>
                      <div>
                        <div className="text-outline">Actor</div>
                        <div className="text-on-surface font-medium">{selected.actor ?? 'system'}</div>
                      </div>
                      <div className="col-span-2">
                        <div className="text-outline">Timestamp</div>
                        <div className="text-on-surface font-medium">{fmtTime(entryTime(selected))}</div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <div className="font-label-sm text-label-sm text-on-surface-variant mb-2 flex items-center justify-between">
                      <span>Raw Audit Payload</span>
                    </div>
                    <div className="bg-inverse-surface text-inverse-on-surface p-4 rounded-lg font-mono text-[11px] overflow-x-auto border border-outline-variant/20 shadow-inner">
                      <pre className="whitespace-pre-wrap leading-tight">{JSON.stringify(entryDetail(selected) ?? {}, null, 2)}</pre>
                    </div>
                  </div>
                  {(entryDetail(selected)?.reason_text || entryDetail(selected)?.reason) && (
                    <div className="bg-primary-container/10 p-4 rounded-lg border border-primary-container/20">
                      <div className="flex items-start gap-3">
                        <span className="material-symbols-outlined text-primary mt-0.5">info</span>
                        <p className="font-body-md text-[14px] text-on-surface-variant leading-relaxed">
                          {entryDetail(selected)?.reason_text || entryDetail(selected)?.reason}
                        </p>
                      </div>
                    </div>
                  )}
                  <div className="pt-2 border-t border-outline-variant/10">
                    <p className="text-[11px] text-outline font-mono break-all">prev_hash: {selected.prev_hash?.slice(0, 24)}…</p>
                    <p className="text-[11px] text-outline font-mono break-all">entry_hash: {selected.entry_hash?.slice(0, 24)}…</p>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
