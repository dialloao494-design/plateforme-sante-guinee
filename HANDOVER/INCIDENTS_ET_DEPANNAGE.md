# Incidents et dépannage

Guide des problèmes fréquents rencontrés en développement et déploiement, avec diagnostics et solutions.

---

## 1. Docker et infrastructure

### 1.1 Docker Desktop ne démarre pas (Windows)

**Symptôme :** `error during connect` ou `Docker Desktop starting...` infini.

**Cause :** WSL2 ou virtualisation désactivée.

**Solution :**

1. Activer virtualisation dans le BIOS
2. PowerShell **administrateur** :
   ```powershell
   wsl --install
   wsl --set-default-version 2
   ```
3. Redémarrer, ouvrir Docker Desktop
4. Guide complet : [`../docs/DOCKER_VIRTUALIZATION_FIX.md`](../docs/DOCKER_VIRTUALIZATION_FIX.md)

---

### 1.2 Backend unhealthy / ne démarre pas

**Symptôme :** `plateforme-sante-backend-1` en état `unhealthy` ou restart loop.

**Diagnostic :**

```bash
docker compose -f docker-compose.yml -f docker-compose.pilot.yml logs backend --tail 50
```

**Causes fréquentes :**

| Message log | Cause | Solution |
|-------------|-------|----------|
| `Production boot guard rejected` | SECRET_KEY faible ou manquant en staging/prod | Générer SECRET_KEY 32+ car. dans `deploy/env/.env.backend` |
| `DB not ready` | PostgreSQL pas encore up | Attendre ; vérifier `docker compose ps db` |
| `ALLOWED_HOSTS or DOMAIN must be set` | Config staging incomplète | Définir `ALLOWED_HOSTS` et `DOMAIN` |
| `alembic` migration error | Schéma DB incohérent | `docker compose exec backend alembic upgrade head` |
| Port 8000 conflict | Autre uvicorn local | Arrêter processus local sur 8000 |

---

### 1.3 Port déjà utilisé (8088, 5433, 8000)

**Symptôme :** `Bind for 0.0.0.0:8088 failed: port is already allocated`

**Solution :**

```powershell
# Windows — trouver processus
netstat -ano | findstr :8088
taskkill /PID <pid> /F

# Ou changer le port dans .env.pilot
HTTP_PORT=8090
```

---

## 2. API et réseau

### 2.1 `Invalid host header` (400)

**Symptôme :** API retourne `400 Invalid host header` via tunnel Cloudflare ou domaine public.

**Cause :** `TrustedHostMiddleware` — le header `Host` n'est pas dans `ALLOWED_HOSTS`.

**Solution :**

Dans `docker-compose.pilot.yml` ou `deploy/env/.env.backend` :

```
ALLOWED_HOSTS=localhost,127.0.0.1,backend,*.trycloudflare.com,votre.domaine.gn
```

Redémarrer backend :

```bash
docker compose ... up -d backend
```

---

### 2.2 CORS bloqué depuis mobile / LAN

**Symptôme :** Erreur CORS dans la console navigateur.

**Cause :** Origin non autorisée.

**Solutions :**

| Contexte | Fix |
|----------|-----|
| Dev LAN | `ENABLE_LAN_DEV=true` dans `.env` |
| Tunnel Cloudflare | `ENABLE_TUNNEL_TEST=true` + `*.trycloudflare.com` dans ALLOWED_HOSTS |
| VPS production | `CORS_ORIGINS=https://votre.domaine.gn` dans `.env.backend` |
| Docker same-origin | `VITE_SAME_ORIGIN_API=true` + `VITE_API_URL=/api` (rebuild frontend) |

---

### 2.3 Frontend appelle `localhost:8000` au lieu de `/api`

**Symptôme :** Requêtes API échouent en production Docker.

**Cause :** Build frontend sans variables Vite correctes.

**Solution :**

```env
# .env.pilot ou .env.staging
VITE_API_URL=/api
VITE_SAME_ORIGIN_API=true
```

```bash
docker compose ... up -d --build frontend
```

Vérifier dans `frontend-sante/frontend/src/services/httpClient.js` la logique same-origin.

---

### 2.4 `/doctors/` retourne du HTML au lieu de JSON

**Symptôme :** API renvoie la page SPA.

**Cause :** URL sans préfixe `/api` ou trailing slash nginx.

**Solution :** Utiliser `https://domaine/api/doctors/` (avec `/api` prefix).

---

## 3. Authentification

### 3.1 Connexion échoue (401) avec comptes démo

**Symptôme :** `test.patient@example.com` / `Patient123!` ne fonctionne pas.

