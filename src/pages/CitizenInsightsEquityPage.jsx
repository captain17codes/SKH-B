import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ticketsAPI, mediaAPI, auditAPI } from '../api/client';

function pct(n) {
  return `${Math.round(n * 100)}%`;
}

export default function CitizenInsightsEquityPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [wardStats, setWardStats] = useState([]);
  const [totals, setTotals] = useState({ total: 0, onTrack: 0, atRisk: 0, overdue: 0 });
  const [clusterCount, setClusterCount] = useState(0);
  const [duplicatesFolded, setDuplicatesFolded] = useState(0);
  const [chainOk, setChainOk] = useState(null);
  const [insight, setInsight] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const [listRes, clustersRes, verifyRes] = await Promise.all([
          ticketsAPI.list({ limit: 500 }),
          mediaAPI.clusters(50).catch(() => ({ clusters: [] })),
          auditAPI.verify().catch(() => null),
        ]);
        if (!mounted) return;

        const tickets = listRes.tickets || [];
        const byWard = {};
        let onTrack = 0, atRisk = 0, overdue = 0;

        tickets.forEach(t => {
          const w = t.ward_id || 'Unassigned';
          if (!byWard[w]) byWard[w] = { ward: w, complaints: 0, priorityWeight: 0, scoredCount: 0 };
          byWard[w].complaints += 1;
          if (t.cci_score != null) {
            byWard[w].priorityWeight += t.cci_score;
            byWard[w].scoredCount += 1;
          }
          const st = t.sla?.operational_status;
          if (st === 'ON_TRACK') onTrack += 1;
          else if (st === 'AT_RISK') atRisk += 1;
          else if (st === 'OVERDUE' || st === 'IMMEDIATE_HANDOFF') overdue += 1;
        });

        const wards = Object.values(byWard).sort((a, b) => b.complaints - a.complaints);
        const maxComplaints = Math.max(1, ...wards.map(w => w.complaints));
        const maxWeight = Math.max(1, ...wards.map(w => w.priorityWeight));
        const totalComplaints = tickets.length || 1;
        const totalWeight = wards.reduce((s, w) => s + w.priorityWeight, 0) || 1;

        const enriched = wards.map(w => ({
          ...w,
          complaintPct: w.complaints / maxComplaints,
          weightPct: w.priorityWeight / maxWeight,
          complaintShare: w.complaints / totalComplaints,
          weightShare: w.priorityWeight / totalWeight,
          slaOnTrack: (() => {
            const wardTickets = tickets.filter(t => (t.ward_id || 'Unassigned') === w.ward);
            const known = wardTickets.filter(t => t.sla?.operational_status && t.sla.operational_status !== 'TARGET_UNDEFINED');
            if (known.length === 0) return null;
            return known.filter(t => t.sla.operational_status === 'ON_TRACK').length / known.length;
          })(),
        }));

        // Find the ward whose priority share most exceeds its complaint volume share —
        // i.e. the algorithm is weighting it more heavily than raw complaint count alone would.
        let best = null;
        enriched.forEach(w => {
          if (w.complaintShare <= 0) return;
          const lift = w.weightShare - w.complaintShare;
          if (!best || lift > best.lift) best = { ward: w.ward, lift, weightShare: w.weightShare, complaintShare: w.complaintShare };
        });

        setWardStats(enriched.slice(0, 8));
        setTotals({ total: tickets.length, onTrack, atRisk, overdue });
        setClusterCount((clustersRes.clusters || []).length);
        setDuplicatesFolded((clustersRes.clusters || []).reduce((s, c) => s + (c.duplicate_count || 0), 0));
        setChainOk(verifyRes?.ok ?? null);
        setInsight(best);
      } catch (err) {
        if (mounted) setError(err.message || 'Failed to load citizen insights');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, []);

  const slaKnown = totals.onTrack + totals.atRisk + totals.overdue;
  const onTrackRate = slaKnown > 0 ? totals.onTrack / slaKnown : null;

  return (
    <div className="bg-background text-on-surface font-body-md flex min-h-screen">
      {/* SideNavBar */}
      <nav className="hidden md:flex bg-surface-container-low border-r border-outline-variant/10 h-screen w-64 fixed left-0 top-0 flex-col py-unit px-4 gap-2 z-40">
        <div className="flex items-center gap-3 px-2 py-4 mb-4">
          <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center shrink-0 text-on-primary">
            <span className="material-symbols-outlined">account_balance</span>
          </div>
          <div className="flex flex-col">
            <span className="text-headline-md font-headline-md text-primary">Kopargaon Civic</span>
            <span className="text-label-sm font-label-sm text-on-surface-variant">Administrative Suite</span>
          </div>
        </div>
        <div className="flex flex-col gap-1 flex-1">
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 rounded-lg transition-all duration-300 group" to="/admin">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">dashboard</span>
            <span className="font-label-sm text-label-sm">Dashboard</span>
          </Link>
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 rounded-lg transition-all duration-300 group" to="/ticket-pool">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">confirmation_number</span>
            <span className="font-label-sm text-label-sm">Ticket Pool</span>
          </Link>
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 rounded-lg transition-all duration-300 group" to="/staff-allocation">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">group_add</span>
            <span className="font-label-sm text-label-sm">Staff Allocation</span>
          </Link>
          <Link className="flex items-center gap-3 px-3 py-2 bg-primary-container text-on-primary-container rounded-lg font-bold transition-all duration-300 group" to="/citizen-insights">
            <span className="material-symbols-outlined">analytics</span>
            <span className="font-label-sm text-label-sm">Citizen Insights</span>
          </Link>
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 rounded-lg transition-all duration-300 group" to="/compliance">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">terminal</span>
            <span className="font-label-sm text-label-sm">System Logs</span>
          </Link>
        </div>
        <div className="mt-auto mb-4">
          <Link to="/submit" className="w-full bg-primary text-on-primary py-2 rounded-lg font-label-sm text-label-sm shadow-sm hover:bg-primary-container hover:text-on-primary-container transition-colors flex items-center justify-center gap-2">
            <span className="material-symbols-outlined">add_alert</span>
            Report Emergency
          </Link>
        </div>
        <div className="flex flex-col gap-1 border-t border-outline-variant/10 pt-2">
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 rounded-lg transition-all duration-300 group" to="/explanations">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">help</span>
            <span className="font-label-sm text-label-sm">Support</span>
          </Link>
          <Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 rounded-lg transition-all duration-300 group" to="/">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">logout</span>
            <span className="font-label-sm text-label-sm">Logout</span>
          </Link>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 ml-0 md:ml-64 min-h-screen bg-surface relative">
        <div className="relative z-10 max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-12 md:py-16">
          <header className="mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-surface-container-high rounded-full border border-outline-variant/20 mb-4">
              <span className="material-symbols-outlined text-primary text-sm">insights</span>
              <span className="font-label-sm text-label-sm text-on-surface-variant">Analytical Overview</span>
            </div>
            <h1 className="font-headline-display text-headline-display text-on-surface mb-2">Socio-Spatial Equity &amp; SLA Compliance</h1>
            <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl">Real-time telemetry on resource distribution and service-level compliance across municipal wards, computed directly from the live ticket pool.</p>
          </header>

          {error && <div className="bg-error-container text-on-error-container p-6 rounded-xl font-semibold mb-8">{error}</div>}

          {/* KPI Cards Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter mb-12">
            <div className="glass-panel rounded-xl p-6 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10"><span className="material-symbols-outlined text-6xl">description</span></div>
              <h3 className="font-label-sm text-label-sm text-on-surface-variant mb-1">Reports on File</h3>
              <div className="font-headline-lg text-headline-lg text-primary flex items-baseline gap-2">
                {loading ? '—' : totals.total}
                <span className="text-sm font-medium text-on-surface-variant">across {wardStats.length} ward(s)</span>
              </div>
            </div>
            <div className="glass-panel rounded-xl p-6 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10"><span className="material-symbols-outlined text-6xl">speed</span></div>
              <h3 className="font-label-sm text-label-sm text-on-surface-variant mb-1">Operational SLA On-Track</h3>
              <div className="font-headline-lg text-headline-lg text-primary flex items-baseline gap-2">
                {loading || onTrackRate == null ? '—' : pct(onTrackRate)}
                <span className="text-sm font-medium text-on-surface-variant">{slaKnown} tickets with a published target</span>
              </div>
            </div>
            <div className="glass-panel rounded-xl p-6 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10"><span className="material-symbols-outlined text-6xl">merge</span></div>
              <h3 className="font-label-sm text-label-sm text-on-surface-variant mb-1">Duplicate Reports Merged</h3>
              <div className="font-headline-lg text-headline-lg text-primary flex items-baseline gap-2">
                {loading ? '—' : duplicatesFolded}
                <span className="text-sm font-medium text-on-surface-variant">{clusterCount} cluster(s)</span>
              </div>
            </div>
          </div>

          {/* Bento Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
            {/* Chart 1: Reporting Bias vs Action */}
            <div className="lg:col-span-8 glass-panel rounded-xl p-6 md:p-8 flex flex-col">
              <div className="flex justify-between items-start mb-8 flex-wrap gap-4">
                <div>
                  <h2 className="font-headline-md text-headline-md text-on-surface mb-2">Reporting Volume vs. Priority Weight</h2>
                  <p className="font-body-md text-body-md text-on-surface-variant">Raw complaint count vs the ward's share of scored TOPSIS priority</p>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-surface-variant border border-outline"></div><span className="font-label-sm text-label-sm text-on-surface-variant">Complaints</span></div>
                  <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-primary"></div><span className="font-label-sm text-label-sm text-on-surface-variant">Priority weight</span></div>
                </div>
              </div>

              {loading ? (
                <div className="h-64 bg-surface-container-low rounded-lg animate-pulse" />
              ) : wardStats.length === 0 ? (
                <p className="text-on-surface-variant">No ward-tagged tickets yet.</p>
              ) : (
                <>
                  <div className="flex-1 flex items-end gap-2 md:gap-6 h-64 border-b border-outline-variant/30 pb-2 relative">
                    {wardStats.map(w => {
                      const isInsightWard = insight && insight.ward === w.ward;
                      return (
                        <div key={w.ward} className="flex-1 flex justify-center items-end gap-1 md:gap-2 h-full z-10 group relative">
                          <div className="w-1/2 md:w-10 bg-surface-variant rounded-t-sm chart-bar transition-all" style={{ height: `${Math.max(4, w.complaintPct * 100)}%` }}></div>
                          <div className={`w-1/2 md:w-10 rounded-t-sm chart-bar transition-all ${isInsightWard ? 'bg-tertiary-container' : 'bg-primary'}`} style={{ height: `${Math.max(4, w.weightPct * 100)}%` }}></div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="flex justify-between items-center mt-2 px-1 text-center text-on-surface-variant font-label-sm text-label-sm">
                    {wardStats.map(w => (
                      <div key={w.ward} className={`flex-1 truncate ${insight && insight.ward === w.ward ? 'font-bold text-primary' : ''}`}>{w.ward}</div>
                    ))}
                  </div>
                  {insight && (
                    <div className="mt-8 bg-tertiary-fixed/30 border border-tertiary-fixed rounded-lg p-4 flex items-start gap-4">
                      <span className="material-symbols-outlined text-tertiary mt-0.5">lightbulb</span>
                      <p className="font-body-md text-body-md text-on-surface">
                        <strong>Insight:</strong> {insight.ward} files {pct(insight.complaintShare)} of complaints but carries {pct(insight.weightShare)} of scored priority weight — the model is directing more resources there than raw complaint volume alone would suggest.
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Chart 2: SLA Compliance by ward */}
            <div className="lg:col-span-4 glass-panel rounded-xl p-6 md:p-8 flex flex-col">
              <h2 className="font-headline-md text-headline-md text-on-surface mb-2">SLA Compliance by Ward</h2>
              <p className="font-body-md text-body-md text-on-surface-variant mb-6">Share of tickets currently on-track against their operational target</p>
              {loading ? (
                <div className="h-64 bg-surface-container-low rounded-lg animate-pulse" />
              ) : (
                <div className="flex-1 flex flex-col justify-center gap-3">
                  {wardStats.map(w => (
                    <div key={w.ward} className="flex items-center gap-3">
                      <span className="w-16 text-xs text-on-surface-variant truncate">{w.ward}</span>
                      <div className="flex-1 bg-surface-container-high h-3 rounded-full overflow-hidden">
                        {w.slaOnTrack != null ? (
                          <div className="bg-primary h-3 rounded-full" style={{ width: `${w.slaOnTrack * 100}%` }}></div>
                        ) : (
                          <div className="bg-outline-variant h-3 rounded-full w-full opacity-30"></div>
                        )}
                      </div>
                      <span className="w-10 text-xs text-right text-on-surface font-semibold">{w.slaOnTrack != null ? pct(w.slaOnTrack) : '—'}</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex justify-between items-center mt-6 border-t border-outline-variant/30 pt-4 text-xs text-on-surface-variant">
                <span>{totals.onTrack} on track</span>
                <span>{totals.atRisk} at risk</span>
                <span>{totals.overdue} overdue</span>
              </div>
              {chainOk != null && (
                <p className="text-xs text-on-surface-variant mt-4 flex items-center gap-1">
                  <span className={`material-symbols-outlined text-[16px] ${chainOk ? 'text-tertiary' : 'text-error'}`}>{chainOk ? 'verified_user' : 'gpp_bad'}</span>
                  Audit chain {chainOk ? 'verified' : 'FAILED verification'}
                </p>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
