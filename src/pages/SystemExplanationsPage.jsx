import React from 'react';

export default function SystemExplanationsPage() {
  return (
    <div className="bg-background text-on-surface font-body-md antialiased overflow-x-hidden selection:bg-primary-fixed selection:text-on-primary-fixed">
      {/* Top Nav (Desktop) */}
      <nav className="hidden md:flex w-full fixed top-0 z-40 bg-surface-container-lowest/80 backdrop-blur-xl border-b border-outline-variant justify-between items-center px-margin-desktop py-4 ml-64" style={{width: 'calc(100% - 256px)'}}>
        <div className="flex items-center"><span className="font-headline-md text-headline-md font-extrabold text-primary">Kopargaon Civic Resource</span></div>
        <div className="flex items-center gap-gutter">
          <div className="relative hidden lg:block">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">search</span>
            <input className="pl-10 pr-4 py-2 bg-surface-container-lowest border border-outline-variant rounded-full text-body-md text-on-surface focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-fixed transition-all w-64" placeholder="Search resources..." type="text" />
          </div>
          <button className="p-2 text-on-surface-variant hover:text-primary transition-colors rounded-full hover:bg-surface-container"><span className="material-symbols-outlined">notifications</span></button>
          <button className="p-2 text-on-surface-variant hover:text-primary transition-colors rounded-full hover:bg-surface-container"><span className="material-symbols-outlined">settings</span></button>
          <div className="h-10 w-10 rounded-full overflow-hidden border border-outline-variant">
            <img alt="Admin" className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDGsJ7eOT3dUIwzCSnL7UF-XCQigxvmw4pq2rXkZZ_nfNl9rn426tbNLrZKFgQ5LedN1qlwkBdQI8w4YkdCCfpw9JKSZB3jodNXLKhTzcR3L2Jytjy1qevo9A_7S1h1kIEW9tBbRb1pqTahTvuhyW7j8dhoWb0kKifqNdeDgrCH2J5N8HOZRAHeSnjt0mloCilYN0fFPeIDWFfcUdZrJ2Ydv3KOWTCKa7a5LihwsukQyFZXLEuccOw" />
          </div>
        </div>
      </nav>

      {/* Side Navigation */}
      <aside className="hidden md:flex h-screen w-64 fixed left-0 top-0 bg-primary z-50 flex-col py-unit px-gutter">
        <div className="flex items-center gap-4 py-6 px-2">
          <div className="h-12 w-12 rounded-full overflow-hidden bg-surface-container-lowest p-1 flex items-center justify-center">
            <span className="material-symbols-outlined text-primary text-[32px]">assured_workload</span>
          </div>
          <div>
            <h1 className="font-headline-md text-headline-md font-bold text-on-primary text-[20px] leading-tight">KMC Portal</h1>
            <p className="font-body-md text-body-md text-primary-fixed-dim text-[14px]">Civic Resource Suite</p>
          </div>
        </div>
        <button className="mt-4 mb-8 bg-surface-container-lowest text-primary font-label-sm text-label-sm py-3 px-6 rounded-full flex items-center justify-center gap-2 hover:bg-secondary-fixed transition-colors shadow-sm w-full font-bold">
          <span className="material-symbols-outlined">add</span> New Ticket
        </button>
        <nav className="flex flex-col gap-2 flex-grow">
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-primary-fixed-dim hover:text-on-primary hover:bg-primary-container/10 transition-colors duration-200" href="#"><span className="material-symbols-outlined">assignment</span><span className="font-label-sm text-label-sm font-semibold">Ticket Pool</span></a>
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-primary-fixed-dim hover:text-on-primary hover:bg-primary-container/10 transition-colors duration-200" href="#"><span className="material-symbols-outlined">priority_high</span><span className="font-label-sm text-label-sm font-semibold">Prioritization</span></a>
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-primary-fixed-dim hover:text-on-primary hover:bg-primary-container/10 transition-colors duration-200" href="#"><span className="material-symbols-outlined">schedule</span><span className="font-label-sm text-label-sm font-semibold">Daily Allocation</span></a>
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-primary bg-primary-container/20 font-bold border-l-4 border-tertiary-fixed opacity-90 transition-all" href="#">
            <span className="material-symbols-outlined text-tertiary-fixed" style={{fontVariationSettings: "'FILL' 1"}}>info</span>
            <span className="font-label-sm text-label-sm">System Explanations</span>
          </a>
        </nav>
        <div className="mt-auto py-4 px-2"><div className="text-primary-fixed-dim text-xs opacity-60 font-label-sm text-label-sm">Powered by KMC Platform</div></div>
      </aside>

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

        {/* Bento Grid */}
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
              {[
                {label: 'Public Safety', value: '42%', width: '42%', color: 'bg-tertiary-fixed', labelColor: 'text-tertiary-fixed'},
                {label: 'Infrastructural Criticality', value: '28%', width: '28%', color: 'bg-primary-fixed-dim', labelColor: 'text-primary-fixed-dim'},
                {label: 'Socio-Spatial Equity', value: '18%', width: '18%', color: 'bg-secondary-fixed-dim', labelColor: 'text-secondary-fixed-dim'},
                {label: 'Resource Requirement', value: '12%', width: '12%', color: 'bg-surface-variant', labelColor: 'text-surface-variant'},
              ].map(w => (
                <div key={w.label}>
                  <div className="flex justify-between text-label-sm font-label-sm mb-2"><span className="text-on-primary">{w.label}</span><span className={`${w.labelColor} font-bold`}>{w.value}</span></div>
                  <div className="w-full bg-primary-container h-2 rounded-full overflow-hidden"><div className={`${w.color} h-full rounded-full`} style={{width: w.width}}></div></div>
                </div>
              ))}
            </div>
          </section>

          {/* SHAP Section */}
          <section className="lg:col-span-12 bg-surface-container-lowest rounded-xl border border-outline/10 p-6 md:p-8 flex flex-col gap-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-outline-variant pb-4">
              <div>
                <h2 className="font-headline-lg text-headline-lg text-primary flex items-center gap-2"><span className="material-symbols-outlined text-primary-container">model_training</span> AI Decision Justification (SHAP)</h2>
                <p className="font-body-md text-body-md text-on-surface-variant mt-1">Analyzing feature contributions for specific allocations.</p>
              </div>
              <div className="flex items-center gap-2 bg-surface-container-low px-4 py-2 rounded-lg border border-outline-variant">
                <span className="font-label-sm text-label-sm text-on-surface-variant">Selected Ticket:</span>
                <span className="font-headline-md text-[16px] font-bold text-primary">#TCK-1042 (Pothole, Main St)</span>
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 pt-2">
              <div className="lg:col-span-2 flex flex-col gap-4">
                <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Feature Impact on Priority Score</h3>
                <div className="relative h-64 border-l border-b border-outline-variant flex flex-col justify-between py-4 pl-4">
                  <div className="absolute inset-0 flex flex-col justify-between pointer-events-none pl-4 py-4 z-0">
                    {[...Array(5)].map((_, i) => <div key={i} className="w-full border-t border-outline-variant/30 h-0"></div>)}
                  </div>
                  <div className="absolute top-0 bottom-0 left-1/2 border-l-2 border-dashed border-outline-variant/50 z-0"></div>
                  {/* Bar 1 */}
                  <div className="relative z-10 flex items-center w-full group">
                    <div className="w-1/2 flex justify-end pr-4 text-right"><span className="font-body-md text-[13px] text-on-surface">Arterial Route (High Traffic)</span></div>
                    <div className="w-1/2 flex items-center"><div className="bg-primary-container h-6 rounded-r-sm transition-all duration-300 group-hover:bg-primary" style={{width: '65%'}}></div><span className="ml-2 font-label-sm text-label-sm text-primary font-bold">+0.32</span></div>
                  </div>
                  {/* Bar 2 */}
                  <div className="relative z-10 flex items-center w-full group">
                    <div className="w-1/2 flex justify-end pr-4 text-right"><span className="font-body-md text-[13px] text-on-surface">Time in Queue (48hrs)</span></div>
                    <div className="w-1/2 flex items-center"><div className="bg-primary-container/80 h-6 rounded-r-sm transition-all duration-300 group-hover:bg-primary" style={{width: '45%'}}></div><span className="ml-2 font-label-sm text-label-sm text-primary font-bold">+0.21</span></div>
                  </div>
                  {/* Bar 3 (negative) */}
                  <div className="relative z-10 flex items-center w-full group">
                    <div className="w-1/2 flex justify-end pr-4 text-right items-center"><span className="mr-2 font-label-sm text-label-sm text-error font-bold">-0.15</span><div className="bg-secondary h-6 rounded-l-sm transition-all duration-300 group-hover:bg-on-surface-variant" style={{width: '35%'}}></div></div>
                    <div className="w-1/2 pl-4"><span className="font-body-md text-[13px] text-on-surface">Clear Weather (No immediate degradation risk)</span></div>
                  </div>
                  {/* Bar 4 */}
                  <div className="relative z-10 flex items-center w-full group">
                    <div className="w-1/2 flex justify-end pr-4 text-right"><span className="font-body-md text-[13px] text-on-surface">School Zone Proximity</span></div>
                    <div className="w-1/2 flex items-center"><div className="bg-primary-container/60 h-6 rounded-r-sm transition-all duration-300 group-hover:bg-primary" style={{width: '25%'}}></div><span className="ml-2 font-label-sm text-label-sm text-primary font-bold">+0.12</span></div>
                  </div>
                </div>
                <div className="flex justify-between px-4 mt-1">
                  <span className="font-label-sm text-[11px] text-on-surface-variant">Negative Impact</span>
                  <span className="font-label-sm text-[11px] text-on-surface-variant">Baseline Score</span>
                  <span className="font-label-sm text-[11px] text-on-surface-variant">Positive Impact</span>
                </div>
              </div>
              {/* NLP Justification */}
              <div className="bg-surface-bright rounded-lg p-6 border border-outline-variant h-full flex flex-col">
                <div className="flex items-center gap-2 mb-4"><span className="material-symbols-outlined text-primary">chat_bubble</span><h3 className="font-label-sm text-label-sm font-bold text-primary">Natural Language Synthesis</h3></div>
                <p className="font-body-md text-body-md text-on-surface-variant italic mb-4">
                  "Ticket #TCK-1042 was elevated to <strong>Priority Rank 2</strong> today primarily due to its location on a major arterial route (High Traffic Volume), which heavily impacts public safety and transit efficiency. The fact that it has been in the queue for 48 hours further increased its priority score. Although current clear weather conditions reduced the urgency slightly (as immediate degradation is unlikely), its proximity to a school zone provided a final positive bump, securing its spot for today's resource allocation."
                </p>
                <div className="mt-auto">
                  <div className="inline-flex items-center gap-2 bg-tertiary-fixed/30 text-primary-container px-3 py-1 rounded-full text-xs font-label-sm border border-tertiary-fixed">
                    <span className="material-symbols-outlined text-[14px]">check_circle</span> High Confidence Score (0.92)
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Governance Table */}
          <section className="lg:col-span-12 bg-surface-container-lowest rounded-xl border border-outline/10 p-6">
            <div className="flex items-center gap-2 mb-6"><span className="material-symbols-outlined text-secondary">gavel</span><h2 className="font-headline-md text-headline-md text-primary">Governance &amp; Defense Architecture</h2></div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-outline-variant bg-surface-container-low">
                    <th className="py-3 px-4 font-label-sm text-label-sm text-on-surface-variant font-bold">Timestamp</th>
                    <th className="py-3 px-4 font-label-sm text-label-sm text-on-surface-variant font-bold">Event Type</th>
                    <th className="py-3 px-4 font-label-sm text-label-sm text-on-surface-variant font-bold">Action/Log</th>
                    <th className="py-3 px-4 font-label-sm text-label-sm text-on-surface-variant font-bold">Status</th>
                  </tr>
                </thead>
                <tbody className="font-body-md text-body-md text-on-surface">
                  <tr className="border-b border-outline-variant hover:bg-surface-bright transition-colors">
                    <td className="py-3 px-4 text-[14px] text-secondary">2023-10-24 08:00:12</td>
                    <td className="py-3 px-4"><span className="inline-flex items-center gap-1 bg-surface-container py-1 px-2 rounded text-xs font-label-sm"><span className="material-symbols-outlined text-[14px]">sync</span> AHP Recalibration</span></td>
                    <td className="py-3 px-4 text-[14px]">Daily matrix update based on weather forecast input (Monsoon mode off).</td>
                    <td className="py-3 px-4"><span className="text-primary font-bold text-xs">VERIFIED</span></td>
                  </tr>
                  <tr className="border-b border-outline-variant hover:bg-surface-bright transition-colors">
                    <td className="py-3 px-4 text-[14px] text-secondary">2023-10-24 07:45:00</td>
                    <td className="py-3 px-4"><span className="inline-flex items-center gap-1 bg-surface-container py-1 px-2 rounded text-xs font-label-sm"><span className="material-symbols-outlined text-[14px]">policy</span> RTS Defense</span></td>
                    <td className="py-3 px-4 text-[14px]">Blocked manual override attempt for Ticket #TCK-0982 (Insufficient justification provided by user: Admin_02).</td>
                    <td className="py-3 px-4"><span className="text-error font-bold text-xs">ENFORCED</span></td>
                  </tr>
                  <tr className="hover:bg-surface-bright transition-colors">
                    <td className="py-3 px-4 text-[14px] text-secondary">2023-10-24 06:30:00</td>
                    <td className="py-3 px-4"><span className="inline-flex items-center gap-1 bg-surface-container py-1 px-2 rounded text-xs font-label-sm"><span className="material-symbols-outlined text-[14px]">data_check</span> Knapsack Run</span></td>
                    <td className="py-3 px-4 text-[14px]">Optimal allocation completed. 42 tickets scheduled within 98% of daily budget constraint.</td>
                    <td className="py-3 px-4"><span className="text-primary font-bold text-xs">SUCCESS</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
