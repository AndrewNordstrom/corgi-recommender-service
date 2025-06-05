#!/usr/bin/env python3

import requests
import json
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def test_auth_endpoints():
    """Test the OAuth authentication endpoints."""
    
    base_url = "https://localhost:5002/api/v1"
    
    print("🧪 Testing OAuth Authentication Endpoints")
    print("=" * 50)
    
    # Test 1: Health check
    try:
        print("1. Testing health endpoint...")
        response = requests.get(f"{base_url.replace('/api/v1', '')}/health", verify=False, timeout=5)
        print(f"   ✅ Health: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   📊 Status: {health_data.get('status', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
    
    # Test 2: Auth status check
    try:
        print("\n2. Testing auth status endpoint...")
        response = requests.get(f"{base_url}/auth/check", verify=False, timeout=5)
        print(f"   ✅ Auth check: {response.status_code}")
        if response.status_code == 200:
            auth_data = response.json()
            print(f"   🔐 Authenticated: {auth_data.get('authenticated', False)}")
    except Exception as e:
        print(f"   ❌ Auth check failed: {e}")
    
    # Test 3: Login endpoint
    try:
        print("\n3. Testing login endpoint...")
        response = requests.get(f"{base_url}/auth/login", verify=False, timeout=5)
        print(f"   ✅ Login: {response.status_code}")
        if response.status_code == 200:
            login_data = response.json()
            print(f"   🎯 Message: {login_data.get('message', 'N/A')}")
            print(f"   🔗 Providers: {login_data.get('providers', [])}")
            if 'google_login' in login_data:
                print(f"   🟢 Google OAuth URL configured")
            if 'github_login' in login_data:
                print(f"   🟣 GitHub OAuth URL configured")
    except Exception as e:
        print(f"   ❌ Login endpoint failed: {e}")
    
    # Test 4: OAuth provider endpoints
    for provider in ['google', 'github']:
        try:
            print(f"\n4. Testing {provider} OAuth initiation...")
            response = requests.get(f"{base_url}/auth/oauth/{provider}", verify=False, timeout=5, allow_redirects=False)
            print(f"   ✅ {provider.title()} OAuth: {response.status_code}")
            if response.status_code in [302, 303]:
                print(f"   🔀 Redirect to OAuth provider (expected)")
                location = response.headers.get('Location', '')
                if 'accounts.google.com' in location or 'github.com' in location:
                    print(f"   ✅ Valid OAuth provider URL")
                else:
                    print(f"   ⚠️  Unexpected redirect: {location[:100]}...")
            elif response.status_code == 500:
                print(f"   ⚠️  Server error - likely missing OAuth credentials")
        except Exception as e:
            print(f"   ❌ {provider.title()} OAuth failed: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Authentication endpoint testing complete!")
    print("\n📝 Next steps:")
    print("   1. Set up OAuth credentials in Google/GitHub consoles")
    print("   2. Add environment variables:")
    print("      - GOOGLE_OAUTH_CLIENT_ID")
    print("      - GOOGLE_OAUTH_CLIENT_SECRET") 
    print("      - GITHUB_OAUTH_CLIENT_ID")
    print("      - GITHUB_OAUTH_CLIENT_SECRET")
    print("      - OAUTH_ENCRYPTION_KEY")
    print("   3. Test full OAuth flow with actual credentials")

if __name__ == "__main__":
    test_auth_endpoints() 