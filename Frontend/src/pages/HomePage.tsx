import React from 'react';
import { Link } from 'react-router-dom';

const HomePage: React.FC = () => {
  return (
    <div className="page-container page-enter-animation">
      <header style={{ textAlign: 'center', marginBottom: 'var(--spacing-xl)' }}>
        <h1>Willkommen zum Seifenkistenrennen!</h1>
        <p style={{ fontSize: '1.1rem', color: 'var(--text-light-color)'}}>
          Erlebe spannende Abfahrten, kreative Seifenkisten und einen Tag voller Spaß
          für die ganze Familie.
        </p>
      </header>

      <section style={{ marginBottom: 'var(--spacing-xl)', lineHeight: '1.7' }}>
        <h2>Über das Rennen</h2>
        <p>
          Das jährliche Seifenkistenrennen, veranstaltet vom CVJM Weissach, ist ein Highlight für Jung und Alt.
          Teams und Einzelfahrer aus der Region und darüber hinaus treten mit ihren selbstgebauten, nicht motorisierten
          Fahrzeugen auf der anspruchsvollen Strecke in Unterweissach gegeneinander an. Bewertet werden nicht nur die Geschwindigkeit,
          sondern oft auch die Kreativität und Originalität der Gefährte.
        </p>
        <p>
          Neben den rasanten Läufen erwartet die Besucher ein buntes Rahmenprogramm mit Verpflegung und Unterhaltung.
          Alle aktuellen Informationen, Zeitpläne und Ergebnisse findest du hier auf unserer Webseite.
        </p>
      </section>

      <div style={{ textAlign: 'center' }}>
        <Link to="/results" className="btn btn-primary btn-lg">
          Zu den aktuellen Ergebnissen
        </Link>
      </div>
    </div>
  );
};

export default HomePage;