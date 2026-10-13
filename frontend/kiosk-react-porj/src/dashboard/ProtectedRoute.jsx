import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext.jsx';

export default function ProtectedRoute() {
  const { doctor, loading } = useAuth();
  const location = useLocation();

  if (loading) return <p>Loading…</p>;
  if (!doctor) return <Navigate to="/dr/login" replace state={{ from: location }} />;
  return <Outlet />;
}