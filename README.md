Plateforme Santé MVP


Fonctionnalités
Authentification (JWT)

Gestion des rôles (admin / patient / médecin)

Prise de rendez-vous

Paiement Stripe

Liste des rendez-vous utilisateur



Setup


Backend


cd backend

pip install -r requirements.txt

uvicorn main:app –reload



Frontend


cd frontend

npm install

npm run dev



Variables d’environnement


Créer un fichier .env avec :

DATABASE_URL=

STRIPE_SECRET_KEY=

STRIPE_PUBLIC_KEY=



Notes


Projet MVP fonctionnel prêt pour amélioration UX et IA.