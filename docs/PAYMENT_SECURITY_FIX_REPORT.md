# Rapport de correction — Paiement fictif `confirm-payment` (audit #2)

**Date :** 2026-05-25  
**Statut :** Corrigé — validé par tests automatisés et tentative d’exploitation  
**Périmètre :** faille #2 uniquement

---

## 1. Vérification indépendante — la faille existait encore

**Oui.** Avant correction, `POST /payments/{id}/confirm-payment` exécutait :

```python
appointment.payment_status = "paid"
appointment.status = "confirmed"
db.commit()
```

sans appel Stripe, sans webhook, sans enregistrement de preuve de paiement. Le frontend patient (`Appointments.jsx`) appelait `paymentsAPI.confirmPayment(appointment.id)` après la modale « Confirmer le paiement ».

Un second chemin `/rendezvous/{id}/confirm-payment` permettait aussi aux **patients** d’appeler `confirm_appointment_after_payment` sans preuve.

---

## 2. Scénario d’exploitation réel

| Étape | Action attaquant | Résultat (avant) |
|-------|------------------|------------------|
| 1 | Créer un compte patient (`POST /auth/register`) | 201 |
| 2 | Réserver un RDV téléconsultation 45 000 GNF (`POST /appointments/`) | `pending` / `unpaid` |
| 3 | `POST /payments/{id}/confirm-payment` avec JWT patient, **sans payer** | 200 → `paid` + `confirmed` |
| 4 | Ouvrir la salle Jitsi / consultation | Accès selon règles métier |

**Impact :** consultation confirmée et potentiellement téléconsultation sans encaissement.

---

## 3. Impact financier

| Dimension | Estimation |
|-----------|------------|
| **Par incident** | 100 % du tarif du RDV (ex. 45 000 GNF ≈ 5 € selon change) |
| **Échelle** | Tout patient authentifié, automatisable (script / Burp) |
| **Récurrent** | Chaque RDV `pending` jusqu’à correction |
| **Risque clinique** | File d’attente médecin encombrée de RDV « payés » fictifs |
| **Conformité** | Rupture piste d’audit trésorerie / anti-fraude |

**Criticité :** **Critique** (fraude directe, pas besoin de privilèges admin).

---

## 4. Architecture cible

```
Patient production
  → POST /payments/create-intent
  → Stripe Checkout (hosted)
  → redirect /success?session_id=...
  → POST /payments/confirm-checkout  ──► Stripe API retrieve (paid?)
       └── PaymentSettlementService (channel=stripe_checkout)

Stripe
  → POST /payments/webhook (signature HMAC)
       └── PaymentSettlementService (channel=stripe_webhook)

Admin trésorerie
  → POST /payments/{id}/manual-confirm
       └── PaymentSettlementService (channel=admin_manual)

Dev/UAT uniquement (non production)
  → POST /payments/{id}/confirm-payment + X-Payment-Stub-Token
       └── PaymentSettlementService (channel=dev_stub)
```

**Principes :**

1. **Single settlement service** — `PaymentSettlementService.settle_appointment`
2. **Canaux explicites** — `core/payment_policy.py`
3. **Stub jamais en production** — `is_stub_settlement_allowed()` → `False` si `ENVIRONMENT=production`
4. **Piste d’audit** — table `payments` mise à jour (`payment_id`, `status=paid`)
5. **Frontend** — hors mode démo : redirection Stripe Checkout, plus de `confirm-payment` nu

---

## 5. Fichiers modifiés

| Fichier | Rôle |
|---------|------|
| `core/payment_policy.py` | Politique canaux + token stub |
| `services/payment_settlement.py` | Règlement centralisé |
| `services/stripe_service.py` | Délégation settlement Stripe |
| `services/rendezvous_service.py` | `confirm_appointment_after_payment` exige un canal |
| `routers/payments.py` | `confirm-payment` stub gated ; `manual-confirm` via settlement |
| `routers/rendezvous.py` | `confirm-payment` admin seulement |
| `frontend/.../Appointments.jsx` | Stripe Checkout ou stub token |
| `frontend/.../api.js` | Header stub optionnel |
| `tests/test_payment_settlement_security.py` | Régression sécurité |
| Scripts E2E | Header `X-Payment-Stub-Token` si configuré |

---

## 6. Variables d’environnement

| Variable | Production | Dev/UAT |
|----------|------------|---------|
| `STRIPE_SECRET_KEY` | Requis | Requis pour checkout réel |
| `STRIPE_WEBHOOK_SECRET` | Requis | Requis pour webhooks |
| `ALLOW_STUB_PAYMENT` | **Interdit / ignoré** | `true` pour démo locale |
| `PAYMENT_STUB_TOKEN` | Non défini | Secret fort partagé backend + `VITE_PAYMENT_STUB_TOKEN` |
| `VITE_ENABLE_PAYMENT_SIMULATION` | `false` | `true` pour UI démo |

---

## 7. Tests

```bash
python -m pytest tests/test_payment_settlement_security.py -q
# 8 passed
```

Couverture :

- `confirm-payment` sans token → **403**
- Token stub invalide → **403**
- RDV reste `unpaid` après échec
- Token stub valide (dev) → **200** + enregistrement `payments`
- Patient `/rendezvous/.../confirm-payment` → **403**
- Admin `manual-confirm` → **200**
- Stub bloqué si `ENVIRONMENT=production`

---

## 8. Preuve post-correction (exploit bloqué)

Requête identique à l’attaque (sans header stub) :

```
POST /payments/{id}/confirm-payment
Authorization: Bearer <patient>
→ HTTP 403
→ payment_status reste unpaid
```

Avec stub valide uniquement en dev (`ALLOW_STUB_PAYMENT=true`, non-production) :

```
X-Payment-Stub-Token: <PAYMENT_STUB_TOKEN>
→ HTTP 200 (attendu en UAT)
```

---

## 9. Contournements tentés après correction

| Vecteur | Résultat |
|---------|----------|
| `confirm-payment` sans header | **403** |
| Mauvais stub token | **403** |
| `/rendezvous/confirm-payment` patient | **403** |
| `manual-confirm` patient | **403** (admin only) |
| Settlement service canal `dev_stub` sans token | **403** |
| Stub en `ENVIRONMENT=production` | **403** même avec token |
| Admin `manual-confirm` | **200** (voulu — ops) |

**Résidu ops :** un admin malveillant peut toujours `manual-confirm` — contrôle de gouvernance / double validation trésorerie recommandé (hors #2).

---

## 10. Certification

**La faille #2 (paiement fictif via API publique patient) est corrigée** pour un déploiement production standard (Stripe + pas de stub).

**Conditions :**

- Ne pas activer `ALLOW_STUB_PAYMENT` en production.
- Configurer webhooks Stripe et `confirm-checkout` après Checkout.
- E2E locaux : définir `PAYMENT_STUB_TOKEN` + header dans scripts.
