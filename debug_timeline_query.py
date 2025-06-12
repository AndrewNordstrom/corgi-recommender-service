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
            LIMIT 1
        """
        
        cur.execute(query, ('fresh',))
        row = cur.fetchone()
        
        if row:
            print(f'Row length: {len(row)}')
            print('Field by field:')
            fields = [
                'post_id', 'content', 'author_username', 'author_id',
                'created_at', 'source_instance', 'favourites_count',
                'reblogs_count', 'replies_count', 'trending_score',
                'author_acct', 'author_display_name', 'author_avatar',
                'author_note', 'url', 'language', 'tags', 'media_attachments',
                'mentions', 'emojis', 'visibility'
            ]
            
            for i, (field, value) in enumerate(zip(fields, row)):
                print(f'  {i:2d}: {field:20} = {value}')
                
            # Test the unpacking
            print('\nTesting unpacking:')
            try:
                (post_id, content, author_username, author_id, created_at, 
                 source_instance, favourites_count, reblogs_count, replies_count, trending_score,
                 author_acct, author_display_name, author_avatar, author_note, url, 
                 language, tags, media_attachments, mentions, emojis, visibility) = row[:21]
                
                print(f'  post_id: {post_id}')
                print(f'  author_username: {author_username}')
                print(f'  author_acct: {author_acct}')
                print(f'  author_display_name: {author_display_name}')
                print(f'  source_instance: {source_instance}')
                print(f'  url: {url}')
                
            except Exception as e:
                print(f'  Error unpacking: {e}')
        else:
            print('No rows found') 