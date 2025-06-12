#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_db_connection, get_cursor

with get_db_connection() as conn:
    with get_cursor(conn) as cur:
        # Test the exact query from the timeline endpoint
        query = """
            SELECT post_id, content, author_username, author_id,
                   created_at, source_instance, favourites_count,
                   reblogs_count, replies_count, trending_score,
                   author_acct, author_display_name, author_avatar,
                   author_note, url, language, tags, media_attachments,
                   mentions, emojis, visibility
            FROM crawled_posts 
            WHERE lifecycle_stage = %s
            LIMIT 1
        """
        
        cur.execute(query, ('fresh',))
        row = cur.fetchone()
        
        if row:
            print(f'Row length: {len(row)}')
            print(f'Expected: 21 fields')
            print(f'Row data:')
            for i, field in enumerate(row):
                print(f'  {i}: {field}')
                
            # Test the build_simple_posts_from_rows function
            from routes.recommendations import build_simple_posts_from_rows
            posts = build_simple_posts_from_rows([row])
            
            if posts:
                post = posts[0]
                print(f'\nProcessed post:')
                print(f'  ID: {post["id"]}')
                print(f'  Username: {post["account"]["username"]}')
                print(f'  Acct: {post["account"]["acct"]}')
                print(f'  Display name: {post["account"]["display_name"]}')
                print(f'  Avatar: {post["account"]["avatar"]}')
        else:
            print('No rows found') 