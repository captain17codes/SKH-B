import React from 'react';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import FormSteps from '../components/portal/FormSteps';
import SubmissionForm from '../components/portal/SubmissionForm';
import RecentSubmissionsTable from '../components/portal/RecentSubmissionsTable';

export default function CitizenPortalPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <div className="flex flex-1 pt-20">
        <Sidebar />
        <main className="flex-1 p-6 lg:p-10 max-w-[1000px]">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-on-surface">Citizen Submission Portal</h1>
            <p className="text-on-surface-variant">Report issues and request city services</p>
          </div>

          <div className="bg-surface rounded-xl border border-surface-variant p-6 md:p-10 shadow-sm mb-8">
            <FormSteps />
            <SubmissionForm />
          </div>

          <RecentSubmissionsTable />
        </main>
      </div>
    </div>
  );
}
