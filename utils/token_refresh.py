"""
Token refresh utility for Mastodon OAuth tokens.

This module provides functionality to automatically refresh OAuth access tokens
for long-term authentication stability.
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from db.connection import get_db_connection

logger = logging.getLogger(__name__)

def get_user_token_data(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user's token data from database.
    
    Args:
        user_id: The internal user ID
        
    Returns:
        Dict with user token data or None if not found
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT access_token, refresh_token, token_scope, token_expires_at,
                       user_id, instance_url, mastodon_id
                FROM user_identities 
                WHERE user_id = %s
            """, (user_id,))
            
            result = cur.fetchone()
            if not result:
                return None
                
            return {
                'access_token': result[0],
                'refresh_token': result[1],
                'token_scope': result[2],
                'token_expires_at': result[3],
                'user_id': result[4],
                'instance_url': result[5],
                'mastodon_id': result[6]
            }
            
    except Exception as e:
        logger.error(f"Error getting user token data for {user_id}: {e}")
        return None

def is_token_expired(expires_at: Optional[datetime], buffer_minutes: int = 5) -> bool:
    """
    Check if a token is expired or will expire soon.
    
    Args:
        expires_at: The token expiration datetime (or None)
        buffer_minutes: Minutes before expiry to consider "expired"
        
    Returns:
        True if token is expired or will expire within buffer time
    """
    if expires_at is None:
        return False  # No expiry set = assume valid
    
    try:
        # Ensure expires_at is a datetime object
        if isinstance(expires_at, str):
            # Try to parse string dates
            from datetime import datetime as dt
            expires_at = dt.fromisoformat(expires_at.replace('Z', '+00:00'))
        
        buffer_time = datetime.utcnow() + timedelta(minutes=buffer_minutes)
        return buffer_time >= expires_at
    except Exception as e:
        logger.error(f"Error checking token expiration: {e}")
        return True  # Assume expired on error

def update_user_tokens(user_id: str, token_info: Dict[str, Any]) -> bool:
    """
    Update user's token information in database.
    
    Args:
        user_id: The internal user ID
        token_info: Token information from OAuth response
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        access_token = token_info['access_token']
        refresh_token = token_info.get('refresh_token')
        expires_in = token_info.get('expires_in', 3600)
        scope = token_info.get('scope', 'read write follow')
        
        # Calculate expiration time
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE user_identities 
                SET access_token = %s,
                    refresh_token = %s,
                    token_expires_at = %s,
                    token_scope = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (access_token, refresh_token, token_expires_at, scope, user_id))
            
            if cur.rowcount == 0:
                logger.error(f"No user found to update for user_id: {user_id}")
                return False
                
            conn.commit()
            logger.info(f"Token updated successfully for user {user_id}, expires at {token_expires_at}")
            return True
            
    except Exception as e:
        logger.error(f"Error updating tokens for user {user_id}: {e}")
        return False

def get_app_credentials(instance_url: str) -> Optional[Dict[str, str]]:
    """
    Get OAuth app credentials for a Mastodon instance from database.
    
    Args:
        instance_url: The Mastodon instance URL
        
    Returns:
        Dict with client_id and client_secret, or None if not found
    """
    try:
        # Ensure instance URL has proper scheme
        if not instance_url.startswith(('http://', 'https://')):
            instance_url = f"https://{instance_url}"
        
        # Check database for app credentials
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT client_id, client_secret 
                FROM mastodon_apps 
                WHERE instance_url = %s
            """, (instance_url,))
            result = cur.fetchone()
            
            if result:
                return {
                    'client_id': result[0],
                    'client_secret': result[1]
                }
        
        logger.error(f"No app credentials found for instance: {instance_url}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting app credentials for {instance_url}: {e}")
        return None

