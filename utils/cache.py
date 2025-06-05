"""
Cache Module for the Corgi Recommender Service.

This module provides Redis-based caching functionality for expensive operations
including recommendation generation, timeline rendering, and API requests.
It helps improve performance, reduce database load, and minimize external API calls.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import hashlib
from urllib.parse import urlencode

import redis

from config import (
    REDIS_ENABLED, REDIS_HOST, REDIS_PORT, REDIS_DB, 
    REDIS_PASSWORD, REDIS_TTL, REDIS_TTL_RECOMMENDATIONS,
    REDIS_TTL_TIMELINE, REDIS_TTL_PROFILE, REDIS_TTL_POST,
    REDIS_TTL_HEALTH, REDIS_TTL_INTERACTIONS, REDIS_TTL_PRIVACY,
    REDIS_TTL_OPTOUT_STATUS
)
from utils.metrics import (
    CACHE_HIT_TOTAL, CACHE_MISS_TOTAL, 
    CACHE_ERROR_TOTAL, CACHE_OPERATION_SECONDS,
    track_cache_hit, track_cache_miss, track_cache_operation_time,
    track_cache_ttl, track_cache_size
)
from utils.mastodon_client import OptOutStatus

# Configure logger
logger = logging.getLogger(__name__)

# Redis client instance (lazy initialization)
_redis_client_instance: Optional[redis.Redis] = None
redis_client: Optional[redis.Redis] = None # Exposed for direct import

def get_redis_client() -> Optional[redis.Redis]:
    """
    Get or create a Redis client.
    
    This lazy initialization pattern only creates the Redis connection
    when it's first needed and then reuses it.
    
    Returns:
        Redis client if Redis is enabled, None otherwise
    """
    global _redis_client_instance, redis_client # Ensure we modify the module-level var
    
    # Return early if Redis is disabled
    if not REDIS_ENABLED:
        return None
    
    # Create client if it doesn't exist
    if _redis_client_instance is None:
        try:
            logger.info(f"Initializing Redis connection to {REDIS_HOST}:{REDIS_PORT}/db{REDIS_DB}")
            _redis_client_instance = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                decode_responses=True  # We need string responses for JSON
            )
            # Test the connection
            _redis_client_instance.ping()
            logger.info("Redis connection successful")
            redis_client = _redis_client_instance # Assign to the importable name
        except redis.RedisError as e:
            logger.error(f"Redis connection failed: {e}")
            _redis_client_instance = None
            redis_client = None # Ensure it's None on failure too
            CACHE_ERROR_TOTAL.labels(operation='connect').inc()
    
    return _redis_client_instance

def clear_cache() -> bool:
    """
    Clear all cached data.
    
    Returns:
        bool: True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        client.flushdb()
        logger.info("Cache cleared successfully")
        return True
    except redis.RedisError as e:
        logger.error(f"Error clearing cache: {e}")
        CACHE_ERROR_TOTAL.labels(operation='clear').inc()
        return False

