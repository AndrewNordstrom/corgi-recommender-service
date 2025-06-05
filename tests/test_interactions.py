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


@patch("routes.interactions.get_db_connection")
def test_log_interaction_success(mock_get_db, client, mock_db_conn):
    """Test successful interaction logging."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_cursor.fetchone.return_value = (1,)  # Return an ID

    # Test data
    test_data = {
        "user_id": "user123",
        "post_id": "post456",
        "action_type": "favorite",
        "context": {"source": "test"},
    }

    # Make request
    response = client.post(
        f"{API_PREFIX}/interactions", json=test_data, content_type="application/json"
    )

    # Verify response
    assert response.status_code == 201
    data = json.loads(response.data)
    assert "Interaction logged successfully" in data["message"]
    assert "id" in data

    # Verify DB operations
    user_alias = generate_user_alias(test_data["user_id"])
    mock_cursor.execute.assert_any_call(
        "SELECT id FROM interactions WHERE user_alias = %s AND post_id = %s AND action_type = %s",
        (user_alias, test_data["post_id"], test_data["action_type"]),
    )


@patch("routes.interactions.get_db_connection")
def test_log_interaction_missing_fields(mock_get_db, client):
    """Test interaction logging with missing fields."""
    # Test with missing fields
    test_data = {"user_id": "user123"}  # Missing post_id and action_type

    # Make request
    response = client.post(
        f"{API_PREFIX}/interactions", json=test_data, content_type="application/json"
    )

    # Verify response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "Missing required fields" in data["error"]
    assert not data["received"]["post_id"]
    assert not data["received"]["action_type"]

    # Verify DB was not called
    mock_get_db.assert_not_called()


@patch("routes.interactions.get_db_connection")
def test_get_interactions_by_post(mock_get_db, client, mock_db_conn):
    """Test getting interactions for a specific post."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_cursor.fetchall.return_value = [("favorite", 5), ("reblog", 2), ("reply", 3)]

    # Make request
    response = client.get("/v1/interactions/post123")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["post_id"] == "post123"
    assert data["interaction_counts"]["favorites"] == 5
    assert data["interaction_counts"]["reblogs"] == 2
    assert data["interaction_counts"]["replies"] == 3

    # Verify DB operations
    mock_cursor.execute.assert_called_with(
        "SELECT action_type, COUNT(*) as count FROM interactions WHERE post_id = %s GROUP BY action_type",
        ("post123",),
    )


@patch("routes.interactions.get_user_privacy_level")
@patch("routes.interactions.get_db_connection")
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
        ("post456", "reblog", {}, mock_timestamp),
    ]

    # Make request
    response = client.get("/v1/interactions/user/user123")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["user_id"] == "user123"
    assert len(data["interactions"]) == 2
    assert data["interactions"][0]["post_id"] == "post123"
    assert data["interactions"][0]["action_type"] == "favorite"

    # Verify DB operations with pseudonymized user ID
    user_alias = generate_user_alias("user123")
    mock_cursor.execute.assert_called_with(
        "SELECT post_id, action_type, context, created_at FROM interactions WHERE user_alias = %s ORDER BY created_at DESC",
        (user_alias,),
    )


@patch("routes.interactions.get_user_privacy_level")
@patch("routes.interactions.get_db_connection")
def test_get_user_interactions_limited_privacy(
    mock_get_db, mock_privacy_level, client, mock_db_conn
):
    """Test getting interactions for a user with limited privacy."""
    # Setup mocks
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_privacy_level.return_value = "limited"  # Set privacy level to limited

    # Mock data - only action type counts for limited privacy
    mock_cursor.fetchall.return_value = [("favorite", 5), ("reblog", 2)]

    # Make request
    response = client.get("/v1/interactions/user/user123")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["user_id"] == "user123"
    assert data["privacy_level"] == "limited"
    assert "interaction_counts" in data
    assert data["interaction_counts"]["favorite"] == 5
    assert data["interaction_counts"]["reblog"] == 2

    # Verify DB operations with pseudonymized user ID
    user_alias = generate_user_alias("user123")
    mock_cursor.execute.assert_called_with(
        "SELECT action_type, COUNT(*) as count FROM interactions WHERE user_alias = %s GROUP BY action_type",
        (user_alias,),
    )


@patch("routes.interactions.get_user_privacy_level")
@patch("routes.interactions.get_db_connection")
def test_get_user_interactions_no_privacy(mock_get_db, mock_privacy_level, client):
    """Test getting interactions for a user with no privacy setting."""
    # Setup mocks
    mock_get_db.return_value = MagicMock()
    mock_privacy_level.return_value = "none"  # Set privacy level to none

    # Make request
    response = client.get("/v1/interactions/user/user123")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["user_id"] == "user123"
    assert data["privacy_level"] == "none"
    assert data["interactions"] == []
    assert "This user has opted out" in data["message"]


@patch("routes.interactions.get_db_connection")
def test_get_user_favourites(mock_get_db, client, mock_db_conn):
    """Test getting favourites for a user."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn

    from datetime import datetime

    mock_timestamp = datetime.now()

    mock_cursor.fetchall.return_value = [
        ("post123", mock_timestamp),
        ("post456", mock_timestamp),
    ]

    # Make request
    response = client.get("/v1/interactions/favourites?user_id=user123")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["user_id"] == "user123"
    assert len(data["favourites"]) == 2
    assert data["favourites"][0]["post_id"] == "post123"

    # Verify DB operations with pseudonymized user ID
    user_alias = generate_user_alias("user123")
    mock_cursor.execute.assert_called_with(
        "SELECT post_id, created_at FROM interactions WHERE user_alias = %s AND action_type = 'favorite' ORDER BY created_at DESC",
        (user_alias,),
    )
