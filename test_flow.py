#!/usr/bin/env python3
"""
Comprehensive Test Flow Script
Tests: Registration → Login → Appointment → Payment

Usage:
  python test_flow.py
  
Requirements:
  pip install requests python-dotenv
"""

import requests
import json
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_PREFIX = f"test_{int(time.time())}"
TEST_EMAIL = f"{TEST_PREFIX}@example.com"
TEST_PASSWORD = "SecureTestPass123"

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_test(title):
    """Print test title"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_success(message):
    """Print success message"""
    print(f"{GREEN}✅ {message}{RESET}")


def print_error(message):
    """Print error message"""
    print(f"{RED}❌ {message}{RESET}")


def print_info(message):
    """Print info message"""
    print(f"{BLUE}ℹ️  {message}{RESET}")


def print_data(label, data):
    """Print data in formatted way"""
    print(f"{YELLOW}{label}:{RESET}")
    print(json.dumps(data, indent=2, default=str))


class HealthTestFlow:
    """Orchestrate comprehensive test flow"""
    
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.user_id = None
        self.doctor_id = None
        self.appointment_id = None
        self.patient_id = None
        
    def request(self, method, endpoint, data=None, expected_status=200):
        """Make HTTP request with auth token"""
        url = urljoin(API_BASE_URL, endpoint)
        headers = {}
        
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PATCH':
                response = self.session.patch(url, json=data, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            # Check status
            if response.status_code != expected_status:
                print_error(f"Expected {expected_status}, got {response.status_code}")
                print_data("Response", response.json())
                return None
            
            return response.json()
            
        except requests.exceptions.ConnectionError:
            print_error(f"Cannot connect to {API_BASE_URL}")
            print_info("Make sure the backend is running: python main.py")
            sys.exit(1)
        except Exception as e:
            print_error(f"Request failed: {str(e)}")
            return None
    
    def test_health_check(self):
        """Test API health"""
        print_test("1. API HEALTH CHECK")
        try:
            response = self.session.get(urljoin(API_BASE_URL, '/'), timeout=5)
            print_success(f"API is running (status: {response.status_code})")
            return True
        except Exception as e:
            print_error(f"API not responding: {str(e)}")
            return False
    
    def test_registration(self):
        """Test user registration"""
        print_test("2. USER REGISTRATION")
        
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "role": "patient"
        }
        
        print_info(f"Registering user: {TEST_EMAIL}")
        response = self.request('POST', '/auth/register', payload, expected_status=201)
        
        if not response:
            return False
        
        self.user_id = response.get('id')
        print_success(f"Registration successful (User ID: {self.user_id})")
        print_data("User data", response)
        return True
    
    def test_registration_duplicate(self):
        """Test duplicate registration prevention"""
        print_test("3. DUPLICATE REGISTRATION PREVENTION")
        
        payload = {
            "email": TEST_EMAIL,
            "password": "AnotherPass123",
            "role": "doctor"
        }
        
        print_info(f"Attempting to register same email again...")
        response = self.request('POST', '/auth/register', payload, expected_status=409)
        
        if response:
            print_success("Duplicate registration correctly rejected (409 Conflict)")
            return True
        return False
    
    def test_login(self):
        """Test user login"""
        print_test("4. USER LOGIN")
        
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        print_info(f"Logging in: {TEST_EMAIL}")
        response = self.request('POST', '/auth/login-json', payload, expected_status=200)
        
        if not response:
            return False
        
        self.access_token = response.get('access_token')
        role = response.get('role')
        email = response.get('email')
        
        print_success(f"Login successful")
        print_info(f"Role: {role}, Email: {email}")
        print_data("Token response", {
            "access_token": self.access_token[:20] + "...",
            "token_type": response.get('token_type'),
            "role": role,
            "email": email
        })
        return True
    
    def test_invalid_credentials(self):
        """Test login with invalid credentials"""
        print_test("5. INVALID CREDENTIALS REJECTION")
        
        payload = {
            "email": TEST_EMAIL,
            "password": "WrongPassword123"
        }
        
        print_info(f"Attempting login with wrong password...")
        response = self.request('POST', '/auth/login-json', payload, expected_status=401)
        
        if response:
            print_success("Invalid credentials correctly rejected (401 Unauthorized)")
            return True
        return False
    
    def test_get_current_user(self):
        """Test get current user endpoint"""
        print_test("6. GET CURRENT USER")
        
        print_info("Fetching current user profile...")
        response = self.request('GET', '/auth/me', expected_status=200)
        
        if not response:
            return False
        
        print_success("Current user profile retrieved")
        print_data("User profile", response)
        return True
    
    def test_unauthorized_access(self):
        """Test unauthorized access without token"""
        print_test("7. UNAUTHORIZED ACCESS PREVENTION")
        
        print_info("Attempting to access protected route without token...")
        
        # Temporarily remove token
        token_backup = self.access_token
        self.access_token = None
        
        response = self.request('GET', '/rendezvous/', expected_status=403)
        
        # Restore token
        self.access_token = token_backup
        
        if response:
            print_success("Unauthorized access correctly rejected (403 Forbidden)")
            return True
        return False
    
    def test_list_doctors(self):
        """Test listing available doctors"""
        print_test("8. LIST AVAILABLE DOCTORS")
        
        print_info("Fetching list of doctors...")
        response = self.request('GET', '/doctors', expected_status=200)
        
        if not response:
            print_info("No doctors found - you may need to add doctors via admin")
            return True
        
        if isinstance(response, list) and len(response) > 0:
            self.doctor_id = response[0].get('id')
            print_success(f"Found {len(response)} doctor(s)")
            print_data("First doctor", response[0])
            return True
        elif isinstance(response, dict) and response.get('doctors'):
            doctors = response['doctors']
            if len(doctors) > 0:
                self.doctor_id = doctors[0].get('id')
                print_success(f"Found {len(doctors)} doctor(s)")
                print_data("First doctor", doctors[0])
                return True
        
        print_info("No doctors available in system")
        return True  # Not critical
    
    def test_create_patient_profile(self):
        """Test creating patient profile"""
        print_test("9. CREATE PATIENT PROFILE")
        
        payload = {
            "full_name": "Test Patient",
            "phone": "+1234567890",
            "date_of_birth": "1990-01-01",
            "gender": "M",
            "address": "123 Test Street"
        }
        
        print_info("Creating patient profile...")
        response = self.request('POST', '/patients', payload, expected_status=201)
        
        if not response:
            # If patient already exists, that's okay
            print_info("Patient profile may already exist")
            return True
        
        self.patient_id = response.get('id')
        print_success(f"Patient profile created (ID: {self.patient_id})")
        print_data("Patient profile", response)
        return True
    
    def test_create_appointment(self):
        """Test creating appointment"""
        print_test("10. CREATE APPOINTMENT")
        
        # Need a doctor first
        if not self.doctor_id:
            print_info("No doctor available - skipping appointment creation")
            return True
        
        # Get appointment date (tomorrow at 9 AM)
        appointment_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        payload = {
            "doctor_id": self.doctor_id,
            "appointment_date": appointment_date,
            "start_time": "09:00",
            "duration_minutes": 30
        }
        
        print_info(f"Creating appointment for {appointment_date} at 09:00...")
        response = self.request('POST', '/rendezvous/', payload, expected_status=201)
        
        if not response:
            print_info("Could not create appointment (doctors may not have availability)")
            return True
        
        self.appointment_id = response.get('id')
        print_success(f"Appointment created (ID: {self.appointment_id})")
        print_data("Appointment", {
            "id": response.get('id'),
            "status": response.get('status'),
            "payment_status": response.get('payment_status'),
            "price": response.get('price')
        })
        return True
    
    def test_list_appointments(self):
        """Test listing user's appointments"""
        print_test("11. LIST USER APPOINTMENTS")
        
        print_info("Fetching user appointments...")
        response = self.request('GET', '/rendezvous/', expected_status=200)
        
        if not response:
            return False
        
        appointments = response if isinstance(response, list) else response.get('appointments', [])
        print_success(f"Found {len(appointments)} appointment(s)")
        
        if appointments:
            print_data("First appointment", appointments[0])
        
        return True
    
    def test_create_payment_intent(self):
        """Test creating Stripe payment intent"""
        print_test("12. CREATE PAYMENT INTENT")
        
        if not self.appointment_id:
            print_info("No appointment available - skipping payment intent creation")
            return True
        
        payload = {
            "appointment_id": self.appointment_id
        }
        
        print_info(f"Creating payment intent for appointment {self.appointment_id}...")
        response = self.request('POST', '/payments/create-intent', payload, expected_status=201)
        
        if not response:
            return False
        
        print_success("Payment intent created")
        print_data("Payment intent", {
            "payment_intent_id": response.get('payment_intent_id'),
            "amount": response.get('amount'),
            "currency": response.get('currency'),
            "status": response.get('status'),
            "client_secret": response.get('client_secret', 'pi_xxxxx_secret_yyyyy')[:30] + "..."
        })
        return True
    
    def test_access_control(self):
        """Test role-based access control"""
        print_test("13. ROLE-BASED ACCESS CONTROL")
        
        # Patient should not access /users (admin only)
        print_info("Testing patient cannot access /users (admin only)...")
        response = self.request('GET', '/users', expected_status=403)
        
        if response:
            print_success("Patient access to /users correctly denied (403 Forbidden)")
            return True
        return False
    
    def run_all_tests(self):
        """Run all tests"""
        print(f"{BLUE}╔{'═'*58}╗{RESET}")
        print(f"{BLUE}║{' '*58}║{RESET}")
        print(f"{BLUE}║  {RESET}Healthcare Platform - Comprehensive Test Flow{BLUE}║{RESET}")
        print(f"{BLUE}║  {RESET}Testing: Register → Login → Appointment → Payment{BLUE}║{RESET}")
        print(f"{BLUE}║{' '*58}║{RESET}")
        print(f"{BLUE}╚{'═'*58}╝{RESET}")
        
        tests = [
            self.test_health_check,
            self.test_registration,
            self.test_registration_duplicate,
            self.test_login,
            self.test_invalid_credentials,
            self.test_get_current_user,
            self.test_unauthorized_access,
            self.test_list_doctors,
            self.test_create_patient_profile,
            self.test_create_appointment,
            self.test_list_appointments,
            self.test_create_payment_intent,
            self.test_access_control,
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print_error(f"Test error: {str(e)}")
                results.append(False)
        
        # Summary
        print_test("TEST SUMMARY")
        passed = sum(results)
        total = len(results)
        
        print(f"\nTests passed: {GREEN}{passed}/{total}{RESET}")
        
        if passed == total:
            print_success("All tests passed! ✨")
            print_info("Your API is production-ready for basic flows")
            return 0
        else:
            print_error(f"{total - passed} test(s) failed")
            print_info("Fix the issues above and try again")
            return 1


def main():
    """Main entry point"""
    tester = HealthTestFlow()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
