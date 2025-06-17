"""
Recommendation routes for the Corgi Recommender Service.

This module provides endpoints for generating and retrieving personalized post 
recommendations for users.
"""

import logging
import json
import time
import os
import requests
from flask import Blueprint, request, jsonify, Response
from datetime import datetime, timezone
import re
import random
import string
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from db.connection import get_db_connection, get_cursor, USE_IN_MEMORY_DB
from core.ranking_algorithm import generate_rankings_for_user
from utils.privacy import generate_user_alias, get_user_privacy_level
from utils.user_signals import get_weighted_post_selection
from utils.logging_decorator import log_route
from routes.analytics import get_active_model_variant
from utils.timeline_injector import inject_into_timeline
from utils.recommendation_engine import (
    get_ranked_recommendations,
    load_cold_start_posts,
    is_new_user,
)
from utils.metrics import (
    track_injection,
    track_fallback,
    track_timeline_post_counts,
    track_injection_processing_time,
    track_recommendation_generation,
    track_recommendation_processing_time,
)
from routes.proxy import (
    get_authenticated_user,
    get_user_instance,
    ALLOW_COLD_START_FOR_ANONYMOUS,
    should_exit_cold_start,
    should_reenter_cold_start,
    generate_user_alias,
)
from utils.rehydration_service import rehydrate_posts
from utils.recommendation_engine import load_cold_start_posts
from utils.ab_testing import assign_user_to_variant

# Set up logging
logger = logging.getLogger(__name__)

# Check if async tasks (Celery) are available
try:
    from utils.celery_app import celery
    ASYNC_TASKS_AVAILABLE = True
    logger.info("Async tasks (Celery) are available")
except ImportError:
    ASYNC_TASKS_AVAILABLE = False
    logger.warning("Async tasks (Celery) are not available - running in synchronous mode")

# Create blueprint
recommendations_bp = Blueprint("recommendations", __name__)

# Import authentication function
from routes.proxy import get_authenticated_user


def inject_diversity_content(recommendations, user_alias, conn, request_id, limit):
    """
    Inject diverse content to prevent filter bubbles using the 70-20-10 strategy:
    - 70% personalized recommendations (keep original)
    - 20% trending from different instances/communities  
    - 10% serendipitous discovery (low overlap with user interests)
    """
    logger.info(f"REQ-{request_id} | Starting diversity injection for {len(recommendations)} posts")
    
    # Calculate diversity quotas
    total_slots = min(limit, len(recommendations) + 5)  # Allow some extra slots for diversity
    personalized_slots = int(total_slots * 0.7)  # 70% personalized
    trending_slots = int(total_slots * 0.2)      # 20% trending outside bubble
    discovery_slots = int(total_slots * 0.1)     # 10% serendipitous discovery
    
    logger.info(f"REQ-{request_id} | Diversity quotas: {personalized_slots} personalized, {trending_slots} trending, {discovery_slots} discovery")
    
    # Keep top personalized recommendations
    final_recommendations = recommendations[:personalized_slots]
    existing_post_ids = {rec['id'] for rec in final_recommendations}
    
    with get_cursor(conn) as cur:
        try:
            # Get user's typical topics/instances to avoid filter bubble
            user_topics = get_user_interests(cur, user_alias)
            user_instances = get_user_instances(cur, user_alias)
            
            # 1. Inject trending content from DIFFERENT instances/communities (20%)
            if trending_slots > 0:
                trending_posts = get_anti_bubble_trending(
                    cur, user_topics, user_instances, existing_post_ids, trending_slots
                )
                for post in trending_posts:
                    post['recommendation_score'] = 0.45  # Medium-low score for trending
                    post['recommendation_reason'] = f"🔥 Trending outside your network"
                    post['is_diversity_injection'] = True
                    post['diversity_type'] = 'trending'
                    final_recommendations.append(post)
                    existing_post_ids.add(post['id'])
                
                logger.info(f"REQ-{request_id} | Added {len(trending_posts)} trending diversity posts")
            
            # 2. Inject serendipitous discovery content (10%)
            if discovery_slots > 0:
                discovery_posts = get_serendipitous_content(
                    cur, user_topics, existing_post_ids, discovery_slots
                )
                for post in discovery_posts:
                    post['recommendation_score'] = 0.35  # Lower score for discovery
                    post['recommendation_reason'] = "✨ Serendipitous discovery"
                    post['is_diversity_injection'] = True
                    post['diversity_type'] = 'discovery'
                    final_recommendations.append(post)
                    existing_post_ids.add(post['id'])
                
                logger.info(f"REQ-{request_id} | Added {len(discovery_posts)} discovery posts")
            
            # 3. Shuffle the diverse content naturally into the timeline
            final_recommendations = natural_diversity_shuffle(final_recommendations, personalized_slots)
            
            # 4. Trim to requested limit
            final_recommendations = final_recommendations[:limit]
            
            logger.info(f"REQ-{request_id} | Final timeline: {len(final_recommendations)} posts with diversity injection")
            return final_recommendations
            
        except Exception as e:
            logger.error(f"REQ-{request_id} | Error in diversity injection: {e}")
            return recommendations  # Return original on error


def get_user_interests(cur, user_alias):
    """Get user's top topics/hashtags to identify their bubble"""
    try:
        # This would analyze user interactions to find their typical interests
        # For now, return empty list - in production this would query user interaction history
        return []
    except Exception as e:
        logger.warning(f"Failed to get user interests: {e}")
        return []


def get_user_instances(cur, user_alias):
    """Get instances user typically sees content from"""
    try:
        # This would analyze user's typical Mastodon instances
        # For now, return empty list - in production this would query interaction patterns
        return []
    except Exception as e:
        logger.warning(f"Failed to get user instances: {e}")
        return []


def get_anti_bubble_trending(cur, user_topics, user_instances, existing_ids, limit):
    """Find trending posts from instances/topics user doesn't usually see"""
    try:
        if USE_IN_MEMORY_DB:
            # SQLite version - simple random selection
            exclude_ids_str = "', '".join(str(id) for id in existing_ids) if existing_ids else ""
            query = f"""
                SELECT post_id, content, author_id, created_at, metadata
                FROM posts
                WHERE post_id NOT IN ('{exclude_ids_str}')
                ORDER BY RANDOM()
                LIMIT ?
            """ if exclude_ids_str else """
                SELECT post_id, content, author_id, created_at, metadata
                FROM posts
                ORDER BY RANDOM()
                LIMIT ?
            """
            
            cur.execute(query, (limit,))
            rows = cur.fetchall()
            
            # Convert to simple format for SQLite
            posts = []
            for row in rows:
                post_id, content, author_id, created_at, metadata_str = row
                try:
                    metadata = json.loads(metadata_str) if metadata_str else {}
                except:
                    metadata = {}
                
                author_name = metadata.get("author_name", f"user_{author_id}")
                posts.append({
                    "id": str(post_id),
                    "content": content,
                    "created_at": created_at or datetime.now().isoformat(),
                    "account": {
                        "id": author_id,
                        "username": author_name,
                        "acct": author_name,
                        "display_name": author_name,
                    },
                    "favourites_count": 0,
                    "reblogs_count": 0,
                    "replies_count": 0,
                    "is_recommendation": True,
                    "is_real_mastodon_post": False,
                    "is_synthetic": True,
                    "source_instance": "example.com"
                })
            return posts
        else:
            # PostgreSQL version - more sophisticated
            exclude_instances = tuple(user_instances) if user_instances else ('example.com',)
            exclude_ids_tuple = tuple(existing_ids) if existing_ids else ('',)
            
            query = """
                SELECT 
                    cp.post_id, cp.content, cp.author_username, cp.author_id,
                    cp.created_at, cp.source_instance, cp.favourites_count,
                    cp.reblogs_count, cp.replies_count, cp.trending_score,
                    cp.author_acct, cp.author_display_name, cp.author_avatar,
                    cp.author_note, cp.url, cp.language, cp.tags, cp.media_attachments,
                    cp.mentions, cp.emojis, cp.visibility
                FROM crawled_posts cp
                WHERE cp.lifecycle_stage = 'fresh'
                    AND cp.trending_score > 0.3
                    AND cp.post_id NOT IN %s
                    AND (cp.source_instance NOT IN %s OR %s = '')
                ORDER BY cp.trending_score DESC, cp.discovery_timestamp DESC
                LIMIT %s
            """
            
            cur.execute(query, (
                exclude_ids_tuple,
                exclude_instances,
                'example.com' if not user_instances else '',
                limit
            ))
            
            return build_simple_posts_from_rows(cur.fetchall())
        
    except Exception as e:
        logger.warning(f"Failed to get anti-bubble trending: {e}")
        return []


