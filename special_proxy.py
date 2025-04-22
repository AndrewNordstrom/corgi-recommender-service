#!/usr/bin/env python3
"""
Special proxy server for testing Elk integration with Corgi.

This script creates a Flask application that serves as a dedicated proxy server
for integrating Elk with Corgi, handling Mastodon API requests and properly
configuring database connections.
"""

import os
import logging
import sys
import sqlite3
import argparse
from flask import Flask, request, g, jsonify, Response
import requests
import json
from urllib.parse import urljoin
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('corgi_proxy')

# Define database file path
DB_FILE = os.path.join(os.path.dirname(__file__), 'corgi_demo.db')

# Create Flask app
app = Flask(__name__)

# Configure CORS
from flask_cors import CORS
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

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
        "access_token": "_Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc",
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
            <p><small>Token: _Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc</small></p>
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
    
    # Add code parameter to redirect URI
    if '?' in redirect_uri:
        redirect_url = f"{redirect_uri}&code=mock_auth_code"
    else:
        redirect_url = f"{redirect_uri}?code=mock_auth_code"
    
    logger.info(f"Redirecting to: {redirect_url}")
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Redirecting...</title>
        <meta http-equiv="refresh" content="0;url={redirect_url}">
    </head>
    <body>
        <p>Redirecting to Elk... If you are not redirected, <a href="{redirect_url}">click here</a>.</p>
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
        
    return jsonify({
        "id": user_id,
        "username": "demo_user",
        "acct": "demo_user@mastodon.social",
        "display_name": "Demo User",
        "locked": False,
        "bot": False,
        "created_at": "2023-01-01T00:00:00.000Z",
        "note": "Demo user for Corgi Recommender",
        "url": "https://mastodon.social/@demo_user",
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

@app.route('/api/v1/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def mastodon_api_proxy(path):
    """
    Handle all Mastodon API requests.
    This route matches both /api/v1/timelines/home and /api/v1/proxy/xyz for compatibility.
    """
    # For proxy-specific endpoints, redirect to the appropriate handler
    if path.startswith('proxy/status'):
        return proxy_status()
    elif path.startswith('proxy/instance'):
        return detect_instance()
    elif path == 'timelines/home':
        return get_home_timeline()
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
        params = request.args.to_dict()
        data = request.get_data()
        
        # Make the request to the target Mastodon instance
        proxied_response = requests.request(
            method=method,
            url=target_url,
            headers=headers,
            params=params,
            data=data,
            timeout=10
        )
        
        # Extract the response for potential modification
        response_headers = {key: value for key, value in proxied_response.headers.items()
                           if key.lower() not in ['content-encoding', 'transfer-encoding', 'content-length']}
        response_content = proxied_response.content
        status_code = proxied_response.status_code
        
        # Prepare final response
        response = Response(
            response_content,
            status=status_code,
            headers=response_headers
        )
        
        # Log completion
        logger.info(
            f"RESP-{request_id} | Request completed | "
            f"Status: {status_code} | "
            f"Response size: {len(response_content)} bytes"
        )
        
        return response
    except requests.RequestException as e:
        logger.error(
            f"ERROR-{request_id} | Proxy failed | "
            f"Target: {instance_url} | "
            f"Error: {str(e)}"
        )
        
        return jsonify({
            "error": "Failed to proxy request to Mastodon instance",
            "instance": instance_url,
            "details": str(e)
        }), 502

@app.route('/api/v1/timelines/home', methods=['GET'])
def get_home_timeline():
    """
    Get a user's home timeline with recommendations
    """
    request_id = hash(f"{request.remote_addr}_{request.path}") % 10000000
    
    # Get authentication
    user_id = get_authenticated_user(request)
    if not user_id:
        logger.warning(f"REQ-{request_id} | No user authenticated for timeline request")
        return jsonify([])
    
    # Get instance
    instance_url = get_user_instance(request)
    
    # Log the timeline request
    logger.info(
        f"TIMELINE-{request_id} | Requesting home timeline | "
        f"User: {user_id} | "
        f"Instance: {instance_url}"
    )
    
    try:
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
                
                # Create a dummy recommendation for testing
                if timeline_data:
                    recommendation = {
                        "id": f"corgi_rec_{hash(user_id) % 10000}",
                        "created_at": timeline_data[0].get('created_at', ''),
                        "content": "This is a test recommendation from Corgi. If you see this, the proxy is working!",
                        "account": {
                            "id": "corgi",
                            "username": "corgi",
                            "display_name": "Corgi Recommender",
                            "url": "https://corgi-recommender.example.com"
                        },
                        "is_recommendation": True,
                        "is_real_mastodon_post": False,
                        "recommendation_reason": "Testing Corgi integration with Elk"
                    }
                    
                    # Insert recommendation as second post
                    if len(timeline_data) > 2:
                        timeline_data.insert(2, recommendation)
                    else:
                        timeline_data.append(recommendation)
                
                logger.info(f"TIMELINE-{request_id} | Successfully retrieved and enhanced timeline")
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
        return jsonify({
            "error": "Failed to retrieve timeline",
            "details": str(e)
        }), 500

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
    logger.info("To use with Elk:")
    logger.info(f"1. Configure Elk to use {server_url} as the server address")
    logger.info("2. Add your token: _Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc")
    logger.info("")
    logger.info("Test endpoints:")
    logger.info(f"- {server_url}/api/v1/proxy/status")
    logger.info(f"- {server_url}/api/v1/proxy/instance")
    logger.info(f"- {server_url}/api/v1/timelines/home")
    logger.info("")
    
    # Print client URLs
    logger.info(f"Test client available at: {server_url}/test-client")
    logger.info(f"Elk configuration guide: {server_url}/elk-config")
    
    # Start the server
    if use_https:
        logger.info(f"Starting server with HTTPS on {host}:{port}")
        app.run(host=host, port=port, debug=DEBUG, ssl_context=ssl_context)
    else:
        logger.info(f"Starting server without HTTPS on {host}:{port}")
        app.run(host=host, port=port, debug=DEBUG)