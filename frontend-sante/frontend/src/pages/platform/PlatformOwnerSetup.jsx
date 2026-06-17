import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { platformSetupAPI } from '../../services/api.js';
import '../Login.css';

export default function PlatformOwnerSetup() {
  const navigate = useNavigate();
  const { loginWithToken, user, authLoading } = useAuth();
  const [statusLoading, setStatusLoading] = useState(true);
  const [setupRequired, setSetupRequired] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!authLoading && user) {
      navigate(user.role === 'platform_owner' ? '/platform' : '/login', { replace: true });
    }
  }, [authLoading, user, navigate]);

  useEffect(() => {
    let cancelled = false;

    const loadStatus = async () => {
      try {
        const data = await platformSetupAPI.getStatus();
        if (cancelled) return;
        if (!data.setup_required) {
          navigate('/login', { replace: true });
          return;
        }
        setSetupRequired(true);
      } catch {
        if (!cancelled) {
          setSubmitError('Impossible de vérifier l’état de la plateforme. Réessayez plus tard.');
        }
      } finally {
        if (!cancelled) {
          setStatusLoading(false);
        }
      }
    };

    loadStatus();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitError('');

    if (password !== passwordConfirm) {
      setSubmitError('Les mots de passe ne correspondent pas.');
      return;
    }

    setSubmitting(true);
    try {
      const tokenData = await platformSetupAPI.completeSetup({
        email: email.trim().toLowerCase(),
        password,
        password_confirm: passwordConfirm,
      });
      const result = await loginWithToken(tokenData);
      if (result.success) {
        navigate('/platform', { replace: true });
      } else {
        setSubmitError(result.error || 'Compte créé mais connexion impossible. Utilisez la page de connexion.');
        navigate('/login', { replace: true });
      }
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map((d) => d.msg || d).join(', ')
        : detail || 'Impossible de créer le compte propriétaire.';
      if (err?.response?.status === 403) {
        navigate('/login', { replace: true });
        return;
      }
      setSubmitError(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading || statusLoading || !setupRequired) {
    return (
      <div className="login-page" role="status" aria-live="polite">
        <div className="login-card login-card--narrow">
          <p className="login-eyebrow">Plateforme Santé · Guinée</p>
          <h1 className="login-title">Configuration initiale</h1>
          <div className="login-loading">
            <span className="app-spinner" aria-hidden />
            <span>Vérification…</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card login-card--narrow">
        <p className="login-eyebrow">Plateforme Santé · Guinée</p>
        <h1 className="login-title">Propriétaire plateforme</h1>
        <p className="login-lead">
          Aucun compte propriétaire n’existe encore. Créez le vôtre pour administrer toute la
          plateforme. Cette page sera désactivée après la première configuration.
        </p>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label htmlFor="setup-email">Email permanent</label>
            <input
              id="setup-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
            />
          </div>

          <div className="login-field">
            <label htmlFor="setup-password">Mot de passe</label>
            <input
              id="setup-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={submitting}
            />
          </div>

          <div className="login-field">
            <label htmlFor="setup-password-confirm">Confirmer le mot de passe</label>
            <input
              id="setup-password-confirm"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              disabled={submitting}
            />
          </div>

          {submitError ? (
            <p className="login-error" role="alert">
              {submitError}
            </p>
          ) : null}

          <button type="submit" className="login-submit" disabled={submitting}>
            {submitting ? 'Création en cours…' : 'Créer mon compte propriétaire'}
          </button>
        </form>

        <p className="login-footer">
          Déjà configuré ? <Link to="/login">Se connecter</Link>
        </p>
      </div>
    </div>
  );
}
