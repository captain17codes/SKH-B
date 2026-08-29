import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import HomePage from './pages/HomePage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import CitizenPortalPage from './pages/CitizenPortalPage';
import AllocationDashboardPage from './pages/AllocationDashboardPage';
import SystemExplanationsPage from './pages/SystemExplanationsPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/admin" element={<AdminDashboardPage />} />
        <Route path="/submit" element={<CitizenPortalPage />} />
        <Route path="/allocation" element={<AllocationDashboardPage />} />
        <Route path="/explanations" element={<SystemExplanationsPage />} />
      </Routes>
    </Router>
  );
}

export default App;
