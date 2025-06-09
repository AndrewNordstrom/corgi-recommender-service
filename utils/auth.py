"""
Authentication related utility functions.
"""
import logging
import functools
from datetime import datetime, timedelta
from flask import request, jsonify, g
from db.connection import get_db_connection

logger = logging.getLogger(__name__)

def require_authentication(f):
    """
    Decorator to require authentication for a route.
    
    Args:
        f: Flask route function
        
    Returns:
        Decorated function that checks authentication
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key in headers
        api_key = request.headers.get('X-API-Key')
        auth_header = request.headers.get('Authorization')
        
        user = None
        
        if api_key:
            # Simple API key validation (would be more robust in production)
            if api_key in ['admin-key', 'user-key', 'crawler-key']:
                user = {'api_key': api_key}
        elif auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            user = get_user_by_token(token)
        
        if not user:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please provide valid API key or Bearer token'
            }), 401
        
        # Store user in Flask's g object for use in the route
        g.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function

def get_user_by_token(token: str) -> dict | None:
    """
    Look up user information based on an OAuth token with expiration validation.
    
    Args:
        token: The OAuth token to look up
        
    Returns:
        dict: User information including instance_url and user_id, or None if not found/expired/error.
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, instance_url, access_token, token_expires_at, created_at
                FROM user_identities 
                WHERE access_token = %s
            """, (token,))
            
            result = cur.fetchone()
            if result:
                user_id, instance_url, access_token, token_expires_at, created_at = result
                
                # Check if token is expired
                if token_expires_at:
                    try:
                        # Try PostgreSQL ISO format first
                        expires_dt = datetime.fromisoformat(str(token_expires_at).replace('T', ' '))
                    except (ValueError, AttributeError):
                        try:
                            expires_dt = datetime.strptime(token_expires_at, "%Y-%m-%d %H:%M:%S.%f")
                        except ValueError:
                            try:
                                expires_dt = datetime.strptime(token_expires_at, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                logger.warning(f"Could not parse token expiration: {token_expires_at}")
                                return None
                    
                    if datetime.utcnow() > expires_dt:
                        logger.info(f"Token for user {user_id} has expired at {token_expires_at}")
                        return None
                
                # Return user info
                return {
                    'user_id': user_id,
                    'instance_url': instance_url,
                    'access_token': access_token
                }
            else:
                logger.debug(f"Token {token[:10]}... not found in database")
                return None
                
    except Exception as e:
        logger.error(f"Database error looking up token: {e}")
        return None


def set_token_expiration(token: str, expires_in_hours: int = 24) -> bool:
    """
    Set or update the expiration time for a token.
    
    Args:
        token: The token to update
        expires_in_hours: Hours from now when token should expire
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE user_identities 
                SET token_expires_at = %s
                WHERE access_token = %s
            """, (expires_at.strftime("%Y-%m-%d %H:%M:%S.%f"), token))
            
            if cur.rowcount > 0:
                conn.commit()
                logger.info(f"Token expiration set to {expires_at}")
                return True
            else:
                logger.warning(f"Token {token[:10]}... not found for expiration update")
                return False
                
    except Exception as e:
        logger.error(f"Error setting token expiration: {e}")
        return False


def revoke_token(token: str) -> bool:
    """
    Revoke a token by removing it from the database.
    
    Args:
        token: The token to revoke
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM user_identities 
                WHERE access_token = %s
            """, (token,))
            
            if cur.rowcount > 0:
                conn.commit()
                logger.info(f"Token {token[:10]}... revoked successfully")
                return True
            else:
                logger.warning(f"Token {token[:10]}... not found for revocation")
                return False
                
    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        return False


def get_token_info(token: str) -> dict | None:
    """
    Get detailed information about a token.
    
    Args:
        token: The token to look up
        
    Returns:
        dict: Token information or None if not found
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, instance_url, access_token, token_expires_at, created_at
                FROM user_identities 
                WHERE access_token = %s
            """, (token,))
            
            result = cur.fetchone()
            if result:
                # Handle variable number of columns returned from database
                if len(result) == 5:
                    user_id, instance_url, access_token, token_expires_at, created_at = result
                elif len(result) == 4:
                    # Assume missing created_at
                    user_id, instance_url, access_token, token_expires_at = result
                    created_at = None
                else:
                    logger.error(f"Unexpected number of columns returned: {len(result)}")
                    return None
                
                # Calculate time until expiration
                expires_in = None
                is_expired = False
                
                if token_expires_at:
                    try:
                        # Try PostgreSQL ISO format first
                        expires_dt = datetime.fromisoformat(str(token_expires_at).replace('T', ' '))
                    except (ValueError, AttributeError):
                        try:
                            expires_dt = datetime.strptime(token_expires_at, "%Y-%m-%d %H:%M:%S.%f")
                        except ValueError:
                            try:
                                expires_dt = datetime.strptime(token_expires_at, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                expires_dt = None
                    
                    if expires_dt:
                        now = datetime.utcnow()
                        if expires_dt > now:
                            expires_in = int((expires_dt - now).total_seconds())
                        else:
                            is_expired = True
                
                return {
                    'user_id': user_id,
                    'instance_url': instance_url,
                    'access_token': access_token,
                    'token_expires_at': token_expires_at,
                    'created_at': created_at,
                    'expires_in_seconds': expires_in,
                    'is_expired': is_expired
                }
            else:
                return None
                
    except Exception as e:
        logger.error(f"Error getting token info: {e}")
        return None 