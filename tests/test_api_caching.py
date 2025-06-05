"""
Integration tests for API endpoint caching behavior.

This module tests the caching behavior of various API endpoints to ensure
they correctly cache responses and respect cache-related parameters.
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock
# import redis as actual_redis_module # No longer need local import for spec if using conftest mock
from flask import url_for, Response as FlaskResponse
import unittest.mock

from utils.cache import clear_cache
# from config import REDIS_ENABLED # This should be handled by conftest.py mocked_redis_client

# The local mock_redis fixture is removed. Tests will use mocked_redis_client from conftest.py

class TestAPICaching:
    """Integration tests for API caching behavior."""
    
    @pytest.fixture(autouse=True)
    # Use the global mocked_redis_client from conftest.py
    def setup_method_fixtures(self, client, mocked_redis_client): 
        """Set up the test environment for each test method."""
        self.client = client
        # self.redis is now the instance from conftest.py:mocked_redis_client
        self.redis = mocked_redis_client 
        if hasattr(self.redis, 'flushdb'): # The mock from conftest should have this
            self.redis.flushdb() 
        
        # Reset mocks on the conftest-provided instance
        if hasattr(self.redis, 'get') and hasattr(self.redis.get, 'reset_mock'):
            self.redis.get.reset_mock()
        if hasattr(self.redis, 'set') and hasattr(self.redis.set, 'reset_mock'):
            self.redis.set.reset_mock()
        if hasattr(self.redis, 'delete') and hasattr(self.redis.delete, 'reset_mock'):
            self.redis.delete.reset_mock()
        if hasattr(self.redis, 'keys') and hasattr(self.redis.keys, 'reset_mock'):
            self.redis.keys.reset_mock()

    def test_health_endpoint_caching(self):
        """Test caching for the main health check endpoint."""
        response1 = self.client.get('/health')
        assert response1.status_code == 200
        self.redis.set.assert_called_once()
        
        # Capture the arguments passed to self.redis.set during the first call
        # cache_health_check calls redis_client.set(key, json.dumps(data), ex=ttl)
        # We need the json.dumps(data) part for the .get().return_value
        args_set, kwargs_set = self.redis.set.call_args
        cached_value_for_get = args_set[1] # This should be the json.dumps(data)
        
        self.redis.set.reset_mock() # Reset for the next potential call if skip_cache is tested
        self.redis.get.reset_mock() # Reset get before configuring its return value for the next call

        # Configure self.redis.get to return the captured value for the second call
        self.redis.get.return_value = cached_value_for_get
        
        response2 = self.client.get('/health')
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        self.redis.get.assert_called_once()
        assert data2.get('cached') is True
        assert 'cache_timestamp' in data2
        
        self.redis.get.reset_mock()
        self.redis.set.reset_mock()
        response3 = self.client.get('/health?skip_cache=true')
        assert response3.status_code == 200
        data3 = json.loads(response3.data)
        self.redis.set.assert_not_called() 
        assert data3.get('cached') is False

    def test_api_docs_spec_caching(self):
        """Test caching for the OpenAPI spec endpoint."""
        api_prefix = self.client.application.config.get("API_PREFIX", "/api/v1")
        
        response1 = self.client.get(f'{api_prefix}/docs/spec')
        assert response1.status_code == 200
        data1 = json.loads(response1.data)
        self.redis.set.assert_called()
        self.redis.set.reset_mock()
        
        response2 = self.client.get(f'{api_prefix}/docs/spec')
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        self.redis.get.assert_called()
        assert data1 == data2
        
        self.redis.get.reset_mock()
        self.redis.set.reset_mock()
        response3 = self.client.get(f'{api_prefix}/docs/spec?skip_cache=true')
        assert response3.status_code == 200
        self.redis.set.assert_not_called()

    def test_profile_requests_caching(self):
        """Test caching for proxied user profile requests and local privacy endpoint effects."""
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
            mock_external_request.assert_called_once()
            # First request should cache the response
            self.redis.set.assert_called_once()
            
            # Capture the cached data for the second request
            args_set, kwargs_set = self.redis.set.call_args
            cached_profile_data = args_set[1]  # Pickled data

            self.redis.set.reset_mock()
            self.redis.get.reset_mock()
            
            # Configure cache to return the cached data for second request
            self.redis.get.return_value = cached_profile_data

            res2_profile = self.client.get(profile_url)
            assert res2_profile.status_code == 200
            data2_profile = json.loads(res2_profile.data)
            assert data2_profile == mock_profile_data
            
            # Second request should hit cache, so no additional external request
            assert mock_external_request.call_count == 1  # Still only called once
            self.redis.get.assert_called_once()  # Cache read should happen
            self.redis.set.assert_not_called()  # No new cache write for cache hit

        user_to_invalidate = "user_privacy_invalidate"
        cache_key_pattern = "api:privacy/settings:*"
        key_to_be_deleted1 = f"api:privacy/settings:dummyhash1_for_test".encode('utf-8')
        key_to_be_deleted2 = f"api:privacy/settings:dummyhash2_for_test".encode('utf-8')
        
        # Use self.redis (from conftest) to set items in its store if needed by the test
        # The conftest mock_redis_client should provide a 'set' that works with its internal store
        if hasattr(self.redis, 'set') and callable(self.redis.set):
             self.redis.set(key_to_be_deleted1, b"dummy_data1")
             self.redis.set(key_to_be_deleted2, b"dummy_data2")

        self.redis.keys.reset_mock()
        self.redis.delete.reset_mock()
        self.redis.keys.return_value = [key_to_be_deleted1, key_to_be_deleted2]


        with patch('routes.privacy.update_user_privacy_level', return_value=True) as mock_db_update:
            privacy_url = f'{api_prefix}/privacy'
            post_data = {"user_id": user_to_invalidate, "tracking_level": "none"}
            res_post_privacy = self.client.post(privacy_url, json=post_data)
            assert res_post_privacy.status_code == 200
            mock_db_update.assert_called_once_with(unittest.mock.ANY, user_to_invalidate, "none")
            
            self.redis.keys.assert_called_once_with(cache_key_pattern)
            self.redis.delete.assert_called_once_with(key_to_be_deleted1, key_to_be_deleted2)


    def test_proxy_status_caching(self):
        """Test caching for the proxy status endpoint."""
        status_url_corrected = f'{self.client.application.config.get("API_PREFIX", "/api/v1")}/status'

        response1 = self.client.get(status_url_corrected)
        assert response1.status_code == 200
        self.redis.set.assert_called() # Should be called by cache_health_check -> cache_set
        
        # Capture the pickled data that was set to redis
        args_set, kwargs_set = self.redis.set.call_args
        pickled_data_for_get = args_set[1] # cache_set stores pickled data as the second arg to redis.set

        self.redis.set.reset_mock()
        self.redis.get.reset_mock() # Reset get before configuring its return value

        # Configure self.redis.get to return the captured pickled data for the second call
        self.redis.get.return_value = pickled_data_for_get
        
        response2 = self.client.get(status_url_corrected)
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        self.redis.get.assert_called()
        assert data2.get('cached') is True 
        assert 'cache_timestamp' in data2

    def test_timeline_caching(self):
        """Test caching for timeline endpoints (e.g., /timelines/home)."""
        api_prefix = self.client.application.config.get("API_PREFIX", "/api/v1")
        timeline_url = f'{api_prefix}/timelines/home'
        # Use a real user ID instead of test_ prefix to avoid synthetic user logic
        test_user_id = "real_user_timeline_caching"

        with patch('routes.timeline.get_authenticated_user', return_value=test_user_id), \
             patch('routes.timeline.get_user_instance', return_value='https://mastodon.social'), \
             patch('routes.timeline.requests.request') as mock_request, \
             patch('routes.timeline.is_new_user', return_value=False), \
             patch('routes.timeline.get_ranked_recommendations') as mock_get_recs:

            # Mock the upstream Mastodon response
            mock_response = MagicMock()
            mock_response.status_code = 200
            sample_posts = [{"id": "post123", "content": "Timeline Post"}]
            mock_response.json.return_value = sample_posts
            mock_request.return_value = mock_response
            
            # Mock recommendations to return empty (so it falls back to cold start)
            mock_get_recs.return_value = []
            
            res1 = self.client.get(timeline_url)
            assert res1.status_code == 200
            data1 = json.loads(res1.data)
            
            # The timeline will contain cold start posts since recommendations are empty
            # Check that we have a timeline response structure
            assert 'timeline' in data1
            assert 'metadata' in data1
            assert len(data1['timeline']) > 0
            
            mock_request.assert_called_once() # Called for the first response
            self.redis.set.assert_called_once() # Timeline should be cached

            # Capture the pickled timeline data that was set to redis
            args_set_timeline, kwargs_set_timeline = self.redis.set.call_args
            pickled_timeline_for_get = args_set_timeline[1]
            
            # Reset mocks before configuring for the second call
            self.redis.get.reset_mock()
            self.redis.set.reset_mock()
            mock_request.reset_mock() # Reset this to ensure it's NOT called for the cached response

            # Configure self.redis.get to return the cached timeline data for the second call
            self.redis.get.return_value = pickled_timeline_for_get

            res2 = self.client.get(timeline_url)
            assert res2.status_code == 200
            data2_cached = json.loads(res2.data)
            # Verify cached response has the same structure
            assert 'timeline' in data2_cached
            assert 'metadata' in data2_cached
            assert len(data2_cached['timeline']) == len(data1['timeline'])

            self.redis.get.assert_called_once() # Cache should be read
            mock_request.assert_not_called() # Should NOT be called for the second response (cache hit)

            # Reset for the skip_cache part
            self.redis.get.reset_mock()
            self.redis.set.reset_mock()
            mock_request.reset_mock()
            self.redis.get.return_value = None # Explicitly ensure cache miss for res3

            res3 = self.client.get(f'{timeline_url}?limit=50') # Should be a cache miss for new params
            assert res3.status_code == 200
            mock_request.assert_called_once() # Should be called now
            self.redis.set.assert_called_once() # And new result cached


    def test_cache_invalidation(self):
        """Test cache invalidation for user timelines via utils.cache.invalidate_user_timelines."""
        user_id_to_invalidate = "user_for_invalidation_utils"
        
        key1 = f"timeline:home:{user_id_to_invalidate}:keyA".encode('utf-8')
        key2 = f"timeline:public:{user_id_to_invalidate}:keyB".encode('utf-8')

        if hasattr(self.redis, 'set') and callable(self.redis.set):
            self.redis.set(key1, b"data_A")
            self.redis.set(key2, b"data_B")

        self.redis.keys.reset_mock()
        self.redis.delete.reset_mock()
        
        self.redis.keys.return_value = [key1, key2]
        self.redis.delete.return_value = 2 

        from utils.cache import invalidate_user_timelines 
        result = invalidate_user_timelines(user_id_to_invalidate)
        
        assert result is True
        self.redis.keys.assert_called_once_with(f"timeline:*:{user_id_to_invalidate}:*")
        self.redis.delete.assert_called_once_with(key1, key2)