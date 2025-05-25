import React, { useState, useEffect, useCallback, useRef } from 'react';
import { NavLink, Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const CVJM_WEBSITE_URL = "https://cvjmweissach.de/";
const LOGO_URL = "/LogoBig.png"; 

const Layout: React.FC = () => {
  const auth = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();
  const mobileNavRef = useRef<HTMLDivElement>(null);
  const mobileToggleRef = useRef<HTMLButtonElement>(null);
  const mobileCloseBtnRef = useRef<HTMLButtonElement>(null);


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
    if (isMobileMenuOpen) { 
        toggleMobileMenu();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps 
  }, [location]); 

  useEffect(() => {
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isMobileMenuOpen) {
        toggleMobileMenu();
        mobileToggleRef.current?.focus(); 
      }
    };

    const handleFocusTrap = (event: KeyboardEvent) => {
      if (event.key === 'Tab' && isMobileMenuOpen && mobileNavRef.current) {
        const focusableElements = Array.from(
            mobileNavRef.current.querySelectorAll<HTMLElement>(
            'a[href]:not([disabled]), button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
            )
        ).filter(el => el.offsetParent !== null); // Filter out invisible elements

        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey) { 
          if (document.activeElement === firstElement) {
            lastElement.focus();
            event.preventDefault();
          }
        } else { 
          if (document.activeElement === lastElement) {
            firstElement.focus();
            event.preventDefault();
          }
        }
      }
    };
    
    document.addEventListener('keydown', handleEscapeKey);
    document.addEventListener('keydown', handleFocusTrap);

    if (isMobileMenuOpen && mobileCloseBtnRef.current) { // Focus the close button first
        mobileCloseBtnRef.current.focus();
    }

    return () => {
      document.removeEventListener('keydown', handleEscapeKey);
      document.removeEventListener('keydown', handleFocusTrap);
      document.body.classList.remove('mobile-menu-open'); 
    };
  }, [isMobileMenuOpen, toggleMobileMenu]);


  return (
    <div className="app-container">
      <header className="app-header">
        <div className="container">
          <nav> 
            <div className="nav-logo">
              <Link to="/">
                <img src={LOGO_URL} alt="Seifenkistenrennen CVJM Weissach Logo" />
              </Link>
            </div>

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
            
            <button
              ref={mobileToggleRef}
              className="mobile-nav-toggle"
              aria-label="Navigation öffnen"
              aria-expanded={isMobileMenuOpen}
              aria-controls="mobile-nav-links-container"
              onClick={toggleMobileMenu}
            >
              ☰ {/* Hamburger Icon */}
            </button>
          </nav>
        </div>
      </header>

      <div 
        ref={mobileNavRef}
        id="mobile-nav-links-container" 
        className={`nav-links-mobile ${isMobileMenuOpen ? 'open' : ''}`}
        aria-hidden={!isMobileMenuOpen}
        role="dialog" 
        aria-modal="true" 
        aria-labelledby="mobile-menu-heading" 
      >
        <div className="nav-links-mobile-header">
            <span id="mobile-menu-heading" className="nav-links-mobile-title">Menü</span>
            <button 
                ref={mobileCloseBtnRef}
                onClick={toggleMobileMenu} 
                aria-label="Navigation schließen"
                className="nav-links-mobile-close-btn"
            >
                ✕
            </button>
        </div>
        
        <div className="nav-links-mobile-list">
            <NavLink to="/" onClick={toggleMobileMenu}>Home</NavLink>
            <NavLink to="/results" onClick={toggleMobileMenu}>Ergebnisse</NavLink>
            {auth?.isAuthenticated && (
            <NavLink to="/admin" onClick={toggleMobileMenu}>Admin</NavLink>
            )}
            <a href={CVJM_WEBSITE_URL} target="_blank" rel="noopener noreferrer" onClick={toggleMobileMenu}>
            CVJM Seite
            </a>
            {auth?.isAuthenticated && (
            <button 
                onClick={() => { 
                    auth.logout(); 
                    // toggleMobileMenu(); // Wird durch Location-Change geschlossen
                }} 
                className="btn btn-sm btn-logout"
            >
                Logout
            </button>
            )}
        </div>
      </div>

      {isMobileMenuOpen && (
        <div 
          className="mobile-menu-overlay open"
          onClick={toggleMobileMenu}
          aria-hidden="true"
          role="button" 
          tabIndex={-1} 
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