def get_serendipitous_content(cur, user_topics, existing_ids, limit):
    """Find random quality content outside user's interests"""
    try:
        if USE_IN_MEMORY_DB:
            # SQLite version
            exclude_ids_str = "', '".join(str(id) for id in existing_ids) if existing_ids else ""
            query = f"""
                SELECT post_id, content, author_id, created_at, metadata
                FROM posts
                WHERE post_id NOT IN ('{exclude_ids_str}')
                ORDER BY RANDOM()
                LIMIT ?
            """ if exclude_ids_str else """
                SELECT post_id, content, author_id, created_at, metadata
                FROM posts
                ORDER BY RANDOM()
                LIMIT ?
            """
            
            cur.execute(query, (limit,))
            rows = cur.fetchall()
            
            # Convert to simple format
            posts = []
            for row in rows:
                post_id, content, author_id, created_at, metadata_str = row
                try:
                    metadata = json.loads(metadata_str) if metadata_str else {}
                except:
                    metadata = {}
                
                author_name = metadata.get("author_name", f"user_{author_id}")
                posts.append({
                    "id": str(post_id),
                    "content": content,
                    "created_at": created_at or datetime.now().isoformat(),
                    "account": {
                        "id": author_id,
                        "username": author_name,
                        "acct": author_name,
                        "display_name": author_name,
                    },
                    "favourites_count": 0,
                    "reblogs_count": 0,
                    "replies_count": 0,
                    "is_recommendation": True,
                    "is_real_mastodon_post": False,
                    "is_synthetic": True,
                    "source_instance": "example.com"
                })
            return posts
        else:
            # PostgreSQL version
            exclude_ids_tuple = tuple(existing_ids) if existing_ids else ('',)
            
            query = """
                SELECT 
                    cp.post_id, cp.content, cp.author_username, cp.author_id,
                    cp.created_at, cp.source_instance, cp.favourites_count,
                    cp.reblogs_count, cp.replies_count, cp.trending_score,
                    cp.author_acct, cp.author_display_name, cp.author_avatar,
                    cp.author_note, cp.url, cp.language, cp.tags, cp.media_attachments,
                    cp.mentions, cp.emojis, cp.visibility
                FROM crawled_posts cp
                WHERE cp.lifecycle_stage = 'fresh'
                    AND cp.post_id NOT IN %s
                    AND (cp.favourites_count + cp.reblogs_count) > 0
                ORDER BY RANDOM()
                LIMIT %s
            """
            
            cur.execute(query, (exclude_ids_tuple, limit))
            return build_simple_posts_from_rows(cur.fetchall())
        
    except Exception as e:
        logger.warning(f"Failed to get serendipitous content: {e}")
        return []


def natural_diversity_shuffle(recommendations, personalized_count):
    """Naturally shuffle diverse content throughout the timeline"""
    if len(recommendations) <= personalized_count:
        return recommendations
    
    # Keep personalized posts in order, insert diverse posts at natural intervals
    personalized = recommendations[:personalized_count]
    diverse = recommendations[personalized_count:]
    
    # Insert diverse posts at strategic positions (every 3-4 posts)
    result = []
    diverse_index = 0
    
    for i, post in enumerate(personalized):
        result.append(post)
        
        # Insert diverse content every 3-4 posts
        if diverse_index < len(diverse) and (i + 1) % 3 == 0:
            result.append(diverse[diverse_index])
            diverse_index += 1
    
    # Add any remaining diverse posts
    result.extend(diverse[diverse_index:])
    
    return result


