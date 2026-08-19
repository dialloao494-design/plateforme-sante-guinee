import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getRoleLabel } from '../utils/roleLabels.js';
import './AccountPages.css';

export default function AccountProfile() {
  const { user, refreshUser, updateProfile, authLoading, loading } = useAuth();
  const [editing, setEditing] = useState(false);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [message, setMessage] = useState('');
  const [formError, setFormError] = useState('');

  useEffect(() => {
    refreshUser().catch(() => {});
  }, [refreshUser]);

  useEffect(() => {
    if (!user || editing) return;
    const fallbackParts = String(user.full_name || '').trim().split(/\s+/).filter(Boolean);
    setFirstName(user.first_name || fallbackParts[0] || '');
    setLastName(user.last_name || fallbackParts.slice(1).join(' ') || '');
  }, [user, editing]);

  const saveName = async (event) => {
    event.preventDefault();
    setMessage('');
    setFormError('');
    const result = await updateProfile({ first_name: firstName, last_name: lastName });
    if (!result.success) {
      setFormError(result.error);
      return;
    }
    setEditing(false);
    setMessage('Nom enregistré. Il est maintenant visible dans les espaces de travail de la clinique.');
  };

  const cancelEdit = () => {
    setEditing(false);
    setMessage('');
    setFormError('');
  };

  if (authLoading || !user) {
    return (
      <div className="account-page">
        <p>Chargement du profil…</p>
      </div>
    );
  }

  return (
    <div className="account-page">
      <header className="account-header">
        <h1>Mon profil</h1>
        <p>Informations de votre compte et contexte clinique.</p>
      </header>

      <div className="account-card">
        <div className="account-identity-heading">
          <div>
            <span className="account-identity-label">Identité professionnelle</span>
            <strong>{user.full_name || 'Nom non renseigné'}</strong>
          </div>
          {!editing && (
            <button type="button" className="account-edit-button" onClick={() => setEditing(true)}>
              Modifier le nom
            </button>
          )}
        </div>

        {message && <p className="account-success" role="status">{message}</p>}
        {formError && <p className="account-error" role="alert">{formError}</p>}

        {editing && (
          <form className="account-name-form" onSubmit={saveName}>
            <label className="account-field">
              <span>Prénom</span>
              <input
                name="first_name"
                autoComplete="given-name"
                value={firstName}
                onChange={(event) => setFirstName(event.target.value)}
                maxLength="128"
                required
                autoFocus
              />
            </label>
            <label className="account-field">
              <span>Nom</span>
              <input
                name="last_name"
                autoComplete="family-name"
                value={lastName}
                onChange={(event) => setLastName(event.target.value)}
                maxLength="128"
                required
              />
            </label>
            <div className="account-form-actions">
              <button type="submit" className="account-submit" disabled={loading}>
                {loading ? 'Enregistrement…' : 'Enregistrer le nom'}
              </button>
              <button type="button" className="account-cancel" onClick={cancelEdit} disabled={loading}>
                Annuler
              </button>
            </div>
          </form>
        )}

        <dl className="account-dl account-dl--details">
          <div>
            <dt>Email</dt>
            <dd>{user.email}</dd>
          </div>
          <div>
            <dt>Rôle</dt>
            <dd>{getRoleLabel(user.role)}</dd>
          </div>
          <div>
            <dt>Clinique</dt>
            <dd>{user.clinic_name || '—'}</dd>
          </div>
        </dl>
      </div>

      <p className="account-links">
        <Link to="/account/password">Changer le mot de passe</Link>
      </p>
    </div>
  );
}
