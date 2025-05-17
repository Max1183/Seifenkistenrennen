import React, { useState } from 'react';
// Importiere hier die Komponenten für die einzelnen Admin-Tabs
// z.B.:
// import AdminManageTeams from './admin/AdminManageTeams';
// import AdminManageParticipants from './admin/AdminManageParticipants';
// import AdminManageResults from './admin/AdminManageResults';

type AdminTab = 'teams' | 'participants' | 'results' | 'settings'; // Beispiel-Tabs

const AdminDashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AdminTab>('teams'); // Standard-Tab

  const renderTabContent = () => {
    switch (activeTab) {
      case 'teams':
        return (
          <div>
            <h2>Team Verwaltung</h2>
            <p>Hier können Teams erstellt, bearbeitet und gelöscht werden.</p>
            {/* <AdminManageTeams /> */}
          </div>
        );
      case 'participants':
        return (
          <div>
            <h2>Teilnehmer Verwaltung</h2>
            <p>Verwaltung der einzelnen Fahrer und deren Zuordnung zu Teams.</p>
            {/* <AdminManageParticipants /> */}
          </div>
        );
      case 'results':
        return (
          <div>
            <h2>Ergebnis Verwaltung</h2>
            <p>Eingabe und Korrektur von Rennergebnissen.</p>
            {/* <AdminManageResults /> */}
          </div>
        );
      case 'settings':
        return (
          <div>
            <h2>Renn-Einstellungen</h2>
            <p>Konfiguration des aktuellen Rennens, Altersklassen etc.</p>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="page-container">
      <h1>Admin Dashboard</h1>

      <div className="admin-tabs">
        <button
          className={`tab-button ${activeTab === 'teams' ? 'active' : ''}`}
          onClick={() => setActiveTab('teams')}
        >
          Teams
        </button>
        <button
          className={`tab-button ${activeTab === 'participants' ? 'active' : ''}`}
          onClick={() => setActiveTab('participants')}
        >
          Teilnehmer
        </button>
        <button
          className={`tab-button ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        >
          Ergebnisse
        </button>
        <button
          className={`tab-button ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          Einstellungen
        </button>
      </div>

      <div className="tab-content">
        {renderTabContent()}
      </div>
    </div>
  );
};

export default AdminDashboardPage;