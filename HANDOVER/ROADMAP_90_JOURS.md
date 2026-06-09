# Roadmap 90 jours — Plateforme Santé Guinée

Plan produit et technique pour les **3 premiers mois** après reprise du projet.  
Priorisation : **sécuriser → déployer → consolider → étendre**.

---

## Vue d'ensemble

```
Mois 1 (J1–J30)   : Reprise + VPS autonome + stabilisation
Mois 2 (J31–J60)  : Pré-production + sécurité + UX clinique
Mois 3 (J61–J90)  : Production publique + paiements GN + scale
```

---

## Mois 1 — Reprise et infrastructure autonome (J1–J30)

### Semaine 1 — Onboarding technique

| Priorité | Tâche | Livrable | Effort |
|----------|-------|----------|--------|
| P0 | Parcourir HANDOVER + faire tourner pilote Docker | Checklist reprise validée | 1 j |
| P0 | Exécuter `pytest` + `pilot_go_live_verify.py` | Rapport tests vert | 0.5 j |
| P0 | Parcours manuel patient + médecin | Notes bugs UI/UX | 1 j |
| P1 | Accès GitHub, Stripe, domaine | Credentials documentés (vault) | 0.5 j |
| P1 | Lire architecture dossier patient | Compréhension RBAC/audit | 1 j |

### Semaine 2 — VPS autonome

| Priorité | Tâche | Livrable | Effort |
|----------|-------|----------|--------|
| P0 | Provisionner VPS Ubuntu 22.04 (4 Go RAM) | IP + SSH | 0.5 j |
| P0 | Configurer DNS A → VPS | Domaine résolu | 0.5 j |
| P0 | Exécuter `bootstrap-autonomous.sh` | HTTPS live | 1 j |
| P0 | Valider `vps_autonomous_verify.py` | Rapport GO autonome | 0.5 j |
| P1 | Tester depuis smartphone 4G (Guinée) | Capture + rapport | 0.5 j |
| P1 | Configurer monitoring uptime (UptimeRobot) | Alertes email | 0.5 j |

### Semaine 3 — Stabilisation

| Priorité | Tâche | Livrable | Effort |
|----------|-------|----------|--------|
| P0 | Renouveler clés Stripe test + webhook staging | Paiement test OK | 1 j |
| P1 | Restauration backup drill | Procédure validée | 0.5 j |
| P1 | Corriger bugs bloquants remontés semaine 1 | PRs mergées | 2–3 j |
| P2 | Documenter runbook ops (incidents) | Mise à jour HANDOVER | 0.5 j |

### Semaine 4 — Jitsi staging

| Priorité | Tâche | Livrable | Effort |
|----------|-------|----------|--------|
| P1 | Déployer Jitsi sur sous-domaine `meet.domaine.gn` | Instance sans lobby | 2 j |
| P1 | Configurer JWT Jitsi + tests téléconsult 4G | Appel vidéo patient↔médecin | 1 j |
| P2 | Script validation E2E téléconsult | `e2e_teleconsult_validation.py` vert | 1 j |

**Jalon M1 :** Plateforme accessible 24/7 sur VPS, parcours patient complet HTTPS, backups OK.

---

## Mois 2 — Pré-production et sécurité (J31–J60)

### Produit (priorités utilisateur)

| # | Fonctionnalité | Détail | Impact |
|---|----------------|--------|--------|
| P1 | UI dossier patient (côté patient) | Voir notes/synthèses/documents en self-service | Fort |
| P1 | Notifications email RDV | Confirmation + rappel J-1 | Fort |
| P2 | Recherche médecin géolocalisée | Améliorer filtres Conakry/Kindia | Moyen |
| P2 | Tableau admin audit logs | Interface lecture `clinical_audit_logs` | Conformité |
| P3 | Onboarding médecin guidé | Wizard profil + disponibilités | UX |

### Technique (priorités engineering)

| # | Amélioration | Détail | Risque si ignoré |
|---|--------------|--------|------------------|
| P0 | Refresh tokens / HttpOnly cookies | Remplacer JWT localStorage | XSS → vol session |
| P1 | Unifier `/rendezvous` et `/appointments` | Duplication endpoints | Dette API, bugs clients |
| P1 | Gunicorn multi-workers backend | `uvicorn` → gunicorn en prod | Limite ~20 users simultanés |
| P1 | Vérification identité médecin | KYC manuel ou partenaire | Praticiens non vérifiés |
| P2 | Rate limiting affiné par route | SlowAPI déjà présent | Abus inscription |
| P2 | Sentry production | `SENTRY_DSN` configuré | Incidents silencieux |
| P3 | CI/CD GitHub Actions deploy VPS | Push → deploy staging auto | Deploy manuel error-prone |

### Sécurité (must-have avant prod publique)

| # | Item | Statut actuel | Cible J60 |
|---|------|---------------|-----------|
| S1 | Inscription admin publique bloquée | ✅ Fait | Maintenir |
| S2 | Uploads /uploads bloqués nginx+API | ✅ Fait | Maintenir |
| S3 | RBAC dossier patient | ✅ Fait | Tests E2E |
| S4 | JWT storage sécurisé | ❌ localStorage | HttpOnly refresh |
| S5 | Stripe webhook signature | ✅ Fait | Tester live |
| S6 | HTTPS HSTS production | ✅ nginx | Vérifier score SSL Labs |
| S7 | Secrets rotation procedure | ❌ | Document + 1 drill |

**Jalon M2 :** Staging validé checklist STAGING_VALIDATION, sécurité renforcée, Jitsi prod-ready.

---

