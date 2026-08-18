# Production Deployment Guide

**Last Updated:** April 13, 2026  
**Status:** Ready for Production Deployment

---

## Overview

This guide covers deploying the Healthcare Platform MVP to production:
- **Backend:** Render.com or Railway.app (FastAPI)
- **Frontend:** Vercel (React + Vite)
- **Database:** PostgreSQL (managed service)

---

## Prerequisites

You'll need accounts for:
- ☑️ **Render.com** or **Railway.app** (for backend)
- ☑️ **Vercel.com** (for frontend)
- ☑️ **PostgreSQL** database (Render/Railway provide managed databases)
- ☑️ **Stripe Account** (Live keys for payments)
- ☑️ **GitHub** (to connect to deployment platforms)

---

## Part 1: Backend Deployment (FastAPI)

### Option A: Deploy on Render.com (Recommended)

**Advantages:**
- Free tier available
- PostgreSQL included
- Simple GitHub integration
- Environment variables UI

#### Step 1: Prepare Backend for Production

1. Update `requirements.txt` to include production dependencies:

```bash
pip install gunicorn
pip freeze > requirements.txt
```

2. Create `Procfile` in root directory:

```
web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT
```

3. Create `.gitignore` entries (if not already present):

```
.env
*.db
__pycache__/
venv/
.venv/
```

#### Step 2: Create Render Web Service

1. Go to **render.com** and sign up
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name:** `sante-api`
   - **Region:** Choose closest to users
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT`
   - **Plan:** Starter (free tier) or higher

#### Step 3: Set Environment Variables in Render

Go to your web service → **Environment**

Add these environment variables:

```
DEBUG=False
HOST=0.0.0.0
PORT=8000
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database (Render will provide)
DATABASE_URL=postgresql://...  (generated from PostgreSQL database)

# JWT Secret (Generate strong random value)
SECRET_KEY=<generate-with-python-secrets>

# Stripe Live Keys (Get from Stripe Dashboard)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# CORS Origins (frontend domain)
FRONTEND_URL=https://your-frontend.vercel.app
```

#### Step 4: Create PostgreSQL Database

1. In Render dashboard: **New +** → **PostgreSQL**
2. Configure:
   - **Name:** `sante-db`
   - **PostgreSQL Version:** 15
   - **Region:** Same as web service
   - **Plan:** Free tier (limited) or Starter
3. Copy the connection string
4. Add to web service environment as `DATABASE_URL`

#### Step 5: Deploy

Render auto-deploys on every push to `main` branch.

**Check deployment:**
```
Backend URL: https://sante-api-xxxx.onrender.com
API Docs: https://sante-api-xxxx.onrender.com/docs
Health Check: curl https://sante-api-xxxx.onrender.com/health
```

---

### Option B: Deploy on Railway.app

**Advantages:**
- Simple Git integration
- PostgreSQL built-in
- Pay-as-you-go pricing
- Good for larger deployments

#### Step 1: Prepare Backend (same as Render)

Create `Procfile`:
```
web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT
```

#### Step 2: Create Railway Project

1. Go to **railway.app** and sign up
2. Click **New Project** → **Deploy from GitHub**
3. Select your repository
4. Railway auto-detects it's a Python project

#### Step 3: Add PostgreSQL Service

1. Click **Add Service** → **PostgreSQL**
2. Railway auto-creates connection string

#### Step 4: Set Environment Variables

In Railway dashboard → Project Settings → Variables

```
DEBUG=False
SECRET_KEY=<strong-random-value>
DATABASE_URL=${{Postgres.DATABASE_URL}}
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
FRONTEND_URL=https://your-frontend.vercel.app
```

#### Step 5: Deploy

Railway auto-deploys. Get URL from **Deployments** tab.

---

## Part 2: Frontend Deployment (Vercel)

### Deploy on Vercel

**Advantages:**
- Purpose-built for React/Vite
- Zero-config deployments
- Automatic HTTPS
- Global CDN
- Free tier available

#### Step 1: Prepare Frontend

The frontend is already configured for environment variables via `VITE_API_BASE_URL`.

Ensure `vite.config.js` is correct (should be already configured):

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
```

