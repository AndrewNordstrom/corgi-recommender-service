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
            print(
                f"WARNING: Port {port} outside valid range (1024-65535). Using default {default}."
            )
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
SSL_CERT_PATH = os.getenv(
    "CORGI_SSL_CERT_PATH", os.path.join(os.path.dirname(__file__), "certs", "cert.pem")
)
SSL_KEY_PATH = os.getenv(
    "CORGI_SSL_KEY_PATH", os.path.join(os.path.dirname(__file__), "certs", "key.pem")
)

# CORS Configuration
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5314"
).split(",")

# PostgreSQL Database Settings
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "user": os.getenv("POSTGRES_USER", ""),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
    "dbname": os.getenv("POSTGRES_DB", "corgi_recommender"),
}

# Validate required database credentials for production
if ENV == "production" and (not DB_CONFIG["user"] or not DB_CONFIG["password"]):
    raise ValueError(
        "POSTGRES_USER and POSTGRES_PASSWORD environment variables must be set in production"
    )
elif not DB_CONFIG["user"] or not DB_CONFIG["password"]:
    # In development, allow fallback to system user authentication if no credentials provided
    print(
        "WARNING: Database credentials not provided. Using system user authentication."
    )
    if not DB_CONFIG["user"]:
        import getpass

        DB_CONFIG["user"] = getpass.getuser()
        print(f"Using system username: {DB_CONFIG['user']}")

# User Privacy Settings
USER_HASH_SALT = os.getenv("USER_HASH_SALT", "")
if not USER_HASH_SALT:
    if ENV == "production":
        raise ValueError(
            "USER_HASH_SALT environment variable must be set in production"
        )
    else:
        print(
            "WARNING: USER_HASH_SALT not set. Using an empty salt is not secure for production!"
        )

# Redis Cache Settings
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "True").lower() == "true"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Construct Redis URL
if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Allow override of Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", REDIS_URL)

# Redis TTL Settings
REDIS_TTL = int(os.getenv("REDIS_TTL", "3600"))  # Default cache TTL: 1 hour
REDIS_TTL_RECOMMENDATIONS = int(os.getenv("REDIS_TTL_RECOMMENDATIONS", "3600"))  # 1 hour
REDIS_TTL_TIMELINE = int(os.getenv("REDIS_TTL_TIMELINE", "300"))  # 5 minutes
REDIS_TTL_PROFILE = int(os.getenv("REDIS_TTL_PROFILE", "600"))  # 10 minutes
REDIS_TTL_POST = int(os.getenv("REDIS_TTL_POST", "1800"))  # 30 minutes
REDIS_TTL_HEALTH = int(os.getenv("REDIS_TTL_HEALTH", "60"))  # 1 minute
REDIS_TTL_INTERACTIONS = int(os.getenv("REDIS_TTL_INTERACTIONS", "600"))  # 10 minutes
REDIS_TTL_PRIVACY = int(os.getenv("REDIS_TTL_PRIVACY", "3600"))  # 1 hour
REDIS_TTL_OPTOUT_STATUS = int(os.getenv("REDIS_TTL_OPTOUT_STATUS", "172800"))  # 48 hours

# Proxy-specific TTL Settings
PROXY_CACHE_TTL_TIMELINE = int(os.getenv("PROXY_CACHE_TTL_TIMELINE", "120"))  # 2 minutes
PROXY_CACHE_TTL_PROFILE = int(os.getenv("PROXY_CACHE_TTL_PROFILE", "600"))  # 10 minutes
PROXY_CACHE_TTL_INSTANCE = int(os.getenv("PROXY_CACHE_TTL_INSTANCE", "3600"))  # 1 hour
PROXY_CACHE_TTL_STATUS = int(os.getenv("PROXY_CACHE_TTL_STATUS", "1800"))  # 30 minutes
PROXY_CACHE_TTL_DEFAULT = int(os.getenv("PROXY_CACHE_TTL_DEFAULT", "900"))  # 15 minutes

# Rate limiting storage URL (uses same Redis as cache)
RATE_LIMITING_STORAGE_URL = os.getenv("RATE_LIMITING_STORAGE_URL", REDIS_URL)

