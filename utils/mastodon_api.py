"""
Mastodon API Client for Corgi Recommender Service.

This module provides functionality to fetch fresh Mastodon status objects
from source instances using stored OAuth tokens. It implements caching
for efficiency and error handling for robustness.
"""

import logging
import requests
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse

from db.connection import get_db_connection, get_cursor
from utils.cache import cache_get, cache_set
from utils.token_refresh import get_user_token_data, is_token_expired, refresh_access_token
from utils.metrics import CACHE_HIT_TOTAL, CACHE_MISS_TOTAL, CACHE_ERROR_TOTAL

logger = logging.getLogger(__name__)

class MastodonAPIClient:
    """Client for interacting with Mastodon instances to fetch fresh status objects."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CorgiRecommender/1.0',
            'Accept': 'application/json'
        })
        
    def get_fresh_status(self, post_id: str, instance_url: str, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a fresh status object from a Mastodon instance.
        
        Args:
            post_id: The Mastodon post ID
            instance_url: The Mastodon instance URL  
            access_token: Valid OAuth access token
            
        Returns:
            Fresh Mastodon status object or None if error
        """
        try:
            # Ensure instance URL has proper scheme
            if not instance_url.startswith(('http://', 'https://')):
                instance_url = f"https://{instance_url}"
                
            # Make API call to fetch status
            url = f"{instance_url}/api/v1/statuses/{post_id}"
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                logger.debug(f"Successfully fetched fresh status {post_id} from {instance_url}")
                return status_data
            elif response.status_code == 404:
                logger.warning(f"Status {post_id} not found on {instance_url} (may have been deleted)")
                return None
            elif response.status_code == 401:
                logger.warning(f"Unauthorized access to status {post_id} on {instance_url} (token may be expired)")
                return None
            else:
                logger.error(f"Failed to fetch status {post_id} from {instance_url}: HTTP {response.status_code}")
                return None
                
        except requests.Timeout:
            logger.warning(f"Timeout fetching status {post_id} from {instance_url}")
            return None
        except requests.RequestException as e:
            logger.error(f"Request error fetching status {post_id} from {instance_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching status {post_id} from {instance_url}: {e}")
            return None

    def get_cached_status(self, post_id: str, instance_url: str, ttl: int = 300) -> Optional[Dict[str, Any]]:
        """
        Get a cached Mastodon status object with short TTL.
        
        Args:
            post_id: The Mastodon post ID
            instance_url: The instance URL
            ttl: Cache TTL in seconds (default: 5 minutes)
            
        Returns:
            Cached status object or None if not found/expired
        """
        cache_key = f"mastodon_status:{instance_url}:{post_id}"
        
        try:
            cached_data = cache_get(cache_key)
            if cached_data:
                CACHE_HIT_TOTAL.labels(cache_type='redis', endpoint='mastodon_status').inc()
                logger.debug(f"Cache hit for status {post_id} from {instance_url}")
                return cached_data
            else:
                CACHE_MISS_TOTAL.labels(cache_type='redis', endpoint='mastodon_status').inc()
                logger.debug(f"Cache miss for status {post_id} from {instance_url}")
                return None
        except Exception as e:
            CACHE_ERROR_TOTAL.labels(cache_type='redis', error_type='get').inc()
            logger.error(f"Cache error getting status {post_id}: {e}")
            return None

    def cache_status(self, post_id: str, instance_url: str, status_data: Dict[str, Any], ttl: int = 300) -> bool:
        """
        Cache a Mastodon status object with short TTL.
        
        Args:
            post_id: The Mastodon post ID
            instance_url: The instance URL
            status_data: The status object to cache
            ttl: Cache TTL in seconds (default: 5 minutes)
            
        Returns:
            True if cached successfully, False otherwise
        """
        cache_key = f"mastodon_status:{instance_url}:{post_id}"
        
        try:
            success = cache_set(cache_key, status_data, ttl=ttl)
            if success:
                logger.debug(f"Cached status {post_id} from {instance_url} for {ttl}s")
            return success
        except Exception as e:
            CACHE_ERROR_TOTAL.labels(cache_type='redis', error_type='set').inc()
            logger.error(f"Cache error storing status {post_id}: {e}")
            return False

# Global client instance
mastodon_client = MastodonAPIClient()

