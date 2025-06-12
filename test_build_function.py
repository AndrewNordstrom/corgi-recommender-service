#!/usr/bin/env python3
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_db_connection, get_cursor
from routes.recommendations import build_simple_posts_from_rows

with get_db_connection() as conn:
    with get_cursor(conn) as cur:
        # Get the same data as the timeline endpoint
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
        
        print(f'Got {len(rows)} rows from database')
        
        if rows:
            # Test the build function
            posts = build_simple_posts_from_rows(rows)
            
            print(f'Built {len(posts)} posts')
            
            if posts:
                post = posts[0]
                print(f'\nPost data:')
                print(f'  ID: {post["id"]}')
                print(f'  URL: {post["url"]}')
                print(f'  URI: {post["uri"]}')
                print(f'  Account username: {post["account"]["username"]}')
                print(f'  Account acct: {post["account"]["acct"]}')
                print(f'  Account display_name: {post["account"]["display_name"]}')
                print(f'  Account URL: {post["account"]["url"]}')
                print(f'  _corgi_external: {post.get("_corgi_external")}')
                print(f'  _corgi_source_instance: {post.get("_corgi_source_instance")}')
                
                # Test JSON serialization
                print(f'\nJSON serialization test:')
                try:
                    json_str = json.dumps(post, indent=2, default=str)
                    print('JSON serialization successful')
                    
                    # Parse it back
                    parsed = json.loads(json_str)
                    print(f'Parsed account username: {parsed["account"]["username"]}')
                    print(f'Parsed account acct: {parsed["account"]["acct"]}')
                    
                except Exception as e:
                    print(f'JSON serialization error: {e}')
        else:
            print('No rows found') 