#### Step 2: Deploy on Vercel

1. Go to **vercel.com** and sign up with GitHub
2. Click **Import Project**
3. Select your repository (github.com/yourname/plateforme-sante-guinee)
4. Configure:
   - **Project Name:** `sante-frontend` or similar
   - **Framework Preset:** Vite
   - **Root Directory:** `./frontend-sante/frontend`
5. Click **Deploy**

#### Step 3: Set Environment Variables in Vercel

After first deploy, go to **Project Settings** → **Environment Variables**

Add:
```
VITE_API_BASE_URL=https://sante-api-xxxx.onrender.com
```

(Use the backend URL from Render/Railway)

#### Step 4: Trigger Redeploy

After setting environment variables, trigger a redeploy:
- Push to `main` branch, OR
- Click **Redeploy** in Vercel dashboard

**Check deployment:**
```
Frontend URL: https://sante-frontend-xxx.vercel.app
```

---

## Part 3: Connect Frontend to Backend

### Update CORS in Backend

In `main.py`, update the CORS origins:

```python
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://sante-frontend-xxx.vercel.app",  # Your Vercel URL
]
```

Redeploy backend after updating.

---

## Part 4: Production Configuration Checklist

### Backend Requirements

- [x] `Procfile` created
- [x] `requirements.txt` includes `gunicorn`
- [x] `.env` NOT committed (only `.env.example`)
- [x] `SECRET_KEY` is strong random value
- [x] Database URL points to PostgreSQL
- [x] Stripe Live keys configured
- [x] CORS origins updated
- [x] DEBUG=False set
- [x] Database migrations applied

### Frontend Requirements

- [x] `VITE_API_BASE_URL` environment variable configured
- [x] Build command: `npm run build`
- [x] Output directory: `dist`
- [x] `vercel.json` created (optional, for advanced config)

### Security Checklist

- [x] HTTPS enforced (automatic on Vercel/Render)
- [x] No credentials in code
- [x] Environment variables for all secrets
- [x] Database backups enabled
- [x] CORS restricted to known domains
- [x] Stripe Webhook signature validation in code
- [x] JWT token validation on all endpoints

---

## Part 5: Stripe Webhook Configuration

### Update Stripe Webhook Endpoint

1. Go to **Stripe Dashboard** → **Webhooks**
2. Create new webhook endpoint:
   - **URL:** `https://your-backend-url.com/payments/webhook`
   - **Events:** `checkout.session.completed`
3. Copy the webhook secret
4. Add to backend environment as `STRIPE_WEBHOOK_SECRET`

---

## Part 6: Database Migration (Production)

When you first deploy with PostgreSQL backend:

```bash
# Run from local machine or deployment logs
alembic upgrade head
```

Or if using SQLite migration:

```bash
# Manually run database init
python -c "
from database import engine, Base
import models
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
```

---

## Part 7: Post-Deployment Verification

### Test Backend

```bash
# Health check
curl https://sante-api-xxxx.onrender.com/

# API docs
curl https://sante-api-xxxx.onrender.com/docs

# Test login
curl -X POST https://sante-api-xxxx.onrender.com/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=123456"
```

### Test Frontend

```bash
# Visit in browser
https://sante-frontend-xxx.vercel.app

# Check browser DevTools Console for errors
# Try login to verify backend connection works
```

### Test Payment Flow

1. Go to frontend
2. Create appointment
3. Attempt payment
4. Check Stripe webhook logs for `checkout.session.completed`

---

## Part 8: Troubleshooting

### Backend Won't Start on Render

**Issue:** "gunicorn: command not found"

