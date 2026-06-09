# Rapport d'audit d'ingénierie — Plateforme Santé Guinée

**Rôle :** Staff / Principal Engineer — revue pré-production clinique  
**Date :** 2026-06-01  
**Périmètre :** dépôt `plateforme-sante-guinee` (lecture seule du code, sans modification)  
**Hypothèse générale :** déploiement cible = clinique réelle en Guinée, données de santé, téléconsultation vidéo intégrée.

---

## Synthèse exécutive

La plateforme est **fonctionnellement avancée** (parcours RDV, paiement Stripe, messagerie, téléconsultation Jitsi embarquée, Docker/VPS documentés). Pour une **mise en production clinique**, plusieurs **failles de sécurité et de gouvernance des données** doivent être traitées avant tout go-live : inscription `admin` publique, confirmation de paiement sans preuve Stripe, fichiers médicaux servis sans authentification, JWT en `localStorage`, synthèses cliniques uniquement côté navigateur, et schéma DB géré par trois mécanismes parallèles.

**Verdict production clinic :** **non prêt** sans plan de remédiation priorisé (voir section 10).

---

## 1. ARCHITECTURE

### 1.1 Structure globale

```
plateforme-sante-guinee/
├── main.py                 # Point d'entrée FastAPI, CORS, seeds, create_all
├── database.py             # SQLAlchemy engine (SQLite / PostgreSQL)
├── security.py             # JWT, rôles, hash bcrypt
├── core/                   # settings, logging, limiter, monitoring (Sentry)
├── models/                 # 8 entités ORM
├── schemas/                # Pydantic v2 (partiellement validators v1 style)
├── routers/                # 12 routeurs API
├── services/               # Métier (rendezvous, stripe, teleconsult, seeds…)
├── alembic/                # 2 révisions (baseline no-op + géoloc)
├── frontend-sante/frontend/  # React 19 + Vite 8
├── deploy/                 # nginx, VPS, Jitsi
├── scripts/                # E2E Python, tunnels, QA PowerShell
└── tests/                  # 1 fichier pytest (téléconsultation)
```

**Preuve :** arborescence du dépôt (~450+ fichiers dont clone `deploy/jitsi/docker-jitsi-meet/` non ignoré par défaut).

### 1.2 Qualité du découpage

| Aspect | Évaluation | Preuve |
|--------|------------|--------|
| Séparation routers / services | **Bonne** | `services/rendezvous_service.py`, `services/teleconsultation_access.py` |
| Duplication API rendez-vous | **Mauvaise** | `/rendezvous` (`routers/rendezvous.py`) **et** `/appointments` (`routers/appointments.py`) avec règles métier **différentes** |
| Configuration centralisée | **Partielle** | `core/settings.py` existe mais `main.py` lit encore `os.getenv` directement pour CORS/seeds |
| Frontend | **Classique** | Contextes React (`AuthContext`, `AppointmentContext`) + services API |

**Exemple critique de divergence :** confirmation sans paiement bloquée sur `/rendezvous` :

```145:150:routers/rendezvous.py
    if update.status == "confirmed" and appointment.payment_status != "paid":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot confirm appointment without payment. Patient must pay first."
        )
```

Mais sur `/appointments` le `PUT` appelle `update_appointment_status` **sans** ce garde-fou :

```130:157:routers/appointments.py
@router.put("/{appointment_id}", ...)
def update_appointment(...):
    ...
    return RendezVousService.update_appointment_status(
        rdv_id=appointment_id,
        new_status=update.status,
        db=db,
    )
```

### 1.3 Dette technique

| Item | Impact | Fichiers |
|------|--------|----------|
| `create_all` à chaque démarrage | Dérive schéma vs Alembic | `main.py` L323-324 |
| Alembic baseline no-op | Schéma réel non versionné | `alembic/versions/20260515_0001_baseline_stamp.py` |
| `AUTO_CREATE_TABLES` documenté mais **non lu** | Confusion ops | `.env.example` vs `main.py` |
| Clone Jitsi volumineux dans le repo | Maintenance, risque secrets `.env` | `deploy/jitsi/docker-jitsi-meet/` |
| `validate_production_secrets()` jamais appelé | SECRET_KEY faible possible en prod | `core/settings.py` L70-75 |
| Documentation abondante mais parfois obsolète | Onboarding coûteux | multiples `*.md` à la racine |

