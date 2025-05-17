import React, { useState, useEffect } from 'react';
import apiService from '../services/apiService';

// Typdefinitionen für Backend-Daten
interface TeamFromAPI {
  id: number;
  name: string;
  racer_count?: number;
  racers?: any[]; // Ggf. detailliertere Typen für Racer
}

type AdminTab = 'teams' | 'participants' | 'results' | 'settings';

const AdminDashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AdminTab>('teams');
  const [teams, setTeams] = useState<TeamFromAPI[]>([]);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [errorTeams, setErrorTeams] = useState<string | null>(null);

  // Lade Daten, wenn der Tab aktiv wird oder die Komponente mounted
  useEffect(() => {
    if (activeTab === 'teams') {
      const fetchTeams = async () => {
        setLoadingTeams(true);
        setErrorTeams(null);
        try {
          const data = await apiService.getTeams();
          setTeams(data);
        } catch (error) {
          console.error("Failed to fetch teams:", error);
          setErrorTeams("Teams konnten nicht geladen werden.");
        } finally {
          setLoadingTeams(false);
        }
      };
      fetchTeams();
    }
    // Ähnliche Logik für andere Tabs hier hinzufügen
  }, [activeTab]); // Neu laden, wenn der aktive Tab sich ändert


  const renderTabContent = () => {
    switch (activeTab) {
      case 'teams':
        return (
          <div>
            <h2>Team Verwaltung</h2>
            {loadingTeams && <p>Lade Teams...</p>}
            {errorTeams && <p style={{ color: 'var(--danger-color)' }}>{errorTeams}</p>}
            {!loadingTeams && !errorTeams && (
              <>
                <button className="btn btn-success" style={{ marginBottom: '1rem' }} onClick={() => alert('Neues Team Formular öffnen...')}>
                  Neues Team erstellen
                </button>
                {teams.length > 0 ? (
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Anzahl Fahrer</th>
                        <th>Aktionen</th>
                      </tr>
                    </thead>
                    <tbody>
                      {teams.map(team => (
                        <tr key={team.id}>
                          <td>{team.id}</td>
                          <td>{team.name}</td>
                          <td>{team.racer_count || team.racers?.length || 0}</td>
                          <td>
                            <button className="btn btn-sm btn-info" style={{marginRight: '0.5rem'}} onClick={() => alert(`Bearbeite Team ${team.name}`)}>Bearbeiten</button>
                            <button className="btn btn-sm btn-danger" onClick={() => {
                                if(window.confirm(`Team "${team.name}" wirklich löschen?`)) {
                                    apiService.deleteTeam(team.id)
                                        .then(() => {
                                            setTeams(prevTeams => prevTeams.filter(t => t.id !== team.id));
                                            alert('Team gelöscht');
                                        })
                                        .catch(err => {
                                            console.error("Fehler beim Löschen des Teams:", err);
                                            alert('Fehler beim Löschen');
                                        });
                                }
                            }}>Löschen</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p>Keine Teams gefunden.</p>
                )}
              </>
            )}
            {/* Hier könnten Formulare zum Erstellen/Bearbeiten von Teams hin */}
          </div>
        );
      case 'participants':
        return (
          <div>
            <h2>Teilnehmer Verwaltung</h2>
            <p>Verwaltung der einzelnen Fahrer.</p>
            {/* Implementiere Laden und Anzeigen von Teilnehmern hier */}
          </div>
        );
      // Weitere Cases für 'results', 'settings'
      default:
        return null;
    }
  };

  return (
    <div className="page-container">
      <h1>Admin Dashboard</h1>
      <div className="admin-tabs">
        {/* Tab-Buttons bleiben gleich */}
        <button
          className={`tab-button ${activeTab === 'teams' ? 'active' : ''}`}
          onClick={() => setActiveTab('teams')}
        > Teams </button>
        {/* ... andere Buttons ... */}
         <button
          className={`tab-button ${activeTab === 'participants' ? 'active' : ''}`}
          onClick={() => setActiveTab('participants')}
        > Teilnehmer </button>
         <button
          className={`tab-button ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        > Ergebnisse </button>
        <button
          className={`tab-button ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        > Einstellungen </button>
      </div>
      <div className="tab-content">
        {renderTabContent()}
      </div>
    </div>
  );
};

export default AdminDashboardPage;