**Solution:**
```bash
pip install gunicorn
pip freeze > requirements.txt
git push  # Redeploy
```

### Frontend Can't Connect to Backend

**Issue:** CORS error or 404 in browser console

**Solution:**
1. Check `VITE_API_BASE_URL` is correct in Vercel environment
2. Verify backend CORS includes frontend URL
3. Check backend is actually running: `curl backend-url/docs`

### Database Connection Error

**Issue:** "psycopg2.OperationalError"

**Solution:**
```
1. Verify DATABASE_URL is correct
2. Ensure PostgreSQL is running (Render/Railway)
3. Check credentials in connection string
4. Run migrations: alembic upgrade head
```

### Stripe Webhook Not Firing

**Issue:** Payments created but status not updating

**Solution:**
1. Check `STRIPE_WEBHOOK_SECRET` is correct
2. Verify webhook endpoint URL in Stripe dashboard
3. Check logs for webhook errors
4. Test webhook from Stripe dashboard

---

## Part 9: Maintenance & Monitoring

### Daily Tasks

- Monitor error logs in Render/Railway/Vercel
- Check database backup status
- Test login from different browsers

### Weekly Tasks

- Review Stripe transaction logs
- Check payment webhook delivery status
- Monitor database size growth

### Monthly Tasks

- Review server logs for errors/warnings
- Check for dependency updates
- Refresh SSL certificates (automatic on Vercel/Render)

### Quarterly Tasks

- Security audit of environment variables
- Database optimization/cleanup
- Update dependencies (pip install --upgrade)

---

## Part 10: Cost Estimates

### Free Tier Usage

| Service | Free Tier | Cost If Exceeded |
|---------|-----------|-----------------|
| Render WEB | $0 (sleeps after 15 min inactivity) | $7/month |
| Render DB | $0 (limited) | $15/month |
| Vercel | $0 | $20/month |
| Stripe | $0 | 2.9% + $0.30 per transaction |

### Recommended Production Plan

| Service | Plan | Cost/Month |
|---------|------|-----------|
| Render WEB | Starter | $7 |
| Render DB | Starter | $15 |
| Vercel | Pro | $20 |
| **Total** | | **~$42** |

Plus Stripe transaction fees (2.9% + $0.30 per payment)

---

## Quick Deployment Checklist

```
PRE-DEPLOYMENT:
[ ] Generate strong SECRET_KEY
[ ] Get Stripe Live keys
[ ] Prepare PostgreSQL connection string
[ ] Update CORS origins in main.py
[ ] Create .env.example with all variables
[ ] Commit all changes to git

BACKEND DEPLOYMENT:
[ ] Create Procfile
[ ] pip install gunicorn + freeze
[ ] Deploy to Render/Railway
[ ] Set all environment variables
[ ] Create PostgreSQL database
[ ] Run migrations
[ ] Test API at /docs
[ ] Update Stripe webhook URL

FRONTEND DEPLOYMENT:
[ ] Deploy to Vercel
[ ] Set VITE_API_BASE_URL in Vercel
[ ] Trigger redeploy
[ ] Test frontend connects to backend
[ ] Test login flow
[ ] Test appointment creation

POST-DEPLOYMENT:
[ ] Test full payment flow
[ ] Monitor error logs
[ ] Verify SSL/HTTPS working
[ ] Test mobile responsiveness
[ ] Load testing with concurrent users
```

---

## Getting Help

- **Render Docs:** https://render.com/docs
- **Railway Docs:** https://docs.railway.app
- **Vercel Docs:** https://vercel.com/docs
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment/
- **Stripe Webhooks:** https://stripe.com/docs/webhooks

---

**Next Steps:**

1. ✅ Read this guide completely
2. ✅ Create accounts on Render/Railway and Vercel
3. ✅ Generate strong SECRET_KEY
4. ✅ Get Stripe Live keys
5. ✅ Follow "Quick Deployment Checklist" above

Good luck! 🚀
