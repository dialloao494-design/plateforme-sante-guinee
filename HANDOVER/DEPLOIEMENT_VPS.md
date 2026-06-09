# Déploiement VPS — Production autonome

Guide pour héberger la plateforme sur un **VPS Ubuntu 22.04** indépendant du PC du développeur initial : HTTPS Let's Encrypt, PostgreSQL, sauvegardes, redémarrage automatique.

---

## 1. Objectif

| Critère | Cible |
|---------|-------|
| Disponibilité | 24/7 sans PC développeur |
| HTTPS | Let's Encrypt valide |
| Domaine | Permanent (ex. `sante.votredomaine.gn`) |
| Base | PostgreSQL 16 sur VPS (volume Docker) |
| Boot | Docker redémarre automatiquement |
| Sauvegardes | Quotidiennes, rétention 14 jours |
| Tunnel Cloudflare | **Non requis** |

---

## 2. Prérequis

### 2.1 Serveur

| Ressource | Staging | Production |
|-----------|---------|------------|
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 Go | 8 Go |
| Disque | 40 Go SSD | 80 Go SSD |
| Fournisseurs | Hetzner, OVH, Contabo, DigitalOcean | idem |

### 2.2 Domaine et DNS

Créer un enregistrement **A** :

```
sante.votredomaine.gn  →  IP_PUBLIQUE_DU_VPS
```

Attendre la propagation DNS (5 min à 48 h). Vérifier :

```bash
dig +short sante.votredomaine.gn
# doit retourner l'IP du VPS
```

### 2.3 Pare-feu

| Port | Usage |
|------|-------|
| 22 | SSH (restreindre par IP si possible) |
| 80 | HTTP (redirect + challenge ACME) |
| 443 | HTTPS |

**Ne pas exposer** le port PostgreSQL 5432 sur Internet.

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 3. Méthode A — Bootstrap automatique (recommandée)

Script one-shot : installe Docker, génère secrets, obtient certificat LE, démarre la stack, configure systemd + cron backup.

### 3.1 Depuis Windows (déploiement distant)

```powershell
cd plateforme-sante-guinee

.\scripts\vps\remote-deploy.ps1 `
  -VpsHost "203.0.113.10" `
  -Domain "sante.votredomaine.gn" `
  -CertbotEmail "admin@votredomaine.gn" `
  -VpsUser "root"
```

Le script :
1. Compresse le dépôt (sans `.git`, `node_modules`, secrets locaux)
2. Envoie l'archive sur le VPS via SCP
3. Exécute `deploy/vps/bootstrap-autonomous.sh`

### 3.2 Directement sur le VPS

```bash
git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git /opt/plateforme-sante-guinee
cd /opt/plateforme-sante-guinee

export DOMAIN=sante.votredomaine.gn
export CERTBOT_EMAIL=admin@votredomaine.gn

# Optionnel : injecter clés Stripe réelles
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_PUBLISHABLE_KEY=pk_test_...

bash deploy/vps/bootstrap-autonomous.sh
```

### 3.3 Ce que fait le bootstrap (8 étapes)

| Étape | Action |
|-------|--------|
| 1 | Installe Docker si absent (`deploy/vps/install-docker.sh`) |
| 2 | Génère `.env.staging` + `deploy/env/.env.backend` |
| 3 | Configure nginx HTTP + ACME (`app.conf.init.template`) |
| 4 | Démarre db, backend, frontend, nginx |
| 5 | Obtient certificat Let's Encrypt (certbot webroot) |
| 6 | Bascule nginx vers HTTPS (`app.conf.template`) |
| 7 | Attend `/api/health` OK |
| 8 | Installe systemd + cron backup + seed démo |

---

## 4. Méthode B — Déploiement manuel (staging puis production)

### 4.1 Installation Docker

```bash
sudo bash deploy/vps/install-docker.sh
sudo usermod -aG docker $USER
# Reconnecter SSH
```

### 4.2 Configuration secrets

```bash
cd /opt/plateforme-sante-guinee

cp .env.staging.example .env.staging
cp deploy/env/.env.backend.example deploy/env/.env.backend
```

Éditer `.env.staging` :

```env
DOMAIN=staging.votredomaine.gn
POSTGRES_PASSWORD=<mot_de_passe_fort_32_car>
ENABLE_PILOT_SEED=true
VITE_API_URL=/api
VITE_SAME_ORIGIN_API=true
CERTBOT_EMAIL=admin@votredomaine.gn
```

Éditer `deploy/env/.env.backend` :

