import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import './Sidebar.css';

function initialsFromUser(user) {
  const email = String(user?.email || '').trim();
  if (!email) return '?';
  const local = email.split('@')[0] || email;
  const parts = local.replace(/[^a-zA-Z0-9.]/g, ' ').split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return local.slice(0, 2).toUpperCase() || '?';
}

const ROLE_LABELS = {
  patient: 'Patient',
  doctor: 'Médecin',
  admin: 'Administrateur',
};

const navItems = [
  { path: '/dashboard', label: 'Tableau de bord', icon: 'dash', roles: ['patient', 'doctor', 'admin'] },
  { path: '/teleconsultation', label: 'Téléconsultation', icon: 'video', roles: ['patient', 'doctor', 'admin'] },
  { path: '/notifications', label: 'Notifications', icon: 'bell', roles: ['patient', 'doctor', 'admin'] },
  { path: '/appointments', label: 'Mes rendez-vous', icon: 'calendar', roles: ['patient', 'admin'] },
  { path: '/doctors', label: 'Médecins', labelDoctor: 'Annuaire', icon: 'steth', roles: ['patient', 'doctor', 'admin'] },
  { path: '/doctor/dashboard', label: 'Agenda clinique', icon: 'board', roles: ['doctor', 'admin'] },
  { path: '/doctor/appointments', label: 'File d’attente', icon: 'queue', roles: ['doctor', 'admin'] },
  { path: '/doctor/messages', label: 'Messagerie', icon: 'chat', roles: ['doctor', 'admin'] },
  { path: '/patients', label: 'Patients', icon: 'people', roles: ['doctor', 'admin'] },
  { path: '/users', label: 'Utilisateurs', icon: 'shield', roles: ['admin'] },
];

