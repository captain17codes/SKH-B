/**
 * Citizen Portal Page - Block 2 (Assistant 1)
 * Entry point for citizens to report civic issues
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import TicketForm from '../components/TicketForm';

export default function CitizenPortalPage() {
  const navigate = useNavigate();

  const handleTicketSuccess = (result) => {
    navigate(`/insights?ticketId=${result.id}&ref_no=${result.ref_no || ''}&dup=${result.is_duplicate || false}`);
  };

  return (
    <div className="bg-surface text-on-surface font-body-md min-h-screen relative">
      {/* Header */}
      <div className="bg-primary text-on-primary py-6">
        <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-4xl">location_city</span>
            <div>
              <h1 className="text-headline-md font-headline-md font-bold">Kopargaon Municipal Council</h1>
              <p className="text-body-md opacity-90">Civic Resource Prioritization Platform</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8">
        <div className="max-w-2xl mx-auto">
          <TicketForm onSuccess={handleTicketSuccess} />

          {/* Info Section */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-surface-container-low rounded-lg p-4 text-center">
              <span className="material-symbols-outlined text-3xl text-primary mb-2">speed</span>
              <h3 className="font-bold text-sm">AI-Powered Triage</h3>
              <p className="text-xs text-on-surface-variant mt-1">Issues prioritized using Fuzzy TOPSIS</p>
            </div>
            <div className="bg-surface-container-low rounded-lg p-4 text-center">
              <span className="material-symbols-outlined text-3xl text-primary mb-2">chat</span>
              <h3 className="font-bold text-sm">WhatsApp Updates</h3>
              <p className="text-xs text-on-surface-variant mt-1">Track status on your phone</p>
            </div>
            <div className="bg-surface-container-low rounded-lg p-4 text-center">
              <span className="material-symbols-outlined text-3xl text-primary mb-2">verified</span>
              <h3 className="font-bold text-sm">RTS Compliant</h3>
              <p className="text-xs text-on-surface-variant mt-1">Maharashtra Right to Services Act</p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-surface-container border-t border-outline-variant mt-12 py-6">
        <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop text-center">
          <p className="text-sm text-on-surface-variant">
            © 2026 Kopargaon Municipal Council | Class 'B' Local Body, Ahilyanagar District
          </p>
          <p className="text-xs text-on-surface-variant mt-2">
            Questions? Contact: kopargaon.municipal@maharashtra.gov.in
          </p>
        </div>
      </footer>
    </div>
  );
}
