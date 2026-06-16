import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../contexts/AuthContext.jsx';
import './AccountPages.css';

export default function ChangePassword() {
  const navigate = useNavigate();
  const { changePassword, loading, logout } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [formError, setFormError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError('');

    if (newPassword.length < 8) {
      setFormError('Le nouveau mot de passe doit contenir au moins 8 caractères.');
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

    toast.success('Mot de passe mis à jour. Veuillez vous reconnecter.');
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="account-page">
      <header className="account-header">
        <h1>Changer le mot de passe</h1>
        <p>Utilisez un mot de passe fort et unique pour votre compte.</p>
      </header>

      <form className="account-card account-form" onSubmit={handleSubmit}>
        {formError && <div className="account-error">{formError}</div>}

        <label className="account-field">
          <span>Mot de passe actuel</span>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>

        <label className="account-field">
          <span>Nouveau mot de passe</span>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>

        <label className="account-field">
          <span>Confirmer le nouveau mot de passe</span>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>

        <button type="submit" className="account-submit" disabled={loading}>
          {loading ? 'Enregistrement…' : 'Mettre à jour le mot de passe'}
        </button>
      </form>
    </div>
  );
}
