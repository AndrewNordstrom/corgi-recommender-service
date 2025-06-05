#!/usr/bin/env python3
"""
OAuth Flow Testing Script

This script helps test the complete GitHub OAuth authentication flow including:
1. Environment configuration validation
2. Backend server startup
3. Frontend server status
4. OAuth endpoint testing
5. Database integration verification

Usage: python3 test_oauth_flow.py
"""

import os
import sys
import time
import requests
import subprocess
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for testing
urllib3.disable_warnings(InsecureRequestWarning)

class OAuthFlowTester:
    def __init__(self):
        self.api_base = "https://localhost:5002/api/v1"
        self.frontend_base = "http://localhost:3001"  # Based on the logs showing port 3001
        self.test_results = []
    
    def log_test(self, test_name, status, details=""):
        """Log test results."""
        symbol = "✅" if status else "❌"
        self.test_results.append((test_name, status, details))
        print(f"{symbol} {test_name}: {details}")
    
    def check_environment_variables(self):
        """Check if required OAuth environment variables are set."""
        print("\n🔍 Checking Environment Variables...")
        
        required_vars = [
            'GITHUB_OAUTH_CLIENT_ID',
            'GITHUB_OAUTH_CLIENT_SECRET',
            'CORGI_DB_URL'
        ]
        
        missing_vars = []
        for var in required_vars:
            value = os.getenv(var)
            if not value or value in ['your_github_client_id_here', 'YOUR_GITHUB_CLIENT_ID_HERE']:
                missing_vars.append(var)
            else:
                # Mask secrets for display
                display_value = value if 'SECRET' not in var else f"{'*' * (len(value) - 4)}{value[-4:]}"
                self.log_test(f"Environment Variable {var}", True, display_value)
        
        if missing_vars:
            self.log_test("Environment Configuration", False, f"Missing: {', '.join(missing_vars)}")
            return False
        
        self.log_test("Environment Configuration", True, "All required variables set")
        return True
    
    def check_backend_server(self):
        """Check if backend server is running and OAuth endpoints are available."""
        print("\n🖥️  Checking Backend Server...")
        
        try:
            # Test health endpoint
            response = requests.get(f"{self.api_base}/health", 
                                  verify=False, timeout=5)
            if response.status_code == 200:
                self.log_test("Backend Server Health", True, f"Status: {response.status_code}")
            else:
                self.log_test("Backend Server Health", False, f"Status: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_test("Backend Server Health", False, f"Connection error: {e}")
            return False
        
        # Test OAuth endpoints
        oauth_endpoints = [
            '/auth/check',
            '/auth/login', 
            '/auth/oauth/github',
            '/auth/oauth/google'
        ]
        
        for endpoint in oauth_endpoints:
            try:
                response = requests.get(f"{self.api_base}{endpoint}", 
                                      verify=False, timeout=5)
                # For OAuth endpoints, expect either 200 or 302 (redirect)
                if response.status_code in [200, 302]:
                    self.log_test(f"OAuth Endpoint {endpoint}", True, f"Status: {response.status_code}")
                else:
                    self.log_test(f"OAuth Endpoint {endpoint}", False, f"Status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                self.log_test(f"OAuth Endpoint {endpoint}", False, f"Error: {e}")
        
        return True
    
    def check_frontend_server(self):
        """Check if frontend server is running."""
        print("\n🌐 Checking Frontend Server...")
        
        # Try both common ports
        frontend_ports = [3000, 3001]
        frontend_running = False
        
        for port in frontend_ports:
            try:
                response = requests.get(f"http://localhost:{port}", timeout=5)
                if response.status_code == 200:
                    self.frontend_base = f"http://localhost:{port}"
                    self.log_test(f"Frontend Server (port {port})", True, f"Available at {self.frontend_base}")
                    frontend_running = True
                    break
            except requests.exceptions.RequestException:
                continue
        
        if not frontend_running:
            self.log_test("Frontend Server", False, "Not running on ports 3000 or 3001")
            print("   💡 Start frontend with: cd frontend && npm run dev")
        
        return frontend_running
    
    def test_github_oauth_flow(self):
        """Test the GitHub OAuth flow initiation."""
        print("\n🔐 Testing GitHub OAuth Flow...")
        
        try:
            # Test OAuth initiation
            response = requests.get(f"{self.api_base}/auth/oauth/github", 
                                  verify=False, timeout=10, allow_redirects=False)
            
            if response.status_code == 302:
                location = response.headers.get('Location', '')
                if 'github.com' in location and 'oauth/authorize' in location:
                    self.log_test("GitHub OAuth Initiation", True, "Redirects to GitHub correctly")
                    self.log_test("GitHub OAuth URL", True, f"Target: {location[:100]}...")
                    return True
                else:
                    self.log_test("GitHub OAuth Initiation", False, f"Unexpected redirect: {location}")
            else:
                self.log_test("GitHub OAuth Initiation", False, f"Status: {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            self.log_test("GitHub OAuth Initiation", False, f"Error: {e}")
        
        return False
    
    def test_database_connection(self):
        """Test database connection and RBAC setup."""
        print("\n🗄️  Testing Database Connection...")
        
        try:
            # Add project root to path
            sys.path.insert(0, os.path.dirname(__file__))
            
            from db.session import db_session
            from db.models import Role, Permission, DashboardUser
            
            session = db_session().__enter__()
            
            # Test basic database connectivity
            roles_count = session.query(Role).count()
            permissions_count = session.query(Permission).count()
            users_count = session.query(DashboardUser).count()
            
            self.log_test("Database Connection", True, "Successfully connected")
            self.log_test("RBAC Setup", True, f"{roles_count} roles, {permissions_count} permissions")
            self.log_test("User Database", True, f"{users_count} users registered")
            
            session.__exit__(None, None, None)
            return True
            
        except Exception as e:
            self.log_test("Database Connection", False, f"Error: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run all OAuth flow tests."""
        print("🧪 OAuth Flow Comprehensive Testing")
        print("=" * 50)
        
        # Environment setup
        env_ok = self.check_environment_variables()
        
        # Database connectivity
        db_ok = self.test_database_connection()
        
        # Backend server
        backend_ok = self.check_backend_server()
        
        # Frontend server
        frontend_ok = self.check_frontend_server()
        
        # OAuth flow
        oauth_ok = self.test_github_oauth_flow()
        
        # Summary
        print("\n📊 Test Summary")
        print("=" * 30)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, status, _ in self.test_results if status)
        
        for test_name, status, details in self.test_results:
            symbol = "✅" if status else "❌"
            print(f"{symbol} {test_name}")
        
        print(f"\n🎯 Results: {passed_tests}/{total_tests} tests passed")
        
        # Next steps guidance
        print("\n🚀 Next Steps:")
        
        if not env_ok:
            print("1. ❗ Run 'python3 setup_oauth_env_dev.py' to configure your .env file")
        
        if not backend_ok:
            print("2. 🖥️  Start backend server: python3 run_server.py")
        
        if not frontend_ok:
            print("3. 🌐 Start frontend server: cd frontend && npm run dev")
        
        if env_ok and backend_ok and frontend_ok and oauth_ok:
            print("✨ Everything looks good! Ready to test OAuth flow:")
            print(f"   1. Open {self.frontend_base}/dashboard/login")
            print("   2. Click 'Continue with GitHub'")
            print("   3. Complete GitHub authentication")
            print("   4. Verify redirect back to dashboard")
            
            print("\n🔍 Things to Watch For:")
            print("   • GitHub authorization page loads correctly")
            print("   • After GitHub auth, redirects to /api/v1/auth/oauth/github/callback")
            print("   • User session is created in database")
            print("   • Dashboard shows authenticated user info")
        
        return passed_tests == total_tests

def main():
    """Main test execution."""
    tester = OAuthFlowTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 All tests passed! OAuth system is ready for testing.")
    else:
        print("\n⚠️  Some tests failed. Address the issues above before proceeding.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 