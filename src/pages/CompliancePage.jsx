import React from 'react';
import { Link } from 'react-router-dom';
import DiagnosticChecks from '../components/DiagnosticChecks';

export default function CompliancePage() {
  return (
    <>

{/* SideNavBar */}
<nav className="bg-surface-container-low dark:bg-surface-container-lowest text-primary dark:text-primary-fixed font-label-sm text-label-sm h-screen w-64 fixed left-0 top-0 border-r border-outline-variant/10 flat no shadows flex flex-col h-full py-unit px-4 gap-2 z-40">
{/* Header */}
<div className="flex items-center gap-3 px-2 py-4 mb-4">
<div className="w-10 h-10 rounded-lg overflow-hidden bg-primary-container flex items-center justify-center shrink-0">
<img alt="Kopargaon Municipal Council Logo" className="w-full h-full object-cover" data-alt="A clean, minimalist vector logo of a tree seamlessly blending with a gear, representing the Sylvan Urbanity and civic administrative focus of Kopargaon Municipal Council. The logo uses deep forest green and warm beige tones on a light background." src="https://lh3.googleusercontent.com/aida-public/AB6AXuAh4XSe1_lshvNMopUcvYrgfXIH7SwLSfvStqM7-6DtckSUlbkJsIqO10O_4Kf1GM4f7U8CeB2JV_a39NHwS2DJN11K9KZ4J_ucogkbVfcSMDipycAazPktSxDWm9oo-nPnporm6n4RWeKHB7Wmk6e_FreNlsVAxWufjdcc5VQcb0heGhquTd3lS7NUUwbbX_HkPmGnwjr99YdkUlbcpmnpsmDjV3GDSGobx_wHxGgID21fovU2J-M"/>
</div>
<div>
<h1 className="text-headline-md font-headline-md text-primary dark:text-primary-fixed truncate">Kopargaon Civic</h1>
<p className="text-on-surface-variant font-label-sm text-label-sm opacity-80">Administrative Suite</p>
</div>
</div>
{/* CTA */}
<button className="w-full bg-error text-on-error py-2 px-4 rounded-lg font-bold mb-6 hover:bg-error/90 transition-colors flex items-center justify-center gap-2 group">
<span className="material-symbols-outlined text-on-error group-hover:scale-110 transition-transform">emergency</span>
            Report Emergency
        </button>
{/* Navigation Tabs */}
<div className="flex-1 overflow-y-auto space-y-1">
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/admin">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">dashboard</span>
<span>Dashboard</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/ticket-pool">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">confirmation_number</span>
<span>Ticket Pool</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/staff-allocation">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">group_add</span>
<span>Staff Allocation</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/insights">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">analytics</span>
<span>Citizen Insights</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 bg-primary-container text-on-primary-container rounded-lg font-bold transition-all duration-300 group" to="/compliance">
<span className="material-symbols-outlined icon-fill">terminal</span>
<span>System Logs</span>
</Link>
</div>
{/* Footer Tabs */}
<div className="mt-auto pt-4 border-t border-outline-variant/20 space-y-1">
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/explanations">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">help</span>
<span>Support</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg transition-all duration-300 group" to="/">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">logout</span>
<span>Logout</span>
</Link>
</div>
</nav>
{/* Main Content Area */}
<main className="ml-64 flex-1 flex flex-col h-full bg-surface-bright relative">
{/* TopAppBar Contextual (Not the shell nav, but a page header) */}
<header className="bg-surface/80 dark:bg-surface-dim/80 backdrop-blur-xl border-b border-outline-variant/10 px-margin-desktop h-20 flex items-center justify-between shrink-0 sticky top-0 z-30">
<div>
<h2 className="font-headline-lg text-headline-lg text-primary">RTS Compliance &amp; Audit Trail</h2>
<p className="font-body-md text-body-md text-on-surface-variant mt-1">Real-time system actions, algorithmic decisions, and SLA compliance logs.</p>
</div>
<button className="bg-primary text-on-primary font-body-md text-body-md font-bold py-2 px-6 rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm">
<span className="material-symbols-outlined">picture_as_pdf</span>
                Export RTS Defense Report (PDF)
            </button>
</header>
{/* Content Canvas */}
<div className="flex-1 flex overflow-hidden">
{/* Left Side: Filters and Log Feed */}
<div className="flex-1 flex flex-col p-8 overflow-hidden">
<DiagnosticChecks />
{/* Filters Bar */}
<div className="flex items-center gap-4 mb-6 shrink-0 bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/20 shadow-sm">
<div className="relative flex-1 max-w-xs">
<span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">calendar_today</span>
<input className="w-full pl-10 pr-4 py-2 bg-surface-bright border border-secondary-container rounded-lg focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-fixed/50 font-body-md text-body-md text-on-surface transition-all" placeholder="Last 24 Hours (Oct 24)" type="text"/>
</div>
<div className="relative flex-1 max-w-xs">
<span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">filter_list</span>
<select className="w-full pl-10 pr-8 py-2 bg-surface-bright border border-secondary-container rounded-lg focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-fixed/50 font-body-md text-body-md text-on-surface appearance-none transition-all">
<option>All Event Types</option>
<option>SLA Warning</option>
<option>Knapsack Deferral</option>
<option>Priority Escalation</option>
<option>Resource Reallocation</option>
</select>
<span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-outline pointer-events-none">expand_more</span>
</div>
<div className="relative flex-1">
<span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">search</span>
<input className="w-full pl-10 pr-4 py-2 bg-surface-bright border border-secondary-container rounded-lg focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-fixed/50 font-body-md text-body-md text-on-surface transition-all" placeholder="Search Hash or TKT ID..." type="text"/>
</div>
<button className="p-2 bg-surface-container hover:bg-surface-variant text-on-surface rounded-lg transition-colors border border-outline-variant/20">
<span className="material-symbols-outlined">refresh</span>
</button>
</div>
{/* Log Table Container */}
<div className="flex-1 bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm overflow-hidden flex flex-col">
{/* Table Header */}
<div className="grid grid-cols-[140px_120px_200px_minmax(250px,1fr)_120px] gap-4 p-4 border-b border-outline-variant/20 bg-surface-container-low font-label-sm text-label-sm text-on-surface-variant sticky top-0 uppercase tracking-wider">
<div>Timestamp</div>
<div>Event Hash</div>
<div>Action Taken</div>
<div>Algorithmic Justification</div>
<div>RTS Status</div>
</div>
{/* Table Body (Scrollable) */}
<div className="overflow-y-auto log-scroll flex-1 font-mono text-mono-sm text-on-surface">
{/* Log Row 1 */}
<div className="grid grid-cols-[140px_120px_200px_minmax(250px,1fr)_120px] gap-4 p-4 border-b border-outline-variant/10 hover:bg-surface-variant/30 cursor-pointer transition-colors active-log-row bg-primary-fixed/10" onclick="toggleDrawer()">
<div className="text-outline">2024-10-24 14:32:01</div>
<div className="text-tertiary">#A7F9B2</div>
<div className="font-medium">Knapsack Deferral</div>
<div className="truncate text-on-surface-variant">Deferred TKT-1088 due to Daily Budget Cap exceeded by 4% in Zone C.</div>
<div>
<span className="inline-flex items-center px-2 py-1 rounded bg-error-container text-on-error-container font-label-sm text-[10px]">
                                    SLA AT RISK
                                </span>
</div>
</div>
{/* Log Row 2 */}
<div className="grid grid-cols-[140px_120px_200px_minmax(250px,1fr)_120px] gap-4 p-4 border-b border-outline-variant/10 hover:bg-surface-variant/30 cursor-pointer transition-colors">
<div className="text-outline">2024-10-24 14:28:45</div>
<div className="text-tertiary">#C4E2D1</div>
<div className="font-medium">Priority Escalation</div>
<div className="truncate text-on-surface-variant">Elevated TKT-1092 severity based on sentiment analysis spike (+2.4σ).</div>
<div>
<span className="inline-flex items-center px-2 py-1 rounded bg-tertiary-container text-on-primary font-label-sm text-[10px]">
                                    COMPLIANT
                                </span>
</div>
</div>
{/* Log Row 3 */}
<div className="grid grid-cols-[140px_120px_200px_minmax(250px,1fr)_120px] gap-4 p-4 border-b border-outline-variant/10 hover:bg-surface-variant/30 cursor-pointer transition-colors">
<div className="text-outline">2024-10-24 14:15:22</div>
<div className="text-tertiary">#F1A8B2</div>
<div className="font-medium">Resource Reallocation</div>
<div className="truncate text-on-surface-variant">Shifted Crew Alpha to TKT-1085 (Water Main) bypassing standard queue.</div>
<div>
<span className="inline-flex items-center px-2 py-1 rounded bg-tertiary-container text-on-primary font-label-sm text-[10px]">
                                    COMPLIANT
                                </span>
</div>
</div>
</div>
</div>
</div>
{/* Right Side: Detail Drawer (Simulated as always visible for demo, or toggled) */}
<div className="w-[400px] border-l border-outline-variant/20 bg-surface-container-lowest flex flex-col shadow-[-10px_0_20px_rgba(22,52,34,0.02)] transition-transform duration-300 transform translate-x-0" id="detailDrawer">
{/* Drawer Header */}
<div className="p-6 border-b border-outline-variant/20 flex justify-between items-center bg-surface-bright">
<div>
<h3 className="font-headline-md text-headline-md text-primary">Log Details</h3>
<p className="font-mono text-mono-sm text-outline mt-1">Hash: #A7F9B2</p>
</div>
<button className="text-outline hover:text-primary transition-colors p-2 rounded-full hover:bg-surface-variant" onclick="toggleDrawer()">
<span className="material-symbols-outlined">close</span>
</button>
</div>
{/* Drawer Content */}
<div className="flex-1 overflow-y-auto p-6 space-y-6 log-scroll">
{/* Context Card */}
<div className="bg-surface-container p-4 rounded-lg border border-outline-variant/10">
<div className="font-label-sm text-label-sm text-on-surface-variant mb-2">Event Context</div>
<div className="grid grid-cols-2 gap-4 font-mono text-mono-sm">
<div>
<div className="text-outline">Target ID</div>
<div className="text-on-surface font-medium">TKT-1088</div>
</div>
<div>
<div className="text-outline">Action</div>
<div className="text-on-surface font-medium">Deferral</div>
</div>
<div>
<div className="text-outline">Model Ver</div>
<div className="text-on-surface font-medium">v4.2.1-KNAP</div>
</div>
<div>
<div className="text-outline">Execution Ms</div>
<div className="text-on-surface font-medium">142ms</div>
</div>
</div>
</div>
{/* SHAP Values / JSON Block */}
<div>
<div className="font-label-sm text-label-sm text-on-surface-variant mb-2 flex items-center justify-between">
<span>Raw Decision Payload (SHAP)</span>
<button className="text-primary hover:underline text-xs flex items-center gap-1">
<span className="material-symbols-outlined text-[16px]">content_copy</span> Copy
                            </button>
</div>
<div className="bg-inverse-surface text-inverse-on-surface p-4 rounded-lg font-mono text-mono-sm overflow-x-auto border border-outline-variant/20 shadow-inner">
<pre className="whitespace-pre text-[11px] leading-tight text-[#a0cfa0]">{"{"}
  "event_id": "evt_99827364",
  "action": "knapsack_defer",
  "ticket_id": "TKT-1088",
  "decision_vector": {"{"}
    "base_priority": 0.65,
    "budget_impact": 0.82,
    "sla_urgency": 0.41,
    "resource_availability": 0.12
  {"}"},
  "shap_values": {"{"}
    "budget_constraint_zC": <span className="text-[#f4a261]">0.45</span>,
    "historical_overrun_prob": <span className="text-[#f4a261]">0.22</span>,
    "citizen_sentiment_score": <span className="text-[#e9c46a]">-0.15</span>,
    "weather_delay_factor": <span className="text-[#e9c46a]">-0.05</span>
  {"}"},
  "knapsack_params": {"{"}
    "max_weight": 5000,
    "current_weight": 4850,
    "item_weight": 350,
    "item_value": 85
  {"}"},
  "conclusion": "Item weight exceeds remaining capacity. Deferred to next epoch."
{"}"}
</pre>
</div>
</div>
{/* Explainer */}
<div className="bg-primary-container/10 p-4 rounded-lg border border-primary-container/20">
<div className="flex items-start gap-3">
<span className="material-symbols-outlined text-primary mt-0.5">info</span>
<p className="font-body-md text-[14px] text-on-surface-variant leading-relaxed">
                                The algorithm deferred this ticket primarily due to the <span className="font-mono text-primary bg-primary-fixed/30 px-1 rounded">budget_constraint_zC</span> variable. Proceeding would have violated the strict daily allocation cap for Zone C.
                            </p>
</div>
</div>
</div>
</div>
</div>
</main>


    </>
  );
}
