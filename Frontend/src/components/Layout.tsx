import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext'; // Wenn du AuthContext verwendest

const Layout: React.FC = () => {
  const auth = useAuth(); // Optional, für bedingte Links oder Logout-Button

  return (
    <div className="app-container">
      <header>
        <nav className="container"> {/* Füge .container für Breitenbeschränkung hinzu, wenn gewünscht */}
          <NavLink to="/">Ergebnisse</NavLink>
          <NavLink to="/admin">Admin Bereich</NavLink>
          {auth?.isAuthenticated && (
            <button onClick={() => auth.logout()} className="btn btn-secondary" style={{ marginLeft: 'auto' }}>
              Logout
            </button>
          )}
        </nav>
      </header>
      <main className="content">
        <Outlet /> {/* Hier wird der Inhalt der aktuellen Route gerendert */}
      </main>
      <footer>
        <p>© {new Date().getFullYear()} Seifenkistenrennen Veranstalter</p>
      </footer>
    </div>
  );
};

export default Layout;