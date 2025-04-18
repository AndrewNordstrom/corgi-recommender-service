"""
Database schema definition module for the Corgi Recommender Service.

This module defines the database tables and schema migrations for the Corgi
recommender system, a PostgreSQL-backed recommendation engine for the fediverse.
"""

import logging

logger = logging.getLogger(__name__)

# SQL to drop all tables (for dev resets)
DROP_TABLES_SQL = """
DROP TABLE IF EXISTS post_rankings;
DROP TABLE IF EXISTS interactions;
DROP TABLE IF EXISTS post_metadata;
DROP TABLE IF EXISTS privacy_settings;
DROP TABLE IF EXISTS user_identities;
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='post_metadata' AND column_name='language'
            """)
            has_language = cur.fetchone() is not None
            
            # Check if post_rankings has recommendation_reason column
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='post_rankings' AND column_name='recommendation_reason'
            """)
            has_reason = cur.fetchone() is not None
            
            # Add more checks as schema evolves
            
            # Return True if all expected columns exist
            return has_language and has_reason
    except Exception as e:
        logger.error(f"Error checking schema version: {e}")
        return False

def init_db(conn=None):
    """
    Initialize the database schema.
    
    Can be called directly or via the db.connection module.
    
    Args:
        conn: Optional database connection (if None, will create one)
    """
    if conn is None:
        from db.connection import get_db_connection
        conn = get_db_connection()
        auto_close = True
    else:
        auto_close = False
    
    try:
        # Check if tables exist first
        with conn.cursor() as cur:
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'post_metadata')")
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
    finally:
        if auto_close:
            conn.close()