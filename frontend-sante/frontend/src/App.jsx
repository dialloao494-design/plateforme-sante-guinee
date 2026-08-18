import { Suspense, useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import AppRoutes from './routes/AppRoutes.jsx';
import Sidebar from './components/Sidebar.jsx';
import PageLoader from './components/PageLoader.jsx';
import { useAuth } from './contexts/AuthContext.jsx';
import { logAuthSessionFailure } from './utils/authSession.js';
import { ToastContainer } from 'react-toastify';
import { getShellContext } from './utils/appShellMeta.js';
import { portalLabel } from './utils/portalAccess.js';
import OfflineStatusIndicator from './components/OfflineStatusIndicator.jsx';
import './AppLayout.css';
import './HospitalTheme.css';

const PUBLIC_PATHS = new Set(['/', '/login', '/signup']);

function App() {
  const { authLoading, user, authInitError, retrySessionBootstrap } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [sessionTimedOut, setSessionTimedOut] = useState(false);

  const showClinicalShell = !(PUBLIC_PATHS.has(location.pathname) && !user);

  const shellMeta = useMemo(
    () => getShellContext(location.pathname, user?.role || user?.user_role),
    [location.pathname, user?.role, user?.user_role]
  );

  const role = user?.role || user?.user_role;
  const topbarTitle = user ? portalLabel(role) : 'Plateforme Santé';

  useEffect(() => {
    if (!authLoading) {
      setSessionTimedOut(false);
      return undefined;
    }
    const timer = window.setTimeout(() => {
      setSessionTimedOut(true);
      logAuthSessionFailure('app_session_timeout', new Error('Initial session bootstrap timeout'), {
        path: location.pathname,
      });
    }, 15_000);
    return () => window.clearTimeout(timer);
  }, [authLoading, location.pathname]);

  if (authLoading) {
    if (sessionTimedOut || authInitError) {
      return (
        <div className="app-loading" role="alert">
          <div className="login-card login-card--narrow" style={{ margin: '2rem auto', maxWidth: '28rem' }}>
            <p className="login-eyebrow">Plateforme Santé · Guinée</p>
            <h1 className="login-title">Session bloquée</h1>
            <p className="login-lead">
              {authInitError || 'La vérification de session a pris trop de temps. Réessayez ou reconnectez-vous.'}
            </p>
            <button type="button" className="btn btn-primary login-submit" onClick={() => retrySessionBootstrap()}>
              Réessayer
            </button>
          </div>
        </div>
      );
    }
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
          <Suspense fallback={<PageLoader label="Chargement de la page…" />}>
            <AppRoutes />
          </Suspense>
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
        <OfflineStatusIndicator />
      </>
    );
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Aller au contenu principal</a>
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
            <span className="app-topbar-title">{topbarTitle}</span>
            <span className="app-topbar-tag">Guinée</span>
          </div>
        </div>
      </header>

      <Sidebar isOpen={menuOpen} onClose={() => setMenuOpen(false)} />

      <main className="app-main" id="main-content" tabIndex="-1">
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
          <div className="app-clinical-status" aria-label="État du poste">
            <span aria-hidden="true" />
            Poste clinique opérationnel
          </div>
        </header>
        <section className="app-view">
          <Suspense fallback={<PageLoader label="Chargement du poste…" />}>
            <AppRoutes />
          </Suspense>
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
      <OfflineStatusIndicator />
    </div>
  );
}

export default App;
