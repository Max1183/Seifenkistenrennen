import React, { createContext, useState, useContext, useEffect } from 'react';
import type { ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import apiService from '../services/apiService'; // Importiere den apiService
import type { AxiosError } from 'axios'; // Für Typsicherheit bei Fehlern

interface AuthContextType {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  isLoading: boolean;
  user: User | null; // Optional: Benutzerdaten speichern
}

interface User { // Beispiel für Benutzerdaten
  username: string;
  // Weitere Felder, die vom Backend beim Login kommen könnten
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null); // Optional
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const checkAuthStatus = async () => {
      const token = apiService.getAccessToken();
      if (token) {
        // Optional: Hier könntest du /api/user/me/ (oder ähnlichen Endpunkt) aufrufen,
        // um Benutzerdaten zu holen und die Gültigkeit des Tokens zu prüfen.
        // Für dieses Beispiel nehmen wir an, ein vorhandenes Token ist gültig.
        setIsAuthenticated(true);
        // setUser({ username: 'admin' }); // Placeholder, hole echte Daten vom Backend
      }
      setIsLoading(false);
    };

    checkAuthStatus();

    // Listener für Authentifizierungsfehler vom apiService
    const handleAuthError = () => {
      console.log("AuthContext: Auth error detected, logging out.");
      performLogoutActions();
    };
    window.addEventListener('authError', handleAuthError);

    return () => {
      window.removeEventListener('authError', handleAuthError);
    };

  }, []);

  const performLogoutActions = () => {
    apiService.logout();
    setIsAuthenticated(false);
    setUser(null);
    navigate('/admin/login', { replace: true });
  };

  const login = async (username: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    try {
      await apiService.login(username, password);
      setIsAuthenticated(true);
      // Optional: Benutzerdaten vom Token oder einem /me Endpunkt holen und setUser(...)
      // setUser({ username }); // Einfacher Platzhalter
      setIsLoading(false);
      const origin = location.state?.from?.pathname || '/admin';
      navigate(origin, { replace: true });
      return true;
    } catch (error) {
      const axiosError = error as AxiosError;
      console.error("Login failed in AuthContext:", axiosError.response?.data || axiosError.message);
      setIsAuthenticated(false);
      setUser(null);
      setIsLoading(false);
      return false;
    }
  };

  const logout = () => {
    performLogoutActions();
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout, isLoading }}>
      {!isLoading ? children : <div className="page-container" style={{textAlign: 'center'}}>App wird geladen...</div>} {/* Zeige Ladeindikator, solange isLoading true ist */}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};