#!/usr/bin/env python3
"""
Simple test script to verify API is working and personalization is functional.
"""
import requests
import json
import sys

def test_api():
    """Test the API server with different user accounts."""
    print("🔍 Testing API server and personalization...")
    
    # Test different user accounts
    test_accounts = [
        "elk_user_account1",
        "elk_user_account2", 
        "demo_user",
        "different_user"
    ]
    
    results = {}
    
    for account in test_accounts:
        print(f"\n📊 Testing account: {account}")
        try:
            # Test with a short timeout
            response = requests.get(
                f"http://localhost:9999/api/v1/timelines/home?user_id={account}&limit=2",
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    first_post = data[0]
                    result = {
                        'posts_count': len(data),
                        'first_post_id': first_post.get('id'),
                        'content_preview': first_post.get('content', '')[:50] + '...',
                        'favourites_count': first_post.get('favourites_count', 0),
                        'favourited': first_post.get('favourited', False),
                        'reblogged': first_post.get('reblogged', False)
                    }
                    results[account] = result
                    print(f"   ✅ Success: {result['posts_count']} posts")
                    print(f"   📝 First post: {result['first_post_id']}")
                    print(f"   💖 Likes: {result['favourites_count']}")
                    print(f"   ⭐ Favorited: {result['favourited']}")
                else:
                    print(f"   ⚠️  Empty response")
                    results[account] = "empty"
            else:
                print(f"   ❌ HTTP {response.status_code}")
                results[account] = f"HTTP_{response.status_code}"
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Timeout")
            results[account] = "timeout"
        except requests.exceptions.ConnectionError:
            print(f"   🔌 Connection failed")
            results[account] = "connection_failed"
        except Exception as e:
            print(f"   💥 Error: {e}")
            results[account] = f"error_{type(e).__name__}"
    
    # Analyze personalization
    print(f"\n🎯 **Personalization Analysis:**")
    unique_responses = len(set(str(v) for v in results.values() if isinstance(v, dict)))
    working_accounts = len([v for v in results.values() if isinstance(v, dict)])
    
    if working_accounts >= 2:
        if unique_responses >= 2:
            print(f"   ✅ **Personalization WORKING**: {unique_responses} unique responses from {working_accounts} accounts")
        else:
            print(f"   ⚠️  **Same responses**: All {working_accounts} accounts got identical feeds")
    else:
        print(f"   ❌ **API issues**: Only {working_accounts} accounts responded successfully")
    
    return results

if __name__ == "__main__":
    results = test_api() 