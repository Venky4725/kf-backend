#!/usr/bin/env python3
"""
Production deployment verification script.
Tests critical endpoints after deployment to Railway.
"""

import requests
import sys
import os
from uuid import uuid4

# Configuration
PRODUCTION_URL = os.getenv("PRODUCTION_URL", "https://your-railway-url.railway.app")
API_BASE = f"{PRODUCTION_URL}/api"
FRONTEND_ORIGIN = "https://kf-frontend-rho.vercel.app"


def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_health():
    """Test health endpoint"""
    print_section("1. Health Check")
    
    try:
        response = requests.get(
            f"{API_BASE}/health",
            headers={"Origin": FRONTEND_ORIGIN},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Check CORS headers
        cors_header = response.headers.get("Access-Control-Allow-Origin")
        print(f"CORS Header: {cors_header}")
        
        if response.status_code == 200 and cors_header:
            print("✅ Health check passed with CORS")
            return True
        else:
            print("❌ Health check failed")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_cors_preflight():
    """Test CORS preflight request"""
    print_section("2. CORS Preflight (OPTIONS)")
    
    try:
        response = requests.options(
            f"{API_BASE}/profiles",
            headers={
                "Origin": FRONTEND_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        # Check all CORS headers
        cors_headers = {
            k: v for k, v in response.headers.items() 
            if "access-control" in k.lower()
        }
        
        print("CORS Headers:")
        for header, value in cors_headers.items():
            print(f"  {header}: {value}")
        
        required_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers",
        ]
        
        missing = [h for h in required_headers if h not in cors_headers]
        
        if not missing:
            print("✅ CORS preflight passed - All headers present")
            return True
        else:
            print(f"❌ CORS preflight failed - Missing headers: {missing}")
            return False
            
    except Exception as e:
        print(f"❌ CORS preflight error: {e}")
        return False


def test_login():
    """Test login endpoint"""
    print_section("3. Login Endpoint")
    
    admin_email = os.getenv("ADMIN_EMAIL", "pravalikan@coastalseven.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    try:
        response = requests.post(
            f"{API_BASE}/auth/login",
            data={
                "username": admin_email,
                "password": admin_password
            },
            headers={"Origin": FRONTEND_ORIGIN},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token", "")
            print(f"Token received: {token[:30]}...")
            print("✅ Login successful")
            return token
        else:
            print(f"❌ Login failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None


def test_batches_api(token):
    """Test batches API with CORS"""
    print_section("4. Batches API")
    
    if not token:
        print("⚠️  Skipping - No auth token")
        return False
    
    try:
        response = requests.get(
            f"{API_BASE}/batches",
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": FRONTEND_ORIGIN,
            },
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            batches = response.json()
            print(f"Batches count: {len(batches)}")
            
            if batches:
                batch = batches[0]
                print(f"\nSample batch structure:")
                print(f"  id: {batch.get('id')} (type: {type(batch.get('id')).__name__})")
                print(f"  name: {batch.get('name')}")
                print(f"  tech_leads_display: {batch.get('tech_leads_display')}")
                print(f"  technical_lead: {batch.get('technical_lead')}")
                
                # Verify UUID is string
                batch_id = batch.get('id')
                if isinstance(batch_id, str):
                    print(f"✅ Batch ID is string (correct)")
                else:
                    print(f"❌ Batch ID is {type(batch_id).__name__} (should be string)")
                    return False
            
            # Check CORS
            cors_header = response.headers.get("Access-Control-Allow-Origin")
            print(f"\nCORS Header: {cors_header}")
            
            if cors_header:
                print("✅ Batches API passed with CORS")
                return True
            else:
                print("❌ Batches API missing CORS header")
                return False
        else:
            print(f"❌ Batches API failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Batches API error: {e}")
        return False


def test_profiles_api(token):
    """Test profiles API with CORS"""
    print_section("5. Profiles API")
    
    if not token:
        print("⚠️  Skipping - No auth token")
        return False
    
    try:
        response = requests.get(
            f"{API_BASE}/profiles",
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": FRONTEND_ORIGIN,
            },
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            profiles = response.json()
            print(f"Profiles count: {len(profiles)}")
            
            if profiles:
                profile = profiles[0]
                print(f"\nSample profile structure:")
                print(f"  id: {profile.get('id')} (type: {type(profile.get('id')).__name__})")
                print(f"  name: {profile.get('name')}")
                print(f"  role: {profile.get('role')}")
                print(f"  batch_id: {profile.get('batch_id')} (type: {type(profile.get('batch_id')).__name__ if profile.get('batch_id') else 'None'})")
                
                # Verify UUIDs are strings
                profile_id = profile.get('id')
                if isinstance(profile_id, str):
                    print(f"✅ Profile ID is string (correct)")
                else:
                    print(f"❌ Profile ID is {type(profile_id).__name__} (should be string)")
                    return False
            
            # Check CORS
            cors_header = response.headers.get("Access-Control-Allow-Origin")
            print(f"\nCORS Header: {cors_header}")
            
            if cors_header:
                print("✅ Profiles API passed with CORS")
                return True
            else:
                print("❌ Profiles API missing CORS header")
                return False
        else:
            print(f"❌ Profiles API failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Profiles API error: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("  PRODUCTION DEPLOYMENT VERIFICATION")
    print("="*70)
    print(f"Production URL: {PRODUCTION_URL}")
    print(f"Frontend Origin: {FRONTEND_ORIGIN}")
    
    results = []
    
    # Test 1: Health
    results.append(("Health Check", test_health()))
    
    # Test 2: CORS Preflight
    results.append(("CORS Preflight", test_cors_preflight()))
    
    # Test 3: Login
    token = test_login()
    results.append(("Login", token is not None))
    
    # Test 4: Batches API
    results.append(("Batches API", test_batches_api(token)))
    
    # Test 5: Profiles API
    results.append(("Profiles API", test_profiles_api(token)))
    
    # Summary
    print_section("SUMMARY")
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n✅ All production tests passed!")
        print("\nDeployment is ready for frontend integration.")
        return 0
    else:
        print("\n❌ Some tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
