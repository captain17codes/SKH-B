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
          client.tickets.list({ limit: 100 }).catch(() => ({ tickets: [] })),
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
      <div className="py-16 bg-surface-container-low/50 rounded-[2rem] border border-outline-variant/20">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 opacity-50 animate-pulse px-6">
          <div className="h-32 bg-outline-variant/20 rounded-xl"></div>
          <div className="h-32 bg-outline-variant/20 rounded-xl"></div>
          <div className="h-32 bg-outline-variant/20 rounded-xl"></div>
          <div className="h-32 bg-outline-variant/20 rounded-xl"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="py-16 bg-surface-container-low/50 rounded-[2rem] border border-outline-variant/20">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-12 divide-y md:divide-y-0 md:divide-x divide-outline-variant/30">
        
        <div className="flex flex-col items-center text-center p-6 gap-4">
          <div className="w-16 h-16 rounded-full bg-tertiary-fixed flex items-center justify-center text-tertiary">
            <span className="material-symbols-outlined icon-filled text-3xl">check_circle</span>
          </div>
          <h3 className="font-headline-lg text-headline-lg text-primary">{data.resolvedTickets}</h3>
          <p className="font-body-md text-body-md text-on-surface-variant">Resolved Complaints</p>
        </div>
        
        <div className="flex flex-col items-center text-center p-6 gap-4">
          <div className="w-16 h-16 rounded-full bg-primary-fixed flex items-center justify-center text-primary-container">
            <span className="material-symbols-outlined icon-filled text-3xl">construction</span>
          </div>
          <h3 className="font-headline-lg text-headline-lg text-primary">{data.activeTickets}</h3>
          <p className="font-body-md text-body-md text-on-surface-variant">Active Operations</p>
        </div>
        
        <div className="flex flex-col items-center text-center p-6 gap-4">
          <div className="w-16 h-16 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container">
            <span className="material-symbols-outlined icon-filled text-3xl">map</span>
          </div>
          <h3 className="font-headline-lg text-headline-lg text-primary">{data.wardCount}</h3>
          <p className="font-body-md text-body-md text-on-surface-variant">Wards Covered</p>
        </div>

        <div className="flex flex-col items-center text-center p-6 gap-4">
          <div className="w-16 h-16 rounded-full bg-error-container flex items-center justify-center text-on-error-container">
            <span className="material-symbols-outlined icon-filled text-3xl">groups</span>
          </div>
          <h3 className="font-headline-lg text-headline-lg text-primary">
            {data.wardPopulationEntered ? "Verified" : "Not entered"}
          </h3>
          <p className="font-body-md text-body-md text-on-surface-variant">Ward Population</p>
        </div>
        
      </div>
    </div>
  );
}
