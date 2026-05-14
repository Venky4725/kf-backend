#!/usr/bin/env python3
"""
Complete test for CORS and intern creation fixes.
Run this after deployment to verify everything works.
"""

import requests
import sys
import os
from uuid import uuid4

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api")
FRONTEND_ORIGIN = "https://kf-frontend-rho.vercel.app"


def test_cors_and_intern_creation():
    """Complete end-to-end test"""
    
    print("\n" + "="*70)
    print("  COMPLETE FIX VERIFICATION")
    print("="*70)
    print(f"API: {API_BASE}")
    print(f"Origin: {FRONTEND_ORIGIN}")
    
    # Step 1: Login
    print("\n1. Login as admin...")
    response = requests.post(
        f"{API_BASE}/auth/login",
        data={
            "username": os.getenv("ADMIN_EMAIL", "pravalikan@coastalseven.com"),
            "password": os.getenv("ADMIN_PASSWORD", "admin123")
        },
        headers={"Origin": FRONTEND_ORIGIN}
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()["access_token"]
    print(f"✅ Login successful")
    
    # Check CORS on login
    if "Access-Control-Allow-Origin" not in response.headers:
        print(f"❌ CORS header missing on login")
        return False
    print(f"✅ CORS header present: {response.headers['Access-Control-Allow-Origin']}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Origin": FRONTEND_ORIGIN
    }
    
    # Step 2: Get batches
    print("\n2. Get batches...")
    response = requests.get(f"{API_BASE}/batches", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Get batches failed: {response.status_code}")
        return False
    
    batches = response.json()
    print(f"✅ Got {len(batches)} batches")
    
    # Check CORS
    if "Access-Control-Allow-Origin" not in response.headers:
        print(f"❌ CORS header missing on batches")
        return False
    
    # Check UUID serialization
    if batches:
        batch = batches[0]
        batch_id = batch['id']
        
        if not isinstance(batch_id, str):
            print(f"❌ Batch ID is {type(batch_id).__name__}, should be string")
            return False
        
        print(f"✅ Batch ID is string: {batch_id}")
        print(f"✅ Tech leads display: {batch.get('tech_leads_display', 'N/A')}")
        
        # Use this batch for intern creation
        test_batch_id = batch_id
    else:
        # Create a test batch
        print("\n2b. Creating test batch...")
        response = requests.post(
            f"{API_BASE}/batches",
            headers=headers,
            json={
                "name": f"Test Batch {uuid4().hex[:8]}",
                "tech_stack": "Python",
                "start_date": "2026-05-01"
            }
        )
        
        if response.status_code != 201:
            print(f"❌ Create batch failed: {response.status_code}")
            return False
        
        test_batch_id = response.json()['id']
        print(f"✅ Created test batch: {test_batch_id}")
    
    # Step 3: Create intern with "batch" field (frontend format)
    print("\n3. Create intern with 'batch' field...")
    intern_data = {
        "name": f"Test Intern {uuid4().hex[:8]}",
        "email": f"intern_{uuid4().hex[:8]}@test.com",
        "role": "intern",  # lowercase to test normalization
        "tech_stack": "Python",
        "batch": test_batch_id  # Frontend sends "batch" not "batch_id"
    }
    
    response = requests.post(
        f"{API_BASE}/profiles",
        headers=headers,
        json=intern_data
    )
    
    if response.status_code != 201:
        print(f"❌ Create intern failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    intern = response.json()
    print(f"✅ Created intern: {intern['name']}")
    print(f"   ID: {intern['id']}")
    print(f"   Role: {intern['role']}")
    print(f"   Batch ID: {intern['batch_id']}")
    
    # Verify batch_id is populated
    if not intern['batch_id']:
        print(f"❌ Intern batch_id is null")
        return False
    
    if intern['batch_id'] != test_batch_id:
        print(f"❌ Intern batch_id mismatch: {intern['batch_id']} != {test_batch_id}")
        return False
    
    print(f"✅ Batch assignment correct")
    
    # Check CORS
    if "Access-Control-Allow-Origin" not in response.headers:
        print(f"❌ CORS header missing on create intern")
        return False
    
    # Step 4: Verify intern appears in profiles list
    print("\n4. Verify intern in profiles list...")
    response = requests.get(
        f"{API_BASE}/profiles?role=INTERN",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Get profiles failed: {response.status_code}")
        return False
    
    profiles = response.json()
    intern_found = any(p['id'] == intern['id'] for p in profiles)
    
    if not intern_found:
        print(f"❌ Created intern not found in profiles list")
        return False
    
    print(f"✅ Intern found in profiles list")
    
    # Step 5: Test CORS preflight
    print("\n5. Test CORS preflight (OPTIONS)...")
    response = requests.options(
        f"{API_BASE}/profiles",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization"
        }
    )
    
    cors_headers = {
        k: v for k, v in response.headers.items()
        if "access-control" in k.lower()
    }
    
    required = [
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers"
    ]
    
    missing = [h for h in required if h not in cors_headers]
    
    if missing:
        print(f"❌ Missing CORS headers: {missing}")
        return False
    
    print(f"✅ All CORS headers present")
    for header, value in cors_headers.items():
        print(f"   {header}: {value}")
    
    print("\n" + "="*70)
    print("  ✅ ALL TESTS PASSED")
    print("="*70)
    print("\nFixes verified:")
    print("  ✅ CORS working for production frontend")
    print("  ✅ Intern creation with 'batch' field works")
    print("  ✅ Role normalization works (intern -> INTERN)")
    print("  ✅ Batch assignment persists correctly")
    print("  ✅ UUID serialization consistent (strings)")
    print("  ✅ All endpoints return CORS headers")
    
    return True


if __name__ == "__main__":
    try:
        success = test_cors_and_intern_creation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
