"""
Demo script to populate database with sample doctors and test the appointment flow.
Run this after creating users to set up sample data.
"""

import requests
import json
from datetime import datetime, timedelta

API_BASE = "http://localhost:8000"

# Sample doctors to create
SAMPLE_DOCTORS = [
    {
        "user_id": 1,
        "first_name": "Ahmed",
        "last_name": "Hassan",
        "specialty": "Cardiology",
        "city": "Kinshasa",
        "phone": "+243123456789",
        "photo_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Ahmed",
        "consultation_fee": 50000
    },
    {
        "user_id": 2,
        "first_name": "Fatima",
        "last_name": "Diallo",
        "specialty": "General Medicine",
        "city": "Kinshasa",
        "phone": "+243987654321",
        "photo_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Fatima",
        "consultation_fee": 30000
    },
    {
        "user_id": 3,
        "first_name": "Pierre",
        "last_name": "Nkomo",
        "specialty": "Pediatrics",
        "city": "Kikwit",
        "phone": "+243456123789",
        "photo_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Pierre",
        "consultation_fee": 40000
    },
    {
        "user_id": 4,
        "first_name": "Marie",
        "last_name": "Kapanga",
        "specialty": "Dermatology",
        "city": "Matadi",
        "phone": "+243789456123",
        "photo_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Marie",
        "consultation_fee": 35000
    },
    {
        "user_id": 5,
        "first_name": "Jean",
        "last_name": "Mwaka",
        "specialty": "Orthopedics",
        "city": "Kinshasa",
        "phone": "+243321654987",
        "photo_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Jean",
        "consultation_fee": 55000
    },
]

def setup_demo_data():
    """Setup demo data in the database"""
    
    print("🏥 Healthcare Platform - Demo Data Setup")
    print("=" * 50)
    
    # Get admin token (you'll need to provide this)
    admin_token = input("\nEnter admin token (or press Enter to skip doctor creation): ").strip()
    
    if not admin_token:
        print("⚠️  Skipping doctor creation (no admin token provided)")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # Create sample doctors
    print("\n📝 Creating sample doctors...")
    created_doctors = []
    
    for i, doctor_data in enumerate(SAMPLE_DOCTORS, 1):
        try:
            response = requests.post(
                f"{API_BASE}/doctors",
                json=doctor_data,
                headers=headers
            )
            
            if response.status_code == 200:
                doctor = response.json()
                created_doctors.append(doctor)
                print(f"  ✅ Doctor {i}: {doctor_data['first_name']} {doctor_data['last_name']} (ID: {doctor.get('id')})")
            else:
                print(f"  ❌ Doctor {i}: {response.json().get('detail', 'Error')}")
        except Exception as e:
            print(f"  ❌ Doctor {i}: {str(e)}")
    
    if created_doctors:
        print(f"\n✅ Successfully created {len(created_doctors)} doctors!")
        
        # Display doctors for reference
        print("\n📋 Doctor Directory:")
        print("-" * 50)
        for doc in created_doctors:
            print(f"  ID: {doc['id']} | {doc['first_name']} {doc['last_name']}")
            print(f"     {doc['specialty']} | {doc['city']} | GNF {doc['consultation_fee']}")
            print()
        
        # Test the list endpoint
        print("\n🔍 Testing GET /doctors endpoint...")
        try:
            response = requests.get(f"{API_BASE}/doctors")
            if response.status_code == 200:
                doctors = response.json()
                print(f"  ✅ Retrieved {len(doctors)} doctors from API")
            else:
                print(f"  ❌ Error: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
        
        # Test filtering
        print("\n🔍 Testing filtering by location...")
        try:
            response = requests.get(f"{API_BASE}/doctors?location=Conakry")
            if response.status_code == 200:
                doctors = response.json()
                print(f"  ✅ Found {len(doctors)} doctors in Conakry")
            else:
                print(f"  ❌ Error: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
        
        # Test filtering by specialty
        print("\n🔍 Testing filtering by specialty...")
        try:
            response = requests.get(f"{API_BASE}/doctors?specialty=Cardiology")
            if response.status_code == 200:
                doctors = response.json()
                print(f"  ✅ Found {len(doctors)} Cardiology doctors")
            else:
                print(f"  ❌ Error: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")

def test_appointment_flow():
    """Test creating an appointment"""
    
    print("\n\n🗓️  Testing Appointment Creation")
    print("=" * 50)
    
    patient_token = input("\nEnter patient token (or press Enter to skip): ").strip()
    
    if not patient_token:
        print("⚠️  Skipping appointment test")
        return
    
    headers = {
        "Authorization": f"Bearer {patient_token}",
        "Content-Type": "application/json"
    }
    
    # Fetch available doctors
    try:
        response = requests.get(f"{API_BASE}/doctors")
        doctors = response.json()
        
        if not doctors:
            print("❌ No doctors available")
            return
        
        print(f"\n📋 Available doctors:")
        for doc in doctors:
            print(f"  {doc['id']}: {doc['first_name']} {doc['last_name']} - {doc['specialty']}")
        
        # Get user input
        doctor_id = input("\nEnter doctor ID to book with: ").strip()
        
        if not doctor_id.isdigit():
            print("❌ Invalid doctor ID")
            return
        
        doctor_id = int(doctor_id)
        
        # Create appointment for tomorrow at 10:00 AM
        appointment_date = (datetime.utcnow() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        
        appointment_data = {
            "doctor_id": doctor_id,
            "date": appointment_date.isoformat() + "Z",
            "duration_minutes": 30
        }
        
        print(f"\n📅 Creating appointment:")
        print(f"  Date: {appointment_date}")
        print(f"  Duration: 30 minutes")
        
        response = requests.post(
            f"{API_BASE}/rendezvous",
            json=appointment_data,
            headers=headers
        )
        
        if response.status_code == 201:
            appointment = response.json()
            print(f"\n✅ Appointment created!")
            print(f"  ID: {appointment['id']}")
            print(f"  Status: {appointment['status']}")
            print(f"  Price: GNF {appointment['price']}")
            print(f"  Date: {appointment['date']}")
        else:
            print(f"\n❌ Error: {response.json().get('detail', 'Unknown error')}")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    print("""
    🏥 Healthcare Platform Demo Setup
    
    This script will help you:
    1. Create sample doctors in the database
    2. Test the doctor browsing API
    3. Test doctor filtering
    4. Test appointment creation
    
    Prerequisites:
    - Backend must be running on http://localhost:8000
    - You need valid admin and patient tokens
    
    """)
    
    input("Press Enter to continue...")
    
    setup_demo_data()
    test_appointment_flow()
    
    print("\n\n✅ Demo setup complete!")
    print("\nNext steps:")
    print("  1. Open http://localhost:5173/doctors in your browser")
    print("  2. View doctors list and use filters")
    print("  3. Click 'Book Appointment' to test appointment booking")
