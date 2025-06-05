"""
Tests for the interaction routes.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from config import API_PREFIX

from utils.privacy import generate_user_alias


@pytest.fixture
def mock_db_conn():
    """Create a mock database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.__enter__.return_value = mock_cursor
    return mock_conn, mock_cursor


@patch('routes.interactions.get_db_connection')
def test_log_interaction_success(mock_get_db, client, mock_db_conn):
    """Test successful interaction logging."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_cursor.fetchone.return_value = None  # No existing interaction
    
    # Test data
    test_data = {
        "user_id": "user123",
        "post_id": "post456",
        "action_type": "favorite",
        "context": {"source": "test"}
    }
    
    # Make request
    response = client.post(f'{API_PREFIX}/interactions', 
                         json=test_data,
                         content_type='application/json')
    
    # Verify response - the app returns 201 CREATED for successful interaction creation
    assert response.status_code == 201
    data = json.loads(response.data)
    assert "Interaction logged successfully" in data["message"]
    assert data["status"] == "ok"


@patch('routes.interactions.get_db_connection')
def test_log_interaction_missing_fields(mock_get_db, client):
    """Test interaction logging with missing fields."""
    # Test with missing fields
    test_data = {"user_id": "user123"}  # Missing post_id and action_type

    # Make request
    response = client.post(f'{API_PREFIX}/interactions',
                         json=test_data,
                         content_type='application/json')

    # Verify response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "Missing required fields" in data["error"]
    # The new validation provides required fields list instead of received fields
    assert "required" in data
    assert "post_id" in str(data["required"])
    assert "action_type" in str(data["required"])


@patch('utils.privacy.generate_user_alias')
@patch('routes.interactions.get_db_connection')
def test_log_interaction_incorrect_types(mock_get_db, mock_generate_alias, client):
    """Test interaction logging with incorrect field types."""
    # Integer user_id now gets caught by sanitize_string() which returns None for non-strings
    test_data = {"user_id": 123, "post_id": "post456", "action_type": "favorite"}

    response = client.post(f'{API_PREFIX}/interactions',
                         json=test_data,
                         content_type='application/json')

    # The enhanced security validation now catches this early and returns 400
    # sanitize_string(123) returns None, triggering "Invalid user_id format or content"
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Invalid user_id format or content" in data["error"]


@patch('routes.interactions.get_db_connection')
def test_log_interaction_empty_payload(mock_get_db, client):
    """Test interaction logging with an empty JSON payload."""
    response = client.post(f'{API_PREFIX}/interactions',
                         json={},
                         content_type='application/json')

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    # Empty payload now triggers the oversized/invalid payload check first
    assert "Invalid or oversized request payload" in data["error"]


@patch('routes.interactions.get_db_connection')
def test_log_interaction_invalid_action_type(mock_get_db, client):
    """Test interaction logging with an invalid action_type."""
    test_data = {
        "user_id": "user123",
        "post_id": "post456",
        "action_type": "invented_action", # Not in ALLOWED_ACTIONS
        "context": {"source": "test"}
    }
    response = client.post(f'{API_PREFIX}/interactions',
                         json=test_data,
                         content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Invalid action_type" in data["error"]
    assert "allowed_values" in data # Check that server suggests valid ones
    mock_get_db.assert_not_called()


@patch('routes.interactions.get_db_connection')
def test_get_interactions_by_post(mock_get_db, client, mock_db_conn):
    """Test getting interactions for a specific post."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_cursor.fetchall.return_value = [
        ("favorite", 5),
        ("reblog", 2),
        ("reply", 3)
    ]
    
    # Make request - use correct URL with API prefix
    response = client.get(f'{API_PREFIX}/interactions/post123')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["post_id"] == "post123"
    assert data["interaction_counts"]["favorites"] == 5
    assert data["interaction_counts"]["reblogs"] == 2
    assert data["interaction_counts"]["replies"] == 3


@patch('routes.interactions.get_user_privacy_level')
@patch('routes.interactions.get_db_connection')
def test_get_user_interactions(mock_get_db, mock_privacy_level, client, mock_db_conn):
    """Test getting all interactions for a user."""
    # Setup mocks
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_privacy_level.return_value = "full"  # Set privacy level to full
    
    from datetime import datetime
    mock_timestamp = datetime.now()
    
    mock_cursor.fetchall.return_value = [
        ("post123", "favorite", {"source": "test"}, mock_timestamp),
        ("post456", "reblog", {}, mock_timestamp)
    ]
    
    # Make request - use correct URL with API prefix
    response = client.get(f'{API_PREFIX}/interactions/user/user123')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["user_id"] == "user123"
    assert len(data["interactions"]) == 2


@patch('routes.interactions.get_user_privacy_level')
@patch('routes.interactions.get_db_connection')
def test_get_user_interactions_limited_privacy(mock_get_db, mock_privacy_level, client, mock_db_conn):
    """Test getting interactions for a user with limited privacy."""
    # Setup mocks
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_privacy_level.return_value = "limited"  # Set privacy level to limited
    
    # Mock data - only action type counts for limited privacy
    mock_cursor.fetchall.return_value = [
        ("favorite", 5),
        ("reblog", 2)
    ]
    
    # Make request - use correct URL with API prefix
    response = client.get(f'{API_PREFIX}/interactions/user/user123')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["user_id"] == "user123"
    assert "interaction_counts" in data
    # For limited privacy, API returns raw action_type keys (not pluralized)
    assert data["interaction_counts"]["favorite"] == 5
    assert data["interaction_counts"]["reblog"] == 2


@patch('routes.interactions.get_user_privacy_level')
@patch('routes.interactions.get_db_connection')
def test_get_user_interactions_no_privacy(mock_get_db, mock_privacy_level, client):
    """Test getting interactions for a user with no privacy setting."""
    # Setup mocks
    mock_get_db.return_value = MagicMock()
    mock_privacy_level.return_value = "none"  # Set privacy level to none
    
    # Make request - use correct URL with API prefix
    response = client.get(f'{API_PREFIX}/interactions/user/user123')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["user_id"] == "user123"
    assert "message" in data  # Should return a message about privacy


@patch('routes.interactions.get_db_connection')
def test_get_user_favourites(mock_get_db, client, mock_db_conn):
    """Test getting favourites for a user."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    
    from datetime import datetime
    mock_timestamp = datetime.now()
    
    mock_cursor.fetchall.return_value = [
        ("post123", mock_timestamp),
        ("post456", mock_timestamp)
    ]
    
    # Make request - use correct URL with API prefix
    response = client.get(f'{API_PREFIX}/interactions/favourites?user_id=user123')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["user_id"] == "user123"
    assert len(data["favourites"]) == 2
    assert data["favourites"][0]["post_id"] == "post123"
    assert data["favourites"][1]["post_id"] == "post456"