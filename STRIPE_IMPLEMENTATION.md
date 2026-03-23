"""
=============================================================================
STRIPE PAYMENT INTEGRATION IMPLEMENTATION SUMMARY
=============================================================================

Complete implementation of Stripe payment processing for appointments.
All business logic is properly separated into service layers.

=============================================================================
"""

## IMPLEMENTATION OVERVIEW

### Files Created:
1. services/stripe_service.py - Stripe payment operations service

### Files Modified:
1. models/rendezvous.py - Added payment_intent_id field
2. schemas/rendezvous.py - Added payment intent schemas
3. services/rendezvous_service.py - Added payment intent methods
4. routers/payments.py - New Stripe integration endpoints
5. requirements.txt - Added stripe package
6. .env.example - Environment variables template

### Files Added (Documentation):
1. STRIPE_SETUP.md - Setup and testing guide

=============================================================================
## DATABASE SCHEMA CHANGES

### RendezVous Table
```
ALTER TABLE rendezvous ADD COLUMN payment_intent_id VARCHAR(255);
CREATE INDEX idx_rendezvous_payment_intent_id ON rendezvous(payment_intent_id);
```

Fields Added:
- payment_intent_id (String, nullable): Stores Stripe payment intent ID

With Previous Implementation:
- payment_status (String): unpaid | paid
- price (Float): Appointment price

=============================================================================
## ARCHITECTURE: SERVICE LAYER SEPARATION

### StripeService (services/stripe_service.py)
Handles all Stripe-specific operations:
- Payment intent creation
- Webhook signature verification
- Webhook event processing
- Payment status retrieval
- Payment intent cancellation

Configuration:
- STRIPE_SECRET_KEY from environment
- STRIPE_WEBHOOK_SECRET for webhook verification
- Auto-validates configuration on initialization

### RendezVousService (services/rendezvous_service.py)
Business logic layer:
- create_payment_intent(appointment_id, db)
  - Validates appointment exists
  - Prevents duplicate payments
  - Fetches patient/doctor info
  - Delegates to StripeService
  
- handle_stripe_webhook(event, db)
  - Delegates to StripeService.handle_webhook_event()

### PaymentRouter (routers/payments.py)
HTTP endpoint layer:
- POST /payments/create-intent/{rdv_id} - Create payment intent
- POST /payments/webhook - Receive Stripe webhooks
- GET /payments/{rdv_id}/status - Check payment status
- POST /payments/{rdv_id}/manual-confirm - Admin manual confirmation

=============================================================================
## API ENDPOINTS

### 1. Create Payment Intent
```
POST /payments/create-intent/{rdv_id}

Authorization: Patient (can only create for own appointments)

Response:
{
  "client_secret": "pi_..._secret_...",
  "payment_intent_id": "pi_...",
  "amount": 50000,              # cents
  "currency": "gnf",
  "status": "requires_payment_method"
}

Behavior:
- Validates appointment exists
- Prevents payment if already paid
- Creates Stripe payment intent
- Stores payment_intent_id in database
- Does NOT confirm appointment yet
```

### 2. Webhook Handler
```
POST /payments/webhook

Stripe sends webhook with signature header

Processing:
1. Verifies signature using STRIPE_WEBHOOK_SECRET
2. On payment_intent.succeeded:
   - Transitions: pending → confirmed
   - Sets: payment_status = "paid"
   - Appointment ready for consultation
   
3. On payment_intent.payment_failed:
   - Sets: payment_status = "unpaid"
   - Status remains "pending"
   - Patient can retry

Returns: {"status": "received", "result": {...}}
```

### 3. Payment Status
```
GET /payments/{rdv_id}/status

Authorization: Patient (own) | Doctor (own) | Admin (any)

Response:
{
  "payment_intent_id": "pi_...",
  "status": "succeeded|processing|requires_payment_method",
  "amount": 50000,
  "currency": "gnf"
}

Note: Returns 400 if no payment intent created yet
```

### 4. Manual Payment Confirmation (Admin Only)
```
POST /payments/{rdv_id}/manual-confirm

Authorization: Admin only

Response:
{
  "id": 123,
  "status": "confirmed",
  "payment_status": "paid",
  ...
}

Use Case:
- Manual payment verification
- Off-platform payment processing
```

=============================================================================
## PAYMENT FLOW DIAGRAM

1. APPOINTMENT CREATION (Existing)
   ├─ status: "pending"
   ├─ payment_status: "unpaid"
   ├─ price: doctor.consultation_fee
   └─ payment_intent_id: null

2. INITIATE PAYMENT
   ├─ Patient: POST /payments/create-intent/{rdv_id}
   ├─ RendezVousService: validate & fetch details
   ├─ StripeService: create payment intent
   ├─ Database: store payment_intent_id
   └─ Response: client_secret for frontend

3. FRONTEND PAYMENT PROCESSING
   ├─ Use client_secret for card processing
   ├─ Stripe processes payment
   └─ Redirect to result page

4. STRIPE WEBHOOK
   └─ Stripe sends webhook for result

5A. SUCCESS WEBHOOK (payment_intent.succeeded)
    ├─ Verify signature
    ├─ Extract appointment_id from metadata
    ├─ Update: status = "confirmed"
    ├─ Update: payment_status = "paid"
    └─ Appointment ready for consultation

