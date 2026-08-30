import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import HomePage from './pages/HomePage';
import CitizenPortalPage from './pages/CitizenPortalPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import AllocationDashboardPage from './pages/AllocationDashboardPage';
import SystemExplanationsPage from './pages/SystemExplanationsPage';
import TicketPoolPage from './pages/TicketPoolPage';
import CitizenInsightsPage from './pages/CitizenInsightsPage';
import CitizenInsightsEquityPage from './pages/CitizenInsightsEquityPage';
import StaffAllocationPage from './pages/StaffAllocationPage';
import CompliancePage from './pages/CompliancePage';
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/submit" element={<CitizenPortalPage />} />
        <Route path="/admin" element={<AdminDashboardPage />} />
        <Route path="/allocation" element={<AllocationDashboardPage />} />
        <Route path="/explanations" element={<SystemExplanationsPage />} />
        <Route path="/ticket-pool" element={<TicketPoolPage />} />
        <Route path="/insights" element={<CitizenInsightsPage />} />
        <Route path="/citizen-insights" element={<CitizenInsightsEquityPage />} />
        <Route path="/staff-allocation" element={<StaffAllocationPage />} />
        <Route path="/compliance" element={<CompliancePage />} />
      </Routes>
    </Router>
  );
}

export default App;
