import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import apiService from '../services/apiService';
import type { AxiosError } from 'axios';

interface AuthContextType {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  isLoading: boolean;
  user: User | null; // Optional: Store user data
}

interface User { // Example user data structure
  username: string;
  // Add other fields that might come from backend upon login/me endpoint
  // e.g., id: number, email: string, first_name: string, last_name: string
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true); // Start true for initial check
  const navigate = useNavigate();
  const location = useLocation();

  const performLogoutActions = useCallback(() => {
    apiService.logout();
    setIsAuthenticated(false);
    setUser(null);
    // Redirect to login, ensuring it's not from a protected route loop
    if (location.pathname.startsWith('/admin') && location.pathname !== '/admin/login') {
        navigate('/admin/login', { replace: true, state: { from: location } });
    } else if (!location.pathname.startsWith('/admin')) {
        // If logout happens outside admin area, just go to login
        navigate('/admin/login', { replace: true });
    }
  }, [navigate, location]);


  useEffect(() => {
    const checkAuthStatus = async () => {
      setIsLoading(true); // Set loading true at the start of the check
      const token = apiService.getAccessToken();
      if (token) {
        // Optionally, verify token with a /api/me endpoint here
        // For now, assume token presence means authenticated
        setIsAuthenticated(true);
        // Example: setUser({ username: 'admin' }); // Replace with actual user data fetching
      } else {
        setIsAuthenticated(false);
      }
      setIsLoading(false);
    };

    checkAuthStatus();

    const handleAuthError = () => {
      // This event is dispatched by apiService on 401 errors after refresh fails
      console.warn("AuthContext: Auth error detected by apiService event. Logging out.");
      performLogoutActions();
    };
    window.addEventListener('authError', handleAuthError);

    return () => {
      window.removeEventListener('authError', handleAuthError);
    };
  }, [performLogoutActions]);

  const login = async (username: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    try {
      await apiService.login(username, password); // Tokens are set by apiService
      setIsAuthenticated(true);
      // Potentially fetch user details here if login response doesn't include them
      // setUser({ username }); // Placeholder
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
      {isLoading ? <div className="app-loading-indicator">App wird geladen...</div> : children}
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