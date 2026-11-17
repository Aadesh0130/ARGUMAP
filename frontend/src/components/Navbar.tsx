import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Network, Sparkles, Menu, X, ArrowRight } from 'lucide-react';
import { Button } from './Button';

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const navLinks = [
    { label: 'Analyze', path: '/analyze' },
    { label: 'Sample Results', path: '/results' },
    { label: 'How It Works', path: '/how-it-works' },
    { label: 'Technology', path: '/technology' },
    { label: 'About', path: '/about' },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="sticky top-0 z-50 bg-slate-950/85 backdrop-blur-md border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center text-white shadow-md shadow-indigo-950 border border-indigo-400/30 group-hover:scale-105 transition-transform duration-150">
              <Network className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="text-lg font-bold tracking-tight text-white group-hover:text-indigo-300 transition-colors">
                  ARGUMAP
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/60 font-medium">
                  v1.0
                </span>
              </div>
              <span className="text-[10px] text-slate-400 tracking-tight -mt-1 hidden sm:inline">
                Debate Reasoning Engine
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <div className="hidden md:flex items-center gap-1 lg:gap-2">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`text-xs lg:text-sm font-medium px-3 py-1.5 rounded-md transition-colors ${
                  isActive(link.path)
                    ? 'text-white bg-slate-800/80'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Desktop CTA Action */}
          <div className="hidden md:flex items-center gap-3">
            <Link to="/analyze">
              <Button size="sm" variant="primary" icon={<Sparkles className="w-3.5 h-3.5" />}>
                Analyze Transcript
              </Button>
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-900"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-slate-800 bg-slate-950 px-4 pt-2 pb-4 space-y-2">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              onClick={() => setMobileMenuOpen(false)}
              className={`block text-sm font-medium px-3 py-2 rounded-md transition-colors ${
                isActive(link.path)
                  ? 'text-white bg-slate-800'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              {link.label}
            </Link>
          ))}
          <div className="pt-2">
            <Link to="/analyze" onClick={() => setMobileMenuOpen(false)}>
              <Button size="md" variant="primary" className="w-full" icon={<ArrowRight className="w-4 h-4" />}>
                Analyze a Debate
              </Button>
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
};
