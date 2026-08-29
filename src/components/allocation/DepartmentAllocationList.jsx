import React from 'react';

export default function DepartmentAllocationList() {
  const departments = [
    { name: 'Public Works', allocated: 450, total: 500 },
    { name: 'Sanitation', allocated: 210, total: 250 },
    { name: 'Traffic Police', allocated: 120, total: 150 },
    { name: 'Parks & Rec', allocated: 45, total: 80 }
  ];

  return (
    <div className="bg-surface rounded-xl border border-surface-variant p-6 shadow-sm">
      <h2 className="text-xl font-bold text-on-surface mb-6">Department Allocation</h2>
      <div className="flex flex-col gap-6">
        {departments.map(dept => {
          const percentage = Math.round((dept.allocated / dept.total) * 100);
          return (
            <div key={dept.name}>
              <div className="flex justify-between font-bold text-sm mb-2">
                <span className="text-on-surface">{dept.name}</span>
                <span className="text-on-surface-variant">{dept.allocated} / {dept.total}</span>
              </div>
              <div className="w-full bg-surface-variant rounded-full h-3">
                <div 
                  className="bg-primary h-3 rounded-full transition-all duration-1000" 
                  style={{width: `${percentage}%`}}
                ></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
