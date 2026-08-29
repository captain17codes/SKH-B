import React from 'react';
import Button from '../Button';

export default function HeroSection() {
  return (
    <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden px-6">
      <div className="absolute inset-0 z-0">
        <img src="https://picsum.photos/seed/smartcity/1920/1080" alt="Kopargaon" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-surface/80 dark:bg-surface/90 backdrop-blur-sm"></div>
      </div>
      
      <div className="relative z-10 max-w-[1280px] mx-auto text-center flex flex-col items-center">
        <span className="px-4 py-1.5 rounded-full bg-primary-container/20 text-primary font-bold text-sm mb-6 border border-primary/20 backdrop-blur-md">
          Welcome to the future of urban living
        </span>
        <h1 className="text-5xl lg:text-7xl font-bold font-headline-display text-on-surface mb-6 max-w-4xl tracking-tight">
          Verdant Aesthetic <br className="hidden lg:block"/> Web Portal
        </h1>
        <p className="text-lg lg:text-xl text-on-surface-variant max-w-2xl mb-10">
          A harmonious blend of organic nature and civic precision. Empowering Kopargaon residents with transparent, efficient, and accessible government services.
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <Button variant="primary" className="flex items-center justify-center gap-2">
            Explore Services
            <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
          </Button>
          <Button variant="secondary">View Projects</Button>
        </div>
      </div>
    </section>
  );
}
