"""
Proxy routes for the Corgi Recommender Service.

This module provides a transparent proxy that forwards requests to Mastodon instances
while intercepting specific endpoints to inject personalized recommendations.
"""

import logging
import requests
import json
from flask import Blueprint, request, Response, jsonify, g, current_app
from urllib.parse import urljoin, urlparse
import time

from db.connection import get_db_connection
from utils.logging_decorator import log_route
from utils.privacy import get_user_privacy_level

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
proxy_bp = Blueprint('proxy', __name__)

def get_user_instance(req):
    """
    Extract the user's Mastodon instance from request.
    
    Attempts to determine the instance from:
    1. X-Mastodon-Instance header
    2. instance query parameter
    3. Authorization token lookup in user_identities
    
    Args:
        req: The Flask request object
        
    Returns:
        str: The Mastodon instance URL with scheme (e.g., https://mastodon.social)
    """
    # Check for explicit instance header (set by client)
    instance = req.headers.get('X-Mastodon-Instance')
    if instance:
        logger.debug(f"Using instance from X-Mastodon-Instance header: {instance}")
        # Ensure instance has scheme
        if not instance.startswith(('http://', 'https://')):
            instance = f"https://{instance}"
        return instance
    
    # Check for instance query parameter
    instance = req.args.get('instance')
    if instance:
        logger.debug(f"Using instance from query parameter: {instance}")
        if not instance.startswith(('http://', 'https://')):
            instance = f"https://{instance}"
        return instance
    
    # Try to extract from authorization token
    auth_header = req.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        # Look up in database
        user_info = get_user_by_token(token)
        if user_info and 'instance_url' in user_info:
            logger.debug(f"Using instance from token lookup: {user_info['instance_url']}")
            return user_info['instance_url']
    
    # Default fallback instance
    default_instance = current_app.config.get('DEFAULT_MASTODON_INSTANCE', 'https://mastodon.social')
    logger.warning(f"No instance found in request, using default: {default_instance}")
    return default_instance

def get_user_by_token(token):
    """
    Look up user information based on an OAuth token.
    
    Args:
        token: The OAuth token to look up
        
    Returns:
        dict: User information including instance_url and user_id
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, instance_url, access_token 
                    FROM user_identities 
                    WHERE access_token = %s
                """, (token,))
                
                result = cur.fetchone()
                if result:
                    return {
                        'user_id': result[0],
                        'instance_url': result[1],
                        'access_token': result[2]
                    }
    except Exception as e:
        logger.error(f"Database error looking up token: {e}")
    
    return None

def get_authenticated_user(req):
    """
    Resolve the internal user ID from the request.
    
    Args:
        req: The Flask request object
        
    Returns:
        str: Internal user ID for the authenticated user or None
    """
    # Try to get from the Authorization header
    auth_header = req.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        # Look up in database
        user_info = get_user_by_token(token)
        if user_info:
            return user_info['user_id']
    
    # Try to get from query parameters (for development/testing)
    user_id = req.args.get('user_id')
    if user_id:
        return user_id
    
    # No user identified
    return None

def check_user_privacy(user_id):
    """
    Check if a user has opted out of personalization.
    
    Args:
        user_id: The user ID to check
        
    Returns:
        bool: True if personalization is allowed, False otherwise
    """
    if not user_id:
        return False
    
    try:
        with get_db_connection() as conn:
            privacy_level = get_user_privacy_level(conn, user_id)
            
            # Only allow personalization for 'full' privacy level
            return privacy_level == 'full'
    except Exception as e:
        logger.error(f"Error checking privacy settings: {e}")
        # Default to no personalization on error
        return False

def get_recommendations(user_id, limit=5):
    """
    Get personalized recommendations for a user.
    
    Args:
        user_id: The user ID to get recommendations for
        limit: Maximum number of recommendations to return
        
    Returns:
        list: List of Mastodon-compatible post objects
    """
    try:
        # Import here to avoid circular imports
        from routes.recommendations import get_recommended_timeline
        
        # Create a mock request with user_id and limit
        class MockRequest:
            args = {'user_id': user_id, 'limit': limit}
        
        # Call the recommendations endpoint directly
        recommendations = get_recommended_timeline(MockRequest())
        
        # Parse the JSON response
        if isinstance(recommendations, Response):
            try:
                recommendations = json.loads(recommendations.get_data(as_text=True))
            except:
                recommendations = []
        
        # Mark recommendations so they can be identified
        for rec in recommendations:
            rec['is_recommendation'] = True
            
            # Ensure recommendations have a minimum set of fields
            if 'id' not in rec:
                rec['id'] = f"rec_{int(time.time())}_{hash(str(rec)) % 10000}"
                
            # Add explanation if missing
            if 'recommendation_reason' not in rec:
                rec['recommendation_reason'] = "Recommended for you"
                
        return recommendations
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return []

