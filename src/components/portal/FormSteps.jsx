import React from 'react';

export default function FormSteps() {
  return (
    <div className="flex items-center justify-between mb-10">
      {['Category', 'Details', 'Location', 'Submit'].map((step, idx) => (
        <div key={step} className="flex flex-col items-center gap-2 relative z-10 w-1/4">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-colors ${idx === 0 ? 'bg-primary text-white' : 'bg-surface-variant text-on-surface-variant'}`}>
            {idx + 1}
          </div>
          <span className="text-xs font-bold font-label text-on-surface-variant hidden md:block">{step}</span>
        </div>
      ))}
    </div>
  );
}
