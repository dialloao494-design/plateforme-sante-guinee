import AppRoutes from './routes/AppRoutes.jsx';
import Sidebar from './components/Sidebar.jsx';
import { useAuth } from './contexts/AuthContext.jsx';
import './AppLayout.css';

function App() {
  const { authLoading } = useAuth();

  if (authLoading) {
    return <div className="app-loading">Chargement de la session...</div>;
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">
        <header className="app-header">
          <div className="app-title">Plateforme Santé</div>
          <p className="app-subtitle">Book appointments, manage your schedule, and pay securely.</p>
        </header>
        <section className="app-view">
          <AppRoutes />
        </section>
      </main>
    </div>
  );
}

export default App;
