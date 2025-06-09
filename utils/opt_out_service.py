"""
User Opt-Out Service for the Corgi Recommender Service.

This module provides functionality to check and manage user opt-out preferences
for content crawling and recommendation services.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# In-memory cache for opt-out status (in production, this would use Redis)
_opt_out_cache = {}
_cache_ttl = timedelta(hours=1)

def check_user_opt_out(user_id: str, instance: Optional[str] = None) -> bool:
    """
    Check if a user has opted out of content crawling and recommendations.
    
    Args:
        user_id: User identifier
        instance: Mastodon instance (optional)
        
    Returns:
        bool: True if user has opted out, False otherwise
    """
    if not user_id:
        return False
    
    # Create cache key
    cache_key = f"{user_id}@{instance}" if instance else user_id
    
    # Check cache first
    if cache_key in _opt_out_cache:
        cached_data = _opt_out_cache[cache_key]
        if datetime.utcnow() - cached_data['timestamp'] < _cache_ttl:
            logger.debug(f"Opt-out status for {cache_key}: {cached_data['opted_out']} (cached)")
            return cached_data['opted_out']
    
    # In a real implementation, this would check a database or external service
    # For now, we'll implement a simple policy:
    # - Users with "nobot" in their profile are considered opted out
    # - Users with specific keywords in their bio are opted out
    # - Default is opted in (False)
    
    opted_out = False
    
    # Simple heuristics for opt-out detection
    user_lower = user_id.lower()
    if any(keyword in user_lower for keyword in ['nobot', 'no-bot', 'private', 'optout', 'opt-out']):
        opted_out = True
        logger.info(f"User {user_id} appears to have opted out based on username")
    
    # Cache the result
    _opt_out_cache[cache_key] = {
        'opted_out': opted_out,
        'timestamp': datetime.utcnow()
    }
    
    logger.debug(f"Opt-out status for {cache_key}: {opted_out}")
    return opted_out

def set_user_opt_out(user_id: str, opted_out: bool, instance: Optional[str] = None) -> bool:
    """
    Set a user's opt-out preference.
    
    Args:
        user_id: User identifier
        opted_out: Whether user wants to opt out
        instance: Mastodon instance (optional)
        
    Returns:
        bool: True if successfully set, False otherwise
    """
    if not user_id:
        return False
    
    cache_key = f"{user_id}@{instance}" if instance else user_id
    
    # Update cache
    _opt_out_cache[cache_key] = {
        'opted_out': opted_out,
        'timestamp': datetime.utcnow()
    }
    
    # In a real implementation, this would update a database
    logger.info(f"Set opt-out status for {cache_key}: {opted_out}")
    return True

def get_opt_out_stats() -> Dict[str, Any]:
    """
    Get statistics about opt-out preferences.
    
    Returns:
        Dict[str, Any]: Statistics about opt-out status
    """
    total_users = len(_opt_out_cache)
    opted_out_users = sum(1 for data in _opt_out_cache.values() if data['opted_out'])
    
    return {
        'total_users_cached': total_users,
        'opted_out_users': opted_out_users,
        'opted_in_users': total_users - opted_out_users,
        'opt_out_rate': opted_out_users / max(total_users, 1),
        'cache_size': len(_opt_out_cache)
    }

def clear_opt_out_cache() -> None:
    """Clear the opt-out cache."""
    global _opt_out_cache
    _opt_out_cache.clear()
    logger.info("Opt-out cache cleared")

def cleanup_expired_cache() -> int:
    """
    Remove expired entries from the opt-out cache.
    
    Returns:
        int: Number of entries removed
    """
    global _opt_out_cache
    current_time = datetime.utcnow()
    expired_keys = []
    
    for key, data in _opt_out_cache.items():
        if current_time - data['timestamp'] >= _cache_ttl:
            expired_keys.append(key)
    
    for key in expired_keys:
        del _opt_out_cache[key]
    
    if expired_keys:
        logger.debug(f"Removed {len(expired_keys)} expired opt-out cache entries")
    
    return len(expired_keys) 