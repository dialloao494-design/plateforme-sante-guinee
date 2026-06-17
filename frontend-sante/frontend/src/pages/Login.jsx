import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getRoleHomePath } from '../utils/rolePaths.js';
import { platformSetupAPI } from '../services/api.js';
import './Login.css';

const PILOT_DEMO_ACCOUNTS = import.meta.env.DEV
  ? {
      patient: { email: 'test.patient@example.com', password: 'Patient123!', label: 'Patient' },
      reception: { email: 'reception@pilot.local', password: 'ReceptionPilot1!', label: 'Réception' },
      doctor: { email: 'dr.pilot@pilot.local', password: 'DoctorPilot1!', label: 'Médecin' },
      lab: { email: 'lab@pilot.local', password: 'LabPilot1!', label: 'Laboratoire' },
      pharmacy: { email: 'pharmacy@pilot.local', password: 'PharmacyPilot1!', label: 'Pharmacie' },
      manager: { email: 'admin@pilot.local', password: 'AdminPilot1!', label: 'Manager' },
    }
  : null;

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitError, setSubmitError] = useState('');
  const { login, loading, user, authLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!authLoading && user) {
      navigate(getRoleHomePath(user.role), { replace: true });
      return;
    }
    if (authLoading || user) {
      return;
    }

    let cancelled = false;
    platformSetupAPI
      .getStatus()
      .then((data) => {
        if (!cancelled && data?.setup_required) {
          navigate('/platform/setup', { replace: true });
        }
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [authLoading, user, navigate]);

  const fillDemoAccount = (account) => {
    setEmail(account.email);
    setPassword(account.password);
    setSubmitError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setSubmitError('');

    try {
      const result = await login(email, password);
      if (result.success) {
        navigate(getRoleHomePath(result.role), { replace: true });
      } else {
        setSubmitError(result.error || 'Une erreur est survenue, veuillez réessayer');
      }
    } catch {
      setSubmitError('Une erreur est survenue, veuillez réessayer');
    }
  };

  if (authLoading) {
    return (
      <div className="login-page" role="status" aria-live="polite">
        <div className="login-card login-card--narrow">
          <p className="login-eyebrow">Plateforme Santé · Guinée</p>
          <h1 className="login-title">Connexion</h1>
          <div className="login-loading">
            <span className="app-spinner" aria-hidden />
            <span>Vérification de la session…</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card login-card--narrow">
        <p className="login-eyebrow">Plateforme Santé · Guinée</p>
        <h1 className="login-title">Connexion</h1>
        <p className="login-lead">Accédez à votre espace selon votre rôle.</p>
        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              placeholder="vous@exemple.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              required
              autoComplete="email"
            />
          </div>

          <div className="login-field">
            <label htmlFor="password">Mot de passe</label>
            <input
              id="password"
              type="password"
              placeholder="Mot de passe"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              required
              autoComplete="current-password"
            />
          </div>
          <p className="login-forgot">
            <Link to="/forgot-password">Mot de passe oublié ?</Link>
          </p>

          {submitError && (
            <p className="login-error" role="alert">
              {submitError}
            </p>
          )}

          {PILOT_DEMO_ACCOUNTS && (
            <div className="login-demo-hint" aria-label="Comptes de démonstration">
              <p className="login-demo-title">Comptes pilote (développement)</p>
              <div className="login-demo-actions">
                {Object.values(PILOT_DEMO_ACCOUNTS).map((account) => (
                  <button
                    key={account.label}
                    type="button"
                    className="login-demo-btn"
                    disabled={loading}
                    onClick={() => fillDemoAccount(account)}
                  >
                    {account.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <button type="submit" className="btn btn-primary login-submit" disabled={loading}>
            {loading ? 'Connexion en cours…' : 'Se connecter'}
          </button>
        </form>
        <p className="login-footer-text">
          Pas encore de compte ? <Link to="/signup">Créer un compte</Link>
        </p>
      </div>
    </div>
  );
};

export default Login;
