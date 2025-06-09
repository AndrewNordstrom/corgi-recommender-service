#!/usr/bin/env python3
"""
ELK Integration End-to-End Test Script

This script tests the complete user authentication and integration flow
between ELK frontend and Corgi Recommender API.
"""

import requests
import json
import sys
import time

def test_service_health():
    """Test that both services are running."""
    print("🔍 Testing service health...")
    
    # Test Corgi API
    try:
        response = requests.get("http://localhost:5002/health", timeout=5)
        if response.status_code == 200:
            print("✅ Corgi API is healthy")
        else:
            print(f"❌ Corgi API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Corgi API is not responding: {e}")
        return False
    
    # Test ELK Frontend
    try:
        response = requests.get("http://localhost:5314", timeout=5)
        if response.status_code == 200:
            print("✅ ELK Frontend is healthy")
        else:
            print(f"❌ ELK Frontend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ELK Frontend is not responding: {e}")
        return False
    
    return True

def test_mastodon_compatibility():
    """Test Mastodon API compatibility endpoints."""
    print("\n🔍 Testing Mastodon API compatibility...")
    
    # Test instance endpoint
    try:
        response = requests.get("http://localhost:5002/api/v1/instance", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Instance endpoint working - Title: {data.get('title')}")
            print(f"   URI: {data.get('uri')}, Version: {data.get('version')}")
        else:
            print(f"❌ Instance endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Instance endpoint error: {e}")
        return False
    
    # Test verify credentials endpoint
    try:
        response = requests.get("http://localhost:5002/api/v1/accounts/verify_credentials", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Verify credentials working - User: {data.get('username')}")
        else:
            print(f"❌ Verify credentials failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Verify credentials error: {e}")
    
    return True

def test_oauth_flow():
    """Test the complete OAuth authentication flow."""
    print("\n🔍 Testing OAuth authentication flow...")
    
    # Step 1: Test OAuth authorization endpoint
    print("   Step 1: Testing OAuth authorization endpoint...")
    try:
        auth_url = "http://localhost:5002/oauth/authorize"
        params = {
            "client_id": "elk_integration_test",
            "redirect_uri": "http://localhost:5314/oauth/callback",
            "response_type": "code",
            "scope": "read write follow"
        }
        
        response = requests.get(auth_url, params=params, timeout=5)
        if response.status_code == 200 and "Authorize ELK" in response.text:
            print("   ✅ OAuth authorization page is working")
        else:
            print(f"   ❌ OAuth authorization failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ OAuth authorization error: {e}")
        return False
    
    # Step 2: Test OAuth token endpoint
    print("   Step 2: Testing OAuth token endpoint...")
    try:
        token_url = "http://localhost:5002/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "code": "test_auth_code",
            "client_id": "elk_integration_test",
            "redirect_uri": "http://localhost:5314/oauth/callback"
        }
        
        response = requests.post(token_url, data=data, timeout=5)
        if response.status_code == 200:
            token_data = response.json()
            print(f"   ✅ OAuth token endpoint working - Token type: {token_data.get('token_type')}")
            print(f"      Access token: {token_data.get('access_token')[:20]}...")
            return token_data.get('access_token')
        else:
            print(f"   ❌ OAuth token failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ OAuth token error: {e}")
        return False

def test_authenticated_requests(access_token):
    """Test API requests with authentication."""
    print("\n🔍 Testing authenticated API requests...")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test authenticated verify credentials
    try:
        response = requests.get(
            "http://localhost:5002/api/v1/accounts/verify_credentials", 
            headers=headers, 
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Authenticated request working - User: {data.get('display_name')}")
        else:
            print(f"❌ Authenticated request failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Authenticated request error: {e}")

def test_elk_configuration():
    """Test ELK configuration."""
    print("\n🔍 Testing ELK configuration...")
    
    try:
        # Check if ELK .env file exists
        import os
        env_path = "/Users/andrewnordstrom/Elk_Corgi/ELK/.env"
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                content = f.read()
                if "NUXT_PUBLIC_DEFAULT_SERVER=http://localhost:5002" in content:
                    print("✅ ELK is configured to use Corgi API as default server")
                else:
                    print("❌ ELK configuration is incorrect")
                    print(f"   Found: {content.strip()}")
        else:
            print("❌ ELK .env file not found")
    except Exception as e:
        print(f"❌ ELK configuration check error: {e}")

def main():
    """Run the complete integration test suite."""
    print("🚀 ELK Integration End-to-End Test")
    print("=" * 50)
    
    # Test 1: Service Health
    if not test_service_health():
        print("\n❌ Service health check failed. Please ensure both services are running.")
        sys.exit(1)
    
    # Test 2: Mastodon Compatibility
    if not test_mastodon_compatibility():
        print("\n❌ Mastodon compatibility test failed.")
        sys.exit(1)
    
    # Test 3: OAuth Flow
    access_token = test_oauth_flow()
    if not access_token:
        print("\n❌ OAuth flow test failed.")
        sys.exit(1)
    
    # Test 4: Authenticated Requests
    test_authenticated_requests(access_token)
    
    # Test 5: ELK Configuration
    test_elk_configuration()
    
    print("\n" + "=" * 50)
    print("🎉 INTEGRATION TEST COMPLETE!")
    print("\n📋 Manual Browser Test Instructions:")
    print("1. Open a private/incognito browser window")
    print("2. Navigate to: http://localhost:5314")
    print("3. Look for a 'Sign in' or 'Log in' button")
    print("4. Click the sign in button")
    print("5. Expected: You should be redirected to:")
    print("   http://localhost:5002/oauth/authorize?...")
    print("6. Expected: You should see the Corgi OAuth authorization page")
    print("7. Click 'Authorize ELK' button")
    print("8. Expected: You should be redirected back to ELK")
    print("\n✨ If you see the Corgi authorization page, the integration is working!")

if __name__ == "__main__":
    main() 