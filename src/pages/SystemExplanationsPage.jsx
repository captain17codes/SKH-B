import React, { useState, useEffect } from 'react';
import AdminSidebar from '../components/AdminSidebar';
import { Link } from 'react-router-dom';
import { triageAPI, explainAPI } from '../api/client';

export default function SystemExplanationsPage() {
  const [manifest, setManifest] = useState(null);
  const [ticketExplain, setTicketExplain] = useState(null);
  const [shapRun, setShapRun] = useState(null);
  const [selectedTicketId, setSelectedTicketId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const init = async () => {
      try {
        // We use the raw endpoint here to get the today's manifest directly
        const res = await triageAPI.getToday();
        if (res) {
          setManifest(res);
          const firstTicket = res.scheduled?.[0]?.ticket_id || res.deferred?.[0]?.ticket_id;
          if (firstTicket) {
            setSelectedTicketId(firstTicket);
            const [tExplain, sRun] = await Promise.all([
              explainAPI.ticket(firstTicket),
              explainAPI.runShap(res.run_id).catch(e => ({ available: false, reason: e.message }))
            ]);
            setTicketExplain(tExplain);
            setShapRun(sRun);
          }
        }
      } catch (err) {
        if (err.status !== 404) {
          setError(err);
        }
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const handleTicketChange = async (e) => {
    const tid = e.target.value;
    setSelectedTicketId(tid);
    if (!tid) return;
    try {
      const tExplain = await explainAPI.ticket(tid);
      setTicketExplain(tExplain);
    } catch (err) {
      console.error(err);
    }
  };

  const AHP_LABELS = {
    C1_infra: 'Infrastructural Criticality',
    C2_safety: 'Public Safety',
    C3_equity: 'Socio-Spatial Equity',
    C4_cost: 'Resource Requirement'
  };

  const ahpColors = {
    C1_infra: 'bg-primary-fixed-dim',
    C2_safety: 'bg-tertiary-fixed',
    C3_equity: 'bg-secondary-fixed-dim',
    C4_cost: 'bg-surface-variant'
  };
  
  const ahpTextColors = {
    C1_infra: 'text-primary-fixed-dim',
    C2_safety: 'text-tertiary-fixed',
    C3_equity: 'text-secondary-fixed-dim',
    C4_cost: 'text-surface-variant'
  };

  return (
    <div className="bg-background text-on-surface font-body-md antialiased overflow-x-hidden selection:bg-primary-fixed selection:text-on-primary-fixed">
      {/* Top Nav (Desktop) */}
      <AdminSidebar />

      {/* Side Navigation */}
      <AdminSidebar />

      {/* Main Content */}
      <main className="md:ml-64 pt-20 md:pt-28 pb-24 md:pb-12 px-margin-mobile md:px-margin-desktop max-w-[1536px] mx-auto min-h-screen">
        <header className="mb-12">
          <div className="flex items-center gap-3 mb-2">
            <span className="material-symbols-outlined text-primary text-3xl">psychology</span>
            <h1 className="font-headline-display text-headline-display md:text-[48px] text-[32px] text-primary">Algorithmic Transparency</h1>
          </div>
          <p className="font-body-lg text-body-lg text-on-surface-variant max-w-3xl">
            Insight into the decision-making processes of the Kopargaon Civic Resource platform. Understanding how Fuzzy TOPSIS, AHP, and Knapsack optimization prioritize city maintenance.
          </p>
        </header>

        {loading ? (
          <div className="animate-pulse space-y-8">
            <div className="h-64 bg-surface-container rounded-xl w-full"></div>
            <div className="h-64 bg-surface-container rounded-xl w-full"></div>
          </div>
        ) : error ? (
          <div className="bg-error-container text-on-error-container p-6 rounded-xl font-semibold">
            {error.message || 'Failed to load explanations.'}
          </div>
        ) : !manifest ? (
          <div className="bg-surface-container-lowest p-8 rounded-xl border border-outline-variant/20 shadow-sm text-center">
            <h2 className="text-xl font-semibold mb-2">No manifest available for today.</h2>
            <p className="text-on-surface-variant">Run daily allocation first to generate explanations.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
            {/* Optimization Engine */}
            <section className="lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline/10 p-6 md:p-8 flex flex-col gap-6 relative overflow-hidden group">
              <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{backgroundImage: 'radial-gradient(#163422 1px, transparent 1px)', backgroundSize: '20px 20px'}}></div>
              <div className="flex justify-between items-start relative z-10">
                <div>
                  <h2 className="font-headline-lg text-headline-lg text-primary flex items-center gap-2"><span className="material-symbols-outlined text-tertiary-container">account_tree</span> Optimization Engine</h2>
                  <p className="font-body-md text-body-md text-on-surface-variant mt-1">Fuzzy TOPSIS &amp; Knapsack Integration</p>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10 flex-grow">
                <div className="bg-surface-bright border border-outline-variant rounded-lg p-5">
                  <div className="flex items-center gap-3 mb-3 text-primary"><div className="h-8 w-8 rounded-full bg-tertiary-fixed flex items-center justify-center"><span className="material-symbols-outlined text-[18px]">filter_alt</span></div><h3 className="font-headline-md text-[18px] font-bold">Fuzzy TOPSIS</h3></div>
                  <p className="font-body-md text-body-md text-on-surface-variant text-[14px]">Evaluates incoming tickets against multiple, often conflicting criteria (severity, impact, cost). It handles the inherent ambiguity in human reporting by using fuzzy logic to determine the "ideal" solution path.</p>
                </div>
                <div className="bg-surface-bright border border-outline-variant rounded-lg p-5">
                  <div className="flex items-center gap-3 mb-3 text-primary"><div className="h-8 w-8 rounded-full bg-secondary-fixed flex items-center justify-center"><span className="material-symbols-outlined text-[18px]">workspaces</span></div><h3 className="font-headline-md text-[18px] font-bold">Knapsack Constraint</h3></div>
                  <p className="font-body-md text-body-md text-on-surface-variant text-[14px]">Once tickets are ranked, the Knapsack algorithm allocates daily resources (budget, labor, equipment) optimally, ensuring the highest priority tasks are addressed without exceeding available municipal capacity.</p>
                </div>
              </div>
            </section>

            {/* AHP Weights */}
            <section className="lg:col-span-4 bg-primary text-on-primary rounded-xl p-6 md:p-8 flex flex-col gap-6 relative overflow-hidden">
              <div className="absolute -top-20 -right-20 w-64 h-64 bg-primary-container rounded-full blur-3xl opacity-50"></div>
              <div className="relative z-10">
                <h2 className="font-headline-lg text-[24px] font-bold flex items-center gap-2"><span className="material-symbols-outlined text-tertiary-fixed">balance</span> Current AHP Weights</h2>
                <p className="font-body-md text-body-md text-primary-fixed-dim mt-1 text-[14px]">Real-time criteria calibration</p>
              </div>
              <div className="flex flex-col gap-5 relative z-10 mt-2">
                {manifest.weights && Object.entries(manifest.weights).map(([key, val]) => (
                  <div key={key}>
                    <div className="flex justify-between text-label-sm font-label-sm mb-2"><span className="text-on-primary">{AHP_LABELS[key] || key}</span><span className={`${ahpTextColors[key] || 'text-surface-variant'} font-bold`}>{(val * 100).toFixed(1)}%</span></div>
                    <div className="w-full bg-primary-container h-2 rounded-full overflow-hidden"><div className={`${ahpColors[key] || 'bg-surface-variant'} h-full rounded-full`} style={{width: `${val * 100}%`}}></div></div>
                  </div>
                ))}
              </div>
            </section>

            {/* Ticket Explanations Section */}
            <section className="lg:col-span-12 bg-surface-container-lowest rounded-xl border border-outline/10 p-6 md:p-8 flex flex-col gap-6 mt-4">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-outline-variant pb-4">
                <div>
                  <h2 className="font-headline-lg text-headline-lg text-primary flex items-center gap-2"><span className="material-symbols-outlined text-primary-container">model_training</span> Ticket Explanation &amp; AI Justification</h2>
                  <p className="font-body-md text-body-md text-on-surface-variant mt-1">Analyzing exact TOPSIS attribution and feature contributions.</p>
                </div>
                <div className="flex items-center gap-2 bg-surface-container-low px-4 py-2 rounded-lg border border-outline-variant">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">Selected Ticket:</span>
                  <select 
                    value={selectedTicketId} 
                    onChange={handleTicketChange} 
                    className="bg-transparent font-headline-md text-[16px] font-bold text-primary outline-none focus:ring-0 cursor-pointer min-w-[200px]"
                  >
                    <optgroup label="Scheduled">
                      {manifest?.scheduled?.map(t => (
                        <option key={t.ticket_id} value={t.ticket_id}>{t.ref_no} ({t.category})</option>
                      ))}
                    </optgroup>
                    <optgroup label="Deferred">
                      {manifest?.deferred?.map(t => (
                        <option key={t.ticket_id} value={t.ticket_id}>{t.ref_no} ({t.category})</option>
                      ))}
                    </optgroup>
                  </select>
                </div>
              </div>

              {ticketExplain ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 pt-2">
                  <div className="lg:col-span-2 flex flex-col gap-4">
                    
                    {/* TOPSIS Exact Attribution */}
                    <div className="mb-6">
                      <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-4">TOPSIS Exact Additive Attribution</h3>
                      <p className="text-sm text-on-surface-variant mb-6">The criteria contributions mathematically sum exactly to the final priority score (CCi).</p>
                      
                      <div className="space-y-4 mb-6">
                        {ticketExplain.attribution?.criteria?.map((crit, idx) => {
                          const pct = (crit.contribution / 1.0) * 100;
                          const share = (crit.share_of_score * 100).toFixed(1);
                          const colors = ['bg-tertiary-fixed', 'bg-primary-fixed-dim', 'bg-secondary-fixed-dim', 'bg-primary'];
                          return (
                            <div key={crit.criterion}>
                              <div className="flex justify-between text-sm mb-1">
                                <span className="text-on-surface font-semibold">{crit.label}</span>
                                <span className="font-bold text-primary">+{crit.contribution.toFixed(4)} ({share}%)</span>
                              </div>
                              <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden flex">
                                <div className={`${colors[idx%colors.length]} h-2`} style={{width: `${pct}%`}}></div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      
                      <div className="border-t border-outline-variant pt-3 flex justify-between items-center text-[16px] bg-surface-container-low p-4 rounded-lg">
                        <span className="font-bold text-on-surface">Total Priority Score (CCi)</span>
                        <span className="font-bold text-primary">{ticketExplain.attribution?.sum_of_contributions?.toFixed(4)}</span>
                      </div>
                    </div>

                  </div>
                  
                  {/* NLP Justification */}
                  <div className="bg-surface-bright rounded-lg p-6 border border-outline-variant h-full flex flex-col">
                    <div className="flex items-center gap-2 mb-4"><span className="material-symbols-outlined text-primary">chat_bubble</span><h3 className="font-label-sm text-label-sm font-bold text-primary">Natural Language Synthesis</h3></div>
                    <p className="font-body-md text-body-md text-on-surface-variant italic mb-4 leading-relaxed">
                      "{ticketExplain.officer_rationale || ticketExplain.citizen_message_en}"
                    </p>
                    <div className="mt-auto">
                      <div className="inline-flex items-center gap-2 bg-tertiary-fixed/30 text-primary-container px-3 py-1 rounded-full text-xs font-label-sm border border-tertiary-fixed">
                        <span className="material-symbols-outlined text-[14px]">check_circle</span> Computed Rationale
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-on-surface-variant">
                  Select a ticket to view its exact attribution breakdown.
                </div>
              )}
            </section>

          </div>
        )}
      </main>
    </div>
  );
}
