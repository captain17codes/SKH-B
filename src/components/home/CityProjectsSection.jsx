import React from 'react';
import Button from '../Button';
import StatusBadge from '../StatusBadge';

export default function CityProjectsSection() {
  const projects = [
    { name: 'Downtown Traffic Lights Upgrade', status: 'In Progress', progress: 65 },
    { name: 'Godavari Riverfront Cleanup', status: 'Completed', progress: 100 },
    { name: 'Smart Water Metering', status: 'Delayed', progress: 30 }
  ];

  return (
    <section className="py-20 px-6 max-w-[1280px] mx-auto border-t border-surface-variant">
      <div className="flex justify-between items-end mb-12">
        <div>
          <h2 className="text-3xl font-bold text-on-surface mb-4">City Projects</h2>
          <p className="text-on-surface-variant max-w-2xl">Track the progress of ongoing infrastructure and community initiatives.</p>
        </div>
        <Button variant="ghost" className="hidden md:flex items-center gap-2">
          View All <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
        </Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {projects.map((project, idx) => (
          <div key={idx} className="bg-surface rounded-xl border border-surface-variant overflow-hidden flex flex-col">
            <div className="h-40 bg-surface-container-high relative">
              <img src={`https://picsum.photos/seed/proj${idx}/600/400`} alt="Project" className="w-full h-full object-cover" />
              <div className="absolute top-4 right-4 backdrop-blur-md">
                <StatusBadge status={project.status} />
              </div>
            </div>
            <div className="p-6 flex-grow flex flex-col justify-between">
              <div>
                <h3 className="text-lg font-bold text-on-surface mb-4">{project.name}</h3>
              </div>
              <div>
                <div className="flex justify-between text-sm font-bold font-label mb-2 text-on-surface-variant">
                  <span>Progress</span>
                  <span>{project.progress}%</span>
                </div>
                <div className="w-full bg-surface-variant rounded-full h-2">
                  <div className="bg-primary h-2 rounded-full transition-all duration-1000" style={{width: `${project.progress}%`}}></div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
