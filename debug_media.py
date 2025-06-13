#!/usr/bin/env python3

from db.connection import get_db_connection, get_cursor
import json

def check_specific_post(post_id):
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            cur.execute("""
                SELECT post_id, media_attachments, card, content
                FROM crawled_posts 
                WHERE post_id = %s
            """, (post_id,))
            row = cur.fetchone()
            
            if row:
                post_id, media, card, content = row
                print(f"Post {post_id}:")
                print(f"  Content: {content[:100]}...")
                print(f"  Media: {media if media else 'None'}")
                print(f"  Card: {card if card else 'None'}")
            else:
                print(f"Post {post_id} not found")

def check_trending_query():
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            # Run the same query as the trending posts function
            cur.execute("""
                SELECT 
                    post_id, content, author_username, author_acct, author_display_name,
                    author_avatar, created_at, favourites_count, reblogs_count, replies_count,
                    url, source_instance, language, author_id, tags, media_attachments,
                    mentions, emojis, visibility,
                    -- Calculate trending score
                    (
                        COALESCE(favourites_count, 0) * 1.0 + 
                        COALESCE(reblogs_count, 0) * 2.0 + 
                        COALESCE(replies_count, 0) * 1.5
                    ) * 
                    CASE 
                        WHEN created_at > NOW() - INTERVAL '1 day' THEN 1.0
                        WHEN created_at > NOW() - INTERVAL '7 days' THEN 0.8
                        ELSE 0.5
                    END as trending_score
                FROM crawled_posts
                WHERE created_at > NOW() - INTERVAL '30 days'  -- Only recent posts
                AND content IS NOT NULL 
                AND LENGTH(content) > 10  -- Ensure substantial content
                ORDER BY trending_score DESC, created_at DESC
                LIMIT 5
            """)
            rows = cur.fetchall()
            
            print(f"\nTop 5 trending posts:")
            for row in rows:
                post_id = row[0]
                media = row[15]  # media_attachments is at index 15
                card = None  # card is not in this query
                trending_score = row[19]  # trending_score is at index 19
                print(f"  Post {post_id}: score={trending_score:.2f}, media={'Yes' if media and media != '[]' else 'No'}")

def check_media_data():
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            # Check for posts with media attachments
            cur.execute("""
                SELECT post_id, media_attachments, url, card 
                FROM crawled_posts 
                WHERE (media_attachments IS NOT NULL AND media_attachments != '[]') 
                   OR (card IS NOT NULL AND card != 'null')
                LIMIT 5
            """)
            rows = cur.fetchall()
            
            print(f"Found {len(rows)} posts with media/cards:")
            for row in rows:
                post_id, media, url, card = row
                print(f"\nPost {post_id}:")
                print(f"  URL: {url}")
                if media and media != '[]':
                    try:
                        media_data = json.loads(media)
                        print(f"  Media: {len(media_data)} attachments")
                        if media_data:
                            print(f"    First: {media_data[0].get('type', 'unknown')} - {media_data[0].get('url', 'no url')[:50]}...")
                    except:
                        print(f"  Media: {media[:100]}...")
                
                if card and card != 'null':
                    try:
                        card_data = json.loads(card)
                        print(f"  Card: {card_data.get('title', 'No title')} - {card_data.get('url', 'no url')[:50]}...")
                    except:
                        print(f"  Card: {card[:100]}...")

if __name__ == "__main__":
    print("=== Checking specific post ===")
    check_specific_post("114674326113571515")
    
    print("\n=== Checking trending query ===")
    check_trending_query()
    
    print("\n=== Checking posts with media ===")
    check_media_data() 