function NavIcon({ name }) {
  const common = { className: 'sidebar-svg', viewBox: '0 0 24 24', fill: 'none', 'aria-hidden': true };
  switch (name) {
    case 'video':
      return (
        <svg {...common}>
          <path
            d="M15 10l5-3v10l-5-3v-4zM4 8h9a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4a2 2 0 012-2z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'bell':
      return (
        <svg {...common}>
          <path
            d="M6 16h12l-1.1-1.32V11a5 5 0 10-10 0v3.68L6 16zM10 16a2 2 0 004 0"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'calendar':
      return (
        <svg {...common}>
          <rect x="3" y="5" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.75" />
          <path d="M8 3v4M16 3v4M3 11h18" stroke="currentColor" strokeWidth="1.75" />
        </svg>
      );
    case 'steth':
      return (
        <svg {...common}>
          <path
            d="M8 4v5a4 4 0 008 0V4M12 9v11M9 20h6"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </svg>
      );
    case 'board':
      return (
        <svg {...common}>
          <rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" strokeWidth="1.75" />
          <path d="M8 9h8M8 13h5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      );
    case 'queue':
      return (
        <svg {...common}>
          <path d="M8 6h12M8 12h12M8 18h8" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          <circle cx="5" cy="6" r="1.5" fill="currentColor" />
          <circle cx="5" cy="12" r="1.5" fill="currentColor" />
          <circle cx="5" cy="18" r="1.5" fill="currentColor" />
        </svg>
      );
    case 'chat':
      return (
        <svg {...common}>
          <path
            d="M4 6a2 2 0 012-2h12a2 2 0 012 2v8a2 2 0 01-2 2H9l-4 3v-3H6a2 2 0 01-2-2V6z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'people':
      return (
        <svg {...common}>
          <circle cx="9" cy="8" r="3" stroke="currentColor" strokeWidth="1.75" />
          <path d="M4 20v-1a4 4 0 014-4h2a4 4 0 014 4v1" stroke="currentColor" strokeWidth="1.75" />
          <circle cx="17" cy="9" r="2.5" stroke="currentColor" strokeWidth="1.75" />
          <path d="M14 20v-1a3 3 0 013-3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      );
    case 'shield':
      return (
        <svg {...common}>
          <path d="M12 3l8 4v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V7l8-4z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
        </svg>
      );
    default:
      return (
        <svg {...common}>
          <rect x="4" y="4" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.75" />
          <rect x="13" y="4" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.75" />
          <rect x="4" y="13" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.75" />
          <rect x="13" y="13" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.75" />
        </svg>
      );
  }
}

function pathIsActive(pathname, itemPath) {
  if (itemPath === '/dashboard') {
    return pathname === '/dashboard';
  }
  if (itemPath === '/notifications') {
    return pathname === '/notifications';
  }
  if (itemPath === '/teleconsultation') {
    return pathname === '/teleconsultation' || pathname.startsWith('/consultation/');
  }
  if (itemPath === '/doctor/dashboard') {
    return pathname === '/doctor/dashboard';
  }
  if (itemPath === '/doctor/appointments') {
    return pathname === '/doctor/appointments';
  }
  if (itemPath === '/doctor/messages') {
    return pathname === '/doctor/messages';
  }
  return pathname === itemPath || pathname.startsWith(`${itemPath}/`);
}

const Sidebar = ({ isOpen, onClose }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user, authLoading } = useAuth();
  const role = String(user?.role || user?.user_role || localStorage.getItem('user_role') || '').toLowerCase();

  const visibleItems = authLoading
    ? []
    : navItems.filter((item) => (role ? item.roles.includes(role) : false));

  const handleLogout = () => {
    logout();
    if (typeof onClose === 'function') {
      onClose();
    }
    navigate('/login');
  };

  const closeIfMobile = () => {
    if (typeof onClose === 'function') {
      onClose();
    }
  };

  const linkLabel = (item) => {
    if (item.path === '/doctors' && (role === 'doctor' || role === 'admin')) {
      return item.labelDoctor || item.label;
    }
    return item.label;
  };

  return (
    <>
      <button
        type="button"
        className={`sidebar-overlay ${isOpen ? 'active' : ''}`}
        aria-label="Fermer le menu"
        onClick={onClose}
      />

      <aside className={`sidebar ${isOpen ? 'open' : ''}`} aria-label="Navigation principale">
        <div className="sidebar-brand">
          <span className="sidebar-brand-mark" aria-hidden />
          <div>
            <div className="sidebar-brand-title">Plateforme Santé</div>
            <div className="sidebar-brand-sub">Guinée · Clinique numérique</div>
          </div>
        </div>

        <div className="sidebar-header">
          <h2 className="sidebar-menu-label">Menu</h2>
          <button type="button" className="close-btn" onClick={closeIfMobile} aria-label="Fermer">
            ✕
          </button>
        </div>

        <nav className="sidebar-nav">
          {authLoading && <p className="sidebar-loading">Chargement…</p>}
          <ul>
            {visibleItems.map((item) => (
              <li key={`${item.path}-${item.label}`}>
                <Link
                  to={item.path}
                  className={`sidebar-link ${pathIsActive(location.pathname, item.path) ? 'active' : ''}`}
                  onClick={closeIfMobile}
                >
                  <span className="sidebar-icon-wrap" aria-hidden>
                    <NavIcon name={item.icon} />
                  </span>
                  <span className="label">{linkLabel(item)}</span>
                </Link>
              </li>
            ))}
          </ul>
          {user && (
            <div className="sidebar-user" aria-label="Compte connecté">
              <div className="sidebar-user-avatar" aria-hidden>
                {initialsFromUser(user)}
              </div>
              <div className="sidebar-user-meta">
                <span className="sidebar-user-email">{user.email}</span>
                <span className="sidebar-user-role">
                  {ROLE_LABELS[String(user.role || user.user_role || '').toLowerCase()] ||
                    String(user.role || user.user_role || '')}
                </span>
              </div>
            </div>
          )}
          <button type="button" className="logout-btn" onClick={handleLogout}>
            Déconnexion
          </button>
        </nav>
      </aside>
    </>
  );
};

export default Sidebar;
