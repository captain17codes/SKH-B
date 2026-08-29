import React from 'react';

export default function AllocationDashboardPage() {
  return (
    <div className="bg-background text-on-background font-body-md min-h-screen flex">
      {/* SideNavBar */}
      <nav className="hidden lg:flex flex-col w-64 h-screen fixed left-0 top-0 py-8 px-4 bg-surface-container-low shadow-md z-40 border-r border-outline-variant/20">
        <div className="flex items-center gap-3 mb-8 px-2">
          <span className="material-symbols-outlined text-primary text-3xl icon-filled">account_balance</span>
          <div>
            <h2 className="text-headline-md font-headline-md font-bold text-primary">Admin Panel</h2>
            <p className="text-label-sm font-label-sm text-on-surface-variant">Kopargaon Digital</p>
          </div>
        </div>
        <button className="bg-primary text-on-primary w-full py-3 rounded-lg font-bold mb-8 hover:opacity-90 transition-opacity flex items-center justify-center gap-2 shadow-sm">
          <span className="material-symbols-outlined text-[20px]">add</span> New Request
        </button>
        <div className="flex flex-col gap-2 flex-grow">
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors" href="#"><span className="material-symbols-outlined">assignment</span><span className="text-label-sm font-label-sm">Ticket Pool</span></a>
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors" href="#"><span className="material-symbols-outlined">leaderboard</span><span className="text-label-sm font-label-sm">Prioritization</span></a>
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg bg-primary-container text-on-primary-container font-bold shadow-sm" href="#"><span className="material-symbols-outlined icon-filled">event_note</span><span className="text-label-sm font-label-sm">Daily Allocation</span></a>
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors" href="#"><span className="material-symbols-outlined">psychology</span><span className="text-label-sm font-label-sm">System Explanations</span></a>
        </div>
        <div className="flex flex-col gap-2 mt-auto border-t border-outline-variant/20 pt-4">
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors" href="#"><span className="material-symbols-outlined">analytics</span><span className="text-label-sm font-label-sm">System Status</span></a>
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors" href="#"><span className="material-symbols-outlined">logout</span><span className="text-label-sm font-label-sm">Logout</span></a>
        </div>
      </nav>

      {/* Main Content */}
      <div className="flex-1 lg:ml-64 flex flex-col min-h-screen relative">
        <header className="lg:hidden bg-surface-container-low shadow-sm sticky top-0 z-50 px-4 py-4 flex justify-between items-center border-b border-outline-variant/20">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-2xl icon-filled">account_balance</span>
            <span className="text-headline-lg-mobile font-headline-lg-mobile text-primary">Kopargaon Civic</span>
          </div>
          <button className="text-on-surface"><span className="material-symbols-outlined text-2xl">menu</span></button>
        </header>

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

          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/20 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10"><span className="material-symbols-outlined text-6xl text-primary">star_rate</span></div>
              <p className="text-label-sm font-label-sm text-on-surface-variant mb-1 uppercase tracking-wider">Total Priority Score</p>
              <p className="text-headline-display font-headline-display text-primary">1,420</p>
              <p className="text-sm text-on-surface-variant mt-2 flex items-center gap-1">
                <span className="material-symbols-outlined text-[16px] text-[#2e7d32]">trending_up</span>
                <span className="text-[#2e7d32] font-semibold">+12%</span> vs yesterday
              </p>
            </div>
            <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/20 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10"><span className="material-symbols-outlined text-6xl text-primary">account_balance_wallet</span></div>
              <p className="text-label-sm font-label-sm text-on-surface-variant mb-1 uppercase tracking-wider">Budget Utilization</p>
              <div className="flex items-end gap-2 mb-2"><p className="text-headline-display font-headline-display text-primary">85<span className="text-headline-md">%</span></p></div>
              <div className="w-full bg-surface-container-high rounded-full h-2"><div className="bg-primary h-2 rounded-full" style={{width: '85%'}}></div></div>
              <p className="text-sm text-on-surface-variant mt-2">₹1.2M / ₹1.5M Allocated</p>
            </div>
            <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/20 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10"><span className="material-symbols-outlined text-6xl text-primary">group</span></div>
              <p className="text-label-sm font-label-sm text-on-surface-variant mb-1 uppercase tracking-wider">Workforce Hours</p>
              <div className="flex items-end gap-2 mb-2"><p className="text-headline-display font-headline-display text-primary">92<span className="text-headline-md">%</span></p></div>
              <div className="w-full bg-surface-container-high rounded-full h-2"><div className="bg-[#d32f2f] h-2 rounded-full" style={{width: '92%'}}></div></div>
              <p className="text-sm text-on-surface-variant mt-2">320 hrs / 348 hrs Capacity (Near Max)</p>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
            {/* Main Table */}
            <div className="xl:col-span-2">
              <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm overflow-hidden">
                <div className="p-6 border-b border-outline-variant/20 flex justify-between items-center bg-surface-container-low">
                  <h3 className="text-headline-md font-headline-md text-on-surface">Allocated Tickets</h3>
                  <button className="text-primary text-sm font-semibold flex items-center gap-1 hover:underline">Export CSV <span className="material-symbols-outlined text-[18px]">download</span></button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-surface border-b border-outline-variant/20">
                        <th className="p-4 text-label-sm font-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Issue ID / Desc</th>
                        <th className="p-4 text-label-sm font-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Ward</th>
                        <th className="p-4 text-label-sm font-label-sm text-on-surface-variant uppercase tracking-wider font-semibold text-center">TOPSIS Score</th>
                        <th className="p-4 text-label-sm font-label-sm text-on-surface-variant uppercase tracking-wider font-semibold text-right">Est. Hours</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant/10">
                      <tr className="hover:bg-surface-container-low/50 transition-colors">
                        <td className="p-4"><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-full bg-error-container/30 flex items-center justify-center text-[#d32f2f]"><span className="material-symbols-outlined text-[20px]">warning</span></div><div><p className="font-semibold text-on-surface">#TCK-892</p><p className="text-sm text-on-surface-variant truncate max-w-[200px]">Severe potholes on Godavari Bridge approach</p></div></div></td>
                        <td className="p-4 text-on-surface">Ward 2 (Central)</td>
                        <td className="p-4 text-center"><span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#e8f5e9] text-[#2e7d32] border border-[#a5d6a7]">0.92</span></td>
                        <td className="p-4 text-right text-on-surface font-mono">18 hrs</td>
                      </tr>
                      <tr className="hover:bg-surface-container-low/50 transition-colors">
                        <td className="p-4"><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container"><span className="material-symbols-outlined text-[20px]">water_drop</span></div><div><p className="font-semibold text-on-surface">#TCK-904</p><p className="text-sm text-on-surface-variant truncate max-w-[200px]">Blocked major drainage near Market Yard</p></div></div></td>
                        <td className="p-4 text-on-surface">Ward 4 (Commercial)</td>
                        <td className="p-4 text-center"><span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#e8f5e9] text-[#2e7d32] border border-[#a5d6a7]">0.88</span></td>
                        <td className="p-4 text-right text-on-surface font-mono">12 hrs</td>
                      </tr>
                      <tr className="hover:bg-surface-container-low/50 transition-colors">
                        <td className="p-4"><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-full bg-primary-container/20 flex items-center justify-center text-primary"><span className="material-symbols-outlined text-[20px]">park</span></div><div><p className="font-semibold text-on-surface">#TCK-877</p><p className="text-sm text-on-surface-variant truncate max-w-[200px]">Fallen tree clearance on Shirdi Road</p></div></div></td>
                        <td className="p-4 text-on-surface">Ward 1 (North)</td>
                        <td className="p-4 text-center"><span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#fff3e0] text-[#ef6c00] border border-[#ffcc80]">0.75</span></td>
                        <td className="p-4 text-right text-on-surface font-mono">8 hrs</td>
                      </tr>
                      <tr className="hover:bg-surface-container-low/50 transition-colors">
                        <td className="p-4"><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-full bg-tertiary-container/20 flex items-center justify-center text-tertiary"><span className="material-symbols-outlined text-[20px]">lightbulb</span></div><div><p className="font-semibold text-on-surface">#TCK-912</p><p className="text-sm text-on-surface-variant truncate max-w-[200px]">Streetlight outage in residential block A</p></div></div></td>
                        <td className="p-4 text-on-surface">Ward 6 (East)</td>
                        <td className="p-4 text-center"><span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#fff3e0] text-[#ef6c00] border border-[#ffcc80]">0.68</span></td>
                        <td className="p-4 text-right text-on-surface font-mono">4 hrs</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div className="p-4 border-t border-outline-variant/20 bg-surface text-center">
                  <button className="text-sm font-semibold text-primary hover:underline">View All 42 Allocated Tickets</button>
                </div>
              </div>
            </div>

            {/* Side Panel */}
            <div className="xl:col-span-1 flex flex-col gap-6">
              <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm p-6">
                <h3 className="text-headline-md font-headline-md text-on-surface mb-6 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">local_shipping</span> Dispatch Status
                </h3>
                <div className="space-y-6">
                  <div className="relative pl-6 border-l-2 border-[#2e7d32]">
                    <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-[#2e7d32] border-2 border-surface-container-lowest"></div>
                    <div className="flex justify-between items-start mb-1"><p className="font-semibold text-on-surface">Heavy Eng. Team Alpha</p><span className="text-xs bg-[#e8f5e9] text-[#2e7d32] px-2 py-1 rounded-md font-bold">On Site</span></div>
                    <p className="text-sm text-on-surface-variant mb-2">Working on #TCK-892 (Godavari Bridge)</p>
                    <div className="w-full bg-surface-container-high rounded-full h-1.5"><div className="bg-[#2e7d32] h-1.5 rounded-full" style={{width: '45%'}}></div></div>
                    <p className="text-xs text-right mt-1 text-on-surface-variant">45% Complete</p>
                  </div>
                  <div className="relative pl-6 border-l-2 border-[#ef6c00]">
                    <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-[#ef6c00] border-2 border-surface-container-lowest"></div>
                    <div className="flex justify-between items-start mb-1"><p className="font-semibold text-on-surface">Sanitation Crew 3</p><span className="text-xs bg-[#fff3e0] text-[#ef6c00] px-2 py-1 rounded-md font-bold">In Transit</span></div>
                    <p className="text-sm text-on-surface-variant">En route to #TCK-904 (Ward 4)</p>
                    <p className="text-xs mt-1 text-on-surface-variant flex items-center gap-1"><span className="material-symbols-outlined text-[14px]">schedule</span> ETA: 12 mins</p>
                  </div>
                  <div className="relative pl-6 border-l-2 border-outline-variant">
                    <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-outline-variant border-2 border-surface-container-lowest"></div>
                    <div className="flex justify-between items-start mb-1"><p className="font-semibold text-on-surface-variant">Electrical Unit B</p><span className="text-xs bg-surface-container-high text-on-surface-variant px-2 py-1 rounded-md font-bold">Preparing</span></div>
                    <p className="text-sm text-on-surface-variant">Gathering supplies for #TCK-912</p>
                  </div>
                </div>
              </div>

              <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm overflow-hidden h-64 relative group">
                <div className="bg-cover bg-center w-full h-full absolute inset-0 opacity-80 mix-blend-multiply filter grayscale-[30%] group-hover:grayscale-0 transition-all duration-500" style={{backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuCsptM1SQl-dQE_ckdumNyMF0Zeo7VqCFqpocb8IuJvsm3ziaXOsIiigT2-n6HKPvTyPh_q0g1x668BqTsmk9OPXbKJB-pkEaAWdkmFLWqQEcw9M-fsc2Hj-xpL1brOWhOxSAhmEdqmdOVbH4HBLhf5R5YxGyuMKZmKg9yolYmGwqWb4wDX8HKj05Fq2IuxXOmmGu3JF_53vvLe3J664ebITM-5kSeRDWXAXfSM9fT0S6drNKH-zuc')"}}></div>
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex items-end p-4">
                  <div>
                    <p className="text-white font-bold text-lg drop-shadow-md">Live Operations Map</p>
                    <p className="text-white/80 text-sm drop-shadow-md">Kopargaon City Limits</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
