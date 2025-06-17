"""
Input Sanitization and Security Validation Utilities

This module provides functions to validate and sanitize user inputs
to prevent common security vulnerabilities such as:
- Null byte injection
- Control character injection
- Oversized payloads
- JSON structure attacks
"""

import json
import re
from typing import Any, Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)

# Security constants
MAX_STRING_LENGTH = 255
MAX_JSON_SIZE = 1024 * 1024  # 1MB
MAX_JSON_DEPTH = 10

# Dangerous characters patterns
NULL_BYTE_PATTERN = re.compile(r'\x00')
CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x1F\x7F]')


def sanitize_string(value: Any, field_name: str = "field", max_length: int = MAX_STRING_LENGTH) -> Optional[str]:
    """
    Sanitize and validate a string input for security.
    
    Args:
        value: Input value to sanitize
        field_name: Name of the field for error reporting
        max_length: Maximum allowed length for the string
        
    Returns:
        Sanitized string or None if invalid
        
    Raises:
        ValueError: If the input contains dangerous characters or is invalid
    """
    # Must be a string
    if not isinstance(value, str):
        logger.warning(f"Invalid {field_name} type: expected string, got {type(value)}")
        raise ValueError(f"Invalid {field_name} format or content")
    
    # Check for null bytes
    if NULL_BYTE_PATTERN.search(value):
        logger.warning(f"Null byte detected in {field_name}: {repr(value[:50])}")
        raise ValueError(f"Invalid {field_name} format or content")
    
    # Check for dangerous control characters
    if CONTROL_CHAR_PATTERN.search(value):
        logger.warning(f"Control characters detected in {field_name}: {repr(value[:50])}")
        raise ValueError(f"Invalid {field_name} format or content")
    
    # SECURITY ENHANCEMENT: Check for path traversal patterns
    if '../' in value or '..\\'  in value or '/..' in value or '\\..' in value:
        logger.warning(f"Path traversal pattern detected in {field_name}: {repr(value[:50])}")
        raise ValueError(f"Invalid {field_name} format or content")
    
    # SECURITY ENHANCEMENT: Check for script injection patterns
    dangerous_patterns = [
        '<script', '</script', 'javascript:', 'vbscript:', 'onload=', 'onerror=',
        'data:text/html', 'data:application/', '<iframe', '<object', '<embed',
        'onmouseover=', 'onfocus=', 'onclick=', 'alert(', 'document.cookie', 'window.location'
    ]
    
    value_lower = value.lower()
    for pattern in dangerous_patterns:
        if pattern in value_lower:
            logger.warning(f"Dangerous pattern '{pattern}' detected in {field_name}: {repr(value[:50])}")
            raise ValueError(f"Invalid {field_name} format or content")
    
    # Check length
    if len(value) > max_length:
        logger.warning(f"String too long for {field_name}: {len(value)} > {max_length}")
        raise ValueError(f"Invalid {field_name} format or length")
    
    return value.strip()


def sanitize_post_id(post_id: str) -> str:
    """
    Sanitize a post_id parameter to prevent SQL injection.
    
    Args:
        post_id: Post ID to sanitize
        
    Returns:
        Sanitized post ID
        
    Raises:
        ValueError: If the post ID contains dangerous patterns
    """
    # First apply general string sanitization
    sanitized = sanitize_string(post_id, 'post_id')
    
    # SQL injection patterns to detect
    sql_injection_patterns = [
        r"'.*--",  # SQL comment injection
        r"'.*OR.*'.*'",  # OR injection
        r"'.*UNION.*SELECT",  # UNION injection
        r"DROP\s+TABLE",  # DROP TABLE
        r"DELETE\s+FROM",  # DELETE FROM
        r"INSERT\s+INTO",  # INSERT INTO
        r"UPDATE\s+.*SET",  # UPDATE SET
        r";",  # Statement terminator
    ]
    
    # Check for SQL injection patterns
    for pattern in sql_injection_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            logger.warning(f"SQL injection pattern detected in post_id: {pattern}")
            raise ValueError("Invalid post_id format")
    
    # Check for path traversal
    if '../' in sanitized or '..\\' in sanitized:
        logger.warning("Path traversal attempt in post_id")
        raise ValueError("Invalid post_id format")
    
    # Check for script tags
    if '<script' in sanitized.lower() or '</script' in sanitized.lower():
        logger.warning("Script tag detected in post_id")
        raise ValueError("Invalid post_id format")
    
    return sanitized


