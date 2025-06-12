#!/usr/bin/env python3
"""Test the timeline API endpoint"""

import requests
import json

def test_timeline():
    url = "http://localhost:9999/api/v1/recommendations/timeline"
    params = {
        "user_id": "test_user",
        "limit": 5
    }
    
    print(f"Testing: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, params=params)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Posts returned: {len(data)}")
            
            if data:
                print("\nFirst 3 posts:")
                for i, post in enumerate(data[:3]):
                    print(f"\n{i+1}. Post ID: {post.get('id')}")
                    print(f"   Content: {post.get('content', '')[:100]}...")
                    print(f"   Created: {post.get('created_at')}")
                    print(f"   Likes: {post.get('favourites_count', 0)}, Reblogs: {post.get('reblogs_count', 0)}")
                    print(f"   Is real post: {post.get('is_real_mastodon_post', False)}")
            else:
                print("No posts returned!")
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_timeline() 