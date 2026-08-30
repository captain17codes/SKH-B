import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';

const points = [
  {
    icon: 'warning',
    title: 'The Problem',
    desc: 'Kopargaon municipality receives far more civic complaints than its limited budget and staff can handle at once.',
    highlight: 'Budget vs. Volume',
  },
  {
    icon: 'model_training',
    title: 'The Core Solution',
    desc: 'We built an AI-driven platform that abandons "first-come-first-serve" and intelligently decides what gets fixed first based on actual urgency.',
    highlight: 'Intelligent Prioritization',
  },
  {
    icon: 'blur_on',
    title: 'Handling Incomplete Data',
    desc: "It uses Fuzzy Logic to process vague citizen complaints, ensuring the system doesn't freeze when exact measurements are missing.",
    highlight: 'Fuzzy Logic',
  },
  {
    icon: 'gavel',
    title: 'Smart Rule Validation',
    desc: 'Officials set priority rules using AHP, while a mathematical CR Gate prevents them from entering illogical or contradictory priorities.',
    highlight: 'AHP & CR Gate',
  },
  {
    icon: 'sort',
    title: 'Mathematical Ranking',
    desc: 'The Fuzzy TOPSIS algorithm scores every issue, pushing life-threatening emergencies (like floods) above routine maintenance (like potholes).',
    highlight: 'Fuzzy TOPSIS',
  },
  {
    icon: 'backpack',
    title: 'Resource Optimization',
    desc: "The Knapsack algorithm acts as the manager, selecting the highest-priority tasks that perfectly fit into today's strict budget and workforce limits.",
    highlight: 'Knapsack Algorithm',
  },
  {
    icon: 'filter_b_and_w',
    title: 'Spam Prevention',
    desc: 'It uses image hashing to detect if multiple people uploaded photos of the exact same issue, merging them to avoid duplicate tickets.',
    highlight: 'Perceptual Hashing',
  },
  {
    icon: 'psychology',
    title: 'AI Transparency',
    desc: 'Using SHAP values, the system translates its complex math into simple English, explaining exactly why a specific issue was selected or delayed.',
    highlight: 'SHAP Values',
  },
  {
    icon: 'chat',
    title: 'Closing the Loop',
    desc: 'This AI-generated explanation is automatically sent to the citizen via WhatsApp, providing transparent governance instead of administrative silence.',
    highlight: 'Automated Feedback',
  },
  {
    icon: 'cloud_off',
    title: 'System Resilience',
    desc: 'If the database suddenly crashes, a "Blackout Mode" automatically catches incoming complaints in an offline queue so no citizen\'s alert is ever lost.',
    highlight: 'Blackout Mode',
  }
];

export default function ArchitecturePage() {
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="bg-background text-on-surface font-body-md antialiased min-h-screen flex flex-col">
      {/* TopNavBar */}
      <nav className="sticky top-0 w-full z-50 flex justify-between items-center px-margin-mobile md:px-margin-desktop py-4 bg-surface/80 backdrop-blur-md shadow-sm border-b border-outline-variant/20">
        <Link to="/" className="flex items-center gap-2 text-primary hover:text-primary-container transition-colors">
          <span className="material-symbols-outlined icon-filled text-3xl">location_city</span>
          <span className="font-headline-md text-headline-md font-bold">Kopargaon Smart City</span>
        </Link>
        <div className="flex items-center gap-4">
          <Link to="/" className="font-label-sm text-label-sm text-primary border border-primary px-6 py-2.5 rounded-full hover:bg-surface-container-low transition-colors duration-200 cursor-pointer">
            Back to Home
          </Link>
          <Link to="/submit" className="font-label-sm text-label-sm bg-primary text-on-primary px-6 py-2.5 rounded-full hover:bg-primary-container transition-colors duration-200 cursor-pointer hidden md:block">
            Report Issue
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-grow">
        <section className="relative py-20 px-margin-mobile md:px-margin-desktop overflow-hidden bg-surface-container-lowest">
          <div className="absolute inset-0 z-0">
            <div className="absolute inset-0 bg-gradient-to-br from-primary-container/20 to-surface-container-lowest"></div>
          </div>
          <div className="relative z-10 w-full max-w-4xl mx-auto text-center flex flex-col items-center">
            <span className="bg-primary/10 text-primary px-4 py-1.5 rounded-full font-label-sm uppercase tracking-widest mb-6 border border-primary/20">
              System Architecture
            </span>
            <h1 className="font-headline-display text-headline-display text-primary leading-tight mb-6">
              AI-Driven Civic Triage
            </h1>
            <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl">
              A comprehensive technical overview of the intelligent engine powering the Kopargaon Smart City platform. From raw citizen reports to optimized field assignments.
            </p>
          </div>
        </section>

        {/* Timeline Section */}
        <section className="w-full max-w-5xl mx-auto px-margin-mobile md:px-margin-desktop py-16 md:py-24">
          <div className="relative border-l border-primary/30 ml-4 md:ml-12 space-y-16">
            
            {points.map((point, idx) => (
              <div key={idx} className="relative pl-8 md:pl-16 group">
                {/* Timeline Node */}
                <div className="absolute -left-[18px] top-1 bg-surface-container-lowest border-2 border-primary w-9 h-9 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(42,92,62,0.4)] group-hover:scale-110 group-hover:bg-primary transition-all duration-300">
                  <span className="font-label-sm text-primary group-hover:text-on-primary font-bold">
                    {idx + 1}
                  </span>
                </div>
                
                {/* Content Card */}
                <div className="bg-surface rounded-2xl p-6 md:p-8 border border-outline-variant/30 shadow-sm hover:shadow-[0_15px_30px_rgba(0,0,0,0.1)] transition-all duration-300 transform group-hover:-translate-y-1 relative overflow-hidden">
                  
                  {/* Decorative background blur */}
                  <div className="absolute -right-20 -top-20 w-40 h-40 bg-primary/5 rounded-full blur-3xl group-hover:bg-primary/10 transition-colors duration-500"></div>

                  <div className="flex flex-col md:flex-row gap-6 relative z-10">
                    <div className="shrink-0 w-16 h-16 rounded-xl bg-primary-container/30 flex items-center justify-center text-primary border border-primary-container">
                      <span className="material-symbols-outlined text-3xl icon-filled">{point.icon}</span>
                    </div>
                    
                    <div>
                      <div className="flex flex-wrap gap-3 items-center mb-2">
                        <h3 className="font-headline-md text-headline-md text-on-surface">{point.title}</h3>
                        <span className="bg-tertiary-container/30 text-tertiary px-3 py-1 rounded-full font-label-sm text-xs border border-tertiary-container">
                          {point.highlight}
                        </span>
                      </div>
                      <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                        {point.desc}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}

          </div>
        </section>
      </main>

      {/* Simple Footer */}
      <footer className="w-full py-8 text-center border-t border-outline-variant/20 bg-surface-container-lowest">
        <p className="font-body-md text-on-surface-variant">© 2026 Kopargaon Smart City Hackathon Project</p>
      </footer>
    </div>
  );
}
