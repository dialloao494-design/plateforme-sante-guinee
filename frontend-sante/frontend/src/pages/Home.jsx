import { Link } from 'react-router-dom';
import './Home.css';

const Home = () => {
  return (
    <div className="home">
      <header className="home-header">
        <div className="home-header-inner">
          <div className="home-brand">
            <span className="home-brand-mark" aria-hidden />
            <h1 className="home-logo">Plateforme Santé</h1>
          </div>
          <nav className="home-nav" aria-label="Navigation publique">
            <Link to="/login" className="btn btn-primary home-nav-cta">
              Se connecter
            </Link>
          </nav>
        </div>
      </header>

      <main className="home-hero">
        <div className="home-hero-inner">
          <p className="home-eyebrow">Guinée · Santé numérique</p>
          <h2 className="home-title">Un parcours de soins clair pour patients et cabinets</h2>
          <p className="home-lead">
            Rendez-vous, téléconsultation, messagerie sécurisée et suivi — une expérience pensée pour les
            professionnels de santé et leurs patients.
          </p>
          <div className="home-actions">
            <Link to="/login" className="btn btn-primary home-btn-primary">
              Accéder à la plateforme
            </Link>
            <Link to="/signup" className="btn btn-ghost home-btn-secondary">
              Créer un compte
            </Link>
          </div>
        </div>
      </main>

      <footer className="home-footer">
        <p>&copy; {new Date().getFullYear()} Plateforme Santé Guinée. Tous droits réservés.</p>
      </footer>
    </div>
  );
};

export default Home;
