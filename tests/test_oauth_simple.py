#!/usr/bin/env python3
"""
Simple OAuth test script to diagnose GitHub OAuth issues.
"""

import requests
import urllib3
import time

# Disable SSL warnings for localhost testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_backend_health():
    """Test if backend server is responding."""
    print("🔍 Testing backend server health...")
    try:
        response = requests.get(
            'https://localhost:5002/api/v1/auth/check',
            verify=False,
            timeout=10
        )
        print(f"✅ Backend health check: {response.status_code}")
        print(f"   Response: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend server not responding: {e}")
        return False

def test_oauth_redirect():
    """Test OAuth redirect functionality."""
    print("\n🔍 Testing GitHub OAuth redirect...")
    try:
        response = requests.get(
            'https://localhost:5002/api/v1/auth/oauth/github',
            verify=False,
            allow_redirects=False,
            timeout=10
        )
        
        print(f"✅ OAuth endpoint status: {response.status_code}")
        
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if 'github.com' in location:
                print(f"✅ Correctly redirects to GitHub: {location[:100]}...")
                return True
            else:
                print(f"❌ Redirects to wrong location: {location}")
        else:
            print(f"❌ Expected 302 redirect, got {response.status_code}")
            print(f"   Response: {response.text[:200]}")
        
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ OAuth test failed: {e}")
        return False

def main():
    print("🐕 Corgi OAuth Diagnostic Tool")
    print("=" * 40)
    
    # Test 1: Backend health
    if not test_backend_health():
        print("\n💡 Fix: Start the backend server with: python3 run_server.py")
        return
    
    # Test 2: OAuth redirect
    if not test_oauth_redirect():
        print("\n💡 Possible fixes:")
        print("   1. Check GitHub OAuth app configuration")
        print("   2. Verify .env has correct GITHUB_OAUTH_CLIENT_ID and GITHUB_OAUTH_CLIENT_SECRET")
        print("   3. Update GitHub app Homepage URL to: http://localhost:3004")
        return
    
    print("\n🎉 OAuth flow looks good! Try the frontend now.")
    print(f"   Frontend: http://localhost:3004/dashboard/login")

if __name__ == '__main__':
    main() 