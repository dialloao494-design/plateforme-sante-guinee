# PRODUCTION DEPLOYMENT GUIDE

## Quick Start

This guide walks through deploying the Healthcare Platform to production.

---

## Prerequisites

- Linux server (Ubuntu 22.04 LTS recommended)
- PostgreSQL 14+
- Python 3.10+
- Node.js 18+
- Nginx or Apache
- SSL Certificate (Let's Encrypt)
- Stripe Live Account

---

## Part 1: Backend Deployment

### 1.1 Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3.10 python3.10-venv python3-pip
sudo apt install -y postgresql postgresql-contrib
sudo apt install -y nginx git curl

# Create app user
sudo useradd -m -s /bin/bash appuser
sudo su - appuser
```

### 1.2 Clone Repository

```bash
cd ~
git clone <your-repo-url> sante-platform
cd sante-platform
```

### 1.3 Python Environment Setup

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install production server
pip install gunicorn
```

### 1.4 Database Setup

```bash
# Create PostgreSQL database and user
sudo -u postgres psql << EOF
CREATE DATABASE sante_production;
CREATE USER sante_user WITH PASSWORD 'YOUR_STRONG_PASSWORD_HERE';
ALTER ROLE sante_user SET client_encoding TO 'utf8';
ALTER ROLE sante_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE sante_user SET default_transaction_deferrable TO on;
ALTER ROLE sante_user SET default_transaction_read_committed TO on;
GRANT ALL PRIVILEGES ON DATABASE sante_production TO sante_user;
\q
EOF

# Verify connection
psql -U sante_user -d sante_production -c "SELECT version();"
```

### 1.5 Environment Configuration

Create `.env` in project root:

```bash
# Application
DEBUG=False
HOST=127.0.0.1
PORT=8000

# Database
DATABASE_URL=postgresql://sante_user:YOUR_PASSWORD@localhost:5432/sante_production

# Security
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_urlsafe(32))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Stripe (LIVE KEYS)
STRIPE_SECRET_KEY=sk_live_YOUR_LIVE_SECRET_KEY
STRIPE_PUBLISHABLE_KEY=pk_live_YOUR_LIVE_PUBLISHABLE_KEY
STRIPE_WEBHOOK_SECRET=whsec_YOUR_LIVE_WEBHOOK_SECRET

# Frontend
FRONTEND_URL=https://yourdomain.com
FRONTEND_PRODUCTION_URL=https://yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=/home/appuser/sante-platform/logs/app.log

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 1.6 Initial Database Setup

```bash
# Run migrations if using Alembic
alembic upgrade head

# Or create tables with SQLAlchemy
python -c "from database import engine, Base; import models; Base.metadata.create_all(bind=engine)"
```

### 1.7 Create Systemd Service

Create `/etc/systemd/system/sante-api.service`:

```ini
[Unit]
Description=Healthcare Platform API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=appuser
WorkingDirectory=/home/appuser/sante-platform

# Python environment
Environment="PATH=/home/appuser/sante-platform/venv/bin"
EnvironmentFile=/home/appuser/sante-platform/.env

# Run gunicorn
ExecStart=/home/appuser/sante-platform/venv/bin/gunicorn \
    main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /home/appuser/sante-platform/logs/access.log \
    --error-logfile /home/appuser/sante-platform/logs/error.log \
    --log-level info

# Restart policy
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sante-api
sudo systemctl start sante-api
sudo systemctl status sante-api
```

---

## Part 2: Frontend Deployment

### 2.1 Build Frontend

```bash
cd frontend-sante/frontend

# Create .env.production
cat > .env.production << EOF
VITE_API_BASE_URL=https://api.yourdomain.com
EOF

# Build
npm install
npm run build

# Output in: dist/
```

### 2.2 Deploy to CDN/Static Host

**Option A: Netlify (Recommended)**
```bash
# Connect git repository
# Configure build: npm run build
# Output directory: dist
# Automatic HTTPS and CDN

# Push to GitHub/GitLab/Bitbucket
git push origin main
# Netlify auto-deploys
```

**Option B: AWS S3 + CloudFront**
```bash
# Upload build artifacts
aws s3 sync dist/ s3://yourbucket/

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id XXXXX --paths "/*"
```

**Option C: Self-hosted**
```bash
# Copy to web server
scp -r dist/* appuser@yourdomain.com:/var/www/sante/

# Configure nginx (see section 2.3)
```

### 2.3 Nginx Configuration for Frontend

Create `/etc/nginx/sites-available/sante-frontend`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    root /var/www/sante;
    index index.html;

    # SPA routing: all requests to index.html except static files
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static files with caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/sante-frontend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Part 3: API Gateway (Nginx Reverse Proxy)

Create `/etc/nginx/sites-available/sante-api`:

```nginx
upstream sante_backend {
    server 127.0.0.1:8000;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS API
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to backend
    location / {
        proxy_pass http://sante_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Webhook endpoint (for Stripe)
    location /payments/webhook {
        proxy_pass http://sante_backend;
        proxy_pass_request_headers on;
        proxy_request_buffering off;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/sante-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Part 4: SSL Certificate Setup

### Using Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d api.yourdomain.com -d yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
sudo systemctl enable certbot.timer
```

---

## Part 5: Database Backups

### Automatic Daily Backups

Create `/home/appuser/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/home/appuser/backups"
DB_NAME="sante_production"
DB_USER="sante_user"
DATE=$(date +"%Y%m%d_%H%M%S")

mkdir -p $BACKUP_DIR

# Create backup
pg_dump -U $DB_USER $DB_NAME > $BACKUP_DIR/sante_$DATE.sql

# Compress
gzip $BACKUP_DIR/sante_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -name "sante_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/sante_$DATE.sql.gz"
```

Create cron job:

```bash
# Add to crontab
crontab -e

# Add:
0 2 * * * /home/appuser/backup.sh
```

---

## Part 6: Monitoring & Logs

### Log Files

Backend logs:
```bash
tail -f /home/appuser/sante-platform/logs/app.log
sudo journalctl -u sante-api -f
```

Nginx logs:
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Health Monitoring

```bash
# Check API health
curl https://api.yourdomain.com/health

# Check service status
sudo systemctl status sante-api

# Check database
psql -U sante_user -d sante_production -c "SELECT count(*) FROM users;"
```

### Uptime Monitoring

Set up monitoring for `/health` endpoint to alert on:
- API response time > 500ms
- Error rate > 5%
- Service down
- Database connection issues

Recommended: Uptime Robot, DataDog, New Relic

---

## Part 7: Stripe Webhook Configuration

1. Log into Stripe Dashboard
2. Go to Developers > Webhooks
3. Add endpoint: `https://api.yourdomain.com/payments/webhook`
4. Select events:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Copy webhook secret to `STRIPE_WEBHOOK_SECRET`

Test webhook:
```bash
curl -X POST https://api.yourdomain.com/payments/webhook \
  -H "Content-Type: application/json" \
  -H "stripe-signature: t=TIMESTAMP,v1=SIGNATURE" \
  -d '{"type":"payment_intent.succeeded",...}'
```

---

## Part 8: First-Time Admin Setup

Connect to API and create admin account:

```bash
curl -X POST https://api.yourdomain.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourdomain.com",
    "password": "StrongSecurePassword123!",
    "role": "admin"
  }'
```

---

## Part 9: Post-Deployment Checklist

- [ ] API health check passing: `https://api.yourdomain.com/health`
- [ ] Frontend loads: `https://yourdomain.com`
- [ ] Can register new user
- [ ] Can login with credentials
- [ ] Can create appointment
- [ ] Can create Stripe payment intent
- [ ] Database backups running
- [ ] SSL certificates valid
- [ ] Monitoring alerts configured
- [ ] Logs being collected
- [ ] Admin account created
- [ ] Production stripe keys verified
- [ ] CORS configured correctly
- [ ] Email notifications working (if enabled)

---

## Part 10: Troubleshooting

### API Not Responding
```bash
# Check service status
sudo systemctl status sante-api

# Check logs
tail -100 /home/appuser/sante-platform/logs/error.log

# Restart service
sudo systemctl restart sante-api
```

### Database Connection Error
```bash
# Test connection
psql -U sante_user -d sante_production -c "SELECT 1;"

# Check DATABASE_URL in .env
grep DATABASE_URL /home/appuser/sante-platform/.env
```

### SSL Certificate Issue
```bash
# Check certificate
sudo certbot certificates

# Renew if needed
sudo certbot renew --force-renewal
```

### Stripe Webhook Not Working
```bash
# Verify webhook secret
grep STRIPE_WEBHOOK_SECRET /home/appuser/sante-platform/.env

# Check webhook logs in Stripe Dashboard
# Test webhook manually with curl
```

### High Memory Usage
```bash
# Reduce worker count in sante-api.service
--workers 2  # from 4

# Restart
sudo systemctl restart sante-api
```

---

## Performance Optimization

### 1. Database Indexing
```sql
-- Add index on frequently queried fields
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_rendezvous_patient_id ON rendezvous(patient_id);
CREATE INDEX idx_rendezvous_doctor_id ON rendezvous(doctor_id);
CREATE INDEX idx_rendezvous_status ON rendezvous(status);
```

### 2. Caching
```python
# Add Redis caching for doctor list
pip install redis
# Configure in FastAPI
```

### 3. API Rate Limiting
```python
# Prevent brute force attacks
pip install slowapi
# Configure rate limits in main.py
```

### 4. Frontend Optimization
- Enable CDN for static assets
- Minimize bundle size
- Enable gzip compression

---

## Security Hardening

### 1. Firewall Rules
```bash
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
```

### 2. SSH Security
```bash
# Disable password auth, use keys only
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart ssh
```

### 3. Regular Updates
```bash
# Enable automatic security updates
sudo apt install unattended-upgrades
sudo systemctl enable unattended-upgrades
```

### 4. Secret Rotation
```bash
# Every 30 days:
# 1. Rotate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
# 2. Update .env on server
# 3. Restart API service
```

---

## Support & Resources

- API Documentation: https://yourdomain.com/docs
- Health Check: https://yourdomain.com/health
- Stripe Documentation: https://stripe.com/docs
- FastAPI Docs: https://fastapi.tiangolo.com/
- PostgreSQL Docs: https://www.postgresql.org/docs/

---

## Emergency Recovery

### Database Recovery from Backup
```bash
# List backups
ls -la /home/appuser/backups/

# Restore
gunzip /home/appuser/backups/sante_YYYYMMDD_HHMMSS.sql.gz
psql -U sante_user sante_production < /home/appuser/backups/sante_YYYYMMDD_HHMMSS.sql
```

### Service Recovery
```bash
# If API is down
sudo systemctl restart sante-api
sudo systemctl status sante-api

# Check logs
tail -100 /home/appuser/sante-platform/logs/error.log
```

---
