#!/usr/bin/env python3
"""
Script to check user identities in the database.
"""

import os
import sqlite3
import sys

# Define the SQLite database file path
DB_FILE = os.path.join(os.path.dirname(__file__), 'corgi_demo.db')

def list_users():
    """List all users in the database."""
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all users
        cursor.execute(
            """
            SELECT id, user_id, instance_url, 
                   substr(access_token, 1, 5) || '...' as token_snippet,
                   created_at, updated_at
            FROM user_identities
            """
        )
        
        users = cursor.fetchall()
        
        # Print results
        print("\nUser Identities in Database:")
        print("=" * 80)
        print(f"{'ID':<5} {'User ID':<20} {'Instance URL':<30} {'Token':<15} {'Created':<20}")
        print("-" * 80)
        
        for user in users:
            print(f"{user['id']:<5} {user['user_id']:<20} {user['instance_url']:<30} {user['token_snippet']:<15} {user['created_at']:<20}")
        
        print("=" * 80)
        print(f"Total: {len(users)} users\n")
        
        # Check for the specific token used in Elk
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
            print(f"Token '_Tb8I...' belongs to user: {result['user_id']}")
            print(f"Instance URL: {result['instance_url']}\n")
        else:
            print("Token '_Tb8I...' is not assigned to any user in the database.\n")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    list_users()