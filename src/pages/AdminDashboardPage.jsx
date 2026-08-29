import React from 'react';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import StatCard from '../components/StatCard';
import Button from '../components/Button';
import LiveMapPanel from '../components/admin/LiveMapPanel';
import RecentActivityList from '../components/admin/RecentActivityList';

export default function AdminDashboardPage() {
  const stats = [
    { title: 'Total Active Projects', value: '24', icon: 'construction', trend: '12%', trendUp: true },
    { title: 'Open Grievances', value: '142', icon: 'report_problem', trend: '5%', trendUp: false },
    { title: 'Workforce Deployed', value: '856', icon: 'engineering', trend: '2%', trendUp: true },
    { title: 'Budget Utilized', value: '68%', icon: 'account_balance', trend: '8%', trendUp: true }
  ];

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <div className="flex flex-1 pt-20">
        <Sidebar />
        <main className="flex-1 p-6 lg:p-10 max-w-[1200px] overflow-x-hidden">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-on-surface">Admin Dashboard</h1>
              <p className="text-on-surface-variant">Kopargaon Smart City Overview</p>
            </div>
            <Button variant="primary" className="flex items-center gap-2 hidden md:flex">
              <span className="material-symbols-outlined text-[20px]">add</span> New Report
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {stats.map((stat, idx) => (
              <StatCard key={idx} {...stat} />
            ))}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">
            <LiveMapPanel />
            <RecentActivityList />
          </div>
        </main>
      </div>
    </div>
  );
}
