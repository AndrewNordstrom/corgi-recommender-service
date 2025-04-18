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
API_VERSION = "v1"
API_PREFIX = f"/{API_VERSION}"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENV = os.getenv("FLASK_ENV", "development")

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