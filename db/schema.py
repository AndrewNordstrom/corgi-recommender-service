"""
Database schema definition module for the Corgi Recommender Service.

This module defines the database tables and schema migrations for the Corgi
recommender system, a PostgreSQL-backed recommendation engine for the fediverse.
It also includes SQLite schema for testing with an in-memory database.
"""

import logging
import os
import psycopg2
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

# Flag for in-memory SQLite mode
USE_IN_MEMORY_DB = os.getenv("USE_IN_MEMORY_DB", "false").lower() == "true"

# SQL to drop all tables (for dev resets)
DROP_TABLES_SQL = """
DROP TABLE IF EXISTS post_rankings;
DROP TABLE IF EXISTS interactions;
DROP TABLE IF EXISTS post_metadata;
DROP TABLE IF EXISTS privacy_settings;
DROP TABLE IF EXISTS user_identities;
DROP TABLE IF EXISTS api_keys;
"""

# Create table definitions
CREATE_TABLES_SQL = """
-- Table: privacy_settings
-- Stores user privacy preferences and tracking consent levels
CREATE TABLE IF NOT EXISTS privacy_settings (
    user_id TEXT PRIMARY KEY,
    tracking_level TEXT CHECK (tracking_level IN ('full', 'limited', 'none')) DEFAULT 'full',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: post_metadata
-- Stores post content and metadata from Mastodon/fediverse
CREATE TABLE IF NOT EXISTS post_metadata (
    post_id TEXT PRIMARY KEY,
    author_id TEXT NOT NULL,
    author_name TEXT,
    content TEXT,
    language TEXT DEFAULT 'en',
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    sensitive BOOLEAN DEFAULT FALSE,
    mastodon_post JSONB,
    interaction_counts JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE,
    created_local_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: interactions
-- Tracks user interactions with posts (favorites, bookmarks, reblogs, etc.)
CREATE TABLE IF NOT EXISTS interactions (
    id SERIAL PRIMARY KEY,
    user_alias TEXT NOT NULL,
    post_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    context JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_post_action UNIQUE (user_alias, post_id, action_type),
    CONSTRAINT fk_post_id FOREIGN KEY (post_id) REFERENCES post_metadata(post_id) ON DELETE CASCADE
);

-- Table: post_rankings
-- Stores personalized post rankings for each user
CREATE TABLE IF NOT EXISTS post_rankings (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    post_id TEXT NOT NULL,
    ranking_score FLOAT NOT NULL,
    recommendation_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_post UNIQUE (user_id, post_id),
    CONSTRAINT fk_post_id FOREIGN KEY (post_id) REFERENCES post_metadata(post_id) ON DELETE CASCADE
);

-- Table: user_identities
-- Stores user identity information for linking Mastodon accounts to internal user IDs
CREATE TABLE IF NOT EXISTS user_identities (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    instance_url TEXT NOT NULL,
    mastodon_id TEXT,
    access_token TEXT,
    refresh_token TEXT,
    token_scope TEXT,
    token_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: ab_user_assignments
-- Tracks which variant each user is assigned to for an experiment
CREATE TABLE IF NOT EXISTS ab_user_assignments (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    experiment_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_experiment UNIQUE (user_id, experiment_id)
);

-- Table: api_keys
-- Stores API keys for secure authentication
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    username VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    description TEXT,
    scopes TEXT[] DEFAULT ARRAY['read_content', 'create_interactions']
);
"""

