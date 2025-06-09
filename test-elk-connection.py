#!/usr/bin/env python3
"""
Enhanced ELK-Corgi Connection Test with Seamless Recommendation Verification
Verifies that recommendation posts are properly marked for seamless display in ELK
"""

import json
import sys
import requests
import time
from datetime import datetime

def print_status(message, status="info"):
    """Print colored status messages"""
    colors = {
        "success": "\033[92m✅",
        "error": "\033[91m❌",
        "warning": "\033[93m⚠️",
        "info": "\033[94mℹ️",
        "recommendation": "\033[95m✨"
    }
    reset = "\033[0m"
    print(f"{colors.get(status, '')} {message}{reset}")

def test_corgi_api_health():
    """Test if Corgi API is responding"""
    try:
        response = requests.get("http://localhost:9999/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_status(f"Corgi API Health: {data.get('status', 'unknown')}", "success")
            return True
        else:
            print_status(f"Corgi API returned status {response.status_code}", "error")
            return False
    except requests.exceptions.RequestException as e:
        print_status(f"Cannot reach Corgi API: {e}", "error")
        return False

def test_elk_frontend():
    """Test if ELK frontend is responding"""
    try:
        response = requests.get("http://localhost:3000/", timeout=5)
        if response.status_code == 200:
            print_status("ELK frontend is responding", "success")
            return True
        else:
            print_status(f"ELK frontend returned status {response.status_code}", "error")
            return False
    except requests.exceptions.RequestException as e:
        print_status(f"Cannot reach ELK frontend: {e}", "error")
        return False

def test_timeline_with_recommendations():
    """Test timeline endpoint for recommendation markers"""
    try:
        # Test the enhanced timeline endpoint
        response = requests.get("http://localhost:9999/api/v1/timelines/home", timeout=10)
        
        if response.status_code != 200:
            print_status(f"Timeline endpoint returned {response.status_code}", "error")
            return False
            
        data = response.json()
        
        if not isinstance(data, list):
            print_status("Timeline response is not a list of posts", "error")
            return False
            
        print_status(f"Retrieved {len(data)} posts from timeline", "success")
        
        # Check for recommendation markers
        recommendation_count = 0
        regular_count = 0
        
        for i, post in enumerate(data):
            if not isinstance(post, dict):
                continue
                
            is_recommendation = post.get('is_recommendation', False)
            
            if is_recommendation:
                recommendation_count += 1
                print_status(
                    f"Post {i+1}: RECOMMENDATION - {post.get('account', {}).get('display_name', 'Unknown')}",
                    "recommendation"
                )
                
                # Check for recommendation metadata
                if 'recommendation_reason' in post:
                    print(f"    Reason: {post['recommendation_reason']}")
                if 'ranking_score' in post:
                    print(f"    Score: {post['ranking_score']}")
                    
            else:
                regular_count += 1
                
        print_status(f"Found {recommendation_count} recommendations and {regular_count} regular posts", "info")
        
        if recommendation_count == 0:
            print_status("⚠️  No recommendation markers found - posts may not be properly flagged", "warning")
            print("   This means ELK frontend won't see recommendation styling")
            return False
        else:
            print_status(f"✅ Recommendations are properly marked for seamless ELK display", "success")
            return True
            
    except requests.exceptions.RequestException as e:
        print_status(f"Error testing timeline: {e}", "error")
        return False
    except json.JSONDecodeError as e:
        print_status(f"Invalid JSON in timeline response: {e}", "error")
        return False

def test_recommendation_endpoint():
    """Test the dedicated recommendations endpoint"""
    try:
        response = requests.get("http://localhost:9999/api/v1/recommendations", timeout=10)
        
        if response.status_code != 200:
            print_status(f"Recommendations endpoint returned {response.status_code}", "warning")
            return False
            
        data = response.json()
        
        if 'recommendations' in data:
            recs = data['recommendations']
            print_status(f"Dedicated recommendations endpoint has {len(recs)} recommendations", "success")
            
            for i, rec in enumerate(recs[:3]):  # Show first 3
                print(f"    Rec {i+1}: {rec.get('account', {}).get('display_name', 'Unknown')}")
                if 'recommendation_reason' in rec:
                    print(f"        Reason: {rec['recommendation_reason']}")
                    
            return True
        else:
            print_status("No recommendations found in dedicated endpoint", "warning")
            return False
            
    except requests.exceptions.RequestException as e:
        print_status(f"Error testing recommendations endpoint: {e}", "warning")
        return False

def check_seamless_integration():
    """Check if the seamless integration requirements are met"""
    print("\n" + "="*60)
    print("🔍 SEAMLESS INTEGRATION VERIFICATION")
    print("="*60)
    
    # Check if posts have the required fields for visual styling
    try:
        response = requests.get("http://localhost:9999/api/v1/timelines/home", timeout=10)
        
        if response.status_code != 200:
            print_status("Cannot verify seamless integration - timeline not accessible", "error")
            return False
            
        posts = response.json()
        
        seamless_ready = True
        rec_posts = [p for p in posts if p.get('is_recommendation', False)]
        
        if not rec_posts:
            print_status("No recommendation posts found for seamless verification", "warning")
            return False
            
        print_status(f"Verifying {len(rec_posts)} recommendation posts for seamless display", "info")
        
        for i, post in enumerate(rec_posts[:5]):  # Check first 5 recommendations
            print(f"\n📝 Recommendation Post {i+1}:")
            
            # Check required fields for seamless display
            required_fields = ['id', 'account', 'content', 'created_at']
            missing_fields = [field for field in required_fields if field not in post]
            
            if missing_fields:
                print_status(f"Missing fields: {missing_fields}", "error")
                seamless_ready = False
            else:
                print_status("All required fields present", "success")
                
            # Check account object
            account = post.get('account', {})
            account_fields = ['display_name', 'username', 'avatar']
            missing_account = [field for field in account_fields if field not in account]
            
            if missing_account:
                print_status(f"Missing account fields: {missing_account}", "warning")
            else:
                print_status("Account info complete", "success")
                
            # Check recommendation metadata
            if 'recommendation_reason' in post:
                print_status(f"Has reason: {post['recommendation_reason']}", "success")
            else:
                print_status("No recommendation reason (optional)", "info")
                
            if 'ranking_score' in post:
                print_status(f"Has ranking score: {post['ranking_score']}", "success")
            else:
                print_status("No ranking score (optional)", "info")
                
        return seamless_ready
        
    except Exception as e:
        print_status(f"Error verifying seamless integration: {e}", "error")
        return False

def provide_integration_instructions():
    """Provide instructions for seamless integration"""
    print("\n" + "="*60)
    print("🎯 SEAMLESS INTEGRATION INSTRUCTIONS")
    print("="*60)
    
    print("\n1. 📋 Copy the enhanced browser script:")
    print("   - Open fix-elk-corgi.js")
    print("   - Copy all the content")
    
    print("\n2. 🌐 In your ELK browser tab:")
    print("   - Open Developer Tools (F12)")
    print("   - Go to Console tab")
    print("   - Paste the script and press Enter")
    
    print("\n3. ✨ What you'll see:")
    print("   - Recommendation posts get subtle golden borders")
    print("   - Small '✨ Recommended' badges appear")
    print("   - Posts have a gentle glow effect")
    print("   - Dark mode is automatically supported")
    
    print("\n4. 🔄 Auto-detection:")
    print("   - New posts are automatically detected")
    print("   - No page reload needed")
    print("   - Works with infinite scroll")
    
    print("\n5. 🎨 Styling is subtle:")
    print("   - Users will think it's native ELK behavior")
    print("   - No jarring visual changes")
    print("   - Recommendations feel naturally integrated")

def main():
    """Main test function"""
    print("🧪 Enhanced ELK-Corgi Seamless Integration Test")
    print("=" * 60)
    print(f"🕒 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test individual components
    tests = [
        ("Corgi API Health", test_corgi_api_health),
        ("ELK Frontend", test_elk_frontend),
        ("Timeline with Recommendations", test_timeline_with_recommendations),
        ("Recommendations Endpoint", test_recommendation_endpoint),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        print("-" * 40)
        results[test_name] = test_func()
    
    # Seamless integration verification
    seamless_ready = check_seamless_integration()
    results["Seamless Integration"] = seamless_ready
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        color = "success" if passed else "error"
        print_status(f"{test_name}: {status}", color)
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if seamless_ready:
        print_status("🎉 System is ready for seamless recommendations!", "success")
        provide_integration_instructions()
    else:
        print_status("⚠️  Seamless integration needs attention", "warning")
        print("\nPlease check:")
        print("- Corgi API is running on port 9999")
        print("- Timeline endpoint returns posts with is_recommendation flags")
        print("- Posts have complete account and content data")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 