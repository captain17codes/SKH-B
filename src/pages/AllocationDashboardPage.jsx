import React, { useState, useEffect } from 'react';
import AdminSidebar from '../components/AdminSidebar';
import { Link } from 'react-router-dom';
import { triageAPI, tolerate404 } from '../api/client';
import { categoryIcon } from '../components/categoryIcon';

export default function AllocationDashboardPage() {
  const [manifest, setManifest] = useState(null);
  const [savedManifestDate, setSavedManifestDate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const [isDryRun, setIsDryRun] = useState(false);
  const [budgetInput, setBudgetInput] = useState('');
  const [hoursInput, setHoursInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showAllAllocated, setShowAllAllocated] = useState(false);

  const loadData = async () => {
    try {
      const res = await tolerate404(() => triageAPI.getToday());
      if (!res.found) {
        setNotFound(true);
        try {
          const cap = await triageAPI.getCapacity();
          setBudgetInput(cap.daily_budget_inr || '');
          setHoursInput(cap.daily_workforce_hours || '');
        } catch {
          // ignore capacity fetch error
        }
      } else {
        setManifest(res.data);
        setSavedManifestDate(res.data.dispatch_date);
        setIsDryRun(false);
        setBudgetInput(res.data.budget_cap || '');
        setHoursInput(res.data.workforce_cap_hours || '');
      }
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handlePreview = async () => {
    try {
      setIsSubmitting(true);
      const res = await triageAPI.dryRun(Number(budgetInput), Number(hoursInput));
      setManifest(res);
      setIsDryRun(true);
    } catch(err) {
      setError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRun = async () => {
    try {
      setIsSubmitting(true);
      const res = await triageAPI.runWith({ daily_budget: Number(budgetInput), daily_workforce: Number(hoursInput) });
      setManifest(res);
      setIsDryRun(false);
      setSavedManifestDate(res.dispatch_date);
      setNotFound(false);
    } catch(err) {
      setError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const exportCSV = () => {
    if (!manifest) return;
    const header = ['ref_no', 'ward_id', 'category', 'rank', 'cci_score', 'cost_estimate', 'hours_estimate', 'reason_code'].join(',');
    const rows = (manifest.scheduled || []).map(r => {
      return [
        r.ref_no,
        r.ward_id,
        r.category,
        r.rank,
        r.cci_score,
        r.cost_estimate ?? '',
        r.hours_estimate ?? '',
        r.reason_code
      ].join(',');
    });
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dispatch-${manifest.dispatch_date}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const renderMainContent = () => {
    if (loading) {
      return (
        <main className="flex-1 p-4 md:p-8 max-w-container-max mx-auto w-full">
           <div className="animate-pulse space-y-8">
             <div className="h-8 bg-surface-container rounded w-1/4"></div>
             <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
               <div className="h-32 bg-surface-container rounded-xl"></div>
               <div className="h-32 bg-surface-container rounded-xl"></div>
               <div className="h-32 bg-surface-container rounded-xl"></div>
             </div>
             <div className="h-96 bg-surface-container rounded-xl"></div>
           </div>
        </main>
      );
    }

    if (error) {
      const msg = error.isOffline ? "Cannot reach the backend at http://localhost:8000. Is it running?" : error.message;
      return (
        <main className="flex-1 p-4 md:p-8 max-w-container-max mx-auto w-full">
          <div className="bg-error-container text-on-error-container p-6 rounded-xl font-semibold">
            {msg}
          </div>
        </main>
      );
    }

    const today = new Date().toISOString().split('T')[0];

    return (
      <main className="flex-1 p-4 md:p-8 max-w-container-max mx-auto w-full">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-headline-lg font-headline-lg text-on-surface mb-2">Daily Dispatch Manifest</h1>
            <p className="text-body-md font-body-md text-on-surface-variant">Optimal task allocation based on Knapsack Dynamic Programming algorithm for today.</p>
          </div>
          <div className="relative w-full md:w-64">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">search</span>
            <input className="w-full pl-10 pr-4 py-2 bg-surface-container rounded-lg border border-outline-variant/30 focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-sm" placeholder="Search manifest..." type="text" />
          </div>
        </div>

        {notFound && !manifest ? (
          <div className="max-w-2xl mx-auto mt-12">
            <div className="bg-surface-container-lowest p-8 rounded-xl border border-outline-variant/20 shadow-sm text-center mb-6">
              <h2 className="text-xl font-semibold mb-2 text-on-surface">No dispatch manifest has been issued for {today} yet.</h2>
              <p className="text-on-surface-variant">Configure capacity and run triage to generate today's manifest.</p>
            </div>
            {/* Run Controls */}
            <div className="flex flex-col md:flex-row items-center gap-4 bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/20 shadow-sm">
              <div className="flex items-center gap-2">
                <label className="text-sm text-on-surface-variant">Budget (₹)</label>
                <input type="number" value={budgetInput} onChange={e => setBudgetInput(e.target.value)} className="w-32 px-3 py-1 bg-surface-container rounded-lg border border-outline-variant/30 text-sm focus:outline-none" />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-on-surface-variant">Hours</label>
                <input type="number" value={hoursInput} onChange={e => setHoursInput(e.target.value)} className="w-24 px-3 py-1 bg-surface-container rounded-lg border border-outline-variant/30 text-sm focus:outline-none" />
              </div>
              <div className="ml-auto flex gap-2">
                <button onClick={handlePreview} disabled={isSubmitting} className="px-4 py-2 bg-secondary-container text-on-secondary-container rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50">
                  {isSubmitting ? 'Computing...' : 'Preview'}
                </button>
                <button onClick={handleRun} disabled={isSubmitting} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50">
                  {isSubmitting ? 'Computing...' : 'Run triage'}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Run Controls */}
            <div className="flex flex-col md:flex-row items-center gap-4 bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/20 shadow-sm mb-6">
              <div className="font-semibold text-on-surface">Dispatch Date: {manifest.dispatch_date}</div>
              <div className="flex items-center gap-2 ml-4">
                <label className="text-sm text-on-surface-variant">Budget (₹)</label>
                <input type="number" value={budgetInput} onChange={e => setBudgetInput(e.target.value)} className="w-32 px-3 py-1 bg-surface-container rounded-lg border border-outline-variant/30 text-sm focus:outline-none" />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-on-surface-variant">Hours</label>
                <input type="number" value={hoursInput} onChange={e => setHoursInput(e.target.value)} className="w-24 px-3 py-1 bg-surface-container rounded-lg border border-outline-variant/30 text-sm focus:outline-none" />
              </div>
              <div className="ml-auto flex gap-2">
                <button onClick={handlePreview} disabled={isSubmitting} className="px-4 py-2 bg-secondary-container text-on-secondary-container rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50">
                  {isSubmitting ? 'Computing...' : 'Preview'}
                </button>
                <button onClick={handleRun} disabled={isSubmitting} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50">
                  {isSubmitting ? 'Computing...' : 'Run triage'}
                </button>
              </div>
            </div>

            {isDryRun && (
              <div className="bg-[#fff3e0] text-[#ef6c00] p-3 rounded-lg mb-6 text-sm font-semibold border border-[#ffcc80]">
                Preview only — nothing has been saved. The dispatch manifest on record is still the one from {savedManifestDate}.
              </div>
            )}

            {/* Solver Honesty Strip */}
            <div className="flex flex-wrap gap-2 mb-4">
              <span className="px-2 py-1 bg-surface-container-high rounded text-xs text-on-surface">{manifest.solver_status}</span>
              <span className="px-2 py-1 bg-surface-container-high rounded text-xs text-on-surface">{manifest.solver}</span>
              <span className="px-2 py-1 bg-surface-container-high rounded text-xs text-on-surface">{manifest.solver_optimal ? 'optimal' : 'suboptimal'}</span>
              <span className="px-2 py-1 bg-surface-container-high rounded text-xs text-on-surface">{manifest.states_explored} states explored</span>
              <span className="px-2 py-1 bg-surface-container-high rounded text-xs text-on-surface">{manifest.budget_outcome}</span>
            </div>
            {manifest.solver_status === 'MANDATORY_OVER_CAPACITY' && (
              <div className="bg-error-container text-on-error-container p-3 rounded-lg mb-6 text-sm font-semibold">
                Statutory and safety-floor work alone exceeds today's capacity. This plan is not feasible as it stands — capacity must be raised or a floor must be formally waived.
              </div>
            )}
            {(manifest.solver_status === 'FEASIBLE_BEAM_LIMITED' || manifest.solver_optimal === false) && (
              <div className="bg-[#fff3e0] text-[#ef6c00] p-3 rounded-lg mb-6 text-sm font-semibold border border-[#ffcc80]">
                Search was truncated for speed; this is a good plan, not a proven optimal one.
              </div>
            )}
            {manifest.solver_status === 'NOT_RUN' && (
              <div className="bg-surface-container-high text-on-surface p-3 rounded-lg mb-6 text-sm font-semibold">
                Nothing was optimised.
              </div>
            )}

            {/* Summary Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/20 shadow-sm relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10"><span className="material-symbols-outlined text-6xl text-primary">star_rate</span></div>
                <p className="text-label-sm font-label-sm text-on-surface-variant mb-1 uppercase tracking-wider">Total Priority Score</p>
                <p className="text-headline-display font-headline-display text-primary">{(manifest.objective_value ?? manifest.plan?.objective_value)?.toFixed(2) || '—'}</p>
                <p className="text-sm text-on-surface-variant mt-2">
                  sum of the closeness scores of the {manifest.summary?.scheduled ?? manifest.scheduled_count} tickets dispatched
                </p>
              </div>
              <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/20 shadow-sm relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10"><span className="material-symbols-outlined text-6xl text-primary">account_balance_wallet</span></div>
                <p className="text-label-sm font-label-sm text-on-surface-variant mb-1 uppercase tracking-wider">Budget Utilization</p>
                {(() => {
                  const cap = manifest.budget_cap;
                  const used = manifest.budget_used ?? manifest.plan?.budget_used;
                  const pct = cap ? Math.round((used / cap) * 100) : NaN;
                  return (
                    <>
                      <div className="flex items-end gap-2 mb-2"><p className="text-headline-display font-headline-display text-primary">{cap ? pct : '—'}<span className="text-headline-md">{cap ? '%' : ''}</span></p></div>
                      {cap ? (
                        <div className="w-full bg-surface-container-high rounded-full h-2 mb-2"><div className="bg-primary h-2 rounded-full" style={{width: `${pct}%`}}></div></div>
                      ) : (
                        <p className="text-sm mb-2">no budget recorded</p>
                      )}
                      <p className="text-sm text-on-surface-variant mt-2">₹{used?.toLocaleString('en-IN') ?? '0'} / ₹{cap?.toLocaleString('en-IN') ?? '0'} allocated</p>
                      {manifest.capacity_verified ? (
                        <p className="text-xs text-outline mt-1">verified by {manifest.capacity_verified_by}</p>
                      ) : (
                        <p className="text-xs text-[#9a6a16] mt-1">unverified default capacity — no officer has signed for today's budget or crew</p>
                      )}
                    </>
                  );
                })()}
              </div>
              <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/20 shadow-sm relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10"><span className="material-symbols-outlined text-6xl text-primary">group</span></div>
                <p className="text-label-sm font-label-sm text-on-surface-variant mb-1 uppercase tracking-wider">Workforce Hours</p>
                {(() => {
                  const wCap = manifest.workforce_cap_hours;
                  const wUsed = manifest.workforce_used ?? manifest.plan?.workforce_used;
                  const wPct = wCap ? Math.round((wUsed / wCap) * 100) : NaN;
                  const isNearMax = wPct >= 90;
                  const barColor = isNearMax ? 'bg-[#d32f2f]' : 'bg-primary';
                  return (
                    <>
                      <div className="flex items-end gap-2 mb-2"><p className="text-headline-display font-headline-display text-primary">{wCap ? wPct : '—'}<span className="text-headline-md">{wCap ? '%' : ''}</span></p></div>
                      {wCap ? (
                        <div className="w-full bg-surface-container-high rounded-full h-2 mb-2"><div className={`${barColor} h-2 rounded-full`} style={{width: `${wPct}%`}}></div></div>
                      ) : (
                        <p className="text-sm mb-2">no capacity recorded</p>
                      )}
                      <p className="text-sm text-on-surface-variant mt-2">{wUsed ?? 0} hrs / {wCap ?? 0} hrs capacity {isNearMax && '(Near Max)'}</p>
                      {manifest.capacity_verified ? (
                        <p className="text-xs text-outline mt-1">verified by {manifest.capacity_verified_by}</p>
                      ) : (
                        <p className="text-xs text-[#9a6a16] mt-1">unverified default capacity — no officer has signed for today's budget or crew</p>
                      )}
                    </>
                  );
                })()}
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
              {/* Main Table */}
              <div className="xl:col-span-2">
                <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm overflow-hidden">
                  <div className="p-6 border-b border-outline-variant/20 flex justify-between items-center bg-surface-container-low">
                    <h3 className="text-headline-md font-headline-md text-on-surface">Allocated Tickets</h3>
                    <button onClick={exportCSV} className="text-primary text-sm font-semibold flex items-center gap-1 hover:underline">Export CSV <span className="material-symbols-outlined text-[18px]">download</span></button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-surface border-b border-outline-variant/20">
                          <th className="p-4 text-label-sm font-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Issue ID / Desc</th>
                          <th className="p-4 text-label-sm font-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Ward</th>
                          <th className="p-4 text-label-sm font-label-sm text-on-surface-variant uppercase tracking-wider font-semibold text-center">TOPSIS Score</th>
                          <th className="p-4 text-label-sm font-label-sm text-on-surface-variant uppercase tracking-wider font-semibold text-right">Est. Hours</th>
                          <th className="p-4 text-label-sm font-label-sm text-on-surface-variant uppercase tracking-wider font-semibold text-right">Est. Cost</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-outline-variant/10">
                        {(showAllAllocated ? manifest.scheduled : manifest.scheduled?.slice(0, 8))?.map(r => (
                          <tr key={r.ticket_id} className="hover:bg-surface-container-low/50 transition-colors">
                            <td className="p-4">
                              <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-primary-container/20 flex items-center justify-center text-primary">
                                  <span className="material-symbols-outlined text-[20px]">{categoryIcon(r.category)}</span>
                                </div>
                                <div>
                                  <p className="font-semibold text-on-surface">{r.ref_no}</p>
                                  <p className="text-sm text-on-surface-variant truncate max-w-[200px]">{r.description || '—'}</p>
                                  <p className="text-xs text-outline mt-0.5">Rank {r.rank}</p>
                                </div>
                              </div>
                              {r.reason_code === 'allocated_mandatory_floor' && (
                                <span title={r.reason_text} className="inline-block mt-2 text-[10px] bg-error-container text-on-error-container px-1.5 py-0.5 rounded uppercase tracking-wider font-bold">Mandatory floor</span>
                              )}
                            </td>
                            <td className="p-4 text-on-surface">{r.ward_id || '—'}</td>
                            <td className="p-4 text-center">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${r.cci_score >= 0.8 ? 'bg-[#e8f5e9] text-[#2e7d32] border-[#a5d6a7]' : 'bg-[#fff3e0] text-[#ef6c00] border-[#ffcc80]'}`}>
                                {r.cci_score?.toFixed(3)}
                              </span>
                            </td>
                            <td className="p-4 text-right text-on-surface font-mono">
                              {r.hours_estimate != null ? `${r.hours_estimate}h` : '—'}
                            </td>
                            <td className="p-4 text-right text-on-surface font-mono">
                              {r.cost_estimate != null ? `₹${r.cost_estimate.toLocaleString('en-IN')}` : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="p-4 border-t border-outline-variant/20 bg-surface text-center">
                    <button onClick={() => setShowAllAllocated(!showAllAllocated)} className="text-sm font-semibold text-primary hover:underline">
                      {showAllAllocated ? 'Show fewer' : `Show all ${manifest.summary?.scheduled ?? manifest.scheduled_count} allocated tickets`}
                    </button>
                  </div>
                </div>
              </div>

              {/* Side Panel */}
              <div className="xl:col-span-1 flex flex-col gap-6">
                
                {/* Why this plan */}
                <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm p-6">
                  <h3 className="text-headline-md font-headline-md text-on-surface mb-4">Why this plan</h3>
                  <div className="space-y-3 mb-4">
                    {Object.entries(manifest.weights || {}).map(([crit, val]) => (
                      <div key={crit} className="flex items-center gap-2">
                        <span className="w-24 text-xs font-semibold truncate text-on-surface">{crit}</span>
                        <div className="flex-1 bg-surface-container-high h-2 rounded-full overflow-hidden">
                          <div className="bg-primary h-2 rounded-full" style={{width: `${val * 100}%`}}></div>
                        </div>
                        <span className="w-12 text-xs text-right text-on-surface">{val.toFixed(3)}</span>
                      </div>
                    ))}
                    <p className="text-xs text-on-surface-variant text-right">criteria weights v{manifest.weight_version}</p>
                  </div>
                  <div className="space-y-1 mb-4">
                    {(manifest.normalisation_notes || []).map((n, i) => <p key={`n-${i}`} className="text-xs text-on-surface-variant">• {n}</p>)}
                    {(manifest.allocator_notes || manifest.plan?.allocator_notes || []).map((n, i) => <p key={`a-${i}`} className="text-xs text-on-surface-variant">• {n}</p>)}
                  </div>
                  {(manifest.cost_incomplete_count ?? manifest.unscorable?.length ?? 0) > 0 && (
                    <p className="text-sm text-on-surface">
                      {manifest.cost_incomplete_count ?? manifest.unscorable?.length} tickets could not be considered at all because their cost has not been estimated yet. <Link to="/ticket-pool" className="text-primary hover:underline">View in Ticket Pool</Link>
                    </p>
                  )}
                </div>

                {/* Deferred Panel */}
                <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm p-6">
                  <h3 className="text-headline-md font-headline-md text-on-surface mb-6 flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary">pending_actions</span> Deferred, and why
                  </h3>
                  <div className="space-y-6">
                    {(() => {
                      const groupedDeferred = Object.entries((manifest.deferred || []).reduce((acc, row) => {
                        if (!acc[row.reason_code]) acc[row.reason_code] = { count: 0, reason_text: row.reason_text, rows: [] };
                        acc[row.reason_code].count++;
                        acc[row.reason_code].rows.push(row);
                        return acc;
                      }, {})).sort((a, b) => b[1].count - a[1].count);

                      return groupedDeferred.map(([code, data]) => (
                        <div key={code} className="mb-4 border-l-2 border-outline-variant pl-4">
                          <h4 className="font-semibold text-on-surface">{code} ({data.count} tickets)</h4>
                          <p className="text-sm text-on-surface-variant mb-2">{data.reason_text}</p>
                          <ul className="space-y-1">
                            {data.rows.map(r => (
                              <li key={r.ticket_id} className="text-xs flex gap-2 text-on-surface items-center">
                                <span className="w-32 truncate font-mono">{r.ref_no}</span>
                                <span className="w-16">{r.ward_id || '—'}</span>
                                <span className="w-12">{r.cci_score?.toFixed(3)}</span>
                                <span className="text-on-surface-variant text-right flex-1 truncate">
                                  {r.cost_status === 'COST_INCOMPLETE' ? 'not costed' : (r.cost_estimate != null ? `₹${r.cost_estimate.toLocaleString('en-IN')}` : '—')}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ));
                    })()}
                  </div>
                </div>

                {/* Ward Bar Chart */}
                <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm p-6 h-64 overflow-y-auto">
                  <h3 className="text-headline-md font-headline-md text-on-surface mb-4">Today's dispatch by ward</h3>
                  <div className="space-y-2">
                    {(() => {
                      const wardCounts = {};
                      const allWards = new Set();
                      (manifest.scheduled || []).forEach(r => {
                        const w = r.ward_id || 'Ward unassigned';
                        wardCounts[w] = (wardCounts[w] || 0) + 1;
                        allWards.add(w);
                      });
                      (manifest.deferred || []).forEach(r => {
                        allWards.add(r.ward_id || 'Ward unassigned');
                      });
                      const sortedWards = Array.from(allWards).sort();
                      const maxCount = Math.max(...Object.values(wardCounts), 1);
                      return sortedWards.map(w => {
                        const count = wardCounts[w] || 0;
                        return (
                          <div key={w} className="flex items-center gap-2">
                            <span className="w-24 truncate text-xs text-on-surface-variant">{w}</span>
                            <div className="flex-1 bg-surface-container-high h-4 rounded-sm flex items-center">
                              {count > 0 && <div className="bg-primary h-4 rounded-sm" style={{width: `${(count/maxCount)*100}%`}}></div>}
                            </div>
                            <span className={`w-6 text-xs text-right ${count === 0 ? 'text-outline' : 'text-on-surface font-semibold'}`}>{count}</span>
                          </div>
                        );
                      });
                    })()}
                  </div>
                </div>

              </div>
            </div>
          </>
        )}
      </main>
    );
  };

  return (
    <div className="bg-background text-on-background font-body-md min-h-screen flex">
      <AdminSidebar />

      {/* Main Content */}
      <div className="flex-1 lg:ml-64 flex flex-col min-h-screen relative">
        <header className="lg:hidden bg-surface-container-low shadow-sm sticky top-0 z-50 px-4 py-4 flex justify-between items-center border-b border-outline-variant/20">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-2xl icon-filled">account_balance</span>
            <span className="text-headline-lg-mobile font-headline-lg-mobile text-primary">Kopargaon Civic</span>
          </div>
          <button className="text-on-surface"><span className="material-symbols-outlined text-2xl">menu</span></button>
        </header>
        
        {renderMainContent()}
      </div>
    </div>
  );
}
