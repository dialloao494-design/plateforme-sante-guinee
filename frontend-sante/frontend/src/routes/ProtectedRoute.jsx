import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';

const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const { authLoading, isAuthenticated, user } = useAuth();

  if (authLoading) {
    return (
      <div className="app-loading" role="status" aria-live="polite">
        <div className="app-loading-inner">
          <span className="app-spinner" aria-hidden />
          <span>Vérification de la session…</span>
        </div>
      </div>
    );
  }

  const token = localStorage.getItem('token') || localStorage.getItem('access_token');
  if (!isAuthenticated || !token) {
    return <Navigate to="/login" replace />;
  }

  const role = user?.role || user?.user_role;
  if (allowedRoles.length > 0 && (!role || !allowedRoles.includes(role))) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

export default ProtectedRoute;