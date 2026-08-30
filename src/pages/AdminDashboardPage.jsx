import React, { useState, useEffect, useCallback } from 'react';
import AdminSidebar from '../components/AdminSidebar';
import { Link } from 'react-router-dom';
import SystemSummaryBlock from '../components/SystemSummaryBlock';
import { triageAPI, explainAPI, tolerate404 } from '../api/client';
import { categoryIcon, titleCase } from '../components/categoryIcon';

const STATUS_STYLE = {
  resolved: { dot: 'bg-[#059669]', label: 'Completed' },
  completed: { dot: 'bg-[#059669]', label: 'Completed' },
  in_progress: { dot: 'bg-[#d97706]', label: 'In Progress' },
  scheduled: { dot: 'bg-[#d97706]', label: 'Scheduled' },
  assigned: { dot: 'bg-[#d97706]', label: 'Assigned' },
  pending_assessment: { dot: 'bg-outline', label: 'Pending Assessment' },
  new: { dot: 'bg-error', label: 'Unassigned' },
  triaged: { dot: 'bg-outline', label: 'Triaged' },
};

function statusFor(status) {
  return STATUS_STYLE[status] || { dot: 'bg-outline', label: status ? titleCase(status) : 'Unknown' };
}

const CATEGORY_BADGE = 'inline-flex items-center gap-1 text-label-sm font-label-sm px-2 py-1 rounded-md';