def fetch_real_mastodon_data(post_url, max_retries=2, timeout=3):
    """
    Fetch real-time data from Mastodon API for a post.
    
    Args:
        post_url: Full URL to the Mastodon post
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
    
    Returns:
        dict: Real-time post data or None if failed
    """
    try:
        # Parse the URL to extract server and post ID
        # URL format: https://server.com/@username/post_id
        parsed = urlparse(post_url)
        if not parsed.netloc or not parsed.path:
            return None
            
        server = parsed.netloc
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) < 2 or not path_parts[0].startswith('@'):
            return None
            
        post_id = path_parts[-1]
        
        # Try to fetch from Mastodon API
        api_url = f"https://{server}/api/v1/statuses/{post_id}"
        
        for attempt in range(max_retries):
            try:
                response = requests.get(api_url, timeout=timeout, headers={
                    'User-Agent': 'Corgi-Recommender/1.0'
                })
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'favourites_count': data.get('favourites_count', 0),
                        'reblogs_count': data.get('reblogs_count', 0),
                        'replies_count': data.get('replies_count', 0),
                        'account': {
                            'username': data.get('account', {}).get('username'),
                            'display_name': data.get('account', {}).get('display_name'),
                            'avatar': data.get('account', {}).get('avatar'),
                            'note': data.get('account', {}).get('note', ''),
                            'followers_count': data.get('account', {}).get('followers_count', 0),
                            'following_count': data.get('account', {}).get('following_count', 0),
                        },
                        'media_attachments': data.get('media_attachments', []),
                        'tags': data.get('tags', []),
                        'mentions': data.get('mentions', []),
                        'emojis': data.get('emojis', []),
                        'card': data.get('card'),
                        'language': data.get('language'),
                        'sensitive': data.get('sensitive', False),
                        'spoiler_text': data.get('spoiler_text', ''),
                        'last_fetched': datetime.now().isoformat()
                    }
                elif response.status_code == 404:
                    # Post not found, don't retry
                    break
                    
            except requests.RequestException as e:
                logger.debug(f"Attempt {attempt + 1} failed for {api_url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # Brief delay before retry
                    
    except Exception as e:
        logger.debug(f"Error fetching real data for {post_url}: {e}")
        
    return None


def ensure_elk_compatibility(post_data, user_id=None):
    """
    Ensures a post object from any source is compatible with ELK's StatusCard.vue.
    This involves adding missing fields, standardizing data types, and creating
    placeholder objects for rich content if they don't exist.
    """
    if not post_data:
        return None

    # Ensure all required top-level fields exist
    post_data.setdefault('id', str(int(time.time() * 1000)))
    post_data.setdefault('content', 'This content is not available.')
    post_data.setdefault('created_at', datetime.now().isoformat())
    
    # For external posts, preserve the original URLs and don't override with corgi://
    is_external = post_data.get('_corgi_external', False)
    
    if is_external:
        # For external posts, preserve the real URLs completely
        # Don't override URI or URL at all for external posts
        pass
    else:
        # Only set corgi:// URIs for posts that don't already have proper URLs
        if not post_data.get('uri') or post_data.get('uri', '').startswith('corgi://'):
            post_data.setdefault('uri', f"corgi://{post_data['id']}")
        if not post_data.get('url') or post_data.get('url', '').startswith('corgi://'):
            post_data.setdefault('url', f"corgi://{post_data['id']}")
    
    # Interaction counts
    post_data.setdefault('favourites_count', 0)
    post_data.setdefault('reblogs_count', 0)
    post_data.setdefault('replies_count', 0)

    # --- ADD CAMELCASE FOR ELK ---
    # The UI components specifically look for these camelCase fields.
    # We set them here to ensure compatibility for any post from any source.
    post_data['favouritesCount'] = post_data.get('favourites_count', 0)
    post_data['reblogsCount'] = post_data.get('reblogs_count', 0)
    post_data['repliesCount'] = post_data.get('replies_count', 0)
    # --- END FIX ---

    # Flags for frontend logic
    post_data.setdefault('favourited', False)
    post_data.setdefault('reblogged', False)
    post_data.setdefault('bookmarked', False)
    post_data.setdefault('pinned', False)
    
    # ELK-specific display fields
    post_data.setdefault('visibility', 'public') # ELK requires this
    post_data.setdefault('sensitive', False)
    post_data.setdefault('spoiler_text', '')

    # Ensure 'account' object is present and has required fields
    if 'account' not in post_data or not isinstance(post_data['account'], dict):
        post_data['account'] = {}
    
    # Only set defaults if the fields don't already exist (preserve existing account data)
    # Use 'username' in post_data['account'] to check if key exists, not just if it's truthy
    logger.info(f"ELK-COMPAT | Before defaults - username: {post_data['account'].get('username')}, display_name: {post_data['account'].get('display_name')}")
    
    if 'id' not in post_data['account'] or post_data['account']['id'] is None:
        post_data['account']['id'] = '0'
    if 'username' not in post_data['account'] or post_data['account']['username'] is None:
        logger.info(f"ELK-COMPAT | Setting username to anonymous (was: {post_data['account'].get('username')})")
        post_data['account']['username'] = 'anonymous'
    if 'acct' not in post_data['account'] or post_data['account']['acct'] is None:
        logger.info(f"ELK-COMPAT | Setting acct to anonymous (was: {post_data['account'].get('acct')})")
        post_data['account']['acct'] = 'anonymous'
    if 'display_name' not in post_data['account'] or post_data['account']['display_name'] is None:
        logger.info(f"ELK-COMPAT | Setting display_name to Anonymous (was: {post_data['account'].get('display_name')})")
        post_data['account']['display_name'] = 'Anonymous'
        
    logger.info(f"ELK-COMPAT | After defaults - username: {post_data['account'].get('username')}, display_name: {post_data['account'].get('display_name')}")
    if 'avatar' not in post_data['account'] or post_data['account']['avatar'] is None:
        post_data['account']['avatar'] = '/assets/favicon/corgi-512x512.png'
    if 'avatar_static' not in post_data['account'] or post_data['account']['avatar_static'] is None:
        post_data['account']['avatar_static'] = '/assets/favicon/corgi-512x512.png'
    if 'header' not in post_data['account'] or post_data['account']['header'] is None:
        post_data['account']['header'] = '/assets/favicon/corgi-512x512.png'
    if 'header_static' not in post_data['account'] or post_data['account']['header_static'] is None:
        post_data['account']['header_static'] = '/assets/favicon/corgi-512x512.png'

    # --- Rich Content Generation ---

    # Ensure media_attachments is a list
    post_data.setdefault('media_attachments', [])
    
    # Generate a 'card' for link previews if one doesn't exist
    if 'card' not in post_data or post_data['card'] is None:
        post_data['card'] = None # Default to null
        
        # Simple regex to find the first link in post content
        import re
        match = re.search(r'https?://[^\s/$.?#].[^\s]*', post_data.get('content', ''))
        
        if match:
            url = match.group(0)
            # Create a basic link card for ELK to render
            post_data['card'] = {
                "url": url,
                "title": url,
                "description": "Link preview from Corgi Recommender",
                "type": "link",
                "image": None, # No thumbnail by default
                "author_name": "", "author_url": "",
                "provider_name": "", "provider_url": "",
                "html": "", "width": 0, "height": 0
            }

    # Ensure 'poll' is null if not present (ELK expects this)
    post_data.setdefault('poll', None)
    
    # Add Corgi-specific metadata
    post_data['_corgi_recommendation'] = True
    post_data.setdefault('reblog', None) # Ensure reblog is present
    
    # -----------------------------------------
    # Bridge Corgi-specific metadata → frontend
    # -----------------------------------------
    # Older UI integrations expect generic keys
    # like `recommendation_reason` and
    # `recommendation_score`.  Map the existing
    # `_corgi_*` fields if the generic ones are
    # not already present so that legacy scripts
    # (e.g. elk-corgi-native.user.js) continue to
    # render the little "reason" badge and score
    # percentage.
    if '_corgi_recommendation_reason' in post_data and 'recommendation_reason' not in post_data:
        post_data['recommendation_reason'] = post_data['_corgi_recommendation_reason']

    # Surface numeric score if available
    if '_corgi_score' in post_data and 'recommendation_score' not in post_data:
        post_data['recommendation_score'] = post_data['_corgi_score']
        # Provide a human-friendly percent (0-100)
        try:
            post_data['recommendation_percent'] = round(float(post_data['_corgi_score']) * 100)
        except (ValueError, TypeError):
            pass

    # Explicit flag for convenience in DOM sniffers
    post_data.setdefault('is_recommendation', True)
    
    return post_data


def build_simple_posts_from_rows(rows, fetch_real_time=True, user_alias=None):
    """Helper to build simplified Mastodon-compatible posts from database rows"""
    posts = []
    for row in rows:
        # Handle both old format (10 fields) and new format (17 fields)
        if len(row) >= 17:
            # New format with rich account data
            (post_id, content, author_username, author_id, created_at, 
             source_instance, favourites_count, reblogs_count, replies_count, trending_score,
             author_acct, author_display_name, author_avatar, author_note, url, 
             language, tags, media_attachments, mentions, emojis, visibility) = row[:21]
        else:
            # Old format - fallback
            (post_id, content, author_username, author_id, created_at, 
             source_instance, favourites_count, reblogs_count, replies_count, trending_score) = row
            author_acct = f"{author_username}@{source_instance}"
            author_display_name = author_username
            author_avatar = ""
            author_note = ""
            url = f"https://{source_instance}/@{author_username}/{post_id}"
            language = "en"
            tags = "[]"
            media_attachments = "[]"
            mentions = "[]"
            emojis = "[]"
            visibility = "public"
        
        # Parse JSON fields safely
        try:
            tags_list = json.loads(tags) if tags else []
        except:
            tags_list = []
            
        try:
            media_list = json.loads(media_attachments) if media_attachments else []
        except:
            media_list = []
            
        try:
            mentions_list = json.loads(mentions) if mentions else []
        except:
            mentions_list = []
            
        try:
            emojis_list = json.loads(emojis) if emojis else []
        except:
            emojis_list = []
        
        # Construct the post URL
        post_url = url or f"https://{source_instance}/@{author_username}/{post_id}"
        
        # Fetch real-time data if enabled
        real_time_data = None
        if fetch_real_time and post_url:
            real_time_data = fetch_real_mastodon_data(post_url)
        
        # Use real-time data if available, otherwise use database data
        if real_time_data:
            # Use real-time interaction counts
            final_favourites = real_time_data.get('favourites_count', favourites_count or 0)
            final_reblogs = real_time_data.get('reblogs_count', reblogs_count or 0)
            final_replies = real_time_data.get('replies_count', replies_count or 0)
            
            # Use real-time account data if available
            rt_account = real_time_data.get('account', {})
            final_display_name = rt_account.get('display_name') or author_display_name or author_username
            final_avatar = rt_account.get('avatar') or author_avatar or ""
            final_note = rt_account.get('note') or author_note or ""
            
            # Use real-time media and tags if available
            final_media = real_time_data.get('media_attachments', media_list)
            final_tags = real_time_data.get('tags', tags_list)
            final_mentions = real_time_data.get('mentions', mentions_list)
            final_emojis = real_time_data.get('emojis', emojis_list)
            final_language = real_time_data.get('language') or language or "en"
            final_sensitive = real_time_data.get('sensitive', False)
            final_spoiler_text = real_time_data.get('spoiler_text', '')
            final_card = real_time_data.get('card')
        else:
            # Use database data
            final_favourites = favourites_count or 0
            final_reblogs = reblogs_count or 0
            final_replies = replies_count or 0
            final_display_name = author_display_name or author_username
            final_avatar = author_avatar or ""
            final_note = author_note or ""
            final_media = media_list
            final_tags = tags_list
            final_mentions = mentions_list
            final_emojis = emojis_list
            final_language = language or "en"
            final_sensitive = False
            final_spoiler_text = ""
            final_card = None
        
        status = {
            "id": post_id,
            "created_at": created_at.isoformat() if created_at else datetime.now().isoformat(),
            "content": content,
            "account": {
                "id": author_id,
                "username": author_username,
                "acct": author_acct or f"{author_username}@{source_instance}",
                "display_name": final_display_name,
                "url": f"https://{source_instance}/@{author_username}",
                "avatar": final_avatar,
                "avatar_static": final_avatar,
                "note": final_note,
                "bot": False,
                "locked": False,
                "verified": False,
                "fields": []
            },
            "favourites_count": final_favourites,
            "reblogs_count": final_reblogs,
            "replies_count": final_replies,
            # Add camelCase versions for ELK UI compatibility
            "favouritesCount": final_favourites,
            "reblogsCount": final_reblogs,
            "repliesCount": final_replies,
            "url": post_url,
            "uri": post_url,  # Use the real URL as URI for external posts
            "language": final_language,
            "tags": final_tags,
            "media_attachments": final_media,
            "mentions": final_mentions,
            "emojis": final_emojis,
            "visibility": visibility or "public",
            "sensitive": final_sensitive,
            "spoiler_text": final_spoiler_text,
            "card": final_card,
            "is_recommendation": True,
            "is_real_mastodon_post": True,
            "is_synthetic": False,
            "source_instance": source_instance,
            "_corgi_external": True,
            "_corgi_cached": True,
            "_corgi_source_instance": source_instance,
            "_corgi_real_time_fetched": real_time_data is not None,
            "_corgi_recommendation_reason": f"High engagement post from {source_instance} with {final_favourites + final_reblogs} interactions",
            "favourited": row[-2] if len(row) > 21 else False,
            "reblogged": row[-1] if len(row) > 21 else False,
        }
        
        # Ensure ELK compatibility (no user_id available in this context)
        status = ensure_elk_compatibility(status)
        posts.append(status)
    
    return posts


@recommendations_bp.route("/rankings/generate", methods=["POST"])
@log_route
def generate_rankings():
    """
    Generate personalized rankings for a user.

    Request body:
    {
        "user_id": "123",
        "force_refresh": false // Optional: Force recalculation even if recent rankings exist
    }

    Returns:
        201 Created if new rankings were generated
        200 OK if using existing rankings
        400 Bad Request if required fields are missing
        500 Server Error on failure
    """
    data = request.json

    # Validate required fields
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing required field: user_id"}), 400

    # Get pseudonymized user ID for privacy
    user_alias = generate_user_alias(user_id)

    # A/B testing: assign user to variant (returns model/variant ID or None)
    variant_model_id = assign_user_to_variant(user_id)

    # Check if we need to generate new rankings
    force_refresh = data.get("force_refresh", False)

    if not force_refresh and not USE_IN_MEMORY_DB:
        # Check if we already have recent rankings for this user
        # (Skip for SQLite since we always regenerate in-memory)
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # For PostgreSQL only
                cur.execute(
                    """
                    SELECT COUNT(*) FROM post_rankings 
                    WHERE user_id = %s 
                    AND created_at > NOW() - INTERVAL '1 hour'
                """,
                    (user_alias,),
                )

                count = cur.fetchone()[0]

                # If we have recent rankings and aren't forcing a refresh, return early
                if count > 0:
                    logger.info(
                        f"Using existing rankings for user {user_alias} (count: {count})"
                    )
                    return (
                        jsonify({"message": "Using existing rankings", "count": count}),
                        200,
                    )

    # Generate new rankings
    try:
        if USE_IN_MEMORY_DB:
            # -----------------------------------------------------------
            # SQLite Path – Use core ranking algorithm respecting variant
            # -----------------------------------------------------------
            ranked_posts = generate_rankings_for_user(
                user_id, model_id=variant_model_id if variant_model_id else None
            )

            logger.info(
                f"Generated {len(ranked_posts)} rankings for user {user_alias} (SQLite)"
            )

            return (
                jsonify(
                    {
                        "message": "Rankings generated successfully",
                        "count": len(ranked_posts),
                        "variant_model_id": variant_model_id,
                    }
                ),
                201,
            )
        else:
            # -----------------------------------------------------------
            # PostgreSQL Path – A/B variant aware
            # -----------------------------------------------------------
            active_variant_id = variant_model_id or get_active_model_variant(user_alias)
            if active_variant_id:
                logger.info(
                    f"Using model variant {active_variant_id} for user {user_alias}"
                )
                ranked_posts = generate_rankings_for_user(
                    user_id, model_id=active_variant_id
                )
            else:
                logger.info(
                    f"Using default model configuration for user {user_alias}"
                )
                ranked_posts = generate_rankings_for_user(user_id)

            logger.info(
                f"Generated {len(ranked_posts)} ranked posts for user {user_alias} (PostgreSQL)"
            )

            return (
                jsonify(
                    {
                        "message": "Rankings generated successfully",
                        "count": len(ranked_posts),
                        "variant_model_id": active_variant_id,
                    }
                ),
                201,
            )
    except Exception as e:
        logger.error(f"Error during ranking generation: {e}")
        return (
            jsonify({"error": "An internal error occurred during ranking generation"}),
            500,
        )


@recommendations_bp.route("/timelines/recommended", methods=["GET"])
@log_route
def get_recommended_timeline():
    """
    Get personalized timeline recommendations for a user.

    Query parameters:
        user_id: ID of the user to get recommendations for
        limit: Maximum number of recommendations to return (default: 20)

    Returns:
        200 OK with Mastodon-compatible posts sorted by ranking_score
        400 Bad Request if required parameters are missing
        404 Not Found if no recommendations exist
        500 Server Error on failure
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing required parameter: user_id"}), 400

    limit = request.args.get("limit", default=20, type=int)

    # Get pseudonymized user ID for privacy
    user_alias = generate_user_alias(user_id)

    # A/B testing: assign user to variant (returns model/variant ID or None)
    variant_model_id = assign_user_to_variant(user_id)

    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            if USE_IN_MEMORY_DB:
                # SQLite in-memory version
                # Check if we have recommendations for this user
                cur.execute(
                    "SELECT COUNT(*) FROM recommendations WHERE user_id = ?",
                    (user_alias,),
                )
                rec_count = cur.fetchone()[0]

                if rec_count == 0:
                    # Try to generate rankings first
                    try:
                        # Call our rankings generation endpoint directly
                        data = {"user_id": user_id, "force_refresh": True}
                        generate_rankings.__wrapped__(data)
                    except Exception as e:
                        logger.error(f"Failed to auto-generate rankings: {e}")
                        return jsonify([]), 200  # Return empty array for compatibility

                # Get recommendations and join with posts
                cur.execute(
                    """
                    SELECT r.post_id, r.score, r.reason, p.content, p.author_id, p.created_at, p.metadata
                    FROM recommendations r
                    JOIN posts p ON r.post_id = p.post_id
                    WHERE r.user_id = ?
                    ORDER BY r.score DESC
                    LIMIT ?
                """,
                    (user_alias, limit),
                )

                recommendations = []
                for row in cur.fetchall():
                    (
                        post_id,
                        score,
                        reason,
                        content,
                        author_id,
                        created_at,
                        metadata_str,
                    ) = row

                    # Parse metadata if available
                    try:
                        metadata = json.loads(metadata_str) if metadata_str else {}
                    except:
                        metadata = {}

                    author_name = metadata.get("author_name", "User")

                    # Create a Mastodon-compatible post format
                    post_data = {
                        "id": post_id,
                        "content": content,
                        "created_at": created_at,
                        "account": {
                            "id": author_id,
                            "username": author_name,
                            "display_name": author_name,
                            "url": f"https://example.com/@{author_name}",
                        },
                        "language": "en",
                        "favourites_count": 0,
                        "reblogs_count": 0,
                        "replies_count": 0,
                        # Add camelCase versions for ELK compatibility
                        "favouritesCount": 0,
                        "reblogsCount": 0,
                        "repliesCount": 0,
                        "ranking_score": score,
                        "recommendation_reason": reason,
                        "is_real_mastodon_post": False,
                        "is_synthetic": True,
                    }

                    # Ensure ELK compatibility (interaction fields) - user_id not available in this context
                    post_data = ensure_elk_compatibility(post_data)

                    # Add to recommendations
                    recommendations.append(post_data)

                # Debug logging to see what's happening to URIs
                if recommendations:
                    first_post = recommendations[0]
                    logger.info(f"TIMELINE-{request_id} | First post after build_simple_posts_from_rows:")
                    logger.info(f"TIMELINE-{request_id} |   ID: {first_post.get('id')}")
                    logger.info(f"TIMELINE-{request_id} |   URI: {first_post.get('uri')}")
                    logger.info(f"TIMELINE-{request_id} |   URL: {first_post.get('url')}")
                    logger.info(f"TIMELINE-{request_id} |   _corgi_external: {first_post.get('_corgi_external')}")

                return jsonify(recommendations)
            else:
                # PostgreSQL version
                placeholder = "%s"

                # Get the ranked post IDs and scores with full post info
                cur.execute(
                    f"""
                    SELECT pr.post_id, pr.ranking_score, pr.recommendation_reason, 
                           pm.mastodon_post, pm.author_id, pm.author_name, 
                           pm.content, pm.created_at, pm.interaction_counts
                    FROM post_rankings pr
                    JOIN post_metadata pm ON pr.post_id = pm.post_id
                    WHERE pr.user_id = {placeholder}
                    ORDER BY pr.ranking_score DESC
                    LIMIT {placeholder}
                """,
                    (user_alias, limit),
                )

                ranking_data = cur.fetchall()

                if not ranking_data:
                    # Try to auto-generate rankings
                    try:
                        ranked_posts = generate_rankings_for_user(user_id)
                        if ranked_posts:
                            logger.info(
                                f"Auto-generated {len(ranked_posts)} rankings for user {user_alias}"
                            )

                            # Now try to fetch the posts again
                            cur.execute(
                                f"""
                                SELECT pr.post_id, pr.ranking_score, pr.recommendation_reason, 
                                       pm.mastodon_post, pm.author_id, pm.author_name, 
                                       pm.content, pm.created_at, pm.interaction_counts
                                FROM post_rankings pr
                                JOIN post_metadata pm ON pr.post_id = pm.post_id
                                WHERE pr.user_id = {placeholder}
                                ORDER BY pr.ranking_score DESC
                                LIMIT {placeholder}
                            """,
                                (user_alias, limit),
                            )

                            ranking_data = cur.fetchall()

                        if not ranking_data:
                            logger.warning(
                                f"No recommendations available for user {user_alias} even after auto-generation"
                            )
                            return (
                                jsonify([]),
                                200,
                            )  # Return empty array for compatibility

                    except Exception as e:
                        logger.error(f"Failed to auto-generate rankings: {e}")
                        return jsonify([]), 200  # Return empty array for compatibility

                # Process the recommendations into Mastodon-compatible format
                recommendations = []
                for row in ranking_data:
                    (
                        post_id,
                        score,
                        reason,
                        mastodon_post,
                        author_id,
                        author_name,
                        content,
                        created_at,
                        interaction_counts,
                    ) = row

                    try:
                        # If we have a stored Mastodon post, use that as the base
                        if mastodon_post:
                            if isinstance(mastodon_post, str):
                                post_data = json.loads(mastodon_post)
                            else:
                                post_data = mastodon_post
                        else:
                            # Otherwise, construct a compatible format from our stored fields
                            post_data = {
                                "id": post_id,
                                "created_at": (
                                    created_at.isoformat()
                                    if hasattr(created_at, "isoformat")
                                    else created_at or datetime.now().isoformat()
                                ),
                                "account": {
                                    "id": author_id,
                                    "username": author_name or "user",
                                    "display_name": author_name or "User",
                                },
                                "content": content or "",
                                "favourites_count": 0,
                                "reblogs_count": 0,
                                "replies_count": 0,
                                # Add camelCase versions for ELK compatibility
                                "favouritesCount": 0,
                                "reblogsCount": 0,
                                "repliesCount": 0,
                            }

                            # Add interaction counts if available
                            if interaction_counts:
                                try:
                                    if isinstance(interaction_counts, str):
                                        counts = json.loads(interaction_counts)
                                    else:
                                        counts = interaction_counts

                                    post_data["favourites_count"] = counts.get(
                                        "favorites", 0
                                    )
                                    post_data["reblogs_count"] = counts.get(
                                        "reblogs", 0
                                    )
                                    post_data["replies_count"] = counts.get(
                                        "replies", 0
                                    )
                                    # Add camelCase versions for ELK compatibility
                                    post_data["favouritesCount"] = counts.get(
                                        "favorites", 0
                                    )
                                    post_data["reblogsCount"] = counts.get(
                                        "reblogs", 0
                                    )
                                    post_data["repliesCount"] = counts.get(
                                        "replies", 0
                                    )
                                except:
                                    pass

                        # Add recommendation metadata
                        post_data["id"] = post_id  # Ensure correct ID
                        post_data["ranking_score"] = score
                        post_data["recommendation_reason"] = reason

                        # Ensure ELK compatibility (interaction fields) with user interaction state
                        post_data = ensure_elk_compatibility(post_data, user_id)

                        # Add user-specific interaction data from the join
                        post_data["favourited"] = favourited
                        post_data["reblogged"] = reblogged

                        # --- ENSURE CAMELCASE FOR ELK ---
                        # The UI components specifically look for these camelCase fields.
                        post_data['favouritesCount'] = post_data.get('favourites_count', 0)
                        post_data['reblogsCount'] = post_data.get('reblogs_count', 0)
                        post_data['repliesCount'] = post_data.get('replies_count', 0)
                        # --- END FIX ---

                        recommendations.append(post_data)
                    except Exception as e:
                        logger.error(f"Error processing post {post_id}: {e}")

                # Debug logging to see what's happening to URIs
                if recommendations:
                    first_post = recommendations[0]
                    logger.info(f"TIMELINE-{request_id} | First post after build_simple_posts_from_rows:")
                    logger.info(f"TIMELINE-{request_id} |   ID: {first_post.get('id')}")
                    logger.info(f"TIMELINE-{request_id} |   URI: {first_post.get('uri')}")
                    logger.info(f"TIMELINE-{request_id} |   URL: {first_post.get('url')}")
                    logger.info(f"TIMELINE-{request_id} |   _corgi_external: {first_post.get('_corgi_external')}")

    return jsonify(recommendations)


@recommendations_bp.route("/status/<task_id>", methods=["GET"])
@log_route
def get_task_status(task_id):
    """
    Get the status of an async recommendation task.
    
    Args:
        task_id: The ID of the async task to check
        
    Returns:
        200 OK with task status if task exists
        404 Not Found if task doesn't exist
        500 Server Error on failure
    """
    logger.info(f"Checking status for task: {task_id}")
    
    # For load testing purposes, simulate task status responses
    # In a real implementation, this would check Celery task status
    
    try:
        # Simulate different task states based on task_id
        task_id_num = int(task_id.split('_')[-1]) if '_' in task_id else hash(task_id)
        
        # Most tasks should be "completed" to simulate normal operation
        if task_id_num % 10 < 8:  # 80% success rate
            return jsonify({
                "task_id": task_id,
                "status": "completed",
                "result": {
                    "recommendations_count": 15,
                    "processing_time": "0.5s"
                },
                "created_at": datetime.now().isoformat()
            }), 200
        elif task_id_num % 10 == 8:  # 10% pending
            return jsonify({
                "task_id": task_id,
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }), 200
        else:  # 10% not found
            return jsonify({
                "error": "Task not found",
                "task_id": task_id
            }), 404
            
    except Exception as e:
        logger.error(f"Error checking task status for {task_id}: {e}")
        return jsonify({
            "error": "Internal error checking task status",
            "task_id": task_id
        }), 500


@recommendations_bp.route("/metrics/<user_id>", methods=["GET"])
@log_route
def get_recommendation_metrics(user_id):
    """
    Get recommendation quality metrics for a specific user.
    
    Args:
        user_id: The ID of the user to get metrics for
        
    Returns:
        200 OK with metrics data
        404 Not Found if user has no metrics
        500 Server Error on failure
    """
    try:
        # Get pseudonymized user ID for privacy
        user_alias = generate_user_alias(user_id)
        logger.info(f"Getting recommendation metrics for user: {user_alias}")
        
        # Simulate realistic metrics for load testing
        # In a real implementation, this would query actual metrics from database
        
        # Simulate some variation in metrics based on user_id
        user_seed = hash(user_id) % 1000
        random.seed(user_seed)
        
        metrics = {
            "user_id": user_alias,
            "total_recommendations_served": random.randint(50, 500),
            "total_interactions": random.randint(10, 100),
            "click_through_rate": round(random.uniform(0.05, 0.25), 3),
            "engagement_rate": round(random.uniform(0.02, 0.15), 3),
            "diversity_score": round(random.uniform(0.6, 0.9), 3),
            "relevance_score": round(random.uniform(0.7, 0.95), 3),
            "cold_start_exits": random.randint(0, 5),
            "personalization_enabled": True,
            "last_recommendation": "2025-06-08T18:00:00Z",
            "metrics_period": "last_30_days"
        }
        
        return jsonify(metrics), 200
        
    except Exception as e:
        logger.error(f"Error getting recommendation metrics for user {user_id}: {e}")
        return jsonify({"error": "Failed to retrieve recommendation metrics"}), 500


@recommendations_bp.route("/real-posts", methods=["GET"])
@log_route
def get_real_posts():
    """
    Get only real Mastodon posts.

    Query parameters:
        limit: Maximum number of posts to return (default: 20)

    Returns:
        200 OK with real posts
        500 Server Error on failure
    """
    limit = request.args.get("limit", default=20, type=int)

    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            if USE_IN_MEMORY_DB:
                # In-memory SQLite version - return test posts
                placeholder = "?"

                # Get all posts from our test DB
                cur.execute(
                    f"""
                    SELECT post_id, content, author_id, created_at, metadata
                    FROM posts
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )

                rows = cur.fetchall()

                real_posts = []
                for row in rows:
                    post_id, content, author_id, created_at, metadata_str = row

                    # Parse metadata if available
                    try:
                        metadata = json.loads(metadata_str) if metadata_str else {}
                    except:
                        metadata = {}

                    author_name = metadata.get("author_name", "User")

                    # Create a Mastodon-compatible post
                    post_data = {
                        "id": post_id,
                        "content": content,
                        "created_at": created_at,
                        "account": {
                            "id": author_id,
                            "username": author_name,
                            "display_name": author_name,
                            "url": f"https://example.com/@{author_name}",
                        },
                        "language": "en",
                        "favourites_count": 0,
                        "reblogs_count": 0,
                        "replies_count": 0,
                        # Add camelCase versions for ELK compatibility
                        "favouritesCount": 0,
                        "reblogsCount": 0,
                        "repliesCount": 0,
                        "is_real_mastodon_post": False,
                        "is_synthetic": True,
                    }

                    real_posts.append(post_data)
            else:
                # PostgreSQL version - get actual Mastodon posts
                placeholder = "%s"

                # Get only real Mastodon posts
                cur.execute(
                    f"""
                    SELECT post_id, mastodon_post
                    FROM post_metadata
                    WHERE mastodon_post IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT {placeholder}
                """,
                    (limit,),
                )

                real_posts = []
                for post_id, mastodon_json in cur.fetchall():
                    try:
                        if isinstance(mastodon_json, str):
                            mastodon_post = json.loads(mastodon_json)
                        else:
                            mastodon_post = mastodon_json

                        # Add explicit real flags for frontend
                        mastodon_post["is_real_mastodon_post"] = True
                        mastodon_post["is_synthetic"] = False

                        # Ensure required fields
                        if "id" not in mastodon_post:
                            mastodon_post["id"] = post_id

                        real_posts.append(mastodon_post)
                    except Exception as e:
                        logger.error(f"Error processing post {post_id}: {e}")

    if not real_posts:
        return jsonify({"message": "No real Mastodon posts found", "posts": []})

    return jsonify(
        {
            "posts": real_posts,
            "count": len(real_posts),
            "message": f"{'Simulated' if USE_IN_MEMORY_DB else 'Real'} posts returned successfully",
        }
    )


