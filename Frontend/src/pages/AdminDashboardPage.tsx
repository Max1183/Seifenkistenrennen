import React from 'react';
import { Link } from 'react-router-dom';

const AdminDashboardPage: React.FC = () => {
  return (
    <div className="page-container">
      <h1>Admin Dashboard</h1>
      <p>Willkommen im gesicherten Admin-Bereich! Hier kannst du das Rennen verwalten.</p>
      <nav>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          <li style={{ marginBottom: '1rem' }}>
            <Link to="/admin/races" className="btn">Rennen verwalten</Link>
          </li>
          <li style={{ marginBottom: '1rem' }}>
            <Link to="/admin/participants" className="btn btn-secondary">Teilnehmer verwalten</Link>
          </li>
          <li style={{ marginBottom: '1rem' }}>
            <Link to="/admin/results/entry" className="btn">Ergebnisse eintragen</Link>
          </li>
        </ul>
      </nav>
      {/* Weitere Inhalte für das Dashboard */}
    </div>
  );
};

export default AdminDashboardPage;