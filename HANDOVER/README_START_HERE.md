# README START HERE — Passation Plateforme Santé Guinée

**Public :** développeur reprenant le projet (passation interne)  
**Dernière mise à jour :** juin 2026  
**Version applicative :** 1.0.0 MVP

---

## 1. Qu'est-ce que ce projet ?

**Plateforme Santé Guinée** est une application SaaS e-santé (MVP) destinée au marché guinéen. Elle permet :

- aux **patients** de s'inscrire, trouver un médecin, prendre rendez-vous (physique ou téléconsultation), payer en ligne, consulter leur dossier ;
- aux **médecins** de gérer leur agenda, leurs patients, le dossier clinique (notes, synthèses, documents), la téléconsultation vidéo ;
- aux **administrateurs** de superviser les utilisateurs.

**État actuel :** MVP fonctionnel, validé en **pilote local Docker + PostgreSQL**. Production VPS autonome **non déployée** au moment de la passation (scripts prêts, exécution en attente de serveur + domaine).

**Dépôt Git :** [github.com/dialloao494-design/plateforme-sante-guinee](https://github.com/dialloao494-design/plateforme-sante-guinee)

---

## 2. Stack technique (résumé)

| Couche | Technologie | Emplacement |
|--------|-------------|-------------|
| Backend API | Python 3.12, FastAPI 0.110, SQLAlchemy 2, Alembic | Racine du dépôt (`main.py`, `routers/`, `services/`) |
| Frontend | React 19, Vite 8, React Router 7 | `frontend-sante/frontend/` |
| Base de données prod | PostgreSQL 16 (Docker) | Service `db` dans Compose |
| Base dev | SQLite (optionnel) | Fichier `sante.db` local |
| Reverse proxy | Nginx 1.27 | `deploy/nginx/` |
| Conteneurs | Docker Compose v2 | `docker-compose*.yml` |
| Auth | JWT (HS256) | `security.py` |
| Paiement | Stripe (+ stub Mobile Money) | `routers/payments.py` |
| Visio | Jitsi (self-hosted ou JaaS) | `routers/teleconsultation.py`, `deploy/jitsi/` |
| Dossier patient | API serveur + audit logs | `routers/patient_record.py`, `services/patient_record_service.py` |

---

## 3. Architecture (vue rapide)

```
Internet / mobile 4G
        │
        ▼
   Nginx (:443 HTTPS, :80 redirect)
        ├── /api/*     → FastAPI backend:8000
        ├── /api/ws/*  → WebSocket
        ├── /uploads/* → 403 (interdit volontairement)
        └── /*         → React SPA (build statique)
                │
                ├── PostgreSQL 16 (volume Docker pgdata)
                ├── uploads/ (documents cliniques)
                ├── Stripe API
                └── Jitsi (instance dédiée recommandée)
```

Schéma détaillé : [`../ARCHITECTURE_GLOBALE.md`](../ARCHITECTURE_GLOBALE.md)

---

## 4. Structure du dépôt (où chercher quoi)

```
plateforme-sante-guinee/
├── main.py                    # Point d'entrée FastAPI
├── routers/                   # Endpoints HTTP (auth, RDV, dossier, etc.)
├── services/                  # Logique métier
├── models/                    # ORM SQLAlchemy
├── schemas/                   # Pydantic (validation API)
├── alembic/                   # Migrations PostgreSQL
├── tests/                     # ~130 tests pytest
├── frontend-sante/frontend/   # Application React
├── deploy/                    # Nginx, VPS, Jitsi, certificats
│   ├── nginx/conf.d/          # Config reverse proxy
│   └── vps/                   # Scripts déploiement Ubuntu
├── scripts/                   # Utilitaires (verify, seed, tunnel)
├── docker-compose.yml         # Stack de base
├── docker-compose.pilot.yml   # Overlay pilote local (8088/9443)
├── docker-compose.staging.yml # Overlay VPS staging (LE)
├── docker-compose.prod.yml    # Overlay VPS production
├── .env.pilot                 # Config pilote (dans le repo — dev only)
├── .env.staging.example       # Template VPS staging
├── .env.production.example    # Template VPS production
└── HANDOVER/                  # ← Vous êtes ici (passation)
```

---

## 5. Accès nécessaires (à obtenir du propriétaire)

| Accès | Pourquoi | Où le configurer |
|-------|----------|------------------|
| **GitHub** (collaborateur ou Owner) | Push, PR, issues | Settings → Collaborators sur le dépôt |
| **VPS Ubuntu 22.04** (SSH root/sudo) | Hébergement autonome | Hetzner, OVH, Contabo, etc. |
| **Nom de domaine** + DNS | HTTPS Let's Encrypt permanent | Registrar (.gn ou .com) |
| **Stripe** (Dashboard test puis live) | Paiements carte | dashboard.stripe.com |
| **Jitsi** (self-hosted ou JaaS 8x8) | Téléconsultation vidéo | `deploy/jitsi/` ou compte 8x8 |
| **Secrets locaux** | JWT, Postgres, webhooks | Fichiers `.env*` (non versionnés) |
| **Compte Cloudflare** (optionnel) | Tunnel temporaire dev | `scripts/tunnel/` |

**Important :** les secrets réels ne sont **pas** dans Git. Recréer depuis les fichiers `.example` ou demander une copie chiffrée au propriétaire.

---

## 6. Environnements disponibles

| Profil | Commande Compose | Fichier env | URL typique | Usage |
|--------|------------------|-------------|-------------|-------|
| Dev local (SQLite) | `uvicorn main:app` | `.env` | `http://127.0.0.1:8000` | Développement rapide backend |
| Dev frontend | `npm run dev` | `frontend-sante/frontend/.env.development` | `http://127.0.0.1:5173` | UI hot-reload |
| **Pilote Docker** | `docker compose -f docker-compose.yml -f docker-compose.pilot.yml --env-file .env.pilot up -d` | `.env.pilot` | `http://localhost:8088` | **Recommandé pour démarrer** |
| Staging VPS | `docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging up -d` | `.env.staging` | `https://staging.domaine.gn` | Pré-production |
| Production VPS | `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d` | `.env.production` | `https://sante.domaine.gn` | Go-live public |

---

## 7. Ordre de lecture recommandé

Lire **dans cet ordre** avant toute modification importante :

| # | Document | Contenu |
|---|----------|---------|
| 1 | **Ce fichier** (`README_START_HERE.md`) | Vue d'ensemble, accès, structure |
| 2 | [`../docs/PLATFORM_EXCELLENCE_ROADMAP.md`](../docs/PLATFORM_EXCELLENCE_ROADMAP.md) | Verdict vivant, risques et priorités vers une plateforme hospitalière |
| 3 | [`INSTALLATION_COMPLETE.md`](./INSTALLATION_COMPLETE.md) | Installation locale + Docker + PostgreSQL |
| 4 | [`CHECKLIST_REPRISE.md`](./CHECKLIST_REPRISE.md) | Vérifications obligatoires avant de coder |
| 5 | [`../ARCHITECTURE_GLOBALE.md`](../ARCHITECTURE_GLOBALE.md) | Architecture technique détaillée |
| 6 | [`../DOSSIER_PATIENT.md`](../DOSSIER_PATIENT.md) | Module dossier clinique + RBAC + audit |
| 7 | [`DEPLOIEMENT_VPS.md`](./DEPLOIEMENT_VPS.md) | Mise en production autonome |
| 8 | [`INCIDENTS_ET_DEPANNAGE.md`](./INCIDENTS_ET_DEPANNAGE.md) | Problèmes connus et solutions |
| 9 | [`ROADMAP_90_JOURS.md`](./ROADMAP_90_JOURS.md) | Priorités produit et technique |
| 10 | [`../GUIDE_UTILISATEUR_PATIENT.md`](../GUIDE_UTILISATEUR_PATIENT.md) | Parcours patient |
| 11 | [`../GUIDE_UTILISATEUR_MEDECIN.md`](../GUIDE_UTILISATEUR_MEDECIN.md) | Parcours médecin |
| 12 | [`../RAPPORT_ETAT_PROJET.md`](../RAPPORT_ETAT_PROJET.md) | État du projet au moment de la passation |

Documentation complémentaire (référence) :

- [`../README.md`](../README.md) — guide racine du dépôt
- [`../DEPLOIEMENT.md`](../DEPLOIEMENT.md) — guide DevOps long format
- [`../deploy/STAGING_VALIDATION.md`](../deploy/STAGING_VALIDATION.md) — checklist staging
- [`../FINAL_AUTH_STABILIZATION.md`](../FINAL_AUTH_STABILIZATION.md) — comptes démo et auth

---

## 8. Démarrage express (15 minutes)

```powershell
# 1. Cloner
git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git
cd plateforme-sante-guinee

# 2. Lancer le pilote Docker (PostgreSQL + stack complète)
docker compose -f docker-compose.yml -f docker-compose.pilot.yml --env-file .env.pilot up -d --build

# 3. Vérifier
curl http://127.0.0.1:8088/api/health

# 4. Ouvrir dans le navigateur
# http://127.0.0.1:8088
```

Comptes démo (si seed activé) :

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Patient | `test.patient@example.com` | `Patient123!` |
| Médecin | `dr.mamady@example.com` | `Doctor123!` |

Provision manuelle des créneaux démo :

```bash
docker compose -f docker-compose.yml -f docker-compose.pilot.yml exec backend python scripts/pilot_provision_demo.py
```

Vérification automatisée pilote :

```bash
python scripts/pilot_go_live_verify.py
```

---

## 9. Commandes utiles au quotidien

```powershell
# État des conteneurs
docker compose -f docker-compose.yml -f docker-compose.pilot.yml ps

# Logs backend
docker compose -f docker-compose.yml -f docker-compose.pilot.yml logs backend -f

# Tests backend
python -m pytest tests/ -q

# Migration Alembic (sur PostgreSQL)
docker compose exec backend alembic upgrade head

# Rebuild frontend après changement VITE_*
docker compose -f docker-compose.yml -f docker-compose.pilot.yml up -d --build frontend
```

---

## 10. Points d'attention immédiats

1. **Ne pas committer** `.env`, `deploy/env/.env.backend`, `certbot/`, `backups/`, clés Stripe.
2. **Production :** mettre `ENABLE_PILOT_SEED=false` et `BYPASS_AVAILABILITY_VALIDATION=false`.
3. **JWT en localStorage** côté frontend — dette sécurité connue (voir roadmap).
4. **Clé Stripe test** peut être expirée — renouveler dans le Dashboard Stripe.
5. **VPS autonome non déployé** — le tunnel Cloudflare (`trycloudflare.com`) n'est **pas** une solution production.
6. **Téléconsultation** nécessite une instance Jitsi dédiée (pas `meet.jit.si` en iframe).

---

## 11. Contacts et propriété

| Élément | Détail |
|---------|--------|
| Organisation GitHub | `dialloao494-design` |
| Propriétaire initial | À confirmer avec le donneur de passation |
| Langue UI | Français |
| Langue code / docs | Français + anglais (commentaires mixtes) |

---

## 12. Prochaine action pour le repreneur

1. Lire [`CHECKLIST_REPRISE.md`](./CHECKLIST_REPRISE.md) et cocher chaque item.
2. Faire tourner le pilote Docker localement.
3. Exécuter `python -m pytest tests/ -q`.
4. Parcourir l'app en patient puis en médecin (comptes ci-dessus).
5. Lire [`ROADMAP_90_JOURS.md`](./ROADMAP_90_JOURS.md) pour comprendre les priorités.

**Bienvenue sur le projet. Toute la documentation de passation est dans le dossier `HANDOVER/`.**