@recommendations_bp.route("/timeline", methods=["GET"])
@log_route
def get_recommendations_timeline():
    """
    Get personalized timeline recommendations from crawled posts.
    Returns real posts from the database, not fake data.
    """
    start_time = time.time()
    request_id = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    
    # Get request parameters
    limit = request.args.get('limit', default=20, type=int)
    max_id = request.args.get('max_id', type=str)
    since_id = request.args.get('since_id', type=str)
    user_alias = request.args.get('user_id', default='anonymous', type=str)
    enable_diversity = request.args.get('enable_diversity', default=True, type=bool)
    exclude_ids_param = request.args.get('exclude_ids', type=str)
    fetch_real_time = request.args.get('fetch_real_time', default=True, type=bool)
    exclude_ids = []
    if exclude_ids_param:
        # Clean and convert exclude_ids to proper format
        raw_ids = exclude_ids_param.split(',')
        for raw_id in raw_ids:
            cleaned_id = raw_id.strip()
            if cleaned_id:
                exclude_ids.append(cleaned_id)
    
    logger.info(f"TIMELINE-{request_id} | Timeline request | User: {user_alias} | Limit: {limit} | Exclude: {len(exclude_ids)} IDs")
    logger.info(f"TIMELINE-{request_id} | Exclude IDs: {exclude_ids}")
    
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                if USE_IN_MEMORY_DB:
                    logger.info(f"REQ-{request_id} | Using SQLite in-memory database")
                    query = """
                        SELECT post_id, content, author_id, created_at, metadata
                        FROM posts
                        WHERE 1=1
                    """
                    params = []
                    
                    if max_id:
                        query += " AND post_id < ?"
                        params.append(max_id)
                    if since_id:
                        query += " AND post_id > ?"
                        params.append(since_id)
                    if exclude_ids:
                        placeholders = ','.join('?' * len(exclude_ids))
                        query += f" AND post_id NOT IN ({placeholders})"
                        # Convert exclude_ids to integers for SQLite
                        for exclude_id in exclude_ids:
                            try:
                                params.append(int(exclude_id))
                            except ValueError:
                                params.append(exclude_id)  # Keep as string if conversion fails
                        
                    query += " ORDER BY created_at DESC LIMIT ?"
                    params.append(limit)
                    
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    
                    if not rows:
                        logger.info(f"TIMELINE-{request_id} | No posts found in SQLite")
                        return jsonify([]), 200
                    
                    # Convert to simple format for SQLite
                    recommendations = []
                    for row in rows:
                        post_id, content, author_id, created_at, metadata = row
                        metadata_dict = json.loads(metadata) if metadata else {}
                        
                        # Create basic Mastodon-compatible structure
                        recommendation = {
                            "id": str(post_id),
                            "created_at": created_at,
                            "content": content,
                            "account": {
                                "id": str(author_id),
                                "username": f"user_{author_id}",
                                "acct": f"user_{author_id}@localhost:5002",
                                "display_name": f"User {author_id}",
                                "url": f"http://localhost:5002/@user_{author_id}",
                                "avatar": f"https://api.dicebear.com/7.x/personas/svg?seed=user_{author_id}",
                                "avatar_static": f"https://api.dicebear.com/7.x/personas/svg?seed=user_{author_id}",
                            },
                            "uri": f"http://localhost:5002/statuses/{post_id}",
                            "url": f"http://localhost:5002/@user_{author_id}/{post_id}",
                            "favourites_count": metadata_dict.get('favourites_count', 0),
                            "reblogs_count": metadata_dict.get('reblogs_count', 0),
                            "replies_count": metadata_dict.get('replies_count', 0),
                            # Corgi-specific enhancements for frontend badges
                            "is_recommendation": True,
                            "recommendation_reason": metadata_dict.get('recommendation_reason') or "Based on your interests",
                            "recommendation_score": metadata_dict.get('recommendation_score'),
                        }
                        recommendations.append(recommendation)
                        
                else:
                    # PostgreSQL - get real crawled posts
                    logger.info(f"REQ-{request_id} | Using PostgreSQL database")
                    query = """
                        SELECT post_id, content, author_username, author_id,
                               created_at, source_instance, favourites_count,
                               reblogs_count, replies_count, trending_score,
                               author_acct, author_display_name, author_avatar,
                               author_note, url, language, tags, media_attachments,
                               mentions, emojis, visibility
                        FROM crawled_posts cp
                        WHERE lifecycle_stage = 'fresh'
                    """
                    params = []
                    
                    if max_id:
                        query += " AND post_id < %s"
                        params.append(max_id)
                    if since_id:
                        query += " AND post_id > %s"
                        params.append(since_id)
                    if exclude_ids:
                        placeholders = ','.join('%s' * len(exclude_ids))
                        query += f" AND post_id NOT IN ({placeholders})"
                        # Convert exclude_ids to integers for PostgreSQL
                        for exclude_id in exclude_ids:
                            try:
                                params.append(int(exclude_id))
                            except ValueError:
                                params.append(exclude_id)  # Keep as string if conversion fails
                        
                    query += " ORDER BY created_at DESC LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    
                    if not rows:
                        logger.info(f"TIMELINE-{request_id} | No posts found in PostgreSQL")
                        return jsonify([]), 200
                    
                    logger.info(f"TIMELINE-{request_id} | Found {len(rows)} posts in database")
                    
                    # Convert to Mastodon-compatible format using build_simple_posts_from_rows
                    recommendations = build_simple_posts_from_rows(rows, fetch_real_time=fetch_real_time)
                    
                    # Debug logging to see what we're getting
                    if recommendations:
                        first_rec = recommendations[0]
                        logger.info(f"TIMELINE-{request_id} | First recommendation account data: username={first_rec.get('account', {}).get('username')}, display_name={first_rec.get('account', {}).get('display_name')}, acct={first_rec.get('account', {}).get('acct')}")
                
                # Remove duplicates based on post ID
                seen_ids = set()
                unique_recommendations = []
                for rec in recommendations:
                    if rec['id'] not in seen_ids:
                        seen_ids.add(rec['id'])
                        unique_recommendations.append(rec)
                    else:
                        logger.info(f"TIMELINE-{request_id} | Removed duplicate post: {rec['id']}")
                
                recommendations = unique_recommendations
                logger.info(f"TIMELINE-{request_id} | After deduplication: {len(recommendations)} unique posts")
                
                logger.info(f"TIMELINE-{request_id} | Returning {len(recommendations)} real posts")
                return jsonify(recommendations), 200
                
    except Exception as e:
        logger.error(f"TIMELINE-{request_id} | Failed to get timeline: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to retrieve timeline: {str(e)}"}), 500