# Create indexes for optimized queries
CREATE_INDEXES_SQL = """
-- Indexes for interactions table
CREATE INDEX IF NOT EXISTS idx_interactions_user_alias ON interactions(user_alias);
CREATE INDEX IF NOT EXISTS idx_interactions_post_id ON interactions(post_id);
CREATE INDEX IF NOT EXISTS idx_interactions_action_type ON interactions(action_type);
CREATE INDEX IF NOT EXISTS idx_interactions_user_post ON interactions(user_alias, post_id);
CREATE INDEX IF NOT EXISTS idx_interactions_context ON interactions USING GIN (context);

-- Indexes for post_metadata table
CREATE INDEX IF NOT EXISTS idx_post_author ON post_metadata(author_id);
CREATE INDEX IF NOT EXISTS idx_post_created_at ON post_metadata(created_at);
CREATE INDEX IF NOT EXISTS idx_post_language ON post_metadata(language);
CREATE INDEX IF NOT EXISTS idx_post_tags ON post_metadata USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_post_interaction_counts ON post_metadata USING GIN (interaction_counts);

-- Indexes for post_rankings table
CREATE INDEX IF NOT EXISTS idx_post_rankings_user_id ON post_rankings(user_id);
CREATE INDEX IF NOT EXISTS idx_post_rankings_post_id ON post_rankings(post_id);
CREATE INDEX IF NOT EXISTS idx_post_rankings_user_score ON post_rankings(user_id, ranking_score DESC);

-- Indexes for user_identities table
CREATE INDEX IF NOT EXISTS idx_user_identities_user_id ON user_identities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_identities_access_token ON user_identities(access_token);
CREATE INDEX IF NOT EXISTS idx_user_identities_mastodon_id ON user_identities(mastodon_id);

-- Indexes for api_keys table
CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
"""


def create_tables(conn):
    """
    Create database tables if they don't exist.

    Args:
        conn: Database connection
    """
    with conn.cursor() as cur:
        # Create tables
        logger.info("Creating database tables...")
        cur.execute(CREATE_TABLES_SQL)

        # Create indexes
        logger.info("Creating table indexes...")
        cur.execute(CREATE_INDEXES_SQL)

        # Commit the transaction
        conn.commit()
        logger.info("Database schema created successfully")


def reset_tables(conn):
    """
    Reset (drop and recreate) all tables - use only in development!

    Args:
        conn: Database connection
    """
    with conn.cursor() as cur:
        logger.warning("Dropping all tables - THIS WILL DELETE ALL DATA!")
        cur.execute(DROP_TABLES_SQL)
        conn.commit()

    # Recreate tables
    create_tables(conn)
    logger.info("Database reset complete")


def check_schema_version(conn):
    """
    Check if schema needs migration by looking for required columns.

    Args:
        conn: Database connection

    Returns:
        bool: True if schema is up to date, False if migration needed
    """
    try:
        with conn.cursor() as cur:
            # Check if post_metadata has language column
            cur.execute(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='post_metadata' AND column_name='language'
            """
            )
            has_language = cur.fetchone() is not None

            # Check if post_rankings has recommendation_reason column
            cur.execute(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='post_rankings' AND column_name='recommendation_reason'
            """
            )
            has_reason = cur.fetchone() is not None

            # Add more checks as schema evolves

            # Return True if all expected columns exist
            return has_language and has_reason
    except Exception as e:
        logger.error(f"Error checking schema version: {e}")
        return False


# SQLite schema for in-memory testing mode
CREATE_SQLITE_TABLES_SQL = """
-- Table: crawled_posts
-- Stores crawled post data from external sources
CREATE TABLE IF NOT EXISTS crawled_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    author_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_url TEXT,
    metadata TEXT DEFAULT '{}',
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rich_content TEXT DEFAULT NULL,
    media_urls TEXT DEFAULT NULL,
    hashtags TEXT DEFAULT NULL,
    mentions TEXT DEFAULT NULL,
    language TEXT DEFAULT NULL,
    engagement_score REAL DEFAULT 0.0,
    favourites_count INTEGER DEFAULT 0,
    reblogs_count INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    interaction_counts TEXT DEFAULT '{}'
);

-- Table: post_metadata
-- Stores additional metadata for posts
CREATE TABLE IF NOT EXISTS post_metadata (
    post_id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    tags TEXT,
    category TEXT,
    language TEXT,
    reading_time INTEGER,
    word_count INTEGER,
    sentiment_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);

-- Table: posts
-- Stores post content and basic metadata
CREATE TABLE IF NOT EXISTS posts (
    post_id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    author_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}',
    language TEXT DEFAULT 'en',
    favourites_count INTEGER DEFAULT 0,
    reblogs_count INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    interaction_counts TEXT DEFAULT '{}'
);

-- Table: interactions
-- Tracks user interactions with posts
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    user_alias TEXT,
    post_id TEXT NOT NULL,
    interaction_type TEXT NOT NULL,
    action_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, post_id, interaction_type)
);

-- Table: recommendations
-- Stores recommendation data
CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    post_id TEXT NOT NULL,
    score REAL NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, post_id)
);

-- Table: privacy_settings
-- Stores user privacy preferences
CREATE TABLE IF NOT EXISTS privacy_settings (
    user_id TEXT PRIMARY KEY,
    tracking_level TEXT CHECK (tracking_level IN ('full', 'limited', 'none')) DEFAULT 'full',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: user_identities
-- Stores user identity information for linking Mastodon accounts to internal user IDs
CREATE TABLE IF NOT EXISTS user_identities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,
    instance_url TEXT NOT NULL,
    mastodon_id TEXT,
    access_token TEXT,
    refresh_token TEXT,
    token_scope TEXT,
    token_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: users
-- Stores basic user information
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    username TEXT,
    display_name TEXT,
    preferences TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: ab_experiments
-- Stores A/B testing experiment definitions
CREATE TABLE IF NOT EXISTS ab_experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'draft',
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: ab_user_assignments
CREATE TABLE IF NOT EXISTS ab_user_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    experiment_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, experiment_id)
);

-- RBAC Tables
-- Table: roles
-- Stores role definitions
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    is_system_role BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: permissions
-- Stores permission definitions
CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(150),
    description TEXT,
    resource VARCHAR(50),
    action VARCHAR(50),
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: role_permissions
-- Associates roles with permissions
CREATE TABLE IF NOT EXISTS role_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)
);

-- Table: user_roles
-- Associates users with roles
CREATE TABLE IF NOT EXISTS user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    assigned_by TEXT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    UNIQUE(user_id, role_id)
);
"""


