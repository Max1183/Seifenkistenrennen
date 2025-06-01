import React, { useState, useEffect, useCallback, useMemo } from 'react';
import ReactDOM from 'react-dom';
import type { FormEvent, ChangeEvent } from 'react';
import apiService from '../services/apiService';
import type {
  TeamFromAPI,
  RacerFromAPI,
  TeamFormData,
  RacerFormData,
  RaceRunFormData,
  RaceRunFromAPI,
  SoapboxClassOption
} from '../types';
import {
  SOAPBOX_CLASS_VALUES,
  SOAPBOX_CLASS_DISPLAY_MAP,
  type SoapboxClassValue,
  RACE_RUN_TYPE_VALUES,
  RACE_RUN_TYPE_DISPLAY_MAP,
  type RaceRunTypeValue
} from '../types';

type AdminTab = 'teams' | 'participants' | 'raceruns';

interface AdminModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

const AdminModal: React.FC<AdminModalProps> = ({ isOpen, onClose, title, children, size = 'md' }) => {
  const modalRoot = document.getElementById('modal-root');
  let maxWidthClass = 'modal-content-md';
  if (size === 'lg') maxWidthClass = 'modal-content-lg';
  if (size === 'sm') maxWidthClass = 'modal-content-sm';

  const modalContent = (
    <div className="modal-overlay modal-enter" onClick={onClose}>
      <div className={`modal-content admin-modal-content ${maxWidthClass}`} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="modal-close-button" onClick={onClose} aria-label="Schließen">×</button>
        </div>
        <div className="modal-body admin-modal-form">
            {children}
        </div>
      </div>
    </div>
  );
  if (!isOpen || !modalRoot) return null;
  return ReactDOM.createPortal(modalContent, modalRoot);
};

const AdminDashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AdminTab>('teams');

  const [teams, setTeams] = useState<TeamFromAPI[]>([]);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [teamForm, setTeamForm] = useState<TeamFormData>({ name: '' });
  const [editingTeam, setEditingTeam] = useState<TeamFromAPI | null>(null);

  const [racers, setRacers] = useState<RacerFromAPI[]>([]);
  const [loadingRacers, setLoadingRacers] = useState(false);
  const initialRacerFormState: RacerFormData = {
    first_name: '',
    last_name: '',
    soapbox_class: SOAPBOX_CLASS_VALUES.UNKNOWN,
    team: '',
    start_number: ''
  };
  const [racerForm, setRacerForm] = useState<RacerFormData>(initialRacerFormState);
  const [editingRacer, setEditingRacer] = useState<RacerFromAPI | null>(null);

  const [raceRuns, setRaceRuns] = useState<RaceRunFromAPI[]>([]);
  const [loadingRaceRuns, setLoadingRaceRuns] = useState(false);
  const initialRaceRunFormState: RaceRunFormData = {
    racer_id: undefined,
    racer_start_number: '',
    time_in_seconds: '',
    disqualified: false,
    run_identifier: 1,
    run_type: RACE_RUN_TYPE_VALUES.PRACTICE,
    notes: ''
  };
  const [raceRunForm, setRaceRunForm] = useState<RaceRunFormData>(initialRaceRunFormState);
  const [editingRaceRun, setEditingRaceRun] = useState<RaceRunFromAPI | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalType, setModalType] = useState<'team' | 'racer' | 'racerun' | null>(null);
  const [errorAlert, setErrorAlert] = useState<string | null>(null);

  const soapboxClassOptionsForAdmin: SoapboxClassOption[] = useMemo(() => {
    return Object.entries(SOAPBOX_CLASS_DISPLAY_MAP).map(([value, label]) => ({
      value: value as SoapboxClassValue,
      label,
    })).sort((a,b) => a.label.localeCompare(b.label));
  }, []);

  const raceRunTypeOptionsForAdmin = useMemo(() => {
    return Object.entries(RACE_RUN_TYPE_DISPLAY_MAP).map(([value, label]) => ({
        value: value as RaceRunTypeValue,
        label,
    }));
  }, []);
  
  const fetchData = useCallback(async () => {
    setErrorAlert(null); 
    if (activeTab === 'teams') {
      setLoadingTeams(true);
      try { 
        const fetchedTeams = await apiService.getTeams();
        setTeams(fetchedTeams); 
      }
      catch (e: any) {
        console.error("Error fetching teams", e);
        setErrorAlert(`Fehler beim Laden der Teams: ${e.message || 'Unbekannter Fehler'}`);
      }
      finally { setLoadingTeams(false); }
    } else if (activeTab === 'participants') {
      setLoadingRacers(true);
      try {
        const currentTeams = await apiService.getTeams();
        setTeams(currentTeams); 

        const fetchedRacers = await apiService.getRacers();
        const racersWithTeamDetails = fetchedRacers.map(r => {
            const team = currentTeams.find(t => t.id === r.team);
            return {...r, team_name: team ? team.name : (r.team_name || null) };
        });
        setRacers(racersWithTeamDetails);
      } catch (e: any) {
        console.error("Error fetching racers", e);
        setErrorAlert(`Fehler beim Laden der Teilnehmer: ${e.message || 'Unbekannter Fehler'}`);
      }
      finally { setLoadingRacers(false); }
    } else if (activeTab === 'raceruns') {
        setLoadingRaceRuns(true);
        try {
            const currentTeams = await apiService.getTeams();
            setTeams(currentTeams);

            const fetchedRacersRaw = await apiService.getRacers();
            const currentRacers = fetchedRacersRaw.map(r => {
                const team = currentTeams.find(t => t.id === r.team);
                return {...r, team_name: team ? team.name : (r.team_name || null) };
            });
            setRacers(currentRacers); 

            const fetchedRaceRuns = await apiService.getRaceRuns();
            const runsWithRacerNames = fetchedRaceRuns.map(rr => {
                const racer = currentRacers.find(r => r.id === rr.racer);
                return {...rr, racer_name: racer ? racer.full_name : (rr.racer_name || `ID: ${rr.racer}`)};
            });
            setRaceRuns(runsWithRacerNames);
        } catch (e: any) {
          console.error("Error fetching race runs", e);
          setErrorAlert(`Fehler beim Laden der Rennläufe: ${e.message || 'Unbekannter Fehler'}`);
        }
        finally { setLoadingRaceRuns(false); }
    }
  }, [activeTab]); 

  useEffect(() => {
    fetchData();
  }, [fetchData]); 

  const openModal = (type: 'team' | 'racer' | 'racerun', data: any | null = null) => {
    setModalType(type);
    setIsModalOpen(true);
    setErrorAlert(null);
    if (type === 'team') {
      setEditingTeam(data);
      setTeamForm(data ? { name: data.name } : { name: '' });
    } else if (type === 'racer') {
      setEditingRacer(data);
      setRacerForm(data ? {
        first_name: data.first_name, 
        last_name: data.last_name,
        soapbox_class: data.soapbox_class,
        team: data.team || '', 
        start_number: data.start_number || ''
      } : initialRacerFormState);
    } else if (type === 'racerun') {
        setEditingRaceRun(data);
        const defaultRacerId = racers.length > 0 ? racers[0].id : undefined;
        if (data) {
            setRaceRunForm({
                racer_id: data.racer,
                racer_start_number: racers.find(r => r.id === data.racer)?.start_number || '',
                time_in_seconds: data.time_in_seconds || '',
                disqualified: data.disqualified,
                notes: data.notes || '',
                run_identifier: data.run_identifier,
                run_type: data.run_type
            });
        } else {
            setRaceRunForm({
                ...initialRaceRunFormState,
                racer_id: defaultRacerId,
            });
        }
    }
  };
  const closeModal = () => setIsModalOpen(false);

  const handleFormChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>, formType: 'team' | 'racer' | 'racerun') => {
    const { name, value, type } = e.target;
    const val = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value;

    if (formType === 'team') setTeamForm(prev => ({ ...prev, [name]: val }));
    if (formType === 'racer') setRacerForm(prev => ({ ...prev, [name]: val as any })); 
    if (formType === 'racerun') {
      if (name === 'racer_id') {
        setRaceRunForm(prev => ({ ...prev, racer_id: Number(val) || undefined, racer_start_number: '' }));
      } else if (name === 'racer_start_number') {
        setRaceRunForm(prev => ({ ...prev, racer_start_number: String(val), racer_id: undefined }));
      } else {
        setRaceRunForm(prev => ({ ...prev, [name]: val as any }));
      }
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorAlert(null);
    try {
      if (modalType === 'team') {
        if (!teamForm.name.trim()) { setErrorAlert("Teamname ist erforderlich."); return; }
        editingTeam ? await apiService.updateTeam(editingTeam.id, teamForm) : await apiService.createTeam(teamForm);
      } else if (modalType === 'racer') {
        if (!racerForm.first_name.trim() || !racerForm.last_name.trim()) { setErrorAlert("Vor- und Nachname sind erforderlich."); return; }
        const racerPayload: RacerFormData = {
            first_name: racerForm.first_name,
            last_name: racerForm.last_name,
            soapbox_class: racerForm.soapbox_class,
            team: racerForm.team === '' ? null : Number(racerForm.team),
            start_number: racerForm.start_number?.trim() || null,
        };
        editingRacer ? await apiService.updateRacer(editingRacer.id, racerPayload) : await apiService.createRacer(racerPayload);
      } else if (modalType === 'racerun') {
        if (!raceRunForm.racer_id && !raceRunForm.racer_start_number?.trim()) {
          setErrorAlert("Fahrer muss über ID oder Startnummer identifiziert werden.");
          return;
        }

        const runPayload: RaceRunFormData = {
            ...(raceRunForm.racer_id && { racer_id: Number(raceRunForm.racer_id) }),
            ...(raceRunForm.racer_start_number?.trim() && { racer_start_number: raceRunForm.racer_start_number.trim() }),
            time_in_seconds: raceRunForm.time_in_seconds?.trim() ? raceRunForm.time_in_seconds.trim().replace(',', '.') : null,
            disqualified: raceRunForm.disqualified,
            notes: raceRunForm.notes?.trim() || null,
            run_identifier: Number(raceRunForm.run_identifier),
            run_type: raceRunForm.run_type,
        };

        if (runPayload.racer_id === undefined) delete runPayload.racer_id;
        if (runPayload.racer_start_number === undefined || runPayload.racer_start_number === '') delete runPayload.racer_start_number;
        
        editingRaceRun ? await apiService.updateRaceRun(editingRaceRun.id, runPayload) : await apiService.createRaceRun(runPayload);
      }
      closeModal();
      fetchData(); 
    } catch (error: any) {
      const data = error.response?.data;
      let message = "Ein unbekannter Fehler ist aufgetreten.";
      if (typeof data === 'string') message = data;
      else if (data && typeof data === 'object') {
        const fieldErrors = Object.entries(data)
            .map(([key, value]) => `${key}: ${(Array.isArray(value) ? value.join(', ') : String(value))}`)
            .join('; ');
        if (fieldErrors) message = fieldErrors;
        else if (data.detail) message = data.detail;
      } else if (error.message) message = error.message;
      
      console.error(`Error saving ${modalType}:`, error);
      setErrorAlert(`Fehler beim Speichern: ${message}`);
    }
  };

  const handleDelete = async (type: 'team' | 'racer' | 'racerun', id: number) => {
    if (!window.confirm(`${type.charAt(0).toUpperCase() + type.slice(1)} wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.`)) return;
    setErrorAlert(null);
    try {
      if (type === 'team') await apiService.deleteTeam(id);
      if (type === 'racer') await apiService.deleteRacer(id);
      if (type === 'racerun') await apiService.deleteRaceRun(id);
      fetchData(); 
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || JSON.stringify(error.response?.data) || error.message;
      console.error(`Error deleting ${type}:`, error);
      setErrorAlert(`Fehler beim Löschen: ${errorMessage}`);
    }
  };

  const renderTeamTabContent = () => (
    <>
      <button className="btn btn-primary" style={{ marginBottom: 'var(--spacing-md)' }} onClick={() => openModal('team')}>Neues Team erstellen</button>
      {loadingTeams && <p>Lade Teams...</p>}
      {!loadingTeams && teams.length === 0 && !errorAlert && <p>Keine Teams vorhanden. Erstelle das erste Team!</p>}
      {!loadingTeams && teams.length > 0 && (
        <div className="table-wrapper">
        <table className="results-table">
          <thead><tr><th>Name</th><th>Anzahl Fahrer</th><th>Aktionen</th></tr></thead>
          <tbody>
            {teams.sort((a,b) => a.name.localeCompare(b.name)).map(team => (
              <tr key={team.id}>
                <td>{team.name}</td>
                <td style={{textAlign: 'center'}}>{team.racer_count || 0}</td>
                <td>
                  <button className="btn btn-sm btn-outline-primary" style={{marginRight: 'var(--spacing-sm)'}} onClick={() => openModal('team', team)}>Bearbeiten</button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDelete('team', team.id)}>Löschen</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </>
  );

  const renderRacerTabContent = () => (
    <>
      <button className="btn btn-primary" style={{ marginBottom: 'var(--spacing-md)' }} onClick={() => openModal('racer')}>Neuen Teilnehmer registrieren</button>
      {loadingRacers && <p>Lade Teilnehmer...</p>}
      {!loadingRacers && racers.length === 0 && !errorAlert && <p>Keine Teilnehmer vorhanden. Registriere den ersten Teilnehmer!</p>}
      {!loadingRacers && racers.length > 0 && (
        <div className="table-wrapper">
        <table className="results-table">
          <thead><tr><th>Name</th><th>Startnr.</th><th>Klasse</th><th>Team</th><th>Aktionen</th></tr></thead>
          <tbody>
            {racers.sort((a,b) => (a.full_name || '').localeCompare(b.full_name || '')).map(racer => (
              <tr key={racer.id}>
                <td>{racer.full_name}</td>
                <td style={{textAlign: 'center'}}>{racer.start_number || '-'}</td>
                <td>{racer.soapbox_class_display}</td>
                <td>{racer.team_name || 'Einzelstarter'}</td>
                <td>
                  <button className="btn btn-sm btn-outline-primary" style={{marginRight: 'var(--spacing-sm)'}} onClick={() => openModal('racer', racer)}>Bearbeiten</button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDelete('racer', racer.id)}>Löschen</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </>
  );

const renderRaceRunTabContent = () => (
    <>
        <button className="btn btn-primary" style={{ marginBottom: 'var(--spacing-md)' }} onClick={() => openModal('racerun')}>Neuen Lauf erfassen</button>
        {loadingRaceRuns && <p>Lade Rennläufe...</p>}
        {!loadingRaceRuns && raceRuns.length === 0 && !errorAlert && <p>Keine Rennläufe vorhanden. Erfasse den ersten Lauf!</p>}
        {!loadingRaceRuns && raceRuns.length > 0 && (
            <div className="table-wrapper">
            <table className="results-table">
                <thead><tr><th>Fahrer</th><th>Typ</th><th>Lauf Nr.</th><th>Zeit (s)</th><th>DQ</th><th style={{minWidth: '150px'}}>Notizen</th><th>Aktionen</th></tr></thead>
                <tbody>
                    {raceRuns.sort((a,b) => (a.racer_name || '').localeCompare(b.racer_name || '') || a.run_type.localeCompare(b.run_type) || a.run_identifier - b.run_identifier).map(run => (
                        <tr key={run.id}>
                            <td>{run.racer_name || `ID: ${run.racer}`}</td>
                            <td>{run.run_type_display}</td>
                            <td style={{textAlign: 'center'}}>{run.run_identifier}</td>
                            <td>{run.disqualified ? <span style={{color: 'var(--danger-color)', fontWeight: 'bold'}}>DQ</span> : (run.time_in_seconds || 'N/A')}</td>
                            <td>{run.disqualified ? <span style={{color: 'var(--danger-color)', fontWeight: 'bold'}}>Ja</span> : 'Nein'}</td>
                            <td style={{maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}} title={run.notes || undefined}>{run.notes || '-'}</td>
                            <td>
                                <button className="btn btn-sm btn-outline-primary" style={{marginRight: 'var(--spacing-sm)'}} onClick={() => openModal('racerun', run)}>Bearbeiten</button>
                                <button className="btn btn-sm btn-danger" onClick={() => handleDelete('racerun', run.id)}>Löschen</button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            </div>
        )}
    </>
  );

  return (
    <div className="page-container page-enter-animation">
      <h1>Admin Dashboard</h1>
      {errorAlert && !isModalOpen && <div className="results-error-message" style={{marginBottom: 'var(--spacing-md)'}}>{errorAlert}</div>}
      <div className="admin-tabs">
        <button className={`tab-button ${activeTab === 'teams' ? 'active' : ''}`} onClick={() => setActiveTab('teams')}>Teams</button>
        <button className={`tab-button ${activeTab === 'participants' ? 'active' : ''}`} onClick={() => setActiveTab('participants')}>Teilnehmer</button>
        <button className={`tab-button ${activeTab === 'raceruns' ? 'active' : ''}`} onClick={() => setActiveTab('raceruns')}>Rennläufe</button>
      </div>
      <div className="tab-content">
        {activeTab === 'teams' && renderTeamTabContent()}
        {activeTab === 'participants' && renderRacerTabContent()}
        {activeTab === 'raceruns' && renderRaceRunTabContent()}
      </div>

      <AdminModal
        isOpen={isModalOpen}
        onClose={closeModal}
        title={
          modalType === 'team' ? (editingTeam ? 'Team bearbeiten' : 'Neues Team') :
          modalType === 'racer' ? (editingRacer ? 'Teilnehmer bearbeiten' : 'Neuer Teilnehmer') :
          modalType === 'racerun' ? (editingRaceRun ? 'Rennlauf bearbeiten' : 'Neuer Rennlauf') : ''
        }
        size={modalType === 'racer' || modalType === 'racerun' ? 'lg' : 'md'}
      >
        <form onSubmit={handleSubmit}>
          {errorAlert && isModalOpen && <p style={{ color: 'var(--danger-color)', marginBottom: 'var(--spacing-md)' }}>{errorAlert}</p>}
          {modalType === 'team' && (
            <div className="form-group">
              <label htmlFor="teamNameModal">Teamname:</label>
              <input type="text" id="teamNameModal" name="name" className="form-control" value={teamForm.name} onChange={e => handleFormChange(e, 'team')} required />
            </div>
          )}
          {modalType === 'racer' && (
            <>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--spacing-md)'}}>
                <div className="form-group"><label htmlFor="racerFirstNameModal">Vorname:</label><input type="text" id="racerFirstNameModal" name="first_name" className="form-control" value={racerForm.first_name} onChange={e => handleFormChange(e, 'racer')} required /></div>
                <div className="form-group"><label htmlFor="racerLastNameModal">Nachname:</label><input type="text" id="racerLastNameModal" name="last_name" className="form-control" value={racerForm.last_name} onChange={e => handleFormChange(e, 'racer')} required /></div>
              </div>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--spacing-md)'}}>
                <div className="form-group"><label htmlFor="racerStartNumberModal">Startnummer:</label><input type="text" id="racerStartNumberModal" name="start_number" className="form-control" value={racerForm.start_number || ''} onChange={e => handleFormChange(e, 'racer')} /></div>
                <div className="form-group">
                  <label htmlFor="racerSoapboxClassModal">Klasse:</label>
                  <select id="racerSoapboxClassModal" name="soapbox_class" className="form-control" value={racerForm.soapbox_class} onChange={e => handleFormChange(e, 'racer')}>
                      {soapboxClassOptionsForAdmin.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="racerTeamModal">Team:</label>
                <select id="racerTeamModal" name="team" className="form-control" value={racerForm.team || ''} onChange={e => handleFormChange(e, 'racer')}>
                  <option value="">Kein Team / Einzelstarter</option>
                  {teams.sort((a,b) => a.name.localeCompare(b.name)).map(team => <option key={team.id} value={team.id}>{team.name}</option>)}
                </select>
              </div>
            </>
          )}
          {modalType === 'racerun' && (
            <>
                <div className="form-group">
                    <label htmlFor="runRacerIdModal">Fahrer (ID):</label>
                    <select
                        id="runRacerIdModal"
                        name="racer_id"
                        className="form-control"
                        value={raceRunForm.racer_id || ''}
                        onChange={e => handleFormChange(e, 'racerun')}
                        disabled={!!editingRaceRun && !!editingRaceRun.racer}
                    >
                        <option value="" disabled={!!editingRaceRun || racers.length === 0}>
                            {racers.length === 0 ? "Bitte zuerst Fahrer anlegen" : "Fahrer per ID auswählen..."}
                        </option>
                        {racers.sort((a,b) => (a.full_name || '').localeCompare(b.full_name || '')).map(r =>
                            <option key={r.id} value={r.id}>
                                {r.full_name} (#{r.start_number || 'N/A'}) - {r.soapbox_class_display}
                            </option>
                        )}
                    </select>
                </div>
                <div className="form-group">
                    <label htmlFor="runRacerStartNumberModal">Oder Fahrer (Startnummer):</label>
                    <input
                        type="text"
                        id="runRacerStartNumberModal"
                        name="racer_start_number"
                        className="form-control"
                        placeholder="z.B. S101 oder 123"
                        value={raceRunForm.racer_start_number || ''}
                        onChange={e => handleFormChange(e, 'racerun')}
                        disabled={!!editingRaceRun && !!editingRaceRun.racer}
                    />
                </div>
                <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--spacing-md)'}}>
                    <div className="form-group">
                        <label htmlFor="runTypeModal">Lauftyp:</label>
                        <select id="runTypeModal" name="run_type" className="form-control" value={raceRunForm.run_type} onChange={e => handleFormChange(e, 'racerun')}>
                            {raceRunTypeOptionsForAdmin.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                        </select>
                    </div>
                    <div className="form-group"><label htmlFor="runIdentifierModal">Lauf Nr. (für diesen Typ):</label><input type="number" id="runIdentifierModal" name="run_identifier" className="form-control" min="1" step="1" value={raceRunForm.run_identifier} onChange={e => handleFormChange(e, 'racerun')} required /></div>
                </div>
                <div className="form-group"><label htmlFor="runTimeModal">Zeit (Format: SS.mmm oder SS,mmm):</label><input type="text" id="runTimeModal" name="time_in_seconds" className="form-control" placeholder="z.B. 45.123 oder leer lassen" value={raceRunForm.time_in_seconds || ''} onChange={e => handleFormChange(e, 'racerun')} pattern="^\d*([.,]\d{1,3})?$" title="Erlaubt sind Zahlen mit bis zu 3 Nachkommastellen (z.B. 45.123 oder 45,123 oder 45)"/></div>
                <div className="form-group-checkbox">
                    <input type="checkbox" id="runDisqualifiedModal" name="disqualified" checked={raceRunForm.disqualified} onChange={e => handleFormChange(e, 'racerun')} />
                    <label htmlFor="runDisqualifiedModal">Disqualifiziert (DQ)</label>
                </div>
                <div className="form-group"><label htmlFor="runNotesModal">Notizen (optional):</label><textarea id="runNotesModal" name="notes" className="form-control" value={raceRunForm.notes || ''} onChange={e => handleFormChange(e, 'racerun')} rows={3}></textarea></div>
            </>
          )}
          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={closeModal}>Abbrechen</button>
            <button type="submit" className="btn btn-primary">Speichern</button>
          </div>
        </form>
      </AdminModal>
    </div>
  );
};

export default AdminDashboardPage;