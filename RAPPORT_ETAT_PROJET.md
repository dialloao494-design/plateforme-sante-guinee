# Rapport d'état du projet — Plateforme Santé Guinée

**Date :** juin 2026  
**Rédaction :** CTO SaaS e-santé  
**Version plateforme :** 1.0.0 MVP  
**Verdict pilote :** GO PILOTE = **OUI** (sous réserve clé Stripe test valide)

---

## 1. Synthèse exécutive

La Plateforme Santé Guinée est un **MVP e-santé fonctionnel** couvrant le parcours complet patient-médecin : inscription, rendez-vous, paiement, téléconsultation vidéo, messagerie et dossier patient serveur avec audit.

| Dimension | État | Note |
|-----------|------|------|
| Parcours patient | Opérationnel | 8/10 |
| Parcours médecin | Opérationnel | 8/10 |
| Dossier clinique | Opérationnel (MVP) | 7/10 |
| Infrastructure Docker/PostgreSQL | Opérationnel | 8/10 |
| Sécurité | Bêta avancée | 7/10 |
| Production publique nationale | Non prêt | 5/10 |

**Capacité pilote validée :** 3–5 sites, 5–8 médecins, 100–150 patients actifs, ~20 utilisateurs simultanés.

---

## 2. Schéma d'architecture (état actuel)

```
                         ┌─────────────────────────────────────┐
                         │         INTERNET / LAN              │
                         └──────────────────┬──────────────────┘
                                            │
                    ┌───────────────────────▼────────────────────────┐
                    │              NGINX (TLS termination)           │
                    │  :443 HTTPS  ·  :80 redirect  ·  pilote :9443  │
                    │                                                │
                    │   /api/*  ──────►  FastAPI Backend :8000       │
                    │   /api/ws/* ────►  WebSocket                   │
                    │   /uploads/* ───►  403 Forbidden               │
                    │   /*      ──────►  React SPA :80               │
                    └───────┬──────────────────────────┬─────────────┘
                            │                          │
              ┌─────────────▼────────────┐   ┌─────────▼──────────┐
              │   BACKEND FastAPI        │   │  FRONTEND React    │
              │   · 13 routeurs          │   │  · Vite build      │
              │   · JWT auth             │   │  · Jitsi SDK embed │
              │   · RBAC 3 rôles         │   │  · Stripe checkout │
              │   · SlowAPI rate limit   │   │  · AuthContext     │
              └─────────────┬────────────┘   └────────────────────┘
                            │
         ┌──────────────────┼──────────────────┬─────────────────┐
         │                  │                  │                 │
         ▼                  ▼                  ▼                 ▼
  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐
  │ PostgreSQL  │  │ Volume       │  │ Stripe API  │  │ Jitsi Server │
  │ 16 (pilote/ │  │ uploads/     │  │ + Webhooks  │  │ self-hosted  │
  │ prod)       │  │ docs chiffrés│  │             │  │ ou JaaS 8x8  │
  └─────────────┘  └──────────────┘  └─────────────┘  └──────────────┘

  ┌─────────────────────────────────────────────────────────────────┐
  │ MODULE DOSSIER PATIENT (Mission A1 — déployé PostgreSQL)        │
  │  clinical_notes · consultation_summaries · patient_documents    │
  │  clinical_audit_logs (append-only) · RBAC · timeline API        │
  └─────────────────────────────────────────────────────────────────┘
```

---

## 3. Ce qui est terminé

Fonctionnalités **complètes, testées et déployables**.

