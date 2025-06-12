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
            ORDER BY created_at DESC
            LIMIT 5
        """
        
        cur.execute(query, ('fresh',))
        rows = cur.fetchall()
        
        print(f'Found {len(rows)} rows')
        for i, row in enumerate(rows):
            print(f'Row {i}: length={len(row)}, post_id={row[0]}')
            print(f'  author_username: {row[2]}')
            print(f'  author_acct: {row[10] if len(row) > 10 else "N/A"}')
            print(f'  author_display_name: {row[11] if len(row) > 11 else "N/A"}')
            print(f'  author_avatar: {row[12] if len(row) > 12 else "N/A"}')
            print()
            
        # Test the build_simple_posts_from_rows function
        from routes.recommendations import build_simple_posts_from_rows
        posts = build_simple_posts_from_rows(rows)
        
        print(f'Processed {len(posts)} posts:')
        for i, post in enumerate(posts):
            print(f'Post {i}: {post["id"]}')
            print(f'  Username: {post["account"]["username"]}')
            print(f'  Acct: {post["account"]["acct"]}')
            print(f'  Display name: {post["account"]["display_name"]}')
            print(f'  Avatar: {post["account"]["avatar"][:50] if post["account"]["avatar"] else "None"}...')
            print() 