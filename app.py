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

    # SECURITY FIX: Require SECRET_KEY to be set explicitly in production
    secret_key = os.getenv("SECRET_KEY")
    if ENV == "production":
        if not secret_key:
            raise ValueError(
                "SECRET_KEY environment variable must be set in production. "
                "Generate one with: openssl rand -hex 32"
            )
        app.secret_key = secret_key
    else:
        # Development: use provided key or generate one with warning
        if secret_key:
            app.secret_key = secret_key
        else:
            app.secret_key = secrets.token_hex(16)
            logger.warning(
                "No SECRET_KEY set in development. Using random key. "
                "Sessions will not persist across restarts."
            )

    # Security configuration - limit JSON payload size to 1MB
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB limit

    # SECURITY FIX: Restrict CORS origins in production
    cors_origins = CORS_ALLOWED_ORIGINS
    if ENV == "production":
        # In production, never allow wildcard origins
        cors_origins = [origin for origin in cors_origins if origin != "*"]
        if not cors_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must be configured with specific domains in production")
    
    logger.info(f"Configuring CORS with allowed origins: {cors_origins}")
    CORS(
        app,
        resources={
            r"/*": {
                "origins": cors_origins,
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

    @app.route("/api/v1/instance", methods=["GET"])
    def get_instance_info_v1():
        # This endpoint is required for Elk compatibility
        return jsonify({
            "uri": request.host_url,
            "title": "Corgi Recommender Service",
            "description": "Personalized recommendations for the Fediverse",
            "email": "contact@corgi.example",
            "version": "1.0.0"
        })

    # IMPORTANT: The proxy blueprint must be registered LAST as it has a wildcard route
    app.register_blueprint(proxy_bp, url_prefix=API_PREFIX)

    # Manager Agent dashboard endpoints
    @app.route(f"{API_PREFIX}/manager/dashboard", methods=["GET"])
    def manager_dashboard():
        """Get Manager Agent dashboard data"""
        try:
            from agents.manager_agent import get_manager_agent
            manager = get_manager_agent()
            
            # Since Flask doesn't support async routes by default, we'll run the async function
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            dashboard_data = loop.run_until_complete(manager.get_dashboard_data())
            return jsonify(dashboard_data)
        except Exception as e:
            logger.error(f"Error getting manager dashboard data: {e}")
            return jsonify({
                "error": "Failed to get dashboard data",
                "details": str(e)
            }), 500

    @app.route(f"{API_PREFIX}/manager/status", methods=["GET"])
    def manager_status():
        """Get Manager Agent status"""
        try:
            from agents.manager_agent import get_manager_agent
            from datetime import datetime
            manager = get_manager_agent()
            
            return jsonify({
                "status": "running",
                "agent_count": len(manager.agent_statuses),
                "active_issues": len([i for i in manager.active_issues.values() if not i.resolved]),
                "monitoring_interval": manager.monitoring_interval,
                "last_check": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error getting manager status: {e}")
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500

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
    app.run(host=HOST, port=PORT, debug=DEBUG, use_reloader=False)
