import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import { AuthProvider } from './contexts/AuthContext'; // Stelle sicher, dass der Pfad korrekt ist

import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

import ResultsPage from './pages/ResultsPage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import AdminManageRacesPage from './pages/AdminManageRacesPage';
import NotFoundPage from './pages/NotFoundPage';


function App() {
  return (
    <BrowserRouter> {/* BrowserRouter jetzt außen */}
      <AuthProvider> {/* AuthProvider jetzt innen, hat Zugriff auf Router-Kontext */}
        <Routes>
          <Route element={<Layout />}> {/* Globales Layout für die meisten Seiten */}

            {/* Öffentliche Routen */}
            <Route path="/" element={<ResultsPage />} />
            <Route path="/results" element={<Navigate to="/" replace />} />

            {/* Admin Login Route (außerhalb von ProtectedRoute) */}
            <Route path="/admin/login" element={<AdminLoginPage />} />

            {/* Geschützte Admin-Routen */}
            <Route element={<ProtectedRoute />}>
              <Route path="/admin" element={<AdminDashboardPage />} />
              <Route path="/admin/dashboard" element={<Navigate to="/admin" replace />} />
              <Route path="/admin/races" element={<AdminManageRacesPage />} />
              {/* Hier weitere Admin-Routen hinzufügen */}
            </Route>

            {/* Fallback für nicht gefundene Routen */}
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;