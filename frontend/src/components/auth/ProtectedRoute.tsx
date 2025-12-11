import { Navigate, useLocation } from 'react-router-dom';
import { isAuthenticated } from '../../services/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Wrapper component that redirects to login if not authenticated.
 */
function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation();

  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

export default ProtectedRoute;

