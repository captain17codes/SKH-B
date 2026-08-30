import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { triageAPI, mediaAPI } from '../api/client';
import { categoryIcon, titleCase as toTitleCase } from '../components/categoryIcon';
import TicketPhoto from '../components/TicketPhoto';

function relative(dateStr, isDeadline = false) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const abs = Math.abs(diff);
  const m = Math.floor(abs / 60000);
  const h = Math.floor(m / 60);
  const d = Math.floor(h / 24);
  
  let val = '';
  if (d > 0) val = `${d}d`;
  else if (h > 0) val = `${h}h`;
  else if (m > 0) val = `${m}m`;
  else val = 'just now';

  if (val === 'just now') return val;
  
  if (isDeadline && diff > 0) {
    return `overdue ${val}`;
  }
  return diff > 0 ? `${val} ago` : `${val} from now`;
}

const isPast = (dateStr) => new Date(dateStr).getTime() < Date.now();

export default function TicketPoolPage() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const [unscored, setUnscored] = useState(0);

  const [mediaIndex, setMediaIndex] = useState({});
  const [clusters, setClusters] = useState([]);

  const [selectedWard, setSelectedWard] = useState('All Wards');
  const [selectedCategory, setSelectedCategory] = useState('All Categories');
  const [selectedStatus, setSelectedStatus] = useState('All Statuses');

  const [assessingCluster, setAssessingCluster] = useState(null);
  const [assessingDetails, setAssessingDetails] = useState(null);
  const [assessingLoading, setAssessingLoading] = useState(false);
  const [unmergeLoading, setUnmergeLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const data = await triageAPI.getPriorities({ limit: 200 });
        if (!mounted) return;
        setTickets(data.tickets || []);
        setTotal(data.total || 0);
        setUnscored(data.unscored || 0);

        if (data.tickets && data.tickets.length > 0) {
          try {
            const ids = data.tickets.map(t => t.id);
            const index = await mediaAPI.index(ids);
            if (mounted) setMediaIndex(index.tickets || {});
          } catch (err) {
            console.error('Failed to load media index', err);
          }
        }
        
        try {
          const cl = await mediaAPI.clusters(20);
          if (mounted) setClusters(cl.clusters || []);
        } catch (err) {
          console.error('Failed to load clusters', err);
        }

      } catch (err) {
        if (mounted) setError(err.message || 'Failed to fetch tickets');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadData();
    return () => { mounted = false; };
  }, []);

  const distinctWards = [...new Set(tickets.map(t => t.ward_id).filter(Boolean))].sort();
  const distinctCategories = [...new Set(tickets.map(t => t.category).filter(Boolean))].sort();
  const distinctStatuses = [...new Set(tickets.map(t => t.status).filter(Boolean))].sort();

  const handleAssess = async (cluster) => {
    setAssessingCluster(cluster);
    setAssessingLoading(true);
    setAssessingDetails(null);
    try {
      const details = await mediaAPI.cluster(cluster.ticket_id);
      setAssessingDetails(details);
    } catch (err) {
      console.error(err);
      alert('Failed to load cluster details.');
    } finally {
      setAssessingLoading(false);
    }
  };

  const handleUnmerge = async (id) => {
    if (!window.confirm("Are you sure you want to unmerge this ticket? It will be treated as an independent report.")) return;
    setUnmergeLoading(true);
    try {
      await ticketsAPI.unmerge(id);
      setAssessingCluster(null);
      // reload basic data
      const data = await triageAPI.getPriorities({ limit: 200 });
      setTickets(data.tickets || []);
      setTotal(data.total || 0);
      setUnscored(data.unscored || 0);
      const cl = await mediaAPI.clusters(20);
      setClusters(cl.clusters || []);
    } catch (err) {
      alert("Failed to unmerge: " + err.message);
    } finally {
      setUnmergeLoading(false);
    }
  };

  const filteredTickets = tickets.filter(t => {
    if (selectedWard !== 'All Wards' && t.ward_id !== selectedWard) return false;
    if (selectedCategory !== 'All Categories' && t.category !== selectedCategory) return false;
    if (selectedStatus !== 'All Statuses' && t.status !== selectedStatus) return false;
    return true;
  });

  return (
    <>

<AdminSidebar />
{/* Main Content Area */}
<main className="flex-1 flex flex-col md:ml-64 relative overflow-y-auto w-full">
{/* Shared Component: TopNavBar */}
<header className="sticky top-0 z-50 flex justify-between items-center w-full px-margin-desktop h-16 bg-surface/80 dark:bg-surface-dim/80 backdrop-blur-xl bg-surface-container-low dark:bg-surface-container-highest shadow-sm">
<div className="flex items-center gap-4 w-full">
{/* Search Bar (on_left configuration) */}
<div className="relative w-full max-w-md hidden md:block">
<span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">search</span>
<input className="w-full bg-surface-container-lowest border border-outline-variant rounded-full py-2 pl-10 pr-4 font-body-md text-body-md text-on-surface focus:outline-none input-glow transition-all" placeholder="Search Civic Triage Engine..." type="text"/>
</div>
</div>
<div className="flex items-center gap-4">
<button className="p-2 text-on-surface-variant hover:bg-secondary-container dark:hover:bg-tertiary-container transition-colors rounded-full cursor-pointer active:scale-95 duration-200">
<span className="material-symbols-outlined">notifications</span>
</button>
<button className="p-2 text-on-surface-variant hover:bg-secondary-container dark:hover:bg-tertiary-container transition-colors rounded-full cursor-pointer active:scale-95 duration-200">
<span className="material-symbols-outlined">settings</span>
</button>
<div className="w-8 h-8 rounded-full bg-primary-container border border-outline-variant/30 flex items-center justify-center overflow-hidden ml-2 cursor-pointer active:scale-95 duration-200">
{/* Placeholder for Profile Image */}
<span className="material-symbols-outlined text-on-primary-container text-sm">person</span>
</div>
</div>
</header>
{/* Page Content Canvas */}
<div className="w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8 md:py-12 space-y-10">
{/* Header Section with Solid Surfaces */}
<section className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/20 shadow-sm">
<div>
<h1 className="font-headline-lg text-headline-lg-mobile md:text-headline-lg text-primary tracking-tight">Master Ticket Pool</h1>
<p className="font-body-md text-body-md text-on-surface-variant mt-2 max-w-2xl">
{loading ? 'Loading the live queue…' : `${total} open reports · ${unscored} awaiting a score · ${clusters.length} duplicate cluster(s)`}
</p>
</div>
{/* Filters */}
<div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
<div className="relative">
<select 
  value={selectedWard}
  onChange={e => setSelectedWard(e.target.value)}
  disabled={distinctWards.length === 0}
  className="appearance-none bg-surface border border-outline-variant/50 rounded-lg py-2 pl-4 pr-10 font-label-sm text-label-sm text-on-surface focus:outline-none input-glow cursor-pointer disabled:opacity-50">
  {distinctWards.length === 0 ? (
    <option>Ward data not entered</option>
  ) : (
    <>
      <option value="All Wards">All Wards</option>
      {distinctWards.map(w => <option key={w} value={w}>{w}</option>)}
    </>
  )}
</select>
<span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-outline text-sm">expand_more</span>
</div>
<div className="relative">
<select 
  value={selectedCategory}
  onChange={e => setSelectedCategory(e.target.value)}
  className="appearance-none bg-surface border border-outline-variant/50 rounded-lg py-2 pl-4 pr-10 font-label-sm text-label-sm text-on-surface focus:outline-none input-glow cursor-pointer">
  <option value="All Categories">All Categories</option>
  {distinctCategories.map(c => <option key={c} value={c}>{toTitleCase(c)}</option>)}
</select>
<span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-outline text-sm">expand_more</span>
</div>
<div className="relative">
<select 
  value={selectedStatus}
  onChange={e => setSelectedStatus(e.target.value)}
  className="appearance-none bg-surface border border-outline-variant/50 rounded-lg py-2 pl-4 pr-10 font-label-sm text-label-sm text-on-surface focus:outline-none input-glow cursor-pointer">
  <option value="All Statuses">All Statuses</option>
  {distinctStatuses.map(s => <option key={s} value={s}>{toTitleCase(s)}</option>)}
</select>
<span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-outline text-sm">expand_more</span>
</div>
</div>
</section>
{/* Recent pHash Clusters Section (Solid Surface) */}
<section>
<div className="flex items-center gap-2 mb-4">
<span className="material-symbols-outlined text-primary">hub</span>
<h2 className="font-headline-md text-headline-md text-on-surface">Recent pHash Clusters</h2>
</div>
{clusters.length === 0 ? (
  <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm p-6 flex justify-center items-center">
    <p className="font-body-md text-body-md text-on-surface-variant">No duplicate clusters detected in the current pool.</p>
  </div>
) : (
  <div className="space-y-4">
    {clusters.map(c => {
      const title = c.description ? (c.description.length > 70 ? c.description.slice(0, 70) + '...' : c.description) : toTitleCase(c.category);
      const isHighMultiplier = c.community_multiplier > 1.3;
      
      return (
        <div key={c.ticket_id} className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm p-4 hover:border-primary/30 transition-colors cursor-pointer group">
          <div className="flex flex-col md:flex-row gap-6 items-start">
            {/* Tile Container */}
            <TicketPhoto media={c.primary_media} category={c.category} className="w-full md:w-64 h-40 rounded-lg relative" />
            {/* Content */}
            <div className="flex-1 flex flex-col justify-between h-full space-y-4 py-1">
              <div>
                <div className="flex flex-wrap gap-2 mb-3">
                  <span className="bg-tertiary-fixed text-on-tertiary-fixed-variant px-2.5 py-1 rounded-full font-label-sm text-label-sm inline-flex items-center gap-1 border border-tertiary-fixed-dim/50">
                    <span className="material-symbols-outlined text-[14px]">merge</span>
                    Merged: {c.report_count} reports
                  </span>
                  {c.merge_bases?.map(basis => (
                    <span key={basis} className="bg-surface-container-high text-on-surface px-2.5 py-1 rounded-full font-label-sm text-label-sm border border-outline-variant/50">
                      {toTitleCase(basis)}
                    </span>
                  ))}
                  <span className={`px-2.5 py-1 rounded-full font-label-sm text-label-sm border ${isHighMultiplier ? 'bg-error-container text-on-error-container border-error-container/50' : 'bg-secondary-container text-on-secondary-container border-secondary-container/50'}`}>
                    Community Multiplier: {c.community_multiplier?.toFixed(2) ?? '—'}
                  </span>
                </div>
                <h3 className="font-headline-lg text-headline-lg-mobile md:text-headline-lg text-on-surface mb-2">{title}</h3>
                <p className="font-body-md text-body-md text-on-surface-variant flex items-center gap-1 mb-2">
                  <span className="material-symbols-outlined text-sm text-outline">location_on</span>
                  {c.ward_id ?? 'Ward unassigned'}{c.lat != null && c.lon != null ? ` · ${c.lat.toFixed(4)}, ${c.lon.toFixed(4)}` : ''}
                </p>
                {c.duplicate_media && c.duplicate_media.length > 0 && (
                  <div className="flex gap-2 mt-2">
                    {c.duplicate_media.map((dupMedia, idx) => (
                      <div key={dupMedia.id || idx} title={dupMedia.phash}>
                        <TicketPhoto 
                          media={dupMedia} 
                          category={c.category} 
                          className="w-12 h-12 rounded"
                          alt={dupMedia.phash ? `pHash: ${dupMedia.phash}` : 'Duplicate evidence'}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex justify-end mt-auto pt-4 border-t border-outline-variant/10">
                <button type="button" onClick={() => handleAssess(c)} className="bg-primary text-on-primary font-label-sm text-label-sm rounded-lg px-6 py-2.5 hover:bg-primary-container transition-colors shadow-sm flex items-center gap-2">
                  Assess Cluster <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    })}
  </div>
)}
</section>
{/* Data Table Section (Solid Surface) */}
<section className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm overflow-hidden">
{error ? (
  <div className="p-6 bg-error-container text-on-error-container font-body-md text-body-md">
    {error}
  </div>
) : (
  <div className="overflow-x-auto">
    <table className="w-full text-left border-collapse">
      <thead className="bg-surface-container-low/50 border-b border-outline-variant/20">
        <tr>
          <th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Evidence</th>
          <th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">ID</th>
          <th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Category</th>
          <th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Location</th>
          <th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Score</th>
          <th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Cost Status</th>
          <th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Deadline</th>
          <th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Action</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-outline-variant/10">
        {filteredTickets.map(t => (
          <tr key={t.id} className="hover:bg-surface-bright/50 transition-colors group">
            <td className="py-4 px-6">
              <TicketPhoto 
                media={mediaIndex?.[t.id]?.[0]} 
                category={t.category} 
                className="w-10 h-10 rounded-lg" 
              />
              {mediaIndex?.[t.id]?.[0] && mediaIndex[t.id][0].phash && (
                <div className="font-label-sm text-outline mt-1">{mediaIndex[t.id][0].phash.slice(0, 8)}</div>
              )}
            </td>
            <td className="py-4 px-6">
              <div className="font-body-md text-body-md text-on-surface font-medium">{t.ref_no ?? `#${t.id.slice(0, 8)}`}</div>
              <div className="font-label-sm text-label-sm text-outline mt-0.5">{t.scored && t.rank != null ? `Rank ${t.rank}` : 'Unranked'}</div>
            </td>
            <td className="py-4 px-6">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px] text-primary">{categoryIcon(t.category)}</span>
                <span className="font-body-md text-body-md text-on-surface">{toTitleCase(t.category)}</span>
              </div>
            </td>
            <td className="py-4 px-6">
              <div className="font-body-md text-body-md text-on-surface">{t.ward_id ?? 'Ward unassigned'}</div>
              <div className="font-label-sm text-label-sm text-outline mt-0.5">{t.reported_at ? `Reported ${relative(t.reported_at)}` : ''}</div>
            </td>
            <td className="py-4 px-6">
              {t.scored ? (
                <div className="flex flex-col gap-1">
                  <span className="font-body-md text-body-md text-on-surface">{t.cci_score?.toFixed(3)}</span>
                  <div className="w-24 h-1.5 rounded-full bg-surface-container-high overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: `${(t.cci_score * 100).toFixed(0)}%` }}></div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-[#9a6a16]">
                  <span className="material-symbols-outlined text-[20px]" style={{fontVariationSettings: "'FILL' 1"}}>warning</span>
                  <span className="font-label-sm text-label-sm">Not scored yet</span>
                </div>
              )}
            </td>
            <td className="py-4 px-6">
              {t.cost_status === 'COST_COMPLETE' ? (
                <div className="flex items-center gap-2 text-tertiary">
                  <span className="material-symbols-outlined text-[20px]" style={{fontVariationSettings: "'FILL' 1"}}>check_circle</span>
                  <span className="font-label-sm text-label-sm whitespace-nowrap">
                    INR {t.estimated_cost_inr?.toLocaleString('en-IN') ?? '—'} &middot; {t.estimated_hours ?? '—'}h
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-[#9a6a16]">
                  <span className="material-symbols-outlined text-[20px]" style={{fontVariationSettings: "'FILL' 1"}}>warning</span>
                  <span className="font-label-sm text-label-sm">Not costed yet</span>
                </div>
              )}
            </td>
            <td className="py-4 px-6">
              {t.rts_deadline_at != null ? (
                <span className={`px-2 py-1 rounded font-label-sm text-label-sm border whitespace-nowrap inline-block ${isPast(t.rts_deadline_at) ? 'bg-error-container text-error border-error/50' : 'bg-error-container text-on-error-container border-error-container/50'}`}>
                  RTS {relative(t.rts_deadline_at, true)}
                </span>
              ) : t.operational_deadline_at ? (
                <span className={`font-label-sm text-label-sm whitespace-nowrap inline-block ${isPast(t.operational_deadline_at) ? 'text-error' : 'text-on-surface-variant'}`}>
                  {relative(t.operational_deadline_at, true)}
                </span>
              ) : (
                <span className="font-label-sm text-label-sm text-on-surface-variant">—</span>
              )}
            </td>
            <td className="py-4 px-6">
              <button 
                disabled
                title="Staff assignment endpoint not built yet"
                className="border border-outline-variant text-outline font-label-sm text-label-sm rounded-lg px-4 py-2 opacity-50 cursor-not-allowed whitespace-nowrap">
                Assign Scout
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)}
</section>
</div>

{assessingCluster && (
  <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex justify-center items-center p-4">
    <div className="bg-surface-container-lowest border border-outline-variant/20 shadow-lg rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto flex flex-col">
      <div className="p-6 border-b border-outline-variant/20 flex justify-between items-center bg-surface-container-low sticky top-0 z-10">
        <div>
          <h2 className="text-headline-md font-headline-md text-on-surface">Assess Cluster</h2>
          <p className="text-label-sm text-on-surface-variant">Review duplicate merges and unmerge if incorrect.</p>
        </div>
        <button onClick={() => setAssessingCluster(null)} className="p-2 hover:bg-surface-variant rounded-full text-on-surface">
          <span className="material-symbols-outlined">close</span>
        </button>
      </div>
      <div className="p-6">
        {assessingLoading ? (
          <div className="text-center py-12 text-on-surface-variant">Loading cluster details...</div>
        ) : assessingDetails ? (
          <div className="space-y-6">
            <div className="bg-primary-container/10 border border-primary-container/30 rounded-lg p-4">
              <h3 className="font-semibold text-primary mb-2 flex items-center gap-2"><span className="material-symbols-outlined">flag</span> Parent Ticket</h3>
              {(() => {
                const parent = assessingDetails.members.find(m => m.role === 'parent');
                return parent && (
                  <div className="flex gap-4">
                    {parent.media?.[0] && (
                      <TicketPhoto media={parent.media[0]} category={parent.category} className="w-24 h-24 rounded-lg object-cover shrink-0" />
                    )}
                    <div>
                      <p className="font-bold">{parent.ref_no}</p>
                      <p className="text-sm text-on-surface-variant mb-1">{parent.description}</p>
                      <p className="text-xs text-outline">{parent.ward_id} &middot; {parent.lat}, {parent.lon}</p>
                    </div>
                  </div>
                );
              })()}
            </div>
            
            <h3 className="font-semibold text-on-surface mt-6 mb-4">Duplicate Reports ({assessingDetails.duplicate_count})</h3>
            <div className="space-y-4">
              {assessingDetails.members.filter(m => m.role === 'duplicate').map(dup => (
                <div key={dup.ticket_id} className="bg-surface border border-outline-variant/30 rounded-lg p-4 flex gap-4">
                  {dup.media?.[0] && (
                    <TicketPhoto media={dup.media[0]} category={dup.category} className="w-24 h-24 rounded-lg object-cover shrink-0" />
                  )}
                  <div className="flex-1">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-bold">{dup.ref_no}</p>
                        <p className="text-sm text-on-surface-variant mb-2">{dup.description}</p>
                        {dup.match && (
                          <div className="bg-surface-variant/30 rounded p-2 text-xs space-y-1">
                            <p><span className="font-semibold">Basis:</span> {toTitleCase(dup.match.basis)} ({dup.match.confidence} confidence)</p>
                            <p><span className="font-semibold">Reason:</span> {dup.match.reason}</p>
                          </div>
                        )}
                      </div>
                      <button 
                        onClick={() => handleUnmerge(dup.ticket_id)}
                        disabled={unmergeLoading}
                        className="bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-label-sm border border-outline-variant/50 px-4 py-2 rounded-lg transition-colors whitespace-nowrap ml-4">
                        {unmergeLoading ? 'Unmerging...' : 'Unmerge'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-error">Failed to load details.</div>
        )}
      </div>
    </div>
  </div>
)}

</main>

    </>
  );
}
