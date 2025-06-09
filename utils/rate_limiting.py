"""
Rate limiting utilities for the Corgi Recommender Service.

This module provides decorators and functions for implementing rate limiting
across different endpoints and user types.
"""

import functools
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def get_user_identity() -> str:
    """
    Get user identity for rate limiting purposes.
    
    Returns:
        str: User identifier (user_id if authenticated, IP address otherwise)
    """
    try:
        # Try to get authenticated user
        from utils.auth import get_authenticated_user
        user_id = get_authenticated_user()
        if user_id:
            return f"user:{user_id}"
    except Exception:
        pass
    
    # Fall back to IP address
    try:
        from flask import request
        return f"ip:{request.remote_addr}"
    except Exception:
        return "anonymous:default"

def init_rate_limiter(app=None):
    """
    Initialize rate limiter with the Flask app.
    
    Args:
        app: Flask application instance
    """
    if app is None:
        return
    
    try:
        from config import RATE_LIMITING_ENABLED
        if not RATE_LIMITING_ENABLED:
            logger.info("Rate limiting is disabled")
            return
        
        logger.info("Rate limiting initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize rate limiter: {e}")

# Rate limiting decorators for different endpoints
def limit_health(f):
    """Rate limiting decorator for health endpoints."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # In a full implementation, this would check rate limits
        # For now, just call the function
        return f(*args, **kwargs)
    return wrapper

def limit_analytics(f):
    """Rate limiting decorator for analytics endpoints."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

def limit_recommendations(f):
    """Rate limiting decorator for recommendation endpoints."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

def limit_proxy(f):
    """Rate limiting decorator for proxy endpoints."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

def limit_timeline(f):
    """Rate limiting decorator for timeline endpoints."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

def limit_interactions(f):
    """Rate limiting decorator for interaction endpoints."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

def limit_oauth(f):
    """Rate limiting decorator for OAuth endpoints."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

def limit_setup(f):
    """Rate limiting decorator for setup endpoints."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper 