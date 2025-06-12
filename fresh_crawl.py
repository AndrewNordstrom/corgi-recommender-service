#!/usr/bin/env python3
"""
Fresh crawl script to clear old posts and crawl 1000 new posts
with proper criteria for Corgi recommendations
"""

import sys
import os
import json
import requests
from datetime import datetime, timezone, timedelta
import logging
import random
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_db_connection, get_cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Diverse instances for better content variety
INSTANCES = [
    'mastodon.social',
    'fosstodon.org', 
    'mas.to',
    'mstdn.social',
    'hachyderm.io',
    'mastodon.world',
    'tech.lgbt',
    'mastodon.online',
    'pixelfed.social',
    'lemmy.world'
]

def clear_old_posts():
    """Clear existing posts from both tables"""
    logger.info("🧹 Clearing old posts from database...")
    
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            try:
                # Clear crawled_posts table
                cur.execute("DELETE FROM crawled_posts")
                crawled_deleted = cur.rowcount
                
                # Clear post_metadata table  
                cur.execute("DELETE FROM post_metadata")
                metadata_deleted = cur.rowcount
                
                # Clear posts table if it exists
                try:
                    cur.execute("DELETE FROM posts")
                    posts_deleted = cur.rowcount
                except Exception:
                    posts_deleted = 0
                
                conn.commit()
                logger.info(f"✅ Cleared {crawled_deleted} crawled_posts, {metadata_deleted} post_metadata, {posts_deleted} posts")
                
            except Exception as e:
                logger.error(f"Error clearing posts: {e}")
                conn.rollback()
                raise

def fetch_mastodon_timeline(instance, limit=40, local=False):
    """Fetch public timeline from a Mastodon instance"""
    try:
        url = f"https://{instance}/api/v1/timelines/public"
        params = {
            'limit': limit,
            'local': local  # False = federated timeline (more diverse)
        }
        
        logger.debug(f"Fetching from {instance} (limit={limit}, local={local})")
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        posts = response.json()
        logger.info(f"✅ Fetched {len(posts)} posts from {instance}")
        return posts
        
    except Exception as e:
        logger.warning(f"❌ Error fetching from {instance}: {e}")
        return []

def is_good_post(post):
    """Check if post meets quality criteria for Corgi recommendations"""
    try:
        # Skip if no content
        content = post.get('content', '').strip()
        if not content or len(content) < 20:
            return False
            
        # Skip if too old (older than 30 days)
        created_at = datetime.fromisoformat(post.get('created_at', '').replace('Z', '+00:00'))
        if created_at < datetime.now(timezone.utc) - timedelta(days=30):
            return False
            
        # Skip if no engagement (completely ignored posts)
        total_engagement = (
            post.get('favourites_count', 0) + 
            post.get('reblogs_count', 0) + 
            post.get('replies_count', 0)
        )
        if total_engagement == 0:
            return False
            
        # Skip if it's a reply (we want original content)
        if post.get('in_reply_to_id'):
            return False
            
        # Skip if sensitive content without description
        if post.get('sensitive', False) and not post.get('spoiler_text'):
            return False
            
        # Must have valid account info
        account = post.get('account', {})
        if not account.get('username') or not account.get('id'):
            return False
            
        return True
        
    except Exception as e:
        logger.debug(f"Error checking post quality: {e}")
        return False

def enhance_post_for_corgi(post, instance):
    """Enhance post data with Corgi-specific fields"""
    account = post.get('account', {})
    
    # Create enhanced account data with federated handle
    enhanced_account = {
        'id': account.get('id', 'unknown'),
        'username': account.get('username', 'unknown'),
        'acct': account.get('acct', account.get('username', 'unknown')),
        'display_name': account.get('display_name') or account.get('username', 'Unknown User'),
        'url': account.get('url', f"https://{instance}/@{account.get('username', 'unknown')}"),
        'avatar': account.get('avatar', ''),
        'avatar_static': account.get('avatar_static', ''),
        'note': account.get('note', ''),
        'followers_count': account.get('followers_count', 0),
        'following_count': account.get('following_count', 0),
        'statuses_count': account.get('statuses_count', 0),
        'created_at': account.get('created_at', ''),
        'bot': account.get('bot', False),
        'locked': account.get('locked', False),
        'verified': account.get('verified', False),
        'fields': account.get('fields', [])
    }
    
    # Ensure federated handle format
    if '@' not in enhanced_account['acct']:
        enhanced_account['acct'] = f"{enhanced_account['username']}@{instance}"
    
    # Add Corgi-specific metadata
    post['_corgi_external'] = True
    post['_corgi_cached'] = True
    post['_corgi_source_instance'] = instance
    post['_corgi_recommendation_reason'] = random.choice([
        'High engagement in your interests',
        'Popular in your network',
        'Trending topic match',
        'Similar to posts you liked',
        'From accounts you might enjoy'
    ])
    
    # Update account data
    post['account'] = enhanced_account
    
    # Ensure URL is present
    if not post.get('url'):
        post['url'] = f"https://{instance}/@{enhanced_account['username']}/{post.get('id', '')}"
    
    return post

def store_post_in_crawled_posts(cur, post, instance):
    """Store post in crawled_posts table"""
    try:
        account = post.get('account', {})
        
        cur.execute("""
            INSERT INTO crawled_posts (
                post_id, content, author_username, source_instance, 
                created_at, favourites_count, reblogs_count, replies_count,
                lifecycle_stage, discovery_timestamp, language,
                trending_score, engagement_velocity, url,
                author_id, author_acct, author_display_name, author_avatar,
                author_note, author_followers_count, author_following_count,
                author_statuses_count, tags, media_attachments, mentions,
                emojis, visibility, in_reply_to_id, in_reply_to_account_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            post['id'],
            post.get('content', ''),
            account.get('username', 'unknown'),
            instance,
            post.get('created_at'),
            post.get('favourites_count', 0),
            post.get('reblogs_count', 0),
            post.get('replies_count', 0),
            'fresh',
            datetime.now(timezone.utc),
            post.get('language', 'en'),
            random.uniform(0.5, 1.0),  # trending_score
            random.uniform(0.1, 0.8),  # engagement_velocity
            post.get('url', ''),
            account.get('id', 'unknown'),
            account.get('acct', f"{account.get('username', 'unknown')}@{instance}"),
            account.get('display_name') or account.get('username', 'Unknown User'),
            account.get('avatar', ''),
            account.get('note', ''),
            account.get('followers_count', 0),
            account.get('following_count', 0),
            account.get('statuses_count', 0),
            json.dumps(post.get('tags', [])),
            json.dumps(post.get('media_attachments', [])),
            json.dumps(post.get('mentions', [])),
            json.dumps(post.get('emojis', [])),
            post.get('visibility', 'public'),
            post.get('in_reply_to_id'),
            post.get('in_reply_to_account_id')
        ))
        
        return True
        
    except Exception as e:
        logger.error(f"Error storing post {post.get('id', 'unknown')} in crawled_posts: {e}")
        return False

def store_post_in_metadata(cur, post, instance):
    """Store post in post_metadata table"""
    try:
        account = post.get('account', {})
        
        # Create interaction counts
        interaction_counts = {
            'favorites': post.get('favourites_count', 0),
            'reblogs': post.get('reblogs_count', 0),
            'replies': post.get('replies_count', 0)
        }
        
        cur.execute("""
            INSERT INTO post_metadata (
                post_id, author_id, author_name, content, created_at,
                interaction_counts, mastodon_post
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            post['id'],
            account.get('id', 'unknown'),
            account.get('username', 'unknown'),
            post.get('content', ''),
            post.get('created_at'),
            json.dumps(interaction_counts),
            json.dumps(post)  # Store full Mastodon post data
        ))
        
        return True
        
    except Exception as e:
        logger.error(f"Error storing post {post.get('id', 'unknown')} in post_metadata: {e}")
        return False

def crawl_fresh_posts(target_count=1000):
    """Crawl fresh posts from multiple instances"""
    logger.info(f"🚀 Starting fresh crawl for {target_count} posts...")
    
    posts_stored = 0
    posts_processed = 0
    
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            
            # Shuffle instances for variety
            instances = INSTANCES.copy()
            random.shuffle(instances)
            
            for instance in instances:
                if posts_stored >= target_count:
                    break
                    
                logger.info(f"📡 Crawling {instance}...")
                
                try:
                    # Fetch both local and federated content
                    for local in [False, True]:  # Federated first, then local
                        if posts_stored >= target_count:
                            break
                            
                        posts = fetch_mastodon_timeline(instance, limit=40, local=local)
                        timeline_type = "local" if local else "federated"
                        logger.info(f"Processing {len(posts)} {timeline_type} posts from {instance}")
                        
                        for post in posts:
                            if posts_stored >= target_count:
                                break
                                
                            posts_processed += 1
                            
                            # Check if post meets quality criteria
                            if not is_good_post(post):
                                continue
                                
                            # Check for duplicates
                            cur.execute("SELECT id FROM crawled_posts WHERE post_id = %s", (post['id'],))
                            if cur.fetchone():
                                continue
                                
                            # Enhance post for Corgi
                            enhanced_post = enhance_post_for_corgi(post, instance)
                            
                            # Store in both tables
                            crawled_success = store_post_in_crawled_posts(cur, enhanced_post, instance)
                            metadata_success = store_post_in_metadata(cur, enhanced_post, instance)
                            
                            if crawled_success and metadata_success:
                                posts_stored += 1
                                if posts_stored % 50 == 0:
                                    logger.info(f"✅ Stored {posts_stored}/{target_count} posts...")
                                    conn.commit()  # Commit periodically
                        
                        # Rate limiting between requests
                        time.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error crawling {instance}: {e}")
                    continue
                    
                # Rate limiting between instances
                time.sleep(2)
            
            # Final commit
            conn.commit()
            
    logger.info(f"🎉 Crawl complete! Processed {posts_processed} posts, stored {posts_stored} quality posts")
    return posts_stored

def main():
    """Main execution function"""
    logger.info("🐕 Starting fresh Corgi post crawl...")
    
    try:
        # Step 1: Clear old posts
        clear_old_posts()
        
        # Step 2: Crawl fresh posts
        posts_stored = crawl_fresh_posts(target_count=1000)
        
        # Step 3: Verify results
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute("SELECT COUNT(*) FROM crawled_posts")
                crawled_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM post_metadata")
                metadata_count = cur.fetchone()[0]
                
                logger.info(f"📊 Final counts: {crawled_count} crawled_posts, {metadata_count} post_metadata")
                
                # Show sample of new posts
                cur.execute("""
                    SELECT post_id, author_username, source_instance, 
                           favourites_count + reblogs_count + replies_count as engagement
                    FROM crawled_posts 
                    ORDER BY discovery_timestamp DESC 
                    LIMIT 10
                """)
                
                sample_posts = cur.fetchall()
                logger.info("📝 Sample of new posts:")
                for post in sample_posts:
                    logger.info(f"  {post[0]} | @{post[1]}@{post[2]} | {post[3]} interactions")
        
        logger.info("✅ Fresh crawl completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Crawl failed: {e}")
        raise

if __name__ == "__main__":
    main() 