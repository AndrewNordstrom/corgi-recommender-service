"""
Configuration module for the Corgi Recommender Service.

This module handles loading environment variables and defining constants
used throughout the application.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_VERSION = os.getenv("API_VERSION", "v1")
# Allow explicit overriding of the full API_PREFIX or construct it from API_VERSION
API_PREFIX = os.getenv("API_PREFIX", f"/api/{API_VERSION}")

# Helper function to validate and parse port number
def parse_port(port_str, default=5002):
    """
    Validate and parse port number from string.
    
    Args:
        port_str: String representation of port number
        default: Default port number if parsing fails
        
    Returns:
        int: Valid port number between 1024 and 65535
    """
    try:
        port = int(port_str)
        # Check if port is in valid range
        if port < 1024 or port > 65535:
            print(f"WARNING: Port {port} outside valid range (1024-65535). Using default {default}.")
            return default
        return port
    except (ValueError, TypeError):
        if port_str:  # Only log if the string isn't empty
            print(f"WARNING: Invalid port '{port_str}'. Using default {default}.")
        return default

# Allow dedicated CORGI_HOST/CORGI_PORT environment variables with fallbacks to HOST/PORT
HOST = os.getenv("CORGI_HOST", os.getenv("HOST", "0.0.0.0"))
PORT = parse_port(os.getenv("CORGI_PORT", os.getenv("PORT", "5002")))
PROXY_PORT = parse_port(os.getenv("CORGI_PROXY_PORT", os.getenv("PROXY_PORT", "5003")))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENV = os.getenv("FLASK_ENV", "development")

# SSL configuration for HTTPS
USE_HTTPS = os.getenv("CORGI_USE_HTTPS", "True").lower() == "true"
SSL_CERT_PATH = os.getenv("CORGI_SSL_CERT_PATH", os.path.join(os.path.dirname(__file__), 'certs', 'cert.pem'))
SSL_KEY_PATH = os.getenv("CORGI_SSL_KEY_PATH", os.path.join(os.path.dirname(__file__), 'certs', 'key.pem'))

# CORS Configuration
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", 
    "http://localhost:3000,http://localhost:5314"
).split(',')

# PostgreSQL Database Settings
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
    'dbname': os.getenv('POSTGRES_DB', 'corgi_recommender'),
}

# User Privacy Settings
USER_HASH_SALT = os.getenv("USER_HASH_SALT", "")
if not USER_HASH_SALT:
    if ENV == "production":
        raise ValueError("USER_HASH_SALT environment variable must be set in production")
    else:
        print("WARNING: USER_HASH_SALT not set. Using an empty salt is not secure for production!")

# Recommendation Algorithm Settings
ALGORITHM_CONFIG = {
    "weights": {
        "author_preference": float(os.getenv("RANKING_WEIGHT_AUTHOR", "0.4")),
        "content_engagement": float(os.getenv("RANKING_WEIGHT_ENGAGEMENT", "0.3")),
        "recency": float(os.getenv("RANKING_WEIGHT_RECENCY", "0.3")),
    },
    "time_decay_days": int(os.getenv("RANKING_TIME_DECAY_DAYS", "7")),
    "min_interactions": int(os.getenv("RANKING_MIN_INTERACTIONS", "0")),
    "max_candidates": int(os.getenv("RANKING_MAX_CANDIDATES", "100")),
    "include_synthetic": os.getenv("RANKING_INCLUDE_SYNTHETIC", "False").lower() == "true"
}

# Health Check Settings
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))

# Proxy Settings
DEFAULT_MASTODON_INSTANCE = os.getenv("DEFAULT_MASTODON_INSTANCE", "https://mastodon.social")
RECOMMENDATION_BLEND_RATIO = float(os.getenv("RECOMMENDATION_BLEND_RATIO", "0.3"))
PROXY_TIMEOUT = int(os.getenv("PROXY_TIMEOUT", "10"))

# Cold Start Settings
COLD_START_ENABLED = os.getenv("COLD_START_ENABLED", "True").lower() == "true"
COLD_START_POSTS_PATH = os.getenv("COLD_START_POSTS_PATH", 
                                os.path.join(os.path.dirname(__file__), 'data', 'cold_start_posts.json'))
COLD_START_POST_LIMIT = int(os.getenv("COLD_START_POST_LIMIT", "30"))
ALLOW_COLD_START_FOR_ANONYMOUS = os.getenv("ALLOW_COLD_START_FOR_ANONYMOUS", "True").lower() == "true"