export default function AdminDashboardPage() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const [selectedTicketId, setSelectedTicketId] = useState(null);
  const [explain, setExplain] = useState(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [explainError, setExplainError] = useState(null);

  const [messageStatus, setMessageStatus] = useState({ sending: false, sentVia: null });

  const handleSendMessage = (method, text) => {
    setMessageStatus({ sending: true, sentVia: method });
    // Simulate network delay for hackathon demo
    setTimeout(() => {
      setMessageStatus({ sending: false, sentVia: method });
      // Optionally open real app links too
      if (method === 'whatsapp') {
        window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
      } else {
        window.location.href = `sms:?body=${encodeURIComponent(text)}`;
      }
      setTimeout(() => setMessageStatus({ sending: false, sentVia: null }), 3000);
    }, 1500);
  };

  const loadExplanation = useCallback(async (ticketId) => {
    if (!ticketId) return;
    setExplainLoading(true);
    setExplainError(null);
    try {
      const res = await explainAPI.ticket(ticketId);
      setExplain(res);
    } catch (err) {
      setExplain(null);
      setExplainError(err.message || 'No explanation available for this ticket yet.');
    } finally {
      setExplainLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await triageAPI.getPriorities({ limit: 8 });
        if (!mounted) return;
        const list = data.tickets || [];
        setTickets(list);
        setLastUpdated(new Date());
        if (list.length > 0) {
          setSelectedTicketId(list[0].id);
          loadExplanation(list[0].id);
        }
      } catch (err) {
        if (mounted) setError(err.message || 'Failed to load ticket pool');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, [loadExplanation]);

  const handleSelect = (ticket) => {
    setSelectedTicketId(ticket.id);
    loadExplanation(ticket.id);
  };

  const criteria = explain?.attribution?.criteria || [];
  const maxAbs = Math.max(1, ...criteria.map(c => Math.abs(c.contribution || 0)));
  const barColors = ['bg-error', 'bg-primary', 'bg-secondary', 'bg-tertiary'];

  return (
    <div className="antialiased flex h-screen overflow-hidden">
      {/* Mobile Header */}
      <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-4 py-4 bg-surface/80 backdrop-blur-md md:hidden border-b border-outline-variant/10">
        <div className="text-headline-lg-mobile font-headline-lg-mobile font-bold text-primary">Kopargaon Digital</div>
        <span className="material-symbols-outlined text-primary cursor-pointer">menu</span>
      </header>

      <AdminSidebar />

      {/* Main Content */}
      <main className="flex-grow flex flex-col md:ml-64 pt-20 md:pt-8 px-4 md:px-margin-desktop overflow-y-auto h-full bg-background relative">
        <div className="absolute inset-0 pointer-events-none opacity-[0.03] z-0" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #163422 1px, transparent 0)', backgroundSize: '32px 32px' }}></div>
        <div className="relative z-10 w-full max-w-container-max mx-auto pb-24">
          <header className="mb-12 flex flex-col md:flex-row justify-between md:items-end gap-4">
            <div>
              <h1 className="text-headline-display font-headline-display text-primary mb-2">Priority Operations</h1>
              <p className="text-body-lg font-body-lg text-on-surface-variant max-w-2xl">Today's algorithmic allocation for Kopargaon municipal tasks. Priority is weighted by urgency, citizen impact, and resource availability.</p>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-label-sm font-label-sm text-secondary bg-surface-container-high px-3 py-1 rounded-full">
                {lastUpdated ? `Last updated: ${lastUpdated.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}` : 'Loading…'}
              </span>
            </div>
          </header>

          <div className="mb-8">
            <SystemSummaryBlock />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
            {/* Ticket List */}
            <div className="lg:col-span-8 flex flex-col gap-6">
              <div className="bg-surface rounded-xl border border-outline-variant/20 shadow-sm overflow-hidden flex flex-col min-h-[500px]">
                <div className="px-6 py-4 border-b border-outline-variant/10 bg-surface-container-lowest flex justify-between items-center">
                  <h2 className="text-headline-md font-headline-md text-primary">Ranked Ticket Pool</h2>
                  <Link to="/ticket-pool" className="text-label-sm font-label-sm text-primary flex items-center gap-1 hover:text-primary-container transition-colors">
                    View all <span className="material-symbols-outlined text-sm">arrow_forward</span>
                  </Link>
                </div>
                <div className="overflow-y-auto flex-grow">
                  {error ? (
                    <div className="p-6 text-error font-body-md text-body-md">{error}</div>
                  ) : loading ? (
                    <div className="p-6 space-y-3 animate-pulse">
                      {Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-10 bg-surface-container rounded" />)}
                    </div>
                  ) : tickets.length === 0 ? (
                    <div className="p-6 text-on-surface-variant font-body-md text-body-md">No scored tickets yet. Run triage to build today's priority order.</div>
                  ) : (
                    <table className="w-full text-left border-collapse">
                      <thead className="sticky top-0 bg-surface-container-lowest border-b border-outline-variant/20 z-10">
                        <tr>
                          <th className="py-3 px-6 text-label-sm font-label-sm text-on-surface-variant font-semibold">ID</th>
                          <th className="py-3 px-6 text-label-sm font-label-sm text-on-surface-variant font-semibold">Category</th>
                          <th className="py-3 px-6 text-label-sm font-label-sm text-on-surface-variant font-semibold">Ward</th>
                          <th className="py-3 px-6 text-label-sm font-label-sm text-primary font-bold">CCi Score</th>
                          <th className="py-3 px-6 text-label-sm font-label-sm text-on-surface-variant font-semibold">Status</th>
                        </tr>
                      </thead>
                      <tbody className="text-body-md font-body-md text-on-surface divide-y divide-outline-variant/10">
                        {tickets.map((t) => {
                          const st = statusFor(t.status);
                          const isSelected = selectedTicketId === t.id;
                          return (
                            <tr
                              key={t.id}
                              className={`table-row-hover cursor-pointer transition-colors ${isSelected ? 'bg-primary/5' : ''}`}
                              onClick={() => handleSelect(t)}
                            >
                              <td className="py-4 px-6 font-mono text-sm text-primary">{t.ref_no ?? `#${t.id.slice(0, 8)}`}</td>
                              <td className="py-4 px-6">
                                <span className={`${CATEGORY_BADGE} bg-surface-container-high text-on-surface`}>
                                  <span className="material-symbols-outlined text-[14px]">{categoryIcon(t.category)}</span>
                                  {titleCase(t.category)}
                                </span>
                              </td>
                              <td className="py-4 px-6 text-on-surface-variant">{t.ward_id ?? 'Unassigned'}</td>
                              <td className="py-4 px-6 font-bold text-primary">{t.scored ? t.cci_score?.toFixed(3) : '—'}</td>
                              <td className="py-4 px-6">
                                <span className={`w-2 h-2 inline-block rounded-full ${st.dot} mr-2`}></span>{st.label}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </div>

            {/* AI Insight Panel */}
            <div className="lg:col-span-4 flex flex-col gap-6">
              <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm p-6 relative overflow-hidden flex flex-col h-full">
                <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none"></div>
                <div className="relative z-10 mb-6 flex justify-between items-start">
                  <div>
                    <div className="text-label-sm font-label-sm text-secondary mb-1 uppercase tracking-wider">AI Priority Explanation</div>
                    <h3 className="text-headline-md font-headline-md text-primary">
                      {tickets.find(t => t.id === selectedTicketId)?.ref_no || (loading ? 'Loading…' : 'Select a ticket')}
                    </h3>
                  </div>
                  <span className="material-symbols-outlined text-tertiary-container bg-tertiary-container/10 p-2 rounded-full">psychology</span>
                </div>

                {explainLoading ? (
                  <div className="animate-pulse space-y-3">
                    <div className="h-16 bg-surface-container-low rounded-lg" />
                    <div className="h-4 bg-surface-container-low rounded w-3/4" />
                    <div className="h-4 bg-surface-container-low rounded w-2/3" />
                  </div>
                ) : explainError ? (
                  <div className="bg-surface-container-low p-4 rounded-lg border border-outline-variant/10 relative z-10 text-body-md font-body-md text-on-surface-variant">
                    {explainError}
                  </div>
                ) : explain ? (
                  <>
                    <div className="bg-surface-container-low p-4 rounded-lg border border-outline-variant/10 mb-6 relative z-10">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="material-symbols-outlined text-[18px] text-primary">chat</span>
                        <span className="text-label-sm font-semibold text-on-surface">Stakeholder Response</span>
                      </div>
                      <p className="text-body-md font-body-md text-on-surface-variant italic mb-4">
                        "{explain.officer_rationale || explain.citizen_message_en || 'No narrative rationale recorded for this ticket.'}"
                      </p>
                      
                      {/* Action Buttons */}
                      <div className="flex flex-wrap gap-2 pt-3 border-t border-outline-variant/10">
                        <button 
                          onClick={() => handleSendMessage('whatsapp', explain.citizen_message_en || explain.officer_rationale)}
                          disabled={messageStatus.sending}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#25D366]/10 text-[#075E54] hover:bg-[#25D366]/20 border border-[#25D366]/30 rounded text-xs font-bold transition-colors disabled:opacity-50"
                        >
                          {messageStatus.sending && messageStatus.sentVia === 'whatsapp' ? (
                            <><span className="material-symbols-outlined text-[16px] animate-spin">sync</span> Sending...</>
                          ) : messageStatus.sentVia === 'whatsapp' ? (
                            <><span className="material-symbols-outlined text-[16px]">check_circle</span> Sent via WhatsApp</>
                          ) : (
                            <><span className="material-symbols-outlined text-[16px]">forum</span> Send via WhatsApp</>
                          )}
                        </button>
                        <button 
                          onClick={() => handleSendMessage('sms', explain.citizen_message_en || explain.officer_rationale)}
                          disabled={messageStatus.sending}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 text-primary hover:bg-primary/20 border border-primary/30 rounded text-xs font-bold transition-colors disabled:opacity-50"
                        >
                          {messageStatus.sending && messageStatus.sentVia === 'sms' ? (
                            <><span className="material-symbols-outlined text-[16px] animate-spin">sync</span> Sending...</>
                          ) : messageStatus.sentVia === 'sms' ? (
                            <><span className="material-symbols-outlined text-[16px]">check_circle</span> Sent via SMS</>
                          ) : (
                            <><span className="material-symbols-outlined text-[16px]">sms</span> Send via SMS</>
                          )}
                        </button>
                      </div>
                    </div>
                    <div className="flex-grow flex flex-col relative z-10">
                      <h4 className="text-label-sm font-label-sm text-on-surface font-semibold mb-4 border-b border-outline-variant/10 pb-2">Feature Impact (Criteria Attribution)</h4>
                      <div className="space-y-4 flex-grow flex flex-col justify-center">
                        {criteria.length === 0 ? (
                          <p className="text-body-md text-on-surface-variant">No attribution breakdown available.</p>
                        ) : criteria.map((c, idx) => {
                          const pct = Math.min(100, Math.round((Math.abs(c.contribution || 0) / maxAbs) * 100));
                          const positive = (c.contribution || 0) >= 0;
                          return (
                            <div key={c.criterion}>
                              <div className="flex justify-between text-label-sm font-label-sm mb-1">
                                <span className="text-on-surface-variant">{c.label || c.criterion}</span>
                                <span className={`font-bold ${positive ? 'text-primary' : 'text-error'}`}>
                                  {positive ? '+' : ''}{c.contribution?.toFixed(3)}
                                </span>
                              </div>
                              <div className="w-full bg-surface-container-highest rounded-full h-2 overflow-hidden">
                                <div className={`${barColors[idx % barColors.length]} h-2 rounded-full animate-bar`} style={{ '--target-width': `${pct}%`, width: `${pct}%` }}></div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <Link to="/explanations" className="mt-6 w-full border border-primary text-primary rounded-full py-2 px-4 font-label-sm text-label-sm font-bold hover:bg-primary/5 transition-colors text-center">
                        View Full Model Metrics
                      </Link>
                    </div>
                  </>
                ) : (
                  <p className="text-body-md text-on-surface-variant relative z-10">Select a ticket from the pool to see its AI priority explanation.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