**Cause :** Seed désactivé ou base reset sans re-seed.

**Solution :**

```bash
# Activer seed
# deploy/env/.env.backend → ENABLE_PILOT_SEED=true

docker compose ... restart backend

# Ou provision manuelle
docker compose exec backend python scripts/pilot_provision_demo.py
```

Comptes canoniques : voir [`../FINAL_AUTH_STABILIZATION.md`](../FINAL_AUTH_STABILIZATION.md)

---

### 3.2 `/patients/me` retourne 500

**Symptôme :** HTTP 500 après login patient.

**Cause :** Champs null dans profil patient (corrigé juin 2026).

**Solution :** S'assurer d'avoir la dernière version de `routers/patient.py` et `services/user_provisioning.py`. Le endpoint répare les champs null au GET.

---

### 3.3 Token expiré / déconnexion fréquente

**Cause :** `ACCESS_TOKEN_EXPIRE_MINUTES=60` par défaut.

**Solution :** Augmenter dans `deploy/env/.env.backend` (staging) ou implémenter refresh tokens (roadmap).

---

## 4. Rendez-vous et disponibilités

### 4.1 Prise de RDV — HTTP 500 (timezone)

**Symptôme :** `TypeError: can't compare offset-naive and offset-aware datetimes`

**Cause :** Client envoie datetime ISO avec timezone, backend compare avec naive.

**Solution :** Corrigé dans `services/rendezvous_service.py` (`_cmp_dt`). Mettre à jour le code.

---

### 4.2 `Ce créneau est déjà réservé` (409)

**Symptôme :** Impossible de booker.

**Cause :** Créneau déjà pris ou chevauchement.

**Solution :** Choisir autre date/heure ou médecin. Vérifier table `rendezvous` :

```sql
SELECT id, doctor_id, date, status FROM rendezvous WHERE doctor_id = 1;
```

---

### 4.3 Aucun créneau disponible

**Symptôme :** Liste médecins OK mais pas de slots.

**Solution :**

```bash
docker compose exec backend python scripts/pilot_provision_demo.py
```

Vérifier `BYPASS_AVAILABILITY_VALIDATION=false` (normal).

---

## 5. Paiements Stripe

### 5.1 Clé Stripe expirée / invalide

**Symptôme :** Erreur checkout, logs `Invalid API Key`.

**Cause :** Clé test expirée (signalé en pilote juin 2026).

**Solution :**

1. Dashboard Stripe → Developers → API keys
2. Regénérer `sk_test_` et `pk_test_`
3. Mettre à jour `deploy/env/.env.backend` et `.env.pilot`
4. Rebuild frontend pour `VITE_STRIPE_PUBLISHABLE_KEY`

**Contournement pilote :** `ALLOW_STUB_PAYMENT=true` + paiement stub.

---

### 5.2 Webhook Stripe non reçu

**Symptôme :** RDV reste `payment_status=unpaid` après paiement.

**Solution :**

1. Configurer webhook Stripe : `https://domaine/api/payments/webhook`
2. Copier `whsec_...` dans `STRIPE_WEBHOOK_SECRET`
3. En local : `stripe listen --forward-to localhost:8088/api/payments/webhook`

---

## 6. Téléconsultation Jitsi

### 6.1 Iframe vide / `membersOnly`

**Symptôme :** Salle Jitsi ne charge pas, erreur membersOnly.

**Cause :** Utilisation de `meet.jit.si` public en iframe (interdit).

**Solution :** Instance Jitsi dédiée :

```powershell
.\scripts\start_jitsi_dev.ps1
```

Configurer `JITSI_DOMAIN=127.0.0.1:8443` (local) ou domaine Jitsi production.

Doc : [`../deploy/jitsi/README.md`](../deploy/jitsi/README.md)

---

### 6.2 Accès téléconsult refusé (403)

**Symptôme :** `GET /teleconsultation/appointments/{id}/access` → 403.

**Cause :** Fenêtre horaire (trop tôt/tard) ou RDV non confirmé/payé.

**Solution :** Vérifier statut RDV, type `teleconsultation`, règles dans `services/teleconsultation_access.py`.

---

## 7. Dossier patient

### 7.1 Patient ne voit pas ses notes

**Symptôme :** GET notes → 403 ou liste vide.

**Cause :** RBAC — patient ne voit que ses propres données ; médecin doit avoir lien RDV.

**Solution :** Créer un RDV entre patient et médecin avant test dossier.

---

### 7.2 Upload document échoue

**Symptôme :** HTTP 413 ou 500 sur POST document.

