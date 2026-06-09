# Checklist reprise — Plateforme Santé Guinée

Liste de vérifications à effectuer **avant toute modification de code** ou **déploiement production**.  
Cocher chaque item. Ne pas passer à la phase suivante tant que la section courante n'est pas complète.

---

## Phase 0 — Accès et contexte

### Documentation lue

- [ ] [`README_START_HERE.md`](./README_START_HERE.md) — vue d'ensemble
- [ ] [`INSTALLATION_COMPLETE.md`](./INSTALLATION_COMPLETE.md) — installation
- [ ] [`../ARCHITECTURE_GLOBALE.md`](../ARCHITECTURE_GLOBALE.md) — architecture
- [ ] [`../DOSSIER_PATIENT.md`](../DOSSIER_PATIENT.md) — module clinique
- [ ] [`INCIDENTS_ET_DEPANNAGE.md`](./INCIDENTS_ET_DEPANNAGE.md) — problèmes connus
- [ ] [`ROADMAP_90_JOURS.md`](./ROADMAP_90_JOURS.md) — priorités

### Accès obtenus

- [ ] Compte GitHub avec droits **Write** ou **Admin** sur `dialloao494-design/plateforme-sante-guinee`
- [ ] Accès Stripe Dashboard (mode test minimum)
- [ ] Copie des secrets ou procédure pour les regénérer :
  - [ ] `SECRET_KEY` (JWT)
  - [ ] `POSTGRES_PASSWORD`
  - [ ] `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET`
  - [ ] `JITSI_APP_SECRET`
- [ ] (Si VPS) Accès SSH au serveur
- [ ] (Si VPS) Accès DNS du domaine

### Compréhension produit

- [ ] Parcours patient compris (inscription → RDV → paiement → téléconsult)
- [ ] Parcours médecin compris (agenda → dossier → notes → synthèses)
- [ ] Rôles RBAC connus : `patient`, `doctor`, `admin`
- [ ] Différence pilote / staging / production comprise

---

## Phase 1 — Environnement local fonctionnel

### Prérequis machine

- [ ] Git installé
- [ ] Python 3.12 installé
- [ ] Node.js 20 LTS installé
- [ ] Docker Desktop fonctionnel (ou Docker Engine sur Linux)
- [ ] `docker compose version` OK

### Clone et configuration

- [ ] Dépôt cloné localement
- [ ] Branche `main` à jour (`git pull`)
- [ ] `.env.pilot` présent et lu (ne pas committer de modifications secrets)
- [ ] `deploy/env/.env.backend` présent (copié depuis `.example` si absent)

### Stack pilote Docker

- [ ] Commande lancement exécutée sans erreur :
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.pilot.yml --env-file .env.pilot up -d --build
  ```
- [ ] 4 conteneurs UP : `db`, `backend`, `frontend`, `nginx`
- [ ] Backend status : **healthy**
- [ ] DB status : **healthy**

### Vérifications API

- [ ] `curl http://127.0.0.1:8088/api/health` → `{"status":"ok",...}`
- [ ] `curl http://127.0.0.1:8088/api/health/ready` → ready
- [ ] `http://127.0.0.1:8088/api/docs` accessible (si staging docs enabled)

### Vérifications base de données

- [ ] PostgreSQL accessible port `5433`
- [ ] `docker compose exec backend alembic current` → head migration
- [ ] Tables dossier présentes :
  - [ ] `clinical_notes`
  - [ ] `consultation_summaries`
  - [ ] `patient_documents`
  - [ ] `clinical_audit_logs`

### Données démo

- [ ] `python scripts/pilot_provision_demo.py` exécuté (ou seed auto)
- [ ] 4 médecins listés via API
- [ ] Créneaux disponibles (≥ 5 par médecin)

---

## Phase 2 — Tests automatisés

### Suite pytest

- [ ] `python -m pytest tests/ -q` → **tous passent**
- [ ] Tests sécurité inscription : `tests/test_registration_security.py`
- [ ] Tests dossier RBAC : `tests/test_patient_record_security.py`
- [ ] Tests paiement : `tests/test_payment_settlement_security.py`
- [ ] Tests téléconsult : `tests/test_teleconsult_access.py`
- [ ] Boot guards prod : `tests/test_production_boot_guard.py`

### Scripts validation

- [ ] `python scripts/pilot_go_live_verify.py` → **GO PILOTE = OUI**
- [ ] `python scripts/verify_pilot_logins.py` → logins démo OK

---

## Phase 3 — Tests manuels UI

### Parcours patient (navigateur http://127.0.0.1:8088)

- [ ] Page d'accueil / login charge sans erreur console critique
- [ ] Inscription nouveau patient
- [ ] Connexion patient démo (`test.patient@example.com`)
- [ ] Dashboard patient affiche statistiques
- [ ] Liste médecins accessible
- [ ] Prise de rendez-vous (physique ou téléconsult)
- [ ] Liste mes rendez-vous
- [ ] Déconnexion / reconnexion

### Parcours médecin

- [ ] Connexion médecin démo (`dr.mamady@example.com`)
- [ ] Dashboard médecin — KPIs visibles
- [ ] File de rendez-vous
- [ ] Accès dossier patient (`/doctor/patient/:id`)
- [ ] Création note clinique
- [ ] Création synthèse consultation
- [ ] Upload document (PDF test)

### Parcours admin (si compte disponible)

- [ ] Page `/users` accessible
- [ ] Liste utilisateurs affichée

