import React from 'react';
import { Link } from 'react-router-dom';

export default function TicketPoolPage() {
  return (
    <>

{/* Shared Component: SideNavBar */}
<aside className="bg-surface-container-low dark:bg-surface-container-lowest h-screen w-64 fixed left-0 top-0 border-r border-outline-variant/10 flex flex-col h-full py-unit px-4 gap-2 z-40 md:flex hidden">
{/* Header */}
<div className="mb-8 mt-4 px-2">
<h2 className="text-headline-md font-headline-md text-primary dark:text-primary-fixed">Kopargaon Civic</h2>
<p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mt-1">Administrative Suite</p>
</div>
{/* CTA */}
<button className="bg-primary text-on-primary font-label-sm text-label-sm rounded-full py-3 px-4 mb-6 hover:bg-primary-container transition-colors shadow-sm w-full text-center">
            Report Emergency
        </button>
{/* Navigation Tabs */}
<nav className="flex-1 space-y-1">
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/admin">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">dashboard</span>
<span className="font-label-sm text-label-sm">Dashboard</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 bg-primary-container text-on-primary-container rounded-lg font-bold group cursor-pointer" to="/ticket-pool">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform" style={{fontVariationSettings: "'FILL' 1"}}>confirmation_number</span>
<span className="font-label-sm text-label-sm">Ticket Pool</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/staff-allocation">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">group_add</span>
<span className="font-label-sm text-label-sm">Staff Allocation</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/insights">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">analytics</span>
<span className="font-label-sm text-label-sm">Citizen Insights</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/compliance">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">terminal</span>
<span className="font-label-sm text-label-sm">System Logs</span>
</Link>
</nav>
{/* Footer Tabs */}
<div className="mt-auto border-t border-outline-variant/10 pt-4 space-y-1">
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/explanations">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">help</span>
<span className="font-label-sm text-label-sm">Support</span>
</Link>
<Link className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary hover:bg-surface-variant rounded-lg hover:bg-surface-variant/50 transition-all duration-300 group cursor-pointer" to="/">
<span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">logout</span>
<span className="font-label-sm text-label-sm">Logout</span>
</Link>
</div>
</aside>
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
<p className="font-body-md text-body-md text-on-surface-variant mt-2 max-w-2xl">Manage and assign open civic reports. High priority pHash clusters require immediate allocation.</p>
</div>
{/* Filters */}
<div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
<div className="relative">
<select className="appearance-none bg-surface border border-outline-variant/50 rounded-lg py-2 pl-4 pr-10 font-label-sm text-label-sm text-on-surface focus:outline-none input-glow cursor-pointer">
<option>All Wards</option>
<option>Ward A (North)</option>
<option>Ward B (Central)</option>
</select>
<span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-outline text-sm">expand_more</span>
</div>
<div className="relative">
<select className="appearance-none bg-surface border border-outline-variant/50 rounded-lg py-2 pl-4 pr-10 font-label-sm text-label-sm text-on-surface focus:outline-none input-glow cursor-pointer">
<option>All Categories</option>
<option>Infrastructure</option>
<option>Sanitation</option>
</select>
<span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-outline text-sm">expand_more</span>
</div>
<div className="relative">
<select className="appearance-none bg-surface border border-outline-variant/50 rounded-lg py-2 pl-4 pr-10 font-label-sm text-label-sm text-on-surface focus:outline-none input-glow cursor-pointer">
<option>Status: Open</option>
<option>Status: Pending</option>
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
<div className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm p-4 hover:border-primary/30 transition-colors cursor-pointer group">
<div className="flex flex-col md:flex-row gap-6 items-start">
{/* Image Container */}
<div className="w-full md:w-64 h-40 bg-surface-container rounded-lg overflow-hidden shrink-0 relative">
<img className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" data-alt="A highly detailed, professional civic dashboard thumbnail image showing a flooded bridge structure in an urban setting. The water levels are high, submerging part of the concrete roadway. The style is a clean, modern civic photography approach, integrating with a sleek UI featuring a 'Sylvan Urbanity' aesthetic—dominantly warm beige and deep forest green tones. Bright, clear lighting emphasizes infrastructural damage over chaos, presenting an organized, high-trust digital interface for city officials." src="https://lh3.googleusercontent.com/aida-public/AB6AXuDVE9WN2ezxmr94MwWjpW1_FUMH5B2FM-i4IVkXE5tfmvKFHAq3wVuZ3MgUJTMj26bhRgNFBCAAtwmeLlAHUZJzhqJll3DoWcyWxFDKp1A5NfjpBQPNEZCEcv95EdOHKNp8gn2jYSKJjwfDsxjcJ_LQIH7CEqQIhzMX5FQWzC7REwv4wusfKRzU4lb-loIVdicWgKHI1V7Ko5b9WdBDYJo2IgXhqU-YYh06go0qQh4jUg6rrzHywyY"/>
</div>
{/* Content */}
<div className="flex-1 flex flex-col justify-between h-full space-y-4 py-1">
<div>
<div className="flex flex-wrap gap-2 mb-3">
<span className="bg-tertiary-fixed text-on-tertiary-fixed-variant px-2.5 py-1 rounded-full font-label-sm text-label-sm inline-flex items-center gap-1 border border-tertiary-fixed-dim/50">
<span className="material-symbols-outlined text-[14px]">merge</span>
                                        Merged: 12 Duplicates
                                    </span>
<span className="bg-error-container text-on-error-container px-2.5 py-1 rounded-full font-label-sm text-label-sm border border-error-container/50">
                                        Community Multiplier: High
                                    </span>
</div>
<h3 className="font-headline-lg text-headline-lg-mobile md:text-headline-lg text-on-surface mb-2">Godavari Bridge Flooding</h3>
<p className="font-body-md text-body-md text-on-surface-variant flex items-center gap-1">
<span className="material-symbols-outlined text-sm text-outline">location_on</span>
                                    Ward C, Near Riverside Promenade
                                </p>
</div>
<div className="flex justify-end mt-auto pt-4 border-t border-outline-variant/10">
<button className="bg-primary text-on-primary font-label-sm text-label-sm rounded-lg px-6 py-2.5 hover:bg-primary-container transition-colors shadow-sm flex items-center gap-2">
                                    Assess Cluster <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
</button>
</div>
</div>
</div>
</div>
</section>
{/* Data Table Section (Solid Surface) */}
<section className="bg-surface-container-lowest rounded-xl border border-outline-variant/20 shadow-sm overflow-hidden">
<div className="overflow-x-auto">
<table className="w-full text-left border-collapse">
<thead className="bg-surface-container-low/50 border-b border-outline-variant/20">
<tr>
<th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">ID</th>
<th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Visual Evidence</th>
<th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Location</th>
<th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Fuzzy Data Status</th>
<th className="py-4 px-6 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-semibold">Action</th>
</tr>
</thead>
<tbody className="divide-y divide-outline-variant/10">
{/* Row 1 */}
<tr className="hover:bg-surface-bright/50 transition-colors group">
<td className="py-4 px-6 font-body-md text-body-md text-on-surface font-medium">#TK-4092</td>
<td className="py-4 px-6">
<div className="w-16 h-12 rounded bg-surface-container overflow-hidden border border-outline-variant/20">
<img className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity" data-alt="A clear, well-lit civic reporting thumbnail photo displaying a significant pothole on an asphalt road in a residential neighborhood. The focus is sharp on the damaged pavement, surrounded by subtle, clean urban elements. The overall image color palette aligns with a modern civic application, utilizing neutral greys and subtle greens, conveying a sense of actionable, precise civic data collection designed for a professional dashboard environment." src="https://lh3.googleusercontent.com/aida-public/AB6AXuDveEIhaOKBkNVxBXRJxskagkvVMYxPG1DoRE8-gOvX2B7_PdPRMnFDOGQ7lqzc6JqW7CKKikMQd8OMz_yeJIUahWKX_QjLMRYkTQnBxBPfxW7iaae7UCx3foju_I85oDo0MNtDIqF2sLW6BjO4rClysNw8wAyFdbTCBjLjBCeC9d5Vfz_s-z58t9_15ynzUEj9xFP9xmuPfe7kvrWvDS74qerBlUXvlKTA1kNqyBFGKr8b8G8vMg8"/>
</div>
</td>
<td className="py-4 px-6">
<div className="font-body-md text-body-md text-on-surface">Sector 4, MG Road</div>
<div className="font-label-sm text-label-sm text-outline mt-0.5">Reported 2h ago</div>
</td>
<td className="py-4 px-6">
<div className="flex items-center gap-2 text-tertiary">
<span className="material-symbols-outlined text-[20px]" style={{fontVariationSettings: "'FILL' 1"}}>check_circle</span>
<span className="font-label-sm text-label-sm">Crisp Data</span>
</div>
</td>
<td className="py-4 px-6">
<button className="border border-primary text-primary font-label-sm text-label-sm rounded-lg px-4 py-2 hover:bg-primary-container/10 transition-colors whitespace-nowrap">
                                        Assign Scout
                                    </button>
</td>
</tr>
{/* Row 2 */}
<tr className="hover:bg-surface-bright/50 transition-colors group">
<td className="py-4 px-6 font-body-md text-body-md text-on-surface font-medium">#TK-4088</td>
<td className="py-4 px-6">
<div className="w-16 h-12 rounded bg-surface-container overflow-hidden border border-outline-variant/20">
<img className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity" data-alt="A high-resolution thumbnail image for a city management portal, depicting a large fallen tree branch partially blocking a clean, paved sidewalk next to a manicured urban green space. The lighting is bright daylight, highlighting the natural textures against the concrete. The visual tone is structured and informative, matching a 'Sylvan Urbanity' design system with integrated natural greens and warm, solid surface colors, avoiding any sense of disorder." src="https://lh3.googleusercontent.com/aida-public/AB6AXuCYN1TI5PJTAMHIdIHYqY-lv21WT_8TN7WN64HF_CEB0oWW0Nxy5v0DJbtO4f1yXgAdirCbYAA3mCcS1Q4BynomevQt6Jw4vbCyATXXnsDswJDqX-oyPU3ONcYH1dii_iTS6NYrUWmP8H6vFNzcYkKtbYka84HRdKAY_9BAS9GOTL1PHqcGKsFiDEDZq6v7J_L5S477LYkavVnWK4nQeZ6vVl2dfigyqBlK7byvfVdeyvhbUanDzK4"/>
</div>
</td>
<td className="py-4 px-6">
<div className="font-body-md text-body-md text-on-surface">Shivaji Park West</div>
<div className="font-label-sm text-label-sm text-outline mt-0.5">Reported 5h ago</div>
</td>
<td className="py-4 px-6">
<div className="flex items-center gap-2 text-[#9a6a16]"> {/* Manual override for amber warning tone needed by spec, as standard config lacks explicit warning color besides error */}
<span className="material-symbols-outlined text-[20px]" style={{fontVariationSettings: "'FILL' 1"}}>warning</span>
<span className="font-label-sm text-label-sm">Pending Scout Metrics</span>
</div>
</td>
<td className="py-4 px-6">
<button className="border border-primary text-primary font-label-sm text-label-sm rounded-lg px-4 py-2 hover:bg-primary-container/10 transition-colors whitespace-nowrap">
                                        Assign Scout
                                    </button>
</td>
</tr>
</tbody>
</table>
</div>
</section>
</div>
</main>

    </>
  );
}
