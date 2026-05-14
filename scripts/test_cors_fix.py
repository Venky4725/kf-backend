#!/usr/bin/env python3
"""
Quick test to verify CORS configuration is working correctly.
This simulates a browser preflight request.
"""

import requests
import sys

# Test both local and production
ENDPOINTS = [
    ("Local", "http://localhost:8000/api/health"),
    ("Production", "https://your-railway-url.railway.app/api/health"),  # Update with actual URL
]

ORIGINS = [
    "https://kf-frontend-rho.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def test_cors(endpoint_name, url, origin):
    """Test CORS preflight request"""
    print(f"\n{'='*60}")
    print(f"Testing: {endpoint_name}")
    print(f"Origin: {origin}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    # Preflight request (OPTIONS)
    try:
        response = requests.options(
            url,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
            timeout=5
        )
        
        print(f"Status: {response.status_code}")
        print(f"Headers:")
        for header, value in response.headers.items():
            if "access-control" in header.lower():
                print(f"  {header}: {value}")
        
        # Check if CORS headers are present
        if "Access-Control-Allow-Origin" in response.headers:
            allowed_origin = response.headers["Access-Control-Allow-Origin"]
            if allowed_origin == origin or allowed_origin == "*":
                print(f"✅ CORS OK - Origin allowed: {allowed_origin}")
                return True
            else:
                print(f"❌ CORS FAIL - Wrong origin: {allowed_origin}")
                return False
        else:
            print(f"❌ CORS FAIL - No Access-Control-Allow-Origin header")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def test_actual_request(endpoint_name, url, origin):
    """Test actual GET request"""
    print(f"\n{'='*60}")
    print(f"Testing actual request: {endpoint_name}")
    print(f"Origin: {origin}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(
            url,
            headers={"Origin": origin},
            timeout=5
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if "Access-Control-Allow-Origin" in response.headers:
            print(f"✅ CORS header present: {response.headers['Access-Control-Allow-Origin']}")
            return True
        else:
            print(f"❌ No CORS header in response")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("  CORS CONFIGURATION TEST")
    print("="*60)
    
    results = []
    
    for endpoint_name, url in ENDPOINTS:
        for origin in ORIGINS:
            # Test preflight
            preflight_ok = test_cors(endpoint_name, url, origin)
            results.append((endpoint_name, origin, "Preflight", preflight_ok))
            
            # Test actual request
            actual_ok = test_actual_request(endpoint_name, url, origin)
            results.append((endpoint_name, origin, "Actual", actual_ok))
    
    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    
    for endpoint, origin, test_type, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {endpoint} - {origin} - {test_type}")
    
    # Overall result
    all_passed = all(success for _, _, _, success in results)
    
    if all_passed:
        print("\n✅ All CORS tests passed!")
        return 0
    else:
        print("\n❌ Some CORS tests failed. Check configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
