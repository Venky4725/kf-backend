#!/usr/bin/env python3
"""
Test script to verify intern creation 422 error fixes.

This script tests:
1. Frontend sending "batch" field (instead of "batch_id")
2. Role validation and normalization
3. Batch validation
4. Proper error messages for validation failures
"""

import sys
import os
import requests
import json
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@knowledgefactory.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(test_name, success, details=""):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")


def login_as_admin():
    """Login and get access token"""
    print_section("Authentication")
    
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print_result("Admin login", True, f"Token: {token[:20]}...")
        return token
    else:
        print_result("Admin login", False, f"Status: {response.status_code}, Error: {response.text}")
        return None


def get_or_create_test_batch(token):
    """Get or create a test batch for testing"""
    print_section("Test Batch Setup")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to get existing batches
    response = requests.get(f"{API_BASE_URL}/batches", headers=headers)
    
    if response.status_code == 200:
        batches = response.json()
        if batches:
            batch = batches[0]
            print_result("Using existing batch", True, f"Batch: {batch['name']} (ID: {batch['id']})")
            return batch['id']
    
    # Create a new test batch
    batch_data = {
        "name": f"Test Batch {uuid4().hex[:8]}",
        "tech_stack": "Python/FastAPI",
        "start_date": "2026-05-01"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/batches",
        headers=headers,
        json=batch_data
    )
    
    if response.status_code == 201:
        batch = response.json()
        print_result("Created test batch", True, f"Batch: {batch['name']} (ID: {batch['id']})")
        return batch['id']
    else:
        print_result("Create test batch", False, f"Status: {response.status_code}, Error: {response.text}")
        return None


def test_intern_creation_with_batch_field(token, batch_id):
    """Test 1: Frontend sends 'batch' field instead of 'batch_id'"""
    print_section("Test 1: Intern Creation with 'batch' Field")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Frontend payload using "batch" field (not "batch_id")
    intern_data = {
        "name": f"Test Intern {uuid4().hex[:8]}",
        "email": f"intern_{uuid4().hex[:8]}@test.com",
        "role": "INTERN",
        "tech_stack": "Python",
        "batch": batch_id  # Frontend sends "batch" not "batch_id"
    }
    
    print(f"Payload: {json.dumps(intern_data, indent=2)}")
    
    response = requests.post(
        f"{API_BASE_URL}/profiles",
        headers=headers,
        json=intern_data
    )
    
    if response.status_code == 201:
        profile = response.json()
        print_result(
            "Create intern with 'batch' field",
            True,
            f"Created: {profile['name']} (ID: {profile['id']}, Batch: {profile['batch_id']})"
        )
        return profile['id']
    else:
        print_result(
            "Create intern with 'batch' field",
            False,
            f"Status: {response.status_code}, Error: {response.text}"
        )
        return None


def test_intern_creation_with_batch_id_field(token, batch_id):
    """Test 2: Standard creation with 'batch_id' field"""
    print_section("Test 2: Intern Creation with 'batch_id' Field")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    intern_data = {
        "name": f"Test Intern {uuid4().hex[:8]}",
        "email": f"intern_{uuid4().hex[:8]}@test.com",
        "role": "INTERN",
        "tech_stack": "JavaScript",
        "batch_id": batch_id  # Standard field name
    }
    
    print(f"Payload: {json.dumps(intern_data, indent=2)}")
    
    response = requests.post(
        f"{API_BASE_URL}/profiles",
        headers=headers,
        json=intern_data
    )
    
    if response.status_code == 201:
        profile = response.json()
        print_result(
            "Create intern with 'batch_id' field",
            True,
            f"Created: {profile['name']} (ID: {profile['id']}, Batch: {profile['batch_id']})"
        )
        return profile['id']
    else:
        print_result(
            "Create intern with 'batch_id' field",
            False,
            f"Status: {response.status_code}, Error: {response.text}"
        )
        return None


