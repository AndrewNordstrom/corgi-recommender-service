#!/usr/bin/env python3
"""
Fixed special proxy server for testing Elk integration with Corgi.

This script creates a Flask application that serves as a dedicated proxy server
for integrating Elk with Corgi, handling Mastodon API requests and properly
configuring database connections.
"""

import os
import logging
import sys
import sqlite3
import argparse
import json
import random
from flask import Flask, request, g, jsonify, Response
import requests
from urllib.parse import urljoin
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('corgi_proxy')

# Define database file path
DB_FILE = os.path.join(os.path.dirname(__file__), 'corgi_demo.db')

# Define cold start posts file path
COLD_START_POSTS_PATH = os.path.join(os.path.dirname(__file__), 'data', 'cold_start_posts.json')

# Create Flask app
app = Flask(__name__)

# Configure CORS - for development, we'll allow all origins
from flask_cors import CORS
CORS(app, 
    resources={r"/*": {"origins": "*"}}, 
    supports_credentials=True,
    allow_headers=["*"],
    expose_headers=["*"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Custom error handler for all exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    """
    Global exception handler that logs the full error but returns a generic message
    to prevent information leakage to potential attackers.
    """
    # Log the full error for debugging
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    
    # Return a generic error message
    return jsonify({
        "status": "error",
        "message": "An internal server error occurred"
    }), 500

@app.before_request
def setup_sqlite_connection():
    """Setup SQLite connection for all requests"""
    # Store the SQLite connection in g
    g.sqlite_conn = sqlite3.connect(DB_FILE)
    g.sqlite_conn.row_factory = sqlite3.Row

@app.teardown_request
def close_sqlite_connection(exception=None):
    """Close SQLite connection after request"""
    sqlite_conn = getattr(g, 'sqlite_conn', None)
    if sqlite_conn is not None:
        sqlite_conn.close()

def get_user_by_token(token):
    """SQLite version of get_user_by_token"""
    if not token:
        return None
        
    try:
        # Use the SQLite connection from g
        cursor = g.sqlite_conn.cursor()
        cursor.execute(
            """
            SELECT user_id, instance_url, access_token 
            FROM user_identities 
            WHERE access_token = ?
            """, 
            (token,)
        )
        
        result = cursor.fetchone()
        if result:
            logger.info(f"Found user {result['user_id']} for token")
            return {
                'user_id': result['user_id'],
                'instance_url': result['instance_url'],
                'access_token': result['access_token']
            }
        else:
            logger.warning(f"No user found for token")
    except Exception as e:
        logger.error(f"Database error looking up token: {e}")
    
    return None

def get_user_instance(req):
    """
    Extract the user's Mastodon instance from request.
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
    default_instance = "https://mastodon.social"
    logger.warning(f"No instance found in request, using default: {default_instance}")
    return default_instance

def get_authenticated_user(req):
    """
    Resolve the internal user ID from the request.
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

@app.route('/api/v1/proxy/status', methods=['GET'])
def proxy_status():
    """
    Status endpoint to check if the proxy is running.
    """
    return jsonify({
        "status": "ok",
        "proxy": "active",
        "default_instance": "https://mastodon.social"
    })

@app.route('/api/v1/proxy/instance', methods=['GET'])
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

@app.route('/oauth/token', methods=['POST'])
def mock_oauth_token():
    """
    Mock OAuth token endpoint for Elk authentication.
    """
    # This is a simplified version that just returns our demo token
    logger.info(f"OAuth token request received: {request.form}")
    
    # Return a mock token response
    return jsonify({
        "access_token": "lJrzv-c0l5_pzmHNnw2EgTzuE0U-A-CIwjbCSTR5cp8",
        "token_type": "Bearer",
        "scope": "read write follow",
        "created_at": 1619068413
    })

@app.route('/oauth/authorize', methods=['GET'])
def mock_oauth_authorize():
    """
    Mock OAuth authorization endpoint for Elk authentication.
    """
    logger.info(f"OAuth authorize request received: {request.args}")
    
    # Get the redirect URI
    redirect_uri = request.args.get('redirect_uri', '')
    
    # Simple HTML form that auto-submits to redirect back to Elk with the code
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authorize Elk</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
            .container {{ max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            button {{ padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Authorize Elk</h1>
            <p>This is a mock OAuth authorization page for testing purposes.</p>
            <p>Click the button below to authorize Elk to use Corgi Recommender.</p>
            <form id="auth-form" method="post" action="/oauth/mock-redirect">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <button type="submit">Authorize</button>
            </form>
            <p><small>Token: lJrzv-c0l5_pzmHNnw2EgTzuE0U-A-CIwjbCSTR5cp8</small></p>
        </div>
    </body>
    </html>
    """
    
    return html

@app.route('/oauth/mock-redirect', methods=['POST'])
def mock_oauth_redirect():
    """
    Handle the redirect back to Elk after OAuth authorization.
    """
    redirect_uri = request.form.get('redirect_uri', '')
    
    if not redirect_uri:
        return "Error: No redirect URI provided", 400
    
    # Validate redirect URI to prevent open redirect
    if not redirect_uri.startswith(('http://', 'https://')):
        return "Error: Invalid redirect URI", 400
        
    # Further restrict to only allow certain domains
    allowed_domains = ['localhost', '127.0.0.1', 'elk.zone', 'corgi-recommender.example.com']
    from urllib.parse import urlparse
    parsed_uri = urlparse(redirect_uri)
    if not any(parsed_uri.netloc.endswith(domain) for domain in allowed_domains):
        return "Error: Redirect URI domain not allowed", 403
    
    # Add code parameter to redirect URI
    if '?' in redirect_uri:
        redirect_url = f"{redirect_uri}&code=mock_auth_code"
    else:
        redirect_url = f"{redirect_uri}?code=mock_auth_code"
    
    logger.info(f"Redirecting to: {redirect_url}")
    
    # Escape the URL to prevent XSS
    import html
    safe_redirect_url = html.escape(redirect_url)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Redirecting...</title>
        <meta http-equiv="refresh" content="0;url={safe_redirect_url}">
    </head>
    <body>
        <p>Redirecting to Elk... If you are not redirected, <a href="{safe_redirect_url}">click here</a>.</p>
    </body>
    </html>
    """

@app.route('/api/v1/apps/verify_credentials', methods=['GET'])
def verify_app_credentials():
    """
    Verify application credentials for Elk.
    """
    return jsonify({
        "name": "Corgi Recommender Proxy",
        "website": "https://example.com/corgi",
        "vapid_key": "MOCK_VAPID_KEY"
    })

@app.route('/api/v1/accounts/verify_credentials', methods=['GET'])
def verify_account_credentials():
    """
    Verify account credentials for Elk.
    """
    user_id = get_authenticated_user(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Use the actual user ID for all fields
    return jsonify({
        "id": user_id,
        "username": user_id,
        "acct": f"{user_id}@mastodon.social",
        "display_name": user_id,
        "locked": False,
        "bot": False,
        "created_at": "2023-01-01T00:00:00.000Z",
        "note": f"Corgi user: {user_id}",
        "url": f"https://mastodon.social/@{user_id}",
        "avatar": "https://mastodon.social/avatars/original/missing.png",
        "avatar_static": "https://mastodon.social/avatars/original/missing.png",
        "header": "https://mastodon.social/headers/original/missing.png",
        "header_static": "https://mastodon.social/headers/original/missing.png",
        "followers_count": 0,
        "following_count": 0,
        "statuses_count": 0,
        "source": {
            "privacy": "public",
            "sensitive": False,
            "language": "en"
        }
    })

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses to ensure preflight works correctly."""
    # For development, allow all origins
    origin = request.headers.get('Origin')
    if origin:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', 
                             'GET, POST, PUT, DELETE, OPTIONS, PATCH')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Max-Age', '86400')  # 24 hours for preflight
    
    # Log the request info for debugging
    logger.debug(f"Request: {request.method} {request.path} | Origin: {origin} | Response: {response.status_code}")
    
    return response

@app.route('/api/v1/preferences', methods=['GET'])
def api_preferences():
    """
    Handle preferences API endpoint.
    """
    logger.info(f"Preferences request received from: {request.remote_addr}")
    # Return basic preference defaults
    return jsonify({
        "posting:default:visibility": "public",
        "posting:default:sensitive": False,
        "posting:default:language": None,
        "reading:expand:media": "default",
        "reading:expand:spoilers": False
    })

@app.route('/api/v1/markers', methods=['GET'])
def api_markers():
    """
    Handle markers API endpoint for timeline position.
    """
    logger.info(f"Markers request received from: {request.remote_addr}")
    return jsonify({
        "home": {
            "last_read_id": "103206804533364471",
            "version": 1,
            "updated_at": "2021-05-12T00:39:08.403Z"
        }
    })

@app.route('/api/v1/filters', methods=['GET'])
def api_filters():
    """
    Handle filters API endpoint.
    """
    logger.info(f"Filters request received from: {request.remote_addr}")
    return jsonify([])

@app.route('/api/v1/lists', methods=['GET'])
def api_lists():
    """
    Handle user lists API endpoint.
    """
    logger.info(f"Lists request received from: {request.remote_addr}")
    return jsonify([])

@app.route('/api/v1/custom_emojis', methods=['GET'])
def api_custom_emojis():
    """
    Handle custom emojis API endpoint.
    """
    logger.info(f"Custom emojis request received from: {request.remote_addr}")
    return jsonify([])

@app.route('/api/v1/notifications', methods=['GET'])
def api_notifications():
    """
    Handle notifications API endpoint.
    """
    logger.info(f"Notifications request received from: {request.remote_addr}")
    return jsonify([])

@app.route('/api/v1/instance', methods=['GET'])
def api_v1_instance():
    """
    Handle API v1 instance information requests.
    """
    logger.info(f"Instance v1 info request received from: {request.remote_addr}")
    return jsonify({
        "uri": "localhost:5004",
        "title": "Corgi Recommender Service",
        "description": "A recommendation engine for Mastodon",
        "email": "admin@example.com",
        "version": "4.1.1",
        "urls": {
            "streaming_api": "wss://localhost:5004"
        },
        "stats": {
            "user_count": 10,
            "status_count": 100,
            "domain_count": 1
        },
        "thumbnail": "https://mastodon.social/avatars/original/missing.png",
        "languages": ["en"],
        "registrations": False,
        "approval_required": True,
        "invites_enabled": False,
        "configuration": {
            "statuses": {
                "max_characters": 500,
                "max_media_attachments": 4,
                "characters_reserved_per_url": 23
            },
            "media_attachments": {
                "supported_mime_types": [
                    "image/jpeg",
                    "image/png",
                    "image/gif",
                    "image/webp"
                ],
                "image_size_limit": 10485760,
                "image_matrix_limit": 16777216,
                "video_size_limit": 41943040,
                "video_frame_rate_limit": 60,
                "video_matrix_limit": 2304000
            },
            "polls": {
                "max_options": 4,
                "max_characters_per_option": 50,
                "min_expiration": 300,
                "max_expiration": 2629746
            }
        }
    })

@app.route('/api/v1/instance/peers', methods=['GET'])
def api_instance_peers():
    """
    Handle instance peers API endpoint.
    """
    logger.info(f"Instance peers request received from: {request.remote_addr}")
    return jsonify(["mastodon.social"])

@app.route('/api/v1/tags/<tag_name>', methods=['GET'])
def api_tag(tag_name):
    """
    Handle tag information endpoint.
    This endpoint is used by Elk to show tag info and posts with the tag.
    """
    logger.info(f"Tag info request for {tag_name} from: {request.remote_addr}")
    
    # Return tag information
    return jsonify({
        "name": tag_name,
        "url": f"https://mastodon.social/tags/{tag_name}",
        "history": [
            {"day": "1624492800", "uses": "18", "accounts": "12"},
            {"day": "1624406400", "uses": "21", "accounts": "15"},
            {"day": "1624320000", "uses": "15", "accounts": "10"}
        ],
        "following": False
    })

@app.route('/api/v1/timelines/tag/<tag_name>', methods=['GET'])
def api_tag_timeline(tag_name):
    """
    Handle tag timeline endpoint.
    This shows posts containing the tag.
    """
    logger.info(f"Tag timeline request for {tag_name} from: {request.remote_addr}")
    request_id = hash(f"{request.remote_addr}_{request.path}") % 10000000
    
    # Load real cold start posts
    cold_start_posts = load_cold_start_posts()
    
    # Filter posts to first 5 (in a real implementation, we'd filter by tag)
    tag_posts = []
    for i, post in enumerate(cold_start_posts[:5]):
        # Clone the post so we don't modify the original
        post_copy = post.copy() if isinstance(post, dict) else {}
        
        # Process the post for Elk compatibility
        # 1. Make sure all required fields exist
        if 'id' not in post_copy:
            post_copy['id'] = f"tag-{tag_name}-{i}-{hash(str(post)) % 10000}"
            
        # 2. Set the key field which is important for Vue rendering
        post_copy['key'] = f"status-{post_copy['id']}"
        
        # 3. Add the tag to post content and tags array if not already present
        # For display purposes, inject the requested tag into the content
        if 'content' in post_copy:
            if f"#{tag_name}" not in post_copy['content']:
                # Inject the tag before the closing paragraph
                post_copy['content'] = post_copy['content'].replace(
                    "</p>",
                    f" <a href=\"https://mastodon.social/tags/{tag_name}\" class=\"mention hashtag\" rel=\"tag\">#{tag_name}</a></p>",
                    1
                )
        
        # 4. Add or update tags array
        if 'tags' not in post_copy or not isinstance(post_copy['tags'], list):
            post_copy['tags'] = []
            
        # Add the tag if not already present
        if not any(t.get('name') == tag_name for t in post_copy['tags']):
            post_copy['tags'].append({
                "name": tag_name,
                "url": f"https://mastodon.social/tags/{tag_name}"
            })
        
        # 5. Make sure the "filtered" field is an array, not a boolean
        post_copy['filtered'] = []
        
        # 6. Ensure account object is fully populated
        if 'account' in post_copy and isinstance(post_copy['account'], dict):
            account = post_copy['account']
            
            # Required fields for Elk
            if 'acct' not in account:
                if '@' in account.get('username', ''):
                    account['acct'] = account['username']
                else:
                    account['acct'] = f"{account.get('username', 'user')}@mastodon.social"
                    
            if 'url' not in account:
                domain = "mastodon.social"
                username = account.get('username', 'user')
                account['url'] = f"https://{domain}/@{username}"
        
        tag_posts.append(post_copy)
    
    logger.info(f"TAG-{request_id} | Generated {len(tag_posts)} posts for tag #{tag_name}")
    return jsonify(tag_posts)

def create_complete_status(status_id, account_id="user123"):
    """
    Create a complete status object with all fields needed by Elk.
    This is a helper function to ensure consistent status objects.
    """
    return {
        "id": status_id,
        "uri": f"https://mastodon.social/users/{account_id}/statuses/{status_id}",
        "url": f"https://mastodon.social/@andrewn/{status_id}",
        "created_at": "2023-01-01T00:00:00.000Z",
        "content": "<p>This is a sample status post created by the Corgi recommender service.</p>",
        "visibility": "public",
        "sensitive": False,
        "spoiler_text": "",
        "media_attachments": [],
        "mentions": [],
        "tags": [],
        "emojis": [],
        "application": {
            "name": "Corgi Recommender"
        },
        "account": {
            "id": account_id,
            "username": "andrewn",
            "acct": "andrewn@mastodon.social",
            "display_name": "Andrew Nordstrom",
            "url": "https://mastodon.social/@andrewn",
            "avatar": "https://mastodon.social/avatars/original/missing.png",
            "avatar_static": "https://mastodon.social/avatars/original/missing.png",
            "header": "https://mastodon.social/headers/original/missing.png",
            "header_static": "https://mastodon.social/headers/original/missing.png",
            "note": "Sample user bio",
            "followers_count": 42,
            "following_count": 100,
            "statuses_count": 255,
            "bot": False,
            "locked": False,
            "created_at": "2021-01-01T00:00:00.000Z",
            "fields": [],
            "emojis": []
        },
        "favourites_count": 5,
        "reblogs_count": 2,
        "replies_count": 1,
        "language": "en",
        "favourited": False,
        "reblogged": False,
        "bookmarked": False,
        "pinned": False,
        "muted": False,
        "filtered": [],
        "in_reply_to_id": None,
        "in_reply_to_account_id": None,
        "card": None,
        "poll": None,
        "edited_at": None,
        "replying_to_id": None,
        "replying_to_account_id": None,
        "replying_to_screen_name": None,
        "reply_count": 0,
        "key": f"status-{status_id}",  # Important for Vue key prop
        "text": "This is a sample status post created by the Corgi recommender service."  # Plain text version
    }

@app.route('/api/v1/statuses/<status_id>', methods=['GET'])
def api_get_status(status_id):
    """
    Handle individual status API endpoint.
    """
    logger.info(f"Status request received for ID {status_id} from: {request.remote_addr}")
    
    # Return a complete status object
    return jsonify(create_complete_status(status_id))

@app.route('/api/v1/statuses/<status_id>/context', methods=['GET'])
def api_status_context(status_id):
    """
    Handle status context API endpoint - this shows conversations.
    """
    logger.info(f"Status context request for ID {status_id} from: {request.remote_addr}")
    
    # For demo purposes, create a simple context with 1 ancestor and 1 descendant
    # This helps Elk render the conversation view correctly
    ancestor_id = f"{status_id}-ancestor"
    descendant_id = f"{status_id}-reply"
    
    ancestors = [create_complete_status(ancestor_id)]
    descendants = [create_complete_status(descendant_id, "other_user")]
    
    # Set reply relationship
    descendants[0]["in_reply_to_id"] = status_id
    descendants[0]["in_reply_to_account_id"] = "user123"
    
    # Return the context
    return jsonify({
        "ancestors": ancestors,
        "descendants": descendants
    })

@app.route('/api/v1/statuses/<status_id>/reblogged_by', methods=['GET'])
def api_status_reblogs(status_id):
    """
    Handle status reblogged by API endpoint.
    """
    logger.info(f"Status reblogs request for ID {status_id} from: {request.remote_addr}")
    
    # Return an empty list (no reblogs)
    return jsonify([])

@app.route('/api/v1/statuses/<status_id>/favourited_by', methods=['GET'])
def api_status_favs(status_id):
    """
    Handle status favourited by API endpoint.
    """
    logger.info(f"Status favs request for ID {status_id} from: {request.remote_addr}")
    
    # Return an empty list (no favorites)
    return jsonify([])

# Handle the duplicate route too
@app.route('/api/v1/status/<status_id>', methods=['GET'])
def api_status(status_id):
    """
    Alternative path for status API endpoint (redirect to the proper one).
    """
    return api_get_status(status_id)

@app.route('/api/v1/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'])
def mastodon_api_proxy(path):
    """
    Handle all Mastodon API requests.
    This route matches both /api/v1/timelines/home and /api/v1/proxy/xyz for compatibility.
    """
    # Handle OPTIONS requests for CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
    
    # Log all API requests for debugging
    logger.info(f"API request: {request.method} {path} from {request.remote_addr}")
    
    # For proxy-specific endpoints, redirect to the appropriate handler
    if path.startswith('proxy/status'):
        return proxy_status()
    elif path.startswith('proxy/instance'):
        return detect_instance()
    # We're letting timelines/home go directly to the proxy for live data
    # This ensures we get live posts from the Mastodon instance
    elif path == 'apps/verify_credentials':
        return verify_app_credentials()
    elif path == 'accounts/verify_credentials':
        return verify_account_credentials()
    
    # Otherwise handle as a standard proxy request
    return proxy_to_mastodon(path)
    
def proxy_to_mastodon(path):
    """
    Proxy requests to the appropriate Mastodon instance.
    """
    # Extract request information for logging
    request_id = hash(f"{request.remote_addr}_{request.path}") % 10000000
    
    # Extract Mastodon instance to proxy to
    instance_url = get_user_instance(request)
    
    # Build the target URL
    target_url = urljoin(instance_url, f"/api/v1/{path}")
    
    # Get authenticated user information
    user_id = get_authenticated_user(request)
    
    # Log the proxy request
    logger.info(
        f"REQ-{request_id} | {request.method} /{path} | "
        f"Target: {instance_url} | "
        f"User: {user_id or 'anonymous'} | "
        f"Client: {request.remote_addr}"
    )
    
    try:
        # Extract request components
        method = request.method
        headers = {key: value for key, value in request.headers.items()
                 if key.lower() not in ['host', 'content-length']}
                 
        # Ensure we have proper Accept header for JSON
        if 'Accept' not in headers:
            headers['Accept'] = 'application/json'
            
        # Add auth token if we have one in storage but not in the request
        auth_header = headers.get('Authorization')
        if not auth_header and user_id:
            # Look up the user's token
            cursor = g.sqlite_conn.cursor()
            cursor.execute(
                """
                SELECT access_token 
                FROM user_identities 
                WHERE user_id = ?
                """, 
                (user_id,)
            )
            result = cursor.fetchone()
            if result and result['access_token']:
                headers['Authorization'] = f"Bearer {result['access_token']}"
                logger.info(f"REQ-{request_id} | Added auth token for user {user_id}")
                
        params = request.args.to_dict()
        data = request.get_data()
        
        # Log the target URL and headers for debugging
        logger.info(f"PROXY-{request_id} | Proxying {method} request to {target_url}")
        logger.debug(f"PROXY-{request_id} | Headers: {headers}")
        logger.debug(f"PROXY-{request_id} | Params: {params}")
        
        # Make the actual proxy request to the target Mastodon instance
        proxied_response = requests.request(
            method=method,
            url=target_url,
            headers=headers,
            params=params,
            data=data,
            timeout=15,  # Increased timeout for real-world connections
            verify=True  # Verify SSL certificates
        )
        
        # Extract the response for potential enhancement
        response_headers = {key: value for key, value in proxied_response.headers.items()
                        if key.lower() not in ['content-encoding', 'transfer-encoding', 'content-length']}
        status_code = proxied_response.status_code
        
        # For JSON responses, potentially enhance them with recommendations
        if 'application/json' in proxied_response.headers.get('Content-Type', ''):
            try:
                # Parse the JSON response
                response_json = proxied_response.json()
                
                # Handle timeline responses - these are arrays of posts
                if path == 'timelines/home' and isinstance(response_json, list):
                    logger.info(f"ENHANCING-{request_id} | Adding recommendations to home timeline with {len(response_json)} posts")
                    
                    # Load some cold start posts to use as recommendations
                    cold_start_posts = load_cold_start_posts()
                    if cold_start_posts:
                        # Select up to 2 posts to insert as recommendations
                        recommended_posts = []
                        for i, post in enumerate(cold_start_posts[:2]):
                            # Clone the post and prepare it
                            post_copy = post.copy() if isinstance(post, dict) else {}
                            
                            # Mark as recommendation
                            post_copy['is_recommendation'] = True
                            post_copy['recommendation_reason'] = f"Recommended by Corgi for {user_id}"
                            post_copy['filtered'] = []
                            
                            # Set a key for Vue rendering
                            if 'id' in post_copy:
                                post_copy['key'] = f"status-{post_copy['id']}"
                                
                            # Ensure account fields
                            if 'account' in post_copy and isinstance(post_copy['account'], dict):
                                account = post_copy['account']
                                # Required fields for Elk
                                if 'acct' not in account and 'username' in account:
                                    account['acct'] = f"{account['username']}@mastodon.social"
                                    
                                if 'url' not in account and 'username' in account:
                                    account['url'] = f"https://mastodon.social/@{account['username']}"
                            
                            recommended_posts.append(post_copy)
                        
                        # Insert recommendations at appropriate positions
                        if len(response_json) > 3:
                            # Insert into existing timeline
                            positions = [len(response_json) // 3, 2 * len(response_json) // 3]
                            for i, pos in enumerate(positions):
                                if i < len(recommended_posts):
                                    response_json.insert(pos, recommended_posts[i])
                        else:
                            # Timeline is sparse, just append recommendations
                            response_json.extend(recommended_posts)
                    
                    logger.info(f"ENHANCED-{request_id} | Returning enhanced timeline with {len(response_json)} posts")
                    return jsonify(response_json)
                
                # For other endpoints, just return the original JSON
                return jsonify(response_json)
                
            except (ValueError, json.JSONDecodeError) as e:
                # If JSON parsing fails, just return the original response
                logger.error(f"JSON-ERROR-{request_id} | Failed to parse JSON: {e}")
                response = Response(
                    proxied_response.content,
                    status=status_code,
                    headers=response_headers
                )
                return response
        
        # For non-JSON responses, just pass through
        response = Response(
            proxied_response.content,
            status=status_code,
            headers=response_headers
        )
        
        # Log completion
        logger.info(
            f"RESP-{request_id} | Request completed | "
            f"Status: {status_code} | "
            f"Response size: {len(proxied_response.content)} bytes"
        )
        
        return response
        
    except requests.RequestException as e:
        # Error handling for network-related issues
        logger.error(
            f"ERROR-{request_id} | Proxy request failed | "
            f"Target: {instance_url} | "
            f"Error: {str(e)}"
        )
        
        # For timelines, we can fall back to cold start posts
        if path == 'timelines/home':
            logger.info(f"FALLBACK-{request_id} | Using cold start posts as fallback for timeline")
            cold_start_posts = load_cold_start_posts()
            posts_to_return = []
            
            # Process up to 10 cold start posts
            for i, post in enumerate(cold_start_posts[:10]):
                # Ensure the post has all required fields
                post_copy = post.copy() if isinstance(post, dict) else {}
                
                # Mark as fallback content
                post_copy['is_recommendation'] = True
                post_copy['is_fallback'] = True
                post_copy['filtered'] = []
                
                # Set key for Vue rendering
                if 'id' in post_copy:
                    post_copy['key'] = f"status-{post_copy['id']}"
                    
                posts_to_return.append(post_copy)
                
            logger.info(f"FALLBACK-{request_id} | Returning {len(posts_to_return)} cold start posts as fallback")
            return jsonify(posts_to_return)
            
        # For other endpoints, return appropriate empty responses
        if 'notifications' in path:
            return jsonify([])
        elif 'timelines' in path:
            return jsonify([])
        elif 'instance' in path:
            return api_v1_instance()
        elif 'preferences' in path:
            return api_preferences()
        elif 'accounts' in path:
            return verify_account_credentials()
        else:
            # Return appropriate response based on path
            return jsonify({"error": "Could not connect to Mastodon instance", "details": str(e)})
            
    except Exception as e:
        # Catch-all exception handler
        logger.error(
            f"ERROR-{request_id} | Unhandled exception in proxy | "
            f"Path: {path} | "
            f"Error: {str(e)}"
        )
        
        # Return a clear error message
        return jsonify({
            "error": "An unexpected error occurred while processing your request",
            "path": path,
            "details": str(e)
        }), 500

def load_cold_start_posts():
    """Load cold start posts from the JSON file."""
    try:
        with open(COLD_START_POSTS_PATH, 'r') as f:
            posts = json.load(f)
            logger.info(f"Loaded {len(posts)} cold start posts")
            return posts
    except Exception as e:
        logger.error(f"Failed to load cold start posts: {e}")
        return []

def ensure_mastodon_post_format(post, user_id=None):
    """
    Ensure that a post has all fields required by Elk's rendering component.
    
    Args:
        post: The post object to update
        user_id: The current user ID (optional)
        
    Returns:
        The updated post object
    """
    # Log entry for validation
    logger.debug(f"Validating post format for ID: {post.get('id', 'unknown')}")
    if 'account' not in post or not isinstance(post['account'], dict):
        # Create account if missing
        post['account'] = {}
    
    account = post['account']
    
    # Ensure required fields are present
    if 'username' not in account:
        account['username'] = account.get('id', 'user')
        
    # CRITICAL: Set acct field which is used by Elk's getFullHandle()
    if 'acct' not in account:
        if '@' in account.get('username', ''):
            account['acct'] = account['username']
        else:
            # Use username@mastodon.social as default format
            account['acct'] = f"{account.get('username', 'user')}@mastodon.social"
            
    # Set display_name if missing
    if 'display_name' not in account:
        account['display_name'] = account.get('username', 'User')
        
    # Set avatar URL if missing
    if 'avatar' not in account:
        account['avatar'] = "https://mastodon.social/avatars/original/missing.png"
        
    # Set url field which is used by StatusCard.vue
    if 'url' not in account:
        domain = "mastodon.social"
        username = account.get('username', 'user')
        account['url'] = f"https://{domain}/@{username}"
        
    # Make sure all standard Mastodon profile fields exist
    if 'avatar_static' not in account:
        account['avatar_static'] = account.get('avatar', "https://mastodon.social/avatars/original/missing.png")
    if 'header' not in account:
        account['header'] = "https://mastodon.social/headers/original/missing.png"
    if 'header_static' not in account:
        account['header_static'] = account.get('header', "https://mastodon.social/headers/original/missing.png")
    if 'note' not in account:
        account['note'] = ""
    if 'followers_count' not in account:
        account['followers_count'] = 0
    if 'following_count' not in account:
        account['following_count'] = 0
    if 'statuses_count' not in account:
        account['statuses_count'] = 0
    
    # Log validation
    logger.debug(f"Post {post.get('id', 'unknown')} has all required Mastodon fields")
    
    # Add validation flag to indicate this post is fully compatible with Elk
    post['_corgi_validated'] = True
    
    # Log completion with critical fields for troubleshooting
    logger.debug(f"Validated post {post.get('id', 'unknown')}: username={account.get('username', 'missing')}, "
               f"acct={account.get('acct', 'missing')}, url={account.get('url', 'missing')}")
    
    return post

@app.route('/api/v1/timelines/home', methods=['GET'])
def get_home_timeline():
    """
    Get a user's home timeline with recommendations or cold start content
    """
    request_id = hash(f"{request.remote_addr}_{request.path}") % 10000000
    
    # Get authentication
    user_id = get_authenticated_user(request)
    if not user_id:
        logger.warning(f"REQ-{request_id} | No user authenticated for timeline request")
        return jsonify([])
    
    # Get instance
    instance_url = get_user_instance(request)
    
    # Check for cold start mode
    cold_start = request.args.get('cold_start', '').lower() in ('true', '1', 'yes')
    
    # Log the timeline request
    logger.info(
        f"TIMELINE-{request_id} | Requesting home timeline | "
        f"User: {user_id} | "
        f"Instance: {instance_url} | "
        f"Cold start: {cold_start}"
    )
    
    try:
        # If cold start is requested, return cold start posts
        if cold_start:
            logger.info(f"TIMELINE-{request_id} | Using cold start mode for user {user_id}")
            
            # Load the actual cold start posts
            cold_start_posts = load_cold_start_posts()
            logger.info(f"TIMELINE-{request_id} | Loaded {len(cold_start_posts)} posts from cold start database")
            
            # Process cold start posts to ensure they have all required fields
            posts_to_return = []
            for post in cold_start_posts[:20]:  # Limit to 20 posts
                # Preserve the existing post structure including content
                # But ensure all required fields are present for Elk rendering
                
                # 1. Make sure all required fields exist
                if 'id' not in post:
                    post['id'] = f"cold-{len(posts_to_return)}-{hash(str(post)) % 10000}"
                    
                # 2. Set the key field which is important for Vue rendering
                post['key'] = f"status-{post['id']}"
                
                # 3. Set flags to indicate these are recommendations
                post['is_recommendation'] = True
                post['is_cold_start'] = True
                
                # 4. Make sure the "filtered" field is an array, not a boolean
                post['filtered'] = []
                
                # 5. Ensure account object is fully populated
                if 'account' in post and isinstance(post['account'], dict):
                    account = post['account']
                    
                    # Required fields for Elk
                    if 'acct' not in account:
                        if '@' in account.get('username', ''):
                            account['acct'] = account['username']
                        else:
                            account['acct'] = f"{account.get('username', 'user')}@mastodon.social"
                            
                    if 'url' not in account:
                        domain = "mastodon.social"
                        username = account.get('username', 'user')
                        account['url'] = f"https://{domain}/@{username}"
                
                posts_to_return.append(post)
            
            logger.info(f"TIMELINE-{request_id} | Returning {len(posts_to_return)} actual cold start posts")
            
            # Log a sample of the posts for debugging
            for i, post in enumerate(posts_to_return[:2]):
                if 'account' in post and isinstance(post['account'], dict):
                    account = post['account']
                    logger.info(f"TIMELINE-{request_id} | Post {i}: id={post.get('id')}, "
                              f"content_preview={post.get('content', '')[:50]}..., "
                              f"username={account.get('username', 'unknown')}, "
                              f"acct={account.get('acct', 'unknown')}")
            
            return jsonify(posts_to_return)
        
        # Forward request to Mastodon
        headers = {key: value for key, value in request.headers.items()
                  if key.lower() not in ['host', 'content-length']}
        params = request.args.to_dict()
        
        # Build the target URL
        target_url = urljoin(instance_url, "/api/v1/timelines/home")
        
        # Make the request
        proxied_response = requests.get(
            url=target_url,
            headers=headers,
            params=params,
            timeout=10
        )
        
        # Handle successful response
        if proxied_response.status_code == 200:
            try:
                timeline_data = proxied_response.json()
                
                # Add custom fields for testing
                for post in timeline_data:
                    post['is_real_mastodon_post'] = True
                
                # Load cold start posts to use as recommendations
                cold_start_posts = load_cold_start_posts()
                
                # If timeline is empty or has very few posts, use cold start posts as recommendations
                if len(timeline_data) < 3:
                    # Use real cold start posts as recommendations
                    recommended_posts = []
                    
                    # Process a few cold start posts
                    recommended_count = 0
                    for post in cold_start_posts[:5]:
                        # Process the post for Elk compatibility
                        
                        # 1. Make sure all required fields exist
                        if 'id' not in post:
                            post['id'] = f"rec-{recommended_count}-{hash(str(post)) % 10000}"
                            
                        # 2. Set the key field which is important for Vue rendering
                        post['key'] = f"status-{post['id']}"
                        
                        # 3. Set flags to indicate these are recommendations
                        post['is_recommendation'] = True
                        post['is_real_mastodon_post'] = False
                        post['is_cold_start'] = True
                        post['recommendation_reason'] = f"Recommended for {user_id}"
                        
                        # 4. Make sure the "filtered" field is an array, not a boolean
                        post['filtered'] = []
                        
                        # 5. Ensure account object is fully populated
                        if 'account' in post and isinstance(post['account'], dict):
                            account = post['account']
                            
                            # Required fields for Elk
                            if 'acct' not in account:
                                if '@' in account.get('username', ''):
                                    account['acct'] = account['username']
                                else:
                                    account['acct'] = f"{account.get('username', 'user')}@mastodon.social"
                                    
                            if 'url' not in account:
                                domain = "mastodon.social"
                                username = account.get('username', 'user')
                                account['url'] = f"https://{domain}/@{username}"
                        
                        recommended_posts.append(post)
                        recommended_count += 1
                    
                    # Add the recommended posts to the timeline
                    timeline_data.extend(recommended_posts)
                else:
                    # Add a couple of real cold start posts as recommendations in between regular posts
                    insertion_points = [len(timeline_data) // 3, 2 * len(timeline_data) // 3]
                    
                    # Use real cold start posts as recommendations
                    for i, insertion_point in enumerate(insertion_points[:2]):
                        if i < len(cold_start_posts):
                            # Get a post from cold start
                            post = cold_start_posts[i]
                            
                            # Process the post for Elk compatibility
                            # 1. Make sure all required fields exist
                            if 'id' not in post:
                                post['id'] = f"rec-inline-{i}-{hash(str(post)) % 10000}"
                                
                            # 2. Set the key field which is important for Vue rendering
                            post['key'] = f"status-{post['id']}"
                            
                            # 3. Set flags to indicate these are recommendations
                            post['is_recommendation'] = True
                            post['is_real_mastodon_post'] = False
                            post['recommendation_reason'] = f"Recommended for {user_id}"
                            
                            # 4. Make sure the "filtered" field is an array, not a boolean
                            post['filtered'] = []
                            
                            # 5. Ensure account object is fully populated
                            if 'account' in post and isinstance(post['account'], dict):
                                account = post['account']
                                
                                # Required fields for Elk
                                if 'acct' not in account:
                                    if '@' in account.get('username', ''):
                                        account['acct'] = account['username']
                                    else:
                                        account['acct'] = f"{account.get('username', 'user')}@mastodon.social"
                                        
                                if 'url' not in account:
                                    domain = "mastodon.social"
                                    username = account.get('username', 'user')
                                    account['url'] = f"https://{domain}/@{username}"
                            
                            # Insert this post at the calculated position
                            timeline_data.insert(insertion_point, post)
                
                # Validate all posts before returning them
                for i, post in enumerate(timeline_data):
                    # Ensure every post has the required fields
                    ensure_mastodon_post_format(post, user_id)
                    
                    # Verify critical fields for every post
                    if 'account' in post and isinstance(post['account'], dict):
                        account = post['account']
                        # Log the first few posts for troubleshooting
                        if i < 3:  # Only log details for the first 3 posts to avoid spamming logs
                            logger.info(f"TIMELINE-{request_id} | Post {i+1}: id={post.get('id', 'unknown')}, "
                                      f"username={account.get('username', 'missing')}, "
                                      f"acct={account.get('acct', 'missing')}, "
                                      f"url={account.get('url', 'missing')}")
                
                logger.info(f"TIMELINE-{request_id} | Successfully retrieved and enhanced timeline with {len(timeline_data)} posts")
                return jsonify(timeline_data)
            except Exception as e:
                logger.error(f"ERROR-{request_id} | Error processing timeline: {e}")
                # Just return the original response
                return Response(
                    proxied_response.content,
                    status=proxied_response.status_code,
                    content_type=proxied_response.headers.get('Content-Type')
                )
        else:
            logger.warning(
                f"ERROR-{request_id} | Mastodon returned error {proxied_response.status_code}"
            )
            return Response(
                proxied_response.content,
                status=proxied_response.status_code,
                content_type=proxied_response.headers.get('Content-Type')
            )
    except Exception as e:
        logger.error(f"ERROR-{request_id} | Failed to get timeline: {e}")
        # If we couldn't connect to Mastodon, return mock posts as a fallback
        fallback_posts = []
        for i in range(1, 6):
            status_id = f"fallback-{i}-{hash(request.remote_addr) % 10000}"
            post = create_complete_status(status_id)
            post['is_recommendation'] = True
            post['is_cold_start'] = True
            post['recommendation_reason'] = "Suggested while we couldn't reach your home timeline"
            fallback_posts.append(post)
        
        # Log the fallback
        logger.info(f"TIMELINE-{request_id} | Returning {len(fallback_posts)} mock posts as fallback")
        return jsonify(fallback_posts)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the Special Corgi Proxy Server for Elk integration')
    parser.add_argument('--host', type=str, help='Host to bind to (overrides environment variables)')
    parser.add_argument('--port', type=int, help='Port to bind to (overrides environment variables)')
    parser.add_argument('--no-https', action='store_true', help='Disable HTTPS')
    parser.add_argument('--force-http', action='store_true', help='Force HTTP even if HTTPS is configured but certs are missing')
    parser.add_argument('--cert', type=str, help='Path to SSL certificate (overrides environment variables)')
    parser.add_argument('--key', type=str, help='Path to SSL key (overrides environment variables)')
    args = parser.parse_args()
    
    # Port validation
    if args.port is not None and (args.port < 1024 or args.port > 65535):
        parser.error(f"Port must be between 1024 and 65535, got {args.port}")
    
    return args

# Add static routes to the app
@app.route('/api/v2/instance')
def instance_info():
    """
    Handle API v2 instance information requests.
    This endpoint is used by Elk to get instance information.
    """
    return jsonify({
        "domain": "localhost:5004",
        "title": "Corgi Recommender Service",
        "version": "4.1.1",
        "source_url": "https://github.com/mastodon/mastodon",
        "description": "Corgi Recommender Service - a Mastodon API-compatible service",
        "usage": {
            "users": {
                "active_month": 10
            }
        },
        "thumbnail": {
            "url": "https://mastodon.social/avatars/original/missing.png"
        },
        "languages": ["en"],
        "configuration": {
            "statuses": {
                "max_characters": 500,
                "max_media_attachments": 4
            },
            "media_attachments": {
                "supported_mime_types": [
                    "image/jpeg",
                    "image/png",
                    "image/gif",
                    "image/webp"
                ]
            }
        }
    })

@app.route('/nodeinfo/2.0')
def nodeinfo():
    """
    Handle nodeinfo requests.
    This endpoint is used by Elk to get server information.
    """
    return jsonify({
        "version": "2.0",
        "software": {
            "name": "corgi-recommender",
            "version": "1.0.0"
        },
        "protocols": ["activitypub"],
        "services": {
            "inbound": [],
            "outbound": []
        },
        "usage": {
            "users": {
                "total": 10,
                "activeMonth": 5,
                "activeHalfyear": 8
            },
            "localPosts": 100
        },
        "openRegistrations": False,
        "metadata": {
            "nodeName": "Corgi Recommender Service",
            "nodeDescription": "A recommendation-focused proxy for Mastodon"
        }
    })

@app.route('/test-corgi-response')
def test_corgi_response():
    """
    Return a sample enhanced timeline post for debugging Elk rendering.
    This endpoint provides a single post that contains all the required fields
    that Elk expects to avoid crashes in getFullHandle() and StatusCard.vue.
    """
    sample_post = {
        "id": "test-post-123456",
        "created_at": "2025-04-21T12:34:56.000Z",
        "content": "<p>This is a test post from the Corgi recommender service.</p>",
        "visibility": "public",
        "is_recommendation": True,
        "recommendation_reason": "Test post for debugging",
        "account": {
            "id": "user123",
            "username": "andrewn",
            "acct": "andrewn@mastodon.social",
            "display_name": "Andrew Nordstrom",
            "url": "https://mastodon.social/@andrewn",
            "avatar": "https://mastodon.social/avatars/original/missing.png",
            "avatar_static": "https://mastodon.social/avatars/original/missing.png",
            "header": "https://mastodon.social/headers/original/missing.png",
            "header_static": "https://mastodon.social/headers/original/missing.png",
            "note": "This is a test account bio",
            "followers_count": 42,
            "following_count": 100,
            "statuses_count": 255
        },
        "media_attachments": [],
        "mentions": [],
        "tags": [],
        "emojis": [],
        "favourites_count": 5,
        "reblogs_count": 2,
        "replies_count": 1,
        "language": "en"
    }
    
    # Add detailed validation info in the response for debugging
    logger.info("Serving test Corgi response for debugging")
    
    # Ensure the sample post has all required fields
    sample_post = ensure_mastodon_post_format(sample_post)
    
    # Return a single post array to simulate a timeline
    return jsonify([sample_post])

def add_static_routes():
    """Add routes for test client and documentation"""
    @app.route('/test-client')
    def serve_test_client():
        """Serve the test client HTML page"""
        with open(os.path.join(os.path.dirname(__file__), 'test_client.html'), 'r') as f:
            return f.read()
            
    @app.route('/elk-config')
    def serve_elk_config():
        """Serve the Elk configuration guide"""
        with open(os.path.join(os.path.dirname(__file__), 'elk_config.html'), 'r') as f:
            return f.read()
    
    @app.route('/elk-integration.js')
    def serve_elk_integration_js():
        """Serve the Elk integration JavaScript file"""
        with open(os.path.join(os.path.dirname(__file__), 'elk_integration.js'), 'r') as f:
            content = f.read()
        return Response(content, mimetype='application/javascript')
    
    @app.route('/elk-integration-guide')
    def serve_elk_integration_guide():
        """Serve the Elk integration guide page"""
        with open(os.path.join(os.path.dirname(__file__), 'elk_integration_guide.html'), 'r') as f:
            content = f.read()
        return content
            
    @app.route('/')
    def root():
        """Redirect root to Elk config page"""
        return f"""
        <html>
        <head>
            <meta http-equiv="refresh" content="0;url=/elk-config">
            <title>Redirecting to Elk Config</title>
        </head>
        <body>
            <h1>Corgi Proxy Server</h1>
            <p>Redirecting to <a href="/elk-config">Elk configuration guide</a>...</p>
        </body>
        </html>
        """

def validate_ssl_config(cert_path, key_path, force_http=False):
    """
    Validate SSL configuration and determine if HTTPS can be used.
    
    Args:
        cert_path: Path to SSL certificate
        key_path: Path to SSL key
        force_http: If True, force HTTP even if HTTPS is configured
        
    Returns:
        tuple: (use_https, ssl_context) where use_https is bool and ssl_context is the SSL context or None
    """
    # If force_http is set, don't use HTTPS
    if force_http:
        logger.info("Forcing HTTP as requested")
        return False, None
    
    # Check if both cert and key files exist
    if os.path.exists(cert_path) and os.path.exists(key_path):
        logger.info(f"Found SSL certificate at {cert_path} and key at {key_path}")
        return True, (cert_path, key_path)
    else:
        # Check if either cert or key is missing
        if not os.path.exists(cert_path):
            logger.warning(f"SSL certificate not found at {cert_path}")
        if not os.path.exists(key_path):
            logger.warning(f"SSL key not found at {key_path}")
        
        # Try adhoc certs if SSL files are missing
        try:
            import ssl
            from cryptography import x509
            logger.info("Using adhoc SSL certificates")
            return True, 'adhoc'
        except ImportError:
            logger.error("Missing required packages for HTTPS. Install with: pip install pyopenssl cryptography")
            logger.warning("Falling back to HTTP")
            return False, None

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()
    
    # Import config for environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Try to import from central config if available
    try:
        # Import configuration - this will load from the updated config.py with CORGI_ prefixed vars
        from config import HOST, PROXY_PORT as PORT, DEBUG, USE_HTTPS, SSL_CERT_PATH, SSL_KEY_PATH
        logger.info("Using configuration from config.py")
    except (ImportError, AttributeError):
        # Fall back to environment variables or defaults
        logger.info("Could not import from config.py, using environment variables and defaults")
        HOST = os.getenv("CORGI_HOST", os.getenv("HOST", "0.0.0.0"))
        PORT = int(os.getenv("CORGI_PROXY_PORT", os.getenv("PORT", "5003")))
        DEBUG = os.getenv("DEBUG", "True").lower() == "true"
        USE_HTTPS = os.getenv("CORGI_USE_HTTPS", "True").lower() == "true"
        SSL_CERT_PATH = os.path.join(os.path.dirname(__file__), 'certs', 'cert.pem')
        SSL_KEY_PATH = os.path.join(os.path.dirname(__file__), 'certs', 'key.pem')
    
    # Command line args override environment variables
    host = args.host or HOST
    port = args.port or PORT
    cert_path = args.cert or SSL_CERT_PATH
    key_path = args.key or SSL_KEY_PATH
    use_https = not args.no_https and USE_HTTPS
    
    # Validate port
    if port < 1024 or port > 65535:
        logger.error(f"Port {port} is outside the valid range (1024-65535)")
        sys.exit(1)
    
    # Make sure the database exists
    if not os.path.exists(DB_FILE):
        logger.error(f"Database file {DB_FILE} does not exist. Run simplified_setup.py first.")
        sys.exit(1)
    
    # Check if cold start posts file exists
    if not os.path.exists(COLD_START_POSTS_PATH):
        logger.warning(f"Cold start posts file {COLD_START_POSTS_PATH} does not exist. Cold start will not work.")
    else:
        # Try to load cold start posts to verify they're valid
        try:
            with open(COLD_START_POSTS_PATH, 'r') as f:
                posts = json.load(f)
                logger.info(f"Successfully loaded {len(posts)} cold start posts")
        except Exception as e:
            logger.error(f"Failed to load cold start posts: {e}")
    
    # Validate SSL configuration if HTTPS is enabled
    if use_https:
        use_https, ssl_context = validate_ssl_config(cert_path, key_path, args.force_http)
    else:
        ssl_context = None
    
    # Add the static routes to the app
    add_static_routes()
    
    # Generate URL for display in logs
    protocol = "https" if use_https else "http"
    server_url = f"{protocol}://{host if host != '0.0.0.0' else 'localhost'}:{port}"
    
    # Print instructions
    logger.info("==============================================")
    logger.info("Special Corgi Proxy Server for Elk Integration")
    logger.info("==============================================")
    logger.info("")
    logger.info("CORS is now enabled for:")
    logger.info("- http://localhost:3013")
    logger.info("- http://10.0.0.122:3002")
    logger.info("- http://127.0.0.1:3013")
    logger.info("")
    logger.info("To use with Elk:")
    logger.info(f"1. Configure Elk to use {server_url} as the server address")
    logger.info("2. Add your token: lJrzv-c0l5_pzmHNnw2EgTzuE0U-A-CIwjbCSTR5cp8")
    logger.info("")
    logger.info("Test endpoints:")
    logger.info(f"- {server_url}/api/v1/proxy/status")
    logger.info(f"- {server_url}/api/v1/proxy/instance")
    logger.info(f"- {server_url}/api/v1/timelines/home")
    logger.info(f"- {server_url}/api/v1/timelines/home?cold_start=true")
    logger.info(f"- {server_url}/test-corgi-response (Debug endpoint for Elk rendering)")
    logger.info("")
    
    # Print client URLs
    logger.info(f"Test client available at: {server_url}/test-client")
    logger.info(f"Elk configuration guide: {server_url}/elk-config")
    logger.info(f"Profile display integration guide: {server_url}/elk-integration-guide")
    
    # Start the server
    if use_https:
        logger.info(f"Starting server with HTTPS on {host}:{port}")
        app.run(host=host, port=port, debug=DEBUG, ssl_context=ssl_context)
    else:
        logger.info(f"Starting server without HTTPS on {host}:{port}")
        app.run(host=host, port=port, debug=DEBUG)