# Step-by-Step Deployment Instructions

**Target:** Deploy Healthcare Platform to production (publicly accessible)

**Time Estimate:** 30-45 minutes

---

## Quick Links

| Service | Link | Purpose |
|---------|------|---------|
| Render | https://render.com | Backend + Database |
| Railway | https://railway.app | Backend + Database (Alternative) |
| Vercel | https://vercel.com | Frontend |
| Stripe | https://dashboard.stripe.com | Payment Processing |
| GitHub | https://github.com | Source Control |

---

## Step 0: Pre-Deployment Checklist

Before starting, ensure:

- [ ] You have a GitHub account with this repository
- [ ] Stripe account created (https://stripe.com)
- [ ] GitHub has `Procfile` committed (should be in repo now)
- [ ] `.env` file is NOT committed (only `.env.example`)
- [ ] Requirements.txt has been updated with gunicorn

### Check Prerequisites:

```bash
# Verify files exist
ls Procfile              # Should exist
cat requirements.txt | grep gunicorn  # Should find gunicorn
cat requirements.txt | grep psycopg2  # Should find psycopg2

# Verify .env isn't committed
git status | grep ".env"  # Should show nothing in staging

# Verify package ready for frontend
cd frontend-sante/frontend
cat package.json | grep "build"  # Should have "build": "vite build"
```

---

## Step 1: Generate Production Secrets

### Generate SECRET_KEY

The application needs a strong random secret for JWT tokens.

```bash
# Navigate to repo root
cd c:\Users\wandassai\Downloads\plateforme-sante-guinee

# Run the secret generator
python generate_secrets.py
```

**Output should show:**
```
JWT SECRET_KEY:
   <long-random-string-here>
```

**⚠️ Important:** Copy this value somewhere safe. You'll need it in Step 3.

---

## Step 2: Backend Deployment (Choose One)

### Option A: Render.com (Recommended)

#### 2A.1: Create Render Account

1. Go to https://render.com
2. Sign up with GitHub (easier)
3. Authorize the app

#### 2A.2: Create Web Service

1. Click **New +** → **Web Service**
2. Select your GitHub repository:
   - `https://github.com/yourusername/plateforme-sante-guinee`
3. Click **Connect**

#### 2A.3: Configure Web Service

Fill in the form:

| Field | Value |
|-------|-------|
| Name | `sante-api` |
| Region | Select closest region |
| Branch | `main` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT` |
| Plan | Free or Starter |

4. Click **Create Web Service**

**Note:** It will start building. You'll see logs scrolling. Wait for "✓ Deployed" message.

#### 2A.4: Create PostgreSQL Database

1. In Render dashboard, click **New +** → **PostgreSQL**
2. Fill form:

| Field | Value |
|-------|-------|
| Name | `sante-db` |
| Database | (auto-filled as `sante_db`) |
| User | (auto-generated) |
| Region | Same as web service |
| PostgreSQL Version | 15 |
| Plan | Free or Starter |

3. Click **Create Database**

**Wait** for database to be created (2-3 minutes)

#### 2A.5: Copy Database URL

1. Click on `sante-db` database
2. Copy the **External Database URL**
3. Paste it in a text editor (you'll need it next)

#### 2A.6: Set Environment Variables

1. Go back to web service (`sante-api`)
2. Click **Environment** (in settings)
3. Click **Add Environment Variable**
4. Add these one by one:

```
DEBUG = False
HOST = 0.0.0.0
PORT = 8000
ALGORITHM = HS256
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DATABASE_URL = <paste the PostgreSQL URL from step 2A.5>
SECRET_KEY = <paste the secret from Step 1>
STRIPE_SECRET_KEY = sk_live_... (get from Stripe)
STRIPE_WEBHOOK_SECRET = whsec_... (get from Stripe)
STRIPE_PUBLISHABLE_KEY = pk_live_... (get from Stripe)
FRONTEND_PRODUCTION_URL = https://your-frontend-domain.vercel.app (update later after frontend deployed)
```

⚠️ **Don't have Stripe keys yet?** Skip them for now, add them after getting keys in Step 4.

5. After adding all vars, click **Save Changes**
6. Render auto-redeploys with new environment variables

#### 2A.7: Wait for Deployment

- Watch the **Deployments** tab
- Wait for green checkmark ✓
- Get your backend URL: `https://sante-api-xxxx.onrender.com`

**Test it:**
```bash
# Replace with your actual URL
curl https://sante-api-xxxx.onrender.com/docs

# Should return Swagger API documentation (if successful)
```

✅ **Backend deployed!**

---

### Option B: Railway.app (Alternative)

#### 2B.1: Create Railway Account

1. Go to https://railway.app
2. Sign up with GitHub
3. Authorize app

#### 2B.2: Create New Project

1. Click **New Project**
2. Select **Deploy from GitHub repo**
3. Select your repository

Railway auto-detects Python project.

#### 2B.3: Add PostgreSQL Service

1. In project, click **Add Service**
2. Select **PostgreSQL**
3. Railway creates database automatically

#### 2B.4: Set Environment Variables

1. Click on web service (main app)
2. Go to **Variables**
3. Add same variables as above (Step 2A.6)
   - For DATABASE_URL: use `${{Postgres.DATABASE_URL}}`

#### 2B.5: Get Backend URL

1. Go to **Deployments**
2. Copy the generated URL
3. Should look like: `https://sante-api-xxxx.railway.app`

**Test it:**
```bash
curl https://sante-api-xxxx.railway.app/docs
```

✅ **Backend deployed!**

---

## Step 3: Get Stripe Live Keys

### 3.1: Access Stripe Dashboard

1. Go to https://dashboard.stripe.com
2. Sign in to your Stripe account
3. Click **Developers** → **API Keys** (top right)

### 3.2: Switch to Live Mode

- Toggle switch to **Live** (top left of page)
- Stripe shows you live keys (they start with `sk_live_` and `pk_live_`)

### 3.3: Copy Keys

**Get three keys:**

| Key | Where to Get | Looks Like |
|-----|--------------|-----------|
| Secret Key | Under "Standard keys" > "Secret key" | `sk_live_...` |
| Publishable Key | Under "Standard keys" > "Publishable key" | `pk_live_...` |
| Webhook Secret | Go to **Webhooks** → Create new → `payments/webhook` | `whsec_...` |

### 3.4: Add to Backend

Add these to your backend environment variables (Render/Railway):

```
STRIPE_SECRET_KEY = sk_live_...
STRIPE_PUBLISHABLE_KEY = pk_live_...
STRIPE_WEBHOOK_SECRET = whsec_...
```

Wait for redeploy to complete.

---

## Step 4: Frontend Deployment (Vercel)

### 4.1: Create Vercel Account

1. Go to https://vercel.com
2. Sign up with GitHub
3. Authorize the app

### 4.2: Import Project

1. Click **Add New...** → **Project**
2. Select your GitHub repository:
   - `https://github.com/yourusername/plateforme-sante-guinee`
3. Click **Import**

#### 4.3: Configure Project

On the import screen:

| Field | Value |
|-------|-------|
| Project Name | `sante-frontend` |
| Framework Preset | **Vite** |
| Root Directory | `frontend-sante/frontend` |

Other settings can remain default.

#### 4.4: Set Environment Variable

Before deploying:

1. Click **Environment Variables** (expand section)
2. Add variable:
   - **Name:** `VITE_API_BASE_URL`
   - **Value:** `https://sante-api-xxxx.onrender.com` (your backend URL)
   - **Environments:** Production, Preview, Development

#### 4.5: Deploy

Click **Deploy**

Wait for green "✓ Deployment Successful" message.

**Get your URL:** https://sante-frontend-xxx.vercel.app

#### 4.6: Test Frontend

1. Open https://sante-frontend-xxx.vercel.app in browser
2. You should see the login page
3. Try logging in with test credentials:
   - Email: `test.patient@example.com`
   - Password: `123456`

✅ **Frontend deployed!**

---

## Step 5: Update Backend CORS

Now that frontend is deployed, update backend to allow it.

### 5.1: Update Code

Edit `main.py`:

```python
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://sante-frontend-xxx.vercel.app",  # Add your Vercel URL here
]
```

### 5.2: Commit and Push

```bash
git add main.py
git commit -m "Update CORS origin for production frontend"
git push origin main
```

Backend auto-redeploys (wait ~2 minutes).

---

## Step 6: Configure Stripe Webhook

### 6.1: Add Webhook Endpoint

1. Go to Stripe Dashboard → **Webhooks**
2. Click **Add endpoint**
3. Fill in:
   - **Endpoint URL:** `https://sante-api-xxxx.onrender.com/payments/webhook`
   - **Events:** Search and select `checkout.session.completed`
4. Click **Add endpoint**

### 6.2: Get Webhook Secret

1. Click on the webhook you just created
2. Find **Signing secret**
3. Click **Reveal** and copy
4. Add to backend environment as `STRIPE_WEBHOOK_SECRET`

### 6.3: Redeploy Backend

Backend auto-redeploys when you update environment variables.

---

## Step 7: Verification Tests

### Test 1: Can you log in?

1. Go to https://sante-frontend-xxx.vercel.app
2. Log in with test credentials:
   - Email: `test.patient@example.com`
   - Password: `123456`
3. Should see dashboard

✅ **Login works**

### Test 2: Can you create appointment?

1. Logged in as patient
2. Go to "Rendez-vous" page
3. Create a new appointment
4. Should see success message

✅ **Appointments work**

### Test 3: Can you pay?

1. After creating appointment
2. Click "Proceed to Payment"
3. Should redirect to Stripe Checkout
4. Use Stripe test card: `4242 4242 4242 4242`
   - Expiry: any future date (e.g., 12/25)
   - CVC: any 3 digits (e.g., 123)
5. Complete payment
6. Should return to app with "Payment successful" message

✅ **Payments work**

### Test 4: Check API responds

```bash
# Replace with your backend URL
curl https://sante-api-xxxx.onrender.com/docs

# Should return Swagger UI HTML (not error)
```

✅ **API works**

---

## Step 8: Update Frontend CORS Origin in Backend (if needed)

If you get CORS errors on frontend:

1. Check error in browser DevTools
2. Update CORS in `main.py` with exact Vercel URL
3. Commit and push
4. Wait for auto-redeploy

---

## Troubleshooting

### Backend won't start

**Error:** "ModuleNotFoundError" or "gunicorn not found"

**Fix:**
```bash
# Update requirements.txt
pip install gunicorn psycopg2-binary
pip freeze > requirements.txt
git push  # Redeploy
```

### Frontend can't reach backend

**Error:** CORS error in browser console

**Fix:**
1. Check `VITE_API_BASE_URL` in Vercel environment
2. Verify backend CORS includes frontend URL in `main.py`
3. Test with curl: `curl https://backend-url/docs`

### Database connection error

**Error:** "psycopg2.OperationalError" or "could not connect"

**Fix:**
1. Verify `DATABASE_URL` is correct
2. Check PostgreSQL is running (should be automatic)
3. Check database credentials in connection string

### Payment not processing

**Error:** Stripe webhook not firing

**Fix:**
1. Verify webhook URL in Stripe dashboard
2. Check `STRIPE_WEBHOOK_SECRET` is correct
3. Test webhook from Stripe dashboard

---

## Summary

After following all steps, you should have:

✅ Backend running on Render/Railway (with PostgreSQL)  
✅ Frontend running on Vercel  
✅ Stripe payments configured  
✅ App publicly accessible at https://sante-frontend-xxx.vercel.app  

**Your app is now live! 🎉**

---

## Next Steps

- Monitor logs daily
- Test periodically
- Keep dependencies updated
- Review Stripe transactions
- Setup backups

See `DEPLOYMENT_GUIDE.md` for detailed information and maintenance instructions.
