# Installation complète — Plateforme Santé Guinée

Guide pas-à-pas pour installer et faire tourner la plateforme en local, avec ou sans Docker.

---

## 1. Prérequis système

### Windows (environnement actuel du projet)

| Outil | Version min. | Vérification |
|-------|--------------|--------------|
| Git | 2.x | `git --version` |
| Python | 3.12 | `python --version` |
| Node.js | 20 LTS | `node --version` |
| npm | 10+ | `npm --version` |
| Docker Desktop | 4.x + WSL2 | `docker compose version` |

**Docker sur Windows :** si Docker échoue au démarrage, voir [`../docs/DOCKER_VIRTUALIZATION_FIX.md`](../docs/DOCKER_VIRTUALIZATION_FIX.md) (WSL2 + virtualisation BIOS).

### Linux / macOS

- Docker Engine 24+ et Compose v2
- Python 3.12, Node 20

---

## 2. Récupération du code

```bash
git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git
cd plateforme-sante-guinee
```

---

## 3. Option A — Pilote Docker (recommandé)

C'est l'environnement le plus proche de la production. Utilise **PostgreSQL 16** dans Docker.

### 3.1 Fichiers de configuration

Le fichier `.env.pilot` est déjà présent à la racine (profil pilote). Pour repartir de zéro :

```bash
cp .env.staging.example .env.pilot   # puis adapter ports et mots de passe
cp deploy/env/.env.backend.example deploy/env/.env.backend
```

Variables clés dans `.env.pilot` :

| Variable | Valeur pilote | Rôle |
|----------|---------------|------|
| `HTTP_PORT` | `8088` | Port HTTP nginx |
| `HTTPS_PORT` | `9443` | Port HTTPS self-signed |
| `POSTGRES_USER` | `sante` | Utilisateur DB |
| `POSTGRES_PASSWORD` | *(fort, unique)* | Mot de passe DB |
| `POSTGRES_DB` | `sante` | Nom base |
| `VITE_API_URL` | `/api` | API same-origin via nginx |
| `VITE_SAME_ORIGIN_API` | `true` | Frontend appelle `/api` sur même domaine |
| `ENABLE_PILOT_SEED` | `false` en prod, `true` pour démo | Comptes démo au boot |

Variables clés dans `deploy/env/.env.backend` :

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Secret JWT — générer : `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ENVIRONMENT` | `staging` pour pilote |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,backend,*.trycloudflare.com` si tunnel |
| `STRIPE_SECRET_KEY` | Clé secrète Stripe test |
| `STRIPE_PUBLISHABLE_KEY` | Clé publique (aussi dans `.env.pilot` pour build frontend) |
| `JITSI_APP_SECRET` | Secret JWT Jitsi (16+ caractères) |
| `JITSI_DOMAIN` | Domaine Jitsi (ex. `127.0.0.1:8443` en local) |

### 3.2 Lancement

```powershell
docker compose -f docker-compose.yml -f docker-compose.pilot.yml --env-file .env.pilot up -d --build
```

Services démarrés :

| Service | Rôle | Port exposé |
|---------|------|-------------|
| `db` | PostgreSQL 16 | `5433` → 5432 |
| `backend` | FastAPI | interne `:8000` |
| `frontend` | React (nginx) | interne `:80` |
| `nginx` | Reverse proxy | `8088` HTTP, `9443` HTTPS |

### 3.3 Vérifications

```powershell
# Santé API
curl http://127.0.0.1:8088/api/health

# État conteneurs
docker compose -f docker-compose.yml -f docker-compose.pilot.yml ps

# Migrations Alembic (automatiques au boot via entrypoint)
docker compose -f docker-compose.yml -f docker-compose.pilot.yml exec backend alembic current

# Données démo (4 médecins × 5 créneaux)
docker compose -f docker-compose.yml -f docker-compose.pilot.yml exec backend python scripts/pilot_provision_demo.py

# Suite de vérification complète
python scripts/pilot_go_live_verify.py
```

URLs :

- Application : http://127.0.0.1:8088
- API : http://127.0.0.1:8088/api
- Docs API (staging) : http://127.0.0.1:8088/api/docs
- PostgreSQL (depuis l'hôte) : `postgresql://sante:<password>@127.0.0.1:5433/sante`

### 3.4 Arrêt / redémarrage

