## STEP 6: Finalization, Testing & Production Readiness

This guide covers security verification, comprehensive testing, cleanup, and production deployment.

---

## 1. SECURITY AUDIT & VERIFICATION

### ✅ Password Security
- **Algorithm**: bcrypt with passlib (industry standard)
- **Location**: `security.py` - `pwd_context = CryptContext(schemes=["bcrypt"])`
- **Verification**: Uses constant-time comparison to prevent timing attacks
- **Frontend**: Passwords never logged or stored in localStorage

**Verification Checklist:**
```python
# Verify in security.py:
- pwd_context.hash() - Hashes with bcrypt
- pwd_context.verify() - Constant-time comparison
- No plaintext storage anywhere
```

### ✅ JWT Token Security
- **Algorithm**: HS256 (HMAC SHA256)
- **Secret**: Loaded from `SECRET_KEY` environment variable (required for production)
- **Expiration**: Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (defaults to 60 min)
- **Claims**: Includes email, role, and expiration time

**Verification Checklist:**
```python
# Verify in security.py:
- SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-...")
- ALGORITHM = "HS256"
- ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
- Expiration checked in jwt.decode() with algorithms=[ALGORITHM]
```

### ✅ Authentication & Authorization
- **Auth Types**: Bearer token (JWT) for API, OAuth2 form for login
- **Protected Routes**: All sensitive endpoints require JWT token
- **Role-based Access Control**: Three roles enforced
  - **patient**: Can view/create own appointments, process own payments
  - **doctor**: Can view own appointments and availability
  - **admin**: Full access to all resources
- **Dependencies**:
  - `get_current_user()` - Validates token, returns User
  - `get_current_patient()` - Validates token + role
  - `get_current_doctor()` - Validates token + role
  - `get_current_admin()` - Validates token + admin role
  - `require_roles(["role1", "role2"])` - Multi-role access

**Verification Checklist:**
```bash
# Verify all protected routes have dependencies:
GET /auth/me - Depends(get_current_user) ✓
GET /rendezvous/ - Depends(require_roles(...)) ✓
POST /payments/create-intent - Depends(get_current_patient) ✓
GET /users - Depends(get_current_admin) ✓
```

### ✅ Input Validation
- **Email**: Regex pattern validation in schemas/user.py
- **Password**: Minimum 6 characters in schemas/user.py
- **Role**: Whitelist validation (must be one of: patient, doctor, admin)
- **Pydantic**: All schemas use field validators for strict validation

**Validation Rules:**
| Field | Rule | Status |
|-------|------|--------|
| email | Valid format, lowercase | ✓ |
| password | 6+ chars | ✓ |
| role | patient\|doctor\|admin | ✓ |
| appointment_id | Must exist and belong to patient | ✓ |

### ✅ Stripe Payment Security
- **Webhook Verification**: Uses `stripe.Webhook.construct_event()`
- **Secret Storage**: `STRIPE_WEBHOOK_SECRET` from environment
- **Payment Intent**: Encrypted and managed by Stripe
- **Metadata Validation**: Ensures payment intent matches appointment

**Verification Checklist:**
```python
# Verify in services/stripe_service.py:
- stripe.Webhook.construct_event(payload, sig_header, secret)
- Raises exception on invalid signature
- No secrets exposed in logs
- Payment operations delegated to Stripe API
```

### ✅ CORS Configuration
- **Allowed Origins**: Specific localhost ports only (not wildcard)
- **Allowed Methods**: ["*"] (all methods, but only from allowed origins)
- **Allowed Headers**: ["*"] (all headers)
- **Credentials**: Enabled for Bearer token

**Configuration (main.py):**
```python
allow_origins=[
    "http://localhost:3000",    # React dev default
    "http://127.0.0.1:3000",
    "http://localhost:5173",     # Vite default
    "http://127.0.0.1:5173",
]
```

**Production Update Required:**
```python
# For production, change to:
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

### ✅ Error Handling Security
- **Generic Messages**: Errors don't leak information (e.g., "Invalid credentials" not "User not found")
- **Auth Errors**: 401 status for authentication, 403 for authorization
- **Client Errors**: 400-422 status codes
- **Server Errors**: 500 status code with generic message

**Verification Checklist:**
```bash
# All auth errors should not reveal details:
- "Invalid credentials" (not "User not found")
- "Email already registered" (reasonable to expose)
- "Access denied" (not leaking why)
```

---

## 2. COMPREHENSIVE TESTING GUIDE

### 2.1 Unit Test Flow: Full Registration → Payment

**Test Case 1: Registration**
```bash
POST /auth/register
{
  "email": "patient@example.com",
  "password": "password123",
  "role": "patient"
}

