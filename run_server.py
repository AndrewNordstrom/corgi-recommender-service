#!/usr/bin/env python3
"""
Run script for the Corgi Recommender Service with in-memory database support.

This is a simplified entry point that runs the Flask application
with an in-memory SQLite database for testing and development.
"""

import os
import sys
import logging
import argparse
from app import create_app
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Set default environment variables if not already set
default_settings = {
    'ENABLE_SETUP_GUI': 'true',
    'API_PREFIX': '/api/v1',
    'USE_IN_MEMORY_DB': 'true'
}

for key, value in default_settings.items():
    if key not in os.environ:
        os.environ[key] = value

# Configure logging - use a format without request_id for the startup script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    stream=sys.stdout
)

# Override the root logger's formatter to avoid request_id errors
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))

logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the Corgi Recommender Service')
    parser.add_argument('--host', type=str, help='Host to bind to (overrides environment variables)')
    parser.add_argument('--port', type=int, default=5002, help='Port to bind to (default: 5002)')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL/HTTPS')
    parser.add_argument('--debug-cors', action='store_true', help='Enable CORS for local development')
    
    # Keep existing args for backward compatibility
    parser.add_argument('--no-https', action='store_true', help='Disable HTTPS (legacy, use --no-ssl instead)')
    parser.add_argument('--force-http', action='store_true', help='Force HTTP even if HTTPS is configured but certs are missing')
    parser.add_argument('--cert', type=str, help='Path to SSL certificate (overrides default)')
    parser.add_argument('--key', type=str, help='Path to SSL key (overrides default)')
    
    args = parser.parse_args()
    
    # Port validation
    if args.port < 1024 or args.port > 65535:
        parser.error(f"Port must be between 1024 and 65535, got {args.port}")
    
    return args

# Create the Flask app
app = create_app()

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

def configure_cors(app, debug_cors=False):
    """
    Configure CORS settings for the Flask app.
    
    Args:
        app: Flask application instance
        debug_cors: If True, also allow localhost origins for development
    
    Returns:
        List of allowed origins that were configured
    """
    from flask_cors import CORS
    
    # Always allow Elk zone
    allowed_origins = ["https://elk.zone"]
    
    # Add local development origins if debug_cors is enabled
    if debug_cors:
        allowed_origins.extend(["http://localhost:3000", "http://localhost:5314"])
    
    # Configure CORS with the allowed origins
    CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)
    
    return allowed_origins

if __name__ == '__main__':
    # Parse command line arguments
    args = parse_args()
    
    # Import configuration - this will load from the updated config.py with CORGI_ prefixed vars
    from config import HOST, PORT, DEBUG
    
    # Command line args override environment variables
    host = args.host or HOST
    port = args.port  # Already has default of 5002
    
    # Default SSL certificate paths - use relative paths as requested
    cert_path = args.cert or "./certs/cert.pem"
    key_path = args.key or "./certs/key.pem"
    
    # Handle SSL configuration - use new --no-ssl flag, with fallback to --no-https
    use_ssl = not (args.no_ssl or args.no_https)
    
    # Configure SSL context
    ssl_context = None
    if use_ssl:
        if os.path.exists(cert_path) and os.path.exists(key_path):
            ssl_context = (cert_path, key_path)
            logger.info(f"Using SSL certificates from {cert_path} and {key_path}")
        else:
            if not os.path.exists(cert_path):
                logger.warning(f"SSL certificate not found at {cert_path}")
            if not os.path.exists(key_path):
                logger.warning(f"SSL key not found at {key_path}")
                
            if args.force_http:
                logger.warning("Force HTTP requested, disabling SSL")
                use_ssl = False
            else:
                try:
                    # Try to use adhoc certificates
                    ssl_context = 'adhoc'
                    logger.info("Using adhoc SSL certificates")
                except ImportError:
                    logger.error("Missing packages for SSL. Install with: pip install pyopenssl")
                    logger.warning("Falling back to HTTP")
                    use_ssl = False
    
    # Configure CORS with debug mode if specified
    allowed_origins = configure_cors(app, args.debug_cors)
    
    # Log startup information
    protocol = "https" if use_ssl else "http"
    server_url = f"{protocol}://{host if host != '0.0.0.0' else 'localhost'}:{port}"
    
    logger.info(f"Starting Corgi Recommender Service on {host}:{port}")
    logger.info(f"Server URL: {server_url}")
    logger.info(f"SSL/HTTPS enabled: {use_ssl}")
    logger.info(f"CORS allowed origins: {', '.join(allowed_origins)}")
    logger.info(f"API Prefix: {os.environ.get('API_PREFIX', '/api/v1')}")
    logger.info(f"Using in-memory database: {os.environ.get('USE_IN_MEMORY_DB', 'false')}")
    logger.info(f"Setup GUI enabled: {os.environ.get('ENABLE_SETUP_GUI', 'false')}")
    
    # Run the Flask development server
    app.run(host=host, port=port, debug=DEBUG, ssl_context=ssl_context)