def create_sqlite_tables(conn):
    """
    Create SQLite tables for in-memory testing.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Create the tables
    logger.info("Creating SQLite in-memory tables...")
    cursor.executescript(CREATE_SQLITE_TABLES_SQL)

    # Create indexes
    logger.info("Creating SQLite indexes...")
    cursor.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_interactions_user_id ON interactions(user_id);
        CREATE INDEX IF NOT EXISTS idx_interactions_post_id ON interactions(post_id);
        CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);
        CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON recommendations(user_id);
    """
    )

    # Commit changes
    conn.commit()
    logger.info("SQLite in-memory database schema created successfully")


def create_api_keys_table(conn):
    """Create the api_keys table for secure API key management."""
    cursor = conn.cursor()
    
    try:
        # Create API keys table for secure authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id SERIAL PRIMARY KEY,
                api_key VARCHAR(255) UNIQUE NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'user',
                username VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP,
                expires_at TIMESTAMP,
                description TEXT,
                scopes TEXT[] DEFAULT ARRAY['read_content', 'create_interactions']
            );
        """)
        
        # Create index for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(api_key);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
        """)
        
        conn.commit()
        logger.info("API keys table created successfully")
        
    except Exception as e:
        logger.error(f"Error creating API keys table: {e}")
        conn.rollback()
        raise


def init_db(conn=None):
    """
    Initialize the database schema.

    Can be called directly or via the db.connection module.

    Args:
        conn: Optional database connection (if None, will create one)
    """
    if conn is None:
        from db.connection import get_db_connection

        with get_db_connection() as conn:
            if USE_IN_MEMORY_DB:
                create_sqlite_tables(conn)
            else:
                try:
                    # Check if tables exist first
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'post_metadata')"
                        )
                        tables_exist = cur.fetchone()[0]

                    if not tables_exist:
                        # No tables, create them all
                        create_tables(conn)
                    else:
                        # Tables exist, check if they need updates
                        if not check_schema_version(conn):
                            logger.info(
                                "Schema needs upgrade - performing migrations..."
                            )
                            # Future: Add migration logic here
                except Exception as e:
                    logger.error(f"Database initialization error: {e}")
                    raise
    else:
        if USE_IN_MEMORY_DB:
            create_sqlite_tables(conn)
        else:
            try:
                # Check if tables exist first
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'post_metadata')"
                    )
                    tables_exist = cur.fetchone()[0]

                if not tables_exist:
                    # No tables, create them all
                    create_tables(conn)
                else:
                    # Tables exist, check if they need updates
                    if not check_schema_version(conn):
                        logger.info("Schema needs upgrade - performing migrations...")
                        # Future: Add migration logic here
            except Exception as e:
                logger.error(f"Database initialization error: {e}")
                raise
