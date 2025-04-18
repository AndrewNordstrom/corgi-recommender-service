#!/usr/bin/env python3
"""
User Identity Link Tool

Utility script to link a local user ID to a Mastodon account for testing
the proxy middleware.
"""

import argparse
import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the Python path
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from db.connection import get_db_connection

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('link_user')

def link_user(user_id, instance_url, mastodon_id=None, access_token=None):
    """
    Link a user to a Mastodon account.
    
    Args:
        user_id: Local user ID to link
        instance_url: Mastodon instance URL (e.g., https://mastodon.social)
        mastodon_id: Mastodon user ID
        access_token: Mastodon OAuth token
    """
    # Ensure instance_url has the correct format
    if instance_url and not instance_url.startswith(('http://', 'https://')):
        instance_url = f"https://{instance_url}"
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if user already exists
                cur.execute(
                    "SELECT id FROM user_identities WHERE user_id = %s",
                    (user_id,)
                )
                result = cur.fetchone()
                
                if result:
                    # Update existing record
                    logger.info(f"Updating existing identity for user {user_id}")
                    cur.execute(
                        """
                        UPDATE user_identities
                        SET instance_url = %s,
                            mastodon_id = %s,
                            access_token = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                        RETURNING id
                        """,
                        (instance_url, mastodon_id, access_token, user_id)
                    )
                else:
                    # Create new record
                    logger.info(f"Creating new identity for user {user_id}")
                    cur.execute(
                        """
                        INSERT INTO user_identities
                        (user_id, instance_url, mastodon_id, access_token)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (user_id, instance_url, mastodon_id, access_token)
                    )
                
                # Get the ID of the created/updated record
                identity_id = cur.fetchone()[0]
                
                # Commit the transaction
                conn.commit()
                
                logger.info(f"Successfully linked user {user_id} to {instance_url} (identity_id={identity_id})")
                return identity_id
                
    except Exception as e:
        logger.error(f"Error linking user: {e}")
        return None

def list_identities():
    """List all user identities in the database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, instance_url, mastodon_id, 
                           CASE WHEN access_token IS NULL THEN 'No' ELSE 'Yes' END as has_token,
                           created_at
                    FROM user_identities
                    ORDER BY created_at DESC
                    """
                )
                
                identities = cur.fetchall()
                
                if not identities:
                    logger.info("No user identities found in the database")
                    return
                
                print("\nUser Identities:")
                print("=" * 80)
                print(f"{'ID':<5} {'User ID':<20} {'Instance':<30} {'Mastodon ID':<15} {'Token':<5} {'Created'}")
                print("-" * 80)
                
                for identity in identities:
                    id, user_id, instance, mastodon_id, has_token, created = identity
                    print(f"{id:<5} {user_id:<20} {instance:<30} {mastodon_id or 'N/A':<15} {has_token:<5} {created}")
                
                print("=" * 80)
                print(f"Total: {len(identities)} identities\n")
                
    except Exception as e:
        logger.error(f"Error listing identities: {e}")

def main():
    parser = argparse.ArgumentParser(description="Link a user to a Mastodon account")
    
    # Command option
    parser.add_argument("--list", action="store_true", help="List all user identities")
    
    # User identity parameters
    parser.add_argument("--user-id", help="Local user ID to link")
    parser.add_argument("--instance", help="Mastodon instance URL (e.g., mastodon.social)")
    parser.add_argument("--mastodon-id", help="Mastodon user ID (optional)")
    parser.add_argument("--token", help="Mastodon OAuth token (optional)")
    
    args = parser.parse_args()
    
    # List identities if requested
    if args.list:
        list_identities()
        return
    
    # Validate parameters for linking
    if not args.user_id or not args.instance:
        parser.error("--user-id and --instance are required when linking a user")
    
    # Link the user
    identity_id = link_user(
        user_id=args.user_id,
        instance_url=args.instance,
        mastodon_id=args.mastodon_id,
        access_token=args.token
    )
    
    if identity_id:
        print(f"\nSuccessfully linked user {args.user_id} to {args.instance}")
        print(f"Identity ID: {identity_id}")
    else:
        print("\nFailed to link user. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()