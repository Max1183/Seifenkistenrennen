import React, { useEffect, useState } from 'react';
import apiService from '../services/apiService'; // Importieren

interface RacerFromAPI { // Definiere die Struktur, die deine API zurückgibt
  id: number;
  full_name: string;
  team: number | null; // Annahme: API gibt Team-ID zurück
  team_name?: string; // Optional, wenn du es im Frontend anreichern willst oder vom Backend bekommst
  best_time?: string; // Dieses Feld müsstest du im Backend berechnen und hinzufügen
}

const ResultsPage: React.FC = () => {
  // Hier müsstest du eigentlich Rennergebnisse laden, nicht nur Racer
  // Für dieses Beispiel laden wir Racer und Teams und simulieren eine Rangliste
  const [racers, setRacers] = useState<RacerFromAPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchResultsData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Idealerweise hättest du einen Endpunkt /api/race-results/
        // der bereits sortierte Ergebnisse liefert.
        // Für dieses Beispiel holen wir Racer und Teams separat.
        const racersData = await apiService.getRacers();
        // const teamsData = await apiService.getTeams(); // Falls du Teamnamen brauchst und sie nicht im Racer-Objekt sind

        // Hier müsstest du die Daten ggf. transformieren oder anreichern
        // z.B. Teamnamen zuordnen, Zeiten formatieren, Rang berechnen
        // Diese Logik gehört eigentlich ins Backend oder in einen speziellen Service.
        const processedRacers = racersData.map((racer: any, index: number) => ({
            ...racer,
            rank: index + 1, // Dummy-Rang
            time: racer.best_time || `00:${45 + index}.${123 + index*50}`, // Dummy-Zeit
            team_name: racer.team_details?.name || (racer.team ? `Team ID ${racer.team}` : 'Einzelstarter')
        }));

        setRacers(processedRacers);
      } catch (err) {
        console.error("Failed to fetch results data:", err);
        setError("Ergebnisse konnten nicht geladen werden.");
      } finally {
        setLoading(false);
      }
    };

    fetchResultsData();
  }, []);

  if (loading) {
    return (
      <div className="page-container">
        <h1>Rennergebnisse</h1>
        <p>Ergebnisse werden geladen...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <h1>Rennergebnisse</h1>
        <p style={{ color: 'var(--danger-color)' }}>{error}</p>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1>Rennergebnisse</h1>
      {racers.length > 0 ? (
        <table className="results-table">
          <thead>
            <tr>
              <th>Platz</th>
              <th>Name</th>
              <th>Team</th>
              <th>Zeit</th>
            </tr>
          </thead>
          <tbody>
            {racers.map((result, index) => (
              <tr key={result.id} className="list-item-appear" style={{ animationDelay: `${index * 0.05}s` }}>
                <td>{result.rank}</td>
                <td>{result.full_name}</td>
                <td>{result.team_name}</td>
                <td>{result.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>Noch keine Ergebnisse vorhanden.</p>
      )}
    </div>
  );
};

export default ResultsPage;