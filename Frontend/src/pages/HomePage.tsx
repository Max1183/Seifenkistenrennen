import React from 'react';
import { Link } from 'react-router-dom';

const HomePage: React.FC = () => {
  return (
    <div className="page-container">
      <h1>Willkommen zum Seifenkistenrennen!</h1>
      <p>
        Erlebe spannende Abfahrten, kreative Seifenkisten und einen Tag voller Spaß
        für die ganze Familie. Hier findest du alle wichtigen Informationen
        rund um das Rennen.
      </p>
      <section style={{ marginTop: '2rem', marginBottom: '2rem' }}>
        <h2>Über das Rennen</h2>
        <p>
          Das jährliche Seifenkistenrennen ist ein Highlight für Jung und Alt.
          Teams aus der ganzen Region treten mit selbstgebauten, nicht motorisierten
          Fahrzeugen gegeneinander an.
        </p>
        {/* Weitere Infos hier */}
      </section>
      <Link to="/results" className="btn btn-primary">
        Zu den aktuellen Ergebnissen
      </Link>
    </div>
  );
};

export default HomePage;