| Module | Détail | Preuve |
|--------|--------|--------|
| **Authentification JWT** | Register, login JSON, `/me`, guards rôle | `routers/auth.py`, tests registration |
| **RBAC 3 rôles** | patient, doctor, admin | `core/roles.py`, `security.py` |
| **Inscription sécurisée** | Pas d'élévation admin publique | `user_provisioning.py`, 16+ tests |
| **Rendez-vous** | CRUD, conflits, types physique/téléconsult | `rendezvous_service.py` |
| **Disponibilités médecin** | CRUD créneaux, validation booking | `availability_service.py` |
| **Paiement Stripe** | Checkout, webhooks idempotents, refunds | `stripe_webhook_processor.py`, 44+ tests |
| **Paiement stub staging** | Token header pour pilote sans carte | `core/payment_policy.py` |
| **Gate paiement téléconsult** | Accès salle bloqué si non payé | `PaymentAccessPolicy` |
| **Téléconsultation Jitsi** | Embed SDK, fenêtre horaire, JWT | `ConsultationRoom.jsx`, tests teleconsult |
| **Messagerie RDV** | Texte + pièces jointes chiffrées | `message_attachment_service.py` |
| **Pièces jointes sécurisées** | Pas de `/uploads` public, download auth | nginx 403, 16 tests attachment |
| **Dossier patient serveur** | Notes, synthèses, documents, timeline | Mission A1, 16 tests RBAC |
| **Audit trail clinique** | Logs read/create immutables | `clinical_audit_logs`, vérifié en pilote |
| **Docker full stack** | db + backend + frontend + nginx | `docker-compose*.yml` |
| **Migrations Alembic** | 3 révisions, head `20260525_0003` | Appliqué PostgreSQL pilote |
| **Boot guards production** | Bloque pilot seed + bypass dispo en prod | `core/settings.py`, 14 tests |
| **Health / readiness** | `/health`, `/health/ready` | Monitoring-ready |
| **Documentation ops** | Deploy VPS, staging validation, backup | `DEPLOIEMENT.md`, scripts VPS |

---

## 4. Ce qui est opérationnel

Fonctionnalités **en service sur l'instance pilote PostgreSQL** (juin 2026).

| Fonction | URL / endpoint | Statut live |
|----------|----------------|-------------|
| Frontend SPA | http://localhost:8088 | ✅ HTTP 200 |
| API backend | http://localhost:8088/api | ✅ HTTP 200 |
| HTTPS pilote | https://127.0.0.1:9443/api | ✅ HTTP 200 (self-signed) |
| PostgreSQL | localhost:5433 | ✅ 15 tables |
| OpenAPI | /api/openapi.json | ✅ 56 paths, dossier inclus |
| Inscription patient/médecin | POST /auth/register | ✅ HTTP 201 |
| Booking RDV | POST /appointments/ | ✅ avec validation dispo |
| Paiement stub | POST /payments/{id}/confirm-payment | ✅ confirmed |
| Notes cliniques | POST/GET /patients/{id}/notes | ✅ CRUD + audit |
| Synthèses | POST/GET /patients/{id}/summaries | ✅ CRUD + audit |
| Documents | POST/GET /patients/{id}/documents | ✅ upload + download |
| Timeline | GET /patients/{id}/timeline | ✅ |
| 4 médecins × 5 créneaux | doctor_availabilities | ✅ 20 slots |
| Flags sécurité pilote | ENABLE_PILOT_SEED=false, BYPASS=false | ✅ confirmé |

**Commande vérification :** `python scripts/pilot_go_live_verify.py`

---

## 5. Ce qui est en bêta

Fonctionnalités **présentes mais nécessitant configuration, validation ou périmètre limité**.

