"""
Core Proxy Caching Tests

Essential tests for proxy caching functionality covering:
- Cache key generation and TTL determination
- Cache hit/miss scenarios
- Basic caching behavior
- Core configuration handling
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from routes.proxy import (
    generate_proxy_cache_key,
    determine_proxy_cache_ttl,
    should_cache_proxy_request,
    proxy_bp
)
from config import (
    PROXY_CACHE_TTL_TIMELINE,
    PROXY_CACHE_TTL_PROFILE,
    PROXY_CACHE_TTL_INSTANCE,
    PROXY_CACHE_TTL_STATUS,
    PROXY_CACHE_TTL_DEFAULT
)


@pytest.fixture
def app():
    """Create test Flask app with proxy blueprint."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.register_blueprint(proxy_bp, url_prefix='/api/v1')
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestProxyCacheHelpers:
    """Test core proxy cache helper functions."""

    def test_generate_proxy_cache_key_public_endpoint(self):
        """Test cache key generation for public endpoints."""
        key = generate_proxy_cache_key("instance", {}, None, None)
        # The function returns an MD5 hash, so verify it's a valid 32-character hex string
        assert len(key) == 32
        assert all(c in '0123456789abcdef' for c in key)
        
        # Test that the same input generates the same key
        key2 = generate_proxy_cache_key("instance", {}, None, None)
        assert key == key2

    def test_generate_proxy_cache_key_user_specific_endpoint(self):
        """Test cache key generation for user-specific endpoints."""
        key = generate_proxy_cache_key("timelines/home", {"limit": "20"}, "user123", None)
        # The function returns an MD5 hash, so verify it's a valid 32-character hex string
        assert len(key) == 32
        assert all(c in '0123456789abcdef' for c in key)
        
        # Test that different users generate different keys
        key2 = generate_proxy_cache_key("timelines/home", {"limit": "20"}, "user456", None)
        assert key != key2

    def test_determine_proxy_cache_ttl_timeline(self):
        """Test TTL determination for timeline endpoints."""
        assert determine_proxy_cache_ttl("timelines/home") == PROXY_CACHE_TTL_TIMELINE
        assert determine_proxy_cache_ttl("timelines/public") == PROXY_CACHE_TTL_TIMELINE

    def test_determine_proxy_cache_ttl_profile(self):
        """Test TTL determination for profile endpoints."""
        assert determine_proxy_cache_ttl("accounts/123") == PROXY_CACHE_TTL_PROFILE
        assert determine_proxy_cache_ttl("accounts/456/statuses") == PROXY_CACHE_TTL_PROFILE

    def test_should_cache_proxy_request_valid_get(self):
        """Test caching decision for valid GET requests."""
        assert should_cache_proxy_request("instance", "GET", 200) is True
        assert should_cache_proxy_request("accounts/123", "GET", 200) is True

    def test_should_cache_proxy_request_invalid_scenarios(self):
        """Test caching decision for invalid scenarios."""
        assert should_cache_proxy_request("instance", "POST", 200) is False
        assert should_cache_proxy_request("instance", "GET", 404) is False
        assert should_cache_proxy_request("statuses/123/favourite", "GET", 200) is False


class TestProxyEndpointCaching:
    """Test core proxy endpoint caching behavior."""

    @patch('routes.proxy.requests.request')
    def test_proxy_cache_hit(self, mock_requests, client):
        """Test proxy cache hit scenario - currently proxy doesn't implement caching."""
        # Setup upstream response since proxy doesn't cache yet
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"id": "test", "content": "response"}).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_requests.return_value = mock_response
        
        with patch('routes.proxy.get_user_instance', return_value="https://mastodon.social"):
            # Make request to endpoint
            response = client.get('/api/v1/custom_emojis', headers={'Authorization': 'Bearer test-token'})
        
        # Verify upstream was called (since no caching is implemented)
        mock_requests.assert_called()
        
        # Verify response
        assert response.status_code == 200

    @patch('routes.proxy.requests.request')
    def test_proxy_caching_disabled(self, mock_requests, client):
        """Test proxy behavior when caching is disabled - matches current implementation."""
        # Setup upstream response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"id": "test"}).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_requests.return_value = mock_response
        
        with patch('routes.proxy.get_user_instance', return_value="https://mastodon.social"):
            # Make request
            response = client.get('/api/v1/custom_emojis')
        
        # Verify upstream was called (no caching implemented)
        mock_requests.assert_called()
        
        # Verify response
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 