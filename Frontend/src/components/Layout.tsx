import React, { useState, useEffect, useCallback } from 'react';
import { NavLink, Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const CVJM_WEBSITE_URL = "https://cvjmweissach.de/";
const LOGO_URL = "/LogoBig.png"; 

const Layout: React.FC = () => {
  const auth = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  const toggleMobileMenu = useCallback(() => {
    setIsMobileMenuOpen(prev => {
      const newState = !prev;
      if (newState) {
        document.body.classList.add('mobile-menu-open');
      } else {
        document.body.classList.remove('mobile-menu-open');
      }
      return newState;
    });
  }, []);

  useEffect(() => {
    if (isMobileMenuOpen) { // Only attempt to close if it was open
        toggleMobileMenu();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location]); // Removed isMobileMenuOpen from deps to avoid loop on manual toggle

  useEffect(() => {
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isMobileMenuOpen) {
        toggleMobileMenu();
      }
    };
    document.addEventListener('keydown', handleEscapeKey);
    return () => {
      document.removeEventListener('keydown', handleEscapeKey);
      document.body.classList.remove('mobile-menu-open'); 
    };
  }, [isMobileMenuOpen, toggleMobileMenu]);


  return (
    <div className="app-container">
      <header className="app-header">
        <div className="container">
          <nav> {/* This nav contains logo, then EITHER desktop links OR mobile toggle */}
            <div className="nav-logo">
              <Link to="/">
                <img src={LOGO_URL} alt="Seifenkistenrennen CVJM Weissach Logo" />
              </Link>
            </div>

            {/* Desktop Links - Styled to be hidden on mobile via CSS */}
            <div className="nav-links-desktop">
              <NavLink to="/">Home</NavLink>
              <NavLink to="/results">Ergebnisse</NavLink>
              {auth?.isAuthenticated && (
                <NavLink to="/admin">Admin</NavLink>
              )}
              <a href={CVJM_WEBSITE_URL} target="_blank" rel="noopener noreferrer">
                CVJM Seite
              </a>
              {auth?.isAuthenticated && (
                <button onClick={() => auth.logout()} className="btn btn-sm btn-logout">
                  Logout
                </button>
              )}
            </div>
            
            {/* Mobile Nav Toggle Button - Styled to be visible on mobile via CSS */}
            <button
              className="mobile-nav-toggle"
              aria-label="Navigation öffnen/schließen"
              aria-expanded={isMobileMenuOpen}
              aria-controls="mobile-nav-links-container"
              onClick={toggleMobileMenu}
            >
              {isMobileMenuOpen ? '✕' : '☰'}
            </button>
          </nav>
        </div>
      </header>

      {/* Off-Canvas Mobile Menu */}
      <div 
        id="mobile-nav-links-container" 
        className={`nav-links-mobile ${isMobileMenuOpen ? 'open' : ''}`}
        aria-hidden={!isMobileMenuOpen}
        // Trap focus within the mobile menu when open (basic example)
        // For full accessibility, a more robust focus trapping library might be needed
        onKeyDown={(e) => {
          if (e.key === 'Tab' && isMobileMenuOpen) {
            const focusableElements = (e.currentTarget as HTMLElement).querySelectorAll(
              'a[href], button:not([disabled])'
            );
            const firstElement = focusableElements[0] as HTMLElement;
            const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

            if (e.shiftKey) { // Shift + Tab
              if (document.activeElement === firstElement) {
                lastElement.focus();
                e.preventDefault();
              }
            } else { // Tab
              if (document.activeElement === lastElement) {
                firstElement.focus();
                e.preventDefault();
              }
            }
          }
        }}
      >
        {/* Ensure the first focusable item can receive focus when menu opens */}
        <NavLink to="/" onClick={toggleMobileMenu} ref={isMobileMenuOpen ? (el) => el?.focus() : null}>Home</NavLink>
        <NavLink to="/results" onClick={toggleMobileMenu}>Ergebnisse</NavLink>
        {auth?.isAuthenticated && (
          <NavLink to="/admin" onClick={toggleMobileMenu}>Admin</NavLink>
        )}
        <a href={CVJM_WEBSITE_URL} target="_blank" rel="noopener noreferrer" onClick={toggleMobileMenu}>
          CVJM Seite
        </a>
        {auth?.isAuthenticated && (
          <button onClick={() => { auth.logout(); toggleMobileMenu(); }} className="btn btn-sm btn-logout">
            Logout
          </button>
        )}
      </div>

      {/* Overlay for mobile menu */}
      {isMobileMenuOpen && (
        <div 
          className="mobile-menu-overlay open"
          onClick={toggleMobileMenu}
          aria-hidden="true"
        />
      )}


      <main className="app-main-content">
        <div className="container"> 
          <Outlet />
        </div>
      </main>

      <footer className="app-footer">
        <div className="footer-links">
          <Link to="/about">Über uns</Link>
          <Link to="/privacy">Datenschutz</Link>
          <Link to="/impressum">Impressum</Link>
        </div>
        <p>© {new Date().getFullYear()} CVJM Weissach e.V.</p>
      </footer>
    </div>
  );
};

export default Layout;