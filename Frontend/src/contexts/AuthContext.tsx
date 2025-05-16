import React, { createContext, useState, useContext, useEffect } from 'react';
import type { ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

interface AuthContextType {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<boolean>; // Simuliert einen API-Aufruf
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true); // Startet als true, um den initialen Check abzuwarten
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Prüfe beim Laden der App, ob ein Token vorhanden ist
    const token = localStorage.getItem('adminToken');
    if (token) {
      // Hier könntest du das Token validieren (z.B. mit einem API-Aufruf)
      // Für dieses Beispiel nehmen wir an, ein vorhandenes Token ist gültig
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);


  const login = async (username: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    // === SIMULIERTER API AUFRUF ===
    // In einer echten App:
    // try {
    //   const response = await apiService.login(username, password);
    //   localStorage.setItem('adminToken', response.token);
    //   setIsAuthenticated(true);
    //   setIsLoading(false);
    //   return true;
    // } catch (error) {
    //   console.error("Login failed", error);
    //   setIsAuthenticated(false);
    //   setIsLoading(false);
    //   return false;
    // }

    // Nur für dieses Beispiel:
    return new Promise((resolve) => {
      setTimeout(() => {
        if (username === 'admin' && password === 'password') {
          localStorage.setItem('adminToken', 'dummy-jwt-token'); // Speichere einen Dummy-Token
          setIsAuthenticated(true);
          console.log("Login successful, navigating...");
          const origin = location.state?.from?.pathname || '/admin';
          navigate(origin, { replace: true });
          resolve(true);
        } else {
          setIsAuthenticated(false);
          resolve(false);
        }
        setIsLoading(false);
      }, 1000);
    });
    // === ENDE SIMULIERTER API AUFRUF ===
  };

  const logout = () => {
    localStorage.removeItem('adminToken');
    setIsAuthenticated(false);
    navigate('/admin/login');
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, isLoading }}>
      {children}
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