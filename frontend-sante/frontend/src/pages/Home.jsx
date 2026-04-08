import { Link } from 'react-router-dom';
import './Home.css';

const Home = () => {
  return (
    <div className="home">
      <header className="header">
        <div className="container">
          <h1 className="logo">Plateforme Santé</h1>
          <nav>
            <Link to="/login" className="btn btn-primary">Se connecter</Link>
          </nav>
        </div>
      </header>

      <main className="hero-section">
        <div className="container">
          <div className="hero-content">
            <h2>Gestion simplifiée de vos patients</h2>
            <p>Une plateforme moderne pour les professionnels de santé.</p>
            <Link to="/login" className="btn btn-primary btn-large">Commencer</Link>
          </div>
        </div>
      </main>

      <footer className="footer">
        <div className="container">
          <p>&copy; 2024 Plateforme Santé. Tous droits réservés.</p>
        </div>
      </footer>
    </div>
  );
};

export default Home;