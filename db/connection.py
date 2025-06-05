"""
Database connection module for the Corgi Recommender Service.

This module provides connection pooling and database access utilities.
It also supports an in-memory mode for testing without a PostgreSQL database.
"""

import logging
import os
import sqlite3
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
import atexit

from config import DB_CONFIG

# Set up logging
logger = logging.getLogger(__name__)

# Determine if we should use the in-memory database
USE_IN_MEMORY_DB = os.getenv("USE_IN_MEMORY_DB", "false").lower() == "true"

# In-memory SQLite connection
in_memory_conn = None

# PostgreSQL connection pool
pool = None


# Function to initialize the pool
def initialize_connection_pool():
    global pool, in_memory_conn

    if USE_IN_MEMORY_DB:
        try:
            # Create SQLite in-memory database
            in_memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            logger.info("In-memory SQLite database initialized for testing")
            return True
        except Exception as e:
            logger.error(f"Error initializing in-memory database: {e}")
            return False
    else:
        try:
            pool = SimpleConnectionPool(minconn=1, maxconn=10, **DB_CONFIG)
            logger.info("Database connection pool established successfully")
            return True
        except Exception as e:
            logger.error(f"Error establishing database connection: {e}")
            return False


# Try initial connection
initialize_connection_pool()


# Register cleanup function to close connections when application exits
@atexit.register
def close_pool():
    global pool, in_memory_conn
    if pool:
        pool.closeall()
        logger.info("Database connection pool closed")
    if in_memory_conn:
        in_memory_conn.close()
        logger.info("In-memory database connection closed")


@contextmanager
def get_db_connection():
    """
    Context manager for getting a database connection.

    If USE_IN_MEMORY_DB is True, returns the SQLite in-memory connection.
    Otherwise, returns a connection from the PostgreSQL pool.

    Usage:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM table")
                results = cur.fetchall()

    Returns:
        A database connection
    """
    global pool, in_memory_conn

    if USE_IN_MEMORY_DB:
        # Return the in-memory SQLite connection
        if in_memory_conn is None:
            initialize_connection_pool()

        if in_memory_conn is None:
            logger.error("Failed to initialize in-memory database")
            raise Exception("In-memory database initialization failed")

        yield in_memory_conn
    else:
        # Try to initialize pool if it failed earlier
        if pool is None:
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries and pool is None:
                retry_count += 1
                logger.info(
                    f"Attempting to reconnect to database (attempt {retry_count}/{max_retries})"
                )

                if initialize_connection_pool():
                    break

                # Wait before retrying, with increasing backoff
                import time

                time.sleep(retry_count * 2)

            if pool is None:
                logger.error(
                    f"Failed to reconnect to database after {max_retries} attempts"
                )
                raise Exception(
                    f"Database connection failed after {max_retries} attempts"
                )

        # Get connection from pool
        try:
            conn = pool.getconn()
            try:
                yield conn
            finally:
                pool.putconn(conn)
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise


def init_db():
    """Initialize database schema if tables don't exist."""
    from db.schema import create_tables, create_sqlite_tables

    try:
        with get_db_connection() as conn:
            if USE_IN_MEMORY_DB:
                create_sqlite_tables(conn)
                logger.info("In-memory SQLite database schema created successfully")

                # Seed with some test data
                seed_test_data(conn)
            else:
                create_tables(conn)
                logger.info("PostgreSQL database schema initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def seed_test_data(conn):
    """Seed the in-memory database with test data for demo purposes."""
    logger.info("Seeding in-memory database with test data...")

    try:
        cursor = conn.cursor()

        # Add test users
        cursor.execute(
            """
            INSERT INTO users (user_id, username, preferences) 
            VALUES 
            ('user1', 'alice', '{"interests": ["corgis", "pets", "technology"]}'),
            ('user2', 'bob', '{"interests": ["cooking", "travel", "corgis"]}')
        """
        )

        # Add some test posts
        cursor.execute(
            """
            INSERT INTO posts (post_id, content, author_id, created_at, metadata) 
            VALUES 
            ('post1', 'Look at my cute corgi!', 'user1', datetime('now', '-1 day'), '{"tags": ["corgi", "cute"]}'),
            ('post2', 'Corgis are the best dogs', 'user2', datetime('now', '-2 day'), '{"tags": ["corgi", "opinion"]}'),
            ('post3', 'My corgi loves the beach', 'user1', datetime('now'), '{"tags": ["corgi", "beach"]}')
        """
        )

        # Add some interactions
        cursor.execute(
            """
            INSERT INTO interactions (user_id, post_id, interaction_type, created_at) 
            VALUES 
            ('user1', 'post2', 'like', datetime('now', '-12 hours')),
            ('user2', 'post1', 'bookmark', datetime('now', '-6 hours')),
            ('user2', 'post3', 'share', datetime('now', '-1 hour'))
        """
        )

        conn.commit()
        logger.info("Test data seeded successfully")
    except Exception as e:
        logger.error(f"Error seeding test data: {e}")
        conn.rollback()
        # Don't raise exception to allow system to continue without test data


# Utility function to handle both SQLite and PostgreSQL cursors
@contextmanager
def get_cursor(conn):
    """
    Context manager for getting a database cursor that works with both
    PostgreSQL (which supports context manager for cursor) and SQLite (which doesn't).

    Args:
        conn: Database connection

    Yields:
        A database cursor
    """
    if USE_IN_MEMORY_DB:
        # SQLite doesn't support context manager for cursor
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    else:
        # PostgreSQL supports context manager for cursor
        with conn.cursor() as cursor:
            yield cursor
