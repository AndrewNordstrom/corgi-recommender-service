#!/usr/bin/env python3
"""
Run the Corgi Recommender Service with SQLite database support for demo
"""

import os
import logging
import sys
import sqlite3
import argparse
from flask import Flask, request, g
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('corgi')

# Define database file path
DB_FILE = os.path.join(os.path.dirname(__file__), 'corgi_demo.db')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the Corgi Proxy Server with SQLite support')
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

def create_app():
    # Import the app module
    sys.path.append(os.path.dirname(__file__))
    from app import create_app as original_create_app
    
    # Create Flask app
    app = original_create_app()
    
    # Override the get_db_connection function for proxy routes
    @app.before_request
    def setup_sqlite_connection():
        """Setup SQLite connection for proxy routes"""
        # Only handle requests to proxy routes
        if request.path.startswith('/api/v1/proxy'):
            # Store the SQLite connection in g
            g.sqlite_conn = sqlite3.connect(DB_FILE)
            g.sqlite_conn.row_factory = sqlite3.Row
            
            # Override get_user_by_token function for proxy
            from routes.proxy import get_user_by_token as original_get_user_by_token
            
            def sqlite_get_user_by_token(token):
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
            
            # Replace the original function
            import routes.proxy
            routes.proxy.get_user_by_token = sqlite_get_user_by_token
    
    @app.teardown_request
    def close_sqlite_connection(exception=None):
        """Close SQLite connection after request"""
        sqlite_conn = getattr(g, 'sqlite_conn', None)
        if sqlite_conn is not None:
            sqlite_conn.close()
    
    return app

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

def main():
    # Parse command line arguments
    args = parse_args()
    
    # Import configuration - this will load from the updated config.py with CORGI_ prefixed vars
    try:
        from config import HOST, PORT, DEBUG, USE_HTTPS, SSL_CERT_PATH, SSL_KEY_PATH
        logger.info("Using configuration from config.py")
    except (ImportError, AttributeError):
        # Fall back to environment variables or defaults
        logger.info("Could not import from config.py, using environment variables and defaults")
        HOST = os.getenv("CORGI_HOST", os.getenv("HOST", "0.0.0.0"))
        PORT = int(os.getenv("CORGI_PORT", os.getenv("PORT", "5002")))
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
        
    # Validate SSL configuration if HTTPS is enabled
    if use_https:
        use_https, ssl_context = validate_ssl_config(cert_path, key_path, args.force_http)
    else:
        ssl_context = None
    
    # Create the app with SQLite support
    app = create_app()
    
    # Generate URL for display in logs
    protocol = "https" if use_https else "http"
    server_url = f"{protocol}://{host if host != '0.0.0.0' else 'localhost'}:{port}"
    
    # Log startup information
    logger.info(f"Starting Corgi Proxy Server with SQLite database support on {host}:{port}")
    logger.info(f"Server URL: {server_url}")
    logger.info(f"HTTPS enabled: {use_https}")
    
    # Run the server
    if use_https:
        app.run(host=host, port=port, debug=DEBUG, ssl_context=ssl_context)
    else:
        app.run(host=host, port=port, debug=DEBUG)

if __name__ == "__main__":
    main()