import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import './Sidebar.css';

const navItems = [
  { path: '/dashboard', label: 'Tableau de bord', icon: '📊', roles: ['patient', 'doctor', 'admin'] },
  { path: '/appointments', label: 'Mes rendez-vous', icon: '📅', roles: ['patient', 'admin'] },
  { path: '/doctors', label: 'Médecins', icon: '🩺', roles: ['patient', 'doctor', 'admin'] },
  { path: '/doctor/dashboard', label: 'Agenda clinique', icon: '🗂️', roles: ['doctor', 'admin'] },
  { path: '/doctor/appointments', label: 'File d’attente', icon: '📋', roles: ['doctor', 'admin'] },
  { path: '/doctor/messages', label: 'Messagerie', icon: '💬', roles: ['doctor', 'admin'] },
  { path: '/patients', label: 'Patients', icon: '👥', roles: ['doctor', 'admin'] },
  { path: '/users', label: 'Utilisateurs', icon: '🛡️', roles: ['admin'] },
];

function pathIsActive(pathname, itemPath) {
  if (itemPath === '/dashboard') {
    return pathname === '/dashboard';
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
            <div className="sidebar-brand-sub">Guinée · Prototype clinique</div>
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
                  <span className="icon" aria-hidden>
                    {item.icon}
                  </span>
                  <span className="label">{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
          <button type="button" className="logout-btn" onClick={handleLogout}>
            Déconnexion
          </button>
        </nav>
      </aside>
    </>
  );
};

export default Sidebar;