def test_role_case_insensitive(token, batch_id):
    """Test 3: Role validation is case-insensitive"""
    print_section("Test 3: Role Case Insensitivity")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    test_cases = [
        ("intern", "lowercase"),
        ("Intern", "mixed case"),
        ("INTERN", "uppercase")
    ]
    
    for role_value, description in test_cases:
        intern_data = {
            "name": f"Test Intern {uuid4().hex[:8]}",
            "email": f"intern_{uuid4().hex[:8]}@test.com",
            "role": role_value,
            "tech_stack": "Python",
            "batch_id": batch_id
        }
        
        response = requests.post(
            f"{API_BASE_URL}/profiles",
            headers=headers,
            json=intern_data
        )
        
        if response.status_code == 201:
            profile = response.json()
            print_result(
                f"Role '{role_value}' ({description})",
                True,
                f"Normalized to: {profile['role']}"
            )
        else:
            print_result(
                f"Role '{role_value}' ({description})",
                False,
                f"Status: {response.status_code}"
            )


def test_intern_without_batch(token):
    """Test 4: Intern creation without batch should fail with clear error"""
    print_section("Test 4: Intern Without Batch (Should Fail)")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    intern_data = {
        "name": f"Test Intern {uuid4().hex[:8]}",
        "email": f"intern_{uuid4().hex[:8]}@test.com",
        "role": "INTERN",
        "tech_stack": "Python"
        # No batch_id or batch field
    }
    
    print(f"Payload: {json.dumps(intern_data, indent=2)}")
    
    response = requests.post(
        f"{API_BASE_URL}/profiles",
        headers=headers,
        json=intern_data
    )
    
    if response.status_code == 422:
        error = response.json()
        print_result(
            "Validation error for missing batch",
            True,
            f"Error message: {error.get('detail', error)}"
        )
    else:
        print_result(
            "Validation error for missing batch",
            False,
            f"Expected 422, got {response.status_code}"
        )


def test_invalid_role(token, batch_id):
    """Test 5: Invalid role should fail with clear error"""
    print_section("Test 5: Invalid Role (Should Fail)")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    intern_data = {
        "name": f"Test User {uuid4().hex[:8]}",
        "email": f"user_{uuid4().hex[:8]}@test.com",
        "role": "INVALID_ROLE",
        "tech_stack": "Python",
        "batch_id": batch_id
    }
    
    print(f"Payload: {json.dumps(intern_data, indent=2)}")
    
    response = requests.post(
        f"{API_BASE_URL}/profiles",
        headers=headers,
        json=intern_data
    )
    
    if response.status_code == 422:
        error = response.json()
        print_result(
            "Validation error for invalid role",
            True,
            f"Error message: {error.get('detail', error)}"
        )
    else:
        print_result(
            "Validation error for invalid role",
            False,
            f"Expected 422, got {response.status_code}"
        )


def test_invalid_batch_id(token):
    """Test 6: Invalid batch_id should fail with clear error"""
    print_section("Test 6: Invalid Batch ID (Should Fail)")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    fake_batch_id = str(uuid4())
    
    intern_data = {
        "name": f"Test Intern {uuid4().hex[:8]}",
        "email": f"intern_{uuid4().hex[:8]}@test.com",
        "role": "INTERN",
        "tech_stack": "Python",
        "batch_id": fake_batch_id
    }
    
    print(f"Payload: {json.dumps(intern_data, indent=2)}")
    
    response = requests.post(
        f"{API_BASE_URL}/profiles",
        headers=headers,
        json=intern_data
    )
    
    if response.status_code == 400:
        error = response.json()
        print_result(
            "Error for non-existent batch",
            True,
            f"Error message: {error.get('detail', error)}"
        )
    else:
        print_result(
            "Error for non-existent batch",
            False,
            f"Expected 400, got {response.status_code}: {response.text}"
        )


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  INTERN CREATION 422 ERROR FIX - TEST SUITE")
    print("=" * 80)
    print(f"API Base URL: {API_BASE_URL}")
    
    # Login
    token = login_as_admin()
    if not token:
        print("\n❌ Cannot proceed without authentication")
        return 1
    
    # Get or create test batch
    batch_id = get_or_create_test_batch(token)
    if not batch_id:
        print("\n❌ Cannot proceed without test batch")
        return 1
    
    # Run tests
    test_intern_creation_with_batch_field(token, batch_id)
    test_intern_creation_with_batch_id_field(token, batch_id)
    test_role_case_insensitive(token, batch_id)
    test_intern_without_batch(token)
    test_invalid_role(token, batch_id)
    test_invalid_batch_id(token)
    
    print_section("Test Suite Complete")
    print("\n✅ All tests completed. Review results above.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
