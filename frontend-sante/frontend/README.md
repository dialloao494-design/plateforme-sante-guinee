# Plateforme Santé

Une plateforme frontend moderne pour les professionnels de santé, similaire à Doctolib, construite avec React et Vite.

## Fonctionnalités

### Authentification
- Page de connexion avec email et mot de passe
- Structure préparée pour l'inscription
- Gestion d'état d'authentification avec React Context

### Tableau de bord
- Message de bienvenue personnalisé
- Liste des patients avec données mockées
- Bouton d'ajout de patient (placeholder)
- Interface propre avec cartes

### Navigation
- Routage React avec React Router
- Routes protégées pour le tableau de bord
- Header avec le nom de la plateforme
- Sidebar responsive

### Design
- Design médical professionnel (blanc et bleu)
- Interface responsive
- Composants réutilisables

## Structure du projet

```
src/
├── components/
│   ├── Header.jsx          # En-tête de l'application
│   ├── Sidebar.jsx         # Menu latéral
│   ├── PatientCard.jsx     # Carte patient individuelle
│   ├── PatientList.jsx     # Liste des patients
│   ├── Header.css
│   ├── Sidebar.css
│   ├── PatientCard.css
│   └── PatientList.css
├── pages/
│   ├── Home.jsx            # Page d'accueil/landing
│   ├── Login.jsx           # Page de connexion
│   ├── Dashboard.jsx       # Tableau de bord principal
│   ├── Home.css
│   ├── Login.css
│   └── Dashboard.css
├── routes/
│   ├── AppRoutes.jsx       # Configuration des routes
│   └── ProtectedRoute.jsx  # Route protégée
├── services/
│   └── api.js              # Service API avec Axios
├── contexts/
│   └── AuthContext.jsx     # Contexte d'authentification
├── App.jsx
├── main.jsx
├── index.css               # Styles globaux
└── App.css
```

## Technologies utilisées

- **React 19** - Bibliothèque frontend
- **Vite** - Outil de build rapide
- **React Router** - Routage
- **Axios** - Requêtes HTTP
- **CSS Modules** - Styles modulaires

## Installation et démarrage

1. Cloner le repository
2. Installer les dépendances :
   ```bash
   npm install
   ```
3. Démarrer le serveur de développement :
   ```bash
   npm run dev
   ```
4. Ouvrir http://localhost:5174 dans votre navigateur

## Connexion de test

- **Email** : doctor@example.com
- **Mot de passe** : password

## API Integration

Le service API est configuré dans `src/services/api.js`. Remplacez `API_BASE_URL` par l'URL de votre backend.

Les endpoints suivants sont préparés :
- `POST /auth/login` - Connexion
- `GET /patients` - Récupérer les patients
- `POST /patients` - Créer un patient

## Développement

### Scripts disponibles

- `npm run dev` - Serveur de développement
- `npm run build` - Build de production
- `npm run preview` - Prévisualisation du build
- `npm run lint` - Linting du code

### Structure recommandée

Le projet suit une architecture modulaire avec séparation claire des préoccupations :
- **Components** : Composants réutilisables
- **Pages** : Pages de l'application
- **Services** : Logique métier et appels API
- **Routes** : Configuration du routage
- **Contexts** : Gestion d'état global

## Fonctionnalités à implémenter

- Inscription utilisateur
- Gestion complète des patients (CRUD)
- Système de rendez-vous
- Notifications
- Recherche et filtres
- Profil utilisateur
- Historique médical

## Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Commit les changements (`git commit -am 'Ajout nouvelle fonctionnalité'`)
4. Push la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Créer une Pull Request

## Licence

Ce projet est sous licence MIT.
