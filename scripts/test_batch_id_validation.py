#!/usr/bin/env python3
"""
Test batch_id validation for INTERN role.
Verifies that valid batch_id is accepted and invalid cases are rejected.
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


def get_or_create_batch(token):
    """Get existing batch or create one"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to get existing batches
    response = requests.get(f"{API_BASE}/batches", headers=headers)
    if response.status_code == 200:
        batches = response.json()
        if batches:
            return batches[0]["id"]
    
    # Create a new batch
    response = requests.post(
        f"{API_BASE}/batches",
        headers=headers,
        json={
            "name": f"Test Batch {uuid4().hex[:8]}",
            "tech_stack": "Python",
            "start_date": "2026-05-01"
        }
    )
    
    if response.status_code == 201:
        return response.json()["id"]
    
    return None


def test_intern_with_batch_id_field(token, batch_id):
    """Test 1: INTERN with batch_id field (standard)"""
    print_section("Test 1: INTERN with batch_id field")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "name": f"Test Intern {uuid4().hex[:8]}",
        "email": f"intern_{uuid4().hex[:8]}@test.com",
        "role": "INTERN",
        "tech_stack": "Python",
        "batch_id": batch_id
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{API_BASE}/profiles",
        headers=headers,
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        intern = response.json()
        print(f"Response: {json.dumps(intern, indent=2, default=str)}")
        
        # Verify batch_id is set
        if intern.get("batch_id") == batch_id:
            print_result("INTERN with batch_id", True, f"Batch ID: {batch_id}")
            return True
        else:
            print_result("INTERN with batch_id", False, f"Batch ID mismatch: {intern.get('batch_id')} != {batch_id}")
            return False
    else:
        print(f"Response: {response.text}")
        print_result("INTERN with batch_id", False, f"Status {response.status_code}")
        return False


def test_intern_with_batch_field(token, batch_id):
    """Test 2: INTERN with batch field (frontend alias)"""
    print_section("Test 2: INTERN with batch field (alias)")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "name": f"Test Intern {uuid4().hex[:8]}",
        "email": f"intern_{uuid4().hex[:8]}@test.com",
        "role": "INTERN",
        "tech_stack": "Python",
        "batch": batch_id  # Using alias
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{API_BASE}/profiles",
        headers=headers,
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        intern = response.json()
        print(f"Response: {json.dumps(intern, indent=2, default=str)}")
        
        # Verify batch_id is set (should be mapped from 'batch')
        if intern.get("batch_id") == batch_id:
            print_result("INTERN with batch (alias)", True, f"Batch ID: {batch_id}")
            return True
        else:
            print_result("INTERN with batch (alias)", False, f"Batch ID mismatch: {intern.get('batch_id')} != {batch_id}")
            return False
    else:
        print(f"Response: {response.text}")
        print_result("INTERN with batch (alias)", False, f"Status {response.status_code}")
        return False


def test_intern_without_batch(token):
    """Test 3: INTERN without batch (should fail)"""
    print_section("Test 3: INTERN without batch (should fail)")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "name": f"Test Intern {uuid4().hex[:8]}",
        "email": f"intern_{uuid4().hex[:8]}@test.com",
        "role": "INTERN",
        "tech_stack": "Python"
        # No batch_id or batch
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{API_BASE}/profiles",
        headers=headers,
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 422:
        error = response.json()
        message = error.get("message", "")
        
        if "batch" in message.lower():
            print_result("INTERN without batch rejected", True, "Proper validation error")
            return True
        else:
            print_result("INTERN without batch rejected", False, "Error message unclear")
            return False
    else:
        print_result("INTERN without batch rejected", False, f"Expected 422, got {response.status_code}")
        return False


def test_intern_with_batch_name(token):
    """Test 4: INTERN with batch_name (CSV upload scenario)"""
    print_section("Test 4: INTERN with batch_name")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    batch_name = f"CSV Batch {uuid4().hex[:8]}"
    
    payload = {
        "name": f"Test Intern {uuid4().hex[:8]}",
        "email": f"intern_{uuid4().hex[:8]}@test.com",
        "role": "INTERN",
        "tech_stack": "Python",
        "batch_name": batch_name
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{API_BASE}/profiles",
        headers=headers,
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        intern = response.json()
        print(f"Response: {json.dumps(intern, indent=2, default=str)}")
        
        # Verify batch_id is set (batch should be created)
        if intern.get("batch_id"):
            print_result("INTERN with batch_name", True, f"Batch created and assigned")
            return True
        else:
            print_result("INTERN with batch_name", False, "Batch ID not set")
            return False
    else:
        print(f"Response: {response.text}")
        print_result("INTERN with batch_name", False, f"Status {response.status_code}")
        return False


def test_admin_without_batch(token):
    """Test 5: ADMIN without batch (should succeed)"""
    print_section("Test 5: ADMIN without batch (should succeed)")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "name": f"Test Admin {uuid4().hex[:8]}",
        "email": f"admin_{uuid4().hex[:8]}@test.com",
        "role": "ADMIN",
        "tech_stack": None
        # No batch - ADMIN doesn't need batch
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{API_BASE}/profiles",
        headers=headers,
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        admin = response.json()
        print(f"Response: {json.dumps(admin, indent=2, default=str)}")
        print_result("ADMIN without batch", True, "ADMIN doesn't require batch")
        return True
    else:
        print(f"Response: {response.text}")
        print_result("ADMIN without batch", False, f"Status {response.status_code}")
        return False


def test_tech_lead_without_batch(token):
    """Test 6: TECHNICAL_LEAD without batch (should succeed)"""
    print_section("Test 6: TECHNICAL_LEAD without batch (should succeed)")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "name": f"Test TL {uuid4().hex[:8]}",
        "email": f"tl_{uuid4().hex[:8]}@test.com",
        "role": "TECHNICAL_LEAD",
        "tech_stack": "Python"
        # No batch - TL can be created without batch
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{API_BASE}/profiles",
        headers=headers,
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        tl = response.json()
        print(f"Response: {json.dumps(tl, indent=2, default=str)}")
        print_result("TECHNICAL_LEAD without batch", True, "TL doesn't require batch")
        return True
    else:
        print(f"Response: {response.text}")
        print_result("TECHNICAL_LEAD without batch", False, f"Status {response.status_code}")
        return False


def main():
    print("\n" + "="*70)
    print("  BATCH_ID VALIDATION TEST")
    print("="*70)
    print(f"API: {API_BASE}")
    
    # Login
    print_section("Authentication")
    token = login_as_admin()
    if not token:
        print("❌ Login failed")
        return 1
    print("✅ Login successful")
    
    # Get or create batch
    print_section("Setup")
    batch_id = get_or_create_batch(token)
    if not batch_id:
        print("❌ Failed to get/create batch")
        return 1
    print(f"✅ Using batch: {batch_id}")
    
    # Run tests
    results = []
    results.append(("INTERN with batch_id", test_intern_with_batch_id_field(token, batch_id)))
    results.append(("INTERN with batch (alias)", test_intern_with_batch_field(token, batch_id)))
    results.append(("INTERN without batch (reject)", test_intern_without_batch(token)))
    results.append(("INTERN with batch_name", test_intern_with_batch_name(token)))
    results.append(("ADMIN without batch", test_admin_without_batch(token)))
    results.append(("TECHNICAL_LEAD without batch", test_tech_lead_without_batch(token)))
    
    # Summary
    print_section("SUMMARY")
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n✅ All batch_id validation tests passed!")
        print("\nPOST /api/profiles works correctly for INTERN role with batch_id.")
        return 0
    else:
        print("\n❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
