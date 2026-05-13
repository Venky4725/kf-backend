#!/usr/bin/env python3
"""
Test script for attendance dashboard endpoints.

This script tests all dashboard endpoints to verify they exist and work correctly.
"""

import sys
import os
import requests
from datetime import date, timedelta

# Configuration
BASE_URL = "https://kf-backend-production-48e5.up.railway.app"
# BASE_URL = "http://localhost:8000"  # For local testing

# Test credentials (replace with actual credentials)
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "your-password"


def login(email: str, password: str) -> str:
    """Login and get JWT token."""
    print("=" * 60)
    print("LOGGING IN")
    print("=" * 60)
    print(f"Email: {email}")
    print("")
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user = data.get("user", {})
        print(f"✅ Login successful")
        print(f"User: {user.get('name')} ({user.get('role')})")
        print(f"Token: {token[:20]}...")
        print("")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.text}")
        print("")
        return None


def test_endpoint(name: str, method: str, path: str, token: str, params: dict = None):
    """Test a single endpoint."""
    print("-" * 60)
    print(f"TEST: {name}")
    print("-" * 60)
    print(f"Method: {method}")
    print(f"Path: {path}")
    if params:
        print(f"Params: {params}")
    print("")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}{path}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=params, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        print(f"Status: {response.status_code}")
        print(f"Response time: {response.elapsed.total_seconds():.2f}s")
        print("")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS")
            print("")
            print("Response structure:")
            print_json_structure(data, indent=2)
            print("")
            return True
        elif response.status_code == 404:
            print("❌ ENDPOINT NOT FOUND (404)")
            print("")
            return False
        elif response.status_code == 403:
            print("⚠️  FORBIDDEN (403) - Check RBAC")
            print(f"Response: {response.text}")
            print("")
            return False
        elif response.status_code == 422:
            print("⚠️  VALIDATION ERROR (422)")
            print(f"Response: {response.json()}")
            print("")
            return False
        else:
            print(f"❌ FAILED ({response.status_code})")
            print(f"Response: {response.text}")
            print("")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT")
        print("")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("")
        return False


def print_json_structure(data, indent=0):
    """Print JSON structure without full data."""
    prefix = "  " * indent
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{prefix}{key}:")
                print_json_structure(value, indent + 1)
            else:
                value_type = type(value).__name__
                value_preview = str(value)[:50] if value is not None else "null"
                print(f"{prefix}{key}: {value_type} = {value_preview}")
    elif isinstance(data, list):
        if len(data) > 0:
            print(f"{prefix}[{len(data)} items]")
            if len(data) > 0:
                print(f"{prefix}Sample item:")
                print_json_structure(data[0], indent + 1)
        else:
            print(f"{prefix}[]")
    else:
        print(f"{prefix}{type(data).__name__} = {str(data)[:50]}")


def main():
    """Main test function."""
    print("=" * 60)
    print("ATTENDANCE DASHBOARD ENDPOINT TESTS")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print("")
    
    # Login
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not token:
        print("❌ Cannot proceed without authentication")
        return 1
    
    # Calculate date range
    today = date.today()
    start_date = (today - timedelta(days=30)).isoformat()
    end_date = today.isoformat()
    
    # Test results
    results = []
    
    # Test 1: Dashboard Summary
    results.append(test_endpoint(
        "Dashboard Summary",
        "GET",
        "/attendance/dashboard/summary",
        token,
        params={"start_date": start_date, "end_date": end_date}
    ))
    
    # Test 2: Dashboard Distribution
    results.append(test_endpoint(
        "Dashboard Distribution",
        "GET",
        "/attendance/dashboard/distribution",
        token,
        params={"start_date": start_date, "end_date": end_date}
    ))
    
    # Test 3: Dashboard Trends
    results.append(test_endpoint(
        "Dashboard Trends",
        "GET",
        "/attendance/dashboard/trends",
        token,
        params={"days": 30}
    ))
    
    # Test 4: Dashboard Batch-wise
    results.append(test_endpoint(
        "Dashboard Batch-wise",
        "GET",
        "/attendance/dashboard/batch-wise",
        token,
        params={"start_date": start_date, "end_date": end_date}
    ))
    
    # Test 5: Analytics Distribution (Legacy)
    results.append(test_endpoint(
        "Analytics Distribution (Legacy)",
        "GET",
        "/attendance/analytics/distribution",
        token,
        params={"start_date": start_date, "end_date": end_date}
    ))
    
    # Test 6: Pending Attendance
    results.append(test_endpoint(
        "Pending Attendance",
        "GET",
        "/attendance/pending",
        token,
        params={"attendance_date": today.isoformat()}
    ))
    
    # Test 7: List Attendance
    results.append(test_endpoint(
        "List Attendance",
        "GET",
        "/attendance",
        token,
        params={"limit": 10}
    ))
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("")
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print("")
    
    if passed == total:
        print("✅ ALL TESTS PASSED")
        print("")
        print("Dashboard endpoints are working correctly!")
        print("")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("")
        print("Issues found:")
        print("- Check if endpoints are registered in router")
        print("- Verify authentication is working")
        print("- Check RBAC permissions")
        print("- Review backend logs for errors")
        print("")
        return 1


if __name__ == "__main__":
    print("")
    print("IMPORTANT: Update ADMIN_EMAIL and ADMIN_PASSWORD before running!")
    print("")
    
    # Check if credentials are set
    if ADMIN_EMAIL == "admin@example.com":
        print("⚠️  Using default credentials - please update them")
        print("")
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response != "yes":
        print("Test cancelled")
        sys.exit(0)
    
    print("")
    sys.exit(main())
