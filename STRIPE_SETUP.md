"""
Stripe Payment Integration Setup Guide

This document explains how to set up and test Stripe payment integration for the appointment system.
"""

# Environment Variables Required

Add the following to your `.env` file:

```
# Stripe API Keys (get from https://dashboard.stripe.com/apikeys)
STRIPE_SECRET_KEY=sk_test_YOUR_SECRET_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE
```

## Getting Your Stripe Keys

1. **Create a Stripe Account**
   - Go to https://stripe.com and sign up
   - Complete your account setup

2. **Access API Keys**
   - Dashboard → Developers → API keys
   - Copy the "Secret key" (starts with `sk_test_` or `sk_live_`)
   - Paste into `STRIPE_SECRET_KEY`

3. **Get Webhook Secret**
   - Dashboard → Developers → Webhooks
   - Click "Add endpoint"
   - Endpoint URL: `https://yourdomain.com/payments/webhook`
   - Select events: `payment_intent.succeeded`, `payment_intent.payment_failed`
   - Copy the "Signing secret" and paste into `STRIPE_WEBHOOK_SECRET`

## Database Migration

Add the `payment_intent_id` column to existing database:

```sql
ALTER TABLE rendezvous ADD COLUMN payment_intent_id VARCHAR(255);
CREATE INDEX idx_rendezvous_payment_intent_id ON rendezvous(payment_intent_id);
```

Or use SQLAlchemy migration tools if available.

## API Endpoints

### Create Payment Intent
```
POST /payments/create-intent/{appointment_id}

Headers:
  Authorization: Bearer {patient_token}

Response:
{
  "client_secret": "pi_..._secret_...",
  "payment_intent_id": "pi_...",
  "amount": 50000,  # in cents
  "currency": "gnf",
  "status": "requires_payment_method"
}
```

### Webhook Endpoint
```
POST /payments/webhook

Stripe will send:
{
  "id": "evt_...",
  "type": "payment_intent.succeeded|payment_intent.payment_failed",
  "data": {
    "object": {
      "id": "pi_...",
      "status": "succeeded|requires_payment_method",
      "metadata": {
        "appointment_id": "123"
      }
    }
  }
}
```

### Check Payment Status
```
GET /payments/{appointment_id}/status

Headers:
  Authorization: Bearer {user_token}

Response:
{
  "payment_intent_id": "pi_...",
  "status": "succeeded|processing|requires_payment_method",
  "amount": 50000,
  "currency": "gnf"
}
```

## Testing Locally

### Option 1: Using Stripe CLI (Recommended)

1. **Install Stripe CLI**
   - Download from: https://stripe.com/docs/stripe-cli
   - Install for your OS

2. **Forward Webhooks to Local**
   ```bash
   stripe listen --forward-to localhost:8000/payments/webhook
   ```
   This command will output your webhook signing secret

3. **Update Environment Variable**
   - Copy the signing secret from CLI output
   - Add to `.env: STRIPE_WEBHOOK_SECRET=...`

4. **Test Payment Succeeded**
   ```bash
   stripe trigger payment_intent.succeeded
   stripe trigger payment_intent.payment_failed
   ```

### Option 2: Using Postman/cURL

1. Create a payment intent via API (get client_secret)
2. Test with Stripe test card: `4242 4242 4242 4242`
3. Manually trigger webhook events in Stripe Dashboard

## Test Cards

| Card Number | Use Case |
|------------|----------|
| 4242 4242 4242 4242 | Visa - Success |
| 4000 0025 0000 3155 | Decline - Insufficient funds |
| 4000 0000 0000 0002 | Decline - Card declined |
| 3782 822463 10005 | American Express - Success |

## Production Checklist

- [ ] Switch from test keys to live keys
- [ ] Update `STRIPE_SECRET_KEY` to live secret key (sk_live_...)
- [ ] Update webhook signing secret to live webhook secret
- [ ] Enable 3D Secure if required by your payment processor
- [ ] Test with real transactions (small amounts)
- [ ] Monitor webhook delivery in Stripe Dashboard
- [ ] Set up failure alerts in Stripe Dashboard
- [ ] Review payment reports regularly

## Troubleshooting

### "Stripe API key not configured"
- Check that `STRIPE_SECRET_KEY` is set in `.env`
- Ensure the key starts with `sk_test_` or `sk_live_`
- Restart the FastAPI application

### "Invalid webhook signature"
- Verify `STRIPE_WEBHOOK_SECRET` matches Stripe Dashboard
- Ensure webhook endpoint is exactly `https://yourdomain.com/payments/webhook`
- Check that your server is receiving the webhook request

### "Payment intent not found"
- Verify the payment intent ID exists in Stripe Dashboard
- Check that the currency matches (gnf)
- Ensure the appointment ID in metadata is correct

### Webhook Not Triggering

1. Check webhook logs in Stripe Dashboard (Developers → Webhooks)
2. Verify endpoint URL is correct and accessible
3. Check that events are being delivered (not failed attempts)
4. Review firewall/network restrictions

## Security Best Practices

✓ Never commit API keys or webhook secrets to version control
✓ Always use environment variables for secrets
✓ Verify webhook signatures on every request
✓ Log all payment events for audit trail
✓ Use HTTPS in production
✓ Implement idempotency keys for retries
✓ Monitor for failed webhooks in Stripe Dashboard
✓ Keep Stripe library updated

## API Documentation References

- Stripe API: https://stripe.com/docs/api
- Payment Intents: https://stripe.com/docs/payments/payment-intents
- Webhooks: https://stripe.com/docs/webhooks
- Signature Verification: https://stripe.com/docs/webhooks/signatures
