#!/usr/bin/env python3
"""Load real Mastodon posts into Corgi database."""

import json
import requests
import time

def load_posts():
    """Load real posts from the fetched data."""
    # Load the fetched posts
    with open('tools/testing/data/cold_start_posts.json', 'r') as f:
        posts = json.load(f)

    print(f'📚 Loaded {len(posts)} real Mastodon posts')

    # Add them to Corgi database via API
    success_count = 0
    for i, post in enumerate(posts[:10]):  # Load first 10 posts
        try:
            # Transform the post to Corgi API format
            corgi_post = {
                "post_id": post["id"],
                "author_id": post["account"]["id"],
                "author_name": post["account"]["username"],
                "content": post["content"],
                "content_type": "text",
                "created_at": post["created_at"],
                "interaction_counts": {
                    "favorites": post.get("favourites_count", 0),
                    "reblogs": post.get("reblogs_count", 0),
                    "replies": post.get("replies_count", 0)
                },
                "mastodon_post": post  # Store full Mastodon object
            }
            
            response = requests.post('http://localhost:9999/api/v1/posts', json=corgi_post, timeout=5)
            if response.status_code in [200, 201]:
                print(f'✅ {i+1}/10: Added post {post["id"]} from @{post["account"]["username"]}')
                success_count += 1
            else:
                print(f'❌ {i+1}/10: Failed to add post {post["id"]}: {response.status_code} - {response.text}')
        except Exception as e:
            print(f'❌ {i+1}/10: Error adding post {post["id"]}: {e}')
        
        # Small delay to be nice to the API
        time.sleep(0.2)

    print(f'\n🎉 Successfully loaded {success_count}/10 real posts!')
    print(f'🔄 Now refresh your ELK page to see real content!')

if __name__ == '__main__':
    load_posts() 