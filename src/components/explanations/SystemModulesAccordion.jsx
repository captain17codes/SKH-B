import React, { useState } from 'react';

export default function SystemModulesAccordion() {
  const [activeIdx, setActiveIdx] = useState(0);

  const modules = [
    { title: 'IoT Sensor Network', icon: 'sensors', desc: 'Overview of environmental and traffic sensors deployed across the city grid.' },
    { title: 'Smart Grid Analytics', icon: 'power', desc: 'Power consumption patterns and renewable energy distribution metrics.' },
    { title: 'Water Management', icon: 'water_drop', desc: 'Real-time monitoring of reservoir levels and pipeline integrity.' },
    { title: 'Automated Waste Collection', icon: 'delete', desc: 'Route optimization and bin capacity sensing algorithms.' }
  ];

  return (
    <div className="flex flex-col gap-4">
      {modules.map((mod, idx) => {
        const isActive = activeIdx === idx;
        return (
          <div key={idx} className={`bg-surface rounded-xl border transition-all ${isActive ? 'border-primary shadow-md' : 'border-surface-variant shadow-sm hover:border-primary/50'}`}>
            <div 
              className="p-6 flex items-start gap-4 cursor-pointer"
              onClick={() => setActiveIdx(idx)}
            >
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center shrink-0 ${isActive ? 'bg-primary text-white' : 'bg-surface-container-high text-primary'}`}>
                <span className="material-symbols-outlined">{mod.icon}</span>
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold text-on-surface mb-2">{mod.title}</h3>
                <p className="text-on-surface-variant">{mod.desc}</p>
                
                {isActive && (
                  <div className="mt-6 pt-6 border-t border-surface-variant animate-in slide-in-from-top-2 fade-in duration-300">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="bg-background rounded-lg p-4 border border-surface-variant">
                        <h4 className="text-sm font-bold font-label text-on-surface-variant uppercase tracking-wider mb-2">Protocol</h4>
                        <p className="font-bold text-on-surface">LoRaWAN / MQTT</p>
                      </div>
                      <div className="bg-background rounded-lg p-4 border border-surface-variant">
                        <h4 className="text-sm font-bold font-label text-on-surface-variant uppercase tracking-wider mb-2">Active Nodes</h4>
                        <p className="font-bold text-on-surface text-primary">1,245 online</p>
                      </div>
                    </div>
                    <p className="mt-6 text-sm text-on-surface-variant leading-relaxed">
                      The sensor network utilizes low-power wide-area networking protocols to transmit telemetry data every 15 minutes. Data is ingested into our central data lake where anomaly detection models flag irregularities in real-time.
                    </p>
                  </div>
                )}
              </div>
              <span className="material-symbols-outlined text-on-surface-variant">
                {isActive ? 'expand_less' : 'expand_more'}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