| Module | État bêta | Limitation | Action requise |
|--------|-----------|------------|----------------|
| **Stripe test** | Clé configurée | Clé test expirée (API error) | Renouveler clés dashboard Stripe |
| **Stripe live** | Code prêt | Non activé en prod | Clés live + webhook prod |
| **Orange Money GN** | Stub API | Pas d'intégration HTTP live | Partenariat opérateur |
| **MTN MoMo GN** | Stub API | Idem | Partenariat opérateur |
| **Jitsi self-hosted** | Fonctionnel en dev | Config manuelle domaine/tunnel | Sync JITSI_DOMAIN frontend/backend |
| **JaaS 8x8** | Code supporté | Non configuré en pilote | Clés JaaS production |
| **Notifications push/SMS/email** | In-app OK | Canaux externes non implémentés | Intégration SMTP/SMS |
| **JWT localStorage** | Fonctionnel | Risque XSS théorique | Migration cookies HttpOnly |
| **Multi-clinique** | Absent modèle | Médecins = sites via `location` | Modèle Clinic post-pilote |
| **Interface audit admin** | Backend only | Pas de UI dédiée | Page admin logs |
| **Dossier patient côté patient** | API OK | UI limitée (vue médecin riche) | Page patient self-service |
| **Concurrence 50+ users** | Testé partiellement | SQLite dev KO ; PG OK ~20 | Multi-workers gunicorn |
| **VPS staging public** | Documenté | Validation opérateur-dépendante | Exécuter STAGING_VALIDATION.md |

---

## 6. Ce qui n'est pas encore développé

Fonctionnalités **absentes ou hors périmètre MVP**.

| Fonctionnalité | Priorité suggérée | Commentaire |
|----------------|-------------------|-------------|
| Vérification identité médecin (ordre) | Haute | Inscription doctor sans KYC |
| Modèle multi-clinique / tenant | Haute | Gouvernance 3–5 cliniques manuelle |
| DMP national / interop HL7 FHIR | Moyenne | Export non standardisé |
| Ordonnance électronique réglementée | Haute | PDF simple, pas de signature qualifiée |
| Prise de RDV sans conflit atomique | Moyenne | Race condition booking (audit V2) |
| App mobile native (iOS/Android) | Basse | Web responsive suffisant MVP |
| Téléconsultation Daily.co / Twilio | Basse | Env detection only |
| Tableau de bord admin complet | Moyenne | Users list basique seulement |
| Rapports epidemio / analytics | Basse | Pas de BI intégré |
| RGPD : export données patient self-service | Moyenne | Demande manuelle admin |
| 2FA / MFA | Moyenne | Non implémenté |
| Rappels SMS automatiques RDV | Moyenne | Notification delivery stub |
| Pharmacie / e-prescription | Basse | Hors scope MVP |
| CI/CD GitHub Actions deploy auto | Moyenne | Tests locaux, pas pipeline deploy |
| Certificat médical numérique | Basse | — |

---

## 7. Matrice de maturité par domaine

```
Légende : ████ Terminé  ▓▓▓▓ Opérationnel  ░░░░ Bêta  .... Absent

Auth & rôles        ████████████ 100%
Rendez-vous         ███████████░  90%
Paiement Stripe     ████████░░░░  70%  (stub OK, live key à renouveler)
Téléconsultation    ████████░░░░  75%
Messagerie          █████████░░░  85%
Dossier patient     ████████░░░░  80%
Audit / conformité  ███████░░░░░  70%
Infra Docker/PG     █████████░░░  85%
HTTPS production    ▓▓▓▓░░░░░░░░  40%  (pilote self-signed OK)
Mobile Money GN     ░░░░........  10%
Notifications multi ░░░░........  20%
Multi-clinique      ............   0%
```

---

## 8. Tests et qualité

| Suite | Résultat | Fichiers clés |
|-------|----------|---------------|
| Sécurité inscription | ✅ Pass | `test_registration_security.py` |
| Paiement / settlement | ✅ Pass | `test_payment_*.py` |
| Téléconsultation | ✅ Pass | `test_teleconsult_*.py` |
| Pièces jointes | ✅ Pass | `test_attachment_security.py` |
| Dossier patient RBAC | ✅ Pass (16) | `test_patient_record_security.py` |
| Boot guards prod | ✅ Pass (14) | `test_production_boot_guard.py` |
| **Total pytest** | **~130+ passed** | `tests/` |
| E2E téléconsult | Script manuel | `scripts/e2e_teleconsult_validation.py` |
| GO PILOTE verify | Script automatisé | `scripts/pilot_go_live_verify.py` |

---

## 9. Stack technique (référence)

