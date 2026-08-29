import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

export default function Navbar() {
  const { theme, toggleTheme } = useTheme();
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav className={`fixed top-0 w-full z-50 transition-all duration-300 ${scrolled || location.pathname !== '/' ? 'bg-surface/90 backdrop-blur-xl border-b border-surface-variant shadow-sm' : 'bg-transparent'}`}>
      <div className="max-w-[1280px] mx-auto px-6 h-20 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-white transform transition-transform group-hover:scale-105">
            <span className="material-symbols-outlined">eco</span>
          </div>
          <div>
            <h1 className={`font-bold text-lg leading-tight ${scrolled || theme === 'dark' || location.pathname !== '/' ? 'text-on-surface' : 'text-on-surface lg:text-white'}`}>Kopargaon</h1>
            <p className={`text-xs font-semibold tracking-wider ${scrolled || theme === 'dark' || location.pathname !== '/' ? 'text-primary' : 'text-primary lg:text-primary-fixed'}`}>SMART CITY</p>
          </div>
        </Link>
        
        <div className="flex items-center gap-4 md:gap-6">
          <Link to="/admin" className={`hidden md:block font-bold hover:text-primary transition-colors ${scrolled || theme === 'dark' || location.pathname !== '/' ? 'text-on-surface-variant' : 'text-white'}`}>
            Admin
          </Link>
          <button onClick={toggleTheme} className={`p-2 rounded-full hover:bg-surface-variant/50 transition-colors ${scrolled || theme === 'dark' || location.pathname !== '/' ? 'text-on-surface' : 'text-white'}`}>
            <span className="material-symbols-outlined">
              {theme === 'dark' ? 'light_mode' : 'dark_mode'}
            </span>
          </button>
          
          <div className="w-10 h-10 rounded-full bg-surface-variant flex items-center justify-center text-primary font-bold cursor-pointer hover:ring-2 hover:ring-primary transition-all">
            AD
          </div>
        </div>
      </div>
    </nav>
  );
}
