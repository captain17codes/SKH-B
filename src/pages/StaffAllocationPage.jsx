import React from 'react';
import { Link } from 'react-router-dom';

export default function StaffAllocationPage() {
  return (
    <>

{/* SideNavBar */}
<nav className="bg-surface-container-low h-screen w-64 fixed left-0 top-0 border-r border-outline-variant/10 flex flex-col py-unit px-4 gap-2 z-40 hidden md:flex">
<div className="mb-8 mt-4 px-2">
<div className="flex items-center gap-3">
<div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center overflow-hidden">
<img alt="Kopargaon Municipal Council Logo" className="w-full h-full object-cover" data-alt="A clean, modern geometric logo design representing a municipality, featuring interconnected green leaves and a subtle cogwheel motif, rendered in a crisp vector graphic style on a white background. The lighting is flat and bright, fitting a high-quality UI asset." src="https://lh3.googleusercontent.com/aida-public/AB6AXuBDBN6Vr66zgAykLIdBF6kJuUUpje2sd40AAIc7HxAmI0QYqK5zRFtyA2M-iqD9MwYWr8jDz9z6EECsY4tblIDj6DJE_jJrMq3RUXjf4bMex3yZ5Opmg7t0g66b_pibuhRi6eeWkK1cBJz24b7mradbAX-IiU4YOa-1KC1k-XcaDnuC4JTKAIJir3O8clRq5RdBQ-rYb7jnF_Yq0T-83nLuzBRMSQj_1XCkF104fgx9Mphd54iwNXw"/>
</div>
<div>
<h1 className="font-headline-md text-headline-md text-primary">Kopargaon Civic</h1>
<p className="font-label-sm text-label-sm text-on-surface-variant">Administrative Suite</p>
</div>
</div>
</div>
<button className="w-full bg-primary text-on-primary font-label-sm text-label-sm py-3 px-4 rounded-xl mb-6 hover:bg-primary/90 transition-colors flex items-center justify-center gap-2">
<span className="material-symbols-outlined text-[18px]">add_alert</span>
            Report Emergency
        </button>
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
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform" style={{fontVariationSettings: "'FILL' 1"}}>group_add</span>
<span className="font-label-sm text-label-sm">Staff Allocation</span>
</Link>
<Link className="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 transition-all duration-300 rounded-lg group" to="/insights">
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
{/* TopNavBar */}
<header className="sticky top-0 z-50 flex justify-between items-center w-full px-margin-mobile md:px-margin-desktop h-16 bg-surface/80 backdrop-blur-xl shadow-sm border-b-0">
<div className="flex items-center gap-4">
<button className="md:hidden text-on-surface p-2">
<span className="material-symbols-outlined">menu</span>
</button>
<div className="hidden md:flex items-center bg-surface-container-high rounded-full px-4 py-2">
<span className="material-symbols-outlined text-on-surface-variant mr-2">search</span>
<input className="bg-transparent border-none focus:ring-0 text-body-md font-body-md text-on-surface w-64 placeholder:text-outline" placeholder="Search resources..." type="text"/>
</div>
</div>
<div className="flex items-center gap-4">
<button className="p-2 text-on-surface-variant hover:bg-secondary-container transition-colors rounded-full cursor-pointer active:scale-95 duration-200">
<span className="material-symbols-outlined">notifications</span>
</button>
<button className="p-2 text-on-surface-variant hover:bg-secondary-container transition-colors rounded-full cursor-pointer active:scale-95 duration-200">
<span className="material-symbols-outlined">settings</span>
</button>
<div className="w-8 h-8 rounded-full overflow-hidden ml-2 cursor-pointer border border-outline-variant/30">
<img alt="Administrator Avatar" className="w-full h-full object-cover" data-alt="A professional headshot of a female administrator wearing a smart casual blazer, smiling confidently. Soft, diffused indoor lighting highlights a modern office background slightly blurred out. The mood is approachable yet authoritative, fitting a high-quality SaaS avatar." src="https://lh3.googleusercontent.com/aida-public/AB6AXuB1WjUMikFMV5hQODEHz3iP2scyiyDQNWlk7y11j6zdq6R2hvupFTN0sq5AinF6IJvYee0t42X64rkUDwkLWePg7SjJfWRsOf876c3hdmyswcd-HbDenbX0E_vPSKmTT-cJsXpxOpfbHMGRNx1Xdiiu_GUuMA4y1BPd6FTTYzEDaoRR7GgjzH-c0o2LYRm55YxnFgj8fNbMsg9aFqxZtIIecLp0c3Rokk7qaObBiwE193X3h2PpRlg"/>
</div>
</div>
</header>
{/* Canvas */}
<main className="flex-1 p-margin-mobile md:p-margin-desktop pb-24 md:pb-margin-desktop">
<div className="mb-8">
<h2 className="font-headline-lg-mobile md:font-headline-lg text-headline-lg-mobile md:text-headline-lg text-on-surface mb-2">Staff Allocation Overview</h2>
<p className="font-body-md text-body-md text-on-surface-variant">Manage municipal teams and monitor daily resource utilization.</p>
</div>
{/* Top Metrics */}
<div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
<div className="glass-panel rounded-xl p-6 shadow-sm">
<div className="flex justify-between items-start mb-4">
<div className="flex items-center gap-2">
<div className="p-2 bg-primary-container/20 rounded-lg text-primary">
<span className="material-symbols-outlined">account_balance_wallet</span>
</div>
<h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Daily Budget Utilized</h3>
</div>
<span className="font-headline-md text-headline-md text-primary">85%</span>
</div>
<div className="w-full bg-surface-container-high rounded-full h-2 overflow-hidden">
<div className="bg-primary h-2 rounded-full" style={{width: '85%'}}></div>
</div>
</div>
<div className="glass-panel rounded-xl p-6 shadow-sm">
<div className="flex justify-between items-start mb-4">
<div className="flex items-center gap-2">
<div className="p-2 bg-primary-container/20 rounded-lg text-primary">
<span className="material-symbols-outlined">schedule</span>
</div>
<h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Man-Hours Deployed</h3>
</div>
<span className="font-headline-md text-headline-md text-primary">142<span className="text-body-md text-outline">/150</span></span>
</div>
<div className="w-full bg-surface-container-high rounded-full h-2 overflow-hidden">
<div className="bg-primary h-2 rounded-full" style={{width: '94%'}}></div>
</div>
</div>
<div className="glass-panel rounded-xl p-6 shadow-sm">
<div className="flex justify-between items-start mb-4">
<div className="flex items-center gap-2">
<div className="p-2 bg-primary-container/20 rounded-lg text-primary">
<span className="material-symbols-outlined">task_alt</span>
</div>
<h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Tickets Addressed</h3>
</div>
<span className="font-headline-md text-headline-md text-primary">14</span>
</div>
<div className="w-full bg-surface-container-high rounded-full h-2 overflow-hidden">
<div className="bg-primary h-2 rounded-full" style={{width: '65%'}}></div>
</div>
</div>
</div>
{/* Layout Split */}
<div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
{/* Left Column: Team Manifests */}
<div className="flex flex-col gap-4">
<h3 className="font-headline-md text-headline-md text-on-surface mb-2">Team Manifests</h3>
{/* Accordion Card 1 */}
<div className="bg-surface rounded-xl shadow-sm border border-outline-variant/20 overflow-hidden">
<div className="p-4 flex justify-between items-center cursor-pointer hover:bg-surface-container-low transition-colors border-b border-outline-variant/10">
<div className="flex items-center gap-3">
<div className="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-primary">
<span className="material-symbols-outlined">water_drop</span>
</div>
<div>
<h4 className="font-label-sm text-label-sm text-on-surface">Rapid Response Team - Water</h4>
<p className="text-sm text-on-surface-variant">4 Members Active</p>
</div>
</div>
<div className="flex items-center gap-4">
<span className="px-2 py-1 bg-error-container text-on-error-container rounded text-xs font-semibold">2h 14m SLA</span>
<span className="material-symbols-outlined text-outline">expand_more</span>
</div>
</div>
<div className="p-4 bg-surface-container-lowest flex flex-col gap-3">
<div className="flex items-start gap-3 p-3 rounded-lg border border-outline-variant/10 hover:border-primary/30 transition-colors">
<span className="material-symbols-outlined text-tertiary mt-0.5">plumbing</span>
<div className="flex-1">
<p className="font-body-md text-body-md text-on-surface font-semibold">Main Pipe Burst - Sector 4</p>
<p className="text-sm text-on-surface-variant">Dispatched: 08:30 AM</p>
</div>
<span className="px-2 py-1 bg-tertiary-fixed text-on-tertiary-fixed rounded-full text-xs">In Progress</span>
</div>
</div>
</div>
{/* Accordion Card 2 */}
<div className="bg-surface rounded-xl shadow-sm border border-outline-variant/20 overflow-hidden">
<div className="p-4 flex justify-between items-center cursor-pointer hover:bg-surface-container-low transition-colors border-b border-outline-variant/10">
<div className="flex items-center gap-3">
<div className="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-primary">
<span className="material-symbols-outlined">cleaning_services</span>
</div>
<div>
<h4 className="font-label-sm text-label-sm text-on-surface">Sanitation Crew B</h4>
<p className="text-sm text-on-surface-variant">6 Members Active</p>
</div>
</div>
<div className="flex items-center gap-4">
<span className="px-2 py-1 bg-tertiary-fixed text-on-tertiary-fixed rounded text-xs font-semibold">On Schedule</span>
<span className="material-symbols-outlined text-outline">expand_more</span>
</div>
</div>
</div>
</div>
{/* Right Column: Dispatch Map & Timeline */}
<div className="flex flex-col gap-4">
<h3 className="font-headline-md text-headline-md text-on-surface mb-2">Live Deployment</h3>
<div className="bg-surface-container-highest rounded-xl h-80 relative overflow-hidden flex items-center justify-center border border-outline-variant/20 shadow-sm">
<span className="material-symbols-outlined text-6xl text-outline-variant absolute">map</span>
<div className="bg-cover bg-center w-full h-full opacity-60" data-alt="A clean, highly stylized vector map of an urban grid, depicted in a light modern UI aesthetic. The map features subtle beige and soft green tones for parks and roads, with semi-transparent routing lines indicating paths. Soft, ambient overhead lighting gives it a premium digital interface feel without heavy shadows." data-location="Kopargaon" style={{backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuAHnb1FrEDcsnhau3KeDab0FhkN40tYQIE4JV1ybKIlvGFfuIjqqkFPdqndX_NowUP2n46hb4SMyRkb2yf1mKxcPetlk8AYI8C2L7I5qI-miaa_1deu9iuxYI2qzbMBknX9kC3D0RcMBZ0vP2EjA9HFDHAWwC7zsKPfMUGGZ1olnNAeIk0i0GA8DjivTO-ervfCHjFJOf66CnYQmQhQfU_lIBDGrGUH5BLncK2CKih_PaHcrO0jMF4')"}}></div>
{/* Map Overlays */}
<div className="absolute top-4 right-4 bg-surface/90 backdrop-blur rounded-lg p-2 shadow-sm flex flex-col gap-2">
<button className="p-1 text-on-surface-variant hover:text-primary"><span className="material-symbols-outlined">my_location</span></button>
<div className="w-full h-px bg-outline-variant/30"></div>
<button className="p-1 text-on-surface-variant hover:text-primary"><span className="material-symbols-outlined">layers</span></button>
</div>
</div>
<div className="bg-surface rounded-xl p-6 shadow-sm border border-outline-variant/20 mt-2">
<h4 className="font-label-sm text-label-sm text-on-surface mb-4">Scheduled Tasks Timeline</h4>
<div className="relative w-full overflow-x-auto pb-4">
<div className="min-w-[600px] flex justify-between relative pt-8">
{/* Timeline Line */}
<div className="absolute top-10 left-4 right-4 h-0.5 bg-outline-variant/30 z-0"></div>
{/* Timeline Points */}
<div className="relative z-10 flex flex-col items-center gap-2">
<div className="w-4 h-4 rounded-full bg-primary ring-4 ring-surface"></div>
<span className="text-xs font-semibold text-on-surface">08:00</span>
<span className="text-xs text-on-surface-variant whitespace-nowrap">Briefing</span>
</div>
<div className="relative z-10 flex flex-col items-center gap-2">
<div className="w-4 h-4 rounded-full bg-primary ring-4 ring-surface"></div>
<span className="text-xs font-semibold text-on-surface">10:30</span>
<span className="text-xs text-on-surface-variant whitespace-nowrap">Zone A Clean</span>
</div>
<div className="relative z-10 flex flex-col items-center gap-2">
<div className="w-4 h-4 rounded-full bg-surface border-2 border-primary ring-4 ring-surface"></div>
<span className="text-xs font-semibold text-on-surface">13:00</span>
<span className="text-xs text-on-surface-variant whitespace-nowrap">Maintenance</span>
</div>
<div className="relative z-10 flex flex-col items-center gap-2">
<div className="w-4 h-4 rounded-full bg-surface-container-high border-2 border-outline-variant ring-4 ring-surface"></div>
<span className="text-xs font-semibold text-outline">16:00</span>
<span className="text-xs text-outline whitespace-nowrap">Debrief</span>
</div>
</div>
</div>
</div>
</div>
</div>
</main>
</div>

    </>
  );
}
