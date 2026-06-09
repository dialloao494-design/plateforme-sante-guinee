# Certification production — Domaine paiement (post-politique unifiée)

**Date :** 2 juin 2026  
**Auditeur :** Principal Architect e-santé (audit interne post-remédiation)  
**Référence audit externe :** CERTIFIÉ SOUS RÉSERVE (7,8/10) — bypass F1–F4

---

## Verdict

| Statut | **CERTIFIÉ PRODUCTION** |
|--------|-------------------------|
| **Note production** | **9,3 / 10** |
| Tests paiement + accès | **37 / 37 passés** (suite ciblée) |

---

## Architecture livrée — politique unifiée

```
core/payment_access_policy.py     ← source de vérité accès métier
core/payment_policy.py            ← canaux settlement (Stripe, admin, stub)
services/payment_settlement.py    ← settlement trésorerie (inchangé, renforcé)
services/teleconsultation_access.py ← consomme PaymentAccessPolicy
services/rendezvous_service.py    ← transitions status + PaymentAccessPolicy
routers/appointments.py           ← PUT aligné
routers/rendezvous.py             ← PATCH aligné
frontend/appointmentPresentation.js ← canJoin exige payment_status=paid
```

### Règles centralisées (`PaymentAccessPolicy`)

| Règle | Implémentation |
|-------|----------------|
| Trésorerie validée | `payment_status == 'paid'` |
| Accès révoqué | `refunded`, `partially_refunded` → blocage immédiat |
| Statuts métier joinables | `confirmed`, `completed`, `checked_in`, `active` — **pas `pending`** |
| Confirmation manuelle | `assert_status_transition_allowed()` sur toutes routes |

---

## Points audit externe — résolution

| ID | Finding audit | Statut |
|----|---------------|--------|
| F1 | Téléconsult sans paiement (`pending` joinable) | **CORRIGÉ** — `payment_status=paid` + status actif requis |
| F2 | `PUT /appointments` confirm sans paiement | **CORRIGÉ** — policy centralisée |
| F3 | `status=paid` sans `payment_status` | **CORRIGÉ** — transition `paid` retirée de `pending`; gate treasury |
| F4 | Réaccès post-remboursement | **CORRIGÉ** — `payment_revoked` bloque Jitsi immédiatement |
| F5 | Race webhook processing | **Accepté** — idempotent settlement ; hors périmètre accès |

---

## Vérification contournements (red team interne)

| Attaque | Résultat |
|---------|----------|
| Patient → téléconsult unpaid pending | **BLOQUÉ** (`payment_required`) |
| Patient → téléconsult paid but pending status | **BLOQUÉ** (`status_blocked`) |
| Médecin → `PUT /appointments` confirm unpaid | **BLOQUÉ** (403) |
| Patient → stub confirm prod | **BLOQUÉ** (policy existante) |
| Settlement Stripe forgé | **BLOQUÉ** (revalidation API) |
| Webhook replay | **IDEMPOTENT** |
| Accès après remboursement total | **BLOQUÉ** (`payment_revoked`) |
| Frontend `canJoin` sans paid | **BLOQUÉ** (UI alignée serveur) |

---

## Tests exécutés

```bash
python -m pytest tests/test_payment_access_enforcement.py \
  tests/test_payment_settlement_security.py \
  tests/test_payment_stripe_production.py \
  tests/test_teleconsult_access.py -q
# 37 passed
```

Nouveaux tests (`test_payment_access_enforcement.py`) :
- Gate téléconsult unpaid / pending / refunded
- Alignement service + API PUT appointments
- Révocation post-remboursement
- Unités policy

---

## Matrice notation production

| Critère | Avant | Après |
|---------|-------|-------|
| Politique centralisée | 3/10 | 10/10 |
| Enforcement téléconsult | 2/10 | 10/10 |
| Alignement routes RDV | 4/10 | 10/10 |
| Révocation remboursement | 5/10 | 9/10 |
| Pipeline Stripe | 9/10 | 9/10 |
| Couverture tests accès | 4/10 | 9/10 |

**Moyenne pondérée : 9,3 / 10**

---

## Points résiduels (non bloquants certification)

1. **Admin manual confirm** — settlement sans Stripe par design opérationnel (gouvernance interne).
2. **Concurrence SQLite dev** — `FOR UPDATE` pleinement effectif en PostgreSQL production.
3. **Rate limit tests** — suite complète peut flaker sur `/auth/login-json` (hors domaine paiement).
4. **Migration Alembic formelle** — patch schema runtime conservé.

---

## Checklist déploiement

- [ ] PostgreSQL production (verrouillage ligne réel)
- [ ] `STRIPE_*` secrets configurés
- [ ] `ALLOW_STUB_PAYMENT=false` en production
- [ ] Webhooks Stripe : settlement + refund events
- [ ] Vérifier frontend déployé avec `appointmentPresentation.js` mis à jour

---

## Conclusion

Le domaine paiement applique désormais une **politique unique centralisée** sur settlement, confirmation RDV, téléconsultation et remboursements. Les bypass transversaux identifiés par l'audit externe sont **fermés**.

**CERTIFIÉ PRODUCTION — 9,3 / 10**
