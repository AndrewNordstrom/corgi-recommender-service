"""
Tests for the privacy utilities.
"""

import pytest
from unittest.mock import patch, MagicMock

from utils.privacy import generate_user_alias, get_user_privacy_level, update_user_privacy_level


def test_generate_user_alias():
    """Test user alias generation is consistent."""
    # Test that the same user ID always produces the same alias
    user_id = "test_user_123"
    alias1 = generate_user_alias(user_id)
    alias2 = generate_user_alias(user_id)
    
    assert alias1 == alias2
    assert len(alias1) == 64  # SHA-256 produces 64 hex chars
    
    # Test that different user IDs produce different aliases
    another_user_id = "test_user_456"
    another_alias = generate_user_alias(another_user_id)
    assert alias1 != another_alias


@pytest.fixture
def mock_db_conn():
    """Create a mock database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.__enter__.return_value = mock_cursor
    return mock_conn, mock_cursor


def test_get_user_privacy_level_existing(mock_db_conn):
    """Test getting existing privacy level."""
    mock_conn, mock_cursor = mock_db_conn
    
    # Setup mock to return an existing privacy level
    mock_cursor.fetchone.return_value = ("limited",)
    
    # Get privacy level
    level = get_user_privacy_level(mock_conn, "test_user_123")
    
    # Verify result
    assert level == "limited"
    
    # Verify correct query was called - detect parameter style from actual call
    actual_query, actual_params = mock_cursor.execute.call_args[0]
    assert actual_params == ("test_user_123",)
    
    # The query should contain the correct placeholder style
    assert "SELECT tracking_level FROM privacy_settings WHERE user_id = " in actual_query
    assert ("?" in actual_query) or ("%s" in actual_query)  # Either SQLite or PostgreSQL style


def test_get_user_privacy_level_default(mock_db_conn):
    """Test getting default privacy level when none exists."""
    mock_conn, mock_cursor = mock_db_conn
    
    # Setup mock to return no existing privacy level
    mock_cursor.fetchone.return_value = None
    
    # Get privacy level
    level = get_user_privacy_level(mock_conn, "test_user_456")
    
    # Verify default level is returned
    assert level == "full"  # The actual default in the code
    
    # Verify correct query was called - detect parameter style from actual call
    actual_query, actual_params = mock_cursor.execute.call_args[0]
    assert actual_params == ("test_user_456",)
    
    # The query should contain the correct placeholder style
    assert "SELECT tracking_level FROM privacy_settings WHERE user_id = " in actual_query
    assert ("?" in actual_query) or ("%s" in actual_query)  # Either SQLite or PostgreSQL style


def test_update_user_privacy_level_success(mock_db_conn):
    """Test successful privacy level update."""
    mock_conn, mock_cursor = mock_db_conn
    
    # Update privacy level
    result = update_user_privacy_level(mock_conn, "test_user_123", "none")
    
    # Verify success
    assert result is True
    
    # Verify DB operations happened - the exact SQL depends on database type
    # So we just verify that execute was called with the right parameters
    assert mock_cursor.execute.called
    
    # Check execute calls specifically
    execute_calls = mock_cursor.execute.call_args_list
    
    # Should have at least one call with our user_id and tracking_level
    found_update_call = False
    for call in execute_calls:
        if call.args and len(call.args) >= 2:  # call has query and params
            params = call.args[1]
            if isinstance(params, tuple) and "test_user_123" in params and "none" in params:
                found_update_call = True
                break
    
    assert found_update_call, f"Expected update call with test_user_123 and none, got execute calls: {execute_calls}"
    
    # Verify commit was called
    mock_conn.commit.assert_called_once()


def test_update_user_privacy_level_invalid(mock_db_conn):
    """Test update with invalid privacy level."""
    mock_conn, mock_cursor = mock_db_conn
    
    # Try to update with invalid level
    result = update_user_privacy_level(mock_conn, "test_user_123", "invalid_level")
    
    # Verify failure
    assert result is False
    
    # Verify no DB operations
    mock_cursor.execute.assert_not_called()
    mock_conn.commit.assert_not_called()


def test_update_user_privacy_level_db_error(mock_db_conn):
    """Test handling of database error during update."""
    mock_conn, mock_cursor = mock_db_conn
    
    # Setup mock to raise exception
    mock_cursor.execute.side_effect = Exception("Database error")
    
    # Try to update
    result = update_user_privacy_level(mock_conn, "test_user_123", "none")
    
    # Verify failure
    assert result is False
    
    # Verify rollback was called
    mock_conn.rollback.assert_called_once()