@recommendations_bp.route("/seamless", methods=["POST"])
@log_route
def get_seamless_recommendations():
    """
    Seamless timeline enhancement endpoint for ELK integration.
    """
    start_time = time.time()
    request_id = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON data required"}), 400
            
        timeline_type = data.get("timeline_type", "home")
        existing_statuses = data.get("existing_statuses", [])
        user_id = data.get("user_id", "anonymous")
        max_recommendations = min(data.get("max_recommendations", 3), 10)
        
        logger.info(f"REQ-{request_id} | Seamless recommendations request | Timeline: {timeline_type} | Existing: {len(existing_statuses)} | Max: {max_recommendations}")
        
        if not existing_statuses:
            logger.info(f"REQ-{request_id} | No existing statuses provided, returning empty")
            return jsonify([])
        
        # Create enhanced recommendations using test data for now
        seamless_recommendations = []
        
        for i in range(max_recommendations):
            post_id = f"corgi_enhanced_{int(time.time())}_{i}"
            author_name = f"Corgi User {i+1}"
            
            # Create proper Mastodon-compatible status with realistic engagement
            account_data = {
                "id": f"corgi_user_{i}",
                "username": author_name.lower().replace(' ', '_'),
                "acct": f"{author_name.lower().replace(' ', '_')}@localhost:5002",
                "display_name": author_name,
                "note": "Enhanced with Corgi AI recommendations",
                "url": f"http://localhost:5002/@{author_name.lower().replace(' ', '_')}",
                "avatar": f"https://api.dicebear.com/7.x/personas/svg?seed={author_name}&backgroundColor=random",
                "avatar_static": f"https://api.dicebear.com/7.x/personas/svg?seed={author_name}&backgroundColor=random",
                "header": "https://images.unsplash.com/photo-1557682250-33bd709cbe85?w=400&h=200&fit=crop",
                "header_static": "https://images.unsplash.com/photo-1557682250-33bd709cbe85?w=400&h=200&fit=crop",
                "locked": False,
                "bot": False,
                "discoverable": True,
                "group": False,
                "created_at": "2023-01-01T00:00:00.000Z",
                "last_status_at": datetime.now().strftime("%Y-%m-%d"),
                "statuses_count": random.randint(50, 500),
                "followers_count": random.randint(20, 1000),
                "following_count": random.randint(10, 200),
                "emojis": [],
                "fields": []
            }
            
            # Generate realistic interaction counts
            favorites_count = random.randint(5, 150)
            reblogs_count = random.randint(0, 50)
            replies_count = random.randint(0, 25)
            
            # Create the status with proper local URI to prevent external fetches
            status_data = {
                "id": post_id,
                "created_at": datetime.now().isoformat(),
                "in_reply_to_id": None,
                "in_reply_to_account_id": None,
                "sensitive": False,
                "spoiler_text": "",
                "visibility": "public",
                "language": "en",
                "uri": f"http://localhost:5002/statuses/{post_id}",  # Local URI prevents ELK from fetching externally
                "url": f"http://localhost:5002/@{author_name.lower().replace(' ', '_')}/{post_id}",
                "replies_count": replies_count,
                "reblogs_count": reblogs_count,
                "favourites_count": favorites_count,
                "content": f"🐕 This is an enhanced recommendation from Corgi AI! Post #{i+1} with improved interaction counts and proper data structure.",
                "reblog": None,
                "account": account_data,
                "media_attachments": [],
                "mentions": [],
                "tags": [
                    {"name": "corgi", "url": f"http://localhost:5002/tags/corgi"},
                    {"name": "ai", "url": f"http://localhost:5002/tags/ai"}
                ],
                "emojis": [],
                "card": None,
                "poll": None,
                "application": {
                    "name": "Corgi AI",
                    "website": "http://localhost:5002"
                },
                "favourited": False,
                "reblogged": False,
                "muted": False,
                "bookmarked": False,
                "pinned": False,
                # Corgi-specific metadata for ELK integration
                "_corgi_recommendation": True,
                "_corgi_score": 0.8 + (i * 0.05),
                "_corgi_reason": f"Enhanced recommendation #{i+1} based on your timeline activity",
                "_corgi_source": "enhanced_test"
            }
            
            # Create recommendation wrapper
            recommendation = {
                "id": f"rec_enhanced_{post_id}",
                "content": status_data,
                "score": 0.8 + (i * 0.05),
                "reason": f"Enhanced recommendation #{i+1} with proper interaction counts",
                "strength": "high" if i == 0 else "medium",
                "strength_emoji": "🐕",
                "confidence": "high",
                "insertion_point": (i + 1) * 4  # Insert every 4 posts
            }
            
            seamless_recommendations.append(recommendation)
        
        processing_time = time.time() - start_time
        logger.info(f"REQ-{request_id} | Generated {len(seamless_recommendations)} enhanced seamless recommendations | Time: {processing_time:.3f}s")
        
        return jsonify(seamless_recommendations)
                
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"REQ-{request_id} | Seamless recommendations failed | Error: {e} | Time: {processing_time:.3f}s")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500


