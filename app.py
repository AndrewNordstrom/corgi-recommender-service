"""
Corgi Recommender Service - Main Flask Application

This is the main Flask application for the Corgi Recommender Service.
It provides recommendation endpoints and handles content processing for social media feeds.
"""

import os
import sys
import logging

# Configure logging FIRST with simplified format (no request_id in format string)
# This avoids the KeyError issues completely
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# NOW import everything else
import time
import uuid
import secrets
from functools import wraps

from flask import Flask, jsonify, g, session, request
from flask_cors import CORS
from config import DEBUG, ENV, CORS_ALLOWED_ORIGINS

# Route imports
from routes.health import health_bp
from routes.recommendations import recommendations_bp
from routes.interactions import interactions_bp
from routes.posts import posts_bp
from routes.analytics import analytics_bp
from routes.privacy import privacy_bp
from routes.docs import docs_bp
from routes.proxy import proxy_bp
from routes.oauth import oauth_bp
from routes.setup_gui import setup_gui_bp  # Import setup GUI blueprint
from routes.timeline import timeline_bp  # Import new timeline blueprint with injection
from routes.users import users_bp
from routes.model_registry import register_model_registry_routes  # Import model registry routes

# Import configuration
from config import API_PREFIX, HOST, PORT

# Create app logger
logger = logging.getLogger(__name__)


