import React from 'react';

export default function LiveMapPanel() {
  return (
    <div className="xl:col-span-2 bg-surface rounded-xl border border-surface-variant p-6 shadow-sm">
      <h2 className="text-xl font-bold text-on-surface mb-6">Live City Map</h2>
      <div className="w-full h-[400px] bg-surface-container-high rounded-xl relative overflow-hidden border border-surface-variant">
        <img src="https://picsum.photos/seed/map/1200/800" alt="Map Placeholder" className="w-full h-full object-cover opacity-80" />
        <div className="absolute top-4 right-4 flex flex-col gap-2">
          <button className="w-10 h-10 bg-surface/90 rounded-lg shadow-sm flex items-center justify-center text-on-surface hover:bg-surface-variant transition-colors backdrop-blur-md"><span className="material-symbols-outlined">add</span></button>
          <button className="w-10 h-10 bg-surface/90 rounded-lg shadow-sm flex items-center justify-center text-on-surface hover:bg-surface-variant transition-colors backdrop-blur-md"><span className="material-symbols-outlined">remove</span></button>
          <button className="w-10 h-10 bg-surface/90 rounded-lg shadow-sm flex items-center justify-center text-on-surface hover:bg-surface-variant transition-colors backdrop-blur-md"><span className="material-symbols-outlined">layers</span></button>
        </div>
      </div>
    </div>
  );
}
