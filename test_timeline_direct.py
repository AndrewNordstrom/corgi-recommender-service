#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_db_connection, get_cursor
from routes.recommendations import build_simple_posts_from_rows

# Test the exact same query as the timeline endpoint
with get_db_connection() as conn:
    with get_cursor(conn) as cur:
        query = """
            SELECT post_id, content, author_username, author_id,
                   created_at, source_instance, favourites_count,
                   reblogs_count, replies_count, trending_score,
                   author_acct, author_display_name, author_avatar,
                   author_note, url, language, tags, media_attachments,
                   mentions, emojis, visibility
            FROM crawled_posts 
            WHERE lifecycle_stage = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        cur.execute(query, ('fresh',))
        rows = cur.fetchall()
        
        print(f"Database query returned {len(rows)} rows")
        
        if rows:
            row = rows[0]
            print(f"Raw row data (first 10 fields):")
            for i, field in enumerate(row[:10]):
                print(f"  [{i}]: {field}")
            
            print(f"\nRaw row data (fields 10-21):")
            for i, field in enumerate(row[10:21], 10):
                print(f"  [{i}]: {field}")
            
            # Test build function
            print(f"\n=== Testing build_simple_posts_from_rows ===")
            posts = build_simple_posts_from_rows(rows, fetch_real_time=False)
            
            if posts:
                post = posts[0]
                print(f"Built post:")
                print(f"  ID: {post['id']}")
                print(f"  URL: {post['url']}")
                print(f"  URI: {post['uri']}")
                print(f"  Account username: {post['account']['username']}")
                print(f"  Account acct: {post['account']['acct']}")
                print(f"  Account display_name: {post['account']['display_name']}")
                print(f"  Favourites: {post['favourites_count']}")
                print(f"  _corgi_external: {post.get('_corgi_external')}")
        else:
            print("No rows found") 