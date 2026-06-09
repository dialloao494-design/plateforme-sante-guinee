# Déploiement — Plateforme Santé Guinée

**Public :** DevOps, administrateurs système  
**Cible :** VPS Ubuntu 22.04+ (staging ou production)  
**Prérequis :** Docker 24+, Docker Compose v2, nom de domaine (staging/prod), accès root/sudo

---

## 1. Vue d'ensemble des profils

| Profil | Fichiers Compose | Env file | HTTPS |
|--------|------------------|----------|-------|
| **Pilote local** | `docker-compose.yml` + `docker-compose.pilot.yml` | `.env.pilot` | Self-signed (9443) |
| **Staging VPS** | `docker-compose.yml` + `docker-compose.staging.yml` | `.env.staging` | Let's Encrypt |
| **Production VPS** | `docker-compose.yml` + `docker-compose.prod.yml` | `.env.production` | Let's Encrypt |

---

## 2. Prérequis serveur

### 2.1 Spécifications minimales

| Ressource | Staging | Production |
|-----------|---------|------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 Go | 8 Go |
| Disque | 40 Go SSD | 80 Go SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### 2.2 Ports ouverts (pare-feu)

| Port | Service |
|------|---------|
| 80 | HTTP (redirect + ACME challenge) |
| 443 | HTTPS |
| 22 | SSH (restreindre par IP si possible) |

Ne **pas** exposer PostgreSQL (5432) en production publique.

### 2.3 Installation Docker (VPS)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Reconnecter la session SSH
docker compose version
```

Script fourni : `deploy/vps/install-docker.sh`

---

## 3. Préparation du dépôt

```bash
git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git
cd plateforme-sante-guinee

# Secrets backend (JAMAIS commités)
cp deploy/env/.env.backend.example deploy/env/.env.backend

# Environnement compose racine
cp .env.staging.example .env.staging      # staging
# ou
cp .env.production.example .env.production  # production
```

---

## 4. Variables d'environnement

### 4.1 Fichier racine (`.env.staging` / `.env.production`)

| Variable | Exemple | Description |
|----------|---------|-------------|
| `DOMAIN` | `staging.sante.gn` | Nom de domaine public |
| `HTTP_PORT` | `80` | Port HTTP nginx |
| `POSTGRES_USER` | `sante` | Utilisateur PostgreSQL |
| `POSTGRES_PASSWORD` | `<fort>` | Mot de passe PostgreSQL (12+ car.) |
| `POSTGRES_DB` | `sante` | Nom de la base |
| `ENVIRONMENT` | `staging` ou `production` | Mode applicatif |
| `ENABLE_PILOT_SEED` | `false` | **Toujours false en prod** |
| `BYPASS_AVAILABILITY_VALIDATION` | `false` | **Toujours false en prod** |
| `VITE_API_URL` | `https://staging.sante.gn/api` | URL API pour build frontend |
| `VITE_TELECONSULT_PROVIDER` | `jitsi` | Provider téléconsultation |
| `VITE_STRIPE_PUBLISHABLE_KEY` | `pk_test_...` ou `pk_live_...` | Clé publique Stripe |
| `CERTBOT_EMAIL` | `admin@sante.gn` | Email Let's Encrypt |

