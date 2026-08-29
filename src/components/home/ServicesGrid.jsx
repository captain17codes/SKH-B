import React from 'react';

export default function ServicesGrid() {
  const services = [
    { title: 'Citizen Portal', icon: 'support_agent', desc: 'Submit grievances and track requests.' },
    { title: 'Resource Allocation', icon: 'engineering', desc: 'View active projects and workforce.' },
    { title: 'System Info', icon: 'data_info_alert', desc: 'Learn about Smart City infrastructure.' }
  ];

  return (
    <section className="py-20 px-6 max-w-[1280px] mx-auto">
      <div className="mb-12 text-center">
        <h2 className="text-3xl font-bold text-on-surface mb-4">Civic Services</h2>
        <p className="text-on-surface-variant max-w-2xl mx-auto">Access digital city services designed for residents, local businesses, and government officials.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {services.map((service, idx) => (
          <div key={idx} className="bg-surface p-8 rounded-xl border border-surface-variant hover:shadow-md transition-shadow group">
            <div className="w-14 h-14 bg-surface-container-high rounded-lg flex items-center justify-center text-primary mb-6 group-hover:bg-primary group-hover:text-white transition-colors">
              <span className="material-symbols-outlined text-[28px]">{service.icon}</span>
            </div>
            <h3 className="text-xl font-bold text-on-surface mb-2">{service.title}</h3>
            <p className="text-on-surface-variant">{service.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
