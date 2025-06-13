#!/usr/bin/env python3

from db.connection import get_db_connection, get_cursor
import json
from datetime import datetime

def debug_trending_posts():
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            # Run the exact same query as get_trending_cold_start_posts
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
            
            print(f"Found {len(rows)} trending posts:")
            
            for i, row in enumerate(rows):
                (post_id, content, author_username, author_acct, author_display_name,
                 author_avatar, created_at, favourites_count, reblogs_count, replies_count,
                 url, source_instance, language, author_id, tags_json, media_json,
                 mentions_json, emojis_json, visibility, trending_score) = row
                
                print(f"\n--- Post {i+1}: {post_id} ---")
                print(f"Trending Score: {trending_score}")
                print(f"Content: {content[:100]}...")
                print(f"Raw media_json: {media_json[:200] if media_json else 'None'}...")
                
                # Parse JSON fields safely (same as in the actual function)
                try:
                    media_attachments = json.loads(media_json) if media_json else []
                    print(f"Parsed media_attachments: {len(media_attachments)} items")
                    if media_attachments:
                        print(f"  First attachment: {media_attachments[0].get('type', 'unknown')} - {media_attachments[0].get('url', 'no url')[:50]}...")
                except Exception as e:
                    print(f"Error parsing media_json: {e}")
                    media_attachments = []
                
                # Create the post object (same as in the actual function)
                post = {
                    "id": str(post_id),
                    "created_at": created_at.isoformat() if created_at else datetime.now().isoformat(),
                    "content": content,
                    "account": {
                        "id": author_id or f"user_{author_username}",
                        "username": author_username,
                        "acct": author_acct or f"{author_username}@{source_instance}",
                        "display_name": author_display_name or author_username,
                        "avatar": author_avatar or "https://via.placeholder.com/48x48",
                        "url": f"https://{source_instance}/@{author_username}",
                    },
                    "favourites_count": favourites_count or 0,
                    "reblogs_count": reblogs_count or 0,
                    "replies_count": replies_count or 0,
                    "language": language or "en",
                    "url": url or f"https://{source_instance}/@{author_username}/{post_id}",
                    "media_attachments": media_attachments,
                    "visibility": visibility or "public",
                    "favourited": False,
                    "reblogged": False,
                    "bookmarked": False,
                    "trending_score": float(trending_score) if trending_score else 0.0,
                }
                
                print(f"Final post media_attachments: {len(post['media_attachments'])} items")

if __name__ == "__main__":
    debug_trending_posts() 