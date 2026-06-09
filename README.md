# Plateforme Santé Guinée

Plateforme de santé numérique (MVP) : rendez-vous, paiements, messagerie, téléconsultation, tableaux de bord patient/médecin.

**Dépôt distant :** [github.com/dialloao494-design/plateforme-sante-guinee](https://github.com/dialloao494-design/plateforme-sante-guinee)

> **Passation projet :** si vous reprenez le projet, commencez par le dossier [`HANDOVER/README_START_HERE.md`](HANDOVER/README_START_HERE.md).

---

## Sommaire

1. [Récupération après perte matérielle](#1-récupération-après-perte-matérielle)
2. [Propriété du dépôt GitHub](#2-propriété-du-dépôt-github)
3. [Développement local](#3-développement-local)
4. [Docker local (HTTP)](#4-docker-local-http)
5. [Staging VPS (Ubuntu 22.04)](#5-staging-vps-ubuntu-2204)
6. [Production publique](#6-production-publique)
7. [Sauvegarde & restauration PostgreSQL](#7-sauvegarde--restauration-postgresql)
8. [Sécurité des secrets](#8-sécurité-des-secrets)
9. [Documentation déploiement](#9-documentation-déploiement)
10. [Comptes pilotes](#10-comptes-pilotes)

---

## 1. Récupération après perte matérielle

Si votre ordinateur est perdu ou cassé :

```bash
# Sur une nouvelle machine
git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git
cd plateforme-sante-guinee

# Secrets : recréer depuis les templates (ne sont PAS dans Git)
cp .env.example .env
cp .env.production.example .env.production    # VPS production
cp .env.staging.example .env.staging          # VPS staging
cp deploy/env/.env.backend.example deploy/env/.env.backend

# Regénérer SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Restaurer la base depuis backup VPS (voir section 7)
```

**Ce qui est dans Git :** code, Docker, nginx, scripts VPS, templates `.example`, documentation.  
**Ce qui n’y est pas :** `.env`, mots de passe Postgres, clés Stripe/Jitsi, certificats SSL (`certbot/`).

---

## 2. Propriété du dépôt GitHub

1. Connectez-vous à GitHub avec le compte **propriétaire** (`dialloao494-design` ou votre org).
2. Ouvrez **Settings → Collaborators** — vérifiez que vous êtes **Owner**.
3. Activez **Settings → Branches → Branch protection** sur `main` (PR obligatoires en équipe).
4. **Settings → Secrets and variables** : ne stockez les secrets de prod que si vous utilisez GitHub Actions deploy (optionnel).

Avant chaque push :

```powershell
.\scripts\git\pre_push_check.ps1
git add .
git commit -m "your message"
git push origin main
```

---

## 3. Développement local

### Backend (FastAPI)

```powershell
cd plateforme-sante-guinee
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Éditer .env : DATABASE_URL sqlite, SECRET_KEY, etc.
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend (Vite + React)

```powershell
cd frontend-sante\frontend
cp .env.example .env.development
# VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

### LAN (téléphone sur même Wi‑Fi)

```powershell
.\scripts\run_local_backend.ps1 -Lan
cd frontend-sante\frontend; npm run dev:lan
.\scripts\print_lan_urls.ps1
```

---

## 4. Docker local (HTTP)

```bash
cp .env.production.example .env.production
cp deploy/env/.env.backend.example deploy/env/.env.backend
# VITE_API_URL=http://localhost/api

docker compose --env-file .env.production up -d --build
```

- Application : http://localhost  
- API : http://localhost/api/health  

---

## 5. Staging VPS (Ubuntu 22.04)

**Objectif :** valider HTTPS, mobile 4G, téléconsultation avant la prod publique.

```bash
sudo apt update && sudo apt upgrade -y
sudo bash deploy/vps/install-docker.sh

git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git /opt/plateforme-sante
cd /opt/plateforme-sante

cp .env.staging.example .env.staging
cp deploy/env/.env.backend.example deploy/env/.env.backend
# Éditer DOMAIN=staging.votredomaine.com, POSTGRES_PASSWORD, SECRET_KEY, CORS, VITE_API_URL

# DNS A record staging → IP du VPS
sudo bash deploy/vps/init-ssl-staging.sh
sudo bash deploy/vps/deploy-staging.sh
sudo bash deploy/vps/validate-staging.sh
```

Checklist complète : [`deploy/STAGING_VALIDATION.md`](deploy/STAGING_VALIDATION.md)

---

## 6. Production publique

Après validation staging :

```bash
cp .env.production.example .env.production
# ENABLE_PILOT_SEED=false après premier bootstrap
# ENVIRONMENT=production dans deploy/env/.env.backend

sudo bash deploy/vps/init-ssl.sh
sudo bash deploy/vps/deploy-production.sh
```

Guide : [`deploy/PRODUCTION_DEPLOYMENT.md`](deploy/PRODUCTION_DEPLOYMENT.md)

---

## 7. Sauvegarde & restauration PostgreSQL

### Sauvegarde (cron quotidien sur VPS)

```bash
bash deploy/vps/backup-db.sh
bash scripts/db/backup_verify.sh
```

### Restauration (incident)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
gunzip -c backups/sante_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
  psql -U sante sante
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Test non destructif

```bash
bash scripts/db/restore_drill.sh backups/sante_YYYYMMDD.sql.gz
```

---

## 8. Sécurité des secrets

| Fichier | Git | Contenu |
|---------|-----|---------|
| `.env.example` | Oui | Modèle dev |
| `.env.production.example` | Oui | Modèle VPS prod |
| `.env.staging.example` | Oui | Modèle VPS staging |
| `.env`, `.env.production`, `.env.staging` | **Non** | Secrets réels |
| `deploy/env/.env.backend` | **Non** | API secrets sur serveur |
| `certbot/`, `backups/` | **Non** | SSL + dumps |

---

## 9. Documentation déploiement

| Document | Description |
|----------|-------------|
| [`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md) | Guide principal |
| [`deploy/ARCHITECTURE.md`](deploy/ARCHITECTURE.md) | Schéma infra |
| [`deploy/PRODUCTION_READINESS_REPORT.md`](deploy/PRODUCTION_READINESS_REPORT.md) | Audit |
| [`deploy/FINAL_LAUNCH_REPORT.md`](deploy/FINAL_LAUNCH_REPORT.md) | Statut lancement |
| [`deploy/STAGING_VALIDATION.md`](deploy/STAGING_VALIDATION.md) | Tests Phase 3 |
| [`deploy/PRODUCTION_DEPLOYMENT.md`](deploy/PRODUCTION_DEPLOYMENT.md) | Phase 4 |

---

## 10. Comptes pilotes

Activés si `ENABLE_PILOT_SEED=true` (désactiver en production publique).

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Médecin | `dr.amu@example.com` | `Doctor123!` |
| Patient | `test.patient@example.com` | `Patient123!` |

---

## Stack

- **Backend :** FastAPI, SQLAlchemy, PostgreSQL, Alembic, JWT, Stripe, Jitsi JWT  
- **Frontend :** React, Vite, React Router  
- **Infra :** Docker Compose, Nginx, Let's Encrypt, optional Sentry  

---

## Prochaine étape

**Staging validé → Production → Couche IA** (intégration après lancement public stable).
