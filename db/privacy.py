"""
Database Privacy Utilities for the Corgi Recommender Service.

This module provides privacy-preserving utilities for database operations,
including user alias generation and data anonymization functions.
"""

import hashlib
import logging
from typing import Optional
import secrets

logger = logging.getLogger(__name__)

def generate_user_alias(user_id: str, salt: Optional[str] = None) -> str:
    """
    Generate a privacy-preserving alias for a user ID.
    
    This function creates a deterministic but non-reversible alias for user IDs
    to protect user privacy while maintaining consistency for analytics.
    
    Args:
        user_id: The original user ID to generate an alias for
        salt: Optional salt for the hash (if not provided, uses a default)
        
    Returns:
        str: A privacy-preserving alias for the user
    """
    if not user_id:
        return "anonymous"
    
    # Use a default salt if none provided (in production this should be from config)
    if salt is None:
        salt = "corgi_privacy_salt_2024"
    
    # Create a hash of the user ID with salt
    hasher = hashlib.sha256()
    hasher.update(f"{salt}:{user_id}".encode('utf-8'))
    hash_hex = hasher.hexdigest()
    
    # Return a shortened, prefixed alias
    return f"alias_{hash_hex[:16]}"

def anonymize_user_data(user_data: dict) -> dict:
    """
    Anonymize user data by removing or hashing personally identifiable information.
    
    Args:
        user_data: Dictionary containing user information
        
    Returns:
        dict: Anonymized version of the user data
    """
    if not user_data:
        return {}
    
    anonymized = user_data.copy()
    
    # Remove direct identifiers
    sensitive_fields = ['email', 'real_name', 'phone', 'address', 'ip_address']
    for field in sensitive_fields:
        if field in anonymized:
            del anonymized[field]
    
    # Hash username if present
    if 'username' in anonymized:
        anonymized['username_hash'] = generate_user_alias(anonymized['username'])
        del anonymized['username']
    
    # Hash user_id if present
    if 'user_id' in anonymized:
        anonymized['user_alias'] = generate_user_alias(anonymized['user_id'])
        del anonymized['user_id']
    
    return anonymized

def generate_session_token(length: int = 32) -> str:
    """
    Generate a secure random session token.
    
    Args:
        length: Length of the token in bytes
        
    Returns:
        str: Secure random token as hex string
    """
    return secrets.token_hex(length)

def sanitize_content(content: str) -> str:
    """
    Sanitize content by removing potentially sensitive information.
    
    Args:
        content: The content to sanitize
        
    Returns:
        str: Sanitized content
    """
    if not content:
        return ""
    
    # Basic email pattern removal
    import re
    
    # Remove email addresses
    content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[email removed]', content)
    
    # Remove phone numbers (basic pattern)
    content = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[phone removed]', content)
    
    # Remove URLs
    content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '[url removed]', content)
    
    return content

def validate_privacy_level(privacy_level: str) -> bool:
    """
    Validate that a privacy level is one of the allowed values.
    
    Args:
        privacy_level: The privacy level to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    valid_levels = {'none', 'limited', 'full', 'public'}
    return privacy_level.lower() in valid_levels

def get_privacy_compliant_fields(privacy_level: str, all_fields: list) -> list:
    """
    Get the list of fields that are compliant with the given privacy level.
    
    Args:
        privacy_level: The privacy level ('none', 'limited', 'full', 'public')
        all_fields: List of all available fields
        
    Returns:
        list: Fields that are allowed for the given privacy level
    """
    privacy_level = privacy_level.lower()
    
    # Define which fields are allowed at each privacy level
    field_restrictions = {
        'none': [],  # No fields allowed
        'limited': ['post_id', 'created_at', 'language'],  # Only basic metadata
        'full': ['post_id', 'created_at', 'language', 'content', 'author_alias'],  # Most fields but anonymized
        'public': all_fields  # All fields allowed
    }
    
    allowed_fields = field_restrictions.get(privacy_level, [])
    
    # Return intersection of allowed fields and available fields
    return [field for field in all_fields if field in allowed_fields]

def hash_sensitive_identifier(identifier: str, hash_type: str = 'sha256') -> str:
    """
    Hash a sensitive identifier using the specified algorithm.
    
    Args:
        identifier: The identifier to hash
        hash_type: The hash algorithm to use ('sha256', 'md5', 'sha1')
        
    Returns:
        str: Hashed identifier
    """
    if not identifier:
        return ""
    
    if hash_type == 'sha256':
        return hashlib.sha256(identifier.encode('utf-8')).hexdigest()
    elif hash_type == 'md5':
        return hashlib.md5(identifier.encode('utf-8')).hexdigest()
    elif hash_type == 'sha1':
        return hashlib.sha1(identifier.encode('utf-8')).hexdigest()
    else:
        # Default to SHA256
        return hashlib.sha256(identifier.encode('utf-8')).hexdigest()

def is_personally_identifiable(field_name: str) -> bool:
    """
    Check if a field name represents personally identifiable information.
    
    Args:
        field_name: The field name to check
        
    Returns:
        bool: True if the field is considered PII, False otherwise
    """
    pii_fields = {
        'email', 'phone', 'address', 'real_name', 'full_name',
        'ssn', 'social_security', 'credit_card', 'passport',
        'driver_license', 'ip_address', 'mac_address'
    }
    
    return field_name.lower() in pii_fields or any(pii in field_name.lower() for pii in pii_fields) 