def clear_cache_by_pattern(pattern: str) -> bool:
    """
    Clear all cache entries matching a specific pattern.
    
    Args:
        pattern: Redis key pattern to match (e.g., "profile:*")
        
    Returns:
        bool: True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
            logger.info(f"Cleared {len(keys)} cache entries matching pattern: {pattern}")
            return True
        logger.debug(f"No cache entries found matching pattern: {pattern}")
        return True
    except redis.RedisError as e:
        logger.error(f"Error clearing cache by pattern: {e}")
        CACHE_ERROR_TOTAL.labels(operation='clear_pattern').inc()
        return False

def cache_key(prefix: str, identifier: str) -> str:
    """
    Generate a standardized cache key.
    
    Args:
        prefix: Domain/type of data (e.g., 'recommendations')
        identifier: Unique ID (e.g., user_id)
        
    Returns:
        Formatted cache key string
    """
    return f"{prefix}:{identifier}"

def cache_get(key: str, cache_type: str = 'general', endpoint: str = 'unknown') -> Optional[Any]:
    """
    Retrieve a value from the cache.
    
    Args:
        key: Cache key to retrieve
        cache_type: Type of cache (e.g., 'proxy', 'recommendations', 'timeline')
        endpoint: Specific endpoint or operation
        
    Returns:
        The cached value or None if not found/error
    """
    client = get_redis_client()
    if not client:
        return None
    
    start_time = time.time()
    try:
        data = client.get(key)
        execution_time = time.time() - start_time
        
        # Track operation time with enhanced metrics
        track_cache_operation_time('get', cache_type, execution_time)
        
        if data:
            # Track cache hit with enhanced metrics
            track_cache_hit(cache_type, endpoint)
            logger.debug(f"Cache hit for key: {key}")
            # ---- DEBUG ----
            if key == "recommendations:returning_user":
                print(f"DEBUG CACHE_GET for {key}: Raw data type from Redis: {type(data)}, len: {len(data) if hasattr(data, '__len__') else 'N/A'}")
                # print(f"DEBUG CACHE_GET for {key}: Raw data content: {data[:200] if isinstance(data, bytes) else data}") # Be careful with large data
            # ---- END DEBUG ----
            loaded_data = json.loads(data)
            # ---- DEBUG ----
            if key == "recommendations:returning_user":
                print(f"DEBUG CACHE_GET for {key}: Unpickled data type: {type(loaded_data)}, len: {len(loaded_data) if hasattr(loaded_data, '__len__') else 'N/A'}")
                if isinstance(loaded_data, list) and loaded_data:
                    print(f"DEBUG CACHE_GET for {key}: First item of unpickled list: {loaded_data[0]}")
            # ---- END DEBUG ----
            return loaded_data
        else:
            # Track cache miss with enhanced metrics
            track_cache_miss(cache_type, endpoint)
            logger.debug(f"Cache miss for key: {key}")
            return None
    except (redis.RedisError, json.JSONDecodeError) as e:
        execution_time = time.time() - start_time
        track_cache_operation_time('get', cache_type, execution_time)
        CACHE_ERROR_TOTAL.labels(operation='get', cache_type=cache_type).inc()
        logger.error(f"Error retrieving from cache: {e}")
        return None

def cache_set(key: str, value: Any, ttl: int = None, cache_type: str = 'general') -> bool:
    """
    Store a value in the cache.
    
    Args:
        key: Cache key
        value: Value to store (will be pickled)
        ttl: Time-to-live in seconds (None for default)
        cache_type: Type of cache for metrics tracking
        
    Returns:
        bool: True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False
    
    if ttl is None:
        ttl = REDIS_TTL
    
    start_time = time.time()
    try:
        # Serialize the value to JSON to handle Python objects securely
        json_value = json.dumps(value)
        result = client.set(key, json_value, ex=ttl)
        execution_time = time.time() - start_time
        
        # Track operation time and TTL with enhanced metrics
        track_cache_operation_time('set', cache_type, execution_time)
        track_cache_ttl(cache_type, ttl)
        
        if result:
            logger.debug(f"Successfully cached value with key: {key}, TTL: {ttl}s")
            return True
        else:
            logger.warning(f"Failed to cache value with key: {key}")
            return False
    except (redis.RedisError, TypeError) as e:
        execution_time = time.time() - start_time
        track_cache_operation_time('set', cache_type, execution_time)
        CACHE_ERROR_TOTAL.labels(operation='set', cache_type=cache_type).inc()
        logger.error(f"Error setting cache: {e}")
        return False

def cache_delete(key: str) -> bool:
    """
    Delete a value from the cache.
    
    Args:
        key: Cache key to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False
    
    start_time = time.time()
    try:
        result = client.delete(key)
        execution_time = time.time() - start_time
        CACHE_OPERATION_SECONDS.labels(operation='delete').observe(execution_time)
        
        if result:
            logger.debug(f"Successfully deleted cache key: {key}")
            return True
        else:
            logger.debug(f"Key not found: {key}")
            return False
    except redis.RedisError as e:
        execution_time = time.time() - start_time
        CACHE_OPERATION_SECONDS.labels(operation='delete').observe(execution_time)
        CACHE_ERROR_TOTAL.labels(operation='delete').inc()
        logger.error(f"Error deleting from cache: {e}")
        return False

def invalidate_pattern(pattern: str) -> bool:
    """
    Invalidate all cache entries matching a pattern.
    
    Args:
        pattern: Redis key pattern to match (e.g., "post:*")
        
    Returns:
        bool: True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False
        
    try:
        # Find all keys matching the pattern
        keys = client.keys(pattern)
        
        if keys:
            client.delete(*keys)
            logger.debug(f"Invalidated {len(keys)} cache entries matching pattern: {pattern}")
            return True
        return True
    except redis.RedisError as e:
        logger.error(f"Error invalidating pattern {pattern}: {e}")
        CACHE_ERROR_TOTAL.labels(operation='invalidate_patterns').inc()
        return False

