import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';

import HomePage from './pages/HomePage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import CitizenPortalPage from './pages/CitizenPortalPage';
import AllocationDashboardPage from './pages/AllocationDashboardPage';
import SystemExplanationsPage from './pages/SystemExplanationsPage';

function App() {
  return (
    <ThemeProvider>
      <Router>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/admin" element={<AdminDashboardPage />} />
          <Route path="/submit" element={<CitizenPortalPage />} />
          <Route path="/allocation" element={<AllocationDashboardPage />} />
          <Route path="/explanations" element={<SystemExplanationsPage />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;
