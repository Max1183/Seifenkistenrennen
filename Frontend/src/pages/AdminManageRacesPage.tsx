import React from 'react';
import { Link } from 'react-router-dom';

const AdminManageRacesPage: React.FC = () => {
  return (
    <div className="page-container">
      <h1>Rennen Verwalten</h1>
      <p>Hier können neue Rennen erstellt oder bestehende bearbeitet werden.</p>
      {/* Hier kommt die Logik zum Anzeigen und Verwalten von Rennen */}
      <p>
        <Link to="/admin" className="btn btn-secondary">« Zurück zum Dashboard</Link>
      </p>
      <button className="btn" style={{ marginTop: '1rem' }}>Neues Rennen erstellen</button>
    </div>
  );
};

export default AdminManageRacesPage;