5B. FAILURE WEBHOOK (payment_intent.payment_failed)
    ├─ Verify signature
    ├─ Extract appointment_id from metadata
    ├─ Update: payment_status = "unpaid"
    └─ status stays "pending" (retry allowed)

=============================================================================
## SECURITY FEATURES

✓ Webhook Signature Verification
  - Uses HMAC-SHA256 algorithm
  - Compares against Stripe signature header
  - Prevents unauthorized webhook processing

✓ Environment Variables
  - STRIPE_SECRET_KEY: Hidden from code
  - STRIPE_WEBHOOK_SECRET: Hidden from code
  - Database URL: Hidden from code

✓ Access Control
  - Patients: Can only manage own appointments
  - Doctors: Can only view own appointments
  - Admins: Can manage all appointments

✓ Status Validation
  - Prevents payment if already paid
  - Validates appointment exists
  - Ensures status transitions are valid

✓ Database Transactions
  - Uses SQLAlchemy sessions
  - Automatic rollback on errors
  - Atomic updates

=============================================================================
## ENVIRONMENT VARIABLES REQUIRED

Add to .env:
```
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_SECRET_HERE
```

See .env.example for complete template.

=============================================================================
## INSTALLATION & SETUP

1. Install Dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set Environment Variables:
   ```
   # Copy .env.example to .env
   cp .env.example .env
   
   # Add your Stripe keys to .env
   # STRIPE_SECRET_KEY=sk_test_...
   # STRIPE_WEBHOOK_SECRET=whsec_...
   ```

3. Configure Database:
   ```
   # For SQLite (default):
   # Create index for payment_intent_id:
   sqlite3 sante.db "CREATE INDEX idx_rendezvous_payment_intent_id ON rendezvous(payment_intent_id);"
   
   # Or migrate using your migration tool
   ```

4. Start Application:
   ```
   python -m uvicorn main:app --reload
   ```

5. Configure Stripe Webhook:
   - Dashboard → Developers → Webhooks
   - Add endpoint: https://yourdomain.com/payments/webhook
   - Select events: payment_intent.succeeded, payment_intent.payment_failed
   - Copy signing secret to STRIPE_WEBHOOK_SECRET

=============================================================================
## TESTING LOCALLY

### Using Stripe CLI:
```bash
# Install Stripe CLI (https://stripe.com/docs/stripe-cli)

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/payments/webhook

# Output shows: webhook signing secret - add to .env

# In another terminal, trigger test events:
stripe trigger payment_intent.succeeded
stripe trigger payment_intent.payment_failed
```

### Using Test Cards:
- 4242 4242 4242 4242 - Visa (success)
- 4000 0025 0000 3155 - Visa (insufficient funds)
- 3782 822463 10005 - Amex (success)

See STRIPE_SETUP.md for complete testing guide.

=============================================================================
## ERROR HANDLING

### StripeService Errors:
- stripe.error.StripeError: API errors → HTTPException 400
- stripe.error.InvalidRequestError: Not found → HTTPException 404
- Webhook verification fails → HTTPException 401

### RendezVousService Errors:
- Appointment not found → HTTPException 404
- Payment already made → HTTPException 400
- Invalid status transition → HTTPException 400

### Router Errors:
- Missing authorization → HTTPException 403
- Invalid appointment ID → HTTPException 404
- Missing webhook secret → HTTPException 500

=============================================================================
## MONITORING & LOGGING

Stripe Dashboard:
- Developers → API logs: See all API calls
- Developers → Webhooks: See webhook delivery history
- Payments → Payment intents: Monitor pending/succeeded/failed

Application Logs:
- All StripeService calls use try/except with detailed errors
- HTTPException messages show payment-related details
- Service methods log appointment IDs for tracing

=============================================================================
## STATUS TRANSITIONS REFERENCE

### Appointment Status:
pending
  ├─ → confirmed (via payment_intent.succeeded webhook)
  └─ → cancelled (user cancellation)

confirmed
  ├─ → completed (after consultation)
  └─ → cancelled (cancellation before consultation)

### Payment Status:
unpaid
  ├─ → paid (via payment_intent.succeeded webhook)
  └─ → paid (via manual confirmation)

paid
  └─ → unpaid (admin refund/revert)

=============================================================================
## NEXT STEPS FOR PRODUCTION

1. Switch to live Stripe keys:
   - STRIPE_SECRET_KEY: sk_live_...
   - Update webhook signing secret

2. Enable 3D Secure if required
   - Dashboard → Settings → Payment methods

3. Set up Stripe alerts:
   - Dashboard → Notifications
   - Alert on webhook failures

4. Configure payment reconciliation:
   - Daily comparison of Stripe payments vs database
   - Handle out-of-sync states

5. Implement idempotency:
   - Add idempotency keys to payment intents
   - Prevent accidental duplicate charges

6. Test payment flows:
   - Use small amounts with live cards
   - Verify webhooks are received
   - Check error handling

7. Review audit trail:
   - Log all payment events
   - Monitor for suspicious patterns
   - Set up fraud detection

=============================================================================
