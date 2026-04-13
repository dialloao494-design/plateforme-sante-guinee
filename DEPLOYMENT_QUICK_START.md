# Production Deployment - Quick Start

**Status:** ✅ READY FOR DEPLOYMENT

**What You'll Have After Deployment:**
- ✅ Public frontend at https://sante-frontend-xxx.vercel.app
- ✅ Public API at https://sante-api-xxxx.onrender.com
- ✅ Working payments with Stripe
- ✅ Managed PostgreSQL database
- ✅ HTTPS everywhere (automatic)

---

## 📝 What Was Created For You

### Configuration Files

1. **`Procfile`** - Web server startup command for Render/Railway
2. **`.env.production.example`** - Template for production environment variables
3. **`vercel.json`** - Vercel configuration (minimal, mostly defaults)
4. **`requirements.txt`** - Updated with gunicorn + psycopg2

### Documentation Files

1. **`DEPLOYMENT_STEPS.md`** ⭐ **START HERE** - Step-by-step walkthrough (30-45 min)
2. **`DEPLOYMENT_GUIDE.md`** - Detailed reference guide
3. **`DEPLOYMENT_CHECKLIST.md`** - Complete verification checklist

### Helper Script

1. **`generate_secrets.py`** - Generates secure JWT secret keys

---

## ⚡ Quick Start (TL;DR)

### 1. Generate Secret (2 minutes)

```bash
python generate_secrets.py
# Copy the SECRET_KEY value
```

### 2. Deploy Backend (10 minutes)

- Go to Render.com (or Railway.app)
- Connect GitHub repo
- Create Web Service + PostgreSQL
- Set environment variables (SECRET_KEY + Stripe keys)
- Get backend URL: `https://sante-api-xxxx.onrender.com`

### 3. Deploy Frontend (5 minutes)

- Go to Vercel.com
- Import GitHub repo
- Set root to `frontend-sante/frontend`
- Set `VITE_API_BASE_URL` = your backend URL
- Get frontend URL: `https://sante-frontend-xxx.vercel.app`

### 4. Update CORS (2 minutes)

- Edit `main.py`
- Add frontend URL to `allowed_origins`
- Commit and push (auto-redeploy)

### 5. Configure Stripe (5 minutes)

- Get live keys from Stripe Dashboard
- Add to backend environment variables
- Create webhook: backend-url/payments/webhook

### 6. Test (5 minutes)

- Log in to frontend
- Create appointment
- Complete Stripe test payment
- Verify success

**Total Time: ~30-45 minutes**

---

## 📚 Detailed Documentation

### For Complete Step-by-Step Instructions:
👉 **Read:** [DEPLOYMENT_STEPS.md](DEPLOYMENT_STEPS.md)

### For Reference & Troubleshooting:
👉 **Read:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

### For Verification After Deployment:
👉 **Use:** [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

---

## 🔑 Environment Variables You'll Need

### From Stripe Dashboard

| Variable | Example | Where to Get |
|----------|---------|--------------|
| `STRIPE_SECRET_KEY` | sk_live_... | Stripe > Developers > API Keys |
| `STRIPE_PUBLISHABLE_KEY` | pk_live_... | Stripe > Developers > API Keys |
| `STRIPE_WEBHOOK_SECRET` | whsec_... | Stripe > Webhooks > Create Endpoint |

### Generated Locally

| Variable | Example | How to Get |
|----------|---------|-----------|
| `SECRET_KEY` | Random 32 chars | `python generate_secrets.py` |

### Provided by Platform

| Variable | Example | Platform |
|----------|---------|----------|
| `DATABASE_URL` | postgresql://user:pass@host:5432/db | Render/Railway (auto) |

---

## 🎯 Deployment Platforms Recommended

### Backend ⭕
Choose ONE:

| Platform | Pros | Cons |
|----------|------|------|
| **Render** (Recommended) | Simple, generous free tier, good UI | - |
| **Railway** | Modern, good documentation | Slightly more complex |
| **Fly.io** | Performance-focused | More expensive |

### Frontend ⭕
Use **Vercel** (only choice needed):
- Purpose-built for React/Vite
- Zero-config deployments
- Generously free tier

### Database ⭕
Use managed service from backend platform:
- Render: PostgreSQL included
- Railway: PostgreSQL included
- Both handle backups automatically

---

## 📊 Cost Estimates (Monthly)

### Free Tier (Starting)
```
Render (Web): $0
Render (DB):  $0
Vercel:       $0
────────────
Total:        $0
(+ Stripe transaction fees: 2.9% + $0.30)
```

### Recommended Production
```
Render (Web): $7
Render (DB):  $15
Vercel:       $20
────────────
Total:        $42
(+ Stripe transaction fees: 2.9% + $0.30)
```

---

## ✅ Pre-Deployment Checklist

Before you start:

- [ ] Code committed to git
- [ ] GitHub account with repository
- [ ] Stripe account created
- [ ] Email ready to save credentials

---

## ⚠️ Common Mistakes to Avoid

1. **Don't commit `.env` file** - It has secrets!
   - Use `.env.example` or `.env.production.example`

2. **Use LIVE Stripe keys** - Not test keys
   - Verify you're in "Live" mode on Stripe Dashboard

3. **Update CORS** - After frontend deployed
   - Add Vercel URL to `main.py`

4. **Don't hardcode SECRET_KEY** - Generate random value
   - Use `python generate_secrets.py`

5. **Don't reuse passwords** - Different for each service
   - Use unique strong passwords everywhere

---

## 🆘 If Something Goes Wrong

### Backend won't deploy
Check: requirements.txt has gunicorn, Procfile exists

### Frontend shows errors
Check: Browser DevTools Console, check VITE_API_BASE_URL

### CORS errors
Check: Frontend URL is in `main.py` allowed_origins

### Payments not working
Check: Stripe keys are LIVE (not test), webhook URL correct

### Database connection errors
Check: DATABASE_URL is correct, PostgreSQL is running

**For detailed troubleshooting:** See DEPLOYMENT_GUIDE.md

---

## 📞 Support & Resources

- **Render Docs:** https://render.com/docs
- **Railway Docs:** https://docs.railway.app
- **Vercel Docs:** https://vercel.com/docs
- **Stripe Docs:** https://stripe.com/docs
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment/

---

## 🎉 After Deployment

Once live:

1. **Monitor** - Check error logs daily first week
2. **Backup** - Ensure database backups running
3. **Iterate** - Collect user feedback and improve
4. **Scale** - Upgrade plan if traffic increases

---

## Next Steps

### NOW:
1. Read [DEPLOYMENT_STEPS.md](DEPLOYMENT_STEPS.md) carefully
2. Create accounts (Render, Vercel, Stripe)
3. Generate SECRET_KEY using `generate_secrets.py`

### THEN:
Follow the step-by-step instructions exactly as written

### FINALLY:
Use [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) to verify everything works

---

**Status:** ✅ All files prepared, app ready for production deployment  
**Time to Deploy:** ~30-45 minutes  
**Difficulty:** Beginner-friendly (follow the steps exactly)

Good luck! 🚀
