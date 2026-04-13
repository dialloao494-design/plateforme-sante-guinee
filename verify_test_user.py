#!/usr/bin/env python3
"""
Script to verify the test user can authenticate.
"""

from database import SessionLocal
from models.user import User
from security import verify_password

def verify_test_user():
    """Verify the test user exists and password works"""

    db = SessionLocal()

    try:
        # Get the test user
        user = db.query(User).filter(User.email == "test@test.com").first()

        if not user:
            print("❌ Test user not found!")
            return

        # Test password verification
        password_valid = verify_password("test123", user.hashed_password)

        print("✅ Test user verification:")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role}")
        print(f"   Password valid: {password_valid}")
        print(f"   User ID: {user.id}")

        if password_valid:
            print("\n🎉 Test user is ready for authentication!")
            print("   You can now login with:")
            print("   Email: test@test.com")
            print("   Password: test123")
        else:
            print("\n❌ Password verification failed!")

    except Exception as e:
        print(f"❌ Error verifying test user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_test_user()