def fetch_fresh_mastodon_statuses(recommendations: List[Dict[str, Any]], user_id: str, cache_ttl: int = 300) -> List[Dict[str, Any]]:
    """
    Fetch fresh Mastodon status objects for a list of recommended posts.
    
    This is the main function that should be called by the recommendation system
    to convert Corgi's internal post data into fresh Mastodon status objects.
    
    Args:
        recommendations: List of recommendation dicts from ranking algorithm
        user_id: User ID for token lookup
        cache_ttl: Cache TTL in seconds for fresh statuses (default: 300)
        
    Returns:
        List of fresh Mastodon status objects with recommendation metadata
    """
    if not recommendations:
        return []
        
    # Get user's OAuth token data
    user_token_data = get_user_token_data(user_id)
    if not user_token_data:
        logger.warning(f"No OAuth token data found for user {user_id}")
        return []
        
    user_instance = user_token_data['instance_url']
    access_token = user_token_data['access_token']
    
    # Check if token is expired and refresh if needed
    token_expires_at = user_token_data.get('token_expires_at')
    if is_token_expired(token_expires_at):
        logger.info(f"Token expired for user {user_id}, attempting refresh")
        refresh_token = user_token_data.get('refresh_token')
        if refresh_token:
            result = refresh_access_token(user_id, refresh_token, user_instance)
            if result.get('success'):
                # Get updated token data
                user_token_data = get_user_token_data(user_id)
                access_token = user_token_data['access_token']
                logger.info(f"Successfully refreshed token for user {user_id}")
            else:
                logger.error(f"Failed to refresh token for user {user_id}: {result.get('message')}")
                return []
        else:
            logger.error(f"No refresh token available for user {user_id}")
            return []
    
    fresh_statuses = []
    
    for rec in recommendations:
        post_id = rec.get('post_id')
        if not post_id:
            logger.warning("Recommendation missing post_id, skipping")
            continue
            
        # Determine the source instance for this post
        # For now, assume all posts are from the user's instance
        # TODO: In the future, this could be enhanced to support multi-instance posts
        instance_url = user_instance
        
        # Try to get from cache first
        cached_status = mastodon_client.get_cached_status(post_id, instance_url, ttl=cache_ttl)
        if cached_status:
            # Add recommendation metadata to cached status
            fresh_status = cached_status.copy()
            fresh_status.update({
                'is_recommendation': True,
                'ranking_score': rec.get('ranking_score'),
                'recommendation_reason': rec.get('recommendation_reason'),
                'recommendation_metadata': {
                    'source': 'corgi_recommendation_engine',
                    'score': rec.get('ranking_score'),
                    'reason': rec.get('recommendation_reason'),
                    'fetched_from_cache': True
                }
            })
            fresh_statuses.append(fresh_status)
            continue
            
        # Fetch fresh status from Mastodon
        fresh_status = mastodon_client.get_fresh_status(post_id, instance_url, access_token)
        
        if fresh_status:
            # Cache the fresh status for future requests with custom TTL
            mastodon_client.cache_status(post_id, instance_url, fresh_status, ttl=cache_ttl)
            
            # Add recommendation metadata
            fresh_status.update({
                'is_recommendation': True,
                'ranking_score': rec.get('ranking_score'),
                'recommendation_reason': rec.get('recommendation_reason'),
                'recommendation_metadata': {
                    'source': 'corgi_recommendation_engine',
                    'score': rec.get('ranking_score'),
                    'reason': rec.get('recommendation_reason'),
                    'fetched_from_cache': False,
                    'fetched_at': datetime.utcnow().isoformat()
                }
            })
            fresh_statuses.append(fresh_status)
            logger.debug(f"Successfully fetched and cached fresh status {post_id}")
        else:
            # Post couldn't be fetched (deleted, private, etc.)
            logger.warning(f"Could not fetch fresh status for post {post_id}, omitting from recommendations")
            # We omit this post from the final recommendations for a cleaner user experience
            
    logger.info(f"Fetched {len(fresh_statuses)} fresh Mastodon statuses out of {len(recommendations)} recommendations for user {user_id}")
    return fresh_statuses

def get_post_source_instance(post_id: str, user_id: str) -> Optional[str]:
    """
    Determine the source Mastodon instance for a given post.
    
    This is a helper function that could be enhanced in the future to support
    multi-instance recommendations by looking up the post's original instance.
    
    Args:
        post_id: The post ID
        user_id: The user ID (for fallback to user's instance)
        
    Returns:
        Instance URL or None if cannot be determined
    """
    # For now, assume all recommended posts are from the user's connected instance
    user_token_data = get_user_token_data(user_id)
    if user_token_data:
        return user_token_data['instance_url']
    return None 