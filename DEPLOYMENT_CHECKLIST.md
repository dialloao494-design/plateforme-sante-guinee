# Production Deployment Checklist

**Project:** Healthcare Platform MVP  
**Date Started:** April 13, 2026

---

## Phase 1: Pre-Deployment Preparation

### Environment & Code

- [ ] All dependencies in `requirements.txt` (gunicorn, psycopg2)
- [ ] `Procfile` created and committed
- [ ] `.env` file NOT in git (only `.env.example`)
- [ ] All code committed to `main` branch
- [ ] No console.error or TODO comments in critical paths
- [ ] All environment variables documented in `.env.production.example`

### Security

- [ ] Generated strong `SECRET_KEY` using `generate_secrets.py`
- [ ] Stripe account created and verified
- [ ] Live Stripe keys obtained (sk_live_*, pk_live_*)
- [ ] No database passwords in code (only via environment)
- [ ] No API keys hardcoded (all from .env)
- [ ] CORS origins will be restricted to known domains

### Database

- [ ] Tested with PostgreSQL locally (optional but recommended)
- [ ] Verified SQLAlchemy works with `postgresql://` URL
- [ ] `alembic` migrations ready (if using)
- [ ] Database backup strategy documented

---

## Phase 2: Backend Deployment

### Render/Railway Setup

- [ ] Created account on Render.com or Railway.app
- [ ] Authenticated with GitHub
- [ ] Repository connected to deployment platform
- [ ] Web service created and building

### Database Setup

- [ ] PostgreSQL database created
- [ ] Database connection string verified
- [ ] Connection string matches `DATABASE_URL` format

### Environment Variables

Set in backend deployment platform:

```
Backend Environment Variables:
[ ] DEBUG = False
[ ] HOST = 0.0.0.0
[ ] PORT = 8000
[ ] ALGORITHM = HS256
[ ] ACCESS_TOKEN_EXPIRE_MINUTES = 60
[ ] DATABASE_URL = postgresql://...
[ ] SECRET_KEY = generated_strong_random_value
[ ] STRIPE_SECRET_KEY = sk_live_...
[ ] STRIPE_WEBHOOK_SECRET = whsec_...
[ ] STRIPE_PUBLISHABLE_KEY = pk_live_...
[ ] FRONTEND_URL = https://sante-frontend-xxx.vercel.app
```

### Verification

- [ ] Backend URL obtained: `https://sante-api-xxxx.onrender.com`
- [ ] API docs accessible: `https://sante-api-xxxx.onrender.com/docs`
- [ ] API responds to health check: `curl https://backend-url/docs`
- [ ] No 500 errors in logs

---

## Phase 3: Frontend Deployment

### Vercel Setup

- [ ] Created account on Vercel.com
- [ ] Authenticated with GitHub
- [ ] Repository imported to Vercel
- [ ] Root directory set to `frontend-sante/frontend`

### Environment Variables

Set in Vercel project:

```
Frontend Environment Variables:
[ ] VITE_API_BASE_URL = https://sante-api-xxxx.onrender.com
```

### Verification

- [ ] Frontend URL obtained: `https://sante-frontend-xxx.vercel.app`
- [ ] Frontend loads without errors (check DevTools Console)
- [ ] Login page visible and functional

---

## Phase 4: Integration Testing

### Authentication

- [ ] Can log in with test credentials
  - Email: test.patient@example.com
  - Password: 123456
- [ ] JWT token received and stored in localStorage
- [ ] Can navigate to authenticated pages
- [ ] Can log out successfully

### Appointments

