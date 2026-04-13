#!/usr/bin/env python3
"""
Script to create a test user in the database.
"""

from database import SessionLocal, engine
from models.user import User
from security import hash_password

def create_test_user():
    """Create a test user with email: test@test.com, password: test123"""

    # Create database session
    db = SessionLocal()

    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == "test@test.com").first()
        if existing_user:
            print("Test user already exists!")
            return

        # Hash the password
        hashed_password = hash_password("test123")

        # Create the test user
        test_user = User(
            email="test@test.com",
            hashed_password=hashed_password,
            role="patient"  # Default role for testing
        )

        # Add to database
        db.add(test_user)
        db.commit()
        db.refresh(test_user)

        print("✅ Test user created successfully!")
        print(f"   Email: {test_user.email}")
        print(f"   Role: {test_user.role}")
        print(f"   ID: {test_user.id}")

    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()