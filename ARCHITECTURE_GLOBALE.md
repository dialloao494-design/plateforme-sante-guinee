# Architecture globale — Plateforme Santé Guinée

**Version :** 1.0 · **Stack :** FastAPI + React + PostgreSQL + Docker + Nginx  
**Public :** équipes techniques, intégrateurs, auditeurs

---

## 1. Vue d'ensemble

La Plateforme Santé Guinée est une application SaaS e-santé couvrant :

- inscription et authentification multi-rôles ;
- prise de rendez-vous (physique ou téléconsultation) ;
- paiement en ligne (Stripe, stubs Mobile Money) ;
- messagerie sécurisée par rendez-vous ;
- téléconsultation vidéo (Jitsi embarqué) ;
- dossier patient serveur (notes, synthèses, documents, audit).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           UTILISATEURS FINAUX                               │
│         Patient (navigateur / mobile)    Médecin    Administrateur          │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ HTTPS (443) ou HTTP (80 / pilote 8088)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NGINX (reverse proxy)                          │
│  /api/*  ──► backend:8000     /api/ws/* ──► WebSocket                       │
│  /uploads/* ──► 403 (interdit)     /* ──► frontend:80 (SPA React)          │
└───────────────┬─────────────────────────────────────┬───────────────────────┘
                │                                     │
                ▼                                     ▼
┌───────────────────────────────┐     ┌───────────────────────────────────────┐
│   BACKEND — FastAPI (Uvicorn) │     │   FRONTEND — React 19 + Vite 8        │
│   Python 3.12                 │     │   Axios · React Router 7              │
│   SQLAlchemy 2 · JWT · Stripe │     │   Jitsi React SDK · Toastify          │
└───────────────┬───────────────┘     └───────────────────────────────────────┘
                │
                ├──────────────► PostgreSQL 16 (production / pilote / staging)
                │                SQLite (développement local uniquement)
                │
                ├──────────────► Volume uploads/ (documents cliniques chiffrés)
                │
                ├──────────────► Stripe API + Webhooks
                │
                └──────────────► Jitsi (self-hosted ou JaaS 8x8) — JWT salle
```

---

## 2. Architecture frontend

### 2.1 Emplacement et stack

| Élément | Détail |
|---------|--------|
| Dossier | `frontend-sante/frontend/` |
| Build | Vite 8, sortie statique servie par nginx dans Docker |
| UI | React 19, CSS modules par page |
| Routing | React Router 7 — `src/routes/AppRoutes.jsx` |
| État global | `AuthContext`, `AppointmentContext`, `PatientContext` |
| HTTP | Axios via `src/services/httpClient.js` |
| API métier | `src/services/api.js` (wrappers par domaine) |

### 2.2 Résolution de l'URL API

| Environnement | Comportement |
|---------------|--------------|
| Développement | `VITE_API_URL` ou auto-détection `http://127.0.0.1:8000` |
| Docker / prod | `VITE_USE_RELATIVE_API=true` → requêtes vers `/api/` (nginx strip prefix) |
| Pilote local | `VITE_API_URL=http://localhost:8088/api` |

### 2.3 Pages principales par rôle

| Route | Rôles | Fonction |
|-------|-------|----------|
| `/`, `/login`, `/signup` | Public | Accueil, connexion, inscription |
| `/dashboard` | patient, doctor, admin | Tableau de bord |
| `/doctors`, `/doctors/:id` | patient, doctor, admin | Annuaire et fiche médecin |
| `/appointments` | patient, admin | Mes rendez-vous (patient) |
| `/doctor/dashboard` | doctor, admin | Tableau de bord médecin |
| `/doctor/appointments` | doctor, admin | File de rendez-vous |
| `/doctor/patient/:id` | doctor, admin | Dossier patient |
| `/consultation/:appointmentId` | patient, doctor, admin | Salle téléconsultation |
| `/messages/:appointmentId` | patient, doctor | Messagerie RDV |
| `/success`, `/cancel` | patient, doctor | Retour paiement Stripe |
| `/users` | admin | Gestion utilisateurs |

### 2.4 Protection des routes

`ProtectedRoute.jsx` vérifie :

1. présence d'un token JWT en `localStorage` ;
2. rôle utilisateur ∈ `allowedRoles` ;
3. redirection vers `/login` si non authentifié.

### 2.5 Téléconsultation côté client

1. `ConsultationRoom.jsx` charge le statut via `GET /teleconsultation/appointments/{id}/room-status`.
2. Demande d'accès via `GET /teleconsultation/appointments/{id}/access` (URL + JWT Jitsi).
3. `JitsiEmbeddedMeeting.jsx` embarque la visio via `@jitsi/react-sdk`.

---

## 3. Architecture backend

### 3.1 Stack

| Composant | Technologie |
|-----------|-------------|
| Framework | FastAPI 0.110 |
| Serveur ASGI | Uvicorn (1 worker par défaut ; multi-workers recommandé en prod) |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Auth | JWT HS256 (`python-jose`), bcrypt (`passlib`) |
| Rate limiting | SlowAPI |
| Paiements | Stripe SDK 7.x |

### 3.2 Point d'entrée

Fichier : `main.py`

Au démarrage :

- validation des secrets (`core/settings.py` → `enforce_production_boot()`) ;
- création du schéma SQLAlchemy + migrations ad hoc ;
- montage des 13 routeurs ;
- middleware CORS, TrustedHost, headers proxy.

### 3.3 Routeurs API

| Préfixe | Fichier | Domaine |
|---------|---------|---------|
| `/auth` | `routers/auth.py` | Inscription, login, `/me` |
| `/users` | `routers/users.py` | Liste utilisateurs, création admin |
| `/patients` | `routers/patient.py` | Profil démographique |
| `/patients` | `routers/patient_record.py` | Dossier clinique (notes, synthèses, documents) |
| `/doctors` | `routers/doctor.py` | Profils médecins, disponibilités |
| `/doctor` | `routers/doctor_dashboard.py` | Dashboard médecin |
| `/appointments` | `routers/appointments.py` | Rendez-vous (API principale) |
| `/rendezvous` | `routers/rendezvous.py` | Rendez-vous (API legacy) |
| `/payments` | `routers/payments.py` | Stripe, webhooks, stubs |
| `/teleconsultation` | `routers/teleconsultation.py` | Accès salle, config Jitsi |
| `/messages` | `routers/messages.py` | Messagerie + pièces jointes |
| `/notifications` | `routers/notifications.py` | Notifications in-app |
| `/ws` | `routers/ws.py` | WebSocket (health, live) |

**Santé :** `GET /health`, `GET /health/ready` (ping base de données).

### 3.4 Couche services (logique métier)

| Service | Responsabilité |
|---------|----------------|
| `rendezvous_service.py` | Validation RDV, conflits, disponibilités |
| `availability_service.py` | Créneaux horaires médecins |
| `payment_settlement.py` | Verrouillage paiement, settlement |
| `stripe_webhook_processor.py` | Webhooks idempotents Stripe |
| `teleconsultation_access.py` | Fenêtre horaire, gate paiement |
| `jitsi_jwt.py` | Génération JWT Jitsi (self-hosted / JaaS) |
| `patient_record_service.py` | CRUD dossier patient |
| `patient_record_access.py` | RBAC dossier |
| `clinical_audit_service.py` | Journal d'audit immutable |
| `message_attachment_service.py` | Pièces jointes messagerie chiffrées |
| `user_provisioning.py` | Inscription sécurisée |

---

## 4. PostgreSQL

### 4.1 Usage par environnement

| Environnement | Moteur | Connexion |
|---------------|--------|-----------|
| Dev local (rapide) | SQLite | `DATABASE_URL=sqlite:///./sante.db` |
| Pilote / staging / prod | PostgreSQL 16 | `postgresql://user:pass@db:5432/sante` |

**Règle pilote :** PostgreSQL obligatoire. SQLite ne convient pas à la concurrence ni au pilote multi-utilisateurs.

### 4.2 Pool de connexions

En PostgreSQL (`database.py`) :

- `pool_pre_ping=True`
- `pool_size=5`, `max_overflow=10`

### 4.3 Tables principales

```
users ──┬── patients ──┬── clinical_notes
        │              ├── consultation_summaries
        │              └── patient_documents
        ├── doctors ──── doctor_availabilities
        └── (admin)

rendezvous ── payments ── messages
clinical_audit_logs (transversal)
stripe_webhook_events
```

### 4.4 Migrations

Double mécanisme :

1. **Alembic** (versionné) — révisions dans `alembic/versions/`
2. **Migrations ad hoc** — `database_migrations.py` (géolocalisation médecins, dossier patient)

Le conteneur backend exécute automatiquement `alembic upgrade head` au démarrage (`scripts/docker/entrypoint-backend.sh`).

---

## 5. Docker

### 5.1 Fichiers Compose

| Fichier | Usage |
|---------|-------|
| `docker-compose.yml` | Stack de base (db, backend, frontend, nginx HTTP) |
| `docker-compose.pilot.yml` | Pilote local : HTTPS self-signed, Postgres exposé 5433 |
| `docker-compose.staging.yml` | Staging VPS : Let's Encrypt, ports 80/443 |
| `docker-compose.prod.yml` | Production : flags sécurisés, certbot renew |

### 5.2 Services

| Service | Image | Rôle |
|---------|-------|------|
| `db` | `postgres:16-alpine` | Base de données, volume `pgdata` |
| `backend` | `Dockerfile` (Python 3.12) | API FastAPI, volume `uploads` |
| `frontend` | `frontend-sante/frontend/Dockerfile` | SPA React buildée |
| `nginx` | `nginx:1.27-alpine` | Reverse proxy, TLS |
| `certbot` | `certbot/certbot` | Renouvellement SSL (staging/prod) |

### 5.3 Ports (pilote local)

| Service | Port hôte |
|---------|-----------|
| HTTP | 8088 |
| HTTPS | 9443 |
| PostgreSQL | 5433 |

### 5.4 Commande pilote

```bash
docker compose -f docker-compose.yml -f docker-compose.pilot.yml --env-file .env.pilot up -d --build
```

---

## 6. Nginx

### 6.1 Configurations

| Fichier | Contexte |
|---------|----------|
| `deploy/nginx/conf.d/app.http-only.conf` | Docker local HTTP |
| `deploy/nginx/conf.d/app.pilot-https.conf` | Pilote HTTP + HTTPS self-signed |
| `deploy/nginx/conf.d/app.conf.template` | Staging/prod Let's Encrypt |

### 6.2 Routage

| Chemin client | Destination | Remarque |
|---------------|-------------|----------|
| `/api/*` | `backend:8000/*` | Préfixe `/api` retiré |
| `/api/ws/*` | `backend:8000/ws/*` | Upgrade WebSocket |
| `/uploads/*` | **403** | Fichiers jamais servis publiquement |
| `/*` | `frontend:80` | SPA React (fallback index.html) |

### 6.3 Sécurité edge

- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- HSTS en HTTPS production
- `client_max_body_size 25m` (upload documents)

---

## 7. Jitsi (téléconsultation)

### 7.1 Modes supportés

| Mode | Variables | Usage |
|------|-----------|-------|
| Self-hosted | `JITSI_DOMAIN`, `JITSI_APP_ID`, `JITSI_APP_SECRET` | Instance Docker locale (`deploy/jitsi/`) |
| JaaS 8x8 | `JITSI_JAAS=true`, clé privée RS256 | Production cloud |

**Interdit :** `meet.jit.si` public pour l'embed (pas de JWT maîtrisé).

### 7.2 Flux d'accès

```
Patient/Médecin → GET /teleconsultation/appointments/{id}/room-status
               → GET /teleconsultation/appointments/{id}/access
                    ├── Vérifie rôle + lien RDV
                    ├── Vérifie payment_status = paid
                    ├── Vérifie fenêtre horaire (±15 min avant, grace après)
                    └── Retourne meeting_url + jitsi_jwt
               → Frontend embarque JitsiEmbeddedMeeting
               → POST /teleconsultation/appointments/{id}/end (fin session)
```

### 7.3 Variables clés

```env
TELECONSULT_PROVIDER=jitsi
JITSI_DOMAIN=127.0.0.1:8443
JITSI_APP_ID=pilot-sante-guinee
JITSI_APP_SECRET=<secret-32-chars-min>
TELECONSULT_JOIN_EARLY_MINUTES=15
TELECONSULT_JOIN_LATE_MINUTES=30
```

Frontend : `VITE_TELECONSULT_PROVIDER=jitsi`, `VITE_JITSI_DOMAIN` (doit correspondre au backend).

---

## 8. Stripe (paiements)

### 8.1 Flux patient

```
1. POST /payments/create-intent  → URL Stripe Checkout
2. Patient paie sur Stripe Hosted Checkout
3. Retour /success → POST /payments/confirm-checkout
4. Webhook POST /payments/webhook → settlement idempotent
5. rendezvous.payment_status = paid, status = confirmed
6. meeting_link généré après paiement (téléconsultation)
```

### 8.2 Webhooks

- Signature vérifiée via `STRIPE_WEBHOOK_SECRET`
- Idempotence sur `event.id` (`stripe_webhook_events`)
- Événements : `checkout.session.completed`, `payment_intent.succeeded`, remboursements

### 8.3 Modes alternatifs

| Mode | Activation | Usage |
|------|------------|-------|
| Stub dev | `ALLOW_STUB_PAYMENT=true` + `PAYMENT_STUB_TOKEN` | Pilote contrôlé sans carte |
| Orange Money GN | Stub (live : `ORANGE_MONEY_LIVE=true`) | Bêta |
| MTN MoMo GN | Stub (live : `MTN_MOMO_LIVE=true`) | Bêta |

### 8.4 Variables

```env
STRIPE_SECRET_KEY=sk_test_... ou sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_test_... ou pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
VITE_STRIPE_PUBLISHABLE_KEY=pk_...  # frontend build
```

---

## 9. Système d'authentification

### 9.1 Mécanisme

- **JWT Bearer** (HS256), durée configurable (`ACCESS_TOKEN_EXPIRE_MINUTES`, défaut 60 min)
- Secret : `SECRET_KEY` (32+ caractères obligatoire en staging/prod)
- Endpoints :
  - `POST /auth/register` — inscription patient ou médecin
  - `POST /auth/login-json` — connexion JSON (frontend)
  - `POST /auth/login` — connexion OAuth2 form (Swagger)
  - `GET /auth/me` — profil courant

### 9.2 Stockage côté client

Token JWT en `localStorage` (`AuthContext.jsx`).

> **Note sécurité :** acceptable pour pilote fermé ; migration vers cookies HttpOnly recommandée en production publique.

### 9.3 Validations

- Cohérence rôle JWT ↔ rôle base de données à chaque requête
- Rate limit : login 10/min, register 5/min (configurable)
- Inscription publique limitée aux rôles `patient` et `doctor` (`core/roles.py`)

---

## 10. Rôles et permissions

### 10.1 Rôles

| Rôle | Création | Périmètre |
|------|----------|-----------|
| **patient** | Inscription publique | Ses RDV, son dossier (lecture), paiements, téléconsultation |
| **doctor** | Inscription publique + profil médecin | Ses RDV, patients liés, écriture dossier clinique, disponibilités |
| **admin** | `POST /users/admins` ou bootstrap env | Accès global, gestion utilisateurs, settlement manuel |

### 10.2 Matrice RBAC simplifiée

| Ressource | patient | doctor | admin |
|-----------|---------|--------|-------|
| Créer RDV | ✅ (pour soi) | ❌ | ✅ |
| Lire dossier patient | ✅ (sien) | ✅ (patients liés par RDV) | ✅ |
| Écrire note / synthèse / document | ❌ | ✅ | ✅ |
| Gérer disponibilités | ❌ | ✅ (sien) | ✅ |
| Accès téléconsultation | ✅ (son RDV) | ✅ (son RDV) | ✅ |
| Liste utilisateurs | ❌ | ❌ | ✅ |

### 10.3 Guards backend

```python
require_roles(["doctor", "admin"])   # Décorateur FastAPI
get_current_user                      # JWT + vérif DB
PatientRecordAccessPolicy             # RBAC dossier clinique
PaymentAccessPolicy                   # Gate paiement téléconsultation
```

---

## 11. Arborescence projet (extrait)

```
plateforme-sante-guinee/
├── main.py                    # Entrée FastAPI
├── core/                      # Settings, policies, limiter
├── routers/                   # Endpoints HTTP
├── services/                  # Logique métier
├── models/                    # ORM SQLAlchemy
├── schemas/                   # Pydantic
├── alembic/                   # Migrations versionnées
├── frontend-sante/frontend/   # SPA React
├── deploy/                    # Nginx, VPS scripts, Jitsi
├── docker-compose*.yml
├── scripts/                   # E2E, pilote, provisioning
└── tests/                     # Pytest (~130+ scénarios)
```

---

## 12. Documentation connexe

| Document | Contenu |
|----------|---------|
| [DOSSIER_PATIENT.md](./DOSSIER_PATIENT.md) | Tables cliniques, RBAC, audit |
| [DEPLOIEMENT.md](./DEPLOIEMENT.md) | Procédure VPS complète |
| [GUIDE_UTILISATEUR_MEDECIN.md](./GUIDE_UTILISATEUR_MEDECIN.md) | Guide médecin |
| [GUIDE_UTILISATEUR_PATIENT.md](./GUIDE_UTILISATEUR_PATIENT.md) | Guide patient |
| [RAPPORT_ETAT_PROJET.md](./RAPPORT_ETAT_PROJET.md) | Maturité et roadmap |
