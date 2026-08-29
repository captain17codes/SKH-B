import React, { useState, useEffect } from 'react';
import client from '../api/client';

export default function SystemSummaryBlock() {
  const [data, setData] = useState({
    resolvedTickets: 0,
    activeTickets: 0,
    wardCount: 0,
    wardPopulationEntered: false,
    loading: true
  });

  useEffect(() => {
    async function fetchData() {
      try {
        const [todayRes, listRes, wardsRes] = await Promise.all([
          client.triage.getToday().catch(() => null),
          client.tickets.list({ limit: 1000 }).catch(() => ({ tickets: [] })),
          client.tickets.wards().catch(() => ({ wards: [], coverage: {} }))
        ]);

        const tickets = listRes?.tickets || [];
        const resolved = tickets.filter(t => t.status === 'resolved' || t.status === 'completed').length;
        const active = tickets.filter(t => t.status === 'scheduled' || t.status === 'in_progress').length;
        
        const coverage = wardsRes?.coverage || {};

        setData({
          resolvedTickets: resolved,
          activeTickets: active,
          wardCount: coverage.ward_count || 0,
          wardPopulationEntered: coverage.with_population_and_area > 0,
          loading: false
        });
      } catch (err) {
        console.error("Failed to fetch summary data", err);
        setData(prev => ({ ...prev, loading: false }));
      }
    }
    fetchData();
  }, []);

  if (data.loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-8 opacity-50 animate-pulse bg-surface-container-low/50 rounded-2xl p-8 border border-outline-variant/20">
        <div className="h-16 bg-outline-variant/20 rounded"></div>
        <div className="h-16 bg-outline-variant/20 rounded"></div>
        <div className="h-16 bg-outline-variant/20 rounded"></div>
        <div className="h-16 bg-outline-variant/20 rounded"></div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-8 divide-y md:divide-y-0 md:divide-x divide-outline-variant/30 bg-surface-container-low/50 rounded-2xl border border-outline-variant/20 py-8 px-6">
      
      <div className="flex flex-col items-center text-center px-4 gap-3">
        <div className="w-12 h-12 rounded-full bg-tertiary-fixed flex items-center justify-center text-tertiary mb-1">
          <span className="material-symbols-outlined icon-filled text-2xl">check_circle</span>
        </div>
        <h3 className="font-headline-lg text-primary">{data.resolvedTickets}</h3>
        <p className="font-body-md text-on-surface-variant">Resolved Complaints</p>
      </div>
      
      <div className="flex flex-col items-center text-center px-4 gap-3">
        <div className="w-12 h-12 rounded-full bg-primary-fixed flex items-center justify-center text-primary-container mb-1">
          <span className="material-symbols-outlined icon-filled text-2xl">construction</span>
        </div>
        <h3 className="font-headline-lg text-primary">{data.activeTickets}</h3>
        <p className="font-body-md text-on-surface-variant">Active Operations</p>
      </div>
      
      <div className="flex flex-col items-center text-center px-4 gap-3">
        <div className="w-12 h-12 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container mb-1">
          <span className="material-symbols-outlined icon-filled text-2xl">map</span>
        </div>
        <h3 className="font-headline-lg text-primary">{data.wardCount}</h3>
        <p className="font-body-md text-on-surface-variant">Wards Tracked</p>
      </div>

      <div className="flex flex-col items-center text-center px-4 gap-3">
        <div className="w-12 h-12 rounded-full bg-error-container flex items-center justify-center text-on-error-container mb-1">
          <span className="material-symbols-outlined icon-filled text-2xl">groups</span>
        </div>
        <h3 className="font-headline-sm text-primary mt-2">
          {data.wardPopulationEntered ? "Verified" : "Not entered"}
        </h3>
        <p className="font-body-sm text-on-surface-variant text-xs mt-1">Ward Population Data</p>
      </div>
      
    </div>
  );
}
