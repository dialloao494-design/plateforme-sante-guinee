import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getRoleLabel } from '../utils/roleLabels.js';
import './AccountPages.css';

export default function AccountProfile() {
  const { user, refreshUser, authLoading } = useAuth();

  useEffect(() => {
    refreshUser().catch(() => {});
  }, [refreshUser]);

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
        <dl className="account-dl">
          <div>
            <dt>Nom complet</dt>
            <dd>{user.full_name || '—'}</dd>
          </div>
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
