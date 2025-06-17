"""
Role-Based Access Control (RBAC) utilities for the Corgi Recommender Service.

This module provides authentication and authorization functionality for
content discovery routes and other protected endpoints.
"""

import functools
import logging
from typing import Optional, List, Dict, Any
from flask import request, jsonify, g

logger = logging.getLogger(__name__)

# Role definitions
ROLES = {
    'admin': {
        'name': 'Administrator',
        'permissions': ['*']  # All permissions
    },
    'user': {
        'name': 'User',
        'permissions': ['read_content', 'create_interactions', 'view_recommendations']
    },
    'guest': {
        'name': 'Guest',
        'permissions': ['read_public_content']
    },
    'crawler': {
        'name': 'Content Crawler',
        'permissions': ['crawl_content', 'create_posts', 'read_content']
    }
}

# Permission definitions
PERMISSIONS = {
    'read_content': 'Read content and posts',
    'read_public_content': 'Read public content only',
    'create_interactions': 'Create user interactions',
    'view_recommendations': 'View personalized recommendations',
    'crawl_content': 'Crawl content from external sources',
    'create_posts': 'Create new posts',
    'admin_access': 'Administrative access',
    'manage_users': 'Manage user accounts',
    'view_analytics': 'View system analytics'
}

def validate_api_key_from_database(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Validate API key against database records.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        Optional[Dict]: User info if valid, None otherwise
    """
    try:
        from db.connection import get_db_connection
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            # Use parameterized query to prevent SQL injection
            cur.execute("""
                SELECT user_id, role, username, is_active 
                FROM api_keys 
                WHERE api_key = %s AND is_active = true
            """, (api_key,))
            
            result = cur.fetchone()
            if result:
                user_id, role, username, is_active = result
                return {
                    'id': user_id,
                    'role': role,
                    'username': username,
                    'api_key': api_key[:8] + '...'  # Truncated for logging
                }
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
    
    return None

def get_user_from_request() -> Optional[Dict[str, Any]]:
    """
    Extract user information from the current request.
    
    Returns:
        Optional[Dict]: User info or None if not authenticated
    """
    # Check for API key in headers
    api_key = request.headers.get('X-API-Key')
    if api_key:
        # Validate against database instead of hardcoded values
        user = validate_api_key_from_database(api_key)
        if user:
            return user
        else:
            logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
    
    # Check for Bearer token
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        # Validate token properly (implementation depends on token type)
        user = validate_bearer_token(token)
        if user:
            return user
    
    # No valid authentication found
    return None

def validate_bearer_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate Bearer token against database or JWT validation.
    
    Args:
        token: Bearer token to validate
        
    Returns:
        Optional[Dict]: User info if valid, None otherwise
    """
    try:
        from utils.auth import get_user_by_token
        
        user_info = get_user_by_token(token)
        if user_info:
            return {
                'id': user_info.get('user_id'),
                'role': 'user',  # Default role, could be enhanced
                'username': user_info.get('user_id'),
                'instance_url': user_info.get('instance_url')
            }
    except Exception as e:
        logger.error(f"Error validating bearer token: {e}")
    
    return None

def has_role(user: Optional[Dict[str, Any]], required_role: str) -> bool:
    """
    Check if user has the required role.
    
    Args:
        user: User dictionary
        required_role: Required role name
        
    Returns:
        bool: True if user has the role
    """
    if not user:
        return False
    
    user_role = user.get('role', 'guest')
    
    # Admin has all roles
    if user_role == 'admin':
        return True
    
    return user_role == required_role

def has_permission(user: Optional[Dict[str, Any]], required_permission: str) -> bool:
    """
    Check if user has the required permission.
    
    Args:
        user: User dictionary
        required_permission: Required permission name
        
    Returns:
        bool: True if user has the permission
    """
    if not user:
        return False
    
    user_role = user.get('role', 'guest')
    
    if user_role not in ROLES:
        return False
    
    role_permissions = ROLES[user_role]['permissions']
    
    # Check for wildcard permission (admin)
    if '*' in role_permissions:
        return True
    
    return required_permission in role_permissions

def check_role(user: Optional[Dict[str, Any]], required_role: str) -> bool:
    """
    Check if user has the required role.
    
    Args:
        user: User dictionary
        required_role: Required role name
        
    Returns:
        bool: True if user has the role
    """
    return has_role(user, required_role)

def check_permission(user: Optional[Dict[str, Any]], required_permission: str) -> bool:
    """
    Check if user has the required permission.
    
    Args:
        user: User dictionary
        required_permission: Required permission name
        
    Returns:
        bool: True if user has the permission
    """
    return has_permission(user, required_permission)

def require_authentication(f):
    """
    Decorator to require authentication for a route.
    
    Args:
        f: Flask route function
        
    Returns:
        Decorated function that checks authentication
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_user_from_request()
        if not user:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please provide valid API key or Bearer token'
            }), 401
        
        # Store user in Flask's g object for use in the route
        g.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function

def require_permission(permission: str):
    """
    Decorator to require a specific permission for a route.
    
    Args:
        permission: Required permission
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_user_from_request()
            
            if not check_permission(user, permission):
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'Permission "{permission}" required',
                    'required_permission': permission
                }), 403
            
            # Store user in Flask's g object for use in the route
            g.current_user = user
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_role(role: str):
    """
    Decorator to require a specific role for a route.
    
    Args:
        role: Required role
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_user_from_request()
            
            if not check_role(user, role):
                return jsonify({
                    'error': 'Insufficient role',
                    'message': f'Role "{role}" required',
                    'required_role': role
                }), 403
            
            # Store user in Flask's g object for use in the route
            g.current_user = user
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get the current authenticated user from Flask's g object.
    
    Returns:
        Optional[Dict]: Current user or None if not authenticated
    """
    return getattr(g, 'current_user', None)

def is_admin(user: Optional[Dict[str, Any]] = None) -> bool:
    """
    Check if a user is an admin.
    
    Args:
        user: User to check, defaults to current user
        
    Returns:
        bool: True if user is admin, False otherwise
    """
    if user is None:
        user = get_current_user()
    
    return check_role(user, 'admin')

def can_access_analytics(user: Optional[Dict[str, Any]] = None) -> bool:
    """
    Check if a user can access analytics.
    
    Args:
        user: User to check, defaults to current user
        
    Returns:
        bool: True if user can access analytics, False otherwise
    """
    if user is None:
        user = get_current_user()
    
    return check_permission(user, 'view_analytics') or is_admin(user) 