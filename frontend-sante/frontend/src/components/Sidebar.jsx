import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Sidebar.css';

const Sidebar = ({ isOpen, onClose }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user, authLoading } = useAuth();
  const role = String(user?.role || user?.user_role || localStorage.getItem('user_role') || '').toLowerCase();

  const patientAdminMenu = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊', roles: ['patient', 'admin'], fallbackVisible: true },
    { path: '/appointments', label: 'Rendez-vous', icon: '📅', roles: ['patient', 'admin'], fallbackVisible: true },
    { path: '/dashboard', label: 'Profil', icon: '👤', roles: ['patient', 'admin'], fallbackVisible: true },
    { path: '/users', label: 'Utilisateurs', icon: '🛡️', roles: ['admin'], fallbackVisible: false },
  ];

  const doctorMenu = [
    { path: '/doctor/dashboard', label: 'Dashboard', icon: '📊', roles: ['doctor'], fallbackVisible: false },
    { path: '/doctor/appointments', label: 'Rendez-vous', icon: '📅', roles: ['doctor'], fallbackVisible: false },
    { path: '/doctor/messages', label: 'Messagerie', icon: '💬', roles: ['doctor'], fallbackVisible: false },
    { path: '/patients', label: 'Patients', icon: '🧑‍⚕️', roles: ['doctor'], fallbackVisible: false },
    { path: '/doctors', label: 'Profil', icon: '👤', roles: ['doctor'], fallbackVisible: false },
  ];

  const menuItems = role === 'doctor' ? doctorMenu : patientAdminMenu;

  const visibleItems = authLoading
    ? []
    : menuItems.filter((item) => (role ? item.roles.includes(role) : item.fallbackVisible));

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
          <button className="logout-btn" onClick={handleLogout}>Déconnexion</button>
        </nav>

      </aside>
    </>
  );
};

export default Sidebar;