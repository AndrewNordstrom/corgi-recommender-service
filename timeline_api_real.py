#!/usr/bin/env python3
"""
Simple timeline API that serves real crawled Mastodon posts
"""

import os
import sys
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_db_connection, USE_IN_MEMORY_DB

app = Flask(__name__)

# Enable CORS for ELK frontend
CORS(app, origins=[
    'http://localhost:5314',  # ELK frontend
    'http://localhost:3000',  # Alternative frontend port
])

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "timeline-api-real"})

@app.route('/api/v1/recommendations/timeline', methods=['GET'])
def get_timeline():
    """Serve real crawled posts from database"""
    user_id = request.args.get('user_id', 'default_user')
    limit = min(int(request.args.get('limit', 20)), 40)
    
    print(f"📊 Request from user: {user_id} -> fetching up to {limit} real posts")
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            if USE_IN_MEMORY_DB:
                # SQLite version - use posts table
                cur.execute("""
                    SELECT post_id, content, author_id, created_at, metadata
                    FROM posts
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                rows = cur.fetchall()
                
                posts = []
                for row in rows:
                    post_id, content, author_id, created_at, metadata_str = row
                    
                    try:
                        metadata = json.loads(metadata_str) if metadata_str else {}
                    except:
                        metadata = {}
                    
                    author_name = metadata.get("author_name", f"user_{author_id}")
                    
                    post = {
                        "id": str(post_id),
                        "created_at": created_at or datetime.now().isoformat(),
                        "content": content,
                        "account": {
                            "id": author_id,
                            "username": author_name,
                            "acct": author_name,
                            "display_name": author_name,
                            "avatar": "https://via.placeholder.com/48x48",
                            "url": f"https://example.com/@{author_name}",
                        },
                        "favourites_count": metadata.get("favourites_count", 0),
                        "reblogs_count": metadata.get("reblogs_count", 0),
                        "replies_count": metadata.get("replies_count", 0),
                        "favouritesCount": metadata.get("favourites_count", 0),
                        "reblogsCount": metadata.get("reblogs_count", 0),
                        "repliesCount": metadata.get("replies_count", 0),
                        "favourited": False,
                        "reblogged": False,
                        "bookmarked": False,
                        "url": metadata.get("url", f"https://example.com/@{author_name}/{post_id}"),
                        "is_real_mastodon_post": metadata.get("is_real_mastodon_post", False),
                        "source_instance": metadata.get("source_instance", "example.com")
                    }
                    posts.append(post)
                    
            else:
                # PostgreSQL version - use crawled_posts
                cur.execute("""
                    SELECT 
                        cp.post_id, cp.content, cp.author_username, cp.author_id,
                        cp.created_at, cp.source_instance, cp.favourites_count,
                        cp.reblogs_count, cp.replies_count, cp.url,
                        cp.author_display_name, cp.author_avatar
                    FROM crawled_posts cp
                    WHERE cp.lifecycle_stage = 'fresh' OR cp.lifecycle_stage = 'relevant'
                    ORDER BY cp.discovery_timestamp DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                
                posts = []
                for row in rows:
                    (post_id, content, author_username, author_id, created_at, 
                     source_instance, favourites_count, reblogs_count, replies_count, 
                     url, author_display_name, author_avatar) = row
                    
                    post = {
                        "id": post_id,
                        "created_at": created_at.isoformat() if created_at else datetime.now().isoformat(),
                        "content": content,
                        "account": {
                            "id": author_id,
                            "username": author_username,
                            "acct": f"{author_username}@{source_instance}",
                            "display_name": author_display_name or author_username,
                            "avatar": author_avatar or "https://via.placeholder.com/48x48",
                            "url": f"https://{source_instance}/@{author_username}",
                        },
                        "favourites_count": favourites_count or 0,
                        "reblogs_count": reblogs_count or 0,
                        "replies_count": replies_count or 0,
                        "favouritesCount": favourites_count or 0,
                        "reblogsCount": reblogs_count or 0,
                        "repliesCount": replies_count or 0,
                        "favourited": False,
                        "reblogged": False,
                        "bookmarked": False,
                        "url": url or f"https://{source_instance}/@{author_username}/{post_id}",
                        "is_real_mastodon_post": True,
                        "source_instance": source_instance
                    }
                    posts.append(post)
            
            print(f"📊 Returning {len(posts)} real posts from database")
            return jsonify(posts)
            
    except Exception as e:
        print(f"❌ Error fetching posts: {e}")
        return jsonify({"error": "Failed to fetch posts"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('CORGI_PORT', 9999))
    print(f"🚀 Starting timeline API with real content on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False) 