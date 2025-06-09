#!/usr/bin/env python3
"""
Load real Mastodon posts from cold_start_posts.json into Corgi database.

These are REAL posts from REAL Mastodon users that should be recommended.
"""

import json
import requests
import time
from datetime import datetime

def load_mastodon_posts():
    """Load real Mastodon posts into the database."""
    
    # Load the REAL Mastodon posts
    with open('tools/testing/data/cold_start_posts.json', 'r') as f:
        real_posts = json.load(f)

    print(f'📚 Found {len(real_posts)} REAL Mastodon posts from various instances')
    print(f'🌐 These are actual posts from real users that Corgi should recommend!')

    success_count = 0
    
    for i, post in enumerate(real_posts[:15]):  # Load first 15 real posts
        try:
            # Extract the actual Mastodon content
            post_id = post["id"]  # This is already formatted like "real_114650..."
            author_username = post["account"]["username"]
            author_display_name = post["account"].get("display_name", author_username)
            content = post["content"]  # This is the REAL Mastodon post content
            
            print(f'\n📝 Loading real post from @{author_username}:')
            print(f'   Content preview: {content[:80]}...')
            
            # Format for Corgi API - store the FULL Mastodon post
            corgi_post = {
                "post_id": post_id,
                "author_id": post["account"]["id"],
                "author_name": author_username,
                "content": content,  # Real Mastodon content
                "content_type": "text",
                "created_at": post["created_at"],
                "interaction_counts": {
                    "favorites": post.get("favourites_count", 0),
                    "reblogs": post.get("reblogs_count", 0),
                    "replies": post.get("replies_count", 0)
                },
                "mastodon_post": post  # Store the COMPLETE Mastodon post object
            }
            
            response = requests.post('http://localhost:9999/api/v1/posts', 
                                   json=corgi_post, timeout=10)
            
            if response.status_code in [200, 201]:
                print(f'✅ {i+1}/{len(real_posts[:15])}: Loaded real post from @{author_username}')
                success_count += 1
            else:
                print(f'❌ {i+1}/{len(real_posts[:15])}: Failed - {response.status_code}')
                if response.text:
                    print(f'   Error: {response.text[:100]}...')
                    
        except Exception as e:
            print(f'❌ {i+1}/{len(real_posts[:15])}: Exception - {e}')
        
        # Small delay
        time.sleep(0.3)

    print(f'\n🎉 Successfully loaded {success_count}/{len(real_posts[:15])} REAL Mastodon posts!')
    
    if success_count > 0:
        print(f'\n🔄 Now regenerating recommendations to include real content...')
        
        # Regenerate rankings to include the new real posts
        try:
            regen_response = requests.post(
                'http://localhost:9999/api/v1/recommendations/rankings/generate',
                json={"user_id": "demo_user", "force_refresh": True},
                timeout=15
            )
            
            if regen_response.status_code == 200:
                result = regen_response.json()
                print(f'✅ Generated {result.get("count", "unknown")} recommendations!')
                print(f'🚀 Refresh your ELK page to see REAL Mastodon posts!')
            else:
                print(f'⚠️ Recommendation generation had issues: {regen_response.status_code}')
                
        except Exception as e:
            print(f'⚠️ Could not regenerate recommendations: {e}')
            print(f'💡 Try manually: curl -X POST "http://localhost:9999/api/v1/recommendations/rankings/generate" -H "Content-Type: application/json" -d \'{"user_id": "demo_user", "force_refresh": true}\'')
    
    else:
        print(f'\n💡 No posts were loaded. The posts API might have issues.')
        print(f'🔍 Check if your Corgi API server is running on port 9999')

if __name__ == '__main__':
    load_mastodon_posts() 