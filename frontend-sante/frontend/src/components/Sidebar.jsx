import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getNavItemsForRole, getNavSectionTitle } from '../utils/navConfig.js';
import { portalLabel, portalSubtitle } from '../utils/portalAccess.js';
import SidebarUserPanel from './SidebarUserPanel.jsx';
import './Sidebar.css';

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
  if (itemPath === '/clinical') {
    return pathname === '/clinical';
  }
  if (itemPath === '/dashboard') {
    return pathname === '/dashboard';
  }
  if (itemPath === '/notifications') {
    return pathname === '/notifications';
  }
  if (itemPath === '/teleconsultation') {
    return pathname === '/teleconsultation' || pathname.startsWith('/consultation/');
  }
  return pathname === itemPath || pathname.startsWith(`${itemPath}/`);
}

const Sidebar = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { user, authLoading } = useAuth();
  const role = String(user?.role || user?.user_role || '').toLowerCase();

  const navItems = authLoading ? [] : getNavItemsForRole(role, user?.clinic_id);

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
            <div className="sidebar-brand-title">{portalLabel(role)}</div>
            <div className="sidebar-brand-sub">{portalSubtitle(role)}</div>
          </div>
        </div>

        <div className="sidebar-header">
          <h2 className="sidebar-menu-label">Menu</h2>
          <button type="button" className="close-btn" onClick={closeIfMobile} aria-label="Fermer">
            ✕
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Menu principal">
          {authLoading && <p className="sidebar-loading">Chargement…</p>}
          <div className="sidebar-nav-scroll">
            {navItems.length > 0 && (
              <div className="sidebar-section">
                <h3 className="sidebar-section-title">{getNavSectionTitle(role)}</h3>
                <ul>
                  {navItems.map((item) => (
                    <li key={item.path}>
                      <Link
                        to={item.path}
                        className={`sidebar-link ${pathIsActive(location.pathname, item.path) ? 'active' : ''}`}
                        onClick={closeIfMobile}
                      >
                        <span className="sidebar-icon-wrap" aria-hidden>
                          <NavIcon name={item.icon} />
                        </span>
                        <span className="label">{item.label}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <div className="sidebar-nav-footer">
            <SidebarUserPanel role={role} onNavigate={closeIfMobile} />
          </div>
        </nav>
      </aside>
    </>
  );
};

export default Sidebar;
