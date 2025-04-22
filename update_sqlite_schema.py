#!/usr/bin/env python3
"""
Update SQLite schema to include user_identities table
"""

import os
import logging

# Force in-memory SQLite mode
os.environ["USE_IN_MEMORY_DB"] = "true"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('update_schema')

def update_sqlite_schema():
    """Update SQLite schema to add user_identities table"""
    try:
        # Import the DB connection module
        from db.connection import get_db_connection
        
        # SQL for adding user_identities table
        add_user_identities_sql = """
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create index for access token lookup
        CREATE INDEX IF NOT EXISTS idx_user_identities_access_token ON user_identities(access_token);
        """
        
        with get_db_connection() as conn:
            # Create cursor
            cursor = conn.cursor()
            
            try:
                logger.info("Adding user_identities table to SQLite schema...")
                cursor.executescript(add_user_identities_sql)
                conn.commit()
                logger.info("User identities table added successfully")
                
                # Check if the table was created
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_identities'")
                if cursor.fetchone():
                    logger.info("Confirmed user_identities table exists")
                    return True
                else:
                    logger.error("Failed to create user_identities table")
                    return False
            finally:
                cursor.close()
    except Exception as e:
        logger.error(f"Error updating schema: {e}")
        return False

if __name__ == "__main__":
    if update_sqlite_schema():
        print("Successfully updated SQLite schema")
    else:
        print("Failed to update SQLite schema")