| Couche | Technologie | Version |
|--------|-------------|---------|
| Backend | Python, FastAPI | 3.12, 0.110 |
| Frontend | React, Vite | 19, 8 |
| Base prod | PostgreSQL | 16 |
| Base dev | SQLite | 3.x |
| Reverse proxy | Nginx | 1.27 |
| Conteneurs | Docker Compose | v2 |
| Visio | Jitsi (+ React SDK) | self-hosted |
| Paiement | Stripe | API v7 |
| Auth | JWT HS256 | — |

---

## 10. Environnements

| Env | Fichier | Base | HTTPS | Usage |
|-----|---------|------|-------|-------|
| Dev local | `.env` | SQLite | Non | Développement rapide |
| Pilote | `.env.pilot` | PostgreSQL Docker | Self-signed 9443 | QA, démo, pilote lundi |
| Staging VPS | `.env.staging` | PostgreSQL Docker | Let's Encrypt | Pré-production |
| Production | `.env.production` | PostgreSQL Docker | Let's Encrypt | Go-live national |

---

## 11. Risques résiduels (pilote)

| # | Risque | Sévérité | Mitigation pilote |
|---|--------|----------|-------------------|
| R1 | Clé Stripe test expirée | Moyenne | Stub payment ou renouveler clé |
| R2 | JWT localStorage | Faible | Pilote fermé, CSP, pas XSS |
| R3 | Pas de KYC médecin | Moyenne | Liste blanche praticiens pilote |
| R4 | ~20 users simultanés max | Faible | Pilote ≤ 100 patients étalés |
| R5 | Pas de multi-tenant clinique | Faible | 1 médecin = 1 site |
| R6 | Booking race condition | Faible | Volume pilote faible |

---

## 12. Roadmap suggérée (post-pilote)

### Phase 1 — Consolidation pilote (2–4 semaines)
- Renouveler clés Stripe test + valider webhook staging
- VPS staging public + checklist STAGING_VALIDATION
- UI dossier patient côté patient
- Multi-workers backend (gunicorn)

### Phase 2 — Pré-production (4–6 semaines)
- Modèle Clinic / multi-site
- Vérification identité médecin
- Cookies HttpOnly / refresh tokens
- Orange Money / MTN intégration live
- Interface admin audit logs

### Phase 3 — Production nationale (8–12 semaines)
- Stripe live + conformité facturation
- JaaS production ou Jitsi HA
- SMS rappels RDV
- Interopérabilité DMP / export FHIR
- Certification sécurité externe

---

## 13. Documentation disponible

| Document | Public |
|----------|--------|
| [ARCHITECTURE_GLOBALE.md](./ARCHITECTURE_GLOBALE.md) | Technique |
| [DOSSIER_PATIENT.md](./DOSSIER_PATIENT.md) | Technique / conformité |
| [DEPLOIEMENT.md](./DEPLOIEMENT.md) | DevOps |
| [GUIDE_UTILISATEUR_MEDECIN.md](./GUIDE_UTILISATEUR_MEDECIN.md) | Médecins |
| [GUIDE_UTILISATEUR_PATIENT.md](./GUIDE_UTILISATEUR_PATIENT.md) | Patients |
| [README.md](./README.md) | Démarrage rapide |
| `deploy/STAGING_VALIDATION.md` | Checklist staging |
| `deploy/ARCHITECTURE.md` | Infra détaillée |

---

## 14. Verdict final

| Question | Réponse |
|----------|---------|
| MVP fonctionnel ? | **Oui** |
| Prêt pilote contrôlé lundi ? | **Oui** (PostgreSQL + dossier A1 déployés) |
| Prêt production publique ? | **Non** — 4 à 8 semaines estimées |
| GO PILOTE | **OUI** |
| Action immédiate | Renouveler clé Stripe test avant paiements carte réels |

---

*Document généré pour permettre à une personne externe de comprendre l'état, exploiter et déployer la plateforme sans assistance supplémentaire.*