### 1.4 Risques de maintenance

- **Deux clients API frontend** conceptuellement un seul (`httpClient.js`), mais chemins `/rendezvous` vs `/appointments` selon les pages.
- **Environnements tunnels** : URLs Cloudflare éphémères dans `.env.tunnel` (risque commit — voir DevOps).
- **Seeds pilot** activés par défaut hors production (`ENABLE_PILOT_SEED` default `not _is_production`) — `main.py` L342-344.

---

## 2. BACKEND

### 2.1 Sécurité

| Finding | Sévérité | Preuve |
|---------|---------|--------|
| Inscription publique avec `role: admin` | **Critique** | `schemas/user.py` L26-32 ; `routers/auth.py` L50-54 |
| `POST /payments/{id}/confirm-payment` marque payé+confirmé **sans Stripe** | **Critique** | `routers/payments.py` L153-214 |
| Fichiers `/uploads/...` montés sans auth | **Élevé** | `main.py` L109-111 ; URLs dans `routers/messages.py` L113 |
| Annuaire médecins public (`GET /doctors/`) | **Moyen** (privacy) | `routers/doctor.py` |
| Webhooks Orange/MTN sans signature | **Moyen** (stubs) | `routers/payments.py` |
| `ProxyHeadersMiddleware(trusted_hosts="*")` | **Moyen** si proxy mal configuré | `main.py` L107 |
| Mots de passe min **6** caractères à l'inscription | **Moyen** | `schemas/user.py` L19-24 vs `validate_password()` inutilisé dans `security.py` |
| JWT HS256, pas de refresh/révocation | **Moyen** | `security.py` |
| Rate limit seulement register/login | **Faible** | `routers/auth.py` + `core/limiter.py` |

### 2.2 Authentification

- **OAuth2PasswordBearer** + JWT (`security.py`).
- Vérification **rôle token vs DB** à chaque requête (`get_current_user`) — **point positif**.
- Login JSON : `/auth/login-json` (utilisé par le frontend).

### 2.3 Autorisations

- Pattern `require_roles([...])` largement utilisé sur téléconsultation, notifications, dashboard médecin.
- **IDOR disponibilités médecin :** création/modification pour tout `doctor_id` sans lien `user_id` — `routers/doctor.py` (signalé en revue ciblée).
- Téléconsultation : contrôle patient/médecin/admin cohérent — `services/teleconsultation_access.py` `_user_may_access`.

### 2.4 Validation des données

- Pydantic v2 sur schémas utilisateur/rendez-vous.
- **Incohérence** : validateurs `@validator` legacy dans `schemas/availability.py` (warnings Pydantic v2 en tests).
- Dates RDV en **naive local** — documenté et géré explicitement en téléconsultation (`datetime.now()`).

### 2.5 Gestion des erreurs

- Handler global 500 masque les détails client — `main.py` (handler Exception).
- HTTPException métier en français sur plusieurs routes — bon pour UX API.

### 2.6 Performances

- Pool PostgreSQL configuré (`database.py`) : `pool_size=5`, `max_overflow=10`.
- Pas de cache, pas de pagination uniforme sur listes longues.
- Upload messages : lecture fichier entier en mémoire — `routers/messages.py` L108-110.

### 2.7 Scalabilité

- **WebSocket** minimal (`routers/ws.py`) — pas utilisé pour la téléconsultation (Jitsi gère le média).
- Fichiers uploads sur disque local — non compatible multi-réplica sans stockage partagé (S3/NFS).
- SQLite par défaut — non adapté production multi-utilisateur.

---

## 3. FRONTEND

### 3.1 Organisation

