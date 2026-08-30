import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { staffAPI } from '../api/client';
import { categoryIcon, titleCase } from '../components/categoryIcon';

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
      {/* SideNavBar */}
      <nav className="bg-surface-container-low h-screen w-64 fixed left-0 top-0 border-r border-outline-variant/10 flex flex-col py-unit px-4 gap-2 z-40 hidden md:flex">
        <div className="mb-8 mt-4 px-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center overflow-hidden text-on-primary-container">
              <span className="material-symbols-outlined">location_city</span>
            </div>
            <div>
              <h1 className="font-headline-md text-headline-md text-primary">Kopargaon Civic</h1>
              <p className="font-label-sm text-label-sm text-on-surface-variant">Administrative Suite</p>
            </div>
          </div>
        </div>
        <div className="flex-1 flex flex-col gap-1">
          <Link className="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 transition-all duration-300 rounded-lg group" to="/admin">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">dashboard</span>
            <span className="font-label-sm text-label-sm">Dashboard</span>
          </Link>
          <Link className="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 transition-all duration-300 rounded-lg group" to="/ticket-pool">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">confirmation_number</span>
            <span className="font-label-sm text-label-sm">Ticket Pool</span>
          </Link>
          <Link className="flex items-center gap-3 px-4 py-3 bg-primary-container text-on-primary-container rounded-lg font-bold group" to="/staff-allocation">
            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>group_add</span>
            <span className="font-label-sm text-label-sm">Staff Allocation</span>
          </Link>
          <Link className="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 transition-all duration-300 rounded-lg group" to="/citizen-insights">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">analytics</span>
            <span className="font-label-sm text-label-sm">Citizen Insights</span>
          </Link>
          <Link className="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 transition-all duration-300 rounded-lg group" to="/compliance">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">terminal</span>
            <span className="font-label-sm text-label-sm">System Logs</span>
          </Link>
        </div>
        <div className="mt-auto border-t border-outline-variant/10 pt-4 flex flex-col gap-1">
          <Link className="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 transition-all duration-300 rounded-lg group" to="/explanations">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">help</span>
            <span className="font-label-sm text-label-sm">Support</span>
          </Link>
          <Link className="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 transition-all duration-300 rounded-lg group" to="/">
            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">logout</span>
            <span className="font-label-sm text-label-sm">Logout</span>
          </Link>
        </div>
      </nav>

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

              {/* Departments */}
              <div className="mb-8">
                <h3 className="font-headline-md text-headline-md text-on-surface mb-4">Team Manifests by Department</h3>
                <div className="flex flex-col gap-4">
                  {(plan.departments || []).map(dept => (
                    <DepartmentCard key={dept.department_id} dept={dept} onRecord={handleRecord} />
                  ))}
                  {(!plan.departments || plan.departments.length === 0) && (
                    <p className="text-on-surface-variant text-sm">No mapped departments for today's manifest.</p>
                  )}
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
