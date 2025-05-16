import React, { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../contexts/AuthContext';

const AdminLoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const auth = useAuth();
  // const navigate = useNavigate(); // Wird jetzt vom AuthContext gehandhabt

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null); // Fehler zurücksetzen
    if (!auth) return;

    const success = await auth.login(username, password);
    if (!success) {
      setError('Login fehlgeschlagen. Bitte Benutzername und Passwort überprüfen.');
    }
    // Die Navigation erfolgt jetzt innerhalb der auth.login Methode bei Erfolg
  };

  return (
    <div className="page-container" style={{ maxWidth: '500px' }}>
      <h1>Admin Login</h1>
      <form onSubmit={handleSubmit}>
        {error && <p style={{ color: 'var(--danger-color)' }}>{error}</p>}
        <div>
          <label htmlFor="username">Benutzername:</label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={auth.isLoading}
          />
        </div>
        <div>
          <label htmlFor="password">Passwort:</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={auth.isLoading}
          />
        </div>
        <button type="submit" className="btn" disabled={auth.isLoading}>
          {auth.isLoading ? 'Melde an...' : 'Anmelden'}
        </button>
      </form>
    </div>
  );
};

export default AdminLoginPage;