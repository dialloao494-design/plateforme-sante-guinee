# Stripe Payment Integration - Quick Reference

## Endpoints

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| POST | `/payments/create-intent/{rdv_id}` | Create Stripe payment intent | Patient |
| POST | `/payments/webhook` | Receive Stripe webhooks | None (signature verified) |
| GET | `/payments/{rdv_id}/status` | Check payment status | Patient/Doctor/Admin |
| POST | `/payments/{rdv_id}/manual-confirm` | Manual payment confirmation | Admin |

## Payment Intent Flow

```
1. POST /payments/create-intent/{rdv_id}
   ↓ (Returns client_secret)
2. Frontend uses client_secret for card payment
   ↓ (Stripe processes)
3. Stripe sends webhook to /payments/webhook
   ↓ (Signature verified, appointment_id extracted)
4. On success → appointment confirmed + paid
   On failure → payment marked unpaid
```

## Headers

Authentication for protected endpoints:
```
Authorization: Bearer {jwt_token}
```

For webhook (Stripe sends):
```
stripe-signature: t={timestamp},v1={signature}
```

## Test Credentials

- API Key: `sk_test_...` (from Stripe Dashboard)
- Webhook Secret: `whsec_...` (from Stripe Dashboard)
- Test Card: `4242 4242 4242 4242`

## Webhook Events

| Event | Action | Result |
|-------|--------|--------|
| `payment_intent.succeeded` | Confirm appointment | status: confirmed, payment_status: paid |
| `payment_intent.payment_failed` | Mark failed | payment_status: unpaid, status: pending |

## Database Fields

```sql
-- Appointment table (rendezvous)
payment_intent_id VARCHAR(255)   -- Stripe payment intent ID
payment_status VARCHAR(50)       -- unpaid, paid
price FLOAT                      -- Appointment price
status VARCHAR(50)               -- pending, confirmed, completed, cancelled
```

## Environment Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_WEBHOOK_SECRET=whsec_...

# 3. Or copy .env.example and edit
cp .env.example .env
# Edit .env with your Stripe keys

# 4. For local testing with Stripe CLI
stripe listen --forward-to localhost:8000/payments/webhook
```

## Common Issues

| Error | Solution |
|-------|----------|
| Stripe API key not configured | Set STRIPE_SECRET_KEY in .env |
| Invalid webhook signature | Verify STRIPE_WEBHOOK_SECRET matches Stripe Dashboard |
| Payment intent not found | Check appointment ID in metadata |
| Access denied | Verify user owns the appointment |

## Response Examples

### Create Payment Intent
```json
{
  "client_secret": "pi_1234567890_secret_abcdef12345",
  "payment_intent_id": "pi_1234567890",
  "amount": 50000,
  "currency": "gnf",
  "status": "requires_payment_method"
}
```

### Check Payment Status
```json
{
  "payment_intent_id": "pi_1234567890",
  "status": "succeeded",
  "amount": 50000,
  "currency": "gnf"
}
```

### Webhook Response
```json
{
  "status": "received",
  "result": {
    "status": "success",
    "event": "payment_intent.succeeded",
    "appointment_id": "123",
    "message": "Appointment confirmed after payment"
  }
}
```

## Testing with cURL

### Create Payment Intent
```bash
curl -X POST http://localhost:8000/payments/create-intent/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

### Check Status
```bash
curl -X GET http://localhost:8000/payments/1/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Trigger Test Webhook (with Stripe CLI)
```bash
stripe trigger payment_intent.succeeded
stripe trigger payment_intent.payment_failed
```

## Stripe Dashboard Links

- API Keys: https://dashboard.stripe.com/apikeys
- Webhooks: https://dashboard.stripe.com/webhooks
- Payment Intents: https://dashboard.stripe.com/payments
- Test Cards: https://stripe.com/docs/testing

## File Locations

```
services/stripe_service.py        -- Stripe operations
services/rendezvous_service.py    -- Payment intent methods (create_payment_intent, handle_stripe_webhook)
routers/payments.py               -- Payment endpoints
models/rendezvous.py              -- payment_intent_id field
schemas/rendezvous.py             -- PaymentIntentResponse schema
requirements.txt                  -- stripe package
.env.example                      -- Environment template
STRIPE_SETUP.md                   -- Setup guide
STRIPE_IMPLEMENTATION.md          -- Complete documentation
```
