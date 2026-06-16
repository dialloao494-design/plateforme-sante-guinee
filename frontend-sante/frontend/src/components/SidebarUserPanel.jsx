import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getRoleLabel } from '../utils/roleLabels.js';
import './SidebarUserPanel.css';

function initialsFromUser(user) {
  const name = String(user?.full_name || '').trim();
  if (name) {
    const parts = name.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }
  const email = String(user?.email || '').trim();
  if (!email) return '?';
  const local = email.split('@')[0] || email;
  return local.slice(0, 2).toUpperCase() || '?';
}

export default function SidebarUserPanel({ role, onNavigate }) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  if (!user) {
    return null;
  }

  const handleLogout = () => {
    logout();
    if (typeof onNavigate === 'function') {
      onNavigate();
    }
    navigate('/login', { replace: true });
  };

  const clinicLabel = user.clinic_name || (role === 'platform_admin' ? 'Plateforme nationale' : '—');

  return (
    <div className="sidebar-user-panel" aria-label="Compte utilisateur">
      <div className="sidebar-user-card">
        <div className="sidebar-user-avatar" aria-hidden>
          {initialsFromUser(user)}
        </div>
        <div className="sidebar-user-meta">
          <span className="sidebar-user-name">{user.full_name || user.email}</span>
          <span className="sidebar-user-role">{getRoleLabel(role)}</span>
          <span className="sidebar-user-clinic" title={clinicLabel}>
            {clinicLabel}
          </span>
        </div>
      </div>

      <div className="sidebar-user-actions">
        <Link to="/account/profile" className="sidebar-user-action" onClick={onNavigate}>
          Mon profil
        </Link>
        <Link to="/account/password" className="sidebar-user-action" onClick={onNavigate}>
          Changer le mot de passe
        </Link>
        <button type="button" className="sidebar-user-action sidebar-user-action-logout" onClick={handleLogout}>
          Déconnexion
        </button>
      </div>
    </div>
  );
}