Expected Response (201):
{
  "id": 1,
  "email": "patient@example.com",
  "role": "patient"
}
```

**Test Case 2: Login**
```bash
POST /auth/login-json
{
  "email": "patient@example.com",
  "password": "password123"
}

Expected Response (200):
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "role": "patient",
  "email": "patient@example.com"
}
```

**Test Case 3: Create Patient Profile**
```bash
POST /patients
Header: Authorization: Bearer {access_token}
{
  "full_name": "John Doe",
  "phone": "+1234567890",
  "date_of_birth": "1990-01-01",
  "gender": "M",
  "address": "123 Main St"
}

Expected Response (201):
{
  "id": 1,
  "user_id": 1,
  "full_name": "John Doe",
  ...
}
```

**Test Case 4: List Doctors**
```bash
GET /doctors
Header: Authorization: Bearer {access_token}

Expected Response (200):
{
  "doctors": [
    {
      "id": 1,
      "full_name": "Dr. Smith",
      "specialization": "Cardiology",
      "consultation_fee": 50.0
    },
    ...
  ]
}
```

**Test Case 5: Create Appointment**
```bash
POST /rendezvous/
Header: Authorization: Bearer {access_token}
{
  "doctor_id": 1,
  "appointment_date": "2024-04-15",
  "start_time": "09:00",
  "duration_minutes": 30
}

Expected Response (201):
{
  "id": 1,
  "doctor_id": 1,
  "patient_id": 1,
  "status": "pending",
  "payment_status": "pending",
  "price": 50.0,
  "payment_intent_id": null
}
```

**Test Case 6: Create Payment Intent**
```bash
POST /payments/create-intent
Header: Authorization: Bearer {access_token}
{
  "appointment_id": 1
}

Expected Response (201):
{
  "client_secret": "pi_xxxxx_secret_yyyyy",
  "payment_intent_id": "pi_xxxxx",
  "amount": 5000,  // cents
  "currency": "usd",
  "status": "requires_payment_method"
}
```

**Test Case 7: List Own Appointments**
```bash
GET /rendezvous/
Header: Authorization: Bearer {access_token}

Expected Response (200):
[
  {
    "id": 1,
    "doctor_id": 1,
    "patient_id": 1,
    "status": "pending",
    "payment_status": "pending",
    "price": 50.0
  }
]
```

### 2.2 Edge Cases & Error Scenarios

**Edge Case 1: Invalid Email Format**
```bash
POST /auth/register
{
  "email": "not-an-email",
  "password": "password123",
  "role": "patient"
}

Expected: 422 Unprocessable Entity
{
  "detail": [{"loc": ["body", "email"], "msg": "Invalid email address"}]
}
```

**Edge Case 2: Short Password**
```bash
POST /auth/register
{
  "email": "test@example.com",
  "password": "123",
  "role": "patient"
}

Expected: 422 Unprocessable Entity
```

**Edge Case 3: Duplicate Email**
```bash
# First registration succeeds
# Second registration with same email:
POST /auth/register
{
  "email": "patient@example.com",
  "password": "different123",
  "role": "doctor"
}

Expected: 409 Conflict
{
  "detail": "Email 'patient@example.com' is already registered..."
}
```

**Edge Case 4: Invalid Credentials**
```bash
POST /auth/login-json
{
  "email": "patient@example.com",
  "password": "wrongpassword"
}

Expected: 401 Unauthorized
{
  "detail": "Incorrect email or password. Please check your credentials..."
}
```

**Edge Case 5: Missing Authentication Token**
```bash
GET /rendezvous/
(no Authorization header)

Expected: 403 Forbidden
{
  "detail": "Not authenticated"
}
```

**Edge Case 6: Invalid Token**
```bash
GET /rendezvous/
Authorization: Bearer invalid.token.here

Expected: 401 Unauthorized
{
  "detail": "Could not validate credentials"
}
```

**Edge Case 7: Accessing Other User's Appointment**
```bash
# Patient A tries to pay for Patient B's appointment:
POST /payments/create-intent
Header: Authorization: Bearer {patient_a_token}
{
  "appointment_id": 2  // Belongs to Patient B
}

