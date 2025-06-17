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


@pytest.fixture
def seed_test_data(app):
    """Seed the test database with comprehensive test data."""
    from db.connection import get_db_connection
    
    with app.app_context():
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Clear existing data more robustly
            try:
                cur.execute("DELETE FROM interactions")
                cur.execute("DELETE FROM recommendations") 
                cur.execute("DELETE FROM posts")
                cur.execute("DELETE FROM crawled_posts")
                cur.execute("DELETE FROM users")
                cur.execute("DELETE FROM ab_experiments")
            except Exception as e:
                # Some tables might not exist, continue
                pass
            
            # Seed users
            cur.execute("""
                INSERT OR REPLACE INTO users (user_id, username, display_name, preferences)
                VALUES 
                    ('test_user123', 'testuser', 'Test User', '{}'),
                    ('test_user456', 'anotheruser', 'Another User', '{}'),
                    ('test_user_main', 'testuser2', 'Test User 2', '{}')
            """)
            
            # Seed posts with engagement data in metadata JSON (using test_ prefix to avoid conflicts)
            posts_data = [
                ('test_post1', 'Test post content 1', 'test_author1', '2024-01-01 10:00:00', '{"favourites_count": 10, "reblogs_count": 5, "replies_count": 2, "author_name": "test_author1"}', 'en'),
                ('test_post2', 'Test post content 2', 'test_author2', '2024-01-02 11:00:00', '{"favourites_count": 42, "reblogs_count": 20, "replies_count": 8, "author_name": "test_author2"}', 'en'),
                ('test_post3', 'Trending post content', 'test_author3', '2024-01-03 12:00:00', '{"favourites_count": 100, "reblogs_count": 50, "replies_count": 25, "author_name": "test_author3"}', 'en'),
                ('test_post4', 'Another test post', 'test_author1', '2024-01-04 13:00:00', '{"favourites_count": 15, "reblogs_count": 8, "replies_count": 3, "author_name": "test_author1"}', 'en'),
                ('test_post5', 'Fifth test post', 'test_author2', '2024-01-05 14:00:00', '{"favourites_count": 25, "reblogs_count": 12, "replies_count": 5, "author_name": "test_author2"}', 'en')
            ]
            
            for post in posts_data:
                cur.execute("""
                    INSERT OR REPLACE INTO posts (post_id, content, author_id, created_at, metadata, language)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, post)
            
            # Seed crawled posts (simplified for SQLite schema)
            crawled_posts_data = [
                ('test_crawled1', 'Crawled post 1', 'test_author4', '2024-01-06 15:00:00', 'http://example.com/1', '{"favourites_count": 8, "reblogs_count": 4, "replies_count": 1, "author_name": "test_author4"}', '2024-01-06 15:00:00', 'en', 0.5),
                ('test_crawled2', 'Crawled post 2', 'test_author5', '2024-01-07 16:00:00', 'http://example.com/2', '{"favourites_count": 12, "reblogs_count": 6, "replies_count": 2, "author_name": "test_author5"}', '2024-01-07 16:00:00', 'en', 0.7)
            ]
            
            for post in crawled_posts_data:
                cur.execute("""
                    INSERT OR REPLACE INTO crawled_posts (post_id, content, author_id, created_at, source_url, metadata, 
                                             crawled_at, language, engagement_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, post)
            
            # Seed interactions
            interactions_data = [
                ('test_user123', 'test_user_alias_123', 'test_post1', 'favorite'),
                ('test_user123', 'test_user_alias_123', 'test_post2', 'reblog'),
                ('test_user456', 'test_user_alias_456', 'test_post1', 'favorite'),
                ('test_user_main', 'test_user_alias_main', 'test_post3', 'favorite')
            ]
            
            for interaction in interactions_data:
                cur.execute("""
                    INSERT OR REPLACE INTO interactions (user_id, user_alias, post_id, interaction_type)
                    VALUES (?, ?, ?, ?)
                """, interaction)
            
            # Seed recommendations
            recommendations_data = [
                ('test_user123', 'test_post1', 0.9, 'High engagement from similar users'),
                ('test_user123', 'test_post2', 0.8, 'Trending in your network'),
                ('test_user456', 'test_post3', 0.95, 'Matches your interests')
            ]
            
            for rec in recommendations_data:
                cur.execute("""
                    INSERT OR REPLACE INTO recommendations (user_id, post_id, score, reason)
                    VALUES (?, ?, ?, ?)
                """, rec)
            
            # Seed AB experiments
            cur.execute("""
                INSERT OR REPLACE INTO ab_experiments (id, name, description, status)
                VALUES 
                    (1, 'test_experiment', 'A test experiment', 'active'),
                    (2, 'another_experiment', 'Another test experiment', 'draft')
            """)
            
            conn.commit()
    
    return True
