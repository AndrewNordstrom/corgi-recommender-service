#!/usr/bin/env python3
"""
Simplified setup script to link a Mastodon user using SQLite file database
"""

import os
import logging
import sqlite3
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('setup')

# Define the SQLite database file path
DB_FILE = os.path.join(os.path.dirname(__file__), 'corgi_demo.db')

def setup_database():
    """Create SQLite database with required tables"""
    logger.info(f"Setting up SQLite database at {DB_FILE}")
    
    # SQL to create tables
    create_tables_sql = """
    -- Table: user_identities
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

    -- Table: privacy_settings
    CREATE TABLE IF NOT EXISTS privacy_settings (
        user_id TEXT PRIMARY KEY,
        tracking_level TEXT CHECK (tracking_level IN ('full', 'limited', 'none')) DEFAULT 'full',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_user_identities_access_token ON user_identities(access_token);
    """
    
    try:
        # Connect to SQLite database (create if it doesn't exist)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Create tables
        cursor.executescript(create_tables_sql)
        conn.commit()
        
        logger.info("Database schema created successfully")
        return conn
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        if conn:
            conn.close()
        return None

def link_mastodon_user(conn, user_id, instance_url, access_token):
    """Link a user to a Mastodon account"""
    try:
        # Ensure instance_url has the correct format
        if instance_url and not instance_url.startswith(('http://', 'https://')):
            instance_url = f"https://{instance_url}"
        
        logger.info(f"Linking user {user_id} to {instance_url} with provided token")
        
        # Create cursor
        cursor = conn.cursor()
        
        # Check if the user already exists
        cursor.execute(
            "SELECT user_id FROM user_identities WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        
        if result:
            # Update existing record
            logger.info(f"Updating existing identity for user {user_id}")
            cursor.execute(
                """
                UPDATE user_identities
                SET instance_url = ?,
                    access_token = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (instance_url, access_token, user_id)
            )
        else:
            # Create new record
            logger.info(f"Creating new identity for user {user_id}")
            cursor.execute(
                """
                INSERT INTO user_identities
                (user_id, instance_url, access_token)
                VALUES (?, ?, ?)
                """,
                (user_id, instance_url, access_token)
            )
        
        # Also set privacy settings to 'full' to allow personalization
        cursor.execute(
            """
            INSERT OR REPLACE INTO privacy_settings
            (user_id, tracking_level)
            VALUES (?, 'full')
            """,
            (user_id,)
        )
        
        # Commit the transaction
        conn.commit()
        logger.info(f"Successfully linked user {user_id} to {instance_url}")
        
        # Verify the token was saved correctly
        cursor.execute(
            "SELECT access_token FROM user_identities WHERE user_id = ?",
            (user_id,)
        )
        saved_token = cursor.fetchone()[0]
        logger.info(f"Verified saved token: {saved_token[:5]}...")
        
        return True
    except Exception as e:
        logger.error(f"Error linking user: {e}")
        return False

def main():
    # User information
    user_id = "demo_user"
    instance_url = "mastodon.social"
    access_token = "_Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc"
    
    # Setup database
    conn = setup_database()
    if not conn:
        print("Failed to set up database")
        sys.exit(1)
    
    try:
        # Link the user
        if link_mastodon_user(conn, user_id, instance_url, access_token):
            print(f"\nSuccessfully linked user {user_id} to {instance_url}")
            print(f"Access token registered and ready to use with Elk")
            
            # Test token lookup
            cursor = conn.cursor()
            cursor.execute(
                "SELECT instance_url FROM user_identities WHERE access_token = ?", 
                (access_token,)
            )
            result = cursor.fetchone()
            if result:
                print(f"Token verification successful: {result[0]}")
            else:
                print("Warning: Token lookup failed")
        else:
            print("\nFailed to link user. Check logs for details.")
            sys.exit(1)
    finally:
        # Close the connection
        if conn:
            conn.close()

if __name__ == "__main__":
    main()