def refresh_access_token(user_id: str, refresh_token: str, instance_url: str) -> Dict[str, Any]:
    """
    Refresh access token for a user.
    
    Args:
        user_id: The internal user ID
        refresh_token: The refresh token to use
        instance_url: The Mastodon instance URL
        
    Returns:
        Dict with success status and token data or error info
    """
    try:
        # Get app credentials for the instance
        app_creds = get_app_credentials(instance_url)
        if not app_creds:
            return {
                'success': False,
                'message': 'App credentials not found for instance'
            }
        
        # Prepare refresh request
        refresh_data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': app_creds['client_id'],
            'client_secret': app_creds['client_secret']
        }
        
        # Make refresh request to Mastodon
        response = requests.post(
            f"{instance_url}/oauth/token",
            data=refresh_data,
            timeout=10,
            headers={'User-Agent': 'CorgiRecommender/1.0'}
        )
        
        response.raise_for_status()
        token_info = response.json()
        
        # Calculate new expiration time
        expires_in = token_info.get('expires_in', 3600)
        new_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Update database with new token data
        access_token = token_info['access_token']
        scope = token_info.get('scope', 'read write follow')
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE user_identities 
                SET access_token = %s,
                    token_expires_at = %s,
                    token_scope = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (access_token, new_expires_at, scope, user_id))
            
            if cur.rowcount == 0:
                logger.error(f"No user found to update for user_id: {user_id}")
                return {
                    'success': False,
                    'message': 'User not found for token update'
                }
                
            conn.commit()
        
        logger.info(f"Token refreshed successfully for user {user_id}")
        return {
            'success': True,
            'message': 'Token refreshed successfully',
            'new_token': access_token,
            'expires_at': new_expires_at
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during token refresh for {user_id}: {e}")
        return {
            'success': False,
            'message': f'Failed to refresh token: {str(e)}'
        }
    
    except Exception as e:
        logger.error(f"Unexpected error during token refresh for {user_id}: {e}")
        return {
            'success': False,
            'message': f'Failed to refresh token: {str(e)}'
        }

def handle_refresh_failure(user_id: str, error_type: str, error_details: str = "") -> None:
    """
    Handle various refresh failure scenarios.
    
    Args:
        user_id: The internal user ID
        error_type: Type of error (e.g., 'invalid_grant', 'network_error')
        error_details: Additional error details
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            if error_type in ['invalid_grant', 'invalid_token', 'invalid_request']:
                # Clear invalid tokens - user needs to re-authenticate
                cur.execute("""
                    UPDATE user_identities 
                    SET access_token = NULL, 
                        refresh_token = NULL,
                        token_expires_at = NULL
                    WHERE user_id = %s
                """, (user_id,))
                
                conn.commit()
                logger.warning(f"Cleared invalid tokens for user {user_id} - re-authentication required")
                
            else:
                # Temporary error - log and retry later
                logger.error(f"Temporary refresh error for {user_id}: {error_type} - {error_details}")
                
    except Exception as e:
        logger.error(f"Error handling refresh failure for {user_id}: {e}")

def get_users_with_expiring_tokens(hours_ahead: int = 1) -> list:
    """
    Get list of users whose tokens will expire within the specified time.
    
    Args:
        hours_ahead: How many hours ahead to look for expiring tokens
        
    Returns:
        List of user dictionaries with expiring tokens
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            expiry_threshold = datetime.utcnow() + timedelta(hours=hours_ahead)
            
            cur.execute("""
                SELECT user_id, access_token, refresh_token, instance_url
                FROM user_identities
                WHERE token_expires_at IS NOT NULL
                AND token_expires_at < %s
                AND refresh_token IS NOT NULL
                AND access_token IS NOT NULL
            """, (expiry_threshold,))
            
            results = cur.fetchall()
            return [
                {
                    'user_id': row[0],
                    'access_token': row[1], 
                    'refresh_token': row[2],
                    'instance': row[3]
                }
                for row in results
            ]
            
    except Exception as e:
        logger.error(f"Error getting users with expiring tokens: {e}")
        return []

def refresh_expiring_tokens_batch(hours_ahead: int = 1) -> Dict[str, Any]:
    """
    Refresh tokens for all users whose tokens will expire soon.
    
    Args:
        hours_ahead: How many hours ahead to look for expiring tokens
        
    Returns:
        Dict with refresh results
    """
    users_to_refresh = get_users_with_expiring_tokens(hours_ahead)
    
    if not users_to_refresh:
        logger.info("No tokens need refreshing")
        return {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'failures': []
        }
    
    logger.info(f"Found {len(users_to_refresh)} users with expiring tokens")
    
    failures = []
    successful = 0
    failed = 0
    
    for user_data in users_to_refresh:
        user_id = user_data['user_id']
        
        # Check if user has refresh token
        if not user_data.get('refresh_token'):
            logger.warning(f"User {user_id} has no refresh token, skipping")
            failed += 1
            failures.append({
                'user_id': user_id,
                'message': 'No refresh token available'
            })
            continue
        
        refresh_result = refresh_access_token(
            user_id, 
            user_data['refresh_token'], 
            user_data['instance']
        )
        
        if refresh_result['success']:
            successful += 1
        else:
            failed += 1
            failures.append({
                'user_id': user_id,
                'message': refresh_result.get('message', 'Unknown error')
            })
            # Handle the failure appropriately
            error_type = refresh_result.get('message', 'unknown')
            handle_refresh_failure(user_id, 'refresh_failed', error_type)
    
    summary = {
        'processed': len(users_to_refresh),
        'successful': successful,
        'failed': failed,
        'failures': failures
    }
    
    logger.info(f"Token refresh batch completed: {successful} successful, {failed} failed")
    return summary 