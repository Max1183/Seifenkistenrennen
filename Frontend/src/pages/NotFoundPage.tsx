import React from 'react';
import { Link } from 'react-router-dom';

const NotFoundPage: React.FC = () => {
  return (
    <div className="page-container page-enter-animation" style={{ textAlign: 'center', paddingTop: 'var(--spacing-xxl)', paddingBottom: 'var(--spacing-xxl)' }}>
      <h1 style={{ fontSize: '5rem', color: 'var(--text-light-color)', marginBottom: 'var(--spacing-sm)'}}>404</h1>
      <h2 style={{ color: 'var(--heading-color)', marginBottom: 'var(--spacing-md)'}}>Seite nicht gefunden</h2>
      <p style={{color: 'var(--text-light-color)', marginBottom: 'var(--spacing-xl)'}}>
        Ups! Die Seite, die du suchst, existiert leider nicht oder wurde verschoben.
      </p>
      <p>
        <Link to="/" className="btn btn-primary btn-lg">Zurück zur Startseite</Link>
      </p>
    </div>
  );
};

export default NotFoundPage;