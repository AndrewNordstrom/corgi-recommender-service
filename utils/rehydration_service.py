#!/usr/bin/env python3
"""
Rehydration Service for Semi-Live Interaction Counts

This service fetches fresh interaction counts from original Mastodon instances
to keep recommended content feeling live and dynamic.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse

import redis
import requests
try:
    from config import REDIS_CONFIG
except ImportError:
    REDIS_CONFIG = {
        'host': 'localhost',
        'port': 6379,
        'db': 0
    }

# Set up logging
logger = logging.getLogger(__name__)

# Redis client for caching
try:
    redis_client = redis.Redis(
        host=REDIS_CONFIG.get('host', 'localhost'),
        port=REDIS_CONFIG.get('port', 6379),
        db=REDIS_CONFIG.get('db', 0),
        decode_responses=True,
        socket_timeout=2,
        socket_connect_timeout=2
    )
    # Test connection
    redis_client.ping()
    logger.info("✅ Redis connection established for rehydration service")
except Exception as e:
    logger.warning(f"⚠️ Redis unavailable for rehydration service: {e}")
    redis_client = None

# Cache TTL for fresh post data (in seconds)
FRESH_POST_CACHE_TTL = 300  # 5 minutes
FAILED_POST_CACHE_TTL = 60  # 1 minute for failures


class MastodonInstanceClient:
    """Lightweight client for fetching fresh data from Mastodon instances."""
    
    def __init__(self, instance_url: str):
        """Initialize client for a specific instance."""
        self.instance_url = instance_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Corgi-Recommender/1.0 (Rehydration Service)',
            'Accept': 'application/json'
        })
    
    def get_fresh_post_data(self, post_id: str, timeout: float = 3.0) -> Optional[Dict]:
        """
        Fetch fresh post data from the Mastodon instance.
        
        Args:
            post_id: The ID of the post to fetch
            timeout: Request timeout in seconds
            
        Returns:
            Fresh post data or None if failed
        """
        try:
            # Construct the API endpoint
            endpoint = f"{self.instance_url}/api/v1/statuses/{post_id}"
            
            # Make the request with short timeout for responsiveness
            response = self.session.get(endpoint, timeout=timeout)
            
            if response.status_code == 200:
                logger.debug(f"✅ Fetched fresh data for {post_id} from {self.instance_url}")
                return response.json()
            elif response.status_code == 404:
                logger.debug(f"Post {post_id} not found on {self.instance_url}")
                return None
            else:
                logger.debug(f"Failed to fetch {post_id} from {self.instance_url}: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.debug(f"Timeout fetching {post_id} from {self.instance_url}")
            return None
        except Exception as e:
            logger.debug(f"Error fetching {post_id} from {self.instance_url}: {e}")
            return None


def get_cache_key(post_id: str, source_instance: str) -> str:
    """Generate Redis cache key for a post."""
    return f"fresh_status:{source_instance}:{post_id}"


def get_fresh_interaction_counts(post_id: str, source_instance: str) -> Optional[Dict]:
    """
    Get fresh interaction counts for a post, using cache when available.
    
    Args:
        post_id: The ID of the post
        source_instance: The source Mastodon instance
        
    Returns:
        Dict with fresh counts or None if unavailable
    """
    if not redis_client:
        logger.debug("Redis unavailable, skipping rehydration")
        return None
        
    cache_key = get_cache_key(post_id, source_instance)
    
    try:
        # Check cache first
        cached_data = redis_client.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            if "error" not in data:
                logger.debug(f"Cache hit for {post_id} from {source_instance}")
                return data
            else:
                logger.debug(f"Cached failure for {post_id} from {source_instance}")
                return None
        
        # Cache miss - fetch fresh data
        logger.debug(f"Cache miss for {post_id}, fetching from {source_instance}")
        
        # Skip non-standard instances that might not support the API
        if source_instance in ['bsky.brid.gy', 'example.com']:
            logger.debug(f"Skipping rehydration for bridged/example instance: {source_instance}")
            return None
        
        # Create client for the instance
        client = MastodonInstanceClient(f"https://{source_instance}")
        fresh_data = client.get_fresh_post_data(post_id)
        
        if fresh_data:
            # Extract interaction counts
            counts = {
                "favourites_count": fresh_data.get("favourites_count", 0),
                "reblogs_count": fresh_data.get("reblogs_count", 0),
                "replies_count": fresh_data.get("replies_count", 0),
                "last_updated": datetime.now().isoformat(),
                "source": "live_api"
            }
            
            # Cache the results
            redis_client.setex(
                cache_key,
                FRESH_POST_CACHE_TTL,
                json.dumps(counts)
            )
            
            logger.info(f"Rehydrated {post_id}: favs={counts['favourites_count']}, boosts={counts['reblogs_count']}")
            return counts
        else:
            # Cache the failure to avoid repeated failed requests
            failure_data = {"error": "fetch_failed", "timestamp": datetime.now().isoformat()}
            redis_client.setex(
                cache_key,
                FAILED_POST_CACHE_TTL,
                json.dumps(failure_data)
            )
            return None
            
    except Exception as e:
        logger.error(f"Error getting fresh interaction counts for {post_id}: {e}")
        return None


def rehydrate_post(post_data: Dict) -> Dict:
    """
    Rehydrate a single post with fresh interaction counts.
    
    Args:
        post_data: The post data to rehydrate
        
    Returns:
        Post data with potentially updated interaction counts
    """
    try:
        # Extract post ID and source instance
        post_id = post_data.get("id")
        source_instance = post_data.get("source_instance")
        
        if not post_id or not source_instance:
            logger.debug("Missing post_id or source_instance for rehydration")
            post_data["is_fresh"] = False
            return post_data
        
        # Get fresh interaction counts
        fresh_counts = get_fresh_interaction_counts(post_id, source_instance)
        
        if fresh_counts:
            # Update the post data with fresh counts
            old_favs = post_data.get("favourites_count", 0)
            old_boosts = post_data.get("reblogs_count", 0)
            
            post_data["favourites_count"] = fresh_counts["favourites_count"]
            post_data["reblogs_count"] = fresh_counts["reblogs_count"]
            post_data["replies_count"] = fresh_counts["replies_count"]
            post_data["is_fresh"] = True
            post_data["last_refreshed"] = fresh_counts["last_updated"]
            
            # Log significant changes
            fav_change = fresh_counts["favourites_count"] - old_favs
            boost_change = fresh_counts["reblogs_count"] - old_boosts
            if fav_change > 0 or boost_change > 0:
                logger.info(f"Post {post_id} gained {fav_change} favs, {boost_change} boosts")
                
        else:
            # Mark as stale if we couldn't get fresh data
            post_data["is_fresh"] = False
            
    except Exception as e:
        logger.error(f"Error rehydrating post {post_data.get('id', 'unknown')}: {e}")
        post_data["is_fresh"] = False
    
    return post_data


def rehydrate_posts(posts: List[Dict]) -> List[Dict]:
    """
    Rehydrate a list of posts with fresh interaction counts.
    
    This is the main function used by the API endpoints to refresh
    interaction counts while keeping the system responsive.
    
    Args:
        posts: List of post data dictionaries
        
    Returns:
        List of posts with updated interaction counts
    """
    if not posts:
        return posts
    
    start_time = time.time()
    rehydrated_count = 0
    
    logger.debug(f"Starting rehydration of {len(posts)} posts...")
    
    # Process each post
    rehydrated_posts = []
    for post in posts:
        try:
            rehydrated_post = rehydrate_post(post)
            if rehydrated_post.get("is_fresh", False):
                rehydrated_count += 1
            rehydrated_posts.append(rehydrated_post)
        except Exception as e:
            logger.error(f"Error rehydrating post: {e}")
            post["is_fresh"] = False
            rehydrated_posts.append(post)
    
    elapsed_time = time.time() - start_time
    
    logger.info(
        f"Rehydration complete: {rehydrated_count}/{len(posts)} posts refreshed "
        f"in {elapsed_time:.2f}s (avg {elapsed_time/len(posts):.3f}s/post)"
    )
    
    return rehydrated_posts


def get_rehydration_stats() -> Dict:
    """Get statistics about the rehydration cache."""
    if not redis_client:
        return {"error": "Redis unavailable"}
    
    try:
        # Count fresh status cache entries
        keys = redis_client.keys("fresh_status:*")
        total_cached = len(keys)
        
        # Sample some entries to check freshness
        fresh_count = 0
        error_count = 0
        
        sample_size = min(20, total_cached)
        if sample_size > 0:
            sample_keys = keys[:sample_size]
            for key in sample_keys:
                try:
                    data = redis_client.get(key)
                    if data:
                        parsed = json.loads(data)
                        if "error" in parsed:
                            error_count += 1
                        else:
                            fresh_count += 1
                except:
                    continue
        
        return {
            "total_cached_posts": total_cached,
            "sample_size": sample_size,
            "fresh_in_sample": fresh_count,
            "errors_in_sample": error_count,
            "cache_hit_rate": f"{(fresh_count/sample_size)*100:.1f}%" if sample_size > 0 else "N/A"
        }
        
    except Exception as e:
        return {"error": str(e)}


# For testing
if __name__ == "__main__":
    print("🧪 Testing rehydration service...")
    
    # Test post data
    test_post = {
        "id": "114654525218805649",
        "source_instance": "mastodon.social",
        "favourites_count": 5,
        "reblogs_count": 2,
        "replies_count": 1
    }
    
    print(f"Original: {test_post['favourites_count']} favs, {test_post['reblogs_count']} boosts")
    
    # Test rehydration
    rehydrated = rehydrate_post(test_post)
    
    print(f"Rehydrated: {rehydrated['favourites_count']} favs, {rehydrated['reblogs_count']} boosts")
    print(f"Is fresh: {rehydrated.get('is_fresh', False)}")
    
    # Test stats
    stats = get_rehydration_stats()
    print(f"Cache stats: {stats}") 