def blend_recommendations(original_posts, recommendations, blend_ratio=0.3):
    """
    Blend recommendations into the original timeline.
    
    Args:
        original_posts: List of posts from Mastodon
        recommendations: List of personalized recommendations
        blend_ratio: Approximate ratio of recommendations to include
        
    Returns:
        list: Combined and sorted list of posts
    """
    if not recommendations:
        logger.debug("No recommendations to blend")
        return original_posts
    
    if not original_posts:
        logger.debug("No original posts, returning only recommendations")
        return recommendations
    
    # Compute how many recommendations to include
    total_posts = len(original_posts)
    rec_count = min(len(recommendations), max(1, int(total_posts * blend_ratio)))
    
    # Get the subset of recommendations to use
    recs_to_use = recommendations[:rec_count]
    
    # Calculate spacing for injecting recommendations
    if total_posts <= rec_count:
        # If few original posts, alternate
        spacing = 1
    else:
        # Otherwise, distribute evenly
        spacing = max(1, total_posts // rec_count - 1)
    
    # Create the blended timeline
    blended = []
    rec_index = 0
    
    for i, post in enumerate(original_posts):
        blended.append(post)
        
        # Insert a recommendation after every 'spacing' posts
        if i % spacing == 0 and rec_index < len(recs_to_use):
            blended.append(recs_to_use[rec_index])
            rec_index += 1
    
    # Add any remaining recommendations at the end
    if rec_index < len(recs_to_use):
        blended.extend(recs_to_use[rec_index:])
    
    # Ensure we're not returning more than the original count (to avoid pagination issues)
    # Allow up to 3 extra posts for a smoother experience
    max_allowed = total_posts + 3
    if len(blended) > max_allowed:
        blended = blended[:max_allowed]
    
    return blended

@proxy_bp.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@log_route
def proxy_to_mastodon(path):
    """
    Proxy requests to the appropriate Mastodon instance.
    
    For most endpoints, simply forwards the request unchanged.
    For timeline endpoints, injects personalized recommendations.
    
    Args:
        path: The API path after /api/v1/
        
    Returns:
        Response: The proxied response, potentially with injected recommendations
    """
    # Extract Mastodon instance to proxy to
    instance_url = get_user_instance(request)
    
    # Build the target URL
    target_url = urljoin(instance_url, f"/api/v1/{path}")
    
    # Log the proxy attempt
    logger.info(f"Proxying {request.method} request to {target_url}")
    
    # Extract request components
    method = request.method
    headers = {key: value for key, value in request.headers.items()
               if key.lower() not in ['host', 'content-length']}
    params = request.args.to_dict()
    data = request.get_data()
    
    try:
        # Make the request to the target Mastodon instance
        start_time = time.time()
        proxied_response = requests.request(
            method=method,
            url=target_url,
            headers=headers,
            params=params,
            data=data,
            timeout=10
        )
        response_time = time.time() - start_time
        
        logger.debug(f"Proxied request completed in {response_time:.3f}s with status {proxied_response.status_code}")
        
        # Extract the response for potential modification
        response_headers = {key: value for key, value in proxied_response.headers.items()
                            if key.lower() not in ['content-encoding', 'transfer-encoding', 'content-length']}
        response_content = proxied_response.content
        status_code = proxied_response.status_code
        
        # For timeline/home, consider injecting recommendations
        if path == 'timelines/home' and method == 'GET' and status_code == 200:
            # Get the authenticated user
            user_id = get_authenticated_user(request)
            
            # Check if personalization is allowed for this user
            personalization_allowed = check_user_privacy(user_id) if user_id else False
            
            if user_id and personalization_allowed:
                try:
                    # Parse the original response
                    original_posts = json.loads(response_content)
                    
                    # Get recommendations for this user
                    recommendations = get_recommendations(user_id)
                    
                    if recommendations:
                        # Blend recommendations with the original posts
                        blended_timeline = blend_recommendations(original_posts, recommendations)
                        
                        # Convert back to JSON
                        response_content = json.dumps(blended_timeline).encode('utf-8')
                        response_headers['Content-Type'] = 'application/json'
                        
                        # Add header to indicate recommendations were injected
                        response_headers['X-Corgi-Recommendations'] = f"injected={len(recommendations)}"
                        
                        logger.info(f"Injected {len(recommendations)} recommendations into timeline for user {user_id}")
                except Exception as e:
                    logger.error(f"Error injecting recommendations: {e}")
                    # Continue with original response on error
            else:
                logger.debug(f"Skipping recommendation injection for user {user_id} (allowed={personalization_allowed})")
        
        # Return the (potentially modified) response
        return Response(
            response_content,
            status=status_code,
            headers=response_headers
        )
                
    except requests.RequestException as e:
        logger.error(f"Proxy request failed: {e}")
        return jsonify({
            "error": "Failed to proxy request to Mastodon instance",
            "instance": instance_url,
            "details": str(e)
        }), 502

# Additional routes for debugging/monitoring

@proxy_bp.route('/status', methods=['GET'])
def proxy_status():
    """
    Status endpoint to check if the proxy is running.
    """
    return jsonify({
        "status": "ok",
        "proxy": "active",
        "default_instance": current_app.config.get('DEFAULT_MASTODON_INSTANCE', 'https://mastodon.social')
    })

@proxy_bp.route('/instance', methods=['GET'])
def detect_instance():
    """
    Debug endpoint to see what instance would be detected for the current request.
    """
    instance = get_user_instance(request)
    user_id = get_authenticated_user(request)
    
    return jsonify({
        "detected_instance": instance,
        "user_id": user_id,
        "headers": dict(request.headers),
        "args": request.args.to_dict()
    })