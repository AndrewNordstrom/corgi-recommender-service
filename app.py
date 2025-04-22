"""
Corgi Recommender Service

A microservice for handling post recommendations and user interaction tracking
for the Elk Mastodon client.

This service provides:
- User interaction logging (favorites, bookmarks, etc.)
- Post metadata storage
- Personalized post recommendations

The API is versioned with a configurable prefix (default: /api/v1) for all routes.
"""

import logging
import time
import os
import uuid
import sys
from flask import Flask, request, g, Response
from flask_cors import CORS

# Import configuration
from config import API_PREFIX, HOST, PORT, DEBUG, CORS_ALLOWED_ORIGINS, ENV

# Import route modules
from routes.health import health_bp
from routes.interactions import interactions_bp
from routes.posts import posts_bp
from routes.recommendations import recommendations_bp
from routes.privacy import privacy_bp
from routes.analytics import analytics_bp
from routes.proxy import proxy_bp
from routes.oauth import oauth_bp
from routes.setup_gui import setup_gui_bp  # Import setup GUI blueprint
from routes.timeline import timeline_bp   # Import new timeline blueprint with injection

# Configure logging based on environment
log_format = '%(asctime)s [%(levelname)s] [%(name)s] [request_id=%(request_id)s] %(message)s'

# Add request_id to log records
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(g, 'request_id', 'no_request_id')
        return True

# Set up logging
root_logger = logging.getLogger()

# Clear existing handlers to avoid duplicates
if len(root_logger.handlers) == 0:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

    # Add request ID filter to root logger only if not in test mode
    if os.getenv("USE_IN_MEMORY_DB", "false").lower() != "true":
        request_id_filter = RequestIdFilter()
        root_logger.addFilter(request_id_filter)

# Create app logger
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure CORS
    logger.info(f"Configuring CORS with allowed origins: {CORS_ALLOWED_ORIGINS}")
    CORS(app, resources={r"/*": {"origins": CORS_ALLOWED_ORIGINS}}, supports_credentials=True)
    
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
    
    # Request ID middleware
    @app.before_request
    def before_request():
        # Use existing request ID from header or generate a new one
        request_id = request.headers.get('X-Request-ID')
        if not request_id:
            request_id = str(uuid.uuid4())
        g.request_id = request_id
        g.start_time = time.time()
    
    # Add request ID header to all responses
    @app.after_request
    def after_request(response):
        # Add request ID to response headers
        response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
        
        # Add processing time for monitoring
        if hasattr(g, 'start_time'):
            elapsed_time = time.time() - g.start_time
            response.headers['X-Process-Time'] = f"{elapsed_time:.6f}"
        
        # Add tracing and observability headers
        response.headers['X-Service-Version'] = os.getenv('APP_VERSION', 'dev')
        
        # Log the request details
        status_code = response.status_code
        log_level = logging.WARNING if status_code >= 400 else logging.INFO
        logger.log(
            log_level,
            f"Request {request.method} {request.path} completed with status {status_code} in {getattr(g, 'start_time', 0):.6f}s"
        )
        
        return response
    
    # Register blueprints - all under versioned API prefix
    app.register_blueprint(health_bp)  # Health check available at / and API_PREFIX/health
    app.register_blueprint(interactions_bp, url_prefix=f"{API_PREFIX}/interactions")
    app.register_blueprint(posts_bp, url_prefix=f"{API_PREFIX}/posts")
    app.register_blueprint(recommendations_bp, url_prefix=f"{API_PREFIX}/recommendations")
    app.register_blueprint(privacy_bp, url_prefix=f"{API_PREFIX}/privacy")
    app.register_blueprint(analytics_bp, url_prefix=f"{API_PREFIX}/analytics")
    app.register_blueprint(oauth_bp, url_prefix=f"{API_PREFIX}/oauth")
    app.register_blueprint(timeline_bp)  # New timeline routes with injection capabilities
    
    # Register API documentation routes
    from routes.docs import register_docs_routes
    register_docs_routes(app)
    
    # Register setup GUI blueprint - only if enabled (disabled in production by default)
    if os.getenv("ENABLE_SETUP_GUI", "false").lower() == "true":
        logger.info("Setup GUI enabled - registering blueprint at /setup")
        app.register_blueprint(setup_gui_bp, url_prefix='/setup')
    else:
        logger.info("Setup GUI disabled - set ENABLE_SETUP_GUI=true to enable")
    
    # Register proxy blueprint - this should be registered last to catch all other routes
    # The proxy will handle any requests that aren't handled by the specific blueprints above
    app.register_blueprint(proxy_bp, url_prefix=API_PREFIX)
    
    # Add direct API endpoints for Mastodon compatibility (required for Elk)
    from flask import jsonify
    from routes.proxy import get_authenticated_user
    
    @app.route('/api/v2/instance', methods=['GET'])
    def get_instance_info():
        """
        Return Mastodon instance information.
        Required by Elk for proper client integration.
        """
        return jsonify({
            "uri": request.host,
            "title": "Corgi Recommender",
            "short_description": "Test instance for Corgi + Elk integration",
            "description": "A test instance for Corgi Recommender + Elk integration",
            "version": "4.3.0",
            "urls": {},
            "stats": {
                "user_count": 1,
                "status_count": 100,
                "domain_count": 1
            },
            "thumbnail": "/static/assets/corgi-mascot.png",
            "languages": ["en"],
            "registrations": False,
            "approval_required": False,
            "contact_account": None
        })
    
    @app.route('/api/v1/accounts/verify_credentials', methods=['GET'])
    def verify_credentials():
        """
        Return user account information.
        Required by Elk to verify user login and access token.
        """
        print("✅ verify_credentials called")
        logger.info("verify_credentials endpoint called")
        
        # Return complete user object that Elk requires
        return jsonify({
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
            "source": {
                "privacy": "public",
                "sensitive": False,
                "language": "en"
            },
            "created_at": "2023-01-01T00:00:00.000Z"
        })
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found", "request_id": getattr(g, 'request_id', 'unknown')}, 404
        
    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"Server error: {error}")
        return {
            "error": "Internal server error", 
            "request_id": getattr(g, 'request_id', 'unknown'),
            "message": str(error) if ENV == 'development' else "An internal error occurred"
        }, 500
    
    return app

if __name__ == "__main__":
    app = create_app()
    logger.info(f"Starting Corgi Recommender Service on {HOST}:{PORT} (debug={DEBUG})")
    app.run(host=HOST, port=PORT, debug=DEBUG)