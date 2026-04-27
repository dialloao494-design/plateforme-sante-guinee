import AppRoutes from './routes/AppRoutes.jsx';
import Sidebar from './components/Sidebar.jsx';
import { useAuth } from './contexts/AuthContext.jsx';
import { ToastContainer } from 'react-toastify';
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
          <p className="app-subtitle">Planifiez vos rendez-vous, suivez votre agenda et payez en toute sécurité.</p>
        </header>
        <section className="app-view">
          <AppRoutes />
        </section>
      </main>
      <ToastContainer
        position="top-right"
        autoClose={2600}
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