## Mois 3 — Production publique Guinée (J61–J90)

### Produit

| # | Fonctionnalité | Détail |
|---|----------------|--------|
| P0 | Go-live domaine production | `sante.domaine.gn` |
| P0 | Stripe live (ou Orange Money MVP) | Paiement réel |
| P1 | SMS rappels RDV (API locale GN) | Partenaire telco |
| P1 | Support WhatsApp lien partage | URL stable + meta OG |
| P2 | Multi-langue (Fr + N'Ko optionnel) | i18n React |
| P2 | Mode offline partiel PWA | Cache assets |

### Technique

| # | Amélioration | Détail |
|---|--------------|--------|
| P0 | `ENABLE_PILOT_SEED=false` production | Retirer comptes démo |
| P0 | Backup off-site (S3/Backblaze) | DR complet |
| P1 | Modèle Clinic / multi-site | 1 clinique = N médecins |
| P1 | Orange Money / MTN Mobile Money | Intégration API opérateur |
| P2 | Export dossier FHIR/JSON | Interopérabilité |
| P2 | Load test (k6) 100 users | Valider capacité |
| P3 | PostgreSQL managed (option) | RDS/Supabase si scale |

### Conformité et ops

| # | Item |
|---|------|
| C1 | Politique de confidentialité + CGU publiées |
| C2 | Registre traitement données santé (Guinée) |
| C3 | Procédure incident breach (< 72 h notification) |
| C4 | Audit sécurité externe (pentest light) |

**Jalon M3 :** Production publique stable, premiers patients réels, paiement live, SLA 99 %.

---

## Dette technique (inventaire)

### Critique (traiter M1–M2)

| ID | Dette | Fichiers | Impact |
|----|-------|----------|--------|
| DT-01 | JWT en localStorage | `AuthContext`, `httpClient.js` | Vol token XSS |
| DT-02 | Duplication `/rendezvous` vs `/appointments` | `routers/rendezvous.py`, `routers/appointments.py` | Confusion API |
| DT-03 | Triple mécanisme schéma DB | `main.py` create_all + Alembic + ensure_schema | Dérive schéma |
| DT-04 | VPS non déployé au handover | infra | Dépendance PC dev |
| DT-05 | Clé Stripe test expirée | `.env.backend` | Paiements cassés |

### Important (traiter M2–M3)

| ID | Dette | Impact |
|----|-------|--------|
| DT-06 | Pydantic v1/v2 mixte | Warnings, incohérence validation |
| DT-07 | Jitsi meet.jit.si fallback | Téléconsult prod impossible |
| DT-08 | Pas de refresh token | UX re-login fréquent |
| DT-09 | Seeds/env flags dispersés | Config error-prone |
| DT-10 | Single worker uvicorn | Limite concurrence |

### Amélioration continue (M3+)

| ID | Dette | Impact |
|----|-------|--------|
| DT-11 | Stockage fichiers local vs S3+KMS | Scale + DR documents |
| DT-12 | Pas multi-tenant clinique | 1 médecin = 1 site |
| DT-13 | Mobile Money stub only | Pas paiement local GN |
| DT-14 | Pas SMS opérateur | Rappels RDV limités email |
| DT-15 | Tests E2E Playwright absents | Régressions UI |

---

## Métriques de succès (90 jours)

| Métrique | J30 | J60 | J90 |
|----------|-----|-----|-----|
| Uptime VPS | 99 % | 99.5 % | 99.9 % |
| Tests pytest pass | 100 % | 100 % | 100 % |
| Patients inscrits réels | 0 (pilote) | 20–50 | 200+ |
| Médecins actifs | 4 démo | 8–10 | 20+ |
| RDV / semaine | tests | 20+ | 100+ |
| Incidents P0 | 0 | 0 | ≤ 1 |
| Backup restore test | 1 | 2 | 4 (hebdo M3) |

---

## Répartition effort recommandée

```
Infrastructure / DevOps     ████████░░  35 %
Backend API / sécurité      ██████░░░░  25 %
Frontend UX clinique        █████░░░░░  20 %
Téléconsultation / Jitsi    ███░░░░░░░  10 %
Produit / conformité GN     ██░░░░░░░░  10 %
```

---

## Risques roadmap

| Risque | Prob. | Mitigation |
|--------|-------|------------|
| Retard VPS/domaine | Moyenne | Provisionner J1, parallel dev local |
| Stripe indisponible GN | Faible | Stub + Orange Money parallèle |
| Régulation données santé | Moyenne | Conseil juridique M2 |
| Charge dev seul | Haute | Prioriser P0 strict, reporter P3 |
| Jitsi complexité ops | Moyenne | JaaS 8x8 payant en fallback |

---

## Backlog post-90 jours (aperçu)

- Intelligence artificielle (triage symptômes, résumé consultation)
- Interopérabilité DMP national
- Application mobile native (React Native)
- Multi-pays (Côte d'Ivoire, Sénégal)
- Certification ISO 27001 / HDS équivalent

---

## Références

- État projet : [`../RAPPORT_ETAT_PROJET.md`](../RAPPORT_ETAT_PROJET.md)
- Audit engineering : [`../ENGINEERING_AUDIT_REPORT.md`](../ENGINEERING_AUDIT_REPORT.md)
- Production readiness : [`../PRODUCTION_READINESS_AUDIT_V2.md`](../PRODUCTION_READINESS_AUDIT_V2.md)
- Checklist reprise : [`CHECKLIST_REPRISE.md`](./CHECKLIST_REPRISE.md)

**Prochaine revue roadmap :** J+30 avec le propriétaire produit.
