import { useState } from 'react';
import { Link } from 'react-router-dom';
import { authAPI } from '../services/api.js';
import './Login.css';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const { data } = await authAPI.forgotPassword(email);
      setMessage(data?.message || 'Si cet email est enregistré, un lien a été envoyé.');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Demande impossible pour le moment.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card login-card--narrow">
        <p className="login-eyebrow">Plateforme Santé · Guinée</p>
        <h1 className="login-title">Mot de passe oublié</h1>
        <p className="login-lead">Entrez votre email pour recevoir un lien de réinitialisation.</p>
        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label htmlFor="forgot-email">Email</label>
            <input
              id="forgot-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              disabled={loading}
            />
          </div>
          {error && <p className="login-error">{error}</p>}
          {message && <p className="login-success">{message}</p>}
          <button type="submit" className="btn btn-primary login-submit" disabled={loading}>
            {loading ? 'Envoi…' : 'Envoyer le lien'}
          </button>
        </form>
        <p className="login-footer-text">
          <Link to="/login">Retour à la connexion</Link>
        </p>
      </div>
    </div>
  );
}
