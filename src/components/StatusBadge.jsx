import React from 'react';

export default function StatusBadge({ status }) {
  const normalizedStatus = status.toLowerCase();
  
  let bg = 'bg-surface-variant';
  let text = 'text-on-surface-variant';
  
  if (normalizedStatus.includes('progress') || normalizedStatus.includes('ongoing')) {
    bg = 'bg-[#fff8e1] dark:bg-[#fff8e1]/10';
    text = 'text-[#f57f17] dark:text-[#f57f17]';
  } else if (normalizedStatus.includes('complet') || normalizedStatus.includes('approved')) {
    bg = 'bg-tertiary-fixed';
    text = 'text-on-tertiary-fixed';
  } else if (normalizedStatus.includes('delay') || normalizedStatus.includes('critical')) {
    bg = 'bg-error-container';
    text = 'text-on-error-container';
  }

  return (
    <span className={`px-3 py-1 rounded-full text-xs font-bold font-label ${bg} ${text} inline-flex items-center justify-center whitespace-nowrap`}>
      {status}
    </span>
  );
}
