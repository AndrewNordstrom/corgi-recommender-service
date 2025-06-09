"""
Integration tests for API endpoint caching behavior.

This module tests the caching behavior of various API endpoints to ensure
they correctly cache responses and respect cache-related parameters.
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock
from flask import url_for, Response as FlaskResponse
import unittest.mock

from utils.cache import clear_cache

class TestAPICaching:
    """Integration tests for API caching behavior."""
    
    @pytest.fixture(autouse=True)
    def setup_method_fixtures(self, client, mocked_redis_client): 
        """Set up the test environment for each test method."""
        self.client = client
        self.redis = mocked_redis_client 

    def test_health_endpoint_caching(self):
        """Test health endpoint basic functionality (caching to be implemented)."""
        response1 = self.client.get('/health')
        assert response1.status_code == 200
        data1 = json.loads(response1.data)
        assert 'status' in data1
        
        # Currently no caching implemented, so just test endpoint works
        response2 = self.client.get('/health')
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        assert 'status' in data2
        
        # Skip cache parameter should still work
        response3 = self.client.get('/health?skip_cache=true')
        assert response3.status_code == 200
        data3 = json.loads(response3.data)
        assert 'status' in data3

    def test_api_docs_spec_caching(self):
        """Test API docs spec endpoint basic functionality (caching to be implemented)."""
        api_prefix = self.client.application.config.get("API_PREFIX", "/api/v1")
        
        response1 = self.client.get(f'{api_prefix}/docs/spec')
        assert response1.status_code == 200
        data1 = json.loads(response1.data)
        assert 'openapi' in data1 or 'swagger' in data1
        
        # Currently no caching implemented, so just test endpoint works
        response2 = self.client.get(f'{api_prefix}/docs/spec')
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        assert data1 == data2  # Should be the same spec
        
        response3 = self.client.get(f'{api_prefix}/docs/spec?skip_cache=true')
        assert response3.status_code == 200

    def test_profile_requests_caching(self):
        """Test profile requests basic functionality (caching to be implemented)."""
        api_prefix = self.client.application.config.get("API_PREFIX", "/api/v1")

        with patch('routes.proxy.requests.request') as mock_external_request:
            mock_mastodon_response = MagicMock()
            mock_mastodon_response.status_code = 200
            mock_profile_data = {"id": "proxy_user_123", "username": "proxy_cached_user"}
            mock_mastodon_response.json.return_value = mock_profile_data
            mock_mastodon_response.content = json.dumps(mock_profile_data).encode('utf-8')
            mock_mastodon_response.headers = {'Content-Type': 'application/json'}
            mock_external_request.return_value = mock_mastodon_response

            profile_url = f'{api_prefix}/proxy/accounts/proxy_user_123'
            res1_profile = self.client.get(profile_url)
            assert res1_profile.status_code == 200
            data1_profile = json.loads(res1_profile.data)
            assert data1_profile == mock_profile_data
            
            # Currently no caching implemented, so each request hits upstream
            res2_profile = self.client.get(profile_url)
            assert res2_profile.status_code == 200
            data2_profile = json.loads(res2_profile.data)
            assert data2_profile == mock_profile_data

        # Test privacy endpoint basic functionality
        user_to_test = "user_privacy_test"
        with patch('routes.privacy.update_user_privacy_level', return_value=True) as mock_db_update:
            privacy_url = f'{api_prefix}/privacy'
            post_data = {"user_id": user_to_test, "tracking_level": "none"}
            res_post_privacy = self.client.post(privacy_url, json=post_data)
            assert res_post_privacy.status_code == 200
            mock_db_update.assert_called_once()

    def test_proxy_status_caching(self):
        """Test proxy status endpoint basic functionality (caching to be implemented)."""
        status_url = f'{self.client.application.config.get("API_PREFIX", "/api/v1")}/status'

        response1 = self.client.get(status_url)
        assert response1.status_code == 200
        data1 = json.loads(response1.data)
        assert 'status' in data1
        
        # Currently no caching implemented, so just test endpoint works
        response2 = self.client.get(status_url)
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        assert 'status' in data2

    def test_timeline_caching(self):
        """Test timeline endpoint basic functionality (caching to be implemented)."""
        api_prefix = self.client.application.config.get("API_PREFIX", "/api/v1")
        timeline_url = f'{api_prefix}/timelines/home'
        test_user_id = "real_user_timeline_caching"

        with patch('routes.timeline.get_authenticated_user', return_value=test_user_id), \
             patch('routes.timeline.get_user_instance', return_value="https://mastodon.social"), \
             patch('routes.timeline.requests.get') as mock_external_request:
            
            # Mock the external Mastodon response
            mock_mastodon_response = MagicMock()
            mock_mastodon_response.status_code = 200
            mock_mastodon_response.json.return_value = [{"id": "114364986883002783"}]
            mock_external_request.return_value = mock_mastodon_response

            response1 = self.client.get(timeline_url)
            assert response1.status_code == 200
            data1 = response1.get_json()
            
            # Timeline should return a list of posts
            assert isinstance(data1, list)
            assert len(data1) > 0

    @patch('utils.cache.REDIS_ENABLED', True)
    @patch('utils.cache.get_redis_client')
    def test_cache_invalidation(self, mock_get_redis_client):
        """Test cache invalidation utility function."""
        # Set up the mock to return our test Redis client
        mock_get_redis_client.return_value = self.redis
        # Mock flushdb to return success
        self.redis.flushdb.return_value = True
        
        # Reset any previous calls from setup
        self.redis.flushdb.reset_mock()
        
        # Clear cache should succeed when Redis is available
        result = clear_cache()
        assert result is True
        self.redis.flushdb.assert_called_once()