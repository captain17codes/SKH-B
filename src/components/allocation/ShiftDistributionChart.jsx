import React from 'react';

export default function ShiftDistributionChart() {
  const shifts = ['Morning', 'Afternoon', 'Evening', 'Night'];
  const heights = ['h-[80%]', 'h-[100%]', 'h-[60%]', 'h-[30%]'];

  return (
    <div className="bg-surface rounded-xl border border-surface-variant p-6 shadow-sm flex flex-col">
      <h2 className="text-xl font-bold text-on-surface mb-6">Shift Distribution</h2>
      <div className="flex-1 flex items-end gap-4 h-64 pt-10">
        {shifts.map((shift, idx) => (
          <div key={shift} className="flex flex-col items-center flex-1 gap-4 h-full justify-end">
            <div className={`w-full bg-primary/20 hover:bg-primary/40 rounded-t-lg relative transition-colors ${heights[idx]}`}>
              <div className="absolute top-0 w-full h-1 bg-primary rounded-t-lg"></div>
            </div>
            <span className="text-xs font-bold text-on-surface-variant">{shift}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
