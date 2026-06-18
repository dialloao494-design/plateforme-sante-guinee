import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { authAPI } from '../services/api.js';
import './Login.css';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = useMemo(() => searchParams.get('token') || '', [searchParams]);
  const [loading, setLoading] = useState(Boolean(token));
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    authAPI
      .verifyEmail(token)
      .then(() => setSuccess(true))
      .catch((err) => setError(err?.response?.data?.detail || 'Vérification impossible.'))
      .finally(() => setLoading(false));
  }, [token]);

  if (!token) {
    return (
      <div className="login-page">
        <div className="login-card login-card--narrow">
          <h1 className="login-title">Lien invalide</h1>
          <p className="login-lead">Demandez un nouveau lien depuis la page de connexion.</p>
          <p className="login-footer-text">
            <Link to="/login">Connexion</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card login-card--narrow">
        <p className="login-eyebrow">Plateforme Santé · Guinée</p>
        <h1 className="login-title">Vérification email</h1>
        {loading && <p className="login-lead">Vérification en cours…</p>}
        {success && (
          <p className="login-lead">Votre adresse email est confirmée. Vous pouvez vous connecter.</p>
        )}
        {error && <p className="login-error">{error}</p>}
        {!loading && (
          <p className="login-footer-text">
            <Link to="/login">Se connecter</Link>
          </p>
        )}
      </div>
    </div>
  );
}
