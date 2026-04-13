#!/usr/bin/env python
"""
Generate secure production secrets for deployment.

Usage:
    python generate_secrets.py
"""

import secrets
import string

def generate_secret_key(length=32):
    """Generate a cryptographically secure random secret key."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_token_urlsafe(length=32):
    """Generate a URL-safe random token."""
    return secrets.token_urlsafe(length)

if __name__ == "__main__":
    print("=" * 60)
    print("PRODUCTION SECRETS GENERATOR")
    print("=" * 60)
    print()
    
    # Generate SECRET_KEY
    secret_key = generate_token_urlsafe(32)
    print("🔐 JWT SECRET_KEY:")
    print(f"   {secret_key}")
    print()
    
    # Generate backup keys
    print("💾 Additional Keys (for rotation):")
    for i in range(2):
        alt_key = generate_token_urlsafe(32)
        print(f"   Backup {i+1}: {alt_key}")
    print()
    
    print("=" * 60)
    print("⚠️  IMPORTANT INSTRUCTIONS:")
    print("=" * 60)
    print()
    print("1. Copy the SECRET_KEY above")
    print("2. Go to your deployment platform (Render/Railway)")
    print("3. Set SECRET_KEY in Environment Variables")
    print("4. DELETE this output (it contains the secret!)")
    print("5. NEVER commit secrets to Git")
    print()
    print("For Stripe keys:")
    print("   - Go to Stripe Dashboard: https://dashboard.stripe.com/apikeys")
    print("   - Copy LIVE keys (not test keys)")
    print("   - Add STRIPE_SECRET_KEY to environment variables")
    print("   - Add STRIPE_PUBLISHABLE_KEY to frontend")
    print("   - Add STRIPE_WEBHOOK_SECRET from webhook settings")
    print()
