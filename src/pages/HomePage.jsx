import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import SystemSummaryBlock from '../components/SystemSummaryBlock';

export default function HomePage() {
  const navigate = useNavigate();
  const [modalState, setModalState] = useState({ isOpen: false, type: 'signin', role: 'resident' });

  const openModal = (type, role = 'resident') => setModalState({ isOpen: true, type, role });
  const closeModal = () => setModalState({ ...modalState, isOpen: false });

  const handleAuthSubmit = (e) => {
    e.preventDefault();
    if (modalState.role === 'admin') navigate('/admin');
    else navigate('/submit');
  };

  return (
    <div className="bg-background text-on-surface font-body-md antialiased min-h-screen flex flex-col">
      {/* TopNavBar */}
      <nav className="fixed top-0 w-full z-50 flex justify-between items-center px-margin-mobile md:px-margin-desktop py-4 max-w-container-max mx-auto bg-surface/80 backdrop-blur-md shadow-sm">
        <div className="flex items-center gap-2 text-primary">
          <span className="material-symbols-outlined icon-filled text-3xl">location_city</span>
          <span className="font-headline-md text-headline-md font-bold">Kopargaon Smart City</span>
        </div>
        <div className="hidden md:flex items-center gap-8">
          <Link className="font-body-md text-body-md text-primary font-bold border-b-2 border-primary hover:text-primary transition-colors duration-200" to="/">About</Link>
          <Link className="font-body-md text-body-md text-on-surface-variant hover:text-primary transition-colors duration-200" to="/">Contact</Link>
          <Link className="font-body-md text-body-md text-on-surface-variant hover:text-primary transition-colors duration-200" to="/">Features</Link>
        </div>
        <div className="hidden md:flex items-center gap-4">
          <button onClick={() => openModal('signin')} className="font-label-sm text-label-sm text-primary border border-primary px-6 py-2.5 rounded-full hover:bg-surface-container-low transition-colors duration-200 cursor-pointer">Sign In</button>
          <button onClick={() => openModal('signup')} className="font-label-sm text-label-sm bg-primary text-on-primary px-6 py-2.5 rounded-full hover:bg-primary-container transition-colors duration-200 cursor-pointer">Sign Up</button>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-grow pt-24 md:pt-32">
        <section className="relative min-h-[80vh] flex items-center mb-24">
          <div className="absolute inset-0 z-0">
            <img alt="Forest Road Background" className="w-full h-full object-cover opacity-30 mix-blend-multiply filter contrast-125 saturate-50" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBqBsDKxKvsLAMWb7K_gxawH65u-Ix0t3IZtPH6K3rkbWPZDFv0zBTLzJ5L03FKHBqGZrHSZ1JdSykSuywT9ffwqq6vRI4-xvwcnY1yTZ36HNa5G_iq5NbpPRhlpPauEUYztoM36oJfjMk3kXVJyGEfftM8ePWRUIiBUbbdAgF21BySOkYAGiGiIlN5Mi9MVGLOWRAuyoUIbCNLRqM_2uO58H_p3L-g-ku-v6ObgFsiiije6RmWIsKsGA5yWcd4-_22" />
            <div className="absolute inset-0 bg-gradient-to-b from-surface/60 via-surface/80 to-background"></div>
          </div>
          <div className="relative z-10 w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div className="flex flex-col gap-6">
              <h1 className="font-headline-display text-headline-display text-primary max-w-lg leading-tight">
                Your Digital Gateway to a Smarter Kopargaon
              </h1>
              <p className="font-body-lg text-body-lg text-on-surface-variant max-w-md">
                A unified platform to report civic issues, track municipal project progress, and access essential smart city services seamlessly.
              </p>
              <blockquote className="border-l-4 border-tertiary-fixed pl-4 my-4 font-body-md italic text-primary-container">
                "Where tradition meets technology in the heart of nature."
              </blockquote>
              <div className="flex flex-col sm:flex-row gap-4 mt-4">
                <Link to="/submit" className="bg-primary text-on-primary font-label-sm text-label-sm px-8 py-4 rounded-full shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300 text-center">
                  Report an Issue
                </Link>
                <Link to="/admin" className="border border-primary text-primary font-label-sm text-label-sm px-8 py-4 rounded-full hover:bg-surface-container-low transition-colors duration-300 text-center">
                  View City Projects
                </Link>
              </div>
            </div>
            <div className="relative rounded-2xl overflow-hidden shadow-[0_10px_20px_rgba(22,52,34,0.05)] border border-outline-variant/30 backdrop-blur-sm bg-white/40 p-2">
              <img className="w-full h-auto rounded-xl object-cover aspect-[4/3]" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCMolb2k_jX5E98CxU8N810tI4gqIsvDJFrAGIXdDYghRrQ6JYZ8xWcPRhnCIFxo6xjViqnUEjsayqOqFY1FMI5p9Oaed9xRmi3I6Iws43zyw3m1NWZbpyiPSqZ3ZYzuXhf71O3SVhp1nW0XaDXw9dDu1jewDBapf23W_736l9rZvfG8gmzZkqVE5GII9QP3NUsIwZT2-dQFi-WgqoB0U8iLwaXgoG1OB_zSc9wA5kYn5KnJLSsG3w" alt="Kopargaon City" />
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop mb-24">
          <SystemSummaryBlock />
        </section>

        {/* Create Account Section */}
        <section className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-16 mb-24">
          <div className="text-center mb-16">
            <h2 className="font-headline-display text-headline-lg md:text-headline-display text-primary mb-4">Create an Account</h2>
            <p className="font-body-lg text-body-lg text-on-surface-variant">Select your role to join the smart city initiative.</p>
          </div>
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2 max-w-4xl mx-auto">
            <div className="bg-surface rounded-2xl p-8 border border-outline-variant/30 hover:shadow-[0_10px_20px_rgba(22,52,34,0.05)] transition-shadow duration-300 flex flex-col items-center text-center h-full">
              <div className="w-16 h-16 rounded-full bg-surface-container-highest flex items-center justify-center text-primary mb-6">
                <span className="material-symbols-outlined text-3xl">person</span>
              </div>
              <h3 className="font-headline-md text-headline-md text-primary mb-4">Resident Sign Up</h3>
              <p className="font-body-md text-body-md text-on-surface-variant mb-8 flex-grow">Report issues, pay utility bills, and access local municipal services.</p>
              <button onClick={() => openModal('signup', 'resident')} className="block w-full border border-primary text-primary font-label-sm text-label-sm px-6 py-3 rounded-full hover:bg-primary hover:text-on-primary transition-colors duration-300 text-center cursor-pointer">
                Register as Resident
              </button>
            </div>
            <div className="bg-surface rounded-2xl p-8 border border-outline-variant/30 hover:shadow-[0_10px_20px_rgba(22,52,34,0.05)] transition-shadow duration-300 flex flex-col items-center text-center h-full">
              <div className="w-16 h-16 rounded-full bg-surface-container-highest flex items-center justify-center text-primary mb-6">
                <span className="material-symbols-outlined text-3xl">shield_person</span>
              </div>
              <h3 className="font-headline-md text-headline-md text-primary mb-4">Administrator Sign Up</h3>
              <p className="font-body-md text-body-md text-on-surface-variant mb-8 flex-grow">For municipal officials to track projects and resolve citizen reports.</p>
              <button onClick={() => openModal('signup', 'admin')} className="block w-full border border-primary text-primary font-label-sm text-label-sm px-6 py-3 rounded-full hover:bg-primary hover:text-on-primary transition-colors duration-300 text-center cursor-pointer">
                Request Admin Access
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="w-full py-16 px-margin-mobile md:px-margin-desktop grid grid-cols-1 md:grid-cols-2 gap-8 border-t border-outline-variant bg-surface-container">
        <div className="flex flex-col gap-4">
          <div className="font-headline-md font-bold text-primary flex items-center gap-2">
            <span className="material-symbols-outlined icon-filled">location_city</span>
            Kopargaon Smart City
          </div>
          <p className="font-body-md text-body-md text-on-surface max-w-sm mt-4">
            © 2026 Kopargaon Smart City. Towards Sustainable Governance.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
          <div className="flex flex-col gap-3">
            <h4 className="font-label-sm text-label-sm text-primary font-bold uppercase tracking-wider mb-2">Quick Links</h4>
            <Link className="font-body-md text-body-md text-on-surface-variant hover:underline decoration-primary transition-all" to="/">About Smart City</Link>
            <Link className="font-body-md text-body-md text-on-surface-variant hover:underline decoration-primary transition-all" to="/">Citizen Charter</Link>
            <Link className="font-body-md text-body-md text-on-surface-variant hover:underline decoration-primary transition-all" to="/">Contact Us</Link>
          </div>
          <div className="flex flex-col gap-3">
            <h4 className="font-label-sm text-label-sm text-primary font-bold uppercase tracking-wider mb-2">Support</h4>
            <Link className="font-body-md text-body-md text-on-surface-variant hover:underline decoration-primary transition-all" to="/">Support Resources</Link>
          </div>
        </div>
      </footer>
      {/* Auth Modal */}
      {modalState.isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-surface rounded-2xl p-8 max-w-md w-full relative shadow-lg border border-outline-variant/30">
            <button onClick={closeModal} className="absolute top-4 right-4 text-on-surface-variant hover:text-primary cursor-pointer">
              <span className="material-symbols-outlined">close</span>
            </button>
            <h2 className="font-headline-md text-primary mb-6 text-center">
              {modalState.type === 'signin' ? 'Sign In' : 'Create Account'}
            </h2>
            <form onSubmit={handleAuthSubmit} className="flex flex-col gap-4">
              <div>
                <label className="font-label-sm text-on-surface-variant mb-1 block">Role</label>
                <select 
                  className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-primary"
                  value={modalState.role} 
                  onChange={(e) => setModalState({...modalState, role: e.target.value})}
                >
                  <option value="resident">Resident / Citizen</option>
                  <option value="admin">Administrator / Staff</option>
                </select>
              </div>
              <div>
                <label className="font-label-sm text-on-surface-variant mb-1 block">Email</label>
                <input required type="email" placeholder="Enter your email" className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-primary" />
              </div>
              <div>
                <label className="font-label-sm text-on-surface-variant mb-1 block">Password</label>
                <input required type="password" placeholder="Enter your password" className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-primary" />
              </div>
              <button type="submit" className="w-full bg-primary text-on-primary font-bold py-3 rounded-full mt-4 hover:bg-primary-container transition-colors cursor-pointer">
                {modalState.type === 'signin' ? 'Sign In' : 'Register'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
