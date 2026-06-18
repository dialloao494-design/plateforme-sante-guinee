import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getRoleHomePath } from '../utils/rolePaths.js';
import { parseApiError, validateSignupPassword } from '../utils/apiErrors.js';
import { authAPI } from '../services/api.js';
import './Login.css';

const Signup = () => {
  const [formData, setFormData] = useState({ email: '', password: '', role: 'patient' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const pwdError = validateSignupPassword(formData.password);
    if (pwdError) {
      setError(pwdError);
      setLoading(false);
      return;
    }

    const email = String(formData.email || '').trim().toLowerCase();
    const role = formData.role === 'doctor' ? 'doctor' : 'patient';

    try {
      const data = await authAPI.signup({
        email,
        password: formData.password,
        role,
      });

      if (!data?.access_token) {
        setError('Compte créé mais connexion automatique impossible. Utilisez la page de connexion.');
        navigate('/login');
        return;
      }

      const result = await loginWithToken(data);
      if (result.success) {
        navigate(getRoleHomePath(result.role, result.clinic_id), { replace: true });
        return;
      }
      setError(result.error || 'Compte créé. Connectez-vous avec votre email et mot de passe.');
      navigate('/login');
    } catch (err) {
      setError(parseApiError(err, 'Inscription impossible pour le moment.'));
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
              placeholder="Min. 8 car., 1 majuscule, 1 chiffre"
              value={formData.password}
              onChange={handleChange}
              required
              autoComplete="new-password"
              disabled={loading}
            />
            <p className="login-stat-hint">Au moins 8 caractères, une majuscule et un chiffre.</p>
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
