import React, { useEffect, useState } from 'react';

// Dummy Daten, später durch API ersetzen
interface Result {
  id: number;
  rank: number;
  name: string;
  team: string;
  time: string;
}

const MOCK_RESULTS: Result[] = [
  { id: 1, rank: 1, name: 'Max Raser', team: 'Blitz-Flitzer', time: '00:45.123' },
  { id: 2, rank: 2, name: 'Lisa Schnell', team: 'Turbo-Schnecken', time: '00:45.890' },
  { id: 3, rank: 3, name: 'Tim Turbo', team: 'Die Düsenjäger', time: '00:46.500' },
  { id: 4, rank: 4, name: 'Anna Kurve', team: 'Blitz-Flitzer', time: '00:47.110' },
];


const ResultsPage: React.FC = () => {
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simuliere API-Aufruf
    setTimeout(() => {
      setResults(MOCK_RESULTS);
      setLoading(false);
    }, 1000); // Simuliere eine Ladezeit
  }, []);

  if (loading) {
    return (
      <div className="page-container">
        <h1>Rennergebnisse</h1>
        <p>Ergebnisse werden geladen...</p>
        {/* Hier könnte ein schönerer Ladeindikator (Spinner) hin */}
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1>Rennergebnisse</h1>
      <p>Die aktuellen Ergebnisse des Seifenkistenrennens.</p>

      {results.length > 0 ? (
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
            {results.map((result, index) => (
              <tr key={result.id} className="list-item-appear" style={{ animationDelay: `${index * 0.05}s` }}>
                <td>{result.rank}</td>
                <td>{result.name}</td>
                <td>{result.team}</td>
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