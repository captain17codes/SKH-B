import React, { useState, useEffect, useCallback } from 'react';
import AdminSidebar from '../components/AdminSidebar';
import { Link } from 'react-router-dom';
import { staffAPI } from '../api/client';
import { categoryIcon, titleCase } from '../components/categoryIcon';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icons in Leaflet when using Webpack/Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

function HeadcountBadge({ status, headcount }) {
  if (status === 'operator_entered_not_yet_verified') {
    return (
      <span className="px-2 py-1 bg-tertiary-fixed text-on-tertiary-fixed-variant rounded text-xs font-semibold">
        {headcount} on shift · unverified
      </span>
    );
  }
  return (
    <span className="px-2 py-1 bg-surface-container-high text-on-surface-variant rounded text-xs font-semibold">
      Headcount not entered
    </span>
  );
}

function DepartmentCard({ dept, onRecord }) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (value === '' || Number(value) < 0) return;
    setSaving(true);
    try {
      await onRecord(dept.department_id, Number(value), note || undefined);
      setValue('');
      setNote('');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-surface rounded-xl shadow-sm border border-outline-variant/20 overflow-hidden">
      <div className="p-4 flex justify-between items-center cursor-pointer hover:bg-surface-container-low transition-colors" onClick={() => setOpen(!open)}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-primary shrink-0">
            <span className="material-symbols-outlined">{categoryIcon(dept.categories?.[0])}</span>
          </div>
          <div>
            <h4 className="font-label-sm text-label-sm text-on-surface font-bold">{dept.department_name}</h4>
            <p className="text-sm text-on-surface-variant">{dept.ticket_count} ticket(s) · {dept.total_hours}h{dept.hours_unknown_for ? ` (${dept.hours_unknown_for} uncosted, excluded)` : ''}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <HeadcountBadge status={dept.headcount_status} headcount={dept.headcount} />
          <span className={`material-symbols-outlined text-outline transition-transform ${open ? 'rotate-180' : ''}`}>expand_more</span>
        </div>
      </div>

      {open && (
        <div className="p-4 bg-surface-container-lowest border-t border-outline-variant/10 flex flex-col gap-3">
          {dept.total_cost_inr != null && (
            <p className="text-sm text-on-surface-variant">Estimated cost: <span className="font-semibold text-on-surface">₹{dept.total_cost_inr.toLocaleString('en-IN')}</span></p>
          )}
          <div className="space-y-2">
            {(dept.tickets || []).slice(0, 6).map(t => (
              <div key={t.ticket_id} className="flex items-start gap-3 p-3 rounded-lg border border-outline-variant/10 hover:border-primary/30 transition-colors">
                <span className="material-symbols-outlined text-tertiary mt-0.5">{categoryIcon(t.category)}</span>
                <div className="flex-1">
                  <p className="font-body-md text-body-md text-on-surface font-semibold">{t.ref_no} · {titleCase(t.category)}</p>
                  <p className="text-sm text-on-surface-variant">Rank {t.rank_position} · {t.hours_estimate != null ? `${t.hours_estimate}h` : 'hours unknown'} {t.cost_inr != null ? `· ₹${t.cost_inr.toLocaleString('en-IN')}` : ''}</p>
                </div>
                <span className="px-2 py-1 bg-tertiary-fixed text-on-tertiary-fixed rounded-full text-xs shrink-0">{t.cost_status === 'COST_COMPLETE' ? 'Costed' : 'Uncosted'}</span>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-end gap-2 pt-3 border-t border-outline-variant/10">
            <div>
              <label className="block text-xs text-on-surface-variant mb-1">Record headcount</label>
              <input type="number" min="0" value={value} onChange={e => setValue(e.target.value)} className="w-24 px-3 py-1.5 bg-surface border border-outline-variant/40 rounded-lg text-sm focus:outline-none focus:border-primary" placeholder="e.g. 6" />
            </div>
            <div className="flex-1 min-w-[140px]">
              <label className="block text-xs text-on-surface-variant mb-1">Note (optional)</label>
              <input type="text" value={note} onChange={e => setNote(e.target.value)} className="w-full px-3 py-1.5 bg-surface border border-outline-variant/40 rounded-lg text-sm focus:outline-none focus:border-primary" placeholder="morning shift" />
            </div>
            <button onClick={submit} disabled={saving || value === ''} className="px-4 py-1.5 bg-primary text-on-primary rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50">
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function StaffAllocationPage() {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await staffAPI.plan();
      setPlan(res);
    } catch (err) {
      setError(err.message || 'Failed to load staff plan');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleRecord = async (departmentId, headcount, note) => {
    await staffAPI.setHeadcount(departmentId, headcount, note);
    await load();
  };

  const wCap = plan?.workforce_cap_hours;
  const wUsed = plan?.workforce_used_hours;
  const wPct = wCap ? Math.round((wUsed / wCap) * 100) : null;

  return (
    <>
      <AdminSidebar />

      {/* Main Content Area */}
      <div className="flex-1 ml-0 md:ml-64 flex flex-col min-h-screen">
        <header className="sticky top-0 z-50 flex justify-between items-center w-full px-margin-mobile md:px-margin-desktop h-16 bg-surface/80 backdrop-blur-xl shadow-sm">
          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center bg-surface-container-high rounded-full px-4 py-2">
              <span className="material-symbols-outlined text-on-surface-variant mr-2">search</span>
              <input className="bg-transparent border-none focus:ring-0 text-body-md font-body-md text-on-surface w-64 placeholder:text-outline" placeholder="Search departments..." type="text" />
            </div>
          </div>
          <button onClick={load} className="p-2 text-on-surface-variant hover:bg-secondary-container transition-colors rounded-full cursor-pointer">
            <span className="material-symbols-outlined">refresh</span>
          </button>
        </header>

        <main className="flex-1 p-margin-mobile md:p-margin-desktop pb-24 md:pb-margin-desktop">
          <div className="mb-6">
            <h2 className="font-headline-lg-mobile md:font-headline-lg text-headline-lg-mobile md:text-headline-lg text-on-surface mb-2">Staff Allocation Overview</h2>
            <p className="font-body-md text-body-md text-on-surface-variant">
              {plan?.message || 'Manage municipal teams and monitor daily resource utilization.'}
            </p>
          </div>

          {loading ? (
            <div className="animate-pulse space-y-6">
              <div className="h-24 bg-surface-container rounded-xl" />
              <div className="h-64 bg-surface-container rounded-xl" />
            </div>
          ) : error ? (
            <div className="bg-error-container text-on-error-container p-6 rounded-xl font-semibold">{error}</div>
          ) : !plan?.manifest_found ? (
            <div className="bg-surface-container-lowest p-8 rounded-xl border border-outline-variant/20 shadow-sm text-center">
              <h3 className="text-xl font-semibold mb-2 text-on-surface">No dispatch manifest for {plan?.dispatch_date}.</h3>
              <p className="text-on-surface-variant">Run daily allocation first, then staffing will populate here automatically.</p>
              <Link to="/allocation" className="inline-block mt-4 px-5 py-2 bg-primary text-on-primary rounded-full text-sm font-semibold hover:opacity-90">Go to Daily Allocation</Link>
            </div>
          ) : (
            <>
              {plan.headcount_caveat && (
                <div className="bg-[#fff3e0] text-[#9a6a16] border border-[#ffcc80] p-3 rounded-lg mb-6 text-sm flex items-start gap-2">
                  <span className="material-symbols-outlined text-[18px] mt-0.5">info</span>
                  {plan.headcount_caveat}
                </div>
              )}

              {/* Top Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="glass-panel rounded-xl p-6 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-2 bg-primary-container/20 rounded-lg text-primary"><span className="material-symbols-outlined">assignment_turned_in</span></div>
                    <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Scheduled Tickets</h3>
                  </div>
                  <span className="font-headline-md text-headline-md text-primary">{plan.scheduled_tickets}</span>
                </div>
                <div className="glass-panel rounded-xl p-6 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-2 bg-primary-container/20 rounded-lg text-primary"><span className="material-symbols-outlined">schedule</span></div>
                    <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Total Hours</h3>
                  </div>
                  <span className="font-headline-md text-headline-md text-primary">{plan.total_hours}h</span>
                </div>
                <div className="glass-panel rounded-xl p-6 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-2 bg-primary-container/20 rounded-lg text-primary"><span className="material-symbols-outlined">account_balance_wallet</span></div>
                    <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Workforce Capacity</h3>
                  </div>
                  {wCap ? (
                    <>
                      <span className="font-headline-md text-headline-md text-primary">{wPct}%</span>
                      <div className="w-full bg-surface-container-high rounded-full h-2 overflow-hidden mt-2">
                        <div className="bg-primary h-2 rounded-full" style={{ width: `${wPct}%` }}></div>
                      </div>
                      <p className="text-xs text-on-surface-variant mt-1">{wUsed}h / {wCap}h capacity</p>
                    </>
                  ) : (
                    <span className="text-sm text-on-surface-variant">no capacity recorded</span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                {/* Left Column: Departments */}
                <div>
                  <h3 className="font-headline-md text-headline-md text-on-surface mb-4">Team Manifests</h3>
                  <div className="flex flex-col gap-4">
                    {(plan.departments || []).map(dept => (
                      <DepartmentCard key={dept.department_id} dept={dept} onRecord={handleRecord} />
                    ))}
                    {(!plan.departments || plan.departments.length === 0) && (
                      <p className="text-on-surface-variant text-sm">No mapped departments for today's manifest.</p>
                    )}
                  </div>
                </div>

                {/* Right Column: Live Deployment Map & Timeline */}
                <div className="flex flex-col gap-6">
                  <div>
                    <h3 className="font-headline-md text-headline-md text-on-surface mb-4">Live Deployment</h3>
                    <div className="bg-surface rounded-xl shadow-sm border border-outline-variant/20 overflow-hidden h-[300px] z-0">
                      <MapContainer center={[19.8850, 74.4750]} zoom={13} scrollWheelZoom={false} className="w-full h-full z-0" style={{ zIndex: 0 }}>
                        <TileLayer
                          attribution='&copy; OpenStreetMap'
                          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />
                        {(plan.departments || []).flatMap(d => d.tickets || []).slice(0, 10).map((t, idx) => {
                           // Mock lat/lon around Kopargaon for demo if missing
                           const lat = t.lat || (19.8850 + (Math.random() - 0.5) * 0.05);
                           const lon = t.lon || (74.4750 + (Math.random() - 0.5) * 0.05);
                           return (
                             <Marker key={idx} position={[lat, lon]}>
                               <Popup>
                                 <span className="font-bold">{t.ref_no}</span><br />
                                 {titleCase(t.category)}<br/>
                                 Rank: {t.rank_position}
                               </Popup>
                             </Marker>
                           );
                        })}
                      </MapContainer>
                    </div>
                  </div>

                  <div className="bg-surface rounded-xl shadow-sm border border-outline-variant/20 p-6">
                     <h4 className="font-label-sm text-label-sm text-on-surface mb-6 font-semibold">Scheduled Tasks Timeline</h4>
                     <div className="relative">
                       <div className="absolute top-1.5 left-0 w-full h-0.5 bg-outline-variant/30"></div>
                       <div className="relative flex justify-between z-10">
                         <div className="flex flex-col items-center">
                           <div className="w-3.5 h-3.5 bg-primary rounded-full mb-2 shadow-sm"></div>
                           <span className="text-[10px] text-on-surface-variant font-semibold">08:00</span>
                         </div>
                         <div className="flex flex-col items-center">
                           <div className="w-3.5 h-3.5 bg-primary rounded-full mb-2 shadow-sm"></div>
                           <span className="text-[10px] text-on-surface-variant font-semibold">10:30</span>
                         </div>
                         <div className="flex flex-col items-center">
                           <div className="w-3.5 h-3.5 border-2 border-primary bg-surface rounded-full mb-2 shadow-sm"></div>
                           <span className="text-[10px] text-on-surface-variant font-bold text-primary">13:00</span>
                         </div>
                         <div className="flex flex-col items-center">
                           <div className="w-3.5 h-3.5 bg-outline-variant/50 rounded-full mb-2"></div>
                           <span className="text-[10px] text-on-surface-variant font-semibold">16:00</span>
                         </div>
                       </div>
                     </div>
                  </div>
                </div>
              </div>

              {/* Unmapped */}
              {(plan.unmapped || []).length > 0 && (
                <div>
                  <h3 className="font-headline-md text-headline-md text-on-surface mb-2 flex items-center gap-2">
                    <span className="material-symbols-outlined text-[#9a6a16]">warning</span> Unmapped Categories
                  </h3>
                  <p className="text-sm text-on-surface-variant mb-4">These categories have no confirmed row in the department-capability matrix; the department shown, if any, is a guess.</p>
                  <div className="flex flex-col gap-3">
                    {plan.unmapped.map(u => (
                      <div key={u.category} className="bg-surface rounded-xl border border-outline-variant/20 p-4 flex flex-col md:flex-row md:items-center gap-2 md:gap-6">
                        <div className="flex items-center gap-2 min-w-[220px]">
                          <span className="material-symbols-outlined text-[#9a6a16]">{categoryIcon(u.category)}</span>
                          <span className="font-semibold text-on-surface">{titleCase(u.category)}</span>
                        </div>
                        <p className="text-sm text-on-surface-variant flex-1">{u.reason}{u.department_id_from_manifest ? ` — manifest guessed ${u.department_id_from_manifest}` : ''}</p>
                        <span className="text-sm text-on-surface font-mono">{u.ticket_count} ticket(s) · {u.total_hours}h</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </>
  );
}
