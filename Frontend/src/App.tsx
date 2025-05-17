import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import { AuthProvider } from './contexts/AuthContext';

import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

// Seiten importieren
import HomePage from './pages/HomePage'; // Die neue Homepage
import ResultsPage from './pages/ResultsPage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
// Placeholder für About, Privacy, Impressum Seiten
const AboutPage: React.FC = () => <div className="page-container"><h1>Über Uns</h1><p>Infos über den Veranstalter...</p></div>;
const PrivacyPage: React.FC = () => <div className="page-container"><h1>Datenschutz</h1><p>Unsere Datenschutzrichtlinien...</p></div>;
const ImpressumPage: React.FC = () => <div className="page-container"><h1>Impressum</h1><p>Impressumsangaben...</p></div>;

import NotFoundPage from './pages/NotFoundPage';


function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>

            {/* Öffentliche Routen */}
            <Route path="/" element={<HomePage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/impressum" element={<ImpressumPage />} />


            {/* Admin Login Route */}
            <Route path="/admin/login" element={<AdminLoginPage />} />

            {/* Geschützte Admin-Routen */}
            <Route element={<ProtectedRoute />}>
              <Route path="/admin" element={<AdminDashboardPage />} />
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