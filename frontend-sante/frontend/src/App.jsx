import AppRoutes from './routes/AppRoutes.jsx';
import Sidebar from './components/Sidebar.jsx';
import './AppLayout.css';

function App() {
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
