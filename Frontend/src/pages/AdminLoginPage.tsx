import React, { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../contexts/useAuth';

const AdminLoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const auth = useAuth();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!auth) return; // Should not happen if AuthProvider is correctly set up

    const success = await auth.login(username, password);
    if (!success) {
      setError('Login fehlgeschlagen. Bitte Benutzername und Passwort überprüfen.');
    }
    // Navigation is handled by AuthContext on successful login
  };

  return (
    <div className="page-container page-enter-animation" style={{ maxWidth: '450px', margin: 'var(--spacing-xl) auto' }}>
      <h1>Admin Login</h1>
      <form onSubmit={handleSubmit}>
        {error && <p style={{ color: 'var(--danger-color)', marginBottom: 'var(--spacing-md)' }}>{error}</p>}
        <div className="form-group">
          <label htmlFor="username">Benutzername:</label>
          <input
            type="text"
            id="username"
            className="form-control"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
            disabled={auth.isLoading}
          />
        </div>
        <div className="form-group">
          <label htmlFor="password">Passwort:</label>
          <input
            type="password"
            id="password"
            className="form-control"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={auth.isLoading}
          />
        </div>
        <button type="submit" className="btn btn-primary btn-lg" style={{width: '100%'}} disabled={auth.isLoading}>
          {auth.isLoading ? 'Melde an...' : 'Anmelden'}
        </button>
      </form>
    </div>
  );
};

export default AdminLoginPage;