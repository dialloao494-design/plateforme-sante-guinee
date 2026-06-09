import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getRoleHomePath } from '../utils/rolePaths.js';
import './Login.css';

const PILOT_DEMO_ACCOUNTS = import.meta.env.DEV
  ? {
      doctor: { email: 'dr.mamady@example.com', password: 'Doctor123!', label: 'Médecin démo' },
      patient: { email: 'test.patient@example.com', password: 'Patient123!', label: 'Patient démo' },
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
    }
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
        <p className="login-lead">Accédez à votre espace patient ou professionnel de santé.</p>
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

          {submitError && (
            <p className="login-error" role="alert">
              {submitError}
            </p>
          )}

          {PILOT_DEMO_ACCOUNTS && (
            <div className="login-demo-hint" aria-label="Comptes de démonstration">
              <p className="login-demo-title">Comptes de test (développement)</p>
              <div className="login-demo-actions">
                <button
                  type="button"
                  className="login-demo-btn"
                  disabled={loading}
                  onClick={() => fillDemoAccount(PILOT_DEMO_ACCOUNTS.doctor)}
                >
                  {PILOT_DEMO_ACCOUNTS.doctor.label}
                </button>
                <button
                  type="button"
                  className="login-demo-btn"
                  disabled={loading}
                  onClick={() => fillDemoAccount(PILOT_DEMO_ACCOUNTS.patient)}
                >
                  {PILOT_DEMO_ACCOUNTS.patient.label}
                </button>
              </div>
              <p className="login-demo-note">
                Médecin : <code>dr.mamady@example.com</code> · Mot de passe : <code>Doctor123!</code>{' '}
                (D majuscule, point d’exclamation)
              </p>
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