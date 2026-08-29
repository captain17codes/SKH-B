import React from 'react';
import { Link } from 'react-router-dom';

export default function CitizenInsightsPage() {
  return (
    <>

{/* SideNavBar Shared Component */}
<nav className="hidden md:flex bg-surface-container-low border-r border-outline-variant/10 h-screen w-64 fixed left-0 top-0 flex-col py-unit px-4 gap-2 z-40">
{/* Header */}
<div className="flex items-center gap-3 px-2 py-4 mb-4">
<div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center shrink-0">
<span className="material-symbols-outlined text-on-primary" data-icon="account_balance">account_balance</span>
</div>
<div className="flex flex-col">
<span className="text-headline-md font-headline-md text-primary">Kopargaon Civic</span>
<span className="text-label-sm font-label-sm text-on-surface-variant">Administrative Suite</span>
</div>
</div>
{/* Navigation Links */}
<div className="flex flex-col gap-1 flex-1">
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/admin">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform" data-icon="dashboard">dashboard</span>
<span className="font-label-sm text-label-sm">Dashboard</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/ticket-pool">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform" data-icon="confirmation_number">confirmation_number</span>
<span className="font-label-sm text-label-sm">Ticket Pool</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/staff-allocation">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform" data-icon="group_add">group_add</span>
<span className="font-label-sm text-label-sm">Staff Allocation</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 bg-primary-container text-on-primary-container rounded-lg font-bold transition-all duration-300 group cursor-pointer" to="/insights">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform" data-icon="analytics">analytics</span>
<span className="font-label-sm text-label-sm">Citizen Insights</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/compliance">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform" data-icon="terminal">terminal</span>
<span className="font-label-sm text-label-sm">System Logs</span>
</Link>
</div>
{/* CTA */}
<div className="mt-auto mb-4">
<button className="w-full bg-primary text-on-primary py-2 rounded-lg font-label-sm text-label-sm shadow-sm hover:bg-primary-container hover:text-on-primary-container transition-colors flex items-center justify-center gap-2">
<span className="material-symbols-outlined" data-icon="add_alert">add_alert</span>
                Report Emergency
            </button>
</div>
{/* Footer Links */}
<div className="flex flex-col gap-1 border-t border-outline-variant/10 pt-2">
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/explanations">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform" data-icon="help">help</span>
<span className="font-label-sm text-label-sm">Support</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform" data-icon="logout">logout</span>
<span className="font-label-sm text-label-sm">Logout</span>
</Link>
</div>
</nav>
{/* Main Content Area */}
<main className="flex-1 ml-0 md:ml-64 h-full overflow-y-auto bg-surface relative">
{/* Ambient Background Image to bleed through glass panels */}
<div className="absolute inset-0 z-0 opacity-40 pointer-events-none" data-alt="A subtle, high-key abstract architectural or organic texture in light beige and soft forest green tones. The lighting is extremely soft, creating a serene, bright corporate modern environment suitable for a smart city dashboard backdrop. Large areas of whitespace and minimal details." style={{backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuAzQrtFUl1EaH_fj5FPu7qBPeUm-pKm23cjQzTxle-p9MjblzMlmeo2cEB5XJutsjF1U5OCCw08QYyQuzqWAwYmrX3pl7wMYmtJVWpHyPQryte3FDA5ZqYEm6sb3pBH9BZwnZhzNoOpaPszQXOuAXAVifwIi4JxvKfYvmSMMu4YWAkV_E4sx9MQD4Y8pjPldgZE3ldTrs-rfuDOtFHBJY-wNHN1km4sCRyjItKqCbaAyK5zNUSZomw')"}}></div>
<div className="relative z-10 max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-12 md:py-16">
{/* Header Section */}
<header className="mb-12">
<div className="inline-flex items-center gap-2 px-3 py-1 bg-surface-container-high rounded-full border border-outline-variant/20 mb-4">
<span className="material-symbols-outlined text-primary text-sm" data-icon="insights">insights</span>
<span className="font-label-sm text-label-sm text-on-surface-variant">Analytical Overview</span>
</div>
<h1 className="font-headline-display text-headline-display text-on-surface mb-2">Socio-Spatial Equity &amp; Communications</h1>
<p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl">Real-time telemetry on resource distribution, service level agreements, and communication efficacy across municipal wards.</p>
</header>
{/* KPI Cards Row */}
<div className="grid grid-cols-1 md:grid-cols-3 gap-gutter mb-12">
{/* KPI 1 */}
<div className="glass-panel rounded-xl p-6 relative overflow-hidden group">
<div className="absolute top-0 right-0 p-4 opacity-10 transform translate-x-4 -translate-y-4 group-hover:scale-110 transition-transform duration-500">
<span className="material-symbols-outlined text-6xl" data-icon="mark_email_read">mark_email_read</span>
</div>
<h3 className="font-label-sm text-label-sm text-on-surface-variant mb-1">Utility Messages Sent</h3>
<div className="font-headline-lg text-headline-lg text-primary flex items-baseline gap-2">
                        1,204
                        <span className="text-sm font-medium text-tertiary-container flex items-center bg-tertiary-fixed px-2 py-0.5 rounded-full">
<span className="material-symbols-outlined text-[16px]" data-icon="trending_up">trending_up</span> +12%
                        </span>
</div>
</div>
{/* KPI 2 */}
<div className="glass-panel rounded-xl p-6 relative overflow-hidden group">
<div className="absolute top-0 right-0 p-4 opacity-10 transform translate-x-4 -translate-y-4 group-hover:scale-110 transition-transform duration-500">
<span className="material-symbols-outlined text-6xl" data-icon="speed">speed</span>
</div>
<h3 className="font-label-sm text-label-sm text-on-surface-variant mb-1">Delivery Rate</h3>
<div className="font-headline-lg text-headline-lg text-primary flex items-baseline gap-2">
                        99.8%
                        <span className="text-sm font-medium text-on-surface-variant">System Optimal</span>
</div>
</div>
{/* KPI 3 */}
<div className="glass-panel rounded-xl p-6 relative overflow-hidden group">
<div className="absolute top-0 right-0 p-4 opacity-10 transform translate-x-4 -translate-y-4 group-hover:scale-110 transition-transform duration-500">
<span className="material-symbols-outlined text-6xl" data-icon="payments">payments</span>
</div>
<h3 className="font-label-sm text-label-sm text-on-surface-variant mb-1">Est. API Cost</h3>
<div className="font-headline-lg text-headline-lg text-primary flex items-baseline gap-2">
                        ₹144.48
                        <span className="text-sm font-medium text-error flex items-center bg-error-container px-2 py-0.5 rounded-full">
<span className="material-symbols-outlined text-[16px]" data-icon="trending_up">trending_up</span> +2%
                        </span>
</div>
</div>
</div>
{/* Bento Grid */}
<div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
{/* Chart 1: Reporting Bias vs. Action (Large span) */}
<div className="lg:col-span-8 glass-panel rounded-xl p-6 md:p-8 flex flex-col">
<div className="flex justify-between items-start mb-8">
<div>
<h2 className="font-headline-md text-headline-md text-on-surface mb-2">Reporting Bias vs. Action</h2>
<p className="font-body-md text-body-md text-on-surface-variant">Volume of Complaints vs Actual Triage Priority</p>
</div>
<div className="flex items-center gap-4">
<div className="flex items-center gap-2">
<div className="w-3 h-3 rounded-full bg-surface-variant border border-outline"></div>
<span className="font-label-sm text-label-sm text-on-surface-variant">Complaints</span>
</div>
<div className="flex items-center gap-2">
<div className="w-3 h-3 rounded-full bg-primary"></div>
<span className="font-label-sm text-label-sm text-on-surface-variant">Priority</span>
</div>
</div>
</div>
{/* Simulated Bar Chart */}
<div className="flex-1 flex items-end gap-2 md:gap-6 h-64 border-b border-outline-variant/30 pb-2 relative">
{/* Y-axis guides */}
<div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-20 z-0">
<div className="border-t border-outline-variant w-full"></div>
<div className="border-t border-outline-variant w-full"></div>
<div className="border-t border-outline-variant w-full"></div>
<div className="border-t border-outline-variant w-full"></div>
</div>
{/* Ward 1 */}
<div className="flex-1 flex justify-center items-end gap-1 md:gap-2 h-full z-10 group">
<div className="w-1/2 md:w-12 bg-surface-variant rounded-t-sm h-[80%] chart-bar group-hover:opacity-80 transition-opacity"></div>
<div className="w-1/2 md:w-12 bg-primary rounded-t-sm h-[40%] chart-bar group-hover:opacity-80 transition-opacity"></div>
</div>
{/* Ward 2 */}
<div className="flex-1 flex justify-center items-end gap-1 md:gap-2 h-full z-10 group">
<div className="w-1/2 md:w-12 bg-surface-variant rounded-t-sm h-[90%] chart-bar group-hover:opacity-80 transition-opacity"></div>
<div className="w-1/2 md:w-12 bg-primary rounded-t-sm h-[50%] chart-bar group-hover:opacity-80 transition-opacity"></div>
</div>
{/* Ward 3 */}
<div className="flex-1 flex justify-center items-end gap-1 md:gap-2 h-full z-10 group">
<div className="w-1/2 md:w-12 bg-surface-variant rounded-t-sm h-[40%] chart-bar group-hover:opacity-80 transition-opacity"></div>
<div className="w-1/2 md:w-12 bg-primary rounded-t-sm h-[30%] chart-bar group-hover:opacity-80 transition-opacity"></div>
</div>
{/* Ward 4 (Under-reported) */}
<div className="flex-1 flex justify-center items-end gap-1 md:gap-2 h-full z-10 group">
<div className="w-1/2 md:w-12 bg-surface-variant rounded-t-sm h-[20%] chart-bar group-hover:opacity-80 transition-opacity relative">
<div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-surface shadow-sm border border-outline-variant/20 px-2 py-1 rounded text-xs font-bold text-on-surface opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">Under-reported</div>
</div>
<div className="w-1/2 md:w-12 bg-tertiary-container rounded-t-sm h-[85%] chart-bar group-hover:opacity-80 transition-opacity relative">
<div className="absolute -top-3 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-primary rounded-full animate-ping"></div>
</div>
</div>
{/* Ward 5 */}
<div className="flex-1 flex justify-center items-end gap-1 md:gap-2 h-full z-10 group">
<div className="w-1/2 md:w-12 bg-surface-variant rounded-t-sm h-[60%] chart-bar group-hover:opacity-80 transition-opacity"></div>
<div className="w-1/2 md:w-12 bg-primary rounded-t-sm h-[50%] chart-bar group-hover:opacity-80 transition-opacity"></div>
</div>
</div>
{/* X-axis Labels */}
<div className="flex justify-between items-center mt-2 px-2 md:px-8 text-center text-on-surface-variant font-label-sm text-label-sm">
<div className="flex-1">Ward 1</div>
<div className="flex-1">Ward 2</div>
<div className="flex-1">Ward 3</div>
<div className="flex-1 font-bold text-primary">Ward 4</div>
<div className="flex-1">Ward 5</div>
</div>
{/* Insight Callout */}
<div className="mt-8 bg-tertiary-fixed/30 border border-tertiary-fixed rounded-lg p-4 flex items-start gap-4">
<span className="material-symbols-outlined text-tertiary mt-0.5" data-icon="lightbulb">lightbulb</span>
<p className="font-body-md text-body-md text-on-surface"><strong>Insight:</strong> Algorithm successfully redirected 22% of resources to under-reported Ward 4.</p>
</div>
</div>
{/* Chart 2: SLA Compliance (Smaller span) */}
<div className="lg:col-span-4 glass-panel rounded-xl p-6 md:p-8 flex flex-col">
<h2 className="font-headline-md text-headline-md text-on-surface mb-2">SLA Compliance</h2>
<p className="font-body-md text-body-md text-on-surface-variant mb-6">Resolution times across income brackets</p>
<div className="flex-1 relative flex flex-col justify-center min-h-[250px]">
{/* Decorative Line Chart representation */}
<svg className="w-full h-full absolute inset-0 preserve-3d overflow-visible" preserveaspectratio="none" viewbox="0 0 100 100">
<defs>
<lineargradient id="lineGrad" x1="0" x2="0" y1="0" y2="1">
<stop offset="0%" stop-color="#163422" stop-opacity="0.2"></stop>
<stop offset="100%" stop-color="#163422" stop-opacity="0"></stop>
</lineargradient>
</defs>
<path d="M0,80 Q25,75 50,40 T100,20 L100,100 L0,100 Z" fill="url(#lineGrad)"></path>
<path d="M0,80 Q25,75 50,40 T100,20" fill="none" stroke="#163422" strokeLinecap="round" strokeWidth="3"></path>
{/* Plot points */}
<circle cx="25" cy="65" fill="#ffffff" r="4" stroke="#163422" strokeWidth="2"></circle>
<circle cx="50" cy="40" fill="#ffffff" r="4" stroke="#163422" strokeWidth="2"></circle>
<circle cx="75" cy="30" fill="#ffffff" r="4" stroke="#163422" strokeWidth="2"></circle>
</svg>
{/* Overlay Labels */}
<div className="absolute inset-0 flex flex-col justify-between py-4 pointer-events-none opacity-40 text-xs text-on-surface-variant font-label-sm">
<div className="flex items-center gap-2"><div className="w-full h-px bg-outline-variant"></div>24hr</div>
<div className="flex items-center gap-2"><div className="w-full h-px bg-outline-variant"></div>48hr</div>
<div className="flex items-center gap-2"><div className="w-full h-px bg-outline-variant"></div>72hr</div>
</div>
</div>
<div className="flex justify-between items-center mt-4 border-t border-outline-variant/30 pt-4">
<div className="text-center">
<div className="font-label-sm text-label-sm text-on-surface-variant">Low</div>
</div>
<div className="text-center">
<div className="font-label-sm text-label-sm text-on-surface-variant">Mid</div>
</div>
<div className="text-center">
<div className="font-label-sm text-label-sm text-on-surface-variant">High</div>
</div>
</div>
</div>
</div>
{/* Footer Shared Component */}
<footer className="mt-24 border-t border-outline-variant/20 py-unit w-full max-w-container-max mx-auto px-margin-desktop flex flex-col md:flex-row justify-between items-center text-secondary dark:text-secondary-fixed bg-surface dark:bg-surface-dim flat no shadows">
<div className="font-bold text-on-surface text-label-sm mb-4 md:mb-0">
                    © 2024 Kopargaon Municipal Council. All rights reserved. Powered by Sylvan Urbanity Framework.
                </div>
<div className="flex gap-6 font-label-sm text-label-sm">
<Link className="text-on-secondary-fixed-variant hover:text-primary transition-colors" to="/">Privacy Policy</Link>
<Link className="text-on-secondary-fixed-variant hover:text-primary transition-colors" to="/">Terms of Service</Link>
<Link className="text-on-secondary-fixed-variant hover:text-primary transition-colors" to="/">Contact Support</Link>
</div>
</footer>
</div>
</main>


    </>
  );
}