- **React 19** + **Vite 8** + **react-router-dom 7**.
- Pages par rôle (Dashboard, Appointments, ConsultationRoom, etc.).
- Téléconsultation : `ConsultationRoom.jsx`, `JitsiEmbeddedMeeting.jsx`, `teleconsultationProvider.js`.

### 3.2 Performance

- Pas de code-splitting documenté ; bundle unique (`npm run build`).
- Polling room-status toutes les 15s en prejoin — `ConsultationRoom.jsx`.
- SDK Jitsi chargé à la demande via iframe — coût réseau important sur mobile.

### 3.3 Gestion d'état

| Donnée | Stockage |
|--------|----------|
| Session | `localStorage` (`token`, `access_token`, `user_role`) — `AuthContext.jsx` |
| RDV / patients | Context + refetch API |
| Synthèses consultation | **`localStorage` uniquement** — `clinicalStorage.js` |
| Paiement simulé (démo) | `localStorage` si `VITE_ENABLE_PAYMENT_SIMULATION` |

### 3.4 UX

- Parcours prejoin caméra/micro, messages FR, machine d'états salle (`prejoin` → `live` → `ended`).
- Compteur participants via API Jitsi — `JitsiEmbeddedMeeting.jsx`.
- Dépendance forte à la config tunnel/Jitsi (échecs = écran noir, 0 participant).

### 3.5 Accessibilité

- Pas de tests a11y, pas de `aria-live` explicite sur la salle vidéo.
- Contrôles Jitsi dans iframe — accessibilité déléguée à Jitsi.

### 3.6 Risques de bugs

| Risque | Preuve |
|--------|--------|
| Double clé token | `AuthContext` écrit `token` et `access_token` |
| Fallback API Railway hardcodé | `httpClient.js` si `VITE_API_URL` absent en prod |
| `meet.jit.si` bloqué côté client mais backend peut encore servir 127.0.0.1 | `teleconsultationProvider.js` |
| Trailing slash `/appointments/{id}/` vs sans slash | tests E2E documentent le piège |
| Vite arrêté = tunnel app 502 | observé en validation ops |

---

## 4. BASE DE DONNÉES

### 4.1 Modèle de données

Entités principales : `User`, `Patient`, `Doctor`, `RendezVous`, `Payment`, `Message`, `DoctorAvailability`, `NotificationEvent`.

**Preuve :** `models/__init__.py`.

### 4.2 Relations

- `RendezVous` → `Doctor`, `Patient` (FK indexées).
- `Message` → `RendezVous`, `User` (sender).
- Cascades ORM limitées aux enfants (`payments`, `messages`, `availabilities`) — pas de `ON DELETE` SQL explicite.

### 4.3 Index

- Bonne couverture sur `rendezvous` (`date`, `status`, `payment_status`, FK).
- **Manques :** `doctor_availabilities.doctor_id` non indexé ; pas d'index composite `(doctor_id, day_of_week)` — `models/availability.py`.

### 4.4 Cohérence

- Statuts en **chaînes libres** (`pending`, `confirmed`, `paid`…) — pas d'enum DB.
- `JOINABLE_STATUSES` inclut `pending` pour téléconsultation — joint possible avant paiement réel :

```58:58:services/teleconsultation_access.py
JOINABLE_STATUSES = frozenset({"confirmed", "completed", "checked_in", "active", "paid", "pending"})
```

### 4.5 Risques de corruption

- `create_all` + migrations runtime + Alembic partiel → risque de schéma différent selon environnement.
- Pas de contrainte unique sur créneaux médecin (double booking possible selon logique applicative).
- Horodatages `datetime.utcnow` sur modèles — téléconsultation utilise `datetime.now()` local (documenté, mais risque de confusion ops).

---

## 5. TÉLÉCONSULTATION

### 5.1 Intégration Jitsi

