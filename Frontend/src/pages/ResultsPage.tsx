import React, { useEffect, useState, useMemo } from 'react';
import apiService from '../services/apiService';
import type { RacerFrontend, SoapboxClassOption } from '../types';

// Hilfsfunktion zum Konvertieren der Zeit in Sekunden (oder null)
const parseTimeToSeconds = (time: string | null): number | null => {
  if (time === null || time === undefined || time === "N/A") return null;
  const parsed = parseFloat(time);
  return isNaN(parsed) ? null : parsed;
};

// Hilfsfunktion zum Formatieren von Sekunden in MM:SS.mmm oder SS.mmm
const formatSecondsToTime = (totalSeconds: number | null | undefined, includeMinutes = false): string => {
  if (totalSeconds === null || totalSeconds === undefined) return "N/A";
  if (includeMinutes) {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, '0')}:${seconds.toFixed(3).padStart(6, '0')}`;
  }
  return totalSeconds.toFixed(3);
};

// Konstanten für Rennläufe (um sie in der Tabelle anzuzeigen)
const RUN_TYPES_ORDER: Record<string, string> = {
  'PR': 'Practice', // Oder wie es in deinem run_type_display steht
  'H1': 'Heat 1',
  'H2': 'Heat 2',
  // Füge hier weitere hinzu, falls nötig, in der gewünschten Reihenfolge
};


// Einfaches Modal für Racer-Details
interface RacerDetailModalProps {
  racer: RacerFrontend | null;
  isOpen: boolean;
  onClose: () => void;
}
const RacerDetailModal: React.FC<RacerDetailModalProps> = ({ racer, isOpen, onClose }) => {
  if (!isOpen || !racer) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close-button" onClick={onClose}>×</button>
        <h2>{racer.full_name}</h2>
        <p><strong>Team:</strong> {racer.team_name || 'Einzelstarter'}</p>
        <p><strong>Klasse:</strong> {racer.soapbox_class_display}</p>
        <p><strong>Beste Zeit:</strong> {formatSecondsToTime(parseTimeToSeconds(racer.best_time_seconds))}s</p>
        <p><strong>Platz:</strong> {racer.rank || 'N/A'}</p>
        <h3>Alle Läufe:</h3>
        {racer.races.length > 0 ? (
          <table className="results-table compact-table">
            <thead>
              <tr>
                <th>Lauf</th>
                <th>Zeit (s)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(RUN_TYPES_ORDER).map(runKey => {
                 const run = racer.races.find(r => r.run_type === runKey);
                 if (!run) return null; // oder eine leere Zeile rendern
                 return (
                    <tr key={`${run.run_type}-${run.run_identifier}`}>
                      <td>{run.run_type_display} {run.run_identifier > 1 ? run.run_identifier : ''}</td>
                      <td>{run.disqualified ? 'DQ' : formatSecondsToTime(parseTimeToSeconds(run.time_in_seconds))}</td>
                      <td>{run.disqualified ? 'Disqualifiziert' : (run.time_in_seconds ? 'OK' : 'N/A')}</td>
                    </tr>
                 );
              })}
            </tbody>
          </table>
        ) : <p>Keine Rennläufe erfasst.</p>}
        {/* Weitere Details hier... */}
      </div>
    </div>
  );
};


const ResultsPage: React.FC = () => {
  const [allRacers, setAllRacers] = useState<RacerFrontend[]>([]);
  const [filteredRacers, setFilteredRacers] = useState<RacerFrontend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedClass, setSelectedClass] = useState<string>(''); // Filter nach Klasse
  const [sortConfig, setSortConfig] = useState<{ key: keyof RacerFrontend | string; direction: 'ascending' | 'descending' }>({
    key: 'best_time_seconds', // Standard-Sortierung
    direction: 'ascending',
  });
  const [selectedRacer, setSelectedRacer] = useState<RacerFrontend | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const soapboxClasses: SoapboxClassOption[] = useMemo(() => {
    if (allRacers.length === 0) return [];
    const classes = new Map<string, string>();
    allRacers.forEach(racer => {
      if (!classes.has(racer.soapbox_class)) {
        classes.set(racer.soapbox_class, racer.soapbox_class_display);
      }
    });
    return Array.from(classes.entries()).map(([value, label]) => ({ value, label }));
  }, [allRacers]);


  useEffect(() => {
    const fetchRacersData = async () => {
      setLoading(true);
      setError(null);
      try {
        const params: Record<string, string> = {};
        if (selectedClass) {
          params.soapbox_class = selectedClass;
        }
        const data = await apiService.getRacers(params);
        setAllRacers(data); // Speichere alle Racer für client-seitiges Filtern/Sortieren, falls API keine Sortierung hat
                            // oder passe an, wenn die API Filterung und Sortierung übernimmt.
      } catch (err) {
        console.error("Failed to fetch racers data:", err);
        setError("Teilnehmerdaten konnten nicht geladen werden.");
      } finally {
        setLoading(false);
      }
    };
    fetchRacersData();
  }, [selectedClass]); // Neu laden, wenn sich der Klassenfilter ändert

  // Client-seitige Filterung und Sortierung (kann auch serverseitig erfolgen)
  useEffect(() => {
    let processedRacers = [...allRacers];

    // Rangberechnung bleibt gleich (oder wird hier nicht mehr benötigt, wenn die Sortierung das übernimmt)
    const racersWithRank = processedRacers
      .filter(racer => parseTimeToSeconds(racer.best_time_seconds) !== null)
      .sort((a, b) => {
        const timeA = parseTimeToSeconds(a.best_time_seconds) ?? Infinity;
        const timeB = parseTimeToSeconds(b.best_time_seconds) ?? Infinity;
        return timeA - timeB;
      })
      .map((racer, index) => ({ ...racer, rank: index + 1 }));

    const racersWithoutTime = processedRacers.filter(racer => parseTimeToSeconds(racer.best_time_seconds) === null);
    let displayRacers = [...racersWithRank, ...racersWithoutTime];

    // Sortierung
    if (sortConfig.key) {
      displayRacers.sort((a, b) => {
        let valA: any;
        let valB: any;

        // Extrahiere die Werte basierend auf dem Sortierschlüssel
        if (sortConfig.key === 'best_time_seconds' || sortConfig.key.startsWith('time_')) {
          const getTime = (racer: RacerFrontend, key: string) => {
            if (key === 'best_time_seconds') return parseTimeToSeconds(racer.best_time_seconds);
            const [, runType, runIdStr] = key.split('_');
            const runId = parseInt(runIdStr); // Annahme: runIdStr ist immer eine Zahl
            const run = racer.races.find(r => r.run_type === runType && r.run_identifier === runId && !r.disqualified);
            return run ? parseTimeToSeconds(run.time_in_seconds) : null;
          };
          valA = getTime(a, sortConfig.key);
          valB = getTime(b, sortConfig.key);
        } else if (sortConfig.key === 'full_name') {
          valA = a.full_name.toLowerCase();
          valB = b.full_name.toLowerCase();
        } else if (sortConfig.key === 'rank') {
          valA = a.rank; // Bereits eine Zahl oder undefined
          valB = b.rank; // Bereits eine Zahl oder undefined
        } else if (sortConfig.key === 'soapbox_class_display') {
          valA = a.soapbox_class_display.toLowerCase();
          valB = b.soapbox_class_display.toLowerCase();
        } else if (sortConfig.key === 'team_name') {
          valA = (a.team_name ?? '').toLowerCase();
          valB = (b.team_name ?? '').toLowerCase();
        } else {
          valA = a[sortConfig.key as keyof RacerFrontend];
          valB = b[sortConfig.key as keyof RacerFrontend];
        }

        // Behandlung von null/undefined für die Sortierung (numerisch und Strings)
        // Für numerische Sortierung (Zeiten, Rang)
        if (typeof valA === 'number' || valA === null || valA === undefined) {
            // Wenn null/undefined, setze auf einen Wert, der sie ans Ende/Anfang sortiert
            const numA = valA === null || valA === undefined ? (sortConfig.direction === 'ascending' ? Infinity : -Infinity) : valA;
            const numB = valB === null || valB === undefined ? (sortConfig.direction === 'ascending' ? Infinity : -Infinity) : valB;

            if (numA < numB) return sortConfig.direction === 'ascending' ? -1 : 1;
            if (numA > numB) return sortConfig.direction === 'ascending' ? 1 : -1;
            return 0;
        }
        // Für String-Sortierung (Name, Klasse)
        else if (typeof valA === 'string' && typeof valB === 'string') {
          return sortConfig.direction === 'ascending' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        // Fallback, falls Typen gemischt oder unerwartet sind (sollte nicht oft passieren mit TypeScript)
        return 0;
      });
    }
    setFilteredRacers(displayRacers);
  }, [allRacers, sortConfig, selectedClass]);


  const requestSort = (key: keyof RacerFrontend | string) => {
    let direction: 'ascending' | 'descending' = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
  };

  const getSortIndicator = (key: keyof RacerFrontend | string) => {
    if (sortConfig.key === key) {
      return sortConfig.direction === 'ascending' ? ' ▲' : ' ▼';
    }
    return '';
  };

  const handleRacerClick = (racer: RacerFrontend) => {
    setSelectedRacer(racer);
    setIsModalOpen(true);
  };

  const getRaceTimeForTable = (racer: RacerFrontend, runType: string, runIdentifier: number = 1) => {
    const raceRun = racer.races.find(r => r.run_type === runType && r.run_identifier === runIdentifier);
    if (!raceRun) return 'N/A';
    if (raceRun.disqualified) return 'DQ';
    return formatSecondsToTime(parseTimeToSeconds(raceRun.time_in_seconds));
  };


  if (loading) return <div className="page-container results-loading">Lade Ergebnisse...</div>;
  if (error) return <div className="page-container results-error">Fehler: {error}</div>;

  return (
    <div className="page-container results-page">
      <h1>Rennergebnisse</h1>
      <div className="filters-container">
        <label htmlFor="classFilter">Klasse filtern: </label>
        <select
          id="classFilter"
          value={selectedClass}
          onChange={(e) => setSelectedClass(e.target.value)}
        >
          <option value="">Alle Klassen</option>
          {soapboxClasses.map(sc => (
            <option key={sc.value} value={sc.value}>{sc.label}</option>
          ))}
        </select>
      </div>

      {filteredRacers.length > 0 ? (
        <div className="table-responsive">
          <table className="results-table">
            <thead>
              <tr>
                <th onClick={() => requestSort('rank')}>Platz {getSortIndicator('rank')}</th>
                <th onClick={() => requestSort('full_name')}>Name {getSortIndicator('full_name')}</th>
                <th onClick={() => requestSort('team_name')}>Team {getSortIndicator('team_name')}</th>
                <th onClick={() => requestSort('soapbox_class_display')}>Klasse {getSortIndicator('soapbox_class_display')}</th>
                {Object.entries(RUN_TYPES_ORDER).map(([key, label]) => (
                    <th key={key} onClick={() => requestSort(`time_${key}_1`)}>{label} {getSortIndicator(`time_${key}_1`)}</th>
                ))}
                <th onClick={() => requestSort('best_time_seconds')}>Beste Zeit {getSortIndicator('best_time_seconds')}</th>
              </tr>
            </thead>
            <tbody>
              {filteredRacers.map((racer) => (
                <tr key={racer.id} onClick={() => handleRacerClick(racer)} className="clickable-row">
                  <td>{racer.rank || '-'}</td>
                  <td>{racer.full_name}</td>
                  <td>{racer.team_name || 'Einzelstarter'}</td>
                  <td>{racer.soapbox_class_display}</td> {/* Anzeige der Klasse */}
                  {Object.keys(RUN_TYPES_ORDER).map(runKey => (
                    <td key={`${racer.id}-${runKey}`}>{getRaceTimeForTable(racer, runKey, 1)}</td>
                  ))}
                  <td>{formatSecondsToTime(parseTimeToSeconds(racer.best_time_seconds))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>Keine Teilnehmer für die ausgewählten Filter gefunden.</p>
      )}
      <RacerDetailModal racer={selectedRacer} isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
};

export default ResultsPage;