"""
Privacy utilities module for the Corgi Recommender Service.

This module provides functions for handling user privacy, including:
- User pseudonymization via hashing
- Privacy settings management
"""

import hashlib
import logging
from config import USER_HASH_SALT
from db.connection import USE_IN_MEMORY_DB, get_cursor

logger = logging.getLogger(__name__)

def generate_user_alias(user_id):
    """
    Hash a user ID for pseudonymization to protect user privacy.
    
    Args:
        user_id (str): The user ID to pseudonymize
        
    Returns:
        str: A SHA-256 hash of the user ID with salt
    """
    if not USER_HASH_SALT:
        logger.warning("Empty salt used for user pseudonymization - set USER_HASH_SALT!")
    
    return hashlib.sha256((user_id + USER_HASH_SALT).encode()).hexdigest()

def get_user_privacy_level(conn, user_id):
    """
    Get the privacy tracking level for a user.
    
    Args:
        conn: Database connection
        user_id (str): The user ID to get privacy settings for
        
    Returns:
        str: Privacy level ('full', 'limited', or 'none')
    """
    with get_cursor(conn) as cur:
        placeholder = "?" if USE_IN_MEMORY_DB else "%s"
        
        # Select based on database type
        if USE_IN_MEMORY_DB:
            table_name = "privacy_settings"
        else:
            table_name = "privacy_settings"
            
        query = f"SELECT tracking_level FROM {table_name} WHERE user_id = {placeholder}"
        cur.execute(query, (user_id,))
        result = cur.fetchone()
        
        if result:
            return result[0]
        else:
            # Default to 'full' tracking if no setting exists
            return 'full'

def update_user_privacy_level(conn, user_id, tracking_level):
    """
    Update the privacy tracking level for a user.
    
    Args:
        conn: Database connection
        user_id (str): The user ID to update privacy settings for
        tracking_level (str): New privacy level ('full', 'limited', or 'none')
        
    Returns:
        bool: True if successful, False otherwise
    """
    if tracking_level not in ('full', 'limited', 'none'):
        logger.error(f"Invalid tracking level: {tracking_level}")
        return False
    
    try:
        with get_cursor(conn) as cur:
            if USE_IN_MEMORY_DB:
                # SQLite version
                # Check if record exists
                cur.execute("SELECT 1 FROM privacy_settings WHERE user_id = ?", (user_id,))
                if cur.fetchone():
                    # Update existing
                    cur.execute('''
                        UPDATE privacy_settings 
                        SET tracking_level = ?
                        WHERE user_id = ?
                    ''', (tracking_level, user_id))
                else:
                    # Insert new
                    cur.execute('''
                        INSERT INTO privacy_settings (user_id, tracking_level)
                        VALUES (?, ?)
                    ''', (user_id, tracking_level))
            else:
                # PostgreSQL version with UPSERT
                cur.execute('''
                    INSERT INTO privacy_settings (user_id, tracking_level)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET tracking_level = EXCLUDED.tracking_level
                ''', (user_id, tracking_level))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating privacy level: {e}")
        conn.rollback()
        return False