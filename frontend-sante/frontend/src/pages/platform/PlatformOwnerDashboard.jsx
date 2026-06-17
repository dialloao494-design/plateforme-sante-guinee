import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import './PlatformOwner.css';

export default function PlatformOwnerDashboard() {
  const { user } = useAuth();

  const cards = [
    {
      title: 'Cliniques',
      description: 'Créer, activer ou désactiver toutes les cliniques de la plateforme.',
      to: '/clinical/admin',
      cta: 'Administration clinique',
    },
    {
      title: 'Utilisateurs',
      description: 'Gérer tous les comptes, créer des administrateurs de clinique, désactiver des accès.',
      to: '/users',
      cta: 'Utilisateurs',
    },
    {
      title: 'Paramètres plateforme',
      description: 'Configuration globale, abonnements et facturation (à venir).',
      to: '/platform/settings',
      cta: 'Paramètres',
    },
    {
      title: 'Système & déploiement',
      description: 'Administration système, santé des services et déploiements (à venir).',
      to: '/platform/system',
      cta: 'Système',
    },
  ];

  return (
    <div className="platform-owner-page">
      <header className="platform-owner-header">
        <h1>Console Propriétaire Plateforme</h1>
        <p>
          Bienvenue, {user?.full_name || user?.email}. Vous disposez des droits complets sur la
          plateforme Santé Guinée.
        </p>
      </header>

      <div className="platform-owner-grid">
        {cards.map((card) => (
          <article key={card.title} className="platform-owner-card">
            <h2>{card.title}</h2>
            <p>{card.description}</p>
            <Link to={card.to} className="platform-owner-link">
              {card.cta}
            </Link>
          </article>
        ))}
      </div>
    </div>
  );
}
