"""
Tests for the proxy middleware functionality.
"""

import json
import pytest
import time
from unittest.mock import patch, MagicMock, ANY
from flask import Flask

from app import create_app
from routes.proxy import (
    get_user_instance,
    get_authenticated_user,
    blend_recommendations,
    record_proxy_metrics,
    get_proxy_metrics,
    reset_proxy_metrics,
)


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["DEFAULT_MASTODON_INSTANCE"] = "https://mastodon.social"
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics before and after each test."""
    reset_proxy_metrics()
    yield
    reset_proxy_metrics()


class TestProxyHelpers:
    """Test helper functions for the proxy middleware."""

    def test_get_user_instance_from_header(self, app):
        """Test extracting instance from headers."""
        with app.test_request_context(
            headers={"X-Mastodon-Instance": "mastodon.social"}
        ):
            from flask import request

            instance = get_user_instance(request)
            assert instance == "https://mastodon.social"

    def test_get_user_instance_from_query(self, app):
        """Test extracting instance from query parameters."""
        with app.test_request_context("/?instance=fosstodon.org"):
            from flask import request

            instance = get_user_instance(request)
            assert instance == "https://fosstodon.org"

    def test_get_user_instance_default(self, app):
        """Test falling back to default instance."""
        app.config["DEFAULT_MASTODON_INSTANCE"] = "https://mastodon.example"
        with app.test_request_context():
            from flask import request

            instance = get_user_instance(request)
            assert instance == "https://mastodon.example"

    @patch("routes.proxy.get_user_by_token")
    def test_get_authenticated_user(self, mock_get_user, app):
        """Test extracting user ID from authentication header."""
        mock_get_user.return_value = {
            "user_id": "user123",
            "instance_url": "https://example.org",
        }

        with app.test_request_context(headers={"Authorization": "Bearer test_token"}):
            from flask import request

            user_id = get_authenticated_user(request)
            assert user_id == "user123"
            mock_get_user.assert_called_once_with("test_token")

    def test_blend_recommendations(self):
        """Test blending recommendations into a timeline."""
        original_posts = [{"id": f"post{i}"} for i in range(10)]
        recommendations = [
            {"id": f"rec{i}", "is_recommendation": True} for i in range(3)
        ]

        blended = blend_recommendations(
            original_posts, recommendations, blend_ratio=0.3
        )

        # Check the length is as expected (should add recommendations)
        assert len(blended) == 13

        # Count recommendations in blended timeline
        rec_count = sum(1 for post in blended if post.get("is_recommendation"))
        assert rec_count == 3

        # Check ordering - recommendations should be distributed
        rec_positions = [
            i for i, post in enumerate(blended) if post.get("is_recommendation")
        ]
        assert len(rec_positions) == 3

        # Check that recommendations are spaced out
        if len(rec_positions) >= 2:
            min_spacing = min(
                rec_positions[i + 1] - rec_positions[i]
                for i in range(len(rec_positions) - 1)
            )
            assert min_spacing > 0


@pytest.mark.parametrize(
    "path,instance,expected_url",
    [
        (
            "timelines/home",
            "https://mastodon.social",
            "https://mastodon.social/api/v1/timelines/home",
        ),
        (
            "statuses/123",
            "https://fosstodon.org",
            "https://fosstodon.org/api/v1/statuses/123",
        ),
    ],
)
@patch("routes.proxy.requests.request")
def test_proxy_forwarding(mock_request, client, path, instance, expected_url):
    """Test that requests are properly forwarded to the Mastodon instance."""
    # Mock the response from the proxied request
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = json.dumps([{"id": "123", "content": "Test post"}]).encode(
        "utf-8"
    )
    mock_response.headers = {"Content-Type": "application/json"}
    mock_request.return_value = mock_response

    # Make a request to the proxy
    headers = {"X-Mastodon-Instance": instance}
    response = client.get(f"/api/v1/{path}", headers=headers)

    # Check that the request was forwarded correctly
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert kwargs["url"] == expected_url

    # Check the response
    assert response.status_code == 200
    assert "Content-Type" in response.headers


@patch("routes.proxy.requests.request")
@patch("routes.proxy.get_recommendations")
@patch("routes.proxy.get_authenticated_user")
@patch("routes.proxy.check_user_privacy")
def test_timeline_recommendation_injection(
    mock_check_privacy, mock_get_user, mock_get_recs, mock_request, client
):
    """Test that recommendations are injected into the home timeline."""
    # Set up mocks
    mock_get_user.return_value = "user123"
    mock_check_privacy.return_value = True

    # Mock the Mastodon API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = json.dumps(
        [
            {"id": "post1", "content": "Original post 1"},
            {"id": "post2", "content": "Original post 2"},
        ]
    ).encode("utf-8")
    mock_response.headers = {"Content-Type": "application/json"}
    mock_request.return_value = mock_response

    # Mock recommendations
    mock_get_recs.return_value = [
        {"id": "rec1", "content": "Recommended post 1", "is_recommendation": True}
    ]

    # Make a request to the home timeline
    response = client.get("/api/v1/timelines/home")

    # Verify the response
    assert response.status_code == 200
    data = json.loads(response.data)

    # Should have 3 posts (2 original + 1 recommendation)
    assert len(data) == 3

    # Verify that a recommendation was injected
    assert any(post.get("is_recommendation") for post in data)

    # Verify the header was added
    assert "X-Corgi-Recommendations" in response.headers

    # Check metrics were recorded
    metrics = get_proxy_metrics()
    assert metrics["timeline_requests"] == 1
    assert metrics["enriched_timelines"] == 1
    assert metrics["total_recommendations"] == 1


@patch("routes.proxy.requests.request")
@patch("routes.proxy.get_authenticated_user")
@patch("routes.proxy.check_user_privacy")
def test_standard_get_passthrough(
    mock_check_privacy, mock_get_user, mock_request, client
):
    """Test that standard GET requests are correctly passed through."""
    # Set up mocks
    mock_get_user.return_value = "user123"

    # Mock the Mastodon API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = json.dumps(
        {"id": "123", "username": "testuser", "display_name": "Test User"}
    ).encode("utf-8")
    mock_response.headers = {"Content-Type": "application/json"}
    mock_request.return_value = mock_response

    # Make a request to verify credentials endpoint
    response = client.get("/api/v1/accounts/verify_credentials")

    # Verify the response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["username"] == "testuser"

    # Verify the request was made correctly
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert kwargs["method"] == "GET"
    assert "accounts/verify_credentials" in kwargs["url"]

    # Check metrics
    metrics = get_proxy_metrics()
    assert metrics["total_requests"] == 1
    assert metrics["successful_requests"] == 1
    assert metrics["timeline_requests"] == 0  # Not a timeline request


@patch("routes.proxy.requests.request")
@patch("routes.proxy.get_authenticated_user")
@patch("routes.proxy.get_user_privacy_level")
def test_timeline_with_privacy_none(
    mock_privacy_level, mock_get_user, mock_request, client, app
):
    """Test that timelines are passed through without enrichment when privacy mode is none."""
    # Set up mocks
    mock_get_user.return_value = "user123"
    mock_privacy_level.return_value = "none"  # User has opted out

    # Mock the Mastodon API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    original_posts = [
        {"id": "post1", "content": "Original post 1"},
        {"id": "post2", "content": "Original post 2"},
    ]
    mock_response.content = json.dumps(original_posts).encode("utf-8")
    mock_response.headers = {"Content-Type": "application/json"}
    mock_request.return_value = mock_response

    # Make a request to the home timeline
    response = client.get("/api/v1/timelines/home")

    # Verify the response
    assert response.status_code == 200
    data = json.loads(response.data)

    # Should have same number of posts as original (no injection)
    assert len(data) == len(original_posts)

    # Verify no recommendation was injected
    assert not any(post.get("is_recommendation") for post in data)

    # Verify no special header was added
    assert "X-Corgi-Recommendations" not in response.headers

    # Check metrics
    metrics = get_proxy_metrics()
    assert metrics["timeline_requests"] == 1
    assert metrics["enriched_timelines"] == 0  # No enrichment occurred


@patch("routes.proxy.requests.request")
def test_proxy_error_when_target_instance_fails(mock_request, client):
    """Test that errors are handled gracefully when the target instance fails."""
    # Mock request to raise an exception
    mock_request.side_effect = requests.RequestException("Connection refused")

    # Make a request
    response = client.get("/api/v1/timelines/home")

    # Verify the response indicates an error
    assert response.status_code == 502
    data = json.loads(response.data)
    assert "error" in data
    assert "Connection refused" in data["details"]

    # Check metrics
    metrics = get_proxy_metrics()
    assert metrics["total_requests"] == 1
    assert metrics["failed_requests"] == 1
    assert len(metrics["recent_errors"]) == 1
    assert "Connection refused" in metrics["recent_errors"][0]["error"]


@patch("routes.proxy.requests.request")
def test_auth_header_passthrough(mock_request, client):
    """Test that authentication headers are properly passed through."""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"{}"
    mock_response.headers = {"Content-Type": "application/json"}
    mock_request.return_value = mock_response

    # Make a request with an auth header
    auth_token = "testauthtoken123"
    response = client.get(
        "/api/v1/accounts/verify_credentials",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # Verify request was made with auth header
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert "headers" in kwargs
    assert "Authorization" in kwargs["headers"]
    assert kwargs["headers"]["Authorization"] == f"Bearer {auth_token}"


@patch("routes.proxy.requests.request")
def test_proxy_metrics_endpoint(mock_request, client):
    """Test the proxy metrics endpoint."""
    # Generate some proxy activity first
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"[]"
    mock_response.headers = {"Content-Type": "application/json"}
    mock_request.return_value = mock_response

    # Make a couple of requests
    client.get("/api/v1/accounts/verify_credentials")
    client.get("/api/v1/timelines/home")

    # Now check the metrics endpoint
    response = client.get("/api/v1/proxy/metrics")

    # Verify metrics
    assert response.status_code == 200
    metrics = json.loads(response.data)

    assert metrics["total_requests"] == 2
    assert metrics["successful_requests"] == 2
    assert metrics["timeline_requests"] == 1
    assert "uptime_seconds" in metrics
    assert "avg_latency_seconds" in metrics

    # Test reset functionality
    response = client.get("/api/v1/proxy/metrics?reset=true")
    metrics = json.loads(response.data)
    assert metrics["reset"] is True

    # Metrics should now be reset
    response = client.get("/api/v1/proxy/metrics")
    metrics = json.loads(response.data)
    assert metrics["total_requests"] == 0