Expected: 403 Forbidden
{
  "detail": "Access denied: This is not your appointment"
}
```

**Edge Case 8: Appointment in the Past**
```bash
POST /rendezvous/
Header: Authorization: Bearer {access_token}
{
  "doctor_id": 1,
  "appointment_date": "2020-01-01",
  "start_time": "09:00",
  "duration_minutes": 30
}

Expected: 400 Bad Request
{
  "detail": "Cannot book appointment in the past"
}
```

**Edge Case 9: Overlapping Appointments**
```bash
# As patient, book two appointments at overlapping times
POST /rendezvous/  // First succeeds (9:00-9:30)
POST /rendezvous/  // Second with 9:15-9:45

Expected: 400 Bad Request
{
  "detail": "Appointment time conflicts with existing confirmed appointment"
}
```

**Edge Case 10: Admin Access**
```bash
# Admin can access all users
GET /users
Header: Authorization: Bearer {admin_token}

Expected: 200 OK
[
  {"id": 1, "email": "patient@example.com", "role": "patient"},
  {"id": 2, "email": "doctor@example.com", "role": "doctor"},
  {"id": 3, "email": "admin@example.com", "role": "admin"}
]
```

### 2.3 API Testing with cURL

Create file `test_api.sh`:

```bash
#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

API_URL="http://localhost:8000"
EMAIL="test_$(date +%s)@example.com"
PASSWORD="testpass123"

echo -e "${BLUE}=== Healthcare Platform API Test ===${NC}\n"

# 1. Register
echo -e "${BLUE}1. Testing Registration...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\",
    \"role\": \"patient\"
  }")

USER_ID=$(echo $REGISTER_RESPONSE | grep -o '"id":[0-9]*' | grep -o '[0-9]*')
if [ -z "$USER_ID" ]; then
  echo -e "${RED}❌ Registration failed${NC}"
  echo $REGISTER_RESPONSE
  exit 1
fi
echo -e "${GREEN}✅ Registration successful (User ID: $USER_ID)${NC}"

# 2. Login
echo -e "\n${BLUE}2. Testing Login...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login-json" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\"
  }")

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
if [ -z "$ACCESS_TOKEN" ]; then
  echo -e "${RED}❌ Login failed${NC}"
  echo $LOGIN_RESPONSE
  exit 1
fi
echo -e "${GREEN}✅ Login successful${NC}"

