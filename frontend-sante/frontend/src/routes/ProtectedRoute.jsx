import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';

const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const { authLoading, isAuthenticated, user } = useAuth();

  if (authLoading) {
    return <div>Chargement...</div>;
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