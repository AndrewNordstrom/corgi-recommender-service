#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_db_connection, get_cursor

with get_db_connection() as conn:
    with get_cursor(conn) as cur:
        cur.execute('SELECT post_id, author_username, author_acct, source_instance, url FROM crawled_posts LIMIT 3')
        
        print("URL Format Analysis:")
        print("=" * 50)
        
        for row in cur.fetchall():
            post_id, username, acct, instance, url = row
            print(f'Post: {post_id}')
            print(f'  Username: {username}')
            print(f'  Acct: {acct}')
            print(f'  Instance: {instance}')
            print(f'  Stored URL: {url}')
            print(f'  Generated URL: https://{instance}/@{username}/{post_id}')
            
            # Check if acct has the format username@instance
            if acct and '@' in acct:
                acct_username, acct_instance = acct.split('@', 1)
                print(f'  Acct breakdown: {acct_username}@{acct_instance}')
                print(f'  Correct URL should be: https://{acct_instance}/@{acct_username}/{post_id}')
            print() 