| Composant | Rôle |
|-----------|------|
| `services/teleconsult_room.py` | Nom de salle hashé `sante-gn-{id}-{hash}` |
| `services/teleconsultation_access.py` | Fenêtre temporelle, RBAC, payload embed |
| `services/jitsi_jwt.py` | JWT HS256 (self-hosted) / RS256 (JaaS) |
| `JitsiEmbeddedMeeting.jsx` | `@jitsi/react-sdk`, config lobby/login désactivés |
| `deploy/jitsi/` | Docker local, patches sans OAuth |

**Preuve :** blocage `meet.jit.si` — `teleconsult_room.py` `BLOCKED_EMBED_DOMAINS`.

### 5.2 Sécurité

- Accès salle via API authentifiée (`/teleconsultation/appointments/{id}/access`).
- JWT Jitsi émis côté serveur si configuré (JaaS ou self-hosted).
- **Risque :** salle dev open (`ENABLE_AUTH=0` en dev Docker) — `deploy/jitsi/patches.env`.
- URLs de réunion prévisibles (hash déterministe avec `SECRET_KEY`) — connaissance de l'ID + salt partiel.

### 5.3 Robustesse

- Gestion erreurs `membersOnly`, lobby dans le composant React.
- Dépendance **Cloudflare tunnel** pour iPhone (ops fragile, URLs volatiles).
- Backend multiple instances sur port 8000 observé en validation (config `JITSI_DOMAIN` stale).

### 5.4 Cas d'échec

| Cas | Comportement |
|-----|----------------|
| Jitsi down | Iframe vide, 0 participant |
| Tunnel expiré | Patient mobile ne joint pas |
| `JITSI_DOMAIN` désaligné backend/front | Salle différente / échec connexion |
| Caméra refusée Safari | `mapMediaDeviceError` FR |
| RDV hors fenêtre | `too_early` / `too_late` API |

### 5.5 Qualité UX

