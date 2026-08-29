import React from 'react';

export default function Button({ children, variant = 'primary', className = '', ...props }) {
  const baseClasses = 'px-6 py-3 rounded-lg font-bold transition-all duration-300';
  const variants = {
    primary: 'bg-primary text-white hover:bg-primary-container shadow-sm hover:shadow-md',
    secondary: 'bg-surface border border-primary text-primary hover:bg-surface-dim',
    ghost: 'text-primary hover:bg-surface-variant'
  };

  return (
    <button className={`${baseClasses} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}
