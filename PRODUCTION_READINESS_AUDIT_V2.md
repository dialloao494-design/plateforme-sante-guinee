# Audit de préparation production — Plateforme Santé Guinée (V2)

**Date :** 2026-05-25  
**Rôle :** Principal Architect e-santé (revue indépendante transversale)  
**Périmètre :** dépôt complet — backend FastAPI, frontend React, infra Docker/VPS, tests, docs  
**Hypothèse :** mise en production clinique réelle en Guinée (données de santé, secret médical, téléconsultation payante)  
**Méthode :** lecture statique du code, analyse des flux inter-modules, exécution de la suite de tests (`78 passed, 1 skipped, 1 error` sur 80 scénarios), recoupement avec audits antérieurs (#1 inscription, #2 paiement, #3 pièces jointes)

**Aucune modification de code** n'a été effectuée dans le cadre de cet audit.

---

## Synthèse exécutive

La plateforme a **franchi un palier significatif** depuis les audits initiaux : les trois blocages critiques historiques (inscription admin publique, paiement contournable, pièces jointes `/uploads` publiques) sont **corrigés et testés**. L'architecture métier converge vers des modules cohérents (`PaymentAccessPolicy`, `PaymentSettlementService`, `MessageAttachmentService`, provisioning sécurisé).

Pour une **mise en production clinique réelle**, des **défaillances systémiques** subsistent : contournement téléconsultation via `meeting_link` pré-paiement, IDOR sur les disponibilités médecin, absence de dossier clinique serveur, JWT en `localStorage`, course aux réservations, et gouvernance ops incomplète (secrets, seeds pilot).

**Verdict global : GO SOUS RÉSERVE**

| Dimension | Note /10 |
|-----------|----------|
| **Architecture** | **7,2** |
| **Sécurité** | **7,6** |
| **Maintenabilité** | **6,8** |
| **Scalabilité** | **6,0** |
| **Production readiness** | **7,0** |

**Estimation de préparation production clinique :** **4 à 8 semaines** (équipe 2–3 ingénieurs) pour fermer les 10 risques prioritaires, valider en staging réel, et obtenir un **GO PRODUCTION** sans réserve.

---

## 1. Périmètre et inventaire

### 1.1 Stack et surface API

| Couche | Technologie | Éléments clés |
|--------|-------------|---------------|
| Backend | FastAPI, SQLAlchemy 2, SlowAPI | ~80 endpoints répartis sur 12 routeurs |
| Frontend | React 19, Vite 8, Axios | Auth context, messagerie, téléconsult Jitsi embarquée |
| Base | SQLite (dev) / PostgreSQL 16 (prod) | Pool SQLAlchemy, `create_all` + Alembic + migrations ad hoc |
| Paiement | Stripe (live) + stubs Mobile Money | Webhooks idempotents, settlement verrouillé |
| Téléconsult | Jitsi (JaaS / self-hosted JWT / open) | JWT salle, fenêtre temporelle, policy paiement |
| Infra | Docker, nginx TLS, scripts VPS | Health/readiness, backups pg_dump, déploiement documenté |
| Tests | 7 modules pytest | ~78 scénarios sécurité/métier passants |

### 1.2 Modules métier analysés

```
Authentification ──┬── Autorisations (RBAC)
                   ├── Rendez-vous (/appointments + /rendezvous)
                   ├── Paiements (Stripe, settlement, refunds)
                   ├── Téléconsultation (access, Jitsi)
                   ├── Messagerie + pièces jointes
                   ├── Dossiers patients (démographie + notes client)
                   └── Notifications / WebSocket
```

---

## 2. État des blocages historiques (#1, #2, #3)

| Blocage | Statut audit V2 | Preuve |
|---------|-----------------|--------|
| **#1** Inscription / élévation admin | **Corrigé** | `user_provisioning`, hooks ORM, tests `test_registration_security.py` |
| **#2** Paiement contournable | **Corrigé** | `PaymentAccessPolicy`, settlement `FOR UPDATE`, tests paiement/téléconsult (44+) |
| **#3** Pièces jointes publiques | **Corrigé** | Pas de `StaticFiles`, download auth, 16 tests attachment, nginx 403 |

Ces corrections **ne suffisent pas** à elles seules pour un go-live clinique sans réserve — des failles **transversales** persistent (voir section 5).

---

## 3. Cohérence inter-modules

### 3.1 Authentification ↔ Autorisations

**Points forts**

- JWT HS256, `SECRET_KEY` obligatoire au démarrage.
- `get_current_user` vérifie la **cohérence rôle JWT / rôle DB** — atténue la rétention de privilèges après rétrogradation.
- Provisioning centralisé avec canaux autorisés (`public_register`, `admin_api`, `admin_bootstrap`, `admin_cli`, `test_fixture`) et hooks SQLAlchemy anti-escalade ORM.
- Rate limiting sur register (5/min) et login (10/min).

**Incohérences / gaps**

| Gap | Impact |
|-----|--------|
| Politique mot de passe : 6 car. public vs 8+ complexité admin | Comptes patients/médecins faibles |
| `get_current_user_or_none` sans sync rôle | Endpoints optionnels (ex. `/doctors/{id}/schedule`) |
| JWT en `localStorage` (frontend) | Vol de session via XSS — vecteur transversal |
| `/ws/live` : token en query string, pas de rechargement user DB | Logs proxy, révocation non prise en compte |
| `validate_production_secrets()` défini mais **jamais appelé** au startup | Clé faible possible en staging/prod |

### 3.2 Paiements ↔ Rendez-vous ↔ Téléconsultation

**Points forts**

- **`PaymentAccessPolicy`** = source de vérité unique pour trésorerie, téléconsult, transitions manuelles.
- Règle claire : seul `payment_status=paid` compte ; `status=pending` exclu même si payé.
- Settlement atomique `confirmed` + `paid` via `PaymentSettlementService` avec `SELECT FOR UPDATE`.
- Webhooks Stripe idempotents (`stripe_webhook_event`).
- Remboursements révoquent l'accès téléconsult.
- Stub paiement **bloqué en production** (`is_production`).

**Contournements inter-modules identifiés**

| # | Contournement | Sévérité | Mécanisme |
|---|---------------|----------|-----------|
| C1 | **Téléconsult sans passer par `/access`** | **Élevée** | `meeting_link` généré à la création du RDV (avant paiement), exposé dans `RendezVousResponse` ; en mode `self_hosted_open`, Jitsi n'exige pas de JWT → bypass paiement + fenêtre horaire |
| C2 | **`status=confirmed` + `payment_status=unpaid`** | Moyenne | `mark_appointment_payment_failed` (admin) ne réaligne pas le workflow |
| C3 | **UI vs API téléconsult** | Moyenne | Frontend peut afficher `canJoin` pour `pending+paid` alors que l'API renvoie `status_blocked` |
| C4 | **Double checkout Stripe** | Moyenne | `assert_checkout_allowed` libère le lock (`commit`) avant l'appel Stripe |
| C5 | **Statuts `checked_in`/`active`** | Faible | Autorisés par policy téléconsult mais non définis dans `VALID_TRANSITIONS` API |

**Verdict cohérence paiement/téléconsult :** les **chemins HTTP officiels** sont alignés ; le risque principal est **infrastructurel** (Jitsi ouvert + fuite `meeting_link`), pas un oubli de garde dans les routeurs.

### 3.3 Messagerie ↔ Pièces jointes ↔ Rendez-vous

**Points forts**

- RBAC rendez-vous sur list/send/download.
- Stockage opaque, chiffrement Fernet optionnel, audit log téléchargements.
- API n'expose pas `attachment_url` legacy.
- Frontend télécharge via blob authentifié.

**Verdict :** **Cohérent et production-grade** au niveau applicatif (blocage #3 fermé).

### 3.4 Dossiers cliniques ↔ Patients ↔ Médecins

**Constat majeur : il n'existe pas de dossier clinique serveur.**

| Donnée | Persistance | Contrôle d'accès |
|--------|-------------|------------------|
| Démographie patient | PostgreSQL | RBAC OK (médecin lié par RDV) |
| Messages / PJ | PostgreSQL + disque sécurisé | RBAC RDV + audit download |
| Synthèses de consultation | **`localStorage` navigateur** (`clinicalStorage.js`) | **Aucun** — perdues si cache effacé, non partagées, non auditées |
| Notes médecin patient | **`localStorage`** (`PatientDetails.jsx`) | **Aucun** — même problème |

Le frontend indique explicitement que la production devrait lier un dossier médical serveur — **non implémenté**.

**Impact conformité :** secret médical, traçabilité, continuité des soins, RGPD (Art. 5 intégrité/disponibilité, Art. 32 sécurité) — **insuffisant pour une clinique réelle**.

### 3.5 Duplication `/appointments` vs `/rendezvous`

Deux surfaces API parallèles pour le même domaine :

| Aspect | `/appointments` | `/rendezvous` |
|--------|-----------------|---------------|
| Création | `get_current_patient` | `get_current_user` + rejet non-patient |
| Mise à jour statut | PUT — patient/médecin/admin | PATCH — **admin/médecin seulement** |
| Policy paiement | `PaymentAccessPolicy` (aligné post-#2) | Idem |

**Risque systémique :** dérive future si un routeur est modifié sans l'autre ; dette cognitive pour les clients API et les audits.

---

## 4. Analyse par catégorie de risque

### 4.1 IDOR (Insecure Direct Object Reference)

| Ressource | Contrôle | Verdict |
|-----------|----------|---------|
| Rendez-vous | `_assert_can_access_appointment` | ✅ |
| Messages / PJ | `assert_appointment_access` | ✅ |
| Patients (lecture) | Lien RDV médecin-patient | ✅ |
| Patients (écriture médecin) | Lien RDV — **tous champs modifiables** | ⚠️ |
| Paiements | Ownership patient + scopes rôle | ✅ |
| Téléconsult `/access` | `_user_may_access` + policy | ✅ |
| **Disponibilités médecin** | Rôle doctor/admin — **sans lien `doctor_id` ↔ user** | ❌ **IDOR confirmé** |

**Exploit disponibilités :** tout médecin authentifié peut `POST/PUT/DELETE /doctors/{doctor_id}/availability` pour **n'importe quel** `doctor_id`.

### 4.2 Privilèges excessifs

| Acteur | Portée | Acceptable ? |
|--------|--------|--------------|
| Admin | Tous RDV, patients, settlement manuel, PJ | Oui (ops) — **sans audit lecture PHI** |
| Admin | Création admins via API | Oui si credentials protégés |
| Médecin | Liste patients avec RDV partagé | Oui |
| Médecin | Modification planning **d'autres médecins** | **Non** |
| Patient | Annulation / lecture propres RDV | Oui |

### 4.3 Fuite de données médicales (PHI)

| Vecteur | État |
|---------|------|
| `/uploads` public | **Fermé** |
| Répertoire médecins public (`GET /doctors/`) | Numéros, tarifs, géoloc — **intentionnel marketplace** |
| Logs auth (email) | Présent — risque modéré |
| `logger.debug` payload RDV si DEBUG | Risque si `LOG_LEVEL=DEBUG` en prod |
| `meeting_link` dans réponses API | **Fuite vecteur téléconsult pré-paiement** |
| Synthèses cliniques localStorage | **Hors périmètre serveur** — fuite par poste compromis |

### 4.4 Séparation des rôles

- Modèle 3 rôles (`patient`, `doctor`, `admin`) **globalement respecté**.
- Provisioning empêche l'auto-attribution admin.
- **Faille :** actions médecin non scopingées par identité professionnelle (disponibilités).

### 4.5 Concurrence et transactions

| Opération | Verrouillage | Risque |
|-----------|--------------|--------|
| Settlement paiement | `FOR UPDATE` | Faible |
| Webhook idempotence | Event dedup | Faible |
| Création RDV | Check-then-insert, re-check final | **TOCTOU** — double réservation créneau possible |
| Changement statut RDV | Pas de lock | Faible (fenêtre courte vs refund) |
| Checkout Stripe | Lock relâché avant API externe | Moyen (sessions multiples) |

### 4.6 Résilience

| Composant | Évaluation |
|-----------|------------|
| Health `/health`, readiness `/health/ready` | ✅ |
| `pool_pre_ping`, restart Docker | ✅ |
| Sentry optionnel | ✅ |
| Backups pg_dump scriptés | ✅ |
| Circuit breakers / retry Stripe | Partiel |
| Webhook `concurrent_claim` → 200 sans settlement | ⚠️ dépend retry Stripe |
| Single uvicorn worker (Dockerfile) | ⚠️ SPOF process |

### 4.7 Scalabilité

| Limite | Détail |
|--------|--------|
| Rate limit SlowAPI | **In-memory** — inefficace multi-workers |
| Pièces jointes | Volume local `uploads/secure` — pas d'object store |
| WebSocket | Placeholder, pas de bus distribué |
| Workers | 1 process uvicorn par défaut |
| DB | Pool 5+10 — suffisant MVP single-node |

### 4.8 Conformité e-santé (RGPD / secret médical — cadre indicatif)

| Exigence | État |
|----------|------|
| Contrôle d'accès PHI | Partiel — messagerie/PJ OK ; dossier clinique absent |
| Traçabilité accès | Partiel — audit PJ ; pas audit lecture dossier/patient |
| Chiffrement transit | TLS nginx — OK si déployé |
| Chiffrement repos | Fernet PJ optionnel ; DB non chiffrée par défaut |
| Minimisation | Liste médecins publique — choix produit |
| Durée conservation / purge | **Non définie** |
| DPA / registre traitements | Hors code |
| Hébergement données santé | Non documenté juridiquement dans le repo |

---

## 5. Top 10 risques restants

| Rang | Risque | Sévérité | Domaine |
|------|--------|----------|---------|
| **R1** | Bypass téléconsult via `meeting_link` + Jitsi `self_hosted_open` sans JWT | **Critique** | Paiement × Téléconsult × Infra |
| **R2** | IDOR disponibilités médecin (modification planning tiers) | **Élevée** | Autorisation |
| **R3** | Dossier clinique / synthèses / notes uniquement en `localStorage` | **Élevée** | Conformité × Architecture |
| **R4** | JWT session en `localStorage` (surface XSS) | **Élevée** | Auth × Frontend |
| **R5** | `validate_production_secrets()` non exécuté ; seeds pilot par défaut `true` en compose prod | **Élevée** | Ops / Config |
| **R6** | Course double réservation (booking sans contrainte DB atomique) | **Moyenne** | Concurrence |
| **R7** | Duplication API `/appointments` vs `/rendezvous` (dérive future) | **Moyenne** | Architecture |
| **R8** | Webhooks Mobile Money non authentifiés (stubs) — risque futur si activés sans HMAC | **Moyenne** | Paiement |
| **R9** | Rate limiting non distribué + worker unique | **Moyenne** | Scalabilité / DoS |
| **R10** | Absence audit lecture PHI (patients, messages, dossier) côté admin | **Moyenne** | Conformité |

---

## 6. Top 10 améliorations prioritaires

| Priorité | Action | Effort | Impact |
|----------|--------|--------|--------|
| **P1** | Ne pas exposer `meeting_link` utilisable avant `payment_status=paid` ; imposer JWT Jitsi en prod (`self_hosted_jwt` ou JaaS) | 3–5 j | Ferme R1 |
| **P2** | Lier mutations disponibilités à `doctor.user_id == current_user.id` (sauf admin) | 1 j | Ferme R2 |
| **P3** | Modèle serveur `ClinicalNote` / `ConsultationSummary` avec RBAC + audit | 2–3 sem. | Ferme R3 |
| **P4** | Tokens en cookie `HttpOnly` + `SameSite` ou BFF — réduire XSS | 1–2 sem. | Atténue R4 |
| **P5** | Appeler `validate_production_secrets()` au startup ; `ENABLE_PILOT_SEED=false` par défaut prod ; checklist deploy | 1 j | Ferme R5 |
| **P6** | Contrainte DB ou lock transactionnel sur chevauchement créneaux médecin | 3–5 j | Ferme R6 |
| **P7** | Déprécier `/rendezvous` ou unifier sur `/appointments` avec tests parité | 1 sem. | Ferme R7 |
| **P8** | Implémenter vérification HMAC avant tout webhook MM live | 3–5 j | Prévient R8 |
| **P9** | Gunicorn multi-workers + Redis rate limit + stockage PJ S3-compatible | 1–2 sem. | Ferme R9 |
| **P10** | Journal d'accès lecture (`phi_access_logs`) pour admin et exports | 1 sem. | Conformité |

---

## 7. Notations détaillées

### 7.1 Architecture — **7,2 / 10**

**Forces :** séparation routers/services, policies centralisées (paiement, PJ), provisioning unifié, documentation deploy riche.

**Faiblesses :** double API rendez-vous, dossier clinique non modélisé côté serveur, trois mécanismes de schéma (`create_all`, Alembic, `database_migrations.py`), logique métier parfois dupliquée frontend/backend (états RDV).

### 7.2 Sécurité — **7,6 / 10**

**Forces :** blocages #1–#3 corrigés avec tests ; RBAC core solide ; settlement verrouillé ; attachments défense en profondeur ; Stripe webhook signé.

**Faiblesses :** bypass Jitsi (R1), IDOR disponibilités (R2), JWT localStorage (R4), webhooks MM stubs, WebSocket token en query.

### 7.3 Maintenabilité — **6,8 / 10**

**Forces :** services extraits, tests sécurité ciblés (~80), docs d'audit par module.

**Faiblesses :** duplication endpoints, Pydantic v1/v2 mixte, seeds et flags env dispersés, dette `rendezvous` legacy.

### 7.4 Scalabilité — **6,0 / 10**

**Forces :** PostgreSQL pool, nginx reverse proxy, architecture stateless API (hors fichiers locaux).

**Faiblesses :** worker unique, rate limit local, PJ sur disque, pas de queue async (notifications, scan AV).

### 7.5 Production readiness — **7,0 / 10**

**Forces :** Docker prod, TLS, health checks, backups, guides VPS/staging, corrections sécurité majeures livrées.

**Faiblesses :** gaps clinique (dossier), ops (secrets validation), téléconsult prod (JWT obligatoire), conformité PHI incomplète.

---

## 8. Matrice de maturité par domaine

| Domaine | Maturité | Commentaire |
|---------|----------|-------------|
| Authentification | 🟢 Mature | JWT, rate limit, provisioning |
| Autorisations | 🟡 Partielle | IDOR disponibilités ; admin sans audit |
| Paiements Stripe | 🟢 Mature | Settlement, idempotence, prod stub off |
| Téléconsultation | 🟡 Partielle | Policy OK ; bypass infra possible |
| Rendez-vous | 🟡 Partielle | Logique OK ; concurrence booking |
| Messagerie | 🟢 Mature | RBAC + PJ sécurisées |
| Dossiers cliniques | 🔴 Immature | Client-only — **non clinique** |
| Pièces jointes | 🟢 Mature | Post-audit #3 |
| Infra / deploy | 🟢 Staging-ready | Prod clinique après durcissement |
| Conformité e-santé | 🔴 Insuffisante | Traçabilité et persistance PHI partielles |

---

## 9. Tests et assurance qualité

| Suite | Scénarios | Résultat observé |
|-------|-----------|------------------|
| `test_registration_security.py` | Inscription, ORM hooks, admin | 1 error (rate limit login flake) |
| `test_attachment_security.py` | PJ, RBAC, legacy | 15 passed, 1 skipped |
| `test_payment_*` | Settlement, access, Stripe | Pass |
| `test_teleconsult_access.py` | Policy, JWT, modes Jitsi | Pass |

**Couverture :** excellente sur chemins **critiques récemment corrigés** ; absente sur IDOR disponibilités, booking concurrent, dossier clinique, WebSocket auth.

**Recommandation :** ajouter tests d'intégration cross-module (booking race, doctor ownership, meeting_link non utilisable pré-paiement).

---

## 10. Checklist go-live clinique (extrait)

| # | Critère | Statut V2 |
|---|---------|-----------|
| 1 | Inscription admin publique impossible | ✅ |
| 2 | Paiement requis pour téléconsult (chemin API) | ✅ |
| 3 | PJ jamais servies sans auth | ✅ |
| 4 | Jitsi JWT obligatoire en production | ❌ |
| 5 | `meeting_link` masqué avant settlement | ❌ |
| 6 | Dossier clinique serveur auditable | ❌ |
| 7 | IDOR disponibilités fermé | ❌ |
| 8 | `ENABLE_PILOT_SEED=false` en prod | ⚠️ manuel |
| 9 | `ATTACHMENT_ENCRYPTION_KEY` défini | ⚠️ manuel |
| 10 | Staging validé bout-en-bout | ⚠️ hors repo |

---

## 11. Estimation de préparation production

| Phase | Durée | Livrables |
|-------|-------|-----------|
| **Phase A — Sécurité bloquante** (P1, P2, P5) | 1–2 sem. | Téléconsult durci, IDOR fix, hardening ops |
| **Phase B — Clinique** (P3, P10) | 2–4 sem. | Notes/synthèses serveur, audit PHI |
| **Phase C — Robustesse** (P4, P6, P7, P8) | 2–3 sem. | Auth cookies, booking atomique, API unifiée |
| **Phase D — Scale & conformité** (P9) | 1–2 sem. | Workers, Redis, object store |
| **Phase E — Validation staging réel** | 1–2 sem. | Parcours patient/médecin/paiement/vidéo |

**Total estimé : 4 à 8 semaines** selon périmètre dossier clinique (minimal vs complet).

**Jalons :**

- **Staging public / pilote contrôlé :** atteignable **immédiatement** après P1+P2+P5 (≈ 2 semaines).
- **Production clinique multi-praticiens :** après Phases A–C minimum.
- **Production à l'échelle nationale :** après Phase D.

---

## 12. Conclusion et statut

### Statut : **GO SOUS RÉSERVE**

**Justification :**

La plateforme **n'est plus en état NON GO** : les failles catastrophiques historiques (admin public, paiement factice, PHI en `/uploads`) sont corrigées avec tests et documentation. L'infrastructure staging (Docker, Postgres, nginx, Stripe, Jitsi documenté) est **déployable**.

Elle **n'atteint pas GO PRODUCTION clinique sans réserve** car :

1. Le **bypass téléconsultation** (R1) contourne la politique de paiement au niveau Jitsi — inacceptable pour un modèle payant clinique.
2. L'**absence de dossier clinique serveur** (R3) invalide la promesse produit « plateforme e-santé » pour un usage médical réel.
3. Des **IDOR et dettes ops** (R2, R5) restent ouverts.

**GO SOUS RÉSERVE** autorise :

- Déploiement **staging / pilote fermé** avec praticiens identifiés, Jitsi JWT configuré manuellement, seeds désactivés, et périmètre fonctionnel limité (RDV + paiement + messagerie, **sans** dossier clinique réglementaire).

**Conditions de passage à GO PRODUCTION :**

- [ ] R1 et R2 fermés et testés
- [ ] R3 adressé (serveur) ou périmètre produit explicitement réduit et validé juridiquement
- [ ] R5 appliqué sur tous environnements deployés
- [ ] Validation staging signée (`deploy/STAGING_VALIDATION.md`)
- [ ] Runbook incident PHI et procédure backup/restore testés

---

## 13. Références internes

| Document | Sujet |
|----------|-------|
| `docs/REGISTRATION_SECURITY_FIX_REPORT.md` | Blocage #1 |
| `docs/PAYMENT_PRODUCTION_CERTIFICATION.md` | Blocage #2 |
| `docs/ATTACHMENT_SECURITY_AUDIT_FINAL.md` | Blocage #3 |
| `ENGINEERING_AUDIT_REPORT.md` | Audit ingénierie V1 |
| `deploy/PRODUCTION_READINESS_REPORT.md` | Readiness staging V1 |
| `CRITICAL_REMEDIATION_PLAN.md` | Plan remédiation historique |

---

*Audit transversal V2 — lecture seule, aucune modification du dépôt.*