@recommendations_bp.route("/timeline/debug", methods=["GET"])
@log_route
def get_timeline_debug():
    """
    Debug version of timeline endpoint that bypasses complex processing.
    """
    request_id = ''.join(random.choices(string.digits, k=7))
    logger.info(f"REQ-{request_id} | Debug timeline request")

    limit = request.args.get('limit', default=20, type=int)
    
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                if USE_IN_MEMORY_DB:
                    logger.info(f"REQ-{request_id} | Using SQLite in-memory database")
                    query = """
                        SELECT post_id, content, author_id, created_at, metadata
                        FROM posts
                        WHERE 1=1
                        ORDER BY created_at DESC LIMIT %s
                    """
                    cur.execute(query, (limit,))
                else:
                    logger.info(f"REQ-{request_id} | Using PostgreSQL database")
                    query = """
                        SELECT 
                            cp.post_id, cp.content, cp.author_username, cp.author_id,
                            cp.created_at, cp.source_instance, cp.favourites_count,
                            cp.reblogs_count, cp.replies_count
                        FROM crawled_posts cp
                        WHERE cp.lifecycle_stage = 'fresh' OR cp.lifecycle_stage = 'relevant'
                        ORDER BY cp.discovery_timestamp DESC LIMIT %s
                    """
                    cur.execute(query, (limit,))
                
                rows = cur.fetchall()
                logger.info(f"REQ-{request_id} | Database query returned {len(rows)} rows")
                
                # Simple processing without ranking/rehydration
                recommendations = []
                for i, row in enumerate(rows):
                    if USE_IN_MEMORY_DB:
                        post_id, content, author_id, created_at, metadata_str = row
                        author_username = f"user_{author_id}"
                        source_instance = "localhost"
                        favourites_count = 0
                        reblogs_count = 0
                        replies_count = 0
                    else:
                        (post_id, content, author_username, author_id, created_at, 
                         source_instance, favourites_count, reblogs_count, replies_count) = row
                    
                    # Create minimal Mastodon-compatible status
                    status = {
                        "id": str(post_id),
                        "created_at": created_at.isoformat() if created_at else datetime.now().isoformat(),
                        "content": content,
                        "visibility": "public",
                        "sensitive": False,
                        "spoiler_text": "",
                        "media_attachments": [],
                        "mentions": [],
                        "tags": [],
                        "emojis": [],
                        "reblogs_count": reblogs_count or 0,
                        "favourites_count": favourites_count or 0,
                        "replies_count": replies_count or 0,
                        "url": f"https://{source_instance}/@{author_username}/{post_id}",
                        "uri": f"https://{source_instance}/@{author_username}/{post_id}",
                        "in_reply_to_id": None,
                        "in_reply_to_account_id": None,
                        "reblog": None,
                        "poll": None,
                        "card": None,
                        "language": "en",
                        "text": content,
                        "account": {
                            "id": str(author_id),
                            "username": author_username,
                            "acct": f"{author_username}@{source_instance}",
                            "display_name": author_username,
                            "locked": False,
                            "bot": False,
                            "discoverable": True,
                            "group": False,
                            "created_at": created_at.isoformat() if created_at else datetime.now().isoformat(),
                            "note": "",
                            "url": f"https://{source_instance}/@{author_username}",
                            "avatar": f"https://api.dicebear.com/7.x/avataaars/svg?seed={author_username}",
                            "avatar_static": f"https://api.dicebear.com/7.x/avataaars/svg?seed={author_username}",
                            "header": f"https://picsum.photos/700/200?random={hash(author_username) % 1000}",
                            "header_static": f"https://picsum.photos/700/200?random={hash(author_username) % 1000}",
                            "followers_count": 0,
                            "following_count": 0,
                            "statuses_count": 1,
                            "last_status_at": created_at.date().isoformat() if created_at else datetime.now().date().isoformat(),
                            "emojis": [],
                            "fields": []
                        },
                        "application": {
                            "name": "Corgi AI Recommender",
                            "website": "https://example.com/corgi"
                        },
                        "edited_at": None,
                        "filtered": [],
                        # Corgi-specific fields
                        "is_recommendation": True,
                        "recommendation_score": 1.0,
                        "recommendation_reason": "Debug timeline",
                        "reason_detail": "Debug timeline",
                        "is_real_mastodon_post": True,
                        "is_synthetic": False,
                        "source_instance": source_instance
                    }
                    
                    recommendations.append(status)
                    logger.info(f"REQ-{request_id} | Processed row {i+1}, recommendations now has {len(recommendations)} posts")
                
                logger.info(f"REQ-{request_id} | Debug timeline returning {len(recommendations)} posts")
                return jsonify(recommendations), 200
                
    except Exception as e:
        logger.error(f"ERROR-{request_id} | Debug timeline failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to retrieve debug timeline"}), 500


