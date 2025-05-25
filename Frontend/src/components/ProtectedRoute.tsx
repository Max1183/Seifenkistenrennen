import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    // Show a loading indicator while authentication status is being checked
    return (
        <div className="page-container" style={{ textAlign: 'center', padding: 'var(--spacing-xxl) 0' }}>
            <p style={{fontSize: '1.2rem', color: 'var(--text-light-color)'}}>Authentifizierung wird geprüft...</p>
            {/* Optional: Add a spinner or more elaborate loading animation here */}
        </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to the login page, preserving the intended destination
    return <Navigate to="/admin/login" state={{ from: location }} replace />;
  }

  return <Outlet />; // Render the protected content
};

export default ProtectedRoute;