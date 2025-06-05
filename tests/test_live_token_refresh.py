#!/usr/bin/env python3
"""
Live Token Refresh Testing Script for Corgi Recommender Service

This script guides through comprehensive testing of the OAuth token refresh mechanism
with your real Mastodon account connection.

Usage:
    python3 test_live_token_refresh.py
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from urllib.parse import urljoin

# Configuration
BASE_URL = "http://localhost:5000"
TEST_USER_ID = "user_94fa7744e3f781ce"  # Your existing user ID
MASTODON_INSTANCE = "mastodon.social"

class TokenRefreshTester:
    def __init__(self, base_url=BASE_URL, user_id=TEST_USER_ID):
        self.base_url = base_url
        self.user_id = user_id
        self.session = requests.Session()
        
    def print_step(self, step_num, title, description=""):
        """Print formatted step header."""
        print(f"\n{'='*60}")
        print(f"STEP {step_num}: {title}")
        print(f"{'='*60}")
        if description:
            print(f"Description: {description}")
        print()
    
    def print_result(self, success, data, title="Result"):
        """Print formatted result."""
        status = "✅ SUCCESS" if success else "❌ FAILURE"
        print(f"\n{title}: {status}")
        if isinstance(data, dict):
            print(json.dumps(data, indent=2, default=str))
        else:
            print(data)
        print("-" * 40)
    
    def test_server_health(self):
        """Test if the Corgi server is running."""
        self.print_step(1, "Server Health Check", 
                       "Verify the Corgi backend server is running and accessible")
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            success = response.status_code == 200
            self.print_result(success, {
                "status_code": response.status_code,
                "response": response.json() if success else response.text
            })
            return success
        except Exception as e:
            self.print_result(False, f"Connection error: {e}")
            return False
    
    def check_user_oauth_status(self):
        """Check the current OAuth status for the test user."""
        self.print_step(2, "Current OAuth Status Check",
                       f"Check existing OAuth connection for user {self.user_id}")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/oauth/status/{self.user_id}")
            success = response.status_code == 200
            data = response.json() if success else {"error": response.text}
            
            self.print_result(success, data)
            
            if success:
                print("📋 CURRENT STATUS SUMMARY:")
                print(f"   Username: {data.get('username', 'unknown')}")
                print(f"   Instance: {data.get('instance', 'unknown')}")
                print(f"   Token Valid: {data.get('token_valid', False)}")
                print(f"   Privacy Level: {data.get('privacy_level', 'unknown')}")
                print(f"   Linked At: {data.get('linked_at', 'unknown')}")
            
            return success, data
        except Exception as e:
            self.print_result(False, f"Request error: {e}")
            return False, {}
    
    def check_token_detailed_status(self):
        """Check detailed token expiration and refresh status."""
        self.print_step(3, "Detailed Token Status Check",
                       "Check token expiration, refresh token availability, and refresh capability")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/oauth/token-status/{self.user_id}")
            success = response.status_code == 200
            data = response.json() if success else {"error": response.text}
            
            self.print_result(success, data)
            
            if success:
                print("📋 TOKEN STATUS SUMMARY:")
                print(f"   Token Expired: {data.get('token_expired', 'unknown')}")
                print(f"   Expires At: {data.get('expires_at', 'unknown')}")
                print(f"   Has Refresh Token: {data.get('has_refresh_token', False)}")
                print(f"   Can Refresh: {data.get('can_refresh', False)}")
                print(f"   Token Scope: {data.get('token_scope', 'unknown')}")
            
            return success, data
        except Exception as e:
            self.print_result(False, f"Request error: {e}")
            return False, {}
    
    def simulate_token_expiry(self):
        """Temporarily modify the database to simulate token expiry."""
        self.print_step(4, "Simulate Token Expiry",
                       "Modify token_expires_at in database to force expiry condition")
        
        print("🔧 DATABASE MODIFICATION COMMAND:")
        print("Execute this SQL command to simulate expiry:")
        print()
        print("UPDATE user_identities")
        print(f"SET token_expires_at = NOW() - INTERVAL '1 hour'")
        print(f"WHERE user_id = '{self.user_id}';")
        print()
        
        input("Press Enter after executing the database command...")
        
        # Verify the expiry was set
        success, data = self.check_token_detailed_status()
        if success and data.get('token_expired'):
            print("✅ Token expiry simulation successful!")
            return True
        else:
            print("❌ Token still appears valid - check database command")
            return False
    
    def test_manual_refresh(self):
        """Test the manual refresh endpoint."""
        self.print_step(5, "Manual Token Refresh Test",
                       "Use the manual refresh endpoint to trigger token refresh")
        
        try:
            response = self.session.post(f"{self.base_url}/api/v1/oauth/refresh/{self.user_id}")
            success = response.status_code == 200
            data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"text": response.text}
            
            self.print_result(success, data)
            
            if success:
                print("📋 REFRESH RESULT SUMMARY:")
                print(f"   Status: {data.get('status', 'unknown')}")
                print(f"   New Expires At: {data.get('expires_at', 'unknown')}")
                print(f"   Scope: {data.get('scope', 'unknown')}")
            
            return success, data
        except Exception as e:
            self.print_result(False, f"Request error: {e}")
            return False, {}
    
    def verify_token_renewal(self):
        """Verify that the token was successfully renewed."""
        self.print_step(6, "Token Renewal Verification",
                       "Check that token expiry was updated and token is now valid")
        
        success, data = self.check_token_detailed_status()
        
        if success:
            print("📋 POST-REFRESH STATUS:")
            print(f"   Token Expired: {data.get('token_expired', 'unknown')}")
            print(f"   New Expires At: {data.get('expires_at', 'unknown')}")
            
            # Check if OAuth status shows token as valid now
            oauth_success, oauth_data = self.check_user_oauth_status()
            if oauth_success:
                print(f"   Token Valid (OAuth Check): {oauth_data.get('token_valid', False)}")
        
        return success
    
    def test_authenticated_api_call(self):
        """Test making an authenticated API call through Corgi proxy."""
        self.print_step(7, "Authenticated API Call Test",
                       "Make an authenticated call to Mastodon via Corgi proxy to confirm new token works")
        
        # First get the current token from status
        try:
            status_response = self.session.get(f"{self.base_url}/api/v1/oauth/status/{self.user_id}")
            if status_response.status_code != 200:
                self.print_result(False, "Cannot get user status for token")
                return False
            
            # Make a test call to verify credentials via proxy
            proxy_response = self.session.get(
                f"{self.base_url}/api/v1/accounts/verify_credentials",
                headers={
                    'Authorization': f'Bearer {self.user_id}',  # Using internal user_id for proxy auth
                    'X-Mastodon-Instance': MASTODON_INSTANCE
                }
            )
            
            success = proxy_response.status_code == 200
            data = proxy_response.json() if success else {
                "status_code": proxy_response.status_code,
                "error": proxy_response.text
            }
            
            self.print_result(success, data)
            
            if success:
                print("📋 AUTHENTICATED CALL SUCCESS:")
                print(f"   Username: {data.get('username', 'unknown')}")
                print(f"   Display Name: {data.get('display_name', 'unknown')}")
                print(f"   Account ID: {data.get('id', 'unknown')}")
            
            return success
        except Exception as e:
            self.print_result(False, f"Request error: {e}")
            return False
    
    def test_refresh_failure_scenario(self):
        """Simulate and test refresh failure handling."""
        self.print_step(8, "Refresh Failure Scenario (Optional)",
                       "Test how system handles refresh token failures")
        
        print("🔧 To test refresh failure scenarios:")
        print("1. Manually invalidate refresh_token in database:")
        print(f"   UPDATE user_identities SET refresh_token = 'invalid_token' WHERE user_id = '{self.user_id}';")
        print("2. Then run the refresh test again")
        print("3. Expected: Refresh should fail with appropriate error message")
        print()
        
        should_test = input("Test refresh failure scenario? (y/N): ").lower().strip() == 'y'
        
        if should_test:
            input("Press Enter after invalidating refresh token in database...")
            
            # Try refresh with invalid token
            try:
                response = self.session.post(f"{self.base_url}/api/v1/oauth/refresh/{self.user_id}")
                success = response.status_code == 200
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"text": response.text}
                
                # For failure testing, we expect this to fail
                expected_failure = not success
                self.print_result(expected_failure, data, "Expected Failure Result")
                
                if expected_failure:
                    print("✅ Failure handling working correctly!")
                else:
                    print("❌ Expected failure but refresh succeeded - check implementation")
                
                return expected_failure
            except Exception as e:
                self.print_result(True, f"Exception as expected: {e}", "Expected Failure Result")
                return True
        else:
            print("⏭️  Skipping failure scenario test")
            return True
    
    def restore_valid_state(self):
        """Help restore the user to a valid state after testing."""
        self.print_step(9, "Restore Valid State",
                       "Restore user to valid OAuth state after testing")
        
        print("🔧 To restore valid state after testing:")
        print("1. If refresh token was invalidated during failure testing, you may need to:")
        print("   a) Reset token_expires_at to future time:")
        print(f"      UPDATE user_identities SET token_expires_at = NOW() + INTERVAL '1 hour' WHERE user_id = '{self.user_id}';")
        print("   b) OR re-authenticate via OAuth flow if refresh token is permanently invalid")
        print()
        print("2. If only expiry was simulated, refresh should have restored valid state")
        print()
        
        # Final status check
        success, data = self.check_user_oauth_status()
        
        if success and data.get('token_valid'):
            print("✅ User is in valid OAuth state!")
        else:
            print("⚠️  User may need re-authentication")
            print("   Visit: http://localhost:5000/api/v1/oauth/connect-ui")
    
    def run_full_test_suite(self):
        """Run the complete token refresh test suite."""
        print("🚀 CORGI TOKEN REFRESH LIVE TESTING SUITE")
        print("=" * 60)
        print(f"Testing user: {self.user_id}")
        print(f"Server: {self.base_url}")
        print(f"Mastodon Instance: {MASTODON_INSTANCE}")
        
        # Test sequence
        tests = [
            ("Server Health", self.test_server_health),
            ("OAuth Status", lambda: self.check_user_oauth_status()[0]),
            ("Token Status", lambda: self.check_token_detailed_status()[0]),
        ]
        
        # Run prerequisite tests
        for test_name, test_func in tests:
            if not test_func():
                print(f"❌ Prerequisites failed at: {test_name}")
                print("Please resolve issues before continuing with refresh testing.")
                return False
        
        print("\n🎯 STARTING REFRESH MECHANISM TESTING")
        
        # Core refresh testing sequence
        if not self.simulate_token_expiry():
            print("❌ Cannot simulate token expiry - stopping test")
            return False
        
        refresh_success, _ = self.test_manual_refresh()
        
        if refresh_success:
            self.verify_token_renewal()
            self.test_authenticated_api_call()
        
        # Optional failure testing
        self.test_refresh_failure_scenario()
        
        # Restore state
        self.restore_valid_state()
        
        print("\n🏁 TESTING COMPLETE!")
        print("Check the results above to verify token refresh functionality.")
        
        return True

def main():
    """Main testing function."""
    print("Corgi Token Refresh Live Testing")
    print("=" * 40)
    print()
    
    # Check if user wants to run full suite or individual tests
    print("Available test modes:")
    print("1. Full test suite (recommended)")
    print("2. Individual test selection")
    print("3. Quick status check only")
    
    choice = input("\nSelect mode (1-3): ").strip()
    
    tester = TokenRefreshTester()
    
    if choice == "1":
        tester.run_full_test_suite()
    elif choice == "2":
        print("\nIndividual tests - select which to run:")
        print("(Implementation left as exercise - for now run full suite)")
        tester.run_full_test_suite()
    elif choice == "3":
        tester.test_server_health()
        tester.check_user_oauth_status()
        tester.check_token_detailed_status()
    else:
        print("Invalid choice - running full suite")
        tester.run_full_test_suite()

if __name__ == "__main__":
    main() 