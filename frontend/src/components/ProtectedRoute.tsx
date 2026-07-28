import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <div style={{ color: 'white', display: 'flex', justifyContent: 'center', marginTop: '50px' }}>Loading...</div>;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;

  return <>{children}</>;
};
