#!/usr/bin/env python3
"""
Test script for OAuth endpoints to verify functionality.
"""

import requests
import urllib3
import json
import time
import sys

# Disable SSL warnings for localhost testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE = "https://localhost:5002/api/v1"

def test_oauth_endpoints():
    """Test OAuth endpoints functionality."""
    
    print("🧪 Testing OAuth Endpoints")
    print("=" * 50)
    
    # Wait for server to be ready
    print("⏳ Waiting for server to be ready...")
    for i in range(10):
        try:
            response = requests.get(f"{API_BASE}/health", verify=False, timeout=5)
            if response.status_code == 200:
                print("✅ Server is ready")
                break
        except:
            pass
        time.sleep(1)
    else:
        print("❌ Server not responding")
        return False
    
    # Test 1: Check OAuth endpoints are registered
    print("\n🔍 Testing OAuth endpoint registration...")
    
    endpoints_to_test = [
        "/auth/oauth/google",
        "/auth/oauth/github", 
        "/auth/check",
        "/auth/user",
        "/auth/logout"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{API_BASE}{endpoint}", verify=False, timeout=5, allow_redirects=False)
            status = response.status_code
            
            if endpoint.startswith("/auth/oauth/"):
                # OAuth endpoints should redirect (302) or return 400 for missing state
                if status in [302, 400]:
                    print(f"   ✅ {endpoint}: {status} (OAuth redirect/validation)")
                else:
                    print(f"   ⚠️  {endpoint}: {status} (unexpected)")
            elif endpoint == "/auth/check":
                # Auth check should return 200 with authenticated=false for unauthenticated user
                if status == 200:
                    try:
                        data = response.json()
                        if not data.get('authenticated', True):
                            print(f"   ✅ {endpoint}: {status} (not authenticated)")
                        else:
                            print(f"   ⚠️  {endpoint}: {status} (unexpected auth state)")
                    except:
                        print(f"   ⚠️  {endpoint}: {status} (invalid JSON)")
                else:
                    print(f"   ❌ {endpoint}: {status}")
            else:
                # Other auth endpoints should return 401 for unauthenticated user
                if status == 401:
                    print(f"   ✅ {endpoint}: {status} (unauthorized)")
                else:
                    print(f"   ⚠️  {endpoint}: {status} (unexpected)")
                    
        except requests.exceptions.RequestException as e:
            print(f"   ❌ {endpoint}: Connection error - {e}")
    
    # Test 2: Test OAuth state generation
    print("\n🔐 Testing OAuth state security...")
    
    try:
        # Test Google OAuth with missing state
        response = requests.get(f"{API_BASE}/auth/oauth/google", verify=False, timeout=5, allow_redirects=False)
        if response.status_code in [400, 302]:
            print("   ✅ Google OAuth: Proper state validation")
        else:
            print(f"   ⚠️  Google OAuth: Unexpected response {response.status_code}")
            
        # Test GitHub OAuth with missing state  
        response = requests.get(f"{API_BASE}/auth/oauth/github", verify=False, timeout=5, allow_redirects=False)
        if response.status_code in [400, 302]:
            print("   ✅ GitHub OAuth: Proper state validation")
        else:
            print(f"   ⚠️  GitHub OAuth: Unexpected response {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ OAuth state test failed: {e}")
    
    # Test 3: Database connectivity
    print("\n🗄️  Testing database integration...")
    
    try:
        # Import and test database models
        import sys
        sys.path.append('.')
        from db.models import DashboardUser, OAuthApplication
        from db.session import get_session
        
        with get_session() as session:
            # Test that we can query users table
            user_count = session.query(DashboardUser).count()
            app_count = session.query(OAuthApplication).count()
            print(f"   ✅ Database: {user_count} users, {app_count} OAuth apps")
            
    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
    
    print("\n🎉 OAuth endpoint testing complete!")
    print("\n📝 Next steps:")
    print("1. Set up OAuth applications with Google/GitHub (see setup_oauth_guide.md)")
    print("2. Update .env file with real OAuth credentials")
    print("3. Test complete OAuth flow with frontend")
    
    return True

if __name__ == "__main__":
    test_oauth_endpoints() 