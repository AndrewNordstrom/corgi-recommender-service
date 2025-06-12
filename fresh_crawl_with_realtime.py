#!/usr/bin/env python3
"""
Enhanced crawl script that fetches real-time data from Mastodon APIs
and ensures proper URL formatting for ELK navigation
"""

import sys
import os
import json
import requests
import time
from datetime import datetime, timezone, timedelta
import logging
from urllib.parse import urlparse

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
    'social.vivaldi.net',
    'mastodon.art'
]

def fetch_real_time_post_data(post_url, timeout=5):
    """
    Fetch real-time data from Mastodon API for a post
    """
    try:
        parsed = urlparse(post_url)
        if not parsed.netloc or not parsed.path:
            return None
            
        server = parsed.netloc
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) < 2 or not path_parts[0].startswith('@'):
            return None
            
        post_id = path_parts[-1]
        
        # Fetch from Mastodon API
        api_url = f"https://{server}/api/v1/statuses/{post_id}"
        
        response = requests.get(api_url, timeout=timeout, headers={
            'User-Agent': 'Corgi-Recommender/1.0'
        })
        
        if response.status_code == 200:
            data = response.json()
            account = data.get('account', {})
            
            return {
                'favourites_count': data.get('favourites_count', 0),
                'reblogs_count': data.get('reblogs_count', 0),
                'replies_count': data.get('replies_count', 0),
                'account_username': account.get('username', ''),
                'account_display_name': account.get('display_name', ''),
                'account_avatar': account.get('avatar', ''),
                'account_note': account.get('note', ''),
                'account_acct': account.get('acct', ''),
                'media_attachments': json.dumps(data.get('media_attachments', [])),
                'tags': json.dumps(data.get('tags', [])),
                'mentions': json.dumps(data.get('mentions', [])),
                'emojis': json.dumps(data.get('emojis', [])),
                'language': data.get('language', 'en'),
                'sensitive': data.get('sensitive', False),
                'spoiler_text': data.get('spoiler_text', ''),
                'card': json.dumps(data.get('card')) if data.get('card') else None,
                'visibility': data.get('visibility', 'public'),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.debug(f"Error fetching real-time data for {post_url}: {e}")
        
    return None

def crawl_instance_timeline(instance, limit=50):
    """
    Crawl public timeline from a Mastodon instance with real-time data
    """
    posts = []
    
    try:
        # Fetch public timeline
        url = f"https://{instance}/api/v1/timelines/public"
        params = {
            'limit': limit,
            'local': False  # Include federated posts
        }
        
        response = requests.get(url, params=params, timeout=10, headers={
            'User-Agent': 'Corgi-Recommender/1.0'
        })
        
        if response.status_code != 200:
            logger.warning(f"Failed to fetch timeline from {instance}: {response.status_code}")
            return posts
            
        timeline_data = response.json()
        logger.info(f"Fetched {len(timeline_data)} posts from {instance}")
        
        for post in timeline_data:
            try:
                # Skip replies and boosts for cleaner content
                if post.get('in_reply_to_id') or post.get('reblog'):
                    continue
                    
                # Skip posts with no engagement
                engagement = (post.get('favourites_count', 0) + 
                            post.get('reblogs_count', 0) + 
                            post.get('replies_count', 0))
                if engagement < 1:
                    continue
                
                account = post.get('account', {})
                post_url = post.get('url', '')
                
                # Ensure proper URL format
                if not post_url:
                    post_url = f"https://{instance}/@{account.get('username', '')}/{post.get('id', '')}"
                
                # Get real-time data (this will be the most current)
                real_time_data = fetch_real_time_post_data(post_url)
                
                # Use real-time data if available, otherwise use timeline data
                if real_time_data:
                    final_data = real_time_data
                    final_data.update({
                        'post_id': post.get('id'),
                        'content': post.get('content', ''),
                        'created_at': post.get('created_at'),
                        'url': post_url,
                        'source_instance': instance
                    })
                else:
                    # Fallback to timeline data
                    final_data = {
                        'post_id': post.get('id'),
                        'content': post.get('content', ''),
                        'created_at': post.get('created_at'),
                        'url': post_url,
                        'source_instance': instance,
                        'favourites_count': post.get('favourites_count', 0),
                        'reblogs_count': post.get('reblogs_count', 0),
                        'replies_count': post.get('replies_count', 0),
                        'account_username': account.get('username', ''),
                        'account_display_name': account.get('display_name', ''),
                        'account_avatar': account.get('avatar', ''),
                        'account_note': account.get('note', ''),
                        'account_acct': account.get('acct', ''),
                        'media_attachments': json.dumps(post.get('media_attachments', [])),
                        'tags': json.dumps(post.get('tags', [])),
                        'mentions': json.dumps(post.get('mentions', [])),
                        'emojis': json.dumps(post.get('emojis', [])),
                        'language': post.get('language', 'en'),
                        'sensitive': post.get('sensitive', False),
                        'spoiler_text': post.get('spoiler_text', ''),
                        'card': json.dumps(post.get('card')) if post.get('card') else None,
                        'visibility': post.get('visibility', 'public'),
                        'last_updated': datetime.now(timezone.utc).isoformat()
                    }
                
                # Calculate trending score
                age_hours = (datetime.now(timezone.utc) - 
                           datetime.fromisoformat(post.get('created_at', '').replace('Z', '+00:00'))).total_seconds() / 3600
                
                engagement_score = (final_data.get('favourites_count', 0) * 1.0 + 
                                  final_data.get('reblogs_count', 0) * 2.0 + 
                                  final_data.get('replies_count', 0) * 1.5)
                
                # Time decay factor
                time_factor = max(0.1, 1.0 / (1.0 + age_hours / 24.0))
                trending_score = engagement_score * time_factor
                
                final_data['trending_score'] = trending_score
                final_data['lifecycle_stage'] = 'fresh'
                final_data['discovery_timestamp'] = datetime.now(timezone.utc)
                
                posts.append(final_data)
                
            except Exception as e:
                logger.error(f"Error processing post from {instance}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error crawling {instance}: {e}")
        
    return posts

def main():
    logger.info("Starting enhanced crawl with real-time data fetching...")
    
    # Clear existing posts
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            cur.execute("DELETE FROM crawled_posts")
            logger.info("Cleared existing posts")
    
    all_posts = []
    target_posts = 200  # Reasonable number for testing
    
    for instance in INSTANCES:
        if len(all_posts) >= target_posts:
            break
            
        logger.info(f"Crawling {instance}...")
        posts = crawl_instance_timeline(instance, limit=30)
        all_posts.extend(posts)
        
        logger.info(f"Total posts collected: {len(all_posts)}")
        time.sleep(1)  # Be respectful to servers
    
    # Sort by trending score and take the best ones
    all_posts.sort(key=lambda x: x.get('trending_score', 0), reverse=True)
    final_posts = all_posts[:target_posts]
    
    logger.info(f"Inserting {len(final_posts)} posts into database...")
    
    # Insert into database
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            for post in final_posts:
                try:
                    cur.execute("""
                        INSERT INTO crawled_posts (
                            post_id, content, author_username, author_id, created_at,
                            source_instance, favourites_count, reblogs_count, replies_count,
                            trending_score, author_acct, author_display_name, author_avatar,
                            author_note, url, language, tags, media_attachments,
                            mentions, emojis, visibility, lifecycle_stage, discovery_timestamp
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (post_id) DO UPDATE SET
                            favourites_count = EXCLUDED.favourites_count,
                            reblogs_count = EXCLUDED.reblogs_count,
                            replies_count = EXCLUDED.replies_count,
                            trending_score = EXCLUDED.trending_score,
                            discovery_timestamp = EXCLUDED.discovery_timestamp
                    """, (
                        post['post_id'], post['content'], post['account_username'],
                        post['account_username'], post['created_at'], post['source_instance'],
                        post['favourites_count'], post['reblogs_count'], post['replies_count'],
                        post['trending_score'], post['account_acct'], post['account_display_name'],
                        post['account_avatar'], post['account_note'], post['url'],
                        post['language'], post['tags'], post['media_attachments'],
                        post['mentions'], post['emojis'], post['visibility'],
                        post['lifecycle_stage'], post['discovery_timestamp']
                    ))
                except Exception as e:
                    logger.error(f"Error inserting post {post.get('post_id', 'unknown')}: {e}")
                    continue
    
    logger.info(f"✅ Enhanced crawl completed! Inserted {len(final_posts)} posts with real-time data")

if __name__ == "__main__":
    main() 