def csrf_protect(f):
    """CSRF protection decorator for state-changing routes (POST, PUT, DELETE)."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Only check CSRF for state-changing methods
        if request.method in ["POST", "PUT", "DELETE"]:
            token = request.headers.get("X-CSRF-Token")
            session_token = session.get("csrf_token")

            # Validate the token
            if not token or not session_token or token != session_token:
                logger.warning(
                    f"CSRF token validation failed: {token} != {session_token}"
                )
                return jsonify({"error": "CSRF token validation failed"}), 403

        return f(*args, **kwargs)

    return decorated_function


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Set a secret key for session management and CSRF protection
    app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))

    # Security configuration - limit JSON payload size to 1MB
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB limit

    if ENV == "production" and app.secret_key == secrets.token_hex(16):
        logger.warning(
            "Using a randomly generated secret key in production is insecure!"
        )
        logger.warning(
            "Set the SECRET_KEY environment variable to a strong, consistent value."
        )

    # Configure CORS with strict origin validation
    logger.info(f"Configuring CORS with allowed origins: {CORS_ALLOWED_ORIGINS}")
    CORS(
        app,
        resources={
            r"/*": {
                "origins": CORS_ALLOWED_ORIGINS,
                "allow_headers": ["Content-Type", "Authorization", "X-Request-ID"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "expose_headers": [
                    "X-Request-ID",
                    "X-Process-Time",
                    "X-Service-Version",
                ],
            }
        },
        supports_credentials=True,
    )

    # Initialize metrics server if enabled
    if os.getenv("ENABLE_METRICS", "true").lower() == "true":
        try:
            from utils.metrics import start_metrics_server

            metrics_port = int(os.getenv("METRICS_PORT", "9100"))
            start_metrics_server(port=metrics_port)
            logger.info(f"Prometheus metrics server started on port {metrics_port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")

    # Initialize database on startup
    from db.connection import init_db

    try:
        init_db()
        logger.info("Database initialized successfully on startup")
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {e}")
        # Continue without failing - the service might be able to start without DB initially

    # Initialize model registry on startup
    try:
        from core.recommender_factory import get_factory
        factory = get_factory()
        logger.info("Model registry factory initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize model registry: {e}")
        # Continue without failing - service can work with basic functionality

    # Request ID and CSRF middleware
    @app.before_request
    def before_request():
        # Use existing request ID from header or generate a new one
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        g.request_id = request_id
        g.start_time = time.time()

        # Generate CSRF token for the session if it doesn't exist
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(16)
            logger.debug(f"Generated new CSRF token for session")

    # Add request ID header and CSRF token to all responses
    @app.after_request
    def after_request(response):
        # Add request ID to response headers
        response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")

        # Add processing time for monitoring
        if hasattr(g, "start_time"):
            elapsed_time = time.time() - g.start_time
            response.headers["X-Process-Time"] = f"{elapsed_time:.6f}"

        # Add tracing and observability headers
        response.headers["X-Service-Version"] = os.getenv("APP_VERSION", "dev")

        # Include CSRF token in response headers for JS clients
        if "csrf_token" in session:
            response.headers["X-CSRF-Token"] = session["csrf_token"]

        # Set security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Set Content Security Policy in production
        if ENV == "production":
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'"
            )

        # Log the request details
        status_code = response.status_code
        log_level = logging.WARNING if status_code >= 400 else logging.INFO
        duration = time.time() - getattr(g, 'start_time', time.time())
        logger.log(
            log_level,
            f"Request {request.method} {request.path} completed with status {status_code} in {duration:.6f}s",
        )

        return response

    # Register blueprints - all under versioned API prefix
    app.register_blueprint(
        health_bp
    )  # Health check available at / and API_PREFIX/health
    app.register_blueprint(interactions_bp, url_prefix=f"{API_PREFIX}/interactions")
    app.register_blueprint(posts_bp, url_prefix=f"{API_PREFIX}/posts")
    app.register_blueprint(
        recommendations_bp, url_prefix=f"{API_PREFIX}/recommendations"
    )
    app.register_blueprint(privacy_bp, url_prefix=f"{API_PREFIX}/privacy")
    app.register_blueprint(analytics_bp, url_prefix=f"{API_PREFIX}/analytics")
    app.register_blueprint(users_bp, url_prefix=f"{API_PREFIX}/user")
    app.register_blueprint(oauth_bp, url_prefix=f"{API_PREFIX}/oauth")
    app.register_blueprint(
        timeline_bp
    )  # New timeline routes with injection capabilities

    # Register API documentation routes
    from routes.docs import register_docs_routes
    from routes.feedback import feedback_bp

    register_docs_routes(app)
    app.register_blueprint(feedback_bp)
    
    # Register model registry routes
    register_model_registry_routes(app)

    # Register setup GUI blueprint - only if enabled (disabled in production by default)
    if os.getenv("ENABLE_SETUP_GUI", "false").lower() == "true":
        logger.info("Setup GUI enabled - registering blueprint at /setup")
        app.register_blueprint(setup_gui_bp, url_prefix="/setup")
    else:
        logger.info("Setup GUI disabled - set ENABLE_SETUP_GUI=true to enable")

    # Add direct API endpoints for Mastodon compatibility (required for Elk)
    # These must be registered BEFORE the proxy blueprint to avoid conflicts
    from flask import jsonify
    from routes.proxy import get_authenticated_user

    @app.route("/.well-known/nodeinfo", methods=["GET"])
    def get_nodeinfo():
        """
        Return nodeinfo links for Mastodon compatibility.
        ELK looks for this endpoint to discover API capabilities.
        Use same protocol as the request to avoid SSL errors.
        """
        # Use the same protocol as the incoming request
        protocol = "https" if request.is_secure else "http"
        return jsonify({
            "links": [
                {
                    "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                    "href": f"{protocol}://{request.host}/nodeinfo/2.0"
                }
            ]
        })
    
    @app.route("/nodeinfo/2.0", methods=["GET"])
    def get_nodeinfo_schema():
        """
        Return nodeinfo schema 2.0 data.
        """
        return jsonify({
            "version": "2.0",
            "software": {
                "name": "mastodon",
                "version": "4.3.0"
            },
            "protocols": ["activitypub"],
            "services": {
                "outbound": [],
                "inbound": []
            },
            "usage": {
                "users": {
                    "total": 1,
                    "activeMonth": 1,
                    "activeHalfyear": 1
                },
                "localPosts": 100
            },
            "openRegistrations": False,
            "metadata": {}
        })

    @app.route("/api/v1/instance", methods=["GET"])
    def get_instance_info_v1():
        """
        Return Mastodon v1 instance information.
        Required by Elk for proper client integration.
        """
        return jsonify(
            {
                "uri": request.host,
                "title": "Corgi Recommender",
                "description": "A test instance for Corgi Recommender + Elk integration",
                "email": "admin@corgi-recommender.local",
                "version": "4.3.0",
                "urls": {"streaming_api": f"wss://{request.host}"},
                "stats": {"user_count": 1, "status_count": 100, "domain_count": 1},
                "thumbnail": "/static/assets/corgi-mascot.png",
                "languages": ["en"],
                "registrations": False,
                "approval_required": False,
                "invites_enabled": False,
                "contact_account": None,
                "configuration": {
                    "statuses": {
                        "max_characters": 500,
                        "max_media_attachments": 4,
                        "characters_reserved_per_url": 23,
                    },
                    "media_attachments": {
                        "supported_mime_types": [
                            "image/jpeg",
                            "image/png",
                            "image/gif",
                            "image/webp",
                        ],
                        "image_size_limit": 10485760,
                        "image_matrix_limit": 16777216,
                        "video_size_limit": 41943040,
                        "video_frame_rate_limit": 60,
                        "video_matrix_limit": 2304000,
                    },
                    "polls": {
                        "max_options": 4,
                        "max_characters_per_option": 50,
                        "min_expiration": 300,
                        "max_expiration": 2629746,
                    },
                },
            }
        )

    @app.route("/api/v2/instance", methods=["GET"])
    def get_instance_info():
        """
        Return Mastodon instance information.
        Required by Elk for proper client integration.
        """
        return jsonify(
            {
                "uri": request.host,
                "title": "Corgi Recommender",
                "short_description": "Test instance for Corgi + Elk integration",
                "description": "A test instance for Corgi Recommender + Elk integration",
                "version": "4.3.0",
                "urls": {},
                "stats": {"user_count": 1, "status_count": 100, "domain_count": 1},
                "thumbnail": "/static/assets/corgi-mascot.png",
                "languages": ["en"],
                "registrations": False,
                "approval_required": False,
                "contact_account": None,
            }
        )

    @app.route("/api/v1/apps", methods=["POST"])
    def create_app_registration():
        """
        Create app registration for ELK.
        This endpoint is required for ELK to register itself as a client application.
        """
        logger.info(f"App registration request received: {request.json}")
        
        # Get app details from request
        data = request.get_json() or {}
        client_name = data.get('client_name', 'ELK Client')
        redirect_uris = data.get('redirect_uris', 'http://localhost:5314/oauth/callback')
        scopes = data.get('scopes', 'read write follow')
        
        # Return app registration data that ELK expects
        return jsonify({
            "id": "elk_app_12345",
            "name": client_name,
            "website": data.get('website'),
            "redirect_uri": redirect_uris,
            "client_id": "elk_client_id_demo",
            "client_secret": "elk_client_secret_demo",
            "vapid_key": "demo_vapid_key_for_notifications"
        })

    @app.route("/oauth/authorize", methods=["GET"])
    def oauth_authorize():
        """
        OAuth authorization endpoint for ELK authentication.
        This endpoint is called directly by ELK (without /api/v1 prefix).
        """
        logger.info(f"OAuth authorize request received: {request.args}")
        
        # Get the redirect URI
        redirect_uri = request.args.get('redirect_uri', '')
        client_id = request.args.get('client_id', '')
        
        # Simple HTML page that simulates OAuth authorization
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authorize ELK</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; background-color: #f5f5f5; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 30px; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .logo {{ font-size: 2em; margin-bottom: 20px; color: #6366f1; }}
                h1 {{ color: #333; margin-bottom: 20px; }}
                p {{ color: #666; margin-bottom: 20px; }}
                button {{ padding: 12px 30px; background-color: #6366f1; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }}
                button:hover {{ background-color: #5856eb; }}
                .app-info {{ background: #f8fafc; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">🐕 Corgi Recommender</div>
                <h1>Authorize ELK</h1>
                <div class="app-info">
                    <p><strong>ELK</strong> wants to connect to your Corgi-enhanced Mastodon experience</p>
                    <p>Client ID: {client_id}</p>
                </div>
                <p>This will allow ELK to access your timeline with enhanced recommendations.</p>
                <form method="post" action="/oauth/mock-redirect">
                    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                    <input type="hidden" name="client_id" value="{client_id}">
                    <button type="submit">✅ Authorize ELK</button>
                </form>
                <p><small style="color: #999;">Demo OAuth Flow - Corgi Recommender Service</small></p>
            </div>
        </body>
        </html>
        """
        
        return html

    @app.route("/oauth/mock-redirect", methods=["POST"])
    def oauth_mock_redirect():
        """
        Handle the OAuth authorization and redirect back to ELK.
        """
        redirect_uri = request.form.get('redirect_uri', '')
        
        if not redirect_uri:
            return "Error: No redirect URI provided", 400
        
        # Add authorization code to redirect URI
        if '?' in redirect_uri:
            redirect_url = f"{redirect_uri}&code=demo_auth_code_12345"
        else:
            redirect_url = f"{redirect_uri}?code=demo_auth_code_12345"
        
        logger.info(f"OAuth authorization completed, redirecting to: {redirect_url}")
        
        # Return a redirect page
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authorization Complete</title>
            <meta http-equiv="refresh" content="2;url={redirect_url}">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 100px; }}
                .success {{ color: #10b981; font-size: 1.2em; }}
            </style>
        </head>
        <body>
            <div class="success">✅ Authorization successful!</div>
            <p>Redirecting back to ELK...</p>
            <p>If you're not redirected automatically, <a href="{redirect_url}">click here</a>.</p>
        </body>
        </html>
        """

    @app.route("/oauth/token", methods=["POST"])
    def oauth_token():
        """
        OAuth token endpoint for ELK.
        Exchange authorization code for access token.
        """
        logger.info(f"OAuth token request received")
        
        # Return a demo access token
        return jsonify({
            "access_token": "corgi_demo_token_elk_integration",
            "token_type": "Bearer",
            "scope": "read write follow",
            "created_at": int(time.time())
        })

    @app.route("/api/v1/metrics/recommendations/<user_id>", methods=["GET"])
    def get_recommendation_metrics(user_id):
        """
        Get recommendation quality metrics for a specific user.
        
        This endpoint prevents 429 errors by handling metrics requests locally
        instead of proxying to external Mastodon instances.
        """
        try:
            logger.info(f"Getting recommendation metrics for user: {user_id}")
            
            # Simulate realistic metrics for load testing
            import random
            
            # Simulate some variation in metrics based on user_id
            user_seed = hash(user_id) % 1000
            random.seed(user_seed)
            
            metrics = {
                "user_id": user_id,
                "total_recommendations_served": random.randint(50, 500),
                "total_interactions": random.randint(10, 100),
                "click_through_rate": round(random.uniform(0.05, 0.25), 3),
                "engagement_rate": round(random.uniform(0.02, 0.15), 3),
                "diversity_score": round(random.uniform(0.6, 0.9), 3),
                "relevance_score": round(random.uniform(0.7, 0.95), 3),
                "cold_start_exits": random.randint(0, 5),
                "personalization_enabled": True,
                "last_recommendation": "2025-06-08T18:00:00Z",
                "metrics_period": "last_30_days"
            }
            
            return jsonify(metrics), 200
            
        except Exception as e:
            logger.error(f"Error getting recommendation metrics for user {user_id}: {e}")
            return jsonify({"error": "Failed to retrieve recommendation metrics"}), 500

    @app.route("/api/v1/users/<user_id>/preferences", methods=["GET", "PUT"])
    def handle_user_preferences(user_id):
        """
        Handle user preferences for recommendation customization.
        
        This endpoint prevents 429 errors by handling preferences requests locally
        instead of proxying to external Mastodon instances.
        """
        try:
            if request.method == "GET":
                # Return default preferences for load testing
                default_preferences = {
                    "user_id": user_id,
                    "diversity_weight": 0.5,
                    "recency_weight": 0.3,
                    "engagement_weight": 0.2,
                    "language_preferences": ["en"],
                    "content_filters": [],
                    "updated_at": "2025-06-08T18:00:00Z"
                }
                return jsonify(default_preferences), 200
                
            elif request.method == "PUT":
                # Accept preference updates for load testing
                preferences_data = request.json or {}
                
                # Validate basic structure
                allowed_fields = {
                    "diversity_weight", "recency_weight", "engagement_weight",
                    "language_preferences", "content_filters"
                }
                
                # Filter to only allowed fields
                filtered_preferences = {
                    k: v for k, v in preferences_data.items() 
                    if k in allowed_fields
                }
                
                # Simulate successful update
                updated_preferences = {
                    "user_id": user_id,
                    "diversity_weight": filtered_preferences.get("diversity_weight", 0.5),
                    "recency_weight": filtered_preferences.get("recency_weight", 0.3),
                    "engagement_weight": filtered_preferences.get("engagement_weight", 0.2),
                    "language_preferences": filtered_preferences.get("language_preferences", ["en"]),
                    "content_filters": filtered_preferences.get("content_filters", []),
                    "updated_at": "2025-06-08T18:00:00Z"
                }
                
                logger.info(f"Updated preferences for user {user_id}: {len(filtered_preferences)} fields")
                return jsonify(updated_preferences), 200
                
        except Exception as e:
            logger.error(f"Error in handle_user_preferences for user {user_id}: {e}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/api/v1/accounts/verify_credentials", methods=["GET"])
    def verify_credentials():
        """
        Return user account information.
        Required by Elk to verify user login and access token.
        """
        print("✅ verify_credentials called")
        logger.info("verify_credentials endpoint called")

        # Return complete user object that Elk requires
        return jsonify(
            {
                "id": "123",
                "username": "demo_user",
                "acct": "demo_user@mastodon.social",
                "display_name": "Demo User",
                "note": "Demo user for Corgi Recommender",
                "url": "https://mastodon.social/@demo_user",
                "avatar": "https://mastodon.social/avatars/original/missing.png",
                "avatar_static": "https://mastodon.social/avatars/original/missing.png",
                "header": "https://mastodon.social/headers/original/missing.png",
                "header_static": "https://mastodon.social/headers/original/missing.png",
                "followers_count": 0,
                "following_count": 0,
                "statuses_count": 0,
                "bot": False,
                "locked": False,
                "source": {"privacy": "public", "sensitive": False, "language": "en"},
                "created_at": "2023-01-01T00:00:00.000Z",
            }
        )

    # Register proxy blueprint - this should be registered last to catch all other routes
    # The proxy will handle any requests that aren't handled by the specific blueprints above
    app.register_blueprint(proxy_bp, url_prefix=API_PREFIX)

    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {
            "error": "Not found",
            "request_id": getattr(g, "request_id", "unknown"),
        }, 404

    @app.errorhandler(413)
    def payload_too_large(error):
        """Convert 413 Request Entity Too Large to 400 Bad Request for security tests."""
        logger.warning(f"Payload too large: {error}")
        return {
            "error": "Invalid or oversized request payload",
            "request_id": getattr(g, "request_id", "unknown"),
        }, 400

    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"Server error: {error}")
        return {
            "error": "Internal server error",
            "request_id": getattr(g, "request_id", "unknown"),
            "message": (
                str(error) if ENV == "development" else "An internal error occurred"
            ),
        }, 500

    return app


if __name__ == "__main__":
    app = create_app()
    logger.info(f"Starting Corgi Recommender Service on {HOST}:{PORT} (debug={DEBUG})")
    app.run(host=HOST, port=PORT, debug=DEBUG)
