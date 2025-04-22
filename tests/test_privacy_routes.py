"""
Tests for the privacy routes.
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


@patch('routes.privacy.get_user_privacy_level')
@patch('routes.privacy.get_db_connection')
def test_get_privacy_settings(mock_get_db, mock_get_privacy, client, mock_db_conn):
    """Test getting privacy settings for a user."""
    # Setup mocks
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_get_privacy.return_value = "limited"
    
    # Make request
    response = client.get(f'{API_PREFIX}/privacy/settings?user_id=user123')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["user_id"] == "user123"
    assert data["tracking_level"] == "limited"
    
    # Verify DB interaction
    mock_get_privacy.assert_called_with(mock_conn, "user123")


@patch('routes.privacy.get_db_connection')
def test_get_privacy_settings_missing_user_id(mock_get_db, client):
    """Test getting privacy settings without user_id."""
    # Make request without user_id
    response = client.get(f'{API_PREFIX}/privacy/settings')
    
    # Verify response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "Missing required parameter" in data["error"]
    
    # Verify no DB interaction
    mock_get_db.assert_not_called()


@patch('routes.privacy.update_user_privacy_level')
@patch('routes.privacy.get_db_connection')
def test_update_privacy_settings_success(mock_get_db, mock_update_privacy, client, mock_db_conn):
    """Test successful privacy settings update."""
    # Setup mocks
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_update_privacy.return_value = True
    
    # Test data
    test_data = {
        "user_id": "user123",
        "tracking_level": "none"
    }
    
    # Make request
    response = client.post(f'{API_PREFIX}/privacy/settings', 
                          json=test_data,
                          content_type='application/json')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "Privacy settings updated successfully" in data["message"]
    assert data["user_id"] == "user123"
    assert data["tracking_level"] == "none"
    
    # Verify DB interaction
    mock_update_privacy.assert_called_with(mock_conn, "user123", "none")


@patch('routes.privacy.update_user_privacy_level')
@patch('routes.privacy.get_db_connection')
def test_update_privacy_settings_invalid_level(mock_get_db, mock_update_privacy, client):
    """Test update with invalid privacy level."""
    # Test data with invalid tracking_level
    test_data = {
        "user_id": "user123",
        "tracking_level": "invalid_level"
    }
    
    # Make request
    response = client.post(f'{API_PREFIX}/privacy/settings', 
                          json=test_data,
                          content_type='application/json')
    
    # Verify response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "Invalid tracking_level value" in data["error"]
    assert "valid_values" in data
    
    # Verify no DB interaction
    mock_update_privacy.assert_not_called()


@patch('routes.privacy.update_user_privacy_level')
@patch('routes.privacy.get_db_connection')
def test_update_privacy_settings_missing_fields(mock_get_db, mock_update_privacy, client):
    """Test update with missing fields."""
    # Test data with missing tracking_level
    test_data = {
        "user_id": "user123"
    }
    
    # Make request
    response = client.post(f'{API_PREFIX}/privacy/settings', 
                          json=test_data,
                          content_type='application/json')
    
    # Verify response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "Missing required field: tracking_level" in data["error"]
    
    # Verify no DB interaction
    mock_update_privacy.assert_not_called()