```powershell
# Arrêt
docker compose -f docker-compose.yml -f docker-compose.pilot.yml down

# Redémarrage (données conservées dans volume pgdata)
docker compose -f docker-compose.yml -f docker-compose.pilot.yml up -d

# Reset complet (DESTRUCTIF — efface la base)
docker compose -f docker-compose.yml -f docker-compose.pilot.yml down -v
```

---

## 4. Option B — Développement local sans Docker

Utile pour itérer rapidement sur le backend ou le frontend séparément.

### 4.1 Backend (SQLite)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env
# Éditer .env :
#   DATABASE_URL=sqlite:///./sante.db
#   SECRET_KEY=<générer>
#   ENVIRONMENT=development
#   DEBUG=true

uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API : http://127.0.0.1:8000/docs

**Limitation :** le dossier patient (module A1) et certaines migrations Alembic sont optimisées pour PostgreSQL. Préférer Docker pour les tests dossier/audit.

### 4.2 Frontend (Vite dev server)

```powershell
cd frontend-sante\frontend
cp .env.example .env.development

# .env.development :
# VITE_API_URL=http://127.0.0.1:8000

npm install
npm run dev
```

UI : http://127.0.0.1:5173

### 4.3 Test LAN (téléphone sur même Wi-Fi)

```powershell
# Terminal 1 — backend accessible LAN
.\scripts\run_local_backend.ps1 -Lan

# Terminal 2 — frontend LAN
cd frontend-sante\frontend
npm run dev:lan

# Afficher les URLs
.\scripts\print_lan_urls.ps1
```

---

## 5. Option C — Docker HTTP simple (sans pilote)

```bash
cp .env.production.example .env.production
cp deploy/env/.env.backend.example deploy/env/.env.backend
# VITE_API_URL=http://localhost/api dans .env.production

docker compose --env-file .env.production up -d --build
```

Application : http://localhost

---

## 6. PostgreSQL — détails

### 6.1 Connexion depuis l'hôte (pilote)

```
Host:     127.0.0.1
Port:     5433
User:     sante
Password: (voir .env.pilot POSTGRES_PASSWORD)
Database: sante
```

Outils compatibles : pgAdmin, DBeaver, `psql`.

```bash
docker compose -f docker-compose.yml -f docker-compose.pilot.yml exec db psql -U sante -d sante
```

### 6.2 Migrations Alembic

Les migrations sont dans `alembic/versions/`. Head actuel (juin 2026) : `20260525_0003_patient_dossier`.

```bash
# Appliquer toutes les migrations
docker compose exec backend alembic upgrade head

# Voir version courante
docker compose exec backend alembic current

# Créer une migration (dev)
docker compose exec backend alembic revision --autogenerate -m "description"
```

Tables dossier patient (module A1) :

- `clinical_notes`
- `consultation_summaries`
- `patient_documents`
- `clinical_audit_logs`

### 6.3 Reset base pilote

```bash
docker compose -f docker-compose.yml -f docker-compose.pilot.yml exec backend python scripts/reset_pilot_db.py
```

---

## 7. Variables d'environnement — référence complète

### 7.1 Fichiers et hiérarchie

```
.env                    → Dev local (uvicorn direct)
.env.pilot              → Pilote Docker local
.env.staging            → VPS staging (non versionné)
.env.production         → VPS production (non versionné)
deploy/env/.env.backend → Secrets backend (monté dans conteneur backend)
frontend-sante/frontend/.env.development → Build dev Vite
```

**Règle :** les variables `VITE_*` sont injectées **au build** du frontend Docker. Après modification, rebuild :

```bash
docker compose ... up -d --build frontend
```

### 7.2 Variables backend critiques

| Variable | Dev | Staging/Prod | Notes |
|----------|-----|--------------|-------|
| `ENVIRONMENT` | `development` | `staging` / `production` | Active les garde-fous prod |
| `SECRET_KEY` | any | **fort, unique** | JWT signing |
| `DATABASE_URL` | sqlite ou postgres | `postgresql://...@db:5432/sante` | Auto en Docker |
| `ALLOWED_HOSTS` | `*` implicite | `domaine,backend` | TrustedHost middleware |
| `CORS_ORIGINS` | auto LAN | URL HTTPS publique | |
| `ENABLE_PILOT_SEED` | true | **false** en prod | Comptes démo |
| `BYPASS_AVAILABILITY_VALIDATION` | false | **false** | Ne jamais activer en prod |
| `ALLOW_STUB_PAYMENT` | true | false prod | Paiement simulé |
| `STRIPE_SECRET_KEY` | sk_test_ | sk_live_ en prod | |
| `JITSI_APP_SECRET` | requis si Jitsi | requis | |
| `ENABLE_TUNNEL_TEST` | true si tunnel CF | false VPS | CORS tunnel |

