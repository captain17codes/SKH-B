import React from 'react';

export default function CategorySelector() {
  const categories = [
    { icon: 'water_drop', name: 'Water' },
    { icon: 'electric_bolt', name: 'Electricity' },
    { icon: 'delete', name: 'Waste' },
    { icon: 'add_road', name: 'Roads' }
  ];

  return (
    <div>
      <h3 className="text-xl font-bold text-on-surface mb-6">Select Category</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {categories.map((cat, idx) => (
          <div key={cat.name} className={`p-4 rounded-xl border cursor-pointer flex flex-col items-center gap-3 transition-all ${idx === 0 ? 'border-primary bg-primary/5 text-primary' : 'border-surface-variant bg-surface hover:bg-surface-variant text-on-surface-variant'}`}>
            <span className="material-symbols-outlined text-[32px]">{cat.icon}</span>
            <span className="font-bold text-sm">{cat.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