# ----- Recommendation Caching Functions -----

def invalidate_user_recommendations(user_id: str) -> bool:
    """
    Invalidate a user's cached recommendations.
    
    This should be called when a user interacts with content or changes
    preferences, as their recommendations need to be recalculated.
    
    Args:
        user_id: User ID whose recommendations should be invalidated
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('recommendations', user_id)
    return cache_delete(key)

def cache_recommendations(user_id: str, recommendations: List[Dict[str, Any]], ttl: int = None) -> bool:
    """
    Cache recommendations for a user.
    
    Args:
        user_id: User identifier
        recommendations: List of recommendation objects
        ttl: TTL in seconds (None for default)
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('recommendations', user_id)
    if ttl is None:
        ttl = REDIS_TTL_RECOMMENDATIONS
    return cache_set(key, recommendations, ttl=ttl, cache_type='recommendations')

def get_cached_recommendations(user_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get cached recommendations for a user.
    
    Args:
        user_id: User identifier
        
    Returns:
        List of recommendations if found, None otherwise
    """
    key = cache_key('recommendations', user_id)
    return cache_get(key, cache_type='recommendations', endpoint='recommendations')


# ----- Timeline Caching Functions -----

def create_params_hash(params: Dict[str, Any]) -> str:
    """
    Create a hash from request parameters to use as part of cache keys.
    
    This is used to create unique cache keys based on query parameters,
    ensuring that different parameter combinations get different cache entries.
    
    Args:
        params: Dictionary of request parameters
        
    Returns:
        str: Hash string derived from parameters
    """
    from urllib.parse import urlencode
    
    # Exclude certain parameters that shouldn't affect caching
    exclude_params = ['_', 'cache', 'timestamp', 'nonce']
    
    # Sort parameters for consistent hashing
    sorted_params = dict(sorted(params.items()))
    filtered_params = {k: v for k, v in sorted_params.items() if k not in exclude_params}
    
    # Generate a consistent query string
    query_string = urlencode(filtered_params, doseq=True)
    
    # Create a secure hash using SHA-256 instead of MD5
    hash_obj = hashlib.sha256(query_string.encode())
    return hash_obj.hexdigest()[:8]  # Use first 8 chars for readability

def cache_timeline(user_id: str, timeline_data: List[Dict[str, Any]], ttl: int = None) -> bool:
    """
    Cache timeline data for a user.
    
    Args:
        user_id: User identifier
        timeline_data: Timeline posts data
        ttl: TTL in seconds (None for default)
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('timeline', user_id)
    if ttl is None:
        ttl = REDIS_TTL_TIMELINE
    return cache_set(key, timeline_data, ttl=ttl, cache_type='timeline')

def get_cached_timeline(user_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get cached timeline for a user.
    
    Args:
        user_id: User identifier
        
    Returns:
        Timeline data if found, None otherwise
    """
    key = cache_key('timeline', user_id)
    return cache_get(key, cache_type='timeline', endpoint='timelines/home')

def invalidate_user_timelines(user_id: str) -> bool:
    """
    Invalidate all cached timelines for a user.
    
    This should be called when a user interacts with content,
    as their timeline content may need to be updated.
    
    Args:
        user_id: User ID whose timelines should be invalidated
        
    Returns:
        bool: True if successful, False otherwise
    """
    return invalidate_pattern(f"timeline:*:{user_id}:*")


# ----- Profile Caching Functions -----

def cache_profile(account_id: str, profile_data: Dict[str, Any]) -> bool:
    """
    Cache a user profile.
    
    Args:
        account_id: Account ID
        profile_data: Profile data to cache
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('profile', account_id)
    return cache_set(key, profile_data, ttl=REDIS_TTL_PROFILE, cache_type='proxy')

def get_cached_profile(account_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a cached user profile.
    
    Args:
        account_id: Account ID
        
    Returns:
        Cached profile data if found, None otherwise
    """
    key = cache_key('profile', account_id)
    return cache_get(key, cache_type='proxy', endpoint='accounts')

def invalidate_profile(account_id: str) -> bool:
    """
    Invalidate a cached user profile.
    
    This should be called when a user updates their profile.
    
    Args:
        account_id: Account ID of the profile to invalidate
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('profile', account_id)
    return cache_delete(key)

def cache_profile_statuses(account_id: str, params: Dict[str, Any], statuses_data: List[Dict]) -> bool:
    """
    Cache a user's status posts.
    
    Args:
        account_id: Account ID of the profile
        params: Request parameters (like limit, max_id, etc.)
        statuses_data: The status posts to cache
        
    Returns:
        bool: True if successful, False otherwise
    """
    params_hash = create_params_hash(params)
    key = cache_key('profile:statuses', f'{account_id}:{params_hash}')
    return cache_set(key, statuses_data, ttl=REDIS_TTL_PROFILE)

def get_cached_profile_statuses(account_id: str, params: Dict[str, Any]) -> Optional[List[Dict]]:
    """
    Get cached status posts for a user.
    
    Args:
        account_id: Account ID of the profile
        params: Request parameters (like limit, max_id, etc.)
        
    Returns:
        Cached status posts if found, None otherwise
    """
    params_hash = create_params_hash(params)
    key = cache_key('profile:statuses', f'{account_id}:{params_hash}')
    return cache_get(key)

def invalidate_profile_statuses(account_id: str) -> bool:
    """
    Invalidate all cached status posts for a user.
    
    This should be called when a user posts new content or deletes old content.
    
    Args:
        account_id: Account ID whose status posts should be invalidated
        
    Returns:
        bool: True if successful, False otherwise
    """
    return invalidate_pattern(f"profile:statuses:{account_id}:*")


# ----- Post Caching Functions -----

def cache_post(post_id: str, post_data: Dict[str, Any]) -> bool:
    """
    Cache an individual post.
    
    Args:
        post_id: ID of the post
        post_data: The post data to cache
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('post', post_id)
    return cache_set(key, post_data, ttl=REDIS_TTL_POST)

def get_cached_post(post_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a cached post.
    
    Args:
        post_id: ID of the post
        
    Returns:
        Cached post data if found, None otherwise
    """
    key = cache_key('post', post_id)
    return cache_get(key)

def invalidate_post(post_id: str) -> bool:
    """
    Invalidate a cached post.
    
    This should be called when a post is updated or deleted.
    
    Args:
        post_id: ID of the post to invalidate
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('post', post_id)
    return cache_delete(key)

def cache_post_context(post_id: str, context_data: Dict[str, Any]) -> bool:
    """
    Cache a post's conversation context.
    
    Args:
        post_id: ID of the post
        context_data: The context data to cache
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('post:context', post_id)
    return cache_set(key, context_data, ttl=REDIS_TTL_POST)

def get_cached_post_context(post_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a cached post's conversation context.
    
    Args:
        post_id: ID of the post
        
    Returns:
        Cached context data if found, None otherwise
    """
    key = cache_key('post:context', post_id)
    return cache_get(key)

def invalidate_post_context(post_id: str) -> bool:
    """
    Invalidate a cached post's conversation context.
    
    This should be called when a post's context changes (new replies, etc).
    
    Args:
        post_id: ID of the post whose context should be invalidated
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('post:context', post_id)
    return cache_delete(key)


# ----- Health Check Caching Functions -----

def cache_health_check(service_name: str, health_data: Dict[str, Any]) -> bool:
    """
    Cache health check results.
    
    Args:
        service_name: Name of the service (e.g., 'api', 'db', 'proxy')
        health_data: The health check data to cache
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('health', service_name)
    return cache_set(key, health_data, ttl=REDIS_TTL_HEALTH)

def get_cached_health_check(service_name: str) -> Optional[Dict[str, Any]]:
    """
    Get cached health check results.
    
    Args:
        service_name: Name of the service
        
    Returns:
        Cached health data if found, None otherwise
    """
    key = cache_key('health', service_name)
    return cache_get(key)


# ----- Generic API Response Caching Functions -----

def cache_api_response(endpoint: str, params: Dict[str, Any], response_data: Any, ttl: int = None) -> bool:
    """
    Cache an API response.
    
    Args:
        endpoint: API endpoint path
        params: Request parameters
        response_data: Response data to cache
        ttl: TTL in seconds (None for default)
        
    Returns:
        bool: True if successful, False otherwise
    """
    params_hash = create_params_hash(params)
    key = cache_key(f'api:{endpoint}', params_hash)
    if ttl is None:
        ttl = REDIS_TTL
    return cache_set(key, response_data, ttl=ttl, cache_type='proxy')

def get_cached_api_response(endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
    """
    Get a cached API response.
    
    Args:
        endpoint: API endpoint path
        params: Request parameters
        
    Returns:
        Cached response data if found, None otherwise
    """
    params_hash = create_params_hash(params)
    key = cache_key(f'api:{endpoint}', params_hash)
    # Extract endpoint name for metrics (remove api: prefix and params)
    endpoint_name = endpoint.replace('api:', '').split(':')[0]
    return cache_get(key, cache_type='proxy', endpoint=endpoint_name)

def invalidate_api_endpoint(endpoint: str) -> bool:
    """
    Invalidate all cached responses for a specific API endpoint.
    
    Args:
        endpoint: API endpoint to invalidate
        
    Returns:
        bool: True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        pattern = f"api:{endpoint}:*"
        return clear_cache_by_pattern(pattern)
    except Exception as e:
        logger.error(f"Error invalidating API endpoint cache: {e}")
        return False

# Opt-Out Status Caching Functions

def cache_user_opt_out_status(user_acct: str, opt_out_status: 'OptOutStatus') -> bool:
    """
    Cache a user's opt-out status.
    
    Args:
        user_acct: User account identifier (username@instance)
        opt_out_status: OptOutStatus object to cache
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key("optout", user_acct)
    
    try:
        data = opt_out_status.to_dict()
        success = cache_set(key, data, ttl=REDIS_TTL_OPTOUT_STATUS)
        if success:
            logger.debug(f"Cached opt-out status for {user_acct}: {'opted out' if opt_out_status.opted_out else 'not opted out'}")
        return success
    except Exception as e:
        logger.error(f"Error caching opt-out status for {user_acct}: {e}")
        CACHE_ERROR_TOTAL.labels(operation='set_optout').inc()
        return False

def get_cached_user_opt_out_status(user_acct: str) -> Optional['OptOutStatus']:
    """
    Retrieve a user's cached opt-out status.
    
    Args:
        user_acct: User account identifier (username@instance)
        
    Returns:
        OptOutStatus object if cached and valid, None otherwise
    """
    from datetime import datetime, timezone
    
    key = cache_key("optout", user_acct)
    
    try:
        data = cache_get(key)
        if not data:
            logger.debug(f"No cached opt-out status for {user_acct}")
            return None
        
        opt_out_status = OptOutStatus.from_dict(data)
        
        # Check if cached data is still valid (within TTL)
        age_seconds = (datetime.now(timezone.utc) - opt_out_status.checked_at).total_seconds()
        if age_seconds > REDIS_TTL_OPTOUT_STATUS:
            logger.debug(f"Cached opt-out status for {user_acct} has expired ({age_seconds:.0f}s old)")
            # Remove expired entry
            cache_delete(key)
            return None
        
        logger.debug(f"Retrieved cached opt-out status for {user_acct}: {'opted out' if opt_out_status.opted_out else 'not opted out'}")
        return opt_out_status
    except Exception as e:
        logger.error(f"Error retrieving cached opt-out status for {user_acct}: {e}")
        CACHE_ERROR_TOTAL.labels(operation='get_optout').inc()
        return None

def invalidate_user_opt_out_status(user_acct: str) -> bool:
    """
    Invalidate a user's cached opt-out status.
    
    Args:
        user_acct: User account identifier to invalidate
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key("optout", user_acct)
    
    try:
        success = cache_delete(key)
        if success:
            logger.debug(f"Invalidated cached opt-out status for {user_acct}")
        return success
    except Exception as e:
        logger.error(f"Error invalidating opt-out status for {user_acct}: {e}")
        CACHE_ERROR_TOTAL.labels(operation='delete_optout').inc()
        return False

def clear_all_opt_out_cache() -> bool:
    """
    Clear all cached opt-out status entries.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        success = clear_cache_by_pattern("optout:*")
        if success:
            logger.info("Cleared all cached opt-out status entries")
        return success
    except Exception as e:
        logger.error(f"Error clearing opt-out cache: {e}")
        CACHE_ERROR_TOTAL.labels(operation='clear_optout').inc()
        return False

# ----- Crawler-Specific Caching Functions -----

def cache_crawl_session(session_id: str, session_data: Dict[str, Any], ttl: int = 7200) -> bool:
    """
    Cache crawl session data for coordination and monitoring.
    
    Args:
        session_id: Unique session identifier
        session_data: Session statistics and metadata
        ttl: TTL in seconds (default: 2 hours)
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('crawl:session', session_id)
    return cache_set(key, session_data, ttl=ttl)

def get_cached_crawl_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get cached crawl session data.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session data if found, None otherwise
    """
    key = cache_key('crawl:session', session_id)
    return cache_get(key)

def cache_instance_response(instance: str, endpoint: str, response_data: Any, ttl: int = 1800) -> bool:
    """
    Cache API response from a specific instance to reduce redundant requests.
    
    Args:
        instance: Instance hostname
        endpoint: API endpoint path
        response_data: Response data to cache
        ttl: TTL in seconds (default: 30 minutes)
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key(f'instance:{instance}', endpoint)
    return cache_set(key, response_data, ttl=ttl)

def get_cached_instance_response(instance: str, endpoint: str) -> Optional[Any]:
    """
    Get cached API response from instance.
    
    Args:
        instance: Instance hostname
        endpoint: API endpoint path
        
    Returns:
        Cached response if found, None otherwise
    """
    key = cache_key(f'instance:{instance}', endpoint)
    return cache_get(key)

def cache_seen_post_ids(session_id: str, post_ids: List[str], ttl: int = 86400) -> bool:
    """
    Cache seen post IDs for deduplication within a crawl session.
    
    Args:
        session_id: Crawl session identifier
        post_ids: List of post IDs that have been processed
        ttl: TTL in seconds (default: 24 hours)
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('crawl:seen_posts', session_id)
    return cache_set(key, post_ids, ttl=ttl)

def get_seen_post_ids(session_id: str) -> List[str]:
    """
    Get list of seen post IDs for a crawl session.
    
    Args:
        session_id: Crawl session identifier
        
    Returns:
        List of seen post IDs, empty list if none found
    """
    key = cache_key('crawl:seen_posts', session_id)
    seen_ids = cache_get(key)
    return seen_ids if seen_ids else []

def is_post_seen(session_id: str, post_id: str) -> bool:
    """
    Check if a post has been seen in this crawl session.
    
    Args:
        session_id: Crawl session identifier
        post_id: Post ID to check
        
    Returns:
        bool: True if post has been seen, False otherwise
    """
    seen_ids = get_seen_post_ids(session_id)
    return post_id in seen_ids

def mark_post_seen(session_id: str, post_id: str) -> bool:
    """
    Mark a post as seen in the current crawl session.
    
    Args:
        session_id: Crawl session identifier
        post_id: Post ID to mark as seen
        
    Returns:
        bool: True if successful, False otherwise
    """
    seen_ids = get_seen_post_ids(session_id)
    if post_id not in seen_ids:
        seen_ids.append(post_id)
        return cache_seen_post_ids(session_id, seen_ids)
    return True  # Already seen, no need to update

def cache_crawler_health_summary(summary_data: Dict[str, Any], ttl: int = 300) -> bool:
    """
    Cache crawler health summary for monitoring dashboards.
    
    Args:
        summary_data: Health summary data
        ttl: TTL in seconds (default: 5 minutes)
        
    Returns:
        bool: True if successful, False otherwise
    """
    key = cache_key('crawler', 'health_summary')
    return cache_set(key, summary_data, ttl=ttl)

def get_cached_crawler_health_summary() -> Optional[Dict[str, Any]]:
    """
    Get cached crawler health summary.
    
    Returns:
        Health summary if found, None otherwise
    """
    key = cache_key('crawler', 'health_summary')
    return cache_get(key)