### 4.2 Fichier backend (`deploy/env/.env.backend`)

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `SECRET_KEY` | ✅ | JWT secret (32+ car., aléatoire) |
| `ENVIRONMENT` | ✅ | `staging` ou `production` |
| `ALLOWED_HOSTS` | ✅ | `domaine,backend` |
| `STRIPE_SECRET_KEY` | ✅ staging/prod | `sk_test_...` ou `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | ✅ | `whsec_...` |
| `JITSI_APP_SECRET` | ✅ si Jitsi | Secret JWT Jitsi (16+ car.) |
| `JITSI_APP_ID` | ✅ si Jitsi | Identifiant application Jitsi |
| `JITSI_DOMAIN` | ✅ si Jitsi | Domaine instance Jitsi |
| `ENABLE_PILOT_SEED` | — | `false` en prod |
| `BYPASS_AVAILABILITY_VALIDATION` | — | `false` en prod |
| `ALLOW_STUB_PAYMENT` | — | `true` staging uniquement |
| `PAYMENT_STUB_TOKEN` | — | Token stub si ALLOW_STUB_PAYMENT |
| `CORS_ORIGINS` | ✅ | URL frontend(s) autorisées |
| `FRONTEND_URL` | ✅ | URL publique frontend |

Génération secret :

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4.3 Pilote local (`.env.pilot`)

```env
DOMAIN=localhost
HTTP_PORT=8088
HTTPS_PORT=9443
POSTGRES_USER=sante
POSTGRES_PASSWORD=<mot-de-passe-fort>
ENVIRONMENT=staging
ENABLE_PILOT_SEED=false
BYPASS_AVAILABILITY_VALIDATION=false
VITE_API_URL=http://localhost:8088/api
```

---

## 5. Docker Compose — déploiement

### 5.1 Pilote local (développement / QA)

```bash
# Certificats self-signed (première fois)
mkdir -p deploy/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deploy/certs/pilot-privkey.pem \
  -out deploy/certs/pilot-fullchain.pem \
  -subj "/CN=localhost"

# Lancer la stack
docker compose -f docker-compose.yml -f docker-compose.pilot.yml \
  --env-file .env.pilot up -d --build

# Vérifier
curl http://localhost:8088/api/health
curl -k https://127.0.0.1:9443/api/health
```

URLs pilote :

| Service | URL |
|---------|-----|
| Frontend | http://localhost:8088 |
| API | http://localhost:8088/api |
| HTTPS | https://127.0.0.1:9443 |
| PostgreSQL | localhost:5433 |

### 5.2 Staging VPS

```bash
# 1. Configurer .env.staging et deploy/env/.env.backend
nano .env.staging
nano deploy/env/.env.backend

# 2. Générer nginx config depuis template
export DOMAIN=staging.votre-domaine.gn
envsubst '${DOMAIN}' < deploy/nginx/conf.d/app.conf.template \
  > deploy/nginx/conf.d/app.conf

# 3. Premier certificat SSL
chmod +x deploy/vps/init-ssl-staging.sh
./deploy/vps/init-ssl-staging.sh

# 4. Déployer
chmod +x deploy/vps/deploy-staging.sh
./deploy/vps/deploy-staging.sh
```

Ou manuellement :

```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml \
  --env-file .env.staging up -d --build
```

### 5.3 Production VPS

```bash
chmod +x deploy/vps/deploy-production.sh
./deploy/vps/deploy-production.sh
```

Compose :

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production up -d --build
```

### 5.4 Cycle de vie des conteneurs

```bash
# Statut
docker compose -f docker-compose.yml -f docker-compose.pilot.yml ps

# Logs backend
docker compose logs backend --tail 100 -f

# Redémarrage backend (zero-downtime partiel)
docker compose restart backend

# Rebuild après changement code
docker compose -f docker-compose.yml -f docker-compose.pilot.yml \
  --env-file .env.pilot up -d --build backend frontend

# Arrêt complet
docker compose -f docker-compose.yml -f docker-compose.pilot.yml down
```

---

## 6. Migrations Alembic

### 6.1 Chaîne de révisions

```
0001_baseline → 0002_doctor_geolocation → 20260525_0003_patient_dossier (HEAD)
```

| Révision | Contenu |
|----------|---------|
| `0001_baseline` | Stamp initial (schéma via modèles SQLAlchemy) |
| `0002_doctor_geolocation` | Colonnes `latitude`, `longitude` sur `doctors` |
| `20260525_0003_patient_dossier` | Tables dossier patient + audit |

### 6.2 Application automatique

