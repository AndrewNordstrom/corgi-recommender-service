"""
Tests for the posts routes.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from config import API_PREFIX


@pytest.fixture
def mock_db_conn():
    """Create a mock database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.__enter__.return_value = mock_cursor
    return mock_conn, mock_cursor


def test_get_posts(client, seed_test_data):
    """Test retrieving posts list."""
    # Make request
    response = client.get(f'{API_PREFIX}/posts')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= 1
    
    # Find the post with favourites_count 10 (our test data)
    post_with_10_favs = next((p for p in data if p.get("favourites_count") == 10), None)
    assert post_with_10_favs is not None
    assert post_with_10_favs["favourites_count"] == 10


def test_get_posts_with_mastodon_data(client, seed_test_data):
    """Test retrieving posts list with mastodon post data."""
    # Make request
    response = client.get(f'{API_PREFIX}/posts')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= 1
    # Find the post with favourites_count 42 (our test data)
    post_with_42_favs = next((p for p in data if p.get("favourites_count") == 42), None)
    assert post_with_42_favs is not None
    assert post_with_42_favs["favourites_count"] == 42  # Should use mastodon data


@patch('routes.posts.get_cursor')
@patch('routes.posts.get_db_connection')
def test_create_post(mock_get_db, mock_get_cursor, client, mock_db_conn):
    """Test creating a new post."""
    # Setup mock
    mock_conn, mock_cursor_fixture = mock_db_conn
    mock_get_db.return_value.__enter__.return_value = mock_conn
    mock_get_cursor.return_value.__enter__.return_value = mock_cursor_fixture
    mock_cursor_fixture.fetchone.return_value = ("post123",)
    
    # Test data
    test_data = {
        "post_id": "post123",
        "author_id": "author456",
        "author_name": "Author Name",
        "content": "Test post content",
        "created_at": "2023-01-01T12:00:00Z",
        "interaction_counts": {"favorites": 0}
    }
    
    # Make request - use correct API prefix
    response = client.post(f'{API_PREFIX}/posts', 
                          json=test_data,
                          content_type='application/json')
    
    # Verify response
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["message"] == "Post saved successfully"
    assert data["post_id"] == "post123"


@patch('routes.posts.get_cursor')
@patch('routes.posts.get_db_connection')
def test_create_post_missing_fields(mock_get_db, mock_get_cursor, client):
    """Test creating a post with missing required fields."""
    # Test with missing author_id for a new post
    test_data = {"post_id": "post123"}
    
    # Setup mock connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value.__enter__.return_value = mock_conn
    mock_get_cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # Post doesn't exist (new post)
    
    # Make request - use correct API prefix
    response = client.post(f'{API_PREFIX}/posts', 
                          json=test_data,
                          content_type='application/json')
    
    # Verify response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "Missing required author_id field" in data["error"]


@patch('routes.posts.get_cursor')
@patch('routes.posts.get_db_connection')
def test_get_post_by_id(mock_get_db, mock_get_cursor, client, mock_db_conn):
    """Test retrieving a specific post by ID."""
    # Setup mock
    mock_conn, mock_cursor_fixture = mock_db_conn
    mock_get_db.return_value.__enter__.return_value = mock_conn
    mock_get_cursor.return_value.__enter__.return_value = mock_cursor_fixture
    
    # Mock data for SQLite path (5 fields: post_id, author_id, content, created_at, metadata)
    import json
    metadata = {
        "author_name": "Author Name",
        "content_type": "text", 
        "interaction_counts": {"favorites": 10, "reblogs": 5},
        "mastodon_post": None
    }
    mock_cursor_fixture.fetchone.return_value = (
        "post123",                          # post_id
        "author456",                        # author_id
        "Post content",                     # content
        "2023-01-01T12:00:00",              # created_at
        json.dumps(metadata)                # metadata (JSON string)
    )
    
    # Make request - use correct API prefix
    response = client.get(f'{API_PREFIX}/posts/post123')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["id"] == "post123"
    assert data["author_id"] == "author456"
    assert data["favourites_count"] == 10


@patch('routes.posts.get_db_connection')
def test_get_post_not_found(mock_get_db, client, mock_db_conn):
    """Test retrieving a non-existent post."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_cursor.fetchone.return_value = None  # Post not found
    
    # Make request - use correct API prefix
    response = client.get(f'{API_PREFIX}/posts/nonexistent')
    
    # Verify response - check for 404 but without assuming specific message format
    assert response.status_code == 404


@patch('routes.posts.get_db_connection')
def test_get_posts_by_author(mock_get_db, client, mock_db_conn):
    """Test retrieving posts by author."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    
    # Mock posts data
    mock_cursor.fetchall.return_value = [
        ("post123", "author456", "Author Name", "Post content 1", "text",
         None, {"favorites": 10}, None),
        ("post789", "author456", "Author Name", "Post content 2", "text",
         None, {"favorites": 5}, None),
    ]
    
    # Make request - use correct API prefix
    response = client.get(f'{API_PREFIX}/posts/author/author456')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert data[0]["id"] == "post123"
    assert data[1]["id"] == "post789"


def test_get_trending_posts(client, seed_test_data):
    """Test retrieving trending posts."""
    # Make request - use correct API prefix
    response = client.get(f'{API_PREFIX}/posts/trending')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= 1
    # Find the post with favourites_count 100 (our test data)
    post_with_100_favs = next((p for p in data if p.get("favourites_count") == 100), None)
    assert post_with_100_favs is not None
    assert post_with_100_favs["favourites_count"] == 100