# Rate Limiting Configuration
RATE_LIMITING_ENABLED = os.getenv("RATE_LIMITING_ENABLED", "True").lower() == "true"
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "2000 per hour")  # Increased from 100/min to 2000/hour
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "3000 per hour")  # Increased from 200/min to 3000/hour for authenticated users
RATE_LIMIT_ANONYMOUS = os.getenv("RATE_LIMIT_ANONYMOUS", "1000 per hour")  # Increased from 50/min to 1000/hour for anonymous users
RATE_LIMIT_HEALTH = os.getenv("RATE_LIMIT_HEALTH", "500 per hour")  # Increased from 10/min to 500/hour

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
    "include_synthetic": os.getenv("RANKING_INCLUDE_SYNTHETIC", "False").lower()
    == "true",
}

# Ranking algorithm thresholds
MIN_RANKING_SCORE = float(os.getenv('MIN_RANKING_SCORE', '0.01'))  # Lowered from 0.1 for better demo experience
DEMO_MIN_POSTS = int(os.getenv('DEMO_MIN_POSTS', '10'))  # Minimum posts to return in demo mode

# Health Check Settings
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))

# Proxy Settings
DEFAULT_MASTODON_INSTANCE = os.getenv(
    "DEFAULT_MASTODON_INSTANCE", "https://mastodon.social"
)
RECOMMENDATION_BLEND_RATIO = float(os.getenv("RECOMMENDATION_BLEND_RATIO", "0.3"))
PROXY_TIMEOUT = int(os.getenv("PROXY_TIMEOUT", "10"))

# Cold Start Settings
COLD_START_ENABLED = os.getenv("COLD_START_ENABLED", "True").lower() == "true"
COLD_START_POSTS_PATH = os.getenv(
    "COLD_START_POSTS_PATH",
    os.path.join(os.path.dirname(__file__), "data", "cold_start_posts.json"),
)
COLD_START_POST_LIMIT = int(os.getenv("COLD_START_POST_LIMIT", "30"))
ALLOW_COLD_START_FOR_ANONYMOUS = (
    os.getenv("ALLOW_COLD_START_FOR_ANONYMOUS", "True").lower() == "true"
)

# Testing Configuration Class
class TestingConfig:
    """Configuration class for testing environment."""
    
    TESTING = True
    DEBUG = True
    ENV = "testing"
    
    # Use in-memory SQLite for testing
    DB_CONFIG = {
        "host": "localhost",
        "port": "5432", 
        "user": "test_user",
        "password": "test_password",
        "dbname": "test_corgi_recommender",
    }
    
    # Disable Redis for testing to avoid external dependencies
    REDIS_ENABLED = False
    
    # Short TTLs for testing
    REDIS_TTL = 10
    REDIS_TTL_RECOMMENDATIONS = 10
    REDIS_TTL_TIMELINE = 5
    REDIS_TTL_PROFILE = 5
    REDIS_TTL_POST = 10
    REDIS_TTL_HEALTH = 5
    REDIS_TTL_INTERACTIONS = 5
    REDIS_TTL_PRIVACY = 10
    REDIS_TTL_OPTOUT_STATUS = 20
    
    # Testing-specific settings
    USER_HASH_SALT = "test_salt_123"
    API_VERSION = "v1"
    API_PREFIX = "/api/v1"
    HOST = "localhost"
    PORT = 5999  # Different port for testing
    PROXY_PORT = 5998
    USE_HTTPS = False
    
    # Algorithm config for testing
    ALGORITHM_CONFIG = {
        "weights": {
            "author_preference": 0.4,
            "content_engagement": 0.3,
            "recency": 0.3,
        },
        "time_decay_days": 7,
        "min_interactions": 0,
        "max_candidates": 10,  # Smaller for faster testing
        "include_synthetic": True,
    }
    
    # Health check settings
    HEALTH_CHECK_TIMEOUT = 1  # Faster for testing
    
    # Proxy settings
    DEFAULT_MASTODON_INSTANCE = "https://mastodon.social"
    RECOMMENDATION_BLEND_RATIO = 0.3
    PROXY_TIMEOUT = 2  # Shorter timeout for testing
    
    # Cold start settings
    COLD_START_ENABLED = True
    COLD_START_POST_LIMIT = 5  # Smaller for testing
    ALLOW_COLD_START_FOR_ANONYMOUS = True