# 3. Get Current User
echo -e "\n${BLUE}3. Testing Get Current User...${NC}"
ME_RESPONSE=$(curl -s -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

if echo $ME_RESPONSE | grep -q "\"email\":\"$EMAIL\""; then
  echo -e "${GREEN}✅ Get current user successful${NC}"
else
  echo -e "${RED}❌ Get current user failed${NC}"
  echo $ME_RESPONSE
fi

# 4. List Appointments (should be empty)
echo -e "\n${BLUE}4. Testing List Appointments...${NC}"
APPT_RESPONSE=$(curl -s -X GET "$API_URL/rendezvous/" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

if echo $APPT_RESPONSE | grep -q "^\["; then
  echo -e "${GREEN}✅ List appointments successful${NC}"
else
  echo -e "${RED}❌ List appointments failed${NC}"
  echo $APPT_RESPONSE
fi

# 5. Test invalid token
echo -e "\n${BLUE}5. Testing Invalid Token...${NC}"
INVALID_RESPONSE=$(curl -s -X GET "$API_URL/rendezvous/" \
  -H "Authorization: Bearer invalid_token_xyz")

if echo $INVALID_RESPONSE | grep -q "Could not validate credentials"; then
  echo -e "${GREEN}✅ Invalid token correctly rejected${NC}"
else
  echo -e "${RED}❌ Invalid token handling failed${NC}"
fi

echo -e "\n${GREEN}=== All Tests Completed ===${NC}"
```

Run the test:
```bash
chmod +x test_api.sh
./test_api.sh
```

---

## 3. ENVIRONMENT SETUP & .env CONFIGURATION

### 3.1 Required Environment Variables

Create `.env` file in project root:

```bash
# ========================================
# APPLICATION ENVIRONMENT
# ========================================
DEBUG=False                          # Set to True for development only
HOST=0.0.0.0                        # Bind to all interfaces
PORT=8000                           # API port

# ========================================
# DATABASE CONFIGURATION
# ========================================
# SQLite (development):
DATABASE_URL=sqlite:///./sante.db

# PostgreSQL (production recommended):
# DATABASE_URL=postgresql://user:password@localhost:5432/sante_db

# ========================================
# JWT & SECURITY
# ========================================
SECRET_KEY=your-super-secret-key-change-to-random-string-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60          # 1 hour
REFRESH_TOKEN_EXPIRE_MINUTES=10080      # 7 days

# ========================================
# STRIPE PAYMENT CONFIGURATION
# ========================================
# Get these from https://dashboard.stripe.com/apikeys
STRIPE_SECRET_KEY=sk_test_4eC39HqLyjWDarhtT657...
STRIPE_PUBLISHABLE_KEY=pk_test_51TcqvPPVEfx8kSnai...

# Webhook secret from Stripe dashboard:
# https://dashboard.stripe.com/webhooks
STRIPE_WEBHOOK_SECRET=whsec_test_5pMuykEWqPgUAMkj...

# ========================================
# FRONTEND CONFIGURATION (for CORS)
# ========================================
FRONTEND_URL=http://localhost:5173      # React dev server
FRONTEND_PRODUCTION_URL=https://your-domain.com

# ========================================
# EMAIL CONFIGURATION (optional, for notifications)
# ========================================
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=noreply@santeplatform.com

# ========================================
# LOGGING CONFIGURATION
# ========================================
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=logs/app.log
```

### 3.2 .env.example for Distribution

Create `.env.example` (safe to commit):

```bash
# Copy this file to .env and fill in your values

# Application
DEBUG=False
HOST=0.0.0.0
PORT=8000

# Database
# For SQLite:
DATABASE_URL=sqlite:///./sante.db
# For PostgreSQL:
# DATABASE_URL=postgresql://user:password@hostname:5432/database_name

# Security
SECRET_KEY=change-me-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Stripe (get from https://dashboard.stripe.com)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Frontend
FRONTEND_URL=http://localhost:5173
FRONTEND_PRODUCTION_URL=https://yourdomain.com

# Email (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

**Important:** Add to `.gitignore`:
```
.env
.env.local
.env.*.local
*.db
logs/
__pycache__/
.venv/
venv/
node_modules/
```

---

## 4. PRODUCTION DEPLOYMENT CHECKLIST

### 4.1 Backend Deployment

- [ ] Update `SECRET_KEY` to random 32+ character string
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

- [ ] Update `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` to production keys
  - Log into Stripe dashboard
  - Switch from "Test Mode" to "Live Mode"
  - Copy production keys

- [ ] Update `DATABASE_URL` to production PostgreSQL
  ```
  DATABASE_URL=postgresql://user:password@prod-db-host:5432/sante_production
  ```

- [ ] Update `FRONTEND_URL` to production domain
  ```
  FRONTEND_PRODUCTION_URL=https://yourdomain.com
  ```

- [ ] Update CORS allowed origins in `main.py`:
  ```python
  allow_origins=[
      "https://yourdomain.com",
      "https://www.yourdomain.com",
  ]
  ```

- [ ] Set `DEBUG=False`

- [ ] Use production WSGI server (gunicorn):
  ```bash
  pip install gunicorn
  gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```

- [ ] Enable HTTPS/SSL
  - Use Let's Encrypt certificate
  - Configure reverse proxy (nginx/Apache)

- [ ] Set up database migrations
  ```bash
  alembic init alembic
  alembic revision --autogenerate -m "Initial schema"
  alembic upgrade head
  ```

- [ ] Configure backup strategy
  - Daily database backups
  - Store backups securely

- [ ] Set up monitoring & logging
  - Application error monitoring (Sentry)
  - Access logs
  - Payment transaction logs

### 4.2 Frontend Deployment

- [ ] Set `VITE_API_BASE_URL` to production backend
  ```
  VITE_API_BASE_URL=https://api.yourdomain.com
  ```

- [ ] Build for production
  ```bash
  npm run build
  ```

- [ ] Deploy to CDN or static host
  - Netlify, Vercel, AWS S3 + CloudFront

- [ ] Configure HTTPS for frontend
  - Automatic with modern hosting platforms

### 4.3 Stripe Webhook Setup

**In Stripe Dashboard:**
1. Go to Developers > Webhooks
2. Add endpoint: `https://yourdomain.com/api/payments/webhook`
3. Select events:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
4. Copy webhook signing secret to `STRIPE_WEBHOOK_SECRET`

Test webhook:
```bash
curl -X POST https://yourdomain.com/api/payments/webhook \
  -H "stripe-signature: t=1234567890,v1=signature_value" \
  -d '{"type":"payment_intent.succeeded",...}'
```

### 4.4 Database & Backups

**PostgreSQL Setup:**
```bash
# Create database
createdb sante_production

# Create user with limited permissions
createuser sante_user
ALTER USER sante_user WITH PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE sante_production TO sante_user;

# Backup daily
pg_dump -U sante_user sante_production > backup_$(date +%Y%m%d).sql
```

**Restore from backup:**
```bash
psql -U sante_user sante_production < backup_20240410.sql
```

---

## 5. CLEANUP & CODE ORGANIZATION

### Files Removed ✓
- `routers/auth_broken.py` - Unused legacy auth implementation

### Unused Import Cleanup
- Verify all imports in each file are used
- Use IDE's "Remove unused imports" feature

### Code Organization Review
- `routers/`: All endpoint implementations
- `models/`: SQLAlchemy ORM models
- `schemas/`: Pydantic request/response models
- `services/`: Business logic layer
- `security.py`: Authentication & authorization
- `database.py`: Database connection
- `main.py`: FastAPI app setup
- `requirements.txt`: Python dependencies

---

## 6. LOGGING & MONITORING

### Basic Logging Setup

Update `main.py`:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Log startup
@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up")

# Log important events
logger.info(f"User {user.email} registered")
logger.warning(f"Failed login attempt for {email}")
logger.error(f"Stripe webhook processing failed: {error}")
```

### Stripe Payment Logging

In `services/stripe_service.py`:

```python
import logging
logger = logging.getLogger(__name__)

def create_payment_intent(self, appointment_id, amount, db):
    logger.info(f"Creating payment intent for appointment {appointment_id}")
    try:
        intent = stripe.PaymentIntent.create(...)
        logger.info(f"payment_intent created: {intent.id}")
        return intent
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating payment intent: {str(e)}")
        raise
```

---

## 7. FINAL VERIFICATION CHECKLIST

### Backend
- [ ] All required environment variables defined
- [ ] Password hashing verified (bcrypt)
- [ ] JWT tokens verified (HS256, expiration)
- [ ] All protected routes have auth dependencies
- [ ] Role-based access control enforced
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak sensitive info
- [ ] CORS configured for production domain
- [ ] Stripe webhook verification implemented
- [ ] Database migrations up to date
- [ ] No hardcoded secrets in code
- [ ] Logging configured


### Frontend
- [ ] API_BASE_URL set correctly for environment
- [ ] Error handling displays user-friendly messages
- [ ] Auth token persisted in localStorage
- [ ] Automatic logout on token expiration
- [ ] Rate limiting on auth endpoints (optional)
- [ ] Sensitive data not logged to console

### Security
- [ ] Secret key rotated for production
- [ ] HTTPS enforced in production
- [ ] Database backups automated
- [ ] Stripe keys are live (production ready)
- [ ] Email verification implemented (optional)
- [ ] Rate limiting on auth endpoints (optional)
- [ ] SQL injection protection (via SQLAlchemy ORM)
- [ ] XSS protection (via Pydantic serialization)
- [ ] CSRF protection (via token framework)

### Testing
- [ ] Full test flow: register → login → appointment → payment
- [ ] Edge cases tested (invalid input, unauthorized access)
- [ ] Error scenarios validated
- [ ] API responses consistent format
- [ ] Database transactions rollback on errors

---

## 8. DEPLOYMENT COMMANDS

### Local Development
```bash
# Backend
python main.py

# Frontend (in frontend-sante/frontend directory)
npm run dev
```

### Production Deployment
```bash
# Backend (with gunicorn)
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -

# Frontend
npm run build
# Deploy dist/ folder to CDN
```

---

## 9. MONITORING & SUPPORT

### Key Metrics to Monitor
- API response times
- Error rates
- Payment success rate
- Database query performance
- Stripe API availability

### Alert Thresholds
- Error rate > 5%
- Response time > 500ms
- Payment failures > 10% of attempts
- Database connection failures
- Stripe API errors

### Support Contact
- Admin: Set up admin email contact form
- Stripe support: https://support.stripe.com
- Application logs: Review `logs/app.log` for issues

---
