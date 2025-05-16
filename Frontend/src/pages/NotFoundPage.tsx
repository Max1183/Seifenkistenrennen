import React from 'react';
import { Link } from 'react-router-dom';

const NotFoundPage: React.FC = () => {
  return (
    <div className="page-container" style={{ textAlign: 'center' }}>
      <h1>404 - Seite nicht gefunden</h1>
      <p>Ups! Die Seite, die du suchst, existiert leider nicht.</p>
      <p>
        <Link to="/" className="btn">Zurück zur Startseite</Link>
      </p>
    </div>
  );
};

export default NotFoundPage;