**Cause :** Fichier trop gros (> 25 Mo nginx) ou type non autorisé.

**Solution :** Vérifier `client_max_body_size` nginx et validation MIME dans `patient_record_service.py`.

---

### 7.3 Audit logs vides

**Diagnostic :**

```sql
SELECT action, resource_type, COUNT(*) FROM clinical_audit_logs GROUP BY 1, 2;
```

**Cause :** Aucune action clinique effectuée ou migration dossier non appliquée.

**Solution :**

```bash
docker compose exec backend alembic upgrade head
# Puis créer une note en tant que médecin
```

---

## 8. HTTPS et VPS

### 8.1 Certbot échoue (ACME challenge)

**Symptôme :** `Certbot failed to authenticate`

**Causes :**

| Cause | Vérification |
|-------|--------------|
| DNS pas propagé | `dig +short domaine.gn` |
| Port 80 fermé | `curl http://domaine/.well-known/acme-challenge/test` |
| Nginx pas démarré | `docker compose ps nginx` |
| mauvais DOMAIN | Cohérence `.env.staging` et certbot `-d` |

**Solution :** Utiliser bootstrap qui démarre nginx HTTP-only avant certbot (`app.conf.init.template`).

---

### 8.2 HTTPS OK mais API 502

**Symptôme :** Nginx répond, backend down.

```bash
docker compose logs backend
docker compose ps
curl http://127.0.0.1:8000/health  # depuis conteneur nginx network
docker compose exec backend curl -fsS http://localhost:8000/health
```

---

### 8.3 Plateforme down après reboot VPS

**Vérifications :**

```bash
sudo systemctl status plateforme-sante
sudo systemctl status docker
docker compose ps
```

**Solution :**

```bash
sudo systemctl enable plateforme-sante docker
sudo systemctl start plateforme-sante
```

---

## 9. Tunnel Cloudflare (dev temporaire)

### 9.1 URL trycloudflare inaccessible

**Cause :** PC éteint, Docker arrêté, ou tunnel fermé.

**Solution :** Relancer stack + tunnel :

```powershell
docker compose -f docker-compose.yml -f docker-compose.pilot.yml --env-file .env.pilot up -d
.\scripts\tunnel\start-pilot-public.ps1
```

**Rappel :** non production, URL change à chaque relance.

---

## 10. Tests et CI

### 10.1 pytest échoue localement

```bash
# Sans DB externe — tests utilisent SQLite in-memory ou mocks
python -m pytest tests/ -v --tb=short

# Test spécifique
python -m pytest tests/test_patient_record_security.py -v
```

---

### 10.2 `pilot_go_live_verify.py` échoue

**Diagnostic :** Lire les lignes `[FAIL]` en fin de sortie.

| Check FAIL | Action |
|------------|--------|
| PostgreSQL | Vérifier conteneur db, port 5433 |
| Tables dossier | `alembic upgrade head` |
| Stripe | Renouveler clé ou ignorer si stub OK |
| Créneaux médecins | `pilot_provision_demo.py` |

---

## 11. Commandes diagnostic rapide

```bash
# Stack status
docker compose -f docker-compose.yml -f docker-compose.pilot.yml ps

# Health
curl -s http://127.0.0.1:8088/api/health | python -m json.tool

# DB connect
docker compose exec db pg_isready -U sante

# Alembic
docker compose exec backend alembic current

# Logs live
docker compose logs -f backend nginx

# Espace disque
df -h
docker system df
```

---

## 12. Escalade — quand demander de l'aide

| Situation | Niveau |
|-----------|--------|
| Bug UI mineur | Corriger directement, PR |
| Faille sécurité | Stop deploy, issue prioritaire |
| Perte données prod | Restaurer backup, post-mortem |
| Certificat LE expiré | Renouveler certbot, vérifier cron |
| Fuite secret (commit) | Rotation immédiate clés + git history |

**Contacts :** propriétaire GitHub `dialloao494-design` + repreneur désigné.

---

## 13. Index documentation incident

| Sujet | Document |
|-------|----------|
| Docker Windows | `docs/DOCKER_VIRTUALIZATION_FIX.md` |
| Téléconsultation | `docs/TELECONSULT_REAL_CALL_PROCEDURE.md` |
| Paiements | `docs/PAYMENT_PRODUCTION_CERTIFICATION.md` |
| Pièces jointes | `docs/ATTACHMENT_SECURITY_AUDIT_FINAL.md` |
| Auth JWT | `JWT_STORAGE_AUDIT.md` |
| Staging mobile | `deploy/STAGING_VALIDATION.md` |
