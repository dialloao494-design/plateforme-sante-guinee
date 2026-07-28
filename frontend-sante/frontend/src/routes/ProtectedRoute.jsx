import { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getRoleHomePath } from '../utils/rolePaths.js';
import { userHasRole } from '../utils/roleAccess.js';
import { userNeedsClinicAssignment } from '../utils/clinicAccess.js';
import { PROFILE_GATE_TIMEOUT_MS, logAuthSessionFailure } from '../utils/authSession.js';
import { getAuthToken } from '../utils/authStorage.js';

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

function SessionRecovery({ title, message, onRetry, retrying = false }) {
  return (
    <div className="app-loading" role="alert">
      <div className="login-card login-card--narrow" style={{ margin: '2rem auto', maxWidth: '28rem' }}>
        <p className="login-eyebrow">Plateforme Santé · Guinée</p>
        <h1 className="login-title">{title}</h1>
        <p className="login-lead">{message}</p>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-primary login-submit" onClick={onRetry} disabled={retrying}>
            {retrying ? 'Nouvelle tentative…' : 'Réessayer'}
          </button>
          <a href="/login" className="btn btn-secondary" style={{ textAlign: 'center' }}>
            Se reconnecter
          </a>
        </div>
      </div>
    </div>
  );
}

function ProfileBootstrapGate({ authInitError, onRetry, authLoading }) {
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    if (authInitError) {
      return undefined;
    }
    const timer = window.setTimeout(() => {
      logAuthSessionFailure('profile_gate_timeout', new Error('Profile bootstrap timeout'), {
        path: window.location.pathname,
      });
      setTimedOut(true);
    }, PROFILE_GATE_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [authInitError]);

  if (authInitError || timedOut) {
    return (
      <SessionRecovery
        title="Profil inaccessible"
        message={
          authInitError ||
          'Le chargement du profil a pris trop de temps. Vérifiez votre connexion ou réessayez.'
        }
        onRetry={onRetry}
        retrying={authLoading}
      />
    );
  }

  return <SessionGate label="Chargement du profil…" />;
}

const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const { authLoading, user, authInitError, retrySessionBootstrap } = useAuth();
  const location = useLocation();
  const token = getAuthToken();

  if (authLoading) {
    return <SessionGate />;
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (!user) {
    return (
      <ProfileBootstrapGate
        authInitError={authInitError}
        onRetry={retrySessionBootstrap}
        authLoading={authLoading}
      />
    );
  }

  // Local / clinic policy: force password change before accessing clinical screens.
  if (
    user.must_change_password &&
    location.pathname !== '/account/password' &&
    location.pathname !== '/login'
  ) {
    return <Navigate to="/account/password" replace state={{ mustChangePassword: true }} />;
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

  if (allowedRoles.length > 0 && !userHasRole(role, allowedRoles)) {
    return <Navigate to={getRoleHomePath(role, user.clinic_id)} replace />;
  }

  return children;
};

export default ProtectedRoute;