### Mobile (optionnel mais recommandé)

- [ ] Test responsive navigateur (390×844 iPhone)
- [ ] Test LAN Wi-Fi (`npm run dev:lan`) ou tunnel pilote
- [ ] Inscription depuis smartphone

---

## Phase 4 — Compréhension technique avant modification

### Backend — fichiers clés identifiés

- [ ] `main.py` — middleware, routers, boot guards
- [ ] `security.py` — JWT, get_current_user, require_roles
- [ ] `core/settings.py` — ENVIRONMENT, ALLOWED_HOSTS
- [ ] `services/rendezvous_service.py` — logique RDV
- [ ] `services/patient_record_service.py` — dossier + audit
- [ ] `routers/patient_record.py` — endpoints dossier
- [ ] `alembic/versions/` — migrations

### Frontend — fichiers clés identifiés

- [ ] `src/routes/AppRoutes.jsx` — routing
- [ ] `src/context/AuthContext.jsx` — auth state
- [ ] `src/services/httpClient.js` — résolution API
- [ ] `src/pages/ConsultationRoom.jsx` — téléconsult
- [ ] `src/pages/PatientDetails.jsx` — dossier médecin

### Règles de développement

- [ ] Ne jamais committer `.env`, secrets, certificats
- [ ] Lancer `pytest` avant chaque PR
- [ ] Rebuild frontend Docker si variable `VITE_*` modifiée
- [ ] Migration Alembic pour tout changement schéma DB
- [ ] `ENABLE_PILOT_SEED=false` avant production publique
- [ ] `BYPASS_AVAILABILITY_VALIDATION=false` toujours en prod

---

## Phase 5 — Pré-déploiement VPS (avant go-live)

### Infrastructure

- [ ] VPS Ubuntu 22.04 provisionné
- [ ] DNS A record configuré et propagé
- [ ] Ports 22, 80, 443 ouverts
- [ ] Docker installé sur VPS

### Configuration production

- [ ] `.env.staging` ou `.env.production` créé sur VPS (chmod 600)
- [ ] `deploy/env/.env.backend` configuré sur VPS
- [ ] `SECRET_KEY` unique et fort (≠ pilote local)
- [ ] `POSTGRES_PASSWORD` unique et fort
- [ ] `DOMAIN` cohérent partout
- [ ] `VITE_SAME_ORIGIN_API=true` + `VITE_API_URL=/api`

### Déploiement

- [ ] `bootstrap-autonomous.sh` exécuté OU deploy manuel OK
- [ ] HTTPS Let's Encrypt valide (cadenas navigateur)
- [ ] `curl https://DOMAIN/api/health` → 200
- [ ] Systemd `plateforme-sante.service` enabled
- [ ] Cron backup configuré
- [ ] Test restauration backup effectué

### Validation VPS

- [ ] `python scripts/vps_autonomous_verify.py` → **PLATEFORME AUTONOME = OUI**
- [ ] Test inscription depuis 4G (smartphone externe)
- [ ] Test reboot VPS → service revient seul

---

## Phase 6 — Sécurité (avant ouverture publique)

- [ ] `ENABLE_PILOT_SEED=false` en production
- [ ] `ALLOW_STUB_PAYMENT=false` en production
- [ ] `ENVIRONMENT=production` dans `.env.backend`
- [ ] API docs désactivées (`DISABLE_API_DOCS` ou prod guard)
- [ ] Stripe webhook configuré URL production
- [ ] Uploads `/uploads/` retournent 403 (test curl)
- [ ] Pas de secret dans l'historique Git récent (`git log -p` spot check)
- [ ] SSH VPS : clé uniquement, pas de root password

---

## Phase 7 — Prêt à développer

Validation finale — **tous doivent être cochés** :

- [ ] Je peux lancer la stack pilote sans aide
- [ ] Je peux me connecter patient et médecin
- [ ] Les tests automatisés passent
- [ ] Je sais où sont les secrets et comment les regénérer
- [ ] Je sais comment déployer sur VPS ([`DEPLOIEMENT_VPS.md`](./DEPLOIEMENT_VPS.md))
- [ ] Je sais qui contacter en cas d'incident
- [ ] J'ai lu la roadmap 90 jours et identifié les P0 du mois 1

---

## Sign-off reprise

| Rôle | Nom | Date | Signature |
|------|-----|------|-----------|
| Repreneur (dev) | | | |
| Propriétaire / donneur | | | |

---

## Annexe — Commandes de vérification rapide (copier-coller)

```powershell
# État stack
docker compose -f docker-compose.yml -f docker-compose.pilot.yml ps

# Health
curl http://127.0.0.1:8088/api/health

# Tests
python -m pytest tests/ -q
python scripts/pilot_go_live_verify.py

# Migrations
docker compose -f docker-compose.yml -f docker-compose.pilot.yml exec backend alembic current

# Logs erreurs
docker compose -f docker-compose.yml -f docker-compose.pilot.yml logs backend --tail 30
```

```bash
# VPS (sur serveur)
curl -fsS https://VOTRE_DOMAINE/api/health
docker compose -f docker-compose.yml -f docker-compose.staging.yml ps
ls -la backups/
sudo systemctl status plateforme-sante
```

---

**Checklist complète → vous êtes prêt à contribuer. Consultez [`ROADMAP_90_JOURS.md`](./ROADMAP_90_JOURS.md) pour la première sprint.**