- Intégration in-app (pas d'onglet externe) — objectif atteint en config correcte.
- Pas d'enregistrement, pas de chat intégré in-call (hors scope).
- Synthèse médecin **non persistée serveur** — perte si changement d'appareil.

---

## 6. CONFORMITÉ E-SANTÉ

> **Hypothèse :** exigences type RGPD / bonnes pratiques données de santé ; **pas d'audit juridique** Guinée.

| Exigence | État | Preuve |
|----------|------|--------|
| Confidentialité | **Insuffisant** | JWT + PHI en localStorage ; uploads publics |
| Données médicales | **Partiel** | Messages/ RDV en DB ; synthèses hors serveur |
| Journalisation | **Partiel** | `core/logging_config.py` JSON en prod ; pas d'audit trail médical |
| Traçabilité accès | **Faible** | Pas de log structuré « qui a accédé à quel RDV » |
| Consentement / DPIA | **Absent** du code | — |
| Rétention / suppression | **Partielle** | Cancel RDV ; pas de purge PHI documentée |
| Chiffrement transit | **Oui** (HTTPS tunnel/prod) | nginx template |
| Chiffrement repos | **Non démontré** | SQLite/Postgres sans TDE dans repo |

**Points positifs :** Sentry optionnel (`core/monitoring.py`), masquage URL DB au log (`database.py`).

---

## 7. TESTS

### 7.1 Couverture actuelle

| Type | Fichiers | Portée |
|------|----------|--------|
| Pytest unitaire | `tests/test_teleconsult_access.py` (9 tests) | `teleconsultation_access` mocké |
| CI GitHub | `.github/workflows/ci.yml` | `npm run build` frontend + secrets-guard |
| E2E manuels | `scripts/e2e_*.py`, `test_flow.py` | API HTTP, comptes pilot |
| Frontend | **Aucun** | pas de Vitest/Playwright |

**Preuve :** `pytest` **absent** de `requirements.txt` / `requirements-prod.txt`.

### 7.2 Parties non testées

- Paiements Stripe (webhook, confirm-payment abuse)
- Autorisations IDOR (doctor availability, appointments PUT)
- Messagerie / uploads
- Frontend (tous parcours)
- Jitsi bout-en-bout (WebRTC)
- Migrations Alembic sur PostgreSQL vierge

### 7.3 Risques majeurs

1. Régression sécurité paiement non détectée en CI.
2. Régression téléconsultation partiellement couverte (9 tests mock).
3. Aucun test de charge (Jitsi + API concurrente).

---

## 8. DEVOPS

### 8.1 Docker

- `docker-compose.yml` : Postgres, backend, frontend, nginx.
- Overlays `staging` / `prod` avec TLS, limites ressources.
- Jitsi **séparé** — `scripts/start_jitsi_dev.ps1`.

### 8.2 Variables d'environnement

- Templates : `.env.example`, `.env.production.example`, `frontend-sante/frontend/.env.example`.
- **Manque :** `deploy/env/.env.backend.example` référencé dans docs mais absent du tree (signalé en exploration).
- `.env.tunnel` avec hostnames réels — **risque commit** (non listé dans `.gitignore` standard).

### 8.3 Déploiement

- Scripts VPS : `deploy/vps/deploy-production.sh`, `init-ssl.sh`.
- Entrypoint backend : Alembic + `create_all` — `scripts/docker/entrypoint-backend.sh`.

### 8.4 Sauvegardes

- `deploy/vps/backup-db.sh` — `pg_dump`, rétention 14 jours.
- Pas de backup SQLite automatisé.

### 8.5 Monitoring

- Health : `/health`, `/health/ready` (DB `SELECT 1`).
- Sentry via `SENTRY_DSN`.
- `LOG_FILE` dans `.env.example` **non implémenté** (stdout uniquement).

### 8.6 Logs

- Format JSON si `LOG_FORMAT=json` en staging/prod — `core/settings.py` L32.

---

## 9. SCORE GLOBAL

| Dimension | Note /10 | Commentaire |
|-----------|----------|-------------|
| **Architecture** | **6.0** | Découpage services correct, duplication `/rendezvous` vs `/appointments`, dette schéma |
| **Sécurité** | **4.0** | Failles critiques inscription admin + paiement + fichiers publics |
| **Maintenabilité** | **5.5** | Docs riches, mais drift ; clone Jitsi ; peu de tests |
| **Scalabilité** | **5.0** | Postgres possible, mais uploads locaux et SQLite dev |
| **Production readiness** | **4.0** | Infra Docker OK ; garde-fous métier/sécurité insuffisants pour clinique |

**Moyenne pondérée (production clinique) : ~4.9 / 10**

---

## 10. PLAN D'ACTION

### A. Top 20 problèmes les plus critiques

| # | Problème | Sévérité | Fichier(s) |
|---|----------|---------|------------|
| 1 | Inscription `admin` ouverte | Critique | `schemas/user.py`, `routers/auth.py` |
| 2 | `confirm-payment` sans vérification Stripe | Critique | `routers/payments.py` L153-214 |
| 3 | Fichiers `/uploads` accessibles sans JWT | Critique | `main.py`, `routers/messages.py` |
| 4 | JWT en `localStorage` (vol XSS) | Élevé | `AuthContext.jsx`, `httpClient.js` |
| 5 | Synthèses cliniques non persistées | Élevé | `clinicalStorage.js` |
| 6 | `PUT /appointments` confirme sans garde paiement | Élevé | `routers/appointments.py` |
| 7 | IDOR créneaux médecin | Élevé | `routers/doctor.py` |
| 8 | `validate_production_secrets()` non appelé | Élevé | `core/settings.py`, `main.py` |
| 9 | `JOINABLE_STATUSES` inclut `pending` | Moyen | `teleconsultation_access.py` |
| 10 | Double backend / env stale (ops) | Moyen | validation terrain |
| 11 | `create_all` à chaque boot | Moyen | `main.py` |
| 12 | Alembic non source de vérité | Moyen | `alembic/versions/` |
| 13 | Pilot seed mots de passe en source | Moyen | `services/pilot_seed.py` |
| 14 | `.env.tunnel` peut fuiter | Moyen | `frontend-sante/frontend/.env.tunnel` |
| 15 | Pas de tests paiement / auth en CI | Moyen | `.github/workflows/ci.yml` |
| 16 | `pytest` absent des requirements | Faible | `requirements.txt` |
| 17 | Annuaire médecins public | Faible | `routers/doctor.py` |
| 18 | Webhooks mobile money non sécurisés | Faible | `routers/payments.py` |
| 19 | Pas d'audit log accès PHI | Faible | global |
| 20 | Tunnel Cloudflare éphémère pour prod | Faible | ops |

### B. Quick wins (< 1 h)

1. **Interdire `role=admin` à l'inscription** — whitelist `patient`/`doctor` côté API.
2. **Désactiver ou protéger `confirm-payment`** (flag dev uniquement ou preuve Stripe obligatoire).
3. **Appeler `get_settings().validate_production_secrets()`** au startup si `ENVIRONMENT=production`.
4. **Retirer `pending` de `JOINABLE_STATUSES`** (ou exiger `payment_status=paid`).
5. **Ajouter `pytest` à `requirements-dev.txt`** + job CI `pytest tests/`.
6. **Gitignore** `.env.tunnel`, `deploy/jitsi/docker-jitsi-meet/.env`.
7. **Unifier** `PUT /appointments` avec la règle paiement de `/rendezvous`.
8. **Documenter** URL tunnels actives dans `docs/VALIDATION_RUN_STATUS.md` (ops).

### C. Améliorations importantes (< 1 jour)

1. **Protéger `/uploads`** (signed URLs ou middleware auth).
2. **Fusionner ou déprécier** `/appointments` vs `/rendezvous`.
3. **Persister synthèses** via endpoint API + table `consultation_notes`.
4. **Cookies httpOnly** pour session (refactor auth).
5. **Fichiers `deploy/env/*.example`** manquants.
6. **Tests d'intégration** paiement Stripe (mock webhook).
7. **Playwright** smoke : login → RDV → salle (sans assert vidéo).
8. **Durcir mots de passe** (utiliser `validate_password` à l'inscription).
9. **Index** `doctor_availabilities.doctor_id`.
10. **CI :** `npm run lint` + `pytest` obligatoires.

### D. Chantiers majeurs (> 1 semaine)

1. **Conformité e-santé** : registre traitements, consentement, rétention, audit log, DPO workflow.
2. **Stockage fichiers S3-compatible** + antivirus + chiffrement repos.
3. **Jitsi production** : JaaS ou self-hosted fixe (domaine, TLS, JWT), plus tunnels éphémères.
4. **Migrations Alembic** complètes ; supprimer `create_all` en prod.
5. **Observabilité** : métriques (Prometheus), alerting, corrélation request-id.
6. **Tests E2E** automatisés PC + BrowserStack Safari (vidéo).
7. **Revue sécurité externe** (pentest) avant ouverture clinique.
8. **Haute disponibilité** : backup restore drill automatisé, runbook incident.

---

## Hypothèses et limites de l'audit

1. **Pas d'exécution** de pentest ni de scan SAST/DAST automatisé dans cet audit.
2. **Pas de revue** du contenu de `sante.db` ni des secrets réels en production.
3. **Docker/Jitsi** supposés opérationnels selon votre dernier message — non re-vérifiés au moment de la rédaction si l'environnement a changé.
4. **Droit local Guinée** : recommandations alignées sur bonnes pratiques internationales, pas avis juridique.

---

## Documents connexes dans le dépôt

- `SECURITY_AUDIT.md` (audit antérieur — à rapprocher, peut être partiellement obsolète)
- `deploy/PRODUCTION_READINESS_REPORT.md`
- `docs/TELECONSULT_REAL_CALL_PROCEDURE.md`
- `docs/VALIDATION_FINAL_REPORT.md`

---

*Rapport généré par audit statique du code. Aucune modification du dépôt n'a été effectuée dans le cadre de cette livraison.*
