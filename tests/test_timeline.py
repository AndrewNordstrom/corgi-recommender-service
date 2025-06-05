"""
Tests for the timeline routes with injection capabilities.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from app import create_app


# Mock response for requests to upstream Mastodon server
def mock_requests_get(*args, **kwargs):
    """Create a mock response for requests.get calls."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    # Return mock timeline posts
    mock_response.json.return_value = [
        {
            "id": "real_post_1",
            "content": "This is a real Mastodon post",
            "created_at": "2025-04-19T10:00:00Z",
            "account": {
                "id": "user123",
                "username": "testuser",
                "display_name": "Test User",
                "url": "https://example.com/@testuser",
            },
        },
        {
            "id": "real_post_2",
            "content": "Another real post from Mastodon",
            "created_at": "2025-04-19T09:45:00Z",
            "account": {
                "id": "user456",
                "username": "anotheruser",
                "display_name": "Another User",
                "url": "https://example.com/@anotheruser",
            },
        },
    ]

    return mock_response


# Mock cold start posts
MOCK_COLD_START_POSTS = [
    {
        "id": "inject_post_1",
        "content": "This is an injected post",
        "created_at": "2025-04-19T08:30:00Z",
        "account": {
            "id": "inject_user",
            "username": "inject_user",
            "display_name": "Inject User",
            "url": "https://example.com/@inject_user",
        },
        "tags": [{"name": "test"}, {"name": "injected"}],
        "is_real_mastodon_post": False,
        "is_synthetic": True,
    },
    {
        "id": "inject_post_2",
        "content": "Another injectable post",
        "created_at": "2025-04-19T08:15:00Z",
        "account": {
            "id": "inject_user",
            "username": "inject_user",
            "display_name": "Inject User",
            "url": "https://example.com/@inject_user",
        },
        "tags": [{"name": "test"}, {"name": "injected"}],
        "is_real_mastodon_post": False,
        "is_synthetic": True,
    },
]


@pytest.fixture
def test_client():
    """Create a test client using the Flask application."""
    app = create_app()
    with app.test_client() as client:
        yield client


@patch("routes.timeline.load_json_file")
@patch("routes.proxy.get_authenticated_user")
@patch("routes.timeline.requests.request", side_effect=mock_requests_get)
def test_timeline_with_injection(
    mock_request, mock_auth_user, mock_load_json, test_client
):
    """Test the /api/v1/timelines/home endpoint with injection."""
    # Setup mocks
    mock_auth_user.return_value = "test_user_123"
    mock_load_json.return_value = MOCK_COLD_START_POSTS

    # Test with injection
    response = test_client.get("/api/v1/timelines/home?strategy=uniform&inject=true")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)

    # Check that we have timeline data and metadata
    assert "timeline" in data
    assert "metadata" in data
    assert "injection" in data["metadata"]

    # Verify injection occurred
    assert data["metadata"]["injection"]["strategy"] == "uniform"
    assert data["metadata"]["injection"]["injected_count"] > 0

    # Check that timeline has the expected number of posts
    # Should include both real and injected posts
    assert len(data["timeline"]) > 2  # More than just the real posts

    # Verify injected posts are marked
    injected_posts = [post for post in data["timeline"] if post.get("injected", False)]
    assert len(injected_posts) > 0
    for post in injected_posts:
        assert post["injected"] is True


@patch("routes.timeline.load_json_file")
@patch("routes.proxy.get_authenticated_user")
@patch("routes.timeline.requests.request", side_effect=mock_requests_get)
def test_timeline_without_injection(
    mock_request, mock_auth_user, mock_load_json, test_client
):
    """Test the /api/v1/timelines/home endpoint with injection disabled."""
    # Setup mocks
    mock_auth_user.return_value = "test_user_123"
    mock_load_json.return_value = MOCK_COLD_START_POSTS

    # Test without injection
    response = test_client.get("/api/v1/timelines/home?inject=false")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)

    # Check that we have timeline data and metadata
    assert "timeline" in data
    assert "metadata" in data
    assert "injection" in data["metadata"]

    # Verify no injection occurred
    assert data["metadata"]["injection"]["performed"] is False
    assert data["metadata"]["injection"]["reason"] == "disabled"

    # Check that timeline has only real posts
    assert len(data["timeline"]) == 2  # Just the mock real posts

    # Verify no posts are marked as injected
    injected_posts = [post for post in data["timeline"] if post.get("injected", False)]
    assert len(injected_posts) == 0


@patch("routes.timeline.load_json_file")
@patch("routes.proxy.get_authenticated_user")
@patch("routes.timeline.requests.request", side_effect=mock_requests_get)
def test_different_injection_strategies(
    mock_request, mock_auth_user, mock_load_json, test_client
):
    """Test different injection strategies."""
    # Setup mocks
    mock_auth_user.return_value = "test_user_123"
    mock_load_json.return_value = MOCK_COLD_START_POSTS

    # Test with each strategy
    strategies = ["uniform", "after_n", "first_only", "tag_match"]

    for strategy in strategies:
        response = test_client.get(
            f"/api/v1/timelines/home?strategy={strategy}&inject=true"
        )

        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)

        # Check injection metadata
        assert data["metadata"]["injection"]["strategy"] == strategy


@patch("routes.timeline.load_json_file", side_effect=FileNotFoundError)
@patch("routes.proxy.get_authenticated_user")
@patch("routes.timeline.requests.request", side_effect=mock_requests_get)
def test_timeline_with_missing_injectable_posts(
    mock_request, mock_auth_user, mock_load_json, test_client
):
    """Test behavior when injectable posts cannot be loaded."""
    # Setup mocks
    mock_auth_user.return_value = "test_user_123"

    # Test
    response = test_client.get("/api/v1/timelines/home?inject=true")

    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)

    # Check that we still get timeline data
    assert "timeline" in data
    assert len(data["timeline"]) == 2  # Just the real posts

    # Verify metadata indicates no injection
    assert "metadata" in data
    assert data["metadata"]["injection"]["performed"] is False
    assert data["metadata"]["injection"]["reason"] == "no_posts_available"


@patch("routes.timeline.load_json_file")
@patch("routes.proxy.get_authenticated_user")
def test_timeline_with_anonymous_user(mock_auth_user, mock_load_json, test_client):
    """Test the timeline endpoint with an anonymous user."""
    # Setup mocks
    mock_auth_user.return_value = None  # No authenticated user
    mock_load_json.return_value = MOCK_COLD_START_POSTS

    # Mock the allow anonymous setting
    with patch("routes.timeline.ALLOW_COLD_START_FOR_ANONYMOUS", True):
        # Test
        response = test_client.get("/api/v1/timelines/home?inject=true")

        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)

        # Check that we have timeline data with injected posts
        assert "timeline" in data
        assert len(data["timeline"]) > 0

        # Check all posts are marked as injected (since anonymous users only get injected posts)
        injected_posts = [
            post for post in data["timeline"] if post.get("injected", False)
        ]
        assert len(injected_posts) > 0
