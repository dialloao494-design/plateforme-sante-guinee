import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../contexts/AuthContext.jsx';
import PasswordInput from '../components/PasswordInput.jsx';
import { getRoleHomePath } from '../utils/rolePaths.js';
import './AccountPages.css';
import './Login.css';

export default function ChangePassword({ forced = false }) {
  const navigate = useNavigate();
  const { changePassword, loading, user, refreshUser } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [formError, setFormError] = useState('');

  const isForced = false;

  useEffect(() => {
    if (isForced) {
      document.title = 'Changer le mot de passe — obligatoire';
    }
  }, [isForced]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError('');

    if (newPassword.length < 8) {
      setFormError('Le nouveau mot de passe doit contenir au moins 8 caractères.');
      return;
    }
    if (!/[A-Z]/.test(newPassword) || !/[0-9]/.test(newPassword)) {
      setFormError('Le mot de passe doit contenir au moins une majuscule et un chiffre.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setFormError('La confirmation ne correspond pas au nouveau mot de passe.');
      return;
    }

    const result = await changePassword(currentPassword, newPassword);
    if (!result.success) {
      setFormError(result.error || 'Échec de la modification.');
      return;
    }

    const updated = await refreshUser();
    toast.success('Mot de passe mis à jour.');
    navigate(getRoleHomePath(updated?.role || user?.role, updated?.clinic_id || user?.clinic_id), {
      replace: true,
    });
  };

  return (
    <div className="account-page">
      <header className="account-header">
        <h1>{isForced ? 'Première connexion — changer le mot de passe' : 'Changer le mot de passe'}</h1>
        <p>
          {isForced
            ? 'Votre compte utilise un mot de passe temporaire. Choisissez un mot de passe personnel pour continuer.'
            : 'Utilisez un mot de passe fort et unique pour votre compte.'}
        </p>
      </header>

      <form className="account-card account-form" onSubmit={handleSubmit}>
        {formError && <div className="account-error">{formError}</div>}

        <PasswordInput
          id="current-password"
          label="Mot de passe actuel (temporaire)"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          autoComplete="current-password"
          disabled={loading}
        />

        <PasswordInput
          id="new-password"
          label="Nouveau mot de passe"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          autoComplete="new-password"
          disabled={loading}
        />

        <PasswordInput
          id="confirm-password"
          label="Confirmer le nouveau mot de passe"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          autoComplete="new-password"
          disabled={loading}
        />

        <p className="login-stat-hint">Au moins 8 caractères, une majuscule et un chiffre.</p>

        <button type="submit" className="account-submit" disabled={loading}>
          {loading ? 'Enregistrement…' : 'Mettre à jour le mot de passe'}
        </button>

        {!isForced && (
          <p className="login-footer-text">
            <Link to="/account/profile">Retour au profil</Link>
          </p>
        )}
      </form>
    </div>
  );
}
