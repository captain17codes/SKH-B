import React, { useState } from 'react';
import { Link } from 'react-router-dom';

export default function AdminDashboardPage() {
  const [selectedTicket, setSelectedTicket] = useState('TKT-1042');

  const explanations = {
    'TKT-1042': '"This ticket received a high TOPSIS score primarily due to the severe health risk associated with post-monsoon drainage blockage in a high-density area (Ward 4). The \'Urgency\' and \'Citizen Impact\' features strongly pushed this to the top of the queue."',
    'TKT-1045': '"The TOPSIS model prioritized this due to significant traffic disruption potential on a major artery (Ward 1). While urgency is high, the lower resource availability score slightly depressed its overall rank compared to TKT-1042."',
  };

  return (
    <div className="antialiased flex h-screen overflow-hidden">
      {/* Mobile Header */}
      <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-4 py-4 bg-surface/80 backdrop-blur-md md:hidden border-b border-outline-variant/10">
        <div className="text-headline-lg-mobile font-headline-lg-mobile font-bold text-primary">Kopargaon Digital</div>
        <span className="material-symbols-outlined text-primary cursor-pointer">menu</span>
      </header>

      {/* SideNavBar */}
      <nav className="hidden md:flex flex-col h-screen fixed left-0 top-0 py-8 px-4 w-64 bg-surface-container-low border-r border-outline-variant/10 z-40">
        <div className="mb-8 px-4 flex items-center gap-3">
          <img alt="Kopargaon Seal" className="w-10 h-10 rounded-full object-cover border border-outline-variant/20" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCbe--BtCQo8VYz2Zrpc_8TgDinye-ag5rEWDgElk6cqKlf1X8Qi27quyeuvoAG6adl7w1pT3brXvpiKJC9fz6jwysBeDE_SL77JOB2UaF6f__Pq5ShBKRLkxlzxdf6kLOaKWOo7sQQtZcOrWahZUhoP82NNQQUYrW4lomHKxmww4RX9BqP89-Vbs_syZX1PbCnIXrlcdkThUGSSDKpVPDpw7v3YwVVUJlTuXV-QHqLPsNy5jDZ1pk" />
          <div>
            <div className="text-headline-md font-headline-md font-bold text-primary text-lg">City Council</div>
            <div className="text-label-sm font-label-sm text-secondary">Governance Portal</div>
          </div>
        </div>
        <div className="flex flex-col gap-2 flex-grow">
          <Link className="flex items-center gap-3 bg-primary-container text-on-primary-container rounded-lg px-4 py-3 font-label-sm text-label-sm font-bold opacity-80 scale-95 transition-all" to="/admin">
            <span className="material-symbols-outlined" style={{fontVariationSettings: "'FILL' 1"}}>dashboard</span> Dashboard
          </Link>
          <Link className="flex items-center gap-3 text-secondary px-4 py-3 hover:bg-secondary-container transition-colors rounded-lg font-label-sm text-label-sm" to="/ticket-pool">
            <span className="material-symbols-outlined">confirmation_number</span> Ticket Pool
          </Link>
          <Link className="flex items-center gap-3 text-secondary px-4 py-3 hover:bg-secondary-container transition-colors rounded-lg font-label-sm text-label-sm" to="/staff-allocation">
            <span className="material-symbols-outlined">group</span> Staff Allocation
          </Link>
          <Link className="flex items-center gap-3 text-secondary px-4 py-3 hover:bg-secondary-container transition-colors rounded-lg font-label-sm text-label-sm" to="/insights">
            <span className="material-symbols-outlined">analytics</span> Citizen Insights
          </Link>
          <Link className="flex items-center gap-3 text-secondary px-4 py-3 hover:bg-secondary-container transition-colors rounded-lg font-label-sm text-label-sm" to="/compliance">
            <span className="material-symbols-outlined">terminal</span> System Logs
          </Link>
        </div>
        <button className="mt-4 w-full bg-primary text-on-primary rounded-full py-3 px-4 font-label-sm text-label-sm font-bold hover:bg-tertiary-container transition-colors flex items-center justify-center gap-2 shadow-sm">
          <span className="material-symbols-outlined text-sm">add</span> New Entry
        </button>
        <div className="mt-8 flex flex-col gap-2 pt-4 border-t border-outline-variant/20">
          <Link className="flex items-center gap-3 text-secondary px-4 py-2 hover:bg-secondary-container transition-colors rounded-lg font-label-sm text-label-sm" to="/explanations">
            <span className="material-symbols-outlined">help</span> Help
          </Link>
          <Link className="flex items-center gap-3 text-secondary px-4 py-2 hover:bg-secondary-container transition-colors rounded-lg font-label-sm text-label-sm" to="/">
            <span className="material-symbols-outlined">logout</span> Logout
          </Link>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-grow flex flex-col md:ml-64 pt-20 md:pt-8 px-4 md:px-margin-desktop overflow-y-auto h-full bg-background relative">
        <div className="absolute inset-0 pointer-events-none opacity-[0.03] z-0" style={{backgroundImage: 'radial-gradient(circle at 2px 2px, #163422 1px, transparent 0)', backgroundSize: '32px 32px'}}></div>
        <div className="relative z-10 w-full max-w-container-max mx-auto pb-24">
          <header className="mb-12 flex justify-between items-end">
            <div>
              <h1 className="text-headline-display font-headline-display text-primary mb-2">Priority Operations</h1>
              <p className="text-body-lg font-body-lg text-on-surface-variant max-w-2xl">Today's algorithmic allocation for Kopargaon municipal tasks. Priority is weighted by urgency, citizen impact, and resource availability.</p>
            </div>
            <div className="hidden lg:flex items-center gap-4">
              <span className="text-label-sm font-label-sm text-secondary bg-surface-container-high px-3 py-1 rounded-full">Last updated: 08:30 AM</span>
            </div>
          </header>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
            {/* Ticket List */}
            <div className="lg:col-span-8 flex flex-col gap-6">
              <div className="bg-surface rounded-xl border border-outline-variant/20 shadow-sm overflow-hidden flex flex-col h-[716px]">
                <div className="px-6 py-4 border-b border-outline-variant/10 bg-surface-container-lowest flex justify-between items-center">
                  <h2 className="text-headline-md font-headline-md text-primary">Ranked Ticket Pool</h2>
                  <button className="text-label-sm font-label-sm text-primary flex items-center gap-1 hover:text-primary-container transition-colors">
                    Filter <span className="material-symbols-outlined text-sm">filter_list</span>
                  </button>
                </div>
                <div className="overflow-y-auto flex-grow">
                  <table className="w-full text-left border-collapse">
                    <thead className="sticky top-0 bg-surface-container-lowest border-b border-outline-variant/20 z-10">
                      <tr>
                        <th className="py-3 px-6 text-label-sm font-label-sm text-on-surface-variant font-semibold">ID</th>
                        <th className="py-3 px-6 text-label-sm font-label-sm text-on-surface-variant font-semibold">Category</th>
                        <th className="py-3 px-6 text-label-sm font-label-sm text-on-surface-variant font-semibold">Description</th>
                        <th className="py-3 px-6 text-label-sm font-label-sm text-on-surface-variant font-semibold">Ward</th>
                        <th className="py-3 px-6 text-label-sm font-label-sm text-primary font-bold cursor-pointer group">
                          <div className="flex items-center gap-1">TOPSIS <span className="material-symbols-outlined text-[16px] opacity-50 group-hover:opacity-100">arrow_drop_down</span></div>
                        </th>
                        <th className="py-3 px-6 text-label-sm font-label-sm text-on-surface-variant font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="text-body-md font-body-md text-on-surface divide-y divide-outline-variant/10">
                      <tr className={`table-row-hover cursor-pointer transition-colors ${selectedTicket === 'TKT-1042' ? 'bg-primary/5' : ''}`} onClick={() => setSelectedTicket('TKT-1042')}>
                        <td className="py-4 px-6 font-mono text-sm text-primary">TKT-1042</td>
                        <td className="py-4 px-6"><span className="inline-flex items-center gap-1 text-label-sm font-label-sm bg-error-container text-on-error-container px-2 py-1 rounded-md"><span className="material-symbols-outlined text-[14px]">water_drop</span> Sanitation</span></td>
                        <td className="py-4 px-6 max-w-xs truncate" title="Drainage blockage after monsoon near Main Market">Drainage blockage after monsoon...</td>
                        <td className="py-4 px-6 text-on-surface-variant">Ward 4</td>
                        <td className="py-4 px-6 font-bold text-primary">0.892</td>
                        <td className="py-4 px-6"><span className="w-2 h-2 inline-block rounded-full bg-[#d97706] mr-2"></span>In Progress</td>
                      </tr>
                      <tr className={`table-row-hover cursor-pointer transition-colors ${selectedTicket === 'TKT-1045' ? 'bg-primary/5' : ''}`} onClick={() => setSelectedTicket('TKT-1045')}>
                        <td className="py-4 px-6 font-mono text-sm text-secondary">TKT-1045</td>
                        <td className="py-4 px-6"><span className="inline-flex items-center gap-1 text-label-sm font-label-sm bg-surface-container-high text-on-surface px-2 py-1 rounded-md"><span className="material-symbols-outlined text-[14px]">directions_car</span> Infra</span></td>
                        <td className="py-4 px-6 max-w-xs truncate">Deep pothole near Godavari Bridge approach</td>
                        <td className="py-4 px-6 text-on-surface-variant">Ward 1</td>
                        <td className="py-4 px-6 font-semibold text-secondary">0.751</td>
                        <td className="py-4 px-6"><span className="w-2 h-2 inline-block rounded-full bg-error mr-2"></span>Unassigned</td>
                      </tr>
                      <tr className="table-row-hover cursor-pointer transition-colors">
                        <td className="py-4 px-6 font-mono text-sm text-secondary">TKT-1048</td>
                        <td className="py-4 px-6"><span className="inline-flex items-center gap-1 text-label-sm font-label-sm bg-tertiary-container text-on-tertiary-container px-2 py-1 rounded-md"><span className="material-symbols-outlined text-[14px]">park</span> Environment</span></td>
                        <td className="py-4 px-6 max-w-xs truncate">Fallen branch obstructing pedestrian path in Shivaji Park</td>
                        <td className="py-4 px-6 text-on-surface-variant">Ward 3</td>
                        <td className="py-4 px-6 font-semibold text-secondary">0.620</td>
                        <td className="py-4 px-6"><span className="w-2 h-2 inline-block rounded-full bg-outline mr-2"></span>Pending Assessment</td>
                      </tr>
                      <tr className="table-row-hover cursor-pointer transition-colors">
                        <td className="py-4 px-6 font-mono text-sm text-secondary">TKT-1021</td>
                        <td className="py-4 px-6"><span className="inline-flex items-center gap-1 text-label-sm font-label-sm bg-surface-container-high text-on-surface px-2 py-1 rounded-md"><span className="material-symbols-outlined text-[14px]">lightbulb</span> Utility</span></td>
                        <td className="py-4 px-6 max-w-xs truncate">Streetlight malfunctioning on Station Road</td>
                        <td className="py-4 px-6 text-on-surface-variant">Ward 2</td>
                        <td className="py-4 px-6 font-semibold text-secondary">0.510</td>
                        <td className="py-4 px-6"><span className="w-2 h-2 inline-block rounded-full bg-[#059669] mr-2"></span>Completed</td>
                      </tr>
                    </tbody>
                  </table>
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
                    <h3 className="text-headline-md font-headline-md text-primary">{selectedTicket}</h3>
                  </div>
                  <span className="material-symbols-outlined text-tertiary-container bg-tertiary-container/10 p-2 rounded-full">psychology</span>
                </div>
                <div className="bg-surface-container-low p-4 rounded-lg border border-outline-variant/10 mb-6 relative z-10">
                  <p className="text-body-md font-body-md text-on-surface-variant italic">
                    {explanations[selectedTicket] || explanations['TKT-1042']}
                  </p>
                </div>
                <div className="flex-grow flex flex-col relative z-10">
                  <h4 className="text-label-sm font-label-sm text-on-surface font-semibold mb-4 border-b border-outline-variant/10 pb-2">Feature Impact (SHAP Values)</h4>
                  <div className="space-y-4 flex-grow flex flex-col justify-center">
                    <div>
                      <div className="flex justify-between text-label-sm font-label-sm mb-1"><span className="text-on-surface-variant">Urgency (Monsoon Hazard)</span><span className="text-error font-bold">+0.32</span></div>
                      <div className="w-full bg-surface-container-highest rounded-full h-2 overflow-hidden"><div className="bg-error h-2 rounded-full animate-bar" style={{'--target-width': '85%'}}></div></div>
                    </div>
                    <div>
                      <div className="flex justify-between text-label-sm font-label-sm mb-1"><span className="text-on-surface-variant">Citizen Impact (Density)</span><span className="text-primary font-bold">+0.28</span></div>
                      <div className="w-full bg-surface-container-highest rounded-full h-2 overflow-hidden"><div className="bg-primary h-2 rounded-full animate-bar" style={{'--target-width': '70%'}}></div></div>
                    </div>
                    <div>
                      <div className="flex justify-between text-label-sm font-label-sm mb-1"><span className="text-on-surface-variant">Resource Availability</span><span className="text-secondary font-bold">-0.05</span></div>
                      <div className="w-full bg-surface-container-highest rounded-full h-2 flex justify-end overflow-hidden"><div className="bg-secondary h-2 rounded-full animate-bar origin-right" style={{'--target-width': '15%'}}></div></div>
                    </div>
                  </div>
                  <button className="mt-6 w-full border border-primary text-primary rounded-full py-2 px-4 font-label-sm text-label-sm font-bold hover:bg-primary/5 transition-colors">
                    View Full Model Metrics
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
