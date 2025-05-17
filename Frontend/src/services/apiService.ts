// src/services/apiService.ts
import axios, { AxiosError } from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import type { RacerFromAPI, RacerData } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

interface TokenPair {
  access: string;
  refresh: string;
}

// Hilfsfunktionen für Tokens
const getAccessToken = (): string | null => localStorage.getItem('accessToken');
const getRefreshToken = (): string | null => localStorage.getItem('refreshToken');
const setTokens = (tokens: TokenPair): void => {
  localStorage.setItem('accessToken', tokens.access);
  localStorage.setItem('refreshToken', tokens.refresh);
};
const clearTokens = (): void => {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
};

// Erstelle eine Axios-Instanz
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Fügt den Access Token zu jedem Request hinzu, falls vorhanden
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: Handhabt Token-Refresh bei 401-Fehlern
// Dies ist eine vereinfachte Version. In einer Produktions-App wäre dies robuster.
let isRefreshing = false;
let failedQueue: Array<{ resolve: (value?: any) => void; reject: (reason?: any) => void }> = [];

const processQueue = (error: AxiosError | null, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
        .then(token => {
          if (originalRequest.headers) {
            originalRequest.headers['Authorization'] = 'Bearer ' + token;
          }
          return apiClient(originalRequest);
        })
        .catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;
      const localRefreshToken = getRefreshToken();

      if (localRefreshToken) {
        try {
          const { data } = await axios.post<TokenPair>(`${API_BASE_URL}/token/refresh/`, {
            refresh: localRefreshToken,
          });
          setTokens(data);
          if (originalRequest.headers) {
             originalRequest.headers.Authorization = `Bearer ${data.access}`;
          }
          processQueue(null, data.access);
          return apiClient(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError as AxiosError, null);
          clearTokens();
          // Hier könntest du den Benutzer zur Login-Seite weiterleiten
          window.dispatchEvent(new Event('authError')); // Event für AuthContext zum Abhören
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      } else {
        // Kein Refresh-Token vorhanden, leite zum Login oder werfe Fehler
        clearTokens();
        window.dispatchEvent(new Event('authError'));
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);


// Authentifizierungs-Funktionen
const login = async (username: string, password: string): Promise<TokenPair> => {
  const response = await apiClient.post<TokenPair>('/token/', { username, password });
  setTokens(response.data);
  return response.data;
};

const logout = (): void => {
  // Optional: Informiere das Backend über den Logout (Invalidierung des Refresh-Tokens)
  // const refreshToken = getRefreshToken();
  // if (refreshToken) {
  //   apiClient.post('/auth/logout/', { refresh: refreshToken }).catch(console.error);
  // }
  clearTokens();
};


// --- Generische CRUD-Funktionen oder spezifische Service-Funktionen ---
// Beispiel für Teams
const getTeams = async () => {
  const response = await apiClient.get('/teams/');
  return response.data;
};

const getTeamById = async (id: number | string) => {
  const response = await apiClient.get(`/teams/${id}/`);
  return response.data;
};

const createTeam = async (teamData: { name: string; /* weitere Felder */ }) => {
  const response = await apiClient.post('/teams/', teamData);
  return response.data;
};

const updateTeam = async (id: number | string, teamData: { name: string; /* weitere Felder */ }) => {
  const response = await apiClient.put(`/teams/${id}/`, teamData);
  return response.data;
};

const deleteTeam = async (id: number | string) => {
  const response = await apiClient.delete(`/teams/${id}/`);
  return response.data; // Oft leer oder Statuscode ist ausreichend
};

const getRacers = async (teamId?: number | string) => {
  const params = teamId ? { team_id: teamId } : {}; // Backend muss diesen Filter unterstützen
  const response = await apiClient.get<RacerFromAPI[]>('/racers/', { params }); // Typ hier hinzufügen
  return response.data;
};

const getRacerById = async (id: number | string) => {
  const response = await apiClient.get<RacerFromAPI>(`/racers/${id}/`); // Typ hier hinzufügen
  return response.data;
};

const createRacer = async (racerData: RacerData) => { // Typ für Eingabedaten
  const response = await apiClient.post<RacerFromAPI>('/racers/', racerData); // Typ hier hinzufügen
  return response.data;
};

const updateRacer = async (id: number | string, racerData: Partial<RacerData>) => { // Partial, da nicht alle Felder gesendet werden müssen
  const response = await apiClient.put<RacerFromAPI>(`/racers/${id}/`, racerData); // Typ hier hinzufügen
  return response.data;
};

const deleteRacer = async (id: number | string) => {
  const response = await apiClient.delete(`/racers/${id}/`);
  return response.data;
};


export default {
  login,
  logout,
  getAccessToken,
  getTeams,
  getTeamById,
  createTeam,
  updateTeam,
  deleteTeam,
  getRacers,      // Hinzugefügt
  getRacerById,   // Hinzugefügt
  createRacer,
  updateRacer,
  deleteRacer,
};