### 7.3 Variables frontend (build)

| Variable | Valeur recommandée Docker/VPS |
|----------|----------------------------|
| `VITE_API_URL` | `/api` |
| `VITE_SAME_ORIGIN_API` | `true` |
| `VITE_TELECONSULT_PROVIDER` | `jitsi` |
| `VITE_STRIPE_PUBLISHABLE_KEY` | `pk_test_...` ou `pk_live_...` |
| `VITE_JITSI_DOMAIN` | domaine Jitsi public |

---

## 8. Tests automatisés

```powershell
# Activer venv si dev local
pip install -r requirements.txt

# Suite complète
python -m pytest tests/ -v

# Par domaine
python -m pytest tests/test_patient_record_security.py -v
python -m pytest tests/test_registration_security.py -v
python -m pytest tests/test_payment_settlement_security.py -v
python -m pytest tests/test_teleconsult_access.py -v
```

Scripts de validation manuelle :

| Script | Usage |
|--------|-------|
| `scripts/pilot_go_live_verify.py` | Checklist GO PILOTE (API + dossier + audit) |
| `scripts/vps_autonomous_verify.py` | Validation VPS public HTTPS |
| `scripts/verify_pilot_logins.py` | Test connexions comptes démo |
| `deploy/vps/validate-staging.sh` | Validation post-déploiement VPS |

---

## 9. Jitsi local (téléconsultation)

La téléconsultation embarquée nécessite une instance Jitsi **sans lobby OAuth**.

```powershell
.\scripts\start_jitsi_dev.ps1
```

Puis configurer dans `deploy/env/.env.backend` :

```
JITSI_DOMAIN=127.0.0.1:8443
JITSI_APP_ID=plateforme-sante-guinee
JITSI_APP_SECRET=<secret généré>
```

Documentation : [`../deploy/jitsi/README.md`](../deploy/jitsi/README.md)

---

## 10. Tunnel public temporaire (dev uniquement)

Pour tester depuis un téléphone 4G **sans VPS** (PC doit rester allumé) :

```powershell
# Stack pilote sur :8088
docker compose -f docker-compose.yml -f docker-compose.pilot.yml --env-file .env.pilot up -d

# Tunnel Cloudflare
.\scripts\tunnel\start-pilot-public.ps1
```

Copier l'URL `https://....trycloudflare.com` affichée. **Non production.**

---

## 11. Dépannage installation

| Problème | Solution |
|----------|----------|
| Docker ne démarre pas (Windows) | WSL2 + virtualisation — voir `docs/DOCKER_VIRTUALIZATION_FIX.md` |
| Port 8088 occupé | Changer `HTTP_PORT` dans `.env.pilot` |
| Backend unhealthy | `docker compose logs backend` — souvent DB pas prête ou SECRET_KEY manquant |
| Frontend appelle mauvaise API | Rebuild frontend ; vérifier `VITE_SAME_ORIGIN_API=true` |
| `Invalid host header` via tunnel | Ajouter `*.trycloudflare.com` dans `ALLOWED_HOSTS` |
| Migrations échouent | `docker compose exec backend alembic upgrade head` |
| psycopg2 manquant en local | `pip install psycopg2-binary` |

Plus de détails : [`INCIDENTS_ET_DEPANNAGE.md`](./INCIDENTS_ET_DEPANNAGE.md)

---

## 12. Checklist installation réussie

- [ ] `curl http://127.0.0.1:8088/api/health` → `{"status":"ok",...}`
- [ ] Page login accessible http://127.0.0.1:8088/login
- [ ] Connexion patient démo OK
- [ ] Connexion médecin démo OK
- [ ] `python -m pytest tests/ -q` → tous passent
- [ ] `python scripts/pilot_go_live_verify.py` → GO PILOTE = OUI
- [ ] PostgreSQL accessible sur port 5433
- [ ] `alembic current` → head migration

**Installation terminée → passer à [`CHECKLIST_REPRISE.md`](./CHECKLIST_REPRISE.md)**
