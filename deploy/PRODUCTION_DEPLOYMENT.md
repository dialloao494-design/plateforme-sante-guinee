# Phase 4 — Production deployment guide

Prerequisites: staging validation signed off (`deploy/STAGING_VALIDATION.md`).

## 1. Prepare production secrets

On the VPS:

```bash
cd /opt/plateforme-sante
cp .env.production.example .env.production
cp deploy/env/.env.backend.example deploy/env/.env.backend
```

Edit `.env.production`:

- `DOMAIN=` your public domain
- `POSTGRES_PASSWORD=` strong random
- `VITE_API_URL=https://YOUR_DOMAIN/api`
- `ALLOWED_HOSTS=YOUR_DOMAIN,backend`
- `ENABLE_PILOT_SEED=false` (after first bootstrap)
- Stripe **live** keys only when ready

Edit `deploy/env/.env.backend`:

- `ENVIRONMENT=production`
- `SECRET_KEY=` 32+ char random
- `CORS_ORIGINS=https://YOUR_DOMAIN`
- `JITSI_APP_ID` + `JITSI_APP_SECRET` for secured video
- `SENTRY_DSN=` optional

## 2. DNS & firewall

- A record `@` and `www` → VPS IP
- UFW: `allow 80,443/tcp`; deny other public ports

## 3. SSL

```bash
sudo bash deploy/vps/init-ssl.sh
```

## 4. Deploy

```bash
sudo bash deploy/vps/deploy-production.sh
```

## 5. Post-deploy hardening

```bash
# Disable demo seed
sed -i 's/ENABLE_PILOT_SEED=true/ENABLE_PILOT_SEED=false/' .env.production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend

# Daily backup cron
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/plateforme-sante/deploy/vps/backup-db.sh") | crontab -
```

## 6. Smoke test

```bash
curl -fsS https://YOUR_DOMAIN/api/health
curl -fsS https://YOUR_DOMAIN/api/health/ready
```

## 7. Clean staging/demo data (if promoted from staging DB)

Do **not** copy staging `pgdata` to production. Production starts fresh or from a sanitized backup.

## Rollback

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
gunzip -c backups/sante_YYYYMMDD.sql.gz | docker compose exec -T db psql -U sante sante
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## READY FOR PUBLIC DEPLOYMENT

Confirm:

- [ ] Staging checklist 100% passed
- [ ] `ENABLE_PILOT_SEED=false`
- [ ] No test Stripe keys in production `.env`
- [ ] `SECRET_KEY` unique per environment
- [ ] Monitoring: Sentry or log aggregation configured
