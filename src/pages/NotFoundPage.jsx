import React from 'react';
import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="bg-background text-on-surface font-body-md antialiased min-h-screen flex flex-col items-center justify-center text-center px-4">
      <span className="material-symbols-outlined text-[80px] text-primary mb-6">error</span>
      <h1 className="font-headline-display text-headline-lg md:text-headline-display text-primary mb-4">404 - Page Not Found</h1>
      <p className="font-body-lg text-body-lg text-on-surface-variant max-w-md mb-8">
        The page you are looking for doesn't exist or has been moved.
      </p>
      <Link to="/" className="bg-primary text-on-primary font-label-sm text-label-sm px-8 py-4 rounded-full shadow-md hover:shadow-lg transition-all duration-300">
        Return to Home
      </Link>
    </div>
  );
}
