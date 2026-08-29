import React from 'react';
import Navbar from '../components/Navbar';
import HeroSection from '../components/home/HeroSection';
import ServicesGrid from '../components/home/ServicesGrid';
import CityProjectsSection from '../components/home/CityProjectsSection';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <HeroSection />
      <ServicesGrid />
      <CityProjectsSection />
    </div>
  );
}
