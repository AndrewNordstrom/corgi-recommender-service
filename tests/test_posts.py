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


@patch("routes.posts.get_db_connection")
def test_get_posts(mock_get_db, client, mock_db_conn):
    """Test retrieving posts list."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn

    # Mock data for a regular post without mastodon data
    mock_cursor.fetchall.return_value = [
        (
            "post123",
            "author456",
            "Author Name",
            "Post content",
            "text",
            None,
            {"favorites": 10, "reblogs": 5},
            None,
        ),
    ]

    # Make request
    response = client.get(f"{API_PREFIX}/posts")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]["id"] == "post123"
    assert data[0]["favourites_count"] == 10
    assert data[0]["reblogs_count"] == 5

    # Verify DB query
    mock_cursor.execute.assert_called_with(
        "SELECT post_id, author_id, author_name, content, content_type, created_at, interaction_counts, mastodon_post FROM post_metadata ORDER BY created_at DESC LIMIT %s",
        (100,),
    )


@patch("routes.posts.get_db_connection")
def test_get_posts_with_mastodon_data(mock_get_db, client, mock_db_conn):
    """Test retrieving posts list with mastodon post data."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn

    # Mock mastodon post data
    mastodon_post = {
        "id": "post123",
        "account": {"username": "mastodon_user"},
        "content": "<p>Mastodon post content</p>",
        "favourites_count": 42,
    }

    # Mock data with mastodon data
    mock_cursor.fetchall.return_value = [
        (
            "post123",
            "author456",
            "Author Name",
            "Post content",
            "text",
            None,
            {"favorites": 10, "reblogs": 5},
            json.dumps(mastodon_post),
        ),
    ]

    # Make request
    response = client.get(f"{API_PREFIX}/posts")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]["id"] == "post123"
    assert data[0]["favourites_count"] == 42  # Should use mastodon data
    assert data[0]["account"]["username"] == "mastodon_user"


@patch("routes.posts.get_db_connection")
def test_create_post(mock_get_db, client, mock_db_conn):
    """Test creating a new post."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_cursor.fetchone.return_value = ("post123",)

    # Test data
    test_data = {
        "post_id": "post123",
        "author_id": "author456",
        "author_name": "Author Name",
        "content": "Test post content",
        "created_at": "2023-01-01T12:00:00Z",
        "interaction_counts": {"favorites": 0},
    }

    # Make request
    response = client.post("/v1/posts", json=test_data, content_type="application/json")

    # Verify response
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["message"] == "Post saved successfully"
    assert data["post_id"] == "post123"

    # Verify first DB operation checks if post exists
    mock_cursor.execute.assert_any_call(
        "SELECT 1 FROM post_metadata WHERE post_id = %s", ("post123",)
    )


@patch("routes.posts.get_db_connection")
def test_create_post_missing_fields(mock_get_db, client):
    """Test creating a post with missing required fields."""
    # Test with missing author_id for a new post
    test_data = {"post_id": "post123"}

    # Setup mock to indicate post doesn't exist
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # Post doesn't exist
    mock_get_db.return_value = mock_conn

    # Make request
    response = client.post("/v1/posts", json=test_data, content_type="application/json")

    # Verify response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "Missing required author_id field" in data["error"]


@patch("routes.posts.get_db_connection")
def test_get_post_by_id(mock_get_db, client, mock_db_conn):
    """Test retrieving a specific post by ID."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn

    # Mock data for a post
    mock_cursor.fetchone.return_value = (
        "post123",
        "author456",
        "Author Name",
        "Post content",
        "text",
        None,
        {"favorites": 10, "reblogs": 5},
        None,
    )

    # Make request
    response = client.get("/v1/posts/post123")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["id"] == "post123"
    assert data["author_id"] == "author456"
    assert data["favourites_count"] == 10

    # Verify DB query
    mock_cursor.execute.assert_called_with(
        "SELECT post_id, author_id, author_name, content, content_type, created_at, interaction_counts, mastodon_post FROM post_metadata WHERE post_id = %s",
        ("post123",),
    )


@patch("routes.posts.get_db_connection")
def test_get_post_not_found(mock_get_db, client, mock_db_conn):
    """Test retrieving a non-existent post."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    mock_cursor.fetchone.return_value = None  # Post not found

    # Make request
    response = client.get("/v1/posts/nonexistent")

    # Verify response
    assert response.status_code == 404
    data = json.loads(response.data)
    assert "Post not found" in data["message"]


@patch("routes.posts.get_db_connection")
def test_get_posts_by_author(mock_get_db, client, mock_db_conn):
    """Test retrieving posts by author."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn

    # Mock posts data
    mock_cursor.fetchall.return_value = [
        (
            "post123",
            "author456",
            "Author Name",
            "Post content 1",
            "text",
            None,
            {"favorites": 10},
            None,
        ),
        (
            "post789",
            "author456",
            "Author Name",
            "Post content 2",
            "text",
            None,
            {"favorites": 5},
            None,
        ),
    ]

    # Make request
    response = client.get("/v1/posts/author/author456")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert data[0]["id"] == "post123"
    assert data[1]["id"] == "post789"

    # Verify DB query
    mock_cursor.execute.assert_called_with(
        "SELECT post_id, author_id, author_name, content, content_type, created_at, interaction_counts, mastodon_post FROM post_metadata WHERE author_id = %s ORDER BY created_at DESC",
        ("author456",),
    )


@patch("routes.posts.get_db_connection")
def test_get_trending_posts(mock_get_db, client, mock_db_conn):
    """Test retrieving trending posts."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn

    # Mock trending posts data with total_interactions
    mock_cursor.fetchall.return_value = [
        (
            "post123",
            "author456",
            "Author Name",
            "Popular post",
            "text",
            None,
            {"favorites": 100, "reblogs": 50},
            150,
            None,
        ),
        (
            "post789",
            "author456",
            "Author Name",
            "Less popular post",
            "text",
            None,
            {"favorites": 20, "reblogs": 10},
            30,
            None,
        ),
    ]

    # Make request
    response = client.get("/v1/posts/trending")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert data[0]["id"] == "post123"
    assert data[0]["total_interactions"] == 150
    assert data[1]["id"] == "post789"
    assert data[1]["total_interactions"] == 30

    # Verify DB query includes total_interactions calculation
    mock_cursor.execute.assert_called()
