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

def get_user_from_request() -> Optional[Dict[str, Any]]:
    """
    Extract user information from the current request.
    
    Returns:
        Optional[Dict]: User info or None if not authenticated
    """
    # Check for API key in headers
    api_key = request.headers.get('X-API-Key')
    if api_key:
        # In a real implementation, this would validate against a database
        # For now, we'll use a simple mock implementation
        if api_key == 'admin-key':
            return {'id': 'admin', 'role': 'admin', 'username': 'admin'}
        elif api_key == 'user-key':
            return {'id': 'user123', 'role': 'user', 'username': 'testuser'}
        elif api_key == 'crawler-key':
            return {'id': 'crawler', 'role': 'crawler', 'username': 'content_crawler'}
    
    # Check for Bearer token
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        # In a real implementation, this would validate the JWT token
        # For now, we'll use a simple mock
        if token == 'valid-user-token':
            return {'id': 'user456', 'role': 'user', 'username': 'tokenuser'}
    
    # No valid authentication found
    return None

def get_user_role(user: Optional[Dict[str, Any]]) -> str:
    """
    Get the role of a user.
    
    Args:
        user: User info dictionary
        
    Returns:
        str: User role, defaults to 'guest' if not authenticated
    """
    if not user:
        return 'guest'
    return user.get('role', 'guest')

def get_role_permissions(role: str) -> List[str]:
    """
    Get permissions for a role.
    
    Args:
        role: Role name
        
    Returns:
        List[str]: List of permissions for the role
    """
    role_info = ROLES.get(role, ROLES.get('guest', {}))
    permissions = role_info.get('permissions', [])
    
    # Handle wildcard permissions (admin)
    if '*' in permissions:
        return list(PERMISSIONS.keys())
    
    return permissions

def check_permission(user: Optional[Dict[str, Any]], required_permission: str) -> bool:
    """
    Check if a user has a specific permission.
    
    Args:
        user: User info dictionary
        required_permission: Permission to check
        
    Returns:
        bool: True if user has permission, False otherwise
    """
    if not user and required_permission != 'read_public_content':
        return False
    
    role = get_user_role(user)
    permissions = get_role_permissions(role)
    
    # Check for wildcard or specific permission
    return '*' in permissions or required_permission in permissions

def check_role(user: Optional[Dict[str, Any]], required_role: str) -> bool:
    """
    Check if a user has a specific role.
    
    Args:
        user: User info dictionary
        required_role: Role to check
        
    Returns:
        bool: True if user has role, False otherwise
    """
    if not user:
        return required_role == 'guest'
    
    user_role = get_user_role(user)
    return user_role == required_role

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