def validate_json_payload(data: Dict[str, Any], max_size: int = MAX_JSON_SIZE) -> Dict[str, Any]:
    """
    Validate a JSON payload for security issues.
    
    Args:
        data: JSON data to validate
        max_size: Maximum allowed JSON size in bytes
        
    Returns:
        Validated JSON data
        
    Raises:
        ValueError: If the JSON contains security issues
    """
    if data is None:
        raise ValueError("Invalid or oversized request payload")
    
    # Check serialized size
    try:
        serialized = json.dumps(data)
        if len(serialized.encode('utf-8')) > max_size:
            logger.warning(f"JSON payload too large: {len(serialized)} bytes > {max_size}")
            raise ValueError("Invalid or oversized request payload")
    except (TypeError, ValueError) as e:
        logger.warning(f"JSON serialization error: {e}")
        raise ValueError("Invalid or oversized request payload")
    
    # Check nesting depth
    if _get_json_depth(data) > MAX_JSON_DEPTH:
        logger.warning(f"JSON nesting too deep: > {MAX_JSON_DEPTH} levels")
        raise ValueError("JSON payload exceeds maximum nesting depth")
    
    return data


def _get_json_depth(obj: Any, current_depth: int = 0) -> int:
    """
    Calculate the nesting depth of a JSON object.
    
    Args:
        obj: JSON object to analyze
        current_depth: Current recursion depth
        
    Returns:
        Maximum nesting depth
    """
    if isinstance(obj, dict):
        if not obj:  # Empty dict
            return current_depth
        return max(_get_json_depth(value, current_depth + 1) for value in obj.values())
    elif isinstance(obj, list):
        if not obj:  # Empty list
            return current_depth
        return max(_get_json_depth(item, current_depth + 1) for item in obj)
    else:
        return current_depth


def validate_context_field(context: Any) -> Dict[str, Any]:
    """
    Validate a context field for security issues.
    
    Args:
        context: Context data to validate
        
    Returns:
        Validated context data
        
    Raises:
        ValueError: If the context contains security issues
    """
    if context is None:
        return {}
    
    if not isinstance(context, dict):
        raise ValueError("Context must be a dictionary")
    
    # Check for oversized context
    try:
        serialized = json.dumps(context)
        if len(serialized.encode('utf-8')) > MAX_JSON_SIZE // 2:  # Half of max payload for context
            logger.warning(f"Context field too large: {len(serialized)} bytes")
            raise ValueError("Context field is too large")
    except (TypeError, ValueError):
        raise ValueError("Invalid context format")
    
    # Check nesting depth in context
    if _get_json_depth(context) > MAX_JSON_DEPTH:
        logger.warning("Context field has excessive nesting depth")
        raise ValueError("Context field exceeds maximum nesting depth")
    
    # Check for suspicious keys that might indicate schema pollution
    suspicious_keys = ['admin', 'role', 'administrator', 'is_admin', 'is_superuser', 
                      'privileges', 'permissions', 'access_level', '__proto__', 'constructor', 'prototype']
    for key in context:
        if key.lower() in suspicious_keys:
            logger.warning(f"Suspicious key in context: {key}")
            raise ValueError("Invalid context field content")
    
    # Check for SQL injection patterns in string values
    sql_injection_patterns = [
        r"'.*--",  # SQL comment injection
        r"'.*OR.*'.*'",  # OR injection
        r"'.*UNION.*SELECT",  # UNION injection
        r"DROP\s+TABLE",  # DROP TABLE
        r"DELETE\s+FROM",  # DELETE FROM
        r"INSERT\s+INTO",  # INSERT INTO
        r"UPDATE\s+.*SET",  # UPDATE SET
    ]
    
    # Validate string values in context
    for key, value in context.items():
        if isinstance(value, str):
            # Check for SQL injection patterns
            for pattern in sql_injection_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"SQL injection pattern detected in context[{key}]: {pattern}")
                    raise ValueError("Invalid context field content")
            
            # Check for path traversal
            if '../' in value or '..\\' in value:
                logger.warning(f"Path traversal attempt in context[{key}]")
                raise ValueError("Invalid context field content")
    
    return context


