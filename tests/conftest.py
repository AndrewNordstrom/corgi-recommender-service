"""
Test fixtures for the Corgi Recommender Service.
"""

import os

# Set test environment FIRST before any other imports
os.environ["USE_IN_MEMORY_DB"] = "true"
os.environ["FLASK_ENV"] = "testing"
os.environ["DEBUG"] = "True"
os.environ["POSTGRES_DB"] = "corgi_recommender_test"
os.environ["USER_HASH_SALT"] = "test-salt-for-pytest"

import pytest
import threading
import time
import logging
from unittest.mock import patch, MagicMock
import psycopg2

from app import create_app


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = create_app()
    app.config["TESTING"] = True

    # Use in-memory database for tests
    with patch("db.connection.init_db"):
        yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def init_test_db():
    """Initialize a test database."""
    # Database connection parameters from environment variables or defaults
    db_params = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "dbname": os.getenv("POSTGRES_DB", "corgi_recommender_test"),
    }

    # Connect to the database
    conn = psycopg2.connect(**db_params)
    conn.autocommit = True

    # Create the tables
    from db.schema import create_tables

    create_tables(conn)

    yield conn

    # Clean up: drop all tables after tests
    with conn.cursor() as cur:
        cur.execute(
            """
            DROP TABLE IF EXISTS interactions CASCADE;
            DROP TABLE IF EXISTS privacy_settings CASCADE;
            DROP TABLE IF EXISTS post_metadata CASCADE;
            DROP TABLE IF EXISTS post_rankings CASCADE;
        """
        )

    conn.close()


@pytest.fixture
def experiment_id():
    """Provide a test experiment ID for A/B testing experiments."""
    # Return a mock experiment ID for testing
    return 12345


@pytest.fixture
def logger():
    """Create a logger for testing agent features."""
    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create console handler with formatting
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


@pytest.fixture
def mocked_redis_client():
    """Create a mocked Redis client for testing API caching."""
    mock_redis = MagicMock()
    
    # Set up common Redis method return values
    mock_redis.get.return_value = None  # Default: no cached data
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.keys.return_value = []
    mock_redis.flushdb.return_value = True
    
    return mock_redis


@pytest.fixture
def variant_ids():
    """Create test variant IDs for A/B testing and performance monitoring tests."""
    return [1001, 1002, 1003]
