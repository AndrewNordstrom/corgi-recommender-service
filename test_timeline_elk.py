#!/usr/bin/env python3
"""
Test script to verify enhanced timeline endpoint with ELK compatibility.
"""
import requests
import json
import sys

def test_timeline():
    print("🔍 Testing enhanced timeline endpoint...")
    
    try:
        # Test the timeline endpoint
        response = requests.get(
            "http://localhost:9999/api/v1/timelines/home?user_id=demo_user&limit=3",
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Timeline returned {len(data)} posts")
            
            if data:
                first_post = data[0]
                print(f"\n📝 First post analysis:")
                print(f"   ID: {first_post.get('id', 'missing')}")
                print(f"   Favourited: {first_post.get('favourited', 'missing')}")
                print(f"   Reblogged: {first_post.get('reblogged', 'missing')}")
                print(f"   Favourites count: {first_post.get('favourites_count', 'missing')}")
                print(f"   Reblogs count: {first_post.get('reblogs_count', 'missing')}")
                
                # Check ELK camelCase fields
                print(f"\n🐪 ELK camelCase fields:")
                print(f"   favouritesCount: {first_post.get('favouritesCount', 'missing')}")
                print(f"   reblogsCount: {first_post.get('reblogsCount', 'missing')}")
                print(f"   repliesCount: {first_post.get('repliesCount', 'missing')}")
                
                # Check if it's a real Mastodon post
                print(f"\n🌐 Post metadata:")
                print(f"   Is real Mastodon post: {first_post.get('is_real_mastodon_post', 'missing')}")
                print(f"   URL: {first_post.get('url', 'missing')}")
                
                # Show complete structure of first post
                print(f"\n📋 Complete first post structure:")
                print(json.dumps(first_post, indent=2, default=str))
            else:
                print("❌ No posts returned")
        else:
            print(f"❌ API error: {response.status_code}")
            print(response.text[:200])
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False
        
    return True

def test_health():
    print("🏥 Testing API health...")
    
    try:
        response = requests.get("http://localhost:9999/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ API is healthy")
            print(f"   Database: {health_data.get('database', 'unknown')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Enhanced Timeline with ELK Compatibility\n")
    
    # Test health first
    if not test_health():
        print("\n❌ API is not responding. Please start the server first.")
        sys.exit(1)
    
    print()
    
    # Test timeline
    if test_timeline():
        print("\n✅ Timeline test completed successfully!")
    else:
        print("\n❌ Timeline test failed!")
        sys.exit(1) 