Le script `scripts/docker/entrypoint-backend.sh` exécute au démarrage :

1. Attente PostgreSQL ready
2. `Base.metadata.create_all()`
3. `alembic upgrade head`
4. `ensure_patient_dossier_schema()` (fallback)

### 6.3 Application manuelle

```bash
# Dans le conteneur backend
docker compose exec backend alembic upgrade head

# Vérifier version
docker compose exec db psql -U sante -d sante \
  -c "SELECT version_num FROM alembic_version;"
```

Résultat attendu :

```
20260525_0003_patient_dossier
```

### 6.4 Vérifier les tables dossier

```bash
docker compose exec db psql -U sante -d sante -c "\dt"
```

Tables attendues : `clinical_notes`, `consultation_summaries`, `patient_documents`, `clinical_audit_logs`.

---

## 7. HTTPS

### 7.1 Staging / Production (Let's Encrypt)

1. Pointer le DNS `A` du domaine vers l'IP du VPS.
2. Exécuter `deploy/vps/init-ssl-staging.sh` ou `init-ssl.sh`.
3. Certbot obtient les certificats via challenge HTTP-01.
4. Renouvellement automatique via conteneur `certbot` (toutes les 12 h).

Vérification :

```bash
curl -I https://staging.votre-domaine.gn/api/health
# Attendu : HTTP/2 200, certificat valide
```

Checklist : `deploy/STAGING_VALIDATION.md`

### 7.2 Pilote local (self-signed)

Certificats dans `deploy/certs/` :

- `pilot-fullchain.pem`
- `pilot-privkey.pem`

Config nginx : `deploy/nginx/conf.d/app.pilot-https.conf` (ports 80 + 443).

Navigateur : accepter l'avertissement certificat ou importer le certificat en trusted.

### 7.3 Headers sécurité (production)

Configurés dans `app.conf.template` :

- HSTS (`Strict-Transport-Security`)
- `X-Frame-Options`, `X-Content-Type-Options`
- Permissions-Policy (caméra/micro pour téléconsultation)

---

## 8. Provisioning post-déploiement

### 8.1 Comptes démo et créneaux médecins

```bash
docker compose exec backend python scripts/pilot_provision_demo.py
```

Ce script :

- crée/synchronise 4 médecins pilote + 1 patient test ;
- ajoute 5 créneaux Lun–Ven 09:00–12:00 par médecin.

Comptes :

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Patient | `test.patient@example.com` | `Patient123!` |
| Médecin | `dr.mamady@example.com` | `Doctor123!` |

> En production réelle : créer des comptes nominatifs, ne pas utiliser `@example.com`.

### 8.2 Vérification GO PILOTE

```bash
python scripts/pilot_go_live_verify.py
# ou avec psycopg2 installé localement
PILOT_API_BASE=http://localhost:8088/api python scripts/pilot_go_live_verify.py
```

---

## 9. Stripe (configuration)

### 9.1 Clés

1. Dashboard Stripe → Developers → API keys
2. Staging : mode **Test** (`sk_test_`, `pk_test_`)
3. Production : mode **Live** (`sk_live_`, `pk_live_`)

### 9.2 Webhook

1. Stripe Dashboard → Webhooks → Add endpoint
2. URL : `https://votre-domaine.gn/api/payments/webhook`
3. Événements : `checkout.session.completed`, `payment_intent.succeeded`, `charge.refunded`
4. Copier `whsec_...` → `STRIPE_WEBHOOK_SECRET`

### 9.3 Test

```bash
# Stripe CLI (local)
stripe listen --forward-to localhost:8088/api/payments/webhook
stripe trigger checkout.session.completed
```

---

## 10. Jitsi (téléconsultation)

### 10.1 Instance dédiée

Documentation : `deploy/jitsi/README.md`

```bash
# Dev local Windows
.\scripts\start_jitsi_dev.ps1
```

Variables backend :

