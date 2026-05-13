import { useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import AppRoutes from './routes/AppRoutes.jsx';
import Sidebar from './components/Sidebar.jsx';
import { useAuth } from './contexts/AuthContext.jsx';
import { ToastContainer } from 'react-toastify';
import { getShellContext } from './utils/appShellMeta.js';
import './AppLayout.css';

const PUBLIC_PATHS = new Set(['/', '/login', '/signup']);

function App() {
  const { authLoading, user } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  const showClinicalShell = !(PUBLIC_PATHS.has(location.pathname) && !user);

  const shellMeta = useMemo(
    () => getShellContext(location.pathname, user?.role || user?.user_role),
    [location.pathname, user?.role, user?.user_role]
  );

  if (authLoading) {
    return (
      <div className="app-loading" role="status" aria-live="polite">
        <div className="app-loading-inner">
          <span className="app-spinner" aria-hidden />
          <span>Chargement de la session…</span>
        </div>
      </div>
    );
  }

  if (!showClinicalShell) {
    return (
      <>
        <div className="app-public-root">
          <AppRoutes />
        </div>
        <ToastContainer
          position="top-right"
          autoClose={2800}
          hideProgressBar={false}
          newestOnTop
          closeOnClick
          pauseOnHover
          draggable
          theme="light"
          toastClassName="app-toast"
          className="app-toast-container"
        />
      </>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <button
          type="button"
          className="app-menu-toggle"
          aria-label="Ouvrir le menu"
          onClick={() => setMenuOpen(true)}
        >
          <span className="app-menu-bar" />
          <span className="app-menu-bar" />
          <span className="app-menu-bar" />
        </button>
        <div className="app-topbar-brand">
          <span className="app-topbar-mark" aria-hidden />
          <div className="app-topbar-text">
            <span className="app-topbar-title">Plateforme Santé</span>
            <span className="app-topbar-tag">Guinée</span>
          </div>
        </div>
      </header>

      <Sidebar isOpen={menuOpen} onClose={() => setMenuOpen(false)} />

      <main className="app-main">
        <header className="app-header">
          <nav className="app-breadcrumb" aria-label="Fil d'Ariane">
            <ol className="app-breadcrumb-list">
              {shellMeta.crumbs.map((item, index) => (
                <li key={`${item.label}-${index}`} className="app-breadcrumb-item">
                  {item.to ? (
                    <Link to={item.to} className="app-breadcrumb-link">
                      {item.label}
                    </Link>
                  ) : (
                    <span className="app-breadcrumb-current" aria-current="page">
                      {item.label}
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </nav>
        </header>
        <section className="app-view">
          <AppRoutes />
        </section>
      </main>
      <ToastContainer
        position="top-right"
        autoClose={2800}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        pauseOnHover
        draggable
        theme="light"
        toastClassName="app-toast"
        className="app-toast-container"
      />
    </div>
  );
}

export default App;
