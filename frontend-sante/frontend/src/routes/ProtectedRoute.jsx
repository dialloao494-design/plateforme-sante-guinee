import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getRoleHomePath } from '../utils/rolePaths.js';
import { userHasRole } from '../utils/roleAccess.js';
import { userNeedsClinicAssignment } from '../utils/clinicAccess.js';

function SessionGate({ label = 'Vérification de la session…' }) {
  return (
    <div className="app-loading" role="status" aria-live="polite">
      <div className="app-loading-inner">
        <span className="app-spinner" aria-hidden />
        <span>{label}</span>
      </div>
    </div>
  );
}

const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const { authLoading, user } = useAuth();
  const location = useLocation();
  const token = localStorage.getItem('token') || localStorage.getItem('access_token');

  if (authLoading) {
    return <SessionGate />;
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // After login the JWT is stored before React commits user profile state.
  if (!user) {
    return <SessionGate label="Chargement du profil…" />;
  }

  if (userNeedsClinicAssignment(user, location.pathname)) {
    return (
      <Navigate
        to={getRoleHomePath(user.role, user.clinic_id)}
        replace
        state={{ clinicRequired: true }}
      />
    );
  }

  const role = user?.role || user?.user_role;

  if (user?.must_change_password && location.pathname !== '/account/password') {
    return <Navigate to="/account/password" replace state={{ forcedPasswordChange: true }} />;
  }

  if (allowedRoles.length > 0 && !userHasRole(role, allowedRoles)) {
    return <Navigate to={getRoleHomePath(role, user.clinic_id)} replace />;
  }

  return children;
};

export default ProtectedRoute;