```env
ENVIRONMENT=staging
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
ALLOWED_HOSTS=staging.votredomaine.gn,backend
DOMAIN=staging.votredomaine.gn
FRONTEND_URL=https://staging.votredomaine.gn
CORS_ORIGINS=https://staging.votredomaine.gn
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
JITSI_APP_SECRET=<32+ caractères>
JITSI_DOMAIN=meet.votredomaine.gn
ENABLE_PILOT_SEED=true
ALLOW_STUB_PAYMENT=true
```

### 4.3 Premier certificat SSL

```bash
export DOMAIN=staging.votredomaine.gn
bash deploy/vps/init-ssl-staging.sh
```

Ou production :

```bash
export DOMAIN=sante.votredomaine.gn
bash deploy/vps/init-ssl.sh
```

### 4.4 Déploiement

Staging :

```bash
bash deploy/vps/deploy-staging.sh
bash deploy/vps/validate-staging.sh
```

Production (après validation staging) :

```bash
# .env.production + ENVIRONMENT=production dans .env.backend
bash deploy/vps/deploy-production.sh
```

---

## 5. HTTPS et renouvellement certificats

### 5.1 Architecture TLS

```
Port 80  → nginx → /.well-known/acme-challenge/ → certbot/www
                 → redirect 301 vers HTTPS

Port 443 → nginx → certificats dans certbot/conf/live/${DOMAIN}/
                 → proxy vers backend / frontend
```

Fichiers nginx :

- Bootstrap ACME : `deploy/nginx/conf.d/app.conf.init.template`
- Production : `deploy/nginx/conf.d/app.conf.template` → `app.conf`

### 5.2 Renouvellement automatique

Le service `certbot` dans Compose relance `certbot renew` toutes les 12 h :

```yaml
# docker-compose.staging.yml / docker-compose.prod.yml
certbot:
  entrypoint: /bin/sh -c "trap exit TERM; while :; do certbot renew; sleep 12h; done"
```

Vérification manuelle :

```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml exec certbot certbot certificates
```

Test renouvellement dry-run :

```bash
docker run --rm \
  -v $(pwd)/certbot/www:/var/www/certbot \
  -v $(pwd)/certbot/conf:/etc/letsencrypt \
  certbot/certbot renew --dry-run
```

---

## 6. Redémarrage automatique au boot VPS

### 6.1 Docker Compose

Tous les services ont `restart: unless-stopped` dans `docker-compose.yml`.

### 6.2 Systemd (installé par bootstrap)

Fichier : `deploy/vps/plateforme-sante.service`

```bash
sudo cp deploy/vps/plateforme-sante.service /etc/systemd/system/
# Adapter WorkingDirectory si différent de /opt/plateforme-sante-guinee
sudo systemctl daemon-reload
sudo systemctl enable plateforme-sante.service
sudo systemctl start plateforme-sante.service
sudo systemctl status plateforme-sante.service
```

Test reboot :

```bash
sudo reboot
# Après reconnexion SSH :
curl -fsS https://sante.votredomaine.gn/api/health
docker compose -f docker-compose.yml -f docker-compose.staging.yml ps
```

---

## 7. Sauvegardes PostgreSQL

### 7.1 Script

`deploy/vps/backup-db.sh` — dump compressé dans `backups/`.

```bash
cd /opt/plateforme-sante-guinee
ENV_FILE=.env.staging COMPOSE_EXTRA='-f docker-compose.staging.yml' bash deploy/vps/backup-db.sh
```

Résultat : `backups/sante_YYYYMMDD_HHMMSS.sql.gz`

Rétention : suppression automatique des fichiers > 14 jours.

### 7.2 Cron (installé par bootstrap)

```
0 3 * * * cd /opt/plateforme-sante-guinee && ENV_FILE=.env.staging COMPOSE_EXTRA='-f docker-compose.staging.yml' bash deploy/vps/backup-db.sh >> /opt/plateforme-sante-guinee/logs/backup.log 2>&1
```

Vérifier :

```bash
crontab -l
ls -la backups/
```

### 7.3 Restauration

```bash
# Arrêt stack
docker compose -f docker-compose.yml -f docker-compose.staging.yml down

# Restauration (ATTENTION : écrase les données)
gunzip -c backups/sante_20260608_030000.sql.gz | \
  docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d db
sleep 5
gunzip -c backups/sante_20260608_030000.sql.gz | \
  docker compose -f docker-compose.yml -f docker-compose.staging.yml exec -T db \
  psql -U sante sante

# Redémarrage
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

Test non destructif : `bash scripts/db/restore_drill.sh backups/sante_XXXX.sql.gz`

### 7.4 Sauvegarde off-site (recommandée)

Copier `backups/` vers un stockage externe (S3, Backblaze, autre VPS) :

```bash
# Exemple rsync vers serveur backup
rsync -avz backups/ backup-user@backup-server:/backups/plateforme-sante/
```

---

## 8. Mise à jour (deploy subsequent)

```bash
cd /opt/plateforme-sante-guinee
git pull origin main

docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging build
docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging up -d

# Migrations si nouvelles
docker compose exec backend alembic upgrade head
```

Fenêtre de maintenance recommandée : sauvegarde avant, test `/api/health` après.

---

## 9. Validation post-déploiement

### 9.1 Automatique

```bash
# Sur le VPS
bash deploy/vps/validate-staging.sh

# Depuis n'importe quelle machine
VPS_API_BASE=https://sante.votredomaine.gn/api \
VPS_DOMAIN=sante.votredomaine.gn \
python scripts/vps_autonomous_verify.py
```

### 9.2 Manuel (checklist)

- [ ] `curl https://DOMAIN/api/health` → 200 OK
- [ ] `curl -I http://DOMAIN` → redirect 301 HTTPS
- [ ] Certificat valide dans le navigateur (cadenas)
- [ ] Inscription patient depuis smartphone 4G
- [ ] Connexion médecin démo
- [ ] Prise de rendez-vous
- [ ] Dossier patient (notes, timeline)
- [ ] Reboot VPS → service revient seul

Checklist complète mobile : [`../deploy/STAGING_VALIDATION.md`](../deploy/STAGING_VALIDATION.md)

---

## 10. Passage staging → production

| Action | Staging | Production |
|--------|---------|------------|
| Fichier env | `.env.staging` | `.env.production` |
| Compose overlay | `docker-compose.staging.yml` | `docker-compose.prod.yml` |
| `ENVIRONMENT` | `staging` | `production` |
| `ENABLE_PILOT_SEED` | `true` (bootstrap) | **`false`** |
| `ALLOW_STUB_PAYMENT` | `true` | **`false`** |
| Stripe | `sk_test_` | `sk_live_` |
| API docs | `/api/docs` si `ENABLE_STAGING_API_DOCS=true` | Désactivées |

```bash
cp .env.production.example .env.production
# Configurer + bash deploy/vps/init-ssl.sh + bash deploy/vps/deploy-production.sh
```

---

## 11. Monitoring minimal

| Vérification | Commande | Fréquence |
|--------------|----------|-----------|
| Health API | `curl -fsS https://DOMAIN/api/health` | 5 min (uptime robot) |
| Ready API | `curl -fsS https://DOMAIN/api/health/ready` | 5 min |
| Espace disque | `df -h` | Quotidien |
| Logs erreurs | `docker compose logs backend --since 1h \| grep -i error` | Quotidien |
| Backup récent | `ls -lt backups/ \| head` | Quotidien |

Optionnel : configurer `SENTRY_DSN` dans `deploy/env/.env.backend`.

---

## 12. Sécurité post-déploiement

- [ ] `ENABLE_PILOT_SEED=false` en production publique
- [ ] Mots de passe Postgres et SECRET_KEY uniques et forts
- [ ] SSH par clé uniquement (désactiver password auth)
- [ ] Fail2ban sur SSH
- [ ] Stripe webhook configuré avec URL `https://DOMAIN/api/payments/webhook`
- [ ] Sauvegardes testées (restauration drill)
- [ ] `.env*` chmod 600

---

## 13. Fichiers clés (référence)

| Fichier | Rôle |
|---------|------|
| `deploy/vps/bootstrap-autonomous.sh` | Installation complète one-shot |
| `scripts/vps/remote-deploy.ps1` | Deploy depuis Windows |
| `deploy/vps/plateforme-sante.service` | Systemd boot |
| `deploy/vps/backup-db.sh` | Sauvegarde PG |
| `deploy/vps/init-ssl.sh` | Premier certificat LE |
| `deploy/vps/validate-staging.sh` | Tests post-deploy |
| `scripts/vps_autonomous_verify.py` | Tests parcours patient HTTPS |

---

## 14. État au moment de la passation

| Élément | Statut |
|---------|--------|
| Scripts VPS | ✅ Prêts |
| Bootstrap autonome | ✅ Testé en conception |
| VPS déployé | ❌ Non (en attente IP + domaine) |
| Tunnel Cloudflare | ⚠️ Solution temporaire dev uniquement |

**Action requise du repreneur :** provisionner VPS + domaine, exécuter `bootstrap-autonomous.sh`, valider avec `vps_autonomous_verify.py`.
