// src/contexts/AuthContext.tsx

import React, { useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import apiService from '../services/apiService';
import type { AxiosError } from 'axios';
import { type User, AuthContext } from './useAuth'; // Assuming User type is defined in ../types/User


// Der Provider bleibt der einzige andere Export. Das ist jetzt konform.
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
    if (location.pathname.startsWith('/admin') && location.pathname !== '/admin/login') {
        navigate('/admin/login', { replace: true, state: { from: location } });
    } else if (!location.pathname.startsWith('/admin')) {
        navigate('/admin/login', { replace: true });
    }
  }, [navigate, location]);


  useEffect(() => {
    const checkAuthStatus = async () => {
      setIsLoading(true); // Set loading true at the start of the check
      const token = apiService.getAccessToken();
      if (token) {
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
      }
      setIsLoading(false);
    };

    checkAuthStatus();

    const handleAuthError = () => {
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
      await apiService.login(username, password);
      setIsAuthenticated(true);
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