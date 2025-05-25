import React, { useEffect, useState, useMemo, useCallback } from 'react';
import ReactDOM from 'react-dom'; 
import apiService from '../services/apiService';
import type { RacerFromAPI, SoapboxClassOption } from '../types'; 
import {
  SOAPBOX_CLASS_DISPLAY_MAP,
  type SoapboxClassValue,
  RACE_RUN_TYPE_DISPLAY_MAP,
  type RaceRunTypeValue,
  DISPLAYED_RUN_TYPES_ORDER
} from '../types';

const parseTimeToSeconds = (time: string | null): number | null => {
  if (!time || time === "N/A") return null;
  const parsed = parseFloat(time);
  return isNaN(parsed) ? null : parsed;
};

const formatSecondsToTime = (totalSeconds: number | null | undefined): string => {
  if (totalSeconds === null || totalSeconds === undefined) return "N/A";
  return totalSeconds.toFixed(3);
};

// Spezieller Wert für den Filter "Einzelstarter"
const SOLO_RACER_FILTER_VALUE = 'SOLO_RACERS_FILTER';

interface RacerDetailModalProps {
  racer: RacerFromAPI | null;
  isOpen: boolean;
  onClose: () => void;
}

const RacerDetailModal: React.FC<RacerDetailModalProps> = ({ racer, isOpen, onClose }) => {
  const modalRoot = document.getElementById('modal-root');

  const modalContent = (
    <div className="modal-overlay modal-enter" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{racer?.full_name} <span style={{fontSize: '1rem', color: 'var(--text-light-color)'}}>(#{racer?.start_number || 'N/A'})</span></h2>
          <button className="modal-close-button" onClick={onClose} aria-label="Schließen">×</button>
        </div>
        <div className="modal-body">
          <p><strong>Team:</strong> {racer?.team_name || 'Einzelstarter'}</p>
          <p><strong>Klasse:</strong> {racer?.soapbox_class_display}</p>
          <p><strong>Beste Zeit:</strong> <span style={{fontWeight: 'bold'}}>{formatSecondsToTime(parseTimeToSeconds(racer?.best_time_seconds || null))}s</span></p>
          {racer?.rank && <p><strong>Platz (Gesamt):</strong> {racer.rank}</p>}

          <h3>Alle Läufe:</h3>
          {racer?.races && racer.races.length > 0 ? (
            <div className="table-wrapper">
              <table className="results-table compact-table">
                <thead>
                  <tr>
                    <th>Lauf</th>
                    <th>Zeit (s)</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {DISPLAYED_RUN_TYPES_ORDER
                    .map(runKey => {
                      const run = racer.races.find(r => r.run_type === runKey);
                      if (!run) {
                        return null; 
                      }
                      return (
                        <tr key={`${run.run_type}-${run.run_identifier}`}>
                          <td>{run.run_type_display} {run.run_identifier > 1 ? run.run_identifier : ''}</td>
                          <td>{run.disqualified ? 'DQ' : formatSecondsToTime(parseTimeToSeconds(run.time_in_seconds))}</td>
                          <td>{run.disqualified ? <span style={{color: 'var(--danger-color)'}}>DQ</span> : (run.time_in_seconds ? 'OK' : 'N/A')}</td>
                        </tr>
                      );
                  })}
                </tbody>
              </table>
            </div>
          ) : <p>Keine Rennläufe erfasst.</p>}
        </div>
      </div>
    </div>
  );

  if (!isOpen || !racer || !modalRoot) return null;

  return ReactDOM.createPortal(modalContent, modalRoot);
};

type SortableRacerKey = keyof Pick<RacerFromAPI, 'full_name' | 'team_name' | 'soapbox_class_display' | 'best_time_seconds' | 'rank'> | `time_${RaceRunTypeValue}`;

interface TeamOption {
    value: number | '' | typeof SOLO_RACER_FILTER_VALUE; // Team ID, leer für "Alle", oder spezieller String
    label: string;
}

const ResultsPage: React.FC = () => {
  const [allRacers, setAllRacers] = useState<RacerFromAPI[]>([]);
  const [filteredAndSortedRacers, setFilteredAndSortedRacers] = useState<RacerFromAPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [selectedClass, setSelectedClass] = useState<SoapboxClassValue | ''>('');
  const [selectedTeam, setSelectedTeam] = useState<number | '' | typeof SOLO_RACER_FILTER_VALUE>(''); // State für Team-Filter angepasst

  const [sortConfig, setSortConfig] = useState<{ key: SortableRacerKey; direction: 'ascending' | 'descending' }>({
    key: 'best_time_seconds',
    direction: 'ascending',
  });
  const [selectedRacer, setSelectedRacer] = useState<RacerFromAPI | null>(null);

  const soapboxClassOptions: SoapboxClassOption[] = useMemo(() => {
    return Object.entries(SOAPBOX_CLASS_DISPLAY_MAP).map(([value, label]) => ({
        value: value as SoapboxClassValue,
        label
    })).sort((a,b) => a.label.localeCompare(b.label));
  }, []);

  const teamOptions: TeamOption[] = useMemo(() => {
    if (!allRacers.length) return [];
    const teamsMap = new Map<number, string>();
    let hasSoloRacers = false;
    allRacers.forEach(racer => {
        if (racer.team && racer.team_name) {
            teamsMap.set(racer.team, racer.team_name);
        } else if (racer.team === null) {
            hasSoloRacers = true;
        }
    });
    
    const options: TeamOption[] = Array.from(teamsMap.entries()).map(([id, name]) => ({
        value: id,
        label: name
    }));

    if (hasSoloRacers) {
        options.push({ value: SOLO_RACER_FILTER_VALUE, label: 'Einzelstarter' });
    }
    
    return options.sort((a, b) => {
        // "Einzelstarter" ans Ende der Teamliste (oder an den Anfang, je nach Präferenz)
        if (a.value === SOLO_RACER_FILTER_VALUE) return 1;
        if (b.value === SOLO_RACER_FILTER_VALUE) return -1;
        return a.label.localeCompare(b.label);
    });
  }, [allRacers]);


  useEffect(() => {
    const fetchRacersData = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiService.getRacers(); 
        setAllRacers(data);
      } catch (err) {
        console.error("Failed to fetch racers data:", err);
        setError("Teilnehmerdaten konnten nicht geladen werden.");
      } finally {
        setLoading(false);
      }
    };
    fetchRacersData();
  }, []); 

  useEffect(() => {
    let processedRacers = [...allRacers];

    if (selectedClass) {
        processedRacers = processedRacers.filter(r => r.soapbox_class === selectedClass);
    }

    if (selectedTeam === SOLO_RACER_FILTER_VALUE) {
        processedRacers = processedRacers.filter(r => r.team === null);
    } else if (selectedTeam !== '') { 
        processedRacers = processedRacers.filter(r => r.team === selectedTeam);
    }

    const rankedRacers = processedRacers
        .filter(r => parseTimeToSeconds(r.best_time_seconds) !== null)
        .sort((a, b) => (parseTimeToSeconds(a.best_time_seconds) ?? Infinity) - (parseTimeToSeconds(b.best_time_seconds) ?? Infinity))
        .map((r, index) => ({ ...r, rank: index + 1 }));

    const unrankedRacers = processedRacers.filter(r => parseTimeToSeconds(r.best_time_seconds) === null).map(r => ({ ...r, rank: undefined }));
    
    processedRacers = [...rankedRacers, ...unrankedRacers];

    processedRacers.sort((a, b) => {
      let valA: string | number | null | undefined;
      let valB: string | number | null | undefined;

      if (sortConfig.key.startsWith('time_')) {
        const runType = sortConfig.key.substring(5) as RaceRunTypeValue;
        const getRunTime = (racer: RacerFromAPI) => {
          const run = racer.races.find(race => race.run_type === runType && !race.disqualified);
          return run ? parseTimeToSeconds(run.time_in_seconds) : null;
        };
        valA = getRunTime(a);
        valB = getRunTime(b);
      } else {
        const key = sortConfig.key as keyof RacerFromAPI; 
        const valueA = a[key];
        const valueB = b[key];
        valA = Array.isArray(valueA) ? undefined : valueA;
        valB = Array.isArray(valueB) ? undefined : valueB;

        if (sortConfig.key === 'best_time_seconds') {
            valA = parseTimeToSeconds(a.best_time_seconds);
            valB = parseTimeToSeconds(b.best_time_seconds);
        } else if (sortConfig.key === 'rank') { 
            valA = a.rank;
            valB = b.rank;
        }
      }
      
      const isAsc = sortConfig.direction === 'ascending';
      if (valA === null || valA === undefined) return (valB === null || valB === undefined) ? 0 : (isAsc ? 1 : -1);
      if (valB === null || valB === undefined) return isAsc ? -1 : 1;


      if (typeof valA === 'string' && typeof valB === 'string') {
        return isAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }
      if (typeof valA === 'number' && typeof valB === 'number') {
        return isAsc ? valA - valB : valB - valA;
      }
      return 0;
    });
    setFilteredAndSortedRacers(processedRacers);
  }, [allRacers, selectedClass, selectedTeam, sortConfig]);

  const requestSort = useCallback((key: SortableRacerKey) => {
    setSortConfig(prevConfig => ({
      key,
      direction: prevConfig.key === key && prevConfig.direction === 'ascending' ? 'descending' : 'ascending',
    }));
  }, []);

  const getSortIndicator = useCallback((key: SortableRacerKey) => {
    if (sortConfig.key === key) {
      return sortConfig.direction === 'ascending' ? '▲' : '▼';
    }
    return '';
  }, [sortConfig]);

  const getRaceTimeForTable = useCallback((racer: RacerFromAPI, runType: RaceRunTypeValue, runIdentifier: number = 1) => {
    const raceRun = racer.races.find(r => r.run_type === runType && r.run_identifier === runIdentifier);
    if (!raceRun) return 'N/A';
    if (raceRun.disqualified) return <span style={{color: 'var(--danger-color)', fontWeight: 'bold'}}>DQ</span>;
    return formatSecondsToTime(parseTimeToSeconds(raceRun.time_in_seconds));
  }, []);

  const handleTeamChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value === '') {
        setSelectedTeam('');
    } else if (value === SOLO_RACER_FILTER_VALUE) {
        setSelectedTeam(SOLO_RACER_FILTER_VALUE);
    } else {
        setSelectedTeam(Number(value));
    }
  };

  if (loading) return <div className="page-container results-loading"><p>Lade Rennergebnisse...</p></div>;
  if (error) return <div className="page-container results-error-message"><p>Fehler: {error}</p></div>;

  return (
    <div className="results-page page-enter-animation">
      <h1>Rennergebnisse</h1>
      <div className="filters-container">
        <div className="filter-group">
            <label htmlFor="classFilter">Klasse filtern:</label>
            <select
            id="classFilter"
            className="form-control"
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value as SoapboxClassValue | '')}
            >
            <option value="">Alle Klassen</option>
            {soapboxClassOptions.map(sc => (
                <option key={sc.value} value={sc.value}>{sc.label}</option>
            ))}
            </select>
        </div>
        <div className="filter-group">
            <label htmlFor="teamFilter">Team filtern:</label>
            <select
            id="teamFilter"
            className="form-control"
            value={selectedTeam} // Kann jetzt '', number oder SOLO_RACER_FILTER_VALUE sein
            onChange={handleTeamChange}
            >
            <option value="">Alle Teams</option>
            {teamOptions.map(team => (
                <option key={team.value.toString()} value={team.value}>{team.label}</option>
            ))}
            </select>
        </div>
      </div>

      {filteredAndSortedRacers.length > 0 ? (
        <div className="table-wrapper">
          <table className="results-table">
            <thead>
              <tr>
                <th onClick={() => requestSort('rank')} className="sortable-header">
                  Platz <span className="sort-indicator">{getSortIndicator('rank')}</span>
                </th>
                <th onClick={() => requestSort('full_name')} className="sortable-header">
                  Name <span className="sort-indicator">{getSortIndicator('full_name')}</span>
                </th>
                <th onClick={() => requestSort('team_name')} className="sortable-header">
                  Team <span className="sort-indicator">{getSortIndicator('team_name')}</span>
                </th>
                <th onClick={() => requestSort('soapbox_class_display')} className="sortable-header">
                  Klasse <span className="sort-indicator">{getSortIndicator('soapbox_class_display')}</span>
                </th>
                {DISPLAYED_RUN_TYPES_ORDER.map((runTypeKey) => (
                  <th key={runTypeKey} onClick={() => requestSort(`time_${runTypeKey}`)} className="sortable-header">
                    {RACE_RUN_TYPE_DISPLAY_MAP[runTypeKey]}
                    <span className="sort-indicator">{getSortIndicator(`time_${runTypeKey}`)}</span>
                  </th>
                ))}
                <th onClick={() => requestSort('best_time_seconds')} className="sortable-header">
                  Beste Zeit <span className="sort-indicator">{getSortIndicator('best_time_seconds')}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedRacers.map((racer) => (
                <tr key={racer.id} onClick={() => setSelectedRacer(racer)} className="clickable-row">
                  <td style={{textAlign: 'center'}}>{racer.rank || '-'}</td>
                  <td>{racer.full_name}</td>
                  <td>{racer.team_name || 'Einzelstarter'}</td>
                  <td>{racer.soapbox_class_display}</td>
                  {DISPLAYED_RUN_TYPES_ORDER.map(runKey => (
                    <td key={`${racer.id}-${runKey}`}>{getRaceTimeForTable(racer, runKey, 1)}</td>
                  ))}
                  <td style={{fontWeight: 'bold'}}>{formatSecondsToTime(parseTimeToSeconds(racer.best_time_seconds))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p style={{marginTop: 'var(--spacing-lg)'}}>
            {allRacers.length === 0 && !loading ? 'Es wurden noch keine Daten geladen oder es sind keine Daten vorhanden.' : 
             !loading ? 'Keine Teilnehmer für die ausgewählten Filter gefunden.' : ''}
        </p>
      )}
      <RacerDetailModal racer={selectedRacer} isOpen={!!selectedRacer} onClose={() => setSelectedRacer(null)} />
    </div>
  );
};

export default ResultsPage;