#!/usr/bin/env python3
"""
Script to link an actual Mastodon user with a provided token to the persistent SQLite database.
"""

import os
import logging
import sys
import sqlite3

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('link_user')

# Define the SQLite database file path
DB_FILE = os.path.join(os.path.dirname(__file__), 'corgi_demo.db')

def link_actual_user(user_id, instance_url, access_token):
    """
    Link a user to a Mastodon account in the persistent database.
    
    Args:
        user_id: Local user ID to link
        instance_url: Mastodon instance URL
        access_token: Mastodon OAuth token
    """
    try:
        # Ensure instance_url has the correct format
        if instance_url and not instance_url.startswith(('http://', 'https://')):
            instance_url = f"https://{instance_url}"
        
        logger.info(f"Linking user {user_id} to {instance_url} with provided token")
        
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        
        try:
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
            
            # Test token lookup (this is how the proxy will find your user)
            cursor.execute(
                "SELECT user_id, instance_url FROM user_identities WHERE access_token = ?", 
                (access_token,)
            )
            result = cursor.fetchone()
            if result:
                logger.info(f"Token lookup successful: user={result[0]}, instance={result[1]}")
            else:
                logger.warning("WARNING: Token lookup failed - proxy might not work correctly")
            
            return True
        finally:
            # Close the connection
            conn.close()
    except Exception as e:
        logger.error(f"Error linking user: {e}")
        return False

def main():
    # User information from the Elk JSON
    user_id = "agent_artemis"  # Use the username from your Elk config
    instance_url = "mastodon.social"  # Use the server from your Elk config
    access_token = "_Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc"  # The token from your Elk config
    
    # Link the user
    if link_actual_user(user_id, instance_url, access_token):
        print(f"\nSuccessfully linked user {user_id} to {instance_url}")
        print(f"Access token registered and ready to use with Elk")
        
        # Check if proxy server is running
        import subprocess
        proxy_running = subprocess.run(
            "ps aux | grep 'special_proxy.py' | grep -v grep", 
            shell=True, 
            capture_output=True
        ).stdout
        
        if not proxy_running:
            print("\nNOTE: The special proxy server is not running!")
            print("Start it with: python3 special_proxy.py")
        
        # Show instructions
        print("\nNow you can configure Elk:")
        print("1. In Elk, sign in with your server set to: https://localhost:5003")
        print("2. Import your JSON configuration (with your token)")
        print("3. When Elk loads, your user should be properly recognized")
    else:
        print("\nFailed to link user. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()