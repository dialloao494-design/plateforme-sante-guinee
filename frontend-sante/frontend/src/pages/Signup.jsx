import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api.js';
import './Login.css';

const Signup = () => {
  const [formData, setFormData] = useState({ email: '', password: '', role: 'patient' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await authAPI.signup(formData);
      navigate('/login');
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Inscription impossible pour le moment.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card login-card--narrow">
        <p className="login-eyebrow">Plateforme Santé · Guinée</p>
        <h1 className="login-title">Créer un compte</h1>
        <p className="login-lead">
          Rejoignez la plateforme pour prendre rendez-vous, échanger avec votre médecin ou gérer votre cabinet.
        </p>
        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label htmlFor="signup-email">Email</label>
            <input
              id="signup-email"
              type="email"
              name="email"
              placeholder="vous@domaine.gn"
              value={formData.email}
              onChange={handleChange}
              required
              autoComplete="email"
              disabled={loading}
            />
          </div>
          <div className="login-field">
            <label htmlFor="signup-password">Mot de passe</label>
            <input
              id="signup-password"
              type="password"
              name="password"
              placeholder="8 caractères minimum recommandés"
              value={formData.password}
              onChange={handleChange}
              required
              autoComplete="new-password"
              disabled={loading}
            />
          </div>
          <div className="login-field">
            <label htmlFor="signup-role">Profil</label>
            <select id="signup-role" name="role" value={formData.role} onChange={handleChange} disabled={loading}>
              <option value="patient">Patient</option>
              <option value="doctor">Médecin / professionnel de santé</option>
            </select>
          </div>
          {error && (
            <p className="login-error" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="btn btn-primary login-submit" disabled={loading}>
            {loading ? 'Création du compte…' : 'S’inscrire'}
          </button>
        </form>
        <p className="login-footer-text">
          Déjà inscrit ? <Link to="/login">Se connecter</Link>
        </p>
      </div>
    </div>
  );
};

export default Signup;