```env
JITSI_DOMAIN=votre-jitsi.domaine.gn
JITSI_APP_ID=pilot-sante-guinee
JITSI_APP_SECRET=<secret-32-chars>
```

Frontend build :

```env
VITE_JITSI_DOMAIN=votre-jitsi.domaine.gn
VITE_TELECONSULT_PROVIDER=jitsi
```

**Important :** `JITSI_DOMAIN` backend = `VITE_JITSI_DOMAIN` frontend.

### 10.2 HTTPS obligatoire

Caméra/micro navigateur requiert HTTPS (staging Let's Encrypt ou pilote self-signed).

---

## 11. Sauvegardes PostgreSQL

### 11.1 Backup manuel

```bash
chmod +x deploy/vps/backup-db.sh
./deploy/vps/backup-db.sh
# Sortie : backups/sante_YYYYMMDD_HHMMSS.sql.gz
```

Ou :

```bash
docker compose exec -T db pg_dump -U sante sante | gzip > backup_$(date +%F).sql.gz
```

### 11.2 Backup automatisé (cron)

```cron
0 3 * * * /opt/plateforme-sante/deploy/vps/backup-db.sh >> /var/log/sante-backup.log 2>&1
```

Rétention : 14 jours (script intégré).

### 11.3 Vérification backup

```bash
chmod +x scripts/db/backup_verify.sh
./scripts/db/backup_verify.sh
```

Teste `gzip -t` sur le dernier fichier.

### 11.4 Restauration

```bash
gunzip -c backups/sante_20260608_030000.sql.gz | \
  docker compose exec -T db psql -U sante -d sante
```

Procédure complète : `scripts/db/restore_drill.sh`

---

## 12. Monitoring et santé

| Endpoint | Usage |
|----------|-------|
| `GET /api/health` | Liveness (API up) |
| `GET /api/health/ready` | Readiness (DB connectée) |
| `GET /api/ws/health` | WebSocket (retourne `pong`) |

Script validation staging : `deploy/vps/validate-staging.sh`

---

## 13. Sécurité des secrets

**Ne jamais committer :**

- `.env`, `.env.production`, `.env.staging`, `.env.pilot`
- `deploy/env/.env.backend`
- `certbot/conf/`, `deploy/certs/*.pem` (prod)
- Clés Stripe, Jitsi, JWT

**Vérification avant push :**

```powershell
.\scripts\git\pre_push_check.ps1
```

---

## 14. Dépannage rapide

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| 502 Bad Gateway | Backend pas ready | `docker compose logs backend` |
| Login 429 | Rate limit | Attendre 1 min ou augmenter `RATE_LIMIT_LOGIN` |
| RDV refusé « pas de disponibilité » | 0 créneaux médecin | `pilot_provision_demo.py` |
| Routes dossier 404 | Backend stale | `docker compose up -d --build backend` |
| Stripe webhook 400 | Secret incorrect | Vérifier `STRIPE_WEBHOOK_SECRET` |
| Jitsi caméra bloquée | HTTP au lieu HTTPS | Activer TLS |
| `localhost:8000` → Jitsi (Windows) | Conflit port IPv6 | Utiliser `127.0.0.1:8088/api` |

---

## 15. Checklist déploiement production

- [ ] DNS `A` record pointé vers VPS
- [ ] `.env.production` + `deploy/env/.env.backend` configurés
- [ ] `ENABLE_PILOT_SEED=false`, `BYPASS_AVAILABILITY_VALIDATION=false`
- [ ] `SECRET_KEY` fort (32+ car.)
- [ ] PostgreSQL mot de passe fort
- [ ] HTTPS Let's Encrypt actif
- [ ] Migrations Alembic HEAD appliquées
- [ ] Stripe live keys + webhook configuré
- [ ] Jitsi JWT configuré
- [ ] Backup cron installé
- [ ] `validate-staging.sh` vert
- [ ] Parcours E2E manuel (RDV → paiement → téléconsult → dossier)
