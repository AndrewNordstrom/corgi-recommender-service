#!/usr/bin/env python3
"""
Script to update token for an actual user in the database.
"""

import os
import sqlite3
import sys

# Define the SQLite database file path
DB_FILE = os.path.join(os.path.dirname(__file__), 'corgi_demo.db')

def update_user_token(user_id, new_token):
    """Update token for a user in the database."""
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Update the token
        cursor.execute(
            """
            UPDATE user_identities
            SET access_token = ?
            WHERE user_id = ?
            """,
            (new_token, user_id)
        )
        
        # Check if any rows were affected
        rows_affected = cursor.rowcount
        conn.commit()
        
        # Verify the update
        cursor.execute(
            """
            SELECT user_id, substr(access_token, 1, 10) || '...' as token_snippet
            FROM user_identities
            WHERE user_id = ?
            """,
            (user_id,)
        )
        
        user = cursor.fetchone()
        
        if user:
            print(f"\nUser {user_id} token updated successfully:")
            print(f"  New token snippet: {user['token_snippet']}")
            
            # Test token lookup
            cursor.execute(
                """
                SELECT user_id, instance_url
                FROM user_identities
                WHERE access_token = ?
                """,
                (new_token,)
            )
            
            result = cursor.fetchone()
            if result:
                print(f"Token lookup successful: user={result['user_id']}, instance={result['instance_url']}")
                print("\nToken updated successfully. Elk should now work correctly with this token.")
            else:
                print("ERROR: Token lookup failed - something went wrong with the update.")
        else:
            print(f"\nERROR: User {user_id} not found in the database!")
        
        conn.close()
        return rows_affected > 0
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # User information from the updated Elk JSON
    user_id = "YOUR_USER_ID"
    new_token = "YOUR_TOKEN_VALUE"
    
    print(f"Updating token for user {user_id}...\n")
    update_user_token(user_id, new_token)