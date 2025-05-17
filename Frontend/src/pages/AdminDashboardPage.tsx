import React, { useState, useEffect } from 'react';
import type { FormEvent } from 'react';
import apiService from '../services/apiService';
import type { TeamFromAPI, RacerFromAPI, TeamData, RacerData } from '../types';

type AdminTab = 'teams' | 'participants'; // Konzentrieren uns erstmal auf diese beiden

// Placeholder für ein einfaches Modal (in einer echten App wäre dies eine eigene Komponente)
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}
const SimpleModal: React.FC<ModalProps> = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;
  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', zIndex: 1050
    }}>
      <div style={{ background: 'white', padding: '20px', borderRadius: '8px', minWidth: '300px', maxWidth: '500px' }}>
        <h2>{title}</h2>
        {children}
        <button onClick={onClose} className="btn btn-secondary" style={{ marginTop: '1rem' }}>Schließen</button>
      </div>
    </div>
  );
};


const AdminDashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AdminTab>('teams');

  // State für Teams
  const [teams, setTeams] = useState<TeamFromAPI[]>([]);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [errorTeams, setErrorTeams] = useState<string | null>(null);
  const [isTeamModalOpen, setIsTeamModalOpen] = useState(false);
  const [currentTeam, setCurrentTeam] = useState<TeamFromAPI | null>(null); // Für Bearbeitung
  const [teamFormData, setTeamFormData] = useState<TeamData>({ name: '' });

  // State für Racer
  const [racers, setRacers] = useState<RacerFromAPI[]>([]);
  const [loadingRacers, setLoadingRacers] = useState(false);
  const [errorRacers, setErrorRacers] = useState<string | null>(null);
  const [isRacerModalOpen, setIsRacerModalOpen] = useState(false);
  const [currentRacer, setCurrentRacer] = useState<RacerFromAPI | null>(null);
  const [racerFormData, setRacerFormData] = useState<RacerData>({
    first_name: '',
    last_name: '',
    date_of_birth: '',
    team: null,
  });


  // --- Daten Ladefunktionen ---
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

  const fetchRacers = async () => {
    setLoadingRacers(true);
    setErrorRacers(null);
    try {
      const data = await apiService.getRacers(); // Hier ggf. anreichern mit Teamnamen, wenn nicht im Backend
      // Für die Anzeige den Teamnamen holen oder die ID direkt anzeigen
      const racersWithTeamNames = await Promise.all(data.map(async (racer: RacerFromAPI) => {
        if (racer.team && (!racer.team_details || !racer.team_details.name)) {
          try {
            const team = teams.find(t => t.id === racer.team) || await apiService.getTeamById(racer.team);
            return { ...racer, team_details: { id: team.id, name: team.name } };
          } catch (e) { return racer; /* Team nicht gefunden, ID belassen */ }
        }
        return racer;
      }));
      setRacers(racersWithTeamNames);
    } catch (error) {
      console.error("Failed to fetch racers:", error);
      setErrorRacers("Teilnehmer konnten nicht geladen werden.");
    } finally {
      setLoadingRacers(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'teams') {
      fetchTeams();
    } else if (activeTab === 'participants') {
      if (teams.length === 0) fetchTeams(); // Lade Teams, falls noch nicht geschehen (für Dropdown)
      fetchRacers();
    }
  }, [activeTab]);

  // --- Team CRUD Operationen ---
  const handleOpenTeamModal = (team: TeamFromAPI | null = null) => {
    setCurrentTeam(team);
    setTeamFormData(team ? { name: team.name } : { name: '' });
    setIsTeamModalOpen(true);
  };

  const handleTeamFormChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTeamFormData({ ...teamFormData, [e.target.name]: e.target.value });
  };

  const handleTeamSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!teamFormData.name) {
      alert("Teamname darf nicht leer sein.");
      return;
    }
    try {
      if (currentTeam) { // Update
        const updatedTeam = await apiService.updateTeam(currentTeam.id, teamFormData);
        setTeams(teams.map(t => (t.id === updatedTeam.id ? updatedTeam : t)));
      } else { // Create
        const newTeam = await apiService.createTeam(teamFormData);
        setTeams([...teams, newTeam]);
      }
      setIsTeamModalOpen(false);
      setCurrentTeam(null);
    } catch (error) {
      console.error("Fehler beim Speichern des Teams:", error);
      alert("Fehler beim Speichern des Teams.");
    }
  };

  const handleDeleteTeam = async (teamId: number) => {
    if (window.confirm(`Team wirklich löschen? Zugehörige Racer verlieren ihre Teamzuordnung.`)) {
      try {
        await apiService.deleteTeam(teamId);
        setTeams(teams.filter(t => t.id !== teamId));
        // Optional: Racer-Liste neu laden oder anpassen, wenn ein Team gelöscht wurde
        if (activeTab === 'participants') fetchRacers();
      } catch (error) {
        console.error("Fehler beim Löschen des Teams:", error);
        alert("Fehler beim Löschen des Teams.");
      }
    }
  };

  // --- Racer CRUD Operationen ---
  const handleOpenRacerModal = (racer: RacerFromAPI | null = null) => {
    setCurrentRacer(racer);
    setRacerFormData(racer ? {
      first_name: racer.first_name,
      last_name: racer.last_name,
      date_of_birth: racer.date_of_birth.split('T')[0], // Nur Datumsteil für <input type="date">
      team: racer.team,
    } : { first_name: '', last_name: '', date_of_birth: '', team: null });
    setIsRacerModalOpen(true);
  };

  const handleRacerFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setRacerFormData(prev => ({
      ...prev,
      [name]: name === 'team' ? (value ? parseInt(value) : null) : value,
    }));
  };

