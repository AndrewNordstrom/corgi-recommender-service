#!/usr/bin/env python3
"""
Script to link a demo Mastodon user with a provided token.
"""

import os
import logging
import sys

# Set environment variable for in-memory database
os.environ["USE_IN_MEMORY_DB"] = "true"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('link_user')

def link_mastodon_user(user_id, instance_url, access_token):
    """
    Link a user to a Mastodon account.
    
    Args:
        user_id: Local user ID to link
        instance_url: Mastodon instance URL
        access_token: Mastodon OAuth token
    """
    try:
        # Import the DB connection module
        from db.connection import get_db_connection
        
        # Ensure instance_url has the correct format
        if instance_url and not instance_url.startswith(('http://', 'https://')):
            instance_url = f"https://{instance_url}"
        
        logger.info(f"Linking user {user_id} to {instance_url} with provided token")
        
        with get_db_connection() as conn:
            # Create cursor (SQLite doesn't support context manager for cursor)
            cur = conn.cursor()
            
            try:
                # Check if the user already exists
                cur.execute(
                    "SELECT user_id FROM user_identities WHERE user_id = ?",
                    (user_id,)
                )
                result = cur.fetchone()
                
                if result:
                    # Update existing record
                    logger.info(f"Updating existing identity for user {user_id}")
                    cur.execute(
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
                    cur.execute(
                        """
                        INSERT INTO user_identities
                        (user_id, instance_url, access_token)
                        VALUES (?, ?, ?)
                        """,
                        (user_id, instance_url, access_token)
                    )
                
                # Also set privacy settings to 'full' to allow personalization
                cur.execute(
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
                return True
            finally:
                # Close the cursor
                cur.close()
    except Exception as e:
        logger.error(f"Error linking user: {e}")
        return False

def main():
    # User information
    user_id = "demo_user"
    instance_url = "mastodon.social"
    access_token = "_Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc"
    
    # Link the user
    if link_mastodon_user(user_id, instance_url, access_token):
        print(f"\nSuccessfully linked user {user_id} to {instance_url}")
        print(f"Access token registered and ready to use with Elk")
    else:
        print("\nFailed to link user. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()