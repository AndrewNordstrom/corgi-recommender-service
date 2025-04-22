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
    
    # Verify DB query
    mock_cursor.execute.assert_called_with(
        "SELECT tracking_level FROM privacy_settings WHERE user_id = %s", 
        ("test_user_123",)
    )


def test_get_user_privacy_level_default(mock_db_conn):
    """Test getting default privacy level when none exists."""
    mock_conn, mock_cursor = mock_db_conn
    
    # Setup mock to return no results
    mock_cursor.fetchone.return_value = None
    
    # Get privacy level
    level = get_user_privacy_level(mock_conn, "test_user_123")
    
    # Verify default is returned
    assert level == "full"
    
    # Verify DB query
    mock_cursor.execute.assert_called_with(
        "SELECT tracking_level FROM privacy_settings WHERE user_id = %s", 
        ("test_user_123",)
    )


def test_update_user_privacy_level_success(mock_db_conn):
    """Test successful privacy level update."""
    mock_conn, mock_cursor = mock_db_conn
    
    # Update privacy level
    result = update_user_privacy_level(mock_conn, "test_user_123", "none")
    
    # Verify success
    assert result is True
    
    # Verify DB operations
    mock_cursor.execute.assert_called_with(
        "INSERT INTO privacy_settings (user_id, tracking_level) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET tracking_level = EXCLUDED.tracking_level",
        ("test_user_123", "none")
    )
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