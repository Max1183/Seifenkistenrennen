import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import HomePage from './pages/HomePage';
import ResultsPage from './pages/ResultsPage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import NotFoundPage from './pages/NotFoundPage';
// AdminManageRacesPage is not currently linked in navigation, kept for potential future use.
// import AdminManageRacesPage from './pages/AdminManageRacesPage';

const PlaceholderPage: React.FC<{ title: string; content?: string }> = ({ title, content }) => (
  <div className="page-container"><h1>{title}</h1><p>{content || `Inhalt für ${title} folgt...`}</p></div>
);

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/about" element={<PlaceholderPage title="Über Uns" />} />
            <Route path="/privacy" element={<PlaceholderPage title="Datenschutz" />} />
            <Route path="/impressum" element={<PlaceholderPage title="Impressum" />} />

            <Route path="/admin/login" element={<AdminLoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/admin" element={<AdminDashboardPage />} />
              {/* Example for a future dedicated race management page:
              <Route path="/admin/races" element={<AdminManageRacesPage />} />
              */}
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;