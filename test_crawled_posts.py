#!/usr/bin/env python3
"""Test if crawled posts are accessible by the ranking algorithm"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_db_connection, get_cursor
from core.ranking_algorithm import get_candidate_posts

def test_crawled_posts():
    print("Testing access to crawled posts...")
    
    # Test database directly
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            cur.execute("SELECT COUNT(*) FROM crawled_posts")
            count = cur.fetchone()[0]
            print(f"Database has {count} crawled posts")
            
            if count > 0:
                cur.execute("SELECT post_id, author_username, source_instance, language FROM crawled_posts LIMIT 3")
                posts = cur.fetchall()
                print("Sample posts from database:")
                for post in posts:
                    print(f"  {post[0]} by @{post[1]}@{post[2]} (lang: {post[3]})")
        
        # Test ranking algorithm
        try:
            posts = get_candidate_posts(conn, limit=3, languages=['en'])
            print(f"\nRanking algorithm found {len(posts)} posts")
            if posts:
                for i, post in enumerate(posts[:3]):
                    print(f"  Post {i+1} raw data: {post}")
                    print(f"  Post {i+1}: {post.get('post_id', 'unknown')} by {post.get('author_username', post.get('author_id', 'unknown'))}")
                    print(f"    Source: {post.get('source_table', 'unknown')}")
                    print(f"    Content preview: {post.get('content', '')[:50]}...")
                    print()
            else:
                print("  No posts returned by ranking algorithm")
        except Exception as e:
            print(f"Error in ranking algorithm: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_crawled_posts() 