const handleRacerSubmit = async (e: FormEvent) => {
  e.preventDefault();
  if (!racerFormData.first_name || !racerFormData.last_name || !racerFormData.date_of_birth) {
    alert("Vorname, Nachname und Geburtsdatum sind erforderlich.");
    return;
  }
  try {
    // Hier die Änderung:
    const payload: RacerData = {
      first_name: racerFormData.first_name,
      last_name: racerFormData.last_name,
      date_of_birth: racerFormData.date_of_birth,
      team: racerFormData.team === undefined ? null : racerFormData.team, // Konvertiere undefined zu null
    };

    if (currentRacer) { // Update
      // Für Update ist Partial<RacerData> oft besser, da nicht alle Felder gesendet werden müssen
      const updatedRacer = await apiService.updateRacer(currentRacer.id, payload);
      setRacers(racers.map(r => (r.id === updatedRacer.id ? { ...updatedRacer, team_details: teams.find(t => t.id === updatedRacer.team) } : r)));
    } else { // Create
      const newRacer = await apiService.createRacer(payload); // Jetzt passt der Typ
      setRacers([...racers, { ...newRacer, team_details: teams.find(t => t.id === newRacer.team) }]);
    }
    setIsRacerModalOpen(false);
    setCurrentRacer(null);
  } catch (error: any) {
    console.error("Fehler beim Speichern des Racers:", error.response?.data || error.message);
    alert(`Fehler beim Speichern des Racers: ${JSON.stringify(error.response?.data) || error.message}`);
  }
};

  const handleDeleteRacer = async (racerId: number) => {
    if (window.confirm(`Teilnehmer wirklich löschen?`)) {
      try {
        await apiService.deleteRacer(racerId); // Annahme: deleteRacer existiert in apiService
        setRacers(racers.filter(r => r.id !== racerId));
      } catch (error) {
        console.error("Fehler beim Löschen des Racers:", error);
        alert("Fehler beim Löschen des Racers.");
      }
    }
  };


  // --- Render Tab Content ---
  const renderTabContent = () => {
    switch (activeTab) {
      case 'teams':
        return (
          <div>
            <h2>Team Verwaltung</h2>
            <button className="btn btn-success" style={{ marginBottom: '1rem' }} onClick={() => handleOpenTeamModal()}>
              Neues Team erstellen
            </button>
            {loadingTeams && <p>Lade Teams...</p>}
            {errorTeams && <p style={{ color: 'var(--danger-color)' }}>{errorTeams}</p>}
            {!loadingTeams && !errorTeams && teams.length > 0 && (
              <table className="results-table">
                <thead><tr><th>ID</th><th>Name</th><th>Fahrer</th><th>Aktionen</th></tr></thead>
                <tbody>
                  {teams.map(team => (
                    <tr key={team.id}>
                      <td>{team.id}</td>
                      <td>{team.name}</td>
                      <td>{team.racer_count || 0}</td>
                      <td>
                        <button className="btn btn-sm btn-info" style={{marginRight: '0.5rem'}} onClick={() => handleOpenTeamModal(team)}>Bearbeiten</button>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDeleteTeam(team.id)}>Löschen</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {!loadingTeams && !errorTeams && teams.length === 0 && <p>Keine Teams gefunden.</p>}
          </div>
        );
      case 'participants':
        return (
          <div>
            <h2>Teilnehmer Verwaltung</h2>
            <button className="btn btn-success" style={{ marginBottom: '1rem' }} onClick={() => handleOpenRacerModal()}>
              Neuen Teilnehmer erstellen
            </button>
            {loadingRacers && <p>Lade Teilnehmer...</p>}
            {errorRacers && <p style={{ color: 'var(--danger-color)' }}>{errorRacers}</p>}
            {!loadingRacers && !errorRacers && racers.length > 0 && (
               <table className="results-table">
                <thead><tr><th>ID</th><th>Name</th><th>Geburtsdatum</th><th>Team</th><th>Aktionen</th></tr></thead>
                <tbody>
                  {racers.map(racer => (
                    <tr key={racer.id}>
                      <td>{racer.id}</td>
                      <td>{racer.full_name || `${racer.first_name} ${racer.last_name}`}</td>
                      <td>{new Date(racer.date_of_birth).toLocaleDateString()}</td>
                      <td>{racer.team_details?.name || (racer.team ? `ID: ${racer.team}` : 'Kein Team')}</td>
                      <td>
                        <button className="btn btn-sm btn-info" style={{marginRight: '0.5rem'}} onClick={() => handleOpenRacerModal(racer)}>Bearbeiten</button>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDeleteRacer(racer.id)}>Löschen</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
             {!loadingRacers && !errorRacers && racers.length === 0 && <p>Keine Teilnehmer gefunden.</p>}
          </div>
        );
      default:
        return <p>Bitte wähle einen Tab.</p>;
    }
  };

  return (
    <div className="page-container">
      <h1>Admin Dashboard</h1>
      <div className="admin-tabs">
        <button className={`tab-button ${activeTab === 'teams' ? 'active' : ''}`} onClick={() => setActiveTab('teams')}>Teams</button>
        <button className={`tab-button ${activeTab === 'participants' ? 'active' : ''}`} onClick={() => setActiveTab('participants')}>Teilnehmer</button>
        {/* Weitere Tab-Buttons für Results, Settings etc. */}
      </div>
      <div className="tab-content">
        {renderTabContent()}
      </div>

      {/* Team Modal */}
      <SimpleModal isOpen={isTeamModalOpen} onClose={() => setIsTeamModalOpen(false)} title={currentTeam ? "Team bearbeiten" : "Neues Team"}>
        <form onSubmit={handleTeamSubmit}>
          <div>
            <label htmlFor="teamName">Teamname:</label>
            <input type="text" id="teamName" name="name" value={teamFormData.name} onChange={handleTeamFormChange} required />
          </div>
          <button type="submit" className="btn" style={{ marginTop: '1rem' }}>Speichern</button>
        </form>
      </SimpleModal>

      {/* Racer Modal */}
      <SimpleModal isOpen={isRacerModalOpen} onClose={() => setIsRacerModalOpen(false)} title={currentRacer ? "Teilnehmer bearbeiten" : "Neuer Teilnehmer"}>
        <form onSubmit={handleRacerSubmit}>
          <div>
            <label htmlFor="racerFirstName">Vorname:</label>
            <input type="text" id="racerFirstName" name="first_name" value={racerFormData.first_name} onChange={handleRacerFormChange} required />
          </div>
          <div>
            <label htmlFor="racerLastName">Nachname:</label>
            <input type="text" id="racerLastName" name="last_name" value={racerFormData.last_name} onChange={handleRacerFormChange} required />
          </div>
          <div>
            <label htmlFor="racerDob">Geburtsdatum:</label>
            <input type="date" id="racerDob" name="date_of_birth" value={racerFormData.date_of_birth} onChange={handleRacerFormChange} required />
          </div>
          <div>
            <label htmlFor="racerTeam">Team:</label>
            <select id="racerTeam" name="team" value={racerFormData.team || ''} onChange={handleRacerFormChange}>
              <option value="">Kein Team</option>
              {teams.map(team => (
                <option key={team.id} value={team.id}>{team.name}</option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn" style={{ marginTop: '1rem' }}>Speichern</button>
        </form>
      </SimpleModal>
    </div>
  );
};

export default AdminDashboardPage;