import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Sidebar.css';

const Sidebar = ({ isOpen, onClose }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user, authLoading } = useAuth();
  const role = user?.role || user?.user_role;

  const menuItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊', roles: ['patient', 'doctor', 'admin'] },
    { path: '/appointments', label: 'Rendez-vous', icon: '📅', roles: ['patient'] },
    { path: '/patients', label: 'Patients', icon: '🧾', roles: ['doctor'] },
    { path: '/appointments', label: 'Agenda', icon: '🗓️', roles: ['doctor'] },
    { path: '/users', label: 'Utilisateurs', icon: '🛡️', roles: ['admin'] },
  ];

  console.log('[Sidebar] user:', user);
  console.log('[Sidebar] role:', role);

  const visibleItems = authLoading
    ? []
    : menuItems.filter((item) => role && item.roles.includes(role));

  const handleLogout = () => {
    logout();
    if (typeof onClose === 'function') {
      onClose();
    }
    navigate('/login');
  };

  return (
    <>
      <div
        className={`sidebar-overlay ${isOpen ? 'active' : ''}`}
        onClick={onClose}
      ></div>

      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>

        <div className="sidebar-header">
          <h2>Menu</h2>
          <button className="close-btn" onClick={onClose}>✖</button>
        </div>

        <nav className="sidebar-nav">
          {authLoading && <p>Chargement...</p>}
          <ul>
            {visibleItems.map((item) => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`sidebar-link ${
                    location.pathname === item.path ? 'active' : ''
                  }`}
                  onClick={onClose}
                >
                  <span className="icon">{item.icon}</span>
                  <span className="label">{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </nav>

      </aside>
    </>
  );
};

export default Sidebar;