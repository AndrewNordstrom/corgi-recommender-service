"""
Test suite for proxy caching functionality.

This module tests the new proxy endpoint caching features including:
- Cache hit/miss scenarios
- TTL handling
- Cache key generation
- Different endpoint types
- Error handling
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
    """Test proxy cache helper functions."""

    def test_generate_proxy_cache_key_public_endpoint(self):
        """Test cache key generation for public endpoints."""
        key = generate_proxy_cache_key("instance", {}, None, None)
        assert key.startswith("proxy:instance:")
        assert "user" not in key.lower()

    def test_generate_proxy_cache_key_user_specific_endpoint(self):
        """Test cache key generation for user-specific endpoints."""
        key = generate_proxy_cache_key("timelines/home", {"limit": "20"}, "user123", None)
        assert "proxy:timelines/home:user123:" in key

    def test_generate_proxy_cache_key_params_handling(self):
        """Test cache key generation handles parameters correctly."""
        params = {"limit": "20", "max_id": "12345"}
        key1 = generate_proxy_cache_key("timelines/public", params, None, None)
        
        # Same params should generate same key
        key2 = generate_proxy_cache_key("timelines/public", params, None, None)
        assert key1 == key2
        
        # Different params should generate different key
        key3 = generate_proxy_cache_key("timelines/public", {"limit": "10"}, None, None)
        assert key1 != key3

    def test_determine_proxy_cache_ttl_timeline(self):
        """Test TTL determination for timeline endpoints."""
        assert determine_proxy_cache_ttl("timelines/home") == PROXY_CACHE_TTL_TIMELINE
        assert determine_proxy_cache_ttl("timelines/public") == PROXY_CACHE_TTL_TIMELINE

    def test_determine_proxy_cache_ttl_profile(self):
        """Test TTL determination for profile endpoints."""
        assert determine_proxy_cache_ttl("accounts/123") == PROXY_CACHE_TTL_PROFILE
        assert determine_proxy_cache_ttl("accounts/456/statuses") == PROXY_CACHE_TTL_PROFILE

    def test_determine_proxy_cache_ttl_instance(self):
        """Test TTL determination for instance endpoints."""
        assert determine_proxy_cache_ttl("instance") == PROXY_CACHE_TTL_INSTANCE
        assert determine_proxy_cache_ttl("v2/instance") == PROXY_CACHE_TTL_INSTANCE
        assert determine_proxy_cache_ttl("custom_emojis") == PROXY_CACHE_TTL_INSTANCE

    def test_determine_proxy_cache_ttl_status(self):
        """Test TTL determination for status endpoints."""
        assert determine_proxy_cache_ttl("statuses/123") == PROXY_CACHE_TTL_STATUS

    def test_determine_proxy_cache_ttl_default(self):
        """Test TTL determination for other endpoints."""
        assert determine_proxy_cache_ttl("unknown/endpoint") == PROXY_CACHE_TTL_DEFAULT

    def test_should_cache_proxy_request_valid_get(self):
        """Test caching decision for valid GET requests."""
        assert should_cache_proxy_request("instance", "GET", 200) is True
        assert should_cache_proxy_request("accounts/123", "GET", 200) is True

    def test_should_cache_proxy_request_non_get_methods(self):
        """Test caching decision for non-GET methods."""
        assert should_cache_proxy_request("instance", "POST", 200) is False
        assert should_cache_proxy_request("instance", "PUT", 200) is False
        assert should_cache_proxy_request("instance", "DELETE", 200) is False

    def test_should_cache_proxy_request_non_200_status(self):
        """Test caching decision for non-200 status codes."""
        assert should_cache_proxy_request("instance", "GET", 404) is False
        assert should_cache_proxy_request("instance", "GET", 500) is False

    def test_should_cache_proxy_request_interaction_endpoints(self):
        """Test caching decision for interaction endpoints."""
        assert should_cache_proxy_request("statuses/123/favourite", "GET", 200) is False
        assert should_cache_proxy_request("statuses/123/bookmark", "GET", 200) is False
        assert should_cache_proxy_request("statuses/123/reblog", "GET", 200) is False


class TestProxyEndpointCaching:
    """Test actual proxy endpoint caching behavior."""

    @patch('routes.proxy.REDIS_ENABLED', True)
    @patch('routes.proxy.get_cached_api_response')
    @patch('routes.proxy.requests.request')
    def test_proxy_cache_hit(self, mock_requests, mock_get_cached, client):
        """Test proxy cache hit scenario."""
        # Setup mock cache hit
        cached_data = {"id": "test", "content": "cached response"}
        mock_get_cached.return_value = cached_data
        
        # Make request to cached endpoint
        response = client.get('/api/v1/custom_emojis', headers={'Authorization': 'Bearer test-token'})
        
        # Verify cache was checked
        mock_get_cached.assert_called()
        
        # Verify upstream was not called
        mock_requests.assert_not_called()
        
        # Verify response
        assert response.status_code == 200
        assert response.get_json() == cached_data

    @patch('routes.proxy.REDIS_ENABLED', True)
    @patch('routes.proxy.get_cached_api_response')
    @patch('routes.proxy.cache_api_response')
    @patch('routes.proxy.requests.request')
    @patch('routes.proxy.get_user_instance')
    def test_proxy_cache_miss_and_store(self, mock_get_instance, mock_requests, 
                                       mock_cache_set, mock_get_cached, client):
        """Test proxy cache miss and subsequent storage."""
        # Setup cache miss
        mock_get_cached.return_value = None
        
        # Setup upstream response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"id": "test", "content": "fresh response"}).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_requests.return_value = mock_response
        
        # Setup instance
        mock_get_instance.return_value = "https://mastodon.social"
        
        with patch('routes.proxy.get_user_instance', return_value="https://mastodon.social"):
            # Make request
            response = client.get('/api/v1/custom_emojis')
        
        # Verify cache was checked
        mock_get_cached.assert_called()
        
        # Verify upstream was called
        mock_requests.assert_called()
        
        # Verify response was cached
        mock_cache_set.assert_called()
        
        # Verify response
        assert response.status_code == 200

    @patch('routes.proxy.REDIS_ENABLED', False)
    @patch('routes.proxy.get_cached_api_response')
    @patch('routes.proxy.requests.request')
    def test_proxy_caching_disabled(self, mock_requests, mock_get_cached, client):
        """Test proxy behavior when caching is disabled."""
        # Setup upstream response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"id": "test"}).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_requests.return_value = mock_response
        
        with patch('routes.proxy.get_user_instance', return_value="https://mastodon.social"):
            # Make request
            response = client.get('/api/v1/custom_emojis')
        
        # Verify cache was not checked
        mock_get_cached.assert_not_called()
        
        # Verify upstream was called
        mock_requests.assert_called()

    @patch('routes.proxy.REDIS_ENABLED', True)
    @patch('routes.proxy.get_cached_api_response')
    @patch('routes.proxy.requests.request')
    def test_proxy_skip_cache_parameter(self, mock_requests, mock_get_cached, client):
        """Test skip_cache parameter bypasses cache."""
        # Setup upstream response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"id": "test"}).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_requests.return_value = mock_response
        
        with patch('routes.proxy.get_user_instance', return_value="https://mastodon.social"):
            # Make request with skip_cache
            response = client.get('/api/v1/custom_emojis?skip_cache=true')
        
        # Verify cache was not checked
        mock_get_cached.assert_not_called()
        
        # Verify upstream was called
        mock_requests.assert_called()

    @patch('routes.proxy.REDIS_ENABLED', True)
    @patch('routes.proxy.get_cached_api_response')
    @patch('routes.proxy.requests.request')
    def test_proxy_interaction_endpoints_not_cached(self, mock_requests, mock_get_cached, client):
        """Test that interaction endpoints are not cached."""
        # Setup upstream response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"id": "123", "favourited": True}).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_requests.return_value = mock_response
        
        with patch('routes.proxy.get_user_instance', return_value="https://mastodon.social"):
            # Make request to interaction endpoint
            response = client.post('/api/v1/statuses/123/favourite', 
                                 headers={'Authorization': 'Bearer test-token'})
        
        # Verify cache was not checked
        mock_get_cached.assert_not_called()

    @patch('routes.proxy.REDIS_ENABLED', True)
    @patch('routes.proxy.get_cached_api_response')
    @patch('routes.proxy.cache_api_response')
    @patch('routes.proxy.requests.request')
    def test_proxy_cache_error_handling(self, mock_requests, mock_cache_set, mock_get_cached, client):
        """Test proxy caching error handling."""
        # Setup cache error
        mock_get_cached.side_effect = Exception("Cache error")
        
        # Setup upstream response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"id": "test"}).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_requests.return_value = mock_response
        
        with patch('routes.proxy.get_user_instance', return_value="https://mastodon.social"):
            # Make request
            response = client.get('/api/v1/custom_emojis')
        
        # Verify upstream was still called despite cache error
        mock_requests.assert_called()
        
        # Verify response is still successful
        assert response.status_code == 200

    @patch('routes.proxy.REDIS_ENABLED', True)
    @patch('routes.proxy.get_cached_api_response')
    @patch('routes.proxy.determine_proxy_cache_ttl')
    @patch('routes.proxy.cache_api_response')
    @patch('routes.proxy.requests.request')
    def test_proxy_ttl_determination(self, mock_requests, mock_cache_set, mock_ttl, 
                                   mock_get_cached, client):
        """Test that appropriate TTL is used for different endpoints."""
        # Setup cache miss
        mock_get_cached.return_value = None
        mock_ttl.return_value = 3600  # 1 hour
        
        # Setup upstream response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"id": "test"}).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_requests.return_value = mock_response
        
        with patch('routes.proxy.get_user_instance', return_value="https://mastodon.social"):
            # Make request
            response = client.get('/api/v1/custom_emojis')
        
        # Verify TTL was determined
        mock_ttl.assert_called_with('custom_emojis')
        
        # Verify cache was set with correct TTL
        mock_cache_set.assert_called()
        args, kwargs = mock_cache_set.call_args
        assert kwargs.get('ttl') == 3600


if __name__ == '__main__':
    pytest.main([__file__]) 