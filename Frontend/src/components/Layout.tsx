import React from 'react';
import { NavLink, Link, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const CVJM_WEBSITE_URL = "https://cvjmweissach.de/";
const LOGO_URL = "/LogoBig.png";

const Layout: React.FC = () => {
  const auth = useAuth();

  return (
    <div className="app-container">
      <header>
        <nav>
          <div className="nav-logo">
            <Link to="/">
              <img src={LOGO_URL} alt="Seifenkistenrennen Logo" />
            </Link>
          </div>
          <div className="nav-links">
            <NavLink to="/">Home</NavLink>
            <NavLink to="/results">Ergebnisse</NavLink>
            {auth?.isAuthenticated && (
              <NavLink to="/admin">Admin</NavLink>
            )}
            <a href={CVJM_WEBSITE_URL} target="_blank" rel="noopener noreferrer">
              CVJM Seite
            </a>
            {auth?.isAuthenticated && (
              <button onClick={() => auth.logout()} className="btn-logout">
                Logout
              </button>
            )}
          </div>
        </nav>
      </header>

      <main className="content">
        <Outlet />
      </main>

      <footer>
        <div className="footer-links">
          <Link to="/about">Über uns</Link>
          <Link to="/privacy">Datenschutz</Link>
          <Link to="/impressum">Impressum</Link>
        </div>
        <p>© {new Date().getFullYear()} Dein Veranstaltername hier</p>
      </footer>
    </div>
  );
};

export default Layout;