import React from 'react';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import SystemModulesAccordion from '../components/explanations/SystemModulesAccordion';

export default function SystemExplanationsPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <div className="flex flex-1 pt-20">
        <Sidebar />
        <main className="flex-1 p-6 lg:p-10 max-w-[1000px]">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-on-surface">System Explanations</h1>
            <p className="text-on-surface-variant">Detailed breakdown of Smart City modules and technical architecture.</p>
          </div>
          <SystemModulesAccordion />
        </main>
      </div>
    </div>
  );
}