@recommendations_bp.route("/timelines/home", methods=["GET"])
@log_route
def get_home_timeline_recommendations():
    """
    Get personalized home timeline recommendations for a user.

    Query parameters:
        user_id: ID of the user to get recommendations for
        limit: Maximum number of recommendations to return (default: 20)

    Returns:
        200 OK with Mastodon-compatible posts sorted by ranking_score
        400 Bad Request if required parameters are missing
        404 Not Found if no recommendations exist
        500 Server Error on failure
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing required parameter: user_id"}), 400

    limit = request.args.get("limit", default=20, type=int)

    # Get pseudonymized user ID for privacy
    user_alias = generate_user_alias(user_id)

    # A/B testing: assign user to variant (returns model/variant ID or None)
    variant_model_id = assign_user_to_variant(user_id)

    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            if USE_IN_MEMORY_DB:
                # SQLite in-memory version
                # Check if we have recommendations for this user
                cur.execute(
                    "SELECT COUNT(*) FROM recommendations WHERE user_id = ?",
                    (user_alias,),
                )
                rec_count = cur.fetchone()[0]

                if rec_count == 0:
                    # Try to generate rankings first
                    try:
                        # Call our rankings generation endpoint directly
                        data = {"user_id": user_id, "force_refresh": True}
                        generate_rankings.__wrapped__(data)
                    except Exception as e:
                        logger.error(f"Failed to auto-generate rankings: {e}")
                        return jsonify([]), 200  # Return empty array for compatibility

                # The main query to fetch posts, now with interaction data
                query = f"""
                    SELECT 
                        cp.post_id, cp.content, cp.author_username, cp.author_id,
                        cp.created_at, cp.source_instance, cp.favourites_count,
                        cp.reblogs_count, cp.replies_count, cp.trending_score,
                        cp.author_acct, cp.author_display_name, cp.author_avatar,
                        cp.author_note, cp.url, cp.language, cp.tags, cp.media_attachments,
                        cp.mentions, cp.emojis, cp.visibility,
                        CASE WHEN i_fav.id IS NOT NULL THEN TRUE ELSE FALSE END AS favourited,
                        CASE WHEN i_reb.id IS NOT NULL THEN TRUE ELSE FALSE END AS reblogged
                    FROM crawled_posts cp
                    LEFT JOIN interactions i_fav 
                        ON cp.post_id = i_fav.post_id 
                        AND i_fav.user_alias = %s
                        AND i_fav.action_type = 'favorite'
                    LEFT JOIN interactions i_reb
                        ON cp.post_id = i_reb.post_id
                        AND i_reb.user_alias = %s
                        AND i_reb.action_type = 'reblog'
                    WHERE cp.lifecycle_stage = 'fresh'
                    ORDER BY cp.created_at DESC
                    LIMIT %s
                """
                
                cur.execute(query, (user_alias, user_alias, limit))
                rows = cur.fetchall()

                posts = build_simple_posts_from_rows(rows, fetch_real_time=False, user_alias=user_alias)

                # Debug logging to see what's happening to URIs
                if posts:
                    first_post = posts[0]
                    logger.info(f"TIMELINE-{request_id} | First post after build_simple_posts_from_rows:")
                    logger.info(f"TIMELINE-{request_id} |   ID: {first_post.get('id')}")
                    logger.info(f"TIMELINE-{request_id} |   URI: {first_post.get('uri')}")
                    logger.info(f"TIMELINE-{request_id} |   URL: {first_post.get('url')}")
                    logger.info(f"TIMELINE-{request_id} |   _corgi_external: {first_post.get('_corgi_external')}")

                return jsonify(posts)
            else:
                # PostgreSQL version
                placeholder = "%s"

                # Get the ranked post IDs and scores with full post info
                cur.execute(
                    f"""
                    SELECT 
                        pr.post_id, pr.ranking_score, pr.recommendation_reason,
                        pm.mastodon_post, pm.author_id, pm.author_name,
                        pm.content, pm.created_at, pm.interaction_counts,
                        CASE WHEN i_fav.id IS NOT NULL THEN TRUE ELSE FALSE END AS favourited,
                        CASE WHEN i_reb.id IS NOT NULL THEN TRUE ELSE FALSE END AS reblogged
                    FROM post_rankings pr
                    JOIN post_metadata pm ON pr.post_id = pm.post_id
                    LEFT JOIN interactions i_fav
                        ON pr.post_id = i_fav.post_id
                        AND i_fav.user_alias = {placeholder}
                        AND i_fav.action_type = 'favorite'
                    LEFT JOIN interactions i_reb
                        ON pr.post_id = i_reb.post_id
                        AND i_reb.user_alias = {placeholder}
                        AND i_reb.action_type = 'reblog'
                    WHERE pr.user_id = {placeholder}
                    ORDER BY pr.ranking_score DESC
                    LIMIT {placeholder}
                 """,
                    (user_alias, user_alias, user_alias, limit),
                )
 
                ranking_data = cur.fetchall()

                if not ranking_data:
                    # Try to auto-generate rankings
                    try:
                        ranked_posts = generate_rankings_for_user(user_id)
                        if ranked_posts:
                            logger.info(
                                f"Auto-generated {len(ranked_posts)} rankings for user {user_alias}"
                            )

                            # Now try to fetch the posts again
                            cur.execute(
                                f"""
                                SELECT pr.post_id, pr.ranking_score, pr.recommendation_reason, 
                                       pm.mastodon_post, pm.author_id, pm.author_name, 
                                       pm.content, pm.created_at, pm.interaction_counts
                                FROM post_rankings pr
                                JOIN post_metadata pm ON pr.post_id = pm.post_id
                                WHERE pr.user_id = {placeholder}
                                ORDER BY pr.ranking_score DESC
                                LIMIT {placeholder}
                            """,
                                (user_alias, limit),
                            )

                            ranking_data = cur.fetchall()

                        if not ranking_data:
                            logger.warning(
                                f"No recommendations available for user {user_alias} even after auto-generation"
                            )
                            return (
                                jsonify([]),
                                200,
                            )  # Return empty array for compatibility

                    except Exception as e:
                        logger.error(f"Failed to auto-generate rankings: {e}")
                        return jsonify([]), 200  # Return empty array for compatibility

                # Process the recommendations into Mastodon-compatible format
                recommendations = []
                for row in ranking_data:
                    (
                        post_id,
                        score,
                        reason,
                        mastodon_post,
                        author_id,
                        author_name,
                        content,
                        created_at,
                        interaction_counts,
                        favourited,
                        reblogged,
                    ) = row

                    try:
                        # If we have a stored Mastodon post, use that as the base
                        if mastodon_post:
                            if isinstance(mastodon_post, str):
                                post_data = json.loads(mastodon_post)
                            else:
                                post_data = mastodon_post
                        else:
                            # Otherwise, construct a compatible format from our stored fields
                            post_data = {
                                "id": post_id,
                                "created_at": (
                                    created_at.isoformat()
                                    if hasattr(created_at, "isoformat")
                                    else created_at or datetime.now().isoformat()
                                ),
                                "account": {
                                    "id": author_id,
                                    "username": author_name or "user",
                                    "display_name": author_name or "User",
                                },
                                "content": content or "",
                                "favourites_count": 0,
                                "reblogs_count": 0,
                                "replies_count": 0,
                                # Add camelCase versions for ELK compatibility
                                "favouritesCount": 0,
                                "reblogsCount": 0,
                                "repliesCount": 0,
                            }

                            # Add interaction counts if available
                            if interaction_counts:
                                try:
                                    if isinstance(interaction_counts, str):
                                        counts = json.loads(interaction_counts)
                                    else:
                                        counts = interaction_counts

                                    post_data["favourites_count"] = counts.get(
                                        "favorites", 0
                                    )
                                    post_data["reblogs_count"] = counts.get(
                                        "reblogs", 0
                                    )
                                    post_data["replies_count"] = counts.get(
                                        "replies", 0
                                    )
                                    # Add camelCase versions for ELK compatibility
                                    post_data["favouritesCount"] = counts.get(
                                        "favorites", 0
                                    )
                                    post_data["reblogsCount"] = counts.get(
                                        "reblogs", 0
                                    )
                                    post_data["repliesCount"] = counts.get(
                                        "replies", 0
                                    )
                                except:
                                    pass

                        # Add recommendation metadata
                        post_data["id"] = post_id  # Ensure correct ID
                        post_data["ranking_score"] = score
                        post_data["recommendation_reason"] = reason

                        # Ensure ELK compatibility (interaction fields) with user interaction state
                        post_data = ensure_elk_compatibility(post_data, user_id)

                        # Add user-specific interaction data from the join
                        post_data["favourited"] = favourited
                        post_data["reblogged"] = reblogged

                        # --- ENSURE CAMELCASE FOR ELK ---
                        # The UI components specifically look for these camelCase fields.
                        post_data['favouritesCount'] = post_data.get('favourites_count', 0)
                        post_data['reblogsCount'] = post_data.get('reblogs_count', 0)
                        post_data['repliesCount'] = post_data.get('replies_count', 0)
                        # --- END FIX ---

                        recommendations.append(post_data)
                    except Exception as e:
                        logger.error(f"Error processing post {post_id}: {e}")

                # Debug logging to see what's happening to URIs
                if recommendations:
                    first_post = recommendations[0]
                    logger.info(f"TIMELINE-{request_id} | First post after build_simple_posts_from_rows:")
                    logger.info(f"TIMELINE-{request_id} |   ID: {first_post.get('id')}")
                    logger.info(f"TIMELINE-{request_id} |   URI: {first_post.get('uri')}")
                    logger.info(f"TIMELINE-{request_id} |   URL: {first_post.get('url')}")
                    logger.info(f"TIMELINE-{request_id} |   _corgi_external: {first_post.get('_corgi_external')}")

                # Final rehydration step if needed
                if os.getenv("ENABLE_REHYDRATION", "false").lower() == "true":
                    recommendations = rehydrate_posts(recommendations)

    return jsonify(recommendations)
