// src/services/apiService.ts
import axios from 'axios';
import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type {
  RacerFromAPI,
  RacerFormData,
  TeamFromAPI,
  TeamFormData,
  RaceRunFromAPI,
  RaceRunFormData,
  SoapboxFromAPI,
  SoapboxFormData,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

interface TokenPair {
  access: string;
  refresh: string;
}

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

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

let isRefreshing = false;
let failedQueue: Array<{ resolve: (value?: string | null) => void; reject: (reason?: AxiosError | null) => void }> = [];

const processQueue = (error: AxiosError | null, token: string | null = null) => {
  failedQueue.forEach(prom => error ? prom.reject(error) : prom.resolve(token));
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry && getRefreshToken()) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => failedQueue.push({ resolve, reject }))
          .then(token => {
            if (originalRequest.headers) originalRequest.headers['Authorization'] = 'Bearer ' + token;
            return apiClient(originalRequest);
          }).catch(err => Promise.reject(err));
      }
      originalRequest._retry = true;
      isRefreshing = true;
      try {
        const refreshToken = getRefreshToken();
        // Ensure refreshToken is not null before making the call, though getRefreshToken() above should suffice
        if (!refreshToken) throw new Error("No refresh token available");

        const { data } = await axios.post<TokenPair>(`${API_BASE_URL}/token/refresh/`, { refresh: refreshToken });
        setTokens(data);
        if (originalRequest.headers) originalRequest.headers.Authorization = `Bearer ${data.access}`;
        processQueue(null, data.access);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as AxiosError, null);
        clearTokens();
        window.dispatchEvent(new Event('authError')); // Notify app about auth failure
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    // If 401 and no refresh token, or if originalRequest._retry is true (meaning refresh already failed)
    if (error.response?.status === 401 && (!getRefreshToken() || originalRequest._retry)) {
        clearTokens();
        window.dispatchEvent(new Event('authError'));
    }
    return Promise.reject(error);
  }
);

const login = async (username: string, password: string): Promise<TokenPair> => {
  const { data } = await apiClient.post<TokenPair>('/token/', { username, password });
  setTokens(data);
  return data;
};

const logout = (): void => clearTokens();

// Teams
const getTeams = async () => apiClient.get<TeamFromAPI[]>('/teams/').then(res => res.data);
const getTeamById = async (id: number | string) => apiClient.get<TeamFromAPI>(`/teams/${id}/`).then(res => res.data);
const createTeam = async (teamData: TeamFormData) => apiClient.post<TeamFromAPI>('/teams/', teamData).then(res => res.data);
const updateTeam = async (id: number | string, teamData: TeamFormData) => apiClient.put<TeamFromAPI>(`/teams/${id}/`, teamData).then(res => res.data);
const deleteTeam = async (id: number | string) => apiClient.delete(`/teams/${id}/`).then(res => res.data);

// Soapboxes
const getSoapboxes = async () => apiClient.get<SoapboxFromAPI[]>('/soapboxes/').then(res => res.data);
const createSoapbox = async (data: SoapboxFormData) => apiClient.post<SoapboxFromAPI>('/soapboxes/', data).then(res => res.data);
const updateSoapbox = async (id: number | string, data: SoapboxFormData) => apiClient.put<SoapboxFromAPI>(`/soapboxes/${id}/`, data).then(res => res.data);
const deleteSoapbox = async (id: number | string) => apiClient.delete(`/soapboxes/${id}/`).then(res => res.data);

// Racers
const getRacers = async (params?: Record<string, string | number>) => apiClient.get<RacerFromAPI[]>('/racers/', { params }).then(res => res.data);
const getRacerDetails = async (id: number | string) => apiClient.get<RacerFromAPI>(`/racers/${id}/`).then(res => res.data);
const createRacer = async (racerData: RacerFormData) => {
    const payload = { 
        ...racerData, 
        team: racerData.team === '' ? null : racerData.team,
        soapbox: racerData.soapbox === '' ? null : racerData.soapbox,
    };
    return apiClient.post<RacerFromAPI>('/racers/', payload).then(res => res.data);
};
const updateRacer = async (id: number | string, racerData: Partial<RacerFormData>) => {
    const payload: Partial<RacerFormData> = { ...racerData };
    if ('team' in racerData) {
        payload.team = racerData.team === '' ? null : racerData.team;
    }
    if ('soapbox' in racerData) {
        payload.soapbox = racerData.soapbox === '' ? null : racerData.soapbox;
    }
    return apiClient.put<RacerFromAPI>(`/racers/${id}/`, payload).then(res => res.data);
};
const deleteRacer = async (id: number | string) => apiClient.delete(`/racers/${id}/`).then(res => res.data);

// RaceRuns
const getRaceRuns = async (params?: Record<string, string | number>) => apiClient.get<RaceRunFromAPI[]>('/raceruns/', { params }).then(res => res.data);
const createRaceRun = async (data: RaceRunFormData) => apiClient.post<RaceRunFromAPI>('/raceruns/', data).then(res => res.data);
const updateRaceRun = async (id: number, data: Partial<RaceRunFormData>) => apiClient.put<RaceRunFromAPI>(`/raceruns/${id}/`, data).then(res => res.data);
const deleteRaceRun = async (id: number) => apiClient.delete(`/raceruns/${id}/`).then(res => res.data);


export default {
  login, logout, getAccessToken,
  getTeams, getTeamById, createTeam, updateTeam, deleteTeam,
  getSoapboxes, createSoapbox, updateSoapbox, deleteSoapbox,
  getRacers, getRacerDetails, createRacer, updateRacer, deleteRacer,
  getRaceRuns, createRaceRun, updateRaceRun, deleteRaceRun,
};