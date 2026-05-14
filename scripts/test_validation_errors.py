#!/usr/bin/env python3
"""
Test validation error handling to ensure backend doesn't crash.
Tests that all validation errors return proper JSON (not Python objects).
"""

import requests
import sys
import os
import json
from uuid import uuid4

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api")


def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_result(test_name, success, details=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")


def login_as_admin():
    """Login and get token"""
    response = requests.post(
        f"{API_BASE}/auth/login",
        data={
            "username": os.getenv("ADMIN_EMAIL", "pravalikan@coastalseven.com"),
            "password": os.getenv("ADMIN_PASSWORD", "admin123")
        }
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


def test_validation_error_serialization(token):
    """Test that validation errors return proper JSON"""
    print_section("Test 1: Validation Error Serialization")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test case: INTERN without batch (should trigger validation error)
    payload = {
        "name": "Test Intern",
        "email": f"test_{uuid4().hex[:8]}@test.com",
        "role": "INTERN",
        "tech_stack": "Python"
        # Missing batch_id and batch_name
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_BASE}/profiles",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        # Should return 422
        if response.status_code != 422:
            print_result(
                "Expected 422 status",
                False,
                f"Got {response.status_code}"
            )
            return False
        
        # Try to parse JSON response
        try:
            error_data = response.json()
            print(f"Response JSON: {json.dumps(error_data, indent=2)}")
            
            # Verify response structure
            if "detail" not in error_data:
                print_result("Response has 'detail' field", False)
                return False
            
            if "message" not in error_data:
                print_result("Response has 'message' field", False)
                return False
            
            # Verify detail is serializable (list of dicts with strings)
            detail = error_data["detail"]
            if not isinstance(detail, list):
                print_result("'detail' is a list", False, f"Got {type(detail)}")
                return False
            
            # Check each error is properly serialized
            for i, error in enumerate(detail):
                if not isinstance(error, dict):
                    print_result(
                        f"Error {i} is a dict",
                        False,
                        f"Got {type(error)}"
                    )
                    return False
                
                # Check all values are JSON-serializable (strings, numbers, etc.)
                for key, value in error.items():
                    if isinstance(value, dict):
                        # Nested dict - check its values too
                        for nested_key, nested_value in value.items():
                            if not isinstance(nested_value, (str, int, float, bool, type(None))):
                                print_result(
                                    f"Error {i}.{key}.{nested_key} is serializable",
                                    False,
                                    f"Got {type(nested_value)}"
                                )
                                return False
                    elif isinstance(value, list):
                        # List - check all items are serializable
                        for item in value:
                            if not isinstance(item, (str, int, float, bool, type(None))):
                                print_result(
                                    f"Error {i}.{key} list item is serializable",
                                    False,
                                    f"Got {type(item)}"
                                )
                                return False
                    elif not isinstance(value, (str, int, float, bool, type(None))):
                        print_result(
                            f"Error {i}.{key} is serializable",
                            False,
                            f"Got {type(value)}"
                        )
                        return False
            
            print_result("All validation errors properly serialized", True)
            print_result("Backend didn't crash", True)
            return True
            
        except json.JSONDecodeError as e:
            print_result("Response is valid JSON", False, f"JSON decode error: {e}")
            print(f"Raw response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print_result("Request didn't timeout", False, "Backend may have crashed")
        return False
    except Exception as e:
        print_result("Request succeeded", False, f"Exception: {e}")
        return False


def test_invalid_role_validation(token):
    """Test invalid role returns proper error"""
    print_section("Test 2: Invalid Role Validation")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "name": "Test User",
        "email": f"test_{uuid4().hex[:8]}@test.com",
        "role": "INVALID_ROLE",
        "tech_stack": "Python"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/profiles",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 422:
            print_result("Expected 422", False, f"Got {response.status_code}")
            return False
        
        error_data = response.json()
        print(f"Response: {json.dumps(error_data, indent=2)}")
        
        # Check error message mentions valid roles
        message = error_data.get("message", "")
        if "ADMIN" in message or "INTERN" in message or "TECHNICAL_LEAD" in message:
            print_result("Error message helpful", True, "Lists valid roles")
        else:
            print_result("Error message helpful", False, "Doesn't list valid roles")
        
        print_result("Invalid role validation works", True)
        return True
        
    except Exception as e:
        print_result("Invalid role validation", False, f"Exception: {e}")
        return False


def test_invalid_email_validation(token):
    """Test invalid email returns proper error"""
    print_section("Test 3: Invalid Email Validation")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "name": "Test User",
        "email": "not-an-email",  # Invalid email
        "role": "INTERN",
        "tech_stack": "Python",
        "batch_id": str(uuid4())
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/profiles",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 422:
            print_result("Expected 422", False, f"Got {response.status_code}")
            return False
        
        error_data = response.json()
        print(f"Response: {json.dumps(error_data, indent=2)}")
        
        print_result("Invalid email validation works", True)
        return True
        
    except Exception as e:
        print_result("Invalid email validation", False, f"Exception: {e}")
        return False


def test_valid_intern_creation(token):
    """Test valid INTERN creation works"""
    print_section("Test 4: Valid INTERN Creation")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # First get a batch
    response = requests.get(f"{API_BASE}/batches", headers=headers)
    if response.status_code != 200:
        print_result("Get batches", False)
        return False
    
    batches = response.json()
    if not batches:
        # Create a batch
        batch_response = requests.post(
            f"{API_BASE}/batches",
            headers=headers,
            json={
                "name": f"Test Batch {uuid4().hex[:8]}",
                "tech_stack": "Python",
                "start_date": "2026-05-01"
            }
        )
        if batch_response.status_code != 201:
            print_result("Create batch", False)
            return False
        batch_id = batch_response.json()["id"]
    else:
        batch_id = batches[0]["id"]
    
    # Create intern with "batch" field (frontend format)
    payload = {
        "name": f"Test Intern {uuid4().hex[:8]}",
        "email": f"intern_{uuid4().hex[:8]}@test.com",
        "role": "intern",  # lowercase
        "tech_stack": "Python",
        "batch": batch_id  # Using "batch" not "batch_id"
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_BASE}/profiles",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 201:
            print(f"Response: {response.text}")
            print_result("Create INTERN", False, f"Got {response.status_code}")
            return False
        
        intern = response.json()
        print(f"Created: {intern['name']}")
        print(f"  Role: {intern['role']}")
        print(f"  Batch ID: {intern['batch_id']}")
        
        # Verify role normalized to uppercase
        if intern['role'] != 'INTERN':
            print_result("Role normalized", False, f"Got {intern['role']}")
            return False
        
        # Verify batch_id populated
        if not intern['batch_id']:
            print_result("Batch ID populated", False)
            return False
        
        print_result("Valid INTERN creation works", True)
        return True
        
    except Exception as e:
        print_result("Valid INTERN creation", False, f"Exception: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("  VALIDATION ERROR HANDLING TEST")
    print("="*70)
    print(f"API: {API_BASE}")
    
    # Login
    print_section("Authentication")
    token = login_as_admin()
    if not token:
        print("❌ Login failed")
        return 1
    print("✅ Login successful")
    
    # Run tests
    results = []
    results.append(("Validation Error Serialization", test_validation_error_serialization(token)))
    results.append(("Invalid Role Validation", test_invalid_role_validation(token)))
    results.append(("Invalid Email Validation", test_invalid_email_validation(token)))
    results.append(("Valid INTERN Creation", test_valid_intern_creation(token)))
    
    # Summary
    print_section("SUMMARY")
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n✅ All validation tests passed!")
        print("\nBackend properly handles validation errors without crashing.")
        return 0
    else:
        print("\n❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
