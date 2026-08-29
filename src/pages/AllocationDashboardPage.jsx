import React from 'react';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import StatCard from '../components/StatCard';
import DepartmentAllocationList from '../components/allocation/DepartmentAllocationList';
import ShiftDistributionChart from '../components/allocation/ShiftDistributionChart';

export default function AllocationDashboardPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <div className="flex flex-1 pt-20">
        <Sidebar />
        <main className="flex-1 p-6 lg:p-10 max-w-[1200px]">
          <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
            <div>
              <h1 className="text-3xl font-bold text-on-surface">Daily Allocation</h1>
              <p className="text-on-surface-variant">Resource & Workforce Management</p>
            </div>
            <div className="flex items-center gap-4 bg-surface border border-surface-variant p-2 rounded-lg">
              <span className="material-symbols-outlined text-on-surface-variant pl-2">calendar_today</span>
              <span className="font-bold text-on-surface pr-4">August 29, 2026</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <StatCard title="Total Workforce" value="980" icon="groups" />
            <StatCard title="Active Vehicles" value="142" icon="local_shipping" trend="12" trendUp={true} />
            <StatCard title="Budget Expended" value="$45.2k" icon="payments" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <DepartmentAllocationList />
            <ShiftDistributionChart />
          </div>
        </main>
      </div>
    </div>
  );
}