- [ ] Can view appointments (GET /appointments)
- [ ] Can create new appointment (POST /appointments)
- [ ] Can update appointment status (PUT /appointments/{id})
- [ ] Can delete appointment (DELETE /appointments/{id})
- [ ] Conflict validation works (can't book same slot)

### Payments

- [ ] Can initiate payment (POST /payments/create-intent)
- [ ] Stripe Checkout modal appears
- [ ] Can complete Stripe test payment
  - Card: 4242 4242 4242 4242
  - Expiry: any future date
  - CVC: any 3 digits
- [ ] Payment confirmed in backend
- [ ] Appointment marked as paid

### Error Handling

- [ ] 401 errors redirect to login
- [ ] 403 errors show appropriate messages
- [ ] Network errors show retry options
- [ ] API errors display user-friendly messages

---

## Phase 5: Stripe Configuration

### API Keys

- [ ] Live Secret Key copied to backend env
- [ ] Live Publishable Key in frontend env (optional, can be constant)
- [ ] Webhook secret copied to backend env

### Webhook

- [ ] Webhook endpoint created: `https://backend-url/payments/webhook`
- [ ] Events selected: `checkout.session.completed`
- [ ] Webhook secret verified and stored
- [ ] Test webhook sent and verified

### Testing

- [ ] Test payment completed successfully
- [ ] Webhook fired and appointment status updated
- [ ] Email confirmation received (if configured)

---

## Phase 6: CORS Configuration

### Backend

- [ ] Updated `main.py` with frontend URL
- [ ] Committed and pushed changes
- [ ] Backend auto-deployed with new CORS origin

### Testing

- [ ] No CORS errors in browser console
- [ ] API requests from frontend succeed
- [ ] Pre-flight requests work properly

---

## Phase 7: Security & Monitoring

### Security

- [ ] All secrets in environment variables (not code)
- [ ] HTTPS enabled (automatic on Vercel/Render)
- [ ] JWT tokens validated on all protected routes
- [ ] No sensitive data in error messages
- [ ] Database backups configured

### Monitoring

- [ ] Error logs accessible and reviewed
- [ ] Performance metrics visible
- [ ] Deployment logs reviewed for warnings

---

## Phase 8: Post-Deployment

### Testing Checklist

Run through complete user journeys:

```
Patient Journey:
[ ] Sign up as new patient
[ ] Log in
[ ] Browse available doctors
[ ] Create appointment
[ ] Pay for appointment
[ ] View appointment status
[ ] Cancel appointment

Doctor Journey:
[ ] Log in as doctor
[ ] View my appointments
[ ] View list of patients
[ ] Manage availability

Admin Journey:
[ ] Log in as admin
[ ] View all users
[ ] View all appointments
[ ] Manage system
```

### Documentation

- [ ] Updated `.env.production.example` with real settings
- [ ] Deployment URLs documented
- [ ] Emergency contacts documented
- [ ] Backup/restore procedures documented

### Backup & Recovery

- [ ] Database backup enabled
- [ ] Backup schedule verified
- [ ] Restore procedure tested
- [ ] Backup retention policy set

---

## Phase 9: Launch Readiness

### Final Checks

- [ ] All tests pass
- [ ] No console errors
- [ ] All environment variables set correctly
- [ ] Stripe live mode active
- [ ] Database populated with seed data
- [ ] Performance acceptable (sub-2 second page loads)

### Monitoring Setup

- [ ] Error tracking enabled (optional: Sentry)
- [ ] Uptime monitoring configured (optional: StatusPage)
- [ ] Log aggregation enabled (optional: Papertrail)
- [ ] Alert notifications configured

### Documentation

- [ ] README updated with production URLs
- [ ] Deployment guide reviewed
- [ ] Troubleshooting guide prepared
- [ ] Team trained on deployment process

---

## Phase 10: Go Live

### Pre-Launch

- [ ] Communicate launch to stakeholders
- [ ] Prepare status page
- [ ] Setup on-call monitoring
- [ ] Final smoke tests in production

### Launch Day

- [ ] Monitor error logs closely
- [ ] Check payment processing
- [ ] Verify email notifications (if any)
- [ ] Monitor database performance

### Post-Launch

- [ ] Collect user feedback
- [ ] Monitor performance metrics
- [ ] Address any issues immediately
- [ ] Plan for first update/patch

---

## URL Reference Sheet

### Production URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | https://sante-frontend-xxx.vercel.app | User interface |
| Backend | https://sante-api-xxxx.onrender.com | API server |
| API Docs | https://sante-api-xxxx.onrender.com/docs | Swagger documentation |
| Stripe Dashboard | https://dashboard.stripe.com | Payments management |

### Environment Variables Summary

**Backend (Render/Railway):**
```env
DEBUG=False
SECRET_KEY=<strong-random-value>
DATABASE_URL=<postgres-connection>
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
FRONTEND_URL=https://sante-frontend-xxx.vercel.app
```

**Frontend (Vercel):**
```env
VITE_API_BASE_URL=https://sante-api-xxxx.onrender.com
```

---

## Rollback Plan

If deployment has critical issues:

### Quick Rollback

1. **Frontend:** Vercel auto-reverts via one-click
2. **Backend:** Render/Railway auto-reverts via one-click
3. **Database:** Restore from backup if corrupted

### Emergency Contacts

| Role | Contact | Responsibility |
|------|---------|-----------------|
| Backend Admin | - | Monitor and maintain APIs |
| Frontend Admin | - | Monitor and maintain UI |
| Database Admin | - | Database backups and maintenance |

---

## Completion Status

| Phase | Status | Completed On |
|-------|--------|--------------|
| 1: Preparation | [ ] Pending | |
| 2: Backend | [ ] Pending | |
| 3: Frontend | [ ] Pending | |
| 4: Integration | [ ] Pending | |
| 5: Stripe | [ ] Pending | |
| 6: CORS | [ ] Pending | |
| 7: Security | [ ] Pending | |
| 8: Post-Deploy | [ ] Pending | |
| 9: Ready | [ ] Pending | |
| 10: Live | [ ] Pending | |

---

## Notes & Observations

(Document any issues, decisions, or observations during deployment)

```
[Space for deployment notes]
```

---

**Last Updated:** April 13, 2026  
**Next Review:** After launch

---

## Quick Links

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Detailed guide
- [DEPLOYMENT_STEPS.md](DEPLOYMENT_STEPS.md) - Step-by-step walkthrough
- [.env.production.example](.env.production.example) - Production environment template
- [Procfile](Procfile) - Web server configuration
- [generate_secrets.py](generate_secrets.py) - Secret key generator
