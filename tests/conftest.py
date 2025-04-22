"""
Test fixtures for the Corgi Recommender Service.
"""

import os
import pytest
import threading
import time
from unittest.mock import patch
import psycopg2

from app import create_app


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    # Setup environment variables for testing
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['DEBUG'] = 'True'
    os.environ['POSTGRES_DB'] = 'corgi_recommender_test'
    os.environ['USER_HASH_SALT'] = 'test-salt-for-pytest'
    
    app = create_app()
    app.config['TESTING'] = True
    
    # Use in-memory database for tests
    with patch('db.connection.init_db'):
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
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'dbname': os.getenv('POSTGRES_DB', 'corgi_recommender_test')
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
        cur.execute("""
            DROP TABLE IF EXISTS interactions CASCADE;
            DROP TABLE IF EXISTS privacy_settings CASCADE;
            DROP TABLE IF EXISTS post_metadata CASCADE;
            DROP TABLE IF EXISTS post_rankings CASCADE;
        """)
    
    conn.close()