def validate_batch_request(batch_items: Any, max_items: int = 100) -> list:
    """
    Validate a batch request for security issues.
    
    Args:
        batch_items: Batch items to validate
        max_items: Maximum allowed number of items
        
    Returns:
        Validated batch items
        
    Raises:
        ValueError: If the batch request is invalid
    """
    if not isinstance(batch_items, list):
        raise ValueError("Batch request must be a list")
    
    if len(batch_items) > max_items:
        logger.warning(f"Batch request too large: {len(batch_items)} > {max_items}")
        raise ValueError(f"Batch request exceeds maximum size of {max_items} items")
    
    # SQL injection patterns to detect
    sql_injection_patterns = [
        r"'.*--",  # SQL comment injection
        r"'.*OR.*'.*'",  # OR injection
        r"'.*UNION.*SELECT",  # UNION injection
        r"DROP\s+TABLE",  # DROP TABLE
        r"DELETE\s+FROM",  # DELETE FROM
        r"INSERT\s+INTO",  # INSERT INTO
        r"UPDATE\s+.*SET",  # UPDATE SET
    ]
    
    # Validate each item
    validated_items = []
    for i, item in enumerate(batch_items):
        try:
            # Basic string validation for each item
            if isinstance(item, str):
                # Check for SQL injection patterns
                for pattern in sql_injection_patterns:
                    if re.search(pattern, item, re.IGNORECASE):
                        logger.warning(f"SQL injection pattern detected in batch item {i}: {pattern}")
                        raise ValueError(f"Invalid item in batch request at index {i}")
                
                validated_item = sanitize_string(item, f"batch_item[{i}]")
                validated_items.append(validated_item)
            else:
                validated_items.append(item)
        except ValueError as e:
            logger.warning(f"Invalid item in batch at index {i}: {e}")
            raise ValueError(f"Invalid item in batch request at index {i}")
    
    return validated_items


def sanitize_interaction_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize interaction data for security.
    
    Args:
        data: Raw interaction data
        
    Returns:
        Sanitized interaction data
        
    Raises:
        ValueError: If the data contains security issues
    """
    # Check for completely empty payload first
    if not data or len(data) == 0:
        logger.warning("Empty payload received")
        raise ValueError("Invalid or oversized request payload")
    
    # Validate overall payload
    data = validate_json_payload(data)
    
    sanitized = {}
    
    # Sanitize user_id/user_alias
    if 'user_id' in data:
        sanitized['user_id'] = sanitize_string(data['user_id'], 'user_id')
    if 'user_alias' in data:
        sanitized['user_alias'] = sanitize_string(data['user_alias'], 'user_alias')
    
    # Sanitize post_id
    if 'post_id' in data:
        sanitized['post_id'] = sanitize_string(data['post_id'], 'post_id')
    
    # Sanitize action_type
    if 'action_type' in data:
        sanitized['action_type'] = sanitize_string(data['action_type'], 'action_type', max_length=50)
    
    # Sanitize interaction_type (alternative field name)
    if 'interaction_type' in data:
        sanitized['interaction_type'] = sanitize_string(data['interaction_type'], 'interaction_type', max_length=50)
    
    # Validate context
    if 'context' in data:
        sanitized['context'] = validate_context_field(data['context'])
    
    return sanitized 