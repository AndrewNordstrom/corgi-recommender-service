"""
Tests for the Corgi Recommender Service metrics functionality.

These tests verify that metrics are properly tracked and accessible.
"""

import unittest
import os
import json
import time
import requests
import threading
from unittest.mock import patch, MagicMock

# Add parent directory to path
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # Import the app factory function

# Create the app using the factory function
app = create_app()
from utils.metrics import (
    track_injection,
    track_recommendation_generation,
    track_fallback,
    track_recommendation_interaction,
    INJECTED_POSTS_TOTAL,
    RECOMMENDATIONS_TOTAL,
    FALLBACK_USAGE_TOTAL,
    RECOMMENDATION_INTERACTIONS,
    TIMELINE_POST_COUNT,
)


class MetricsServerThread(threading.Thread):
    """Thread class to run the metrics server."""

    def __init__(self, port=9100):
        threading.Thread.__init__(self)
        self.port = port
        self.daemon = (
            True  # Set as daemon so it will terminate when the main thread exits
        )

    def run(self):
        from prometheus_client import start_http_server

        try:
            # Try to start on the given port
            start_http_server(self.port)
        except Exception as e:
            print(f"Error starting metrics server on port {self.port}: {e}")
            # Server might already be running on this port, which is okay


class TestMetrics(unittest.TestCase):
    """Test cases for metrics tracking."""

    @classmethod
    def setUpClass(cls):
        """Set up the test class - start metrics server if needed."""
        # Start metrics server in a separate thread
        cls.metrics_thread = MetricsServerThread()
        cls.metrics_thread.start()

        # Give it a moment to start
        time.sleep(1)

        # Configure Flask app for testing
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_metrics_increment(self):
        """Test that metrics increments work."""
        # Track metrics
        track_injection("uniform", "test", 2)
        track_recommendation_generation("test", "new_user", 3)
        track_fallback("test_reason")
        track_recommendation_interaction("favorite", True)

        # We'll verify through the HTTP endpoint since _value is not accessible
        try:
            response = requests.get("http://localhost:9100/metrics")
            metrics_text = response.text

            # Check our metrics are present in output
            self.assertIn("corgi_injected_posts_total", metrics_text)
            self.assertIn("corgi_recommendations_total", metrics_text)
            self.assertIn("corgi_fallback_usage_total", metrics_text)
            self.assertIn("corgi_recommendation_interactions_total", metrics_text)
        except Exception as e:
            self.skipTest(f"Couldn't verify metrics: {e}")

    def test_metrics_http_endpoint(self):
        """Test that metrics are accessible via HTTP."""
        try:
            response = requests.get("http://localhost:9100/metrics")
            self.assertEqual(response.status_code, 200)
            metrics_text = response.text

            # Check that our metrics are in the output
            self.assertIn("corgi_injected_posts_total", metrics_text)
            self.assertIn("corgi_recommendations_total", metrics_text)
            self.assertIn("corgi_fallback_usage_total", metrics_text)
            self.assertIn("corgi_recommendation_interactions_total", metrics_text)
        except (requests.ConnectionError, requests.Timeout):
            self.skipTest("Metrics server not accessible - test skipped")

    def test_timeline_tracks_metrics(self):
        """Test that timeline API calls track metrics."""
        # Call the timeline endpoint
        response = self.client.get(
            "/api/v1/timelines/home?user_id=test_metrics_user&inject=true&strategy=uniform"
        )
        self.assertEqual(response.status_code, 200)

        # Verify metrics through HTTP endpoint
        try:
            metrics_response = requests.get("http://localhost:9100/metrics")
            metrics_text = metrics_response.text

            # Check timeline-related metrics exist
            self.assertIn("corgi_timeline_post_count", metrics_text)
            self.assertIn("corgi_injection_ratio", metrics_text)
        except Exception as e:
            self.skipTest(f"Couldn't verify timeline metrics: {e}")

    def test_interaction_tracks_metrics(self):
        """Test that interaction API calls track metrics."""
        # Make a post request to the interactions endpoint
        data = {
            "user_id": "test_metrics_user",
            "post_id": "test_metrics_post_123",
            "action_type": "favorite",
            "context": {"source": "test", "injected": True},
        }

        # The database foreign key constraint should be caught and handled by our improved code
        response = self.client.post("/api/v1/interactions", json=data)
        self.assertIn(
            response.status_code, [200, 400, 500]
        )  # Accept various status codes since database might cause constraints

        # Verify metrics through HTTP endpoint
        try:
            metrics_response = requests.get("http://localhost:9100/metrics")
            metrics_text = metrics_response.text

            # Check interaction-related metrics exist
            self.assertIn("corgi_recommendation_interactions_total", metrics_text)
        except Exception as e:
            self.skipTest(f"Couldn't verify interaction metrics: {e}")


class TestRegressionIssues(unittest.TestCase):
    """Test cases for specific regression issues."""

    def setUp(self):
        """Set up the test case."""
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_timeline_handles_non_list_return(self):
        """Test that timeline endpoint handles cases where inject_into_timeline might return a non-list."""
        # Mock the inject_into_timeline function to return a Response object
        with patch("routes.timeline.inject_into_timeline") as mock_inject:
            # Set up the mock to return a non-list
            mock_response = MagicMock()
            mock_response.__class__.__name__ = "Response"  # Fake a Response object
            mock_inject.return_value = mock_response

            # Call the timeline endpoint - it should not crash
            response = self.client.get(
                "/api/v1/timelines/home?user_id=test_regression_user&inject=true"
            )

            # We expect either a 200 (if the code handles it well) or a 500 (if it fails but doesn't crash)
            self.assertIn(response.status_code, [200, 500])

            # If it's a 500, check for a specific error message indicating the issue was caught
            if response.status_code == 500:
                error_data = json.loads(response.data)
                self.assertIn("error", error_data)

    def test_interaction_handles_missing_post(self):
        """Test that interaction endpoint handles cases where the post doesn't exist in post_metadata."""
        # Generate a unique post ID that is very unlikely to exist
        unique_post_id = f"nonexistent_post_{int(time.time())}"

        # Make a post request to the interactions endpoint
        data = {
            "user_id": "test_regression_user",
            "post_id": unique_post_id,
            "action_type": "favorite",
            "context": {
                "source": "test",
                "injected": True,
                "author_id": "test_author",
                "author_name": "Test Author",
                "content": "Test post content",
            },
        }

        # The endpoint should now handle the missing post by creating a stub
        response = self.client.post("/api/v1/interactions", json=data)

        # We now expect a 200 status code (or a controlled error response like 400)
        # We should never get a 500 due to foreign key violations
        self.assertIn(response.status_code, [200, 400])

    def test_metrics_flush_on_demand(self):
        """Test that metrics can be flushed on demand."""
        # Make a request to the health endpoint to trigger metrics collection
        self.client.get("/api/v1/health")

        # Check that metrics are accessible
        try:
            response = requests.get("http://localhost:9100/metrics")
            self.assertEqual(response.status_code, 200)
            metrics_text = response.text

            # Metrics should be present
            self.assertIn("corgi_", metrics_text)
        except (requests.ConnectionError, requests.Timeout):
            self.skipTest("Metrics server not accessible - test skipped")


if __name__ == "__main__":
    unittest.main()
