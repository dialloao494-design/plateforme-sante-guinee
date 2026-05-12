import { useState } from 'react';
import AppRoutes from './routes/AppRoutes.jsx';
import Sidebar from './components/Sidebar.jsx';
import { useAuth } from './contexts/AuthContext.jsx';
import { ToastContainer } from 'react-toastify';
import './AppLayout.css';

function App() {
  const { authLoading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

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
          <span className="app-topbar-title">Plateforme Santé</span>
          <span className="app-topbar-tag">Guinée</span>
        </div>
      </header>

      <Sidebar isOpen={menuOpen} onClose={() => setMenuOpen(false)} />

      <main className="app-main">
        <header className="app-header">
          <div className="app-title">Espace connecté</div>
          <p className="app-subtitle">
            Agenda, téléconsultation, messagerie sécurisée et dossiers patients — expérience clinique unifiée.
          </p>
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
      />
    </div>
  );
}

export default App;
