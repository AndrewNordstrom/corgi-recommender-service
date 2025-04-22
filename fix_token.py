#!/usr/bin/env python3
"""
Script to fix token assignment in the database.
"""

import os
import sqlite3
import sys
import uuid

# Define the SQLite database file path
DB_FILE = os.path.join(os.path.dirname(__file__), 'corgi_demo.db')

def fix_token_assignment():
    """Fix token assignment in the database."""
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Generate a new unique token for demo_user
        new_demo_token = f"demo_{uuid.uuid4().hex[:20]}"
        
        # Update demo_user with the new token
        cursor.execute(
            """
            UPDATE user_identities
            SET access_token = ?
            WHERE user_id = 'demo_user'
            """,
            (new_demo_token,)
        )
        
        conn.commit()
        
        # Verify the update
        cursor.execute(
            """
            SELECT user_id, substr(access_token, 1, 10) || '...' as token_snippet
            FROM user_identities
            """
        )
        
        users = cursor.fetchall()
        print("\nUpdated User Tokens:")
        print("=" * 50)
        for user in users:
            print(f"{user['user_id']:<20} {user['token_snippet']:<20}")
        print("=" * 50)
        
        # Verify which user now has the Elk token
        token = "_Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc"
        cursor.execute(
            """
            SELECT user_id, instance_url
            FROM user_identities
            WHERE access_token = ?
            """,
            (token,)
        )
        
        result = cursor.fetchone()
        if result:
            print(f"\nToken '_Tb8I...' is now assigned ONLY to: {result['user_id']}")
            print(f"Instance URL: {result['instance_url']}\n")
            print("Elk integration should now work correctly with your actual user account.")
            print("Restart the proxy server if it's already running.")
        else:
            print("\nERROR: The Elk token is not assigned to any user in the database.\n")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    fix_token_assignment()