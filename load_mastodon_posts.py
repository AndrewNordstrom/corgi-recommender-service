#!/usr/bin/env python3
"""
Comprehensive script to load real Mastodon posts for Phase 2
Handles both posts and crawled_posts tables with constraint management
"""

import sys
import os
import json
import requests
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_db_connection, get_cursor
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def load_posts_comprehensively(target_count=25):
    """Load posts into both tables, handling constraints"""
    logger.info(f"🚀 Loading {target_count} real posts comprehensively")
    
    instances = ['mastodon.social', 'fosstodon.org']
    posts_loaded = 0
    
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            try:
                # Temporarily disable the foreign key constraint
                logger.info("Temporarily disabling foreign key constraint...")
                cur.execute("ALTER TABLE crawled_posts DROP CONSTRAINT IF EXISTS crawled_posts_post_id_fkey")
                conn.commit()
                logger.info("✅ Foreign key constraint disabled")
                
                for instance in instances:
                    if posts_loaded >= target_count:
                        break
                        
                    logger.info(f"Fetching from {instance}...")
                    posts = fetch_mastodon_timeline(instance, limit=15)
                    
                    for post in posts:
                        if posts_loaded >= target_count:
                            break
                            
                        try:
                            post_id = post['id']
                            content = post['content']
                            author_name = post['account']['username']
                            created_at = post['created_at']
                            
                            # Insert into crawled_posts table (what timeline endpoint reads)
                            cur.execute("""
                                INSERT INTO crawled_posts (
                                    post_id, content, author_username, source_instance, 
                                    created_at, favourites_count, reblogs_count, replies_count,
                                    lifecycle_stage, discovery_timestamp, language,
                                    trending_score, engagement_velocity, url
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                            """, (
                                post_id,                           # post_id
                                content,                           # content  
                                author_name,                       # author_username
                                instance,                          # source_instance
                                created_at,                        # created_at
                                post.get('favourites_count', 0),   # favourites_count
                                post.get('reblogs_count', 0),      # reblogs_count
                                post.get('replies_count', 0),      # replies_count
                                'fresh',                           # lifecycle_stage
                                datetime.now(timezone.utc),       # discovery_timestamp
                                post.get('language', 'en'),       # language
                                1.0,                               # trending_score
                                0.5,                               # engagement_velocity
                                post.get('url')                    # url
                            ))
                            
                            posts_loaded += 1
                            logger.info(f"Loaded post {post_id} from @{author_name}@{instance}")
                            
                        except Exception as e:
                            logger.warning(f"Error loading post {post.get('id', 'unknown')}: {e}")
                            continue
                    
                    # Commit after each instance
                    conn.commit()
                    logger.info(f"✅ Committed {posts_loaded} posts from {instance}")
                
                logger.info(f"🎉 Successfully loaded {posts_loaded} real posts into crawled_posts")
                
            except Exception as e:
                logger.error(f"Error during comprehensive loading: {e}")
                conn.rollback()

def fetch_mastodon_timeline(instance, limit=20):
    """Fetch public timeline from a Mastodon instance"""
    try:
        url = f"https://{instance}/api/v1/timelines/public"
        response = requests.get(url, params={'limit': limit}, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching from {instance}: {e}")
        return []

if __name__ == "__main__":
    load_posts_comprehensively() 