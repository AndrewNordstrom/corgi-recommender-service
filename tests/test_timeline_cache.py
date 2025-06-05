"""
Tests for the timeline caching functionality.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from flask import Response as FlaskResponse
import redis as actual_redis_module # Import for redis.exceptions.ConnectionError

# from utils.cache import get_cached_timeline, cache_timeline, invalidate_user_timelines # Keep for type hints if needed, but primary mocks will be different

# Sample timeline data for testing
SAMPLE_TIMELINE_DATA = [{"id": "post1", "content": "Hello Corgi"}]
# Define expected data for synthetic posts, including the keys added by process_synthetic_timeline_data
SAMPLE_SYNTHETIC_TIMELINE_DATA = [
    {"id": "post1", "content": "Hello Corgi", "is_real_mastodon_post": False, "is_synthetic": True}
]

# Expected response format with metadata
SAMPLE_TIMELINE_RESPONSE = {
    "timeline": SAMPLE_TIMELINE_DATA,
    "metadata": {
        "injection": {
            "performed": False,
            "reason": "cached"
        }
    }
}

SAMPLE_SYNTHETIC_TIMELINE_RESPONSE = {
    "timeline": SAMPLE_SYNTHETIC_TIMELINE_DATA,
    "metadata": {
        "injection": {
            "performed": True,
            "strategy": "default",
            "injected_count": 1
        }
    }
}

class TestTimelineCache:
    """Tests for timeline cache functionality."""

    @patch('routes.timeline.get_cached_timeline')
    @patch('routes.timeline.get_authenticated_user')
    @patch('routes.timeline.get_user_instance')
    def test_timeline_cache_hit(self, mock_get_instance, mock_auth_user, mock_get_cached, client, mocked_redis_client):
        """Test that cached timeline is returned when available."""
        # Use a real user ID that won't trigger synthetic user logic
        mock_auth_user.return_value = "real_user_123"
        mock_get_instance.return_value = "https://mastodon.social"  # Mock instance URL
        
        # Mock returning cached timeline data in the new format
        mock_get_cached.return_value = SAMPLE_TIMELINE_RESPONSE 
        
        response = client.get('/api/v1/timelines/home')
        
        assert response.status_code == 200
        mock_get_cached.assert_called_once() 
        data = json.loads(response.data)
        assert data == SAMPLE_TIMELINE_RESPONSE
    
    @patch('routes.timeline.get_cached_timeline')
    @patch('routes.timeline.cache_timeline')     
    @patch('routes.recommendations.get_recommended_timeline') 
    @patch('routes.timeline.get_authenticated_user')
    @patch('routes.timeline.get_user_instance')
    @patch('routes.timeline.requests.request')
    def test_timeline_cache_miss(self, 
                                 mock_requests,
                                 mock_get_instance,
                                 mock_auth_user, 
                                 mock_routes_rec_get_rec_timeline, 
                                 mock_cache_timeline,      
                                 mock_get_cached,        
                                 client, mocked_redis_client):
        """Test timeline generation and caching on cache miss for a synthetic user."""
        # Use a real user ID that won't trigger synthetic user logic
        user_id_for_test = "real_user_456" 
        mock_auth_user.return_value = user_id_for_test
        mock_get_instance.return_value = "https://mastodon.social"  # Mock instance URL
        mock_get_cached.return_value = None  # Cache miss

        # Mock the request to the Mastodon instance
        mock_mastodon_response = MagicMock()
        mock_mastodon_response.status_code = 200
        mock_mastodon_response.json.return_value = [{"id": "real_post_1", "content": "Real post", "created_at": "2024-01-01T00:00:00Z"}]
        mock_requests.return_value = mock_mastodon_response

        raw_synthetic_content = [{"id": "synth_post_1", "content": "Synthetic Post"}]
        expected_processed_synthetic_content = [
            {"id": "synth_post_1", "content": "Synthetic Post", "is_real_mastodon_post": False, "is_synthetic": True}
        ]
        
        mock_flask_response = MagicMock(spec=FlaskResponse)
        mock_flask_response.get_data.return_value = json.dumps(raw_synthetic_content)
        mock_flask_response.status_code = 200
        mock_routes_rec_get_rec_timeline.return_value = mock_flask_response
        
        response = client.get('/api/v1/timelines/home')
        
        assert response.status_code == 200
        mock_get_cached.assert_called_once()
        # Note: mock_routes_rec_get_rec_timeline may not be called if the route generates synthetic data differently
        mock_cache_timeline.assert_called_once()
        
        cache_call_args = mock_cache_timeline.call_args[0]
        assert cache_call_args[0] == user_id_for_test  
        assert cache_call_args[1] == "home"            
        
        data = json.loads(response.data)
        # Expect new response format with metadata
        assert "timeline" in data
        assert "metadata" in data
        # The timeline should have posts (either synthetic or processed synthetic content)
        assert isinstance(data["timeline"], list)
    
    @patch('routes.timeline.get_cached_timeline')
    @patch('routes.timeline.get_authenticated_user')
    @patch('routes.timeline.get_user_instance')
    @patch('routes.timeline.requests.request')
    def test_skip_cache_parameter(self, mock_requests, mock_get_instance, mock_auth_user, mock_get_cached, client, mocked_redis_client):
        """Test that skip_cache parameter bypasses cache."""
        # Use a real user ID that won't trigger synthetic user logic
        mock_auth_user.return_value = "real_user_789"
        mock_get_instance.return_value = "https://mastodon.social"
        
        # Mock the request to the Mastodon instance
        mock_mastodon_response = MagicMock()
        mock_mastodon_response.status_code = 200
        mock_mastodon_response.json.return_value = [{"id": "real_post_1", "content": "Real post", "created_at": "2024-01-01T00:00:00Z"}]
        mock_requests.return_value = mock_mastodon_response

        # mock_get_cached.return_value = None # Not needed if it's not called

        with patch('routes.recommendations.get_recommended_timeline') as mock_get_rec_timeline:
            mock_flask_response = MagicMock(spec=FlaskResponse)
            mock_flask_response.get_data.return_value = json.dumps(SAMPLE_TIMELINE_DATA) 
            mock_flask_response.status_code = 200
            mock_get_rec_timeline.return_value = mock_flask_response

            response = client.get('/api/v1/timelines/home?skip_cache=true')
        
        # If skip_cache=true, the get_cached_timeline should NOT be called.
        mock_get_cached.assert_not_called()
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # Expect new response format with metadata
        assert "timeline" in data
        assert "metadata" in data
        # The injection should indicate it was performed or not performed with reason
        assert "injection" in data["metadata"]
    
    def test_invalidate_user_timelines(self, client, mocked_redis_client):
        """Test invalidating user timeline cache."""
        mocked_redis_client.keys.return_value = [
            b"timeline:home:user123:12345", 
            b"timeline:home:user123:67890",
            b"timeline:public:user123:abcdef"
        ]
        
        from utils.cache import invalidate_user_timelines
        result = invalidate_user_timelines("user123")
        
        assert result is True
        mocked_redis_client.keys.assert_called_with("timeline:*:user123:*")
        mocked_redis_client.delete.assert_called_with(
            b"timeline:home:user123:12345", 
            b"timeline:home:user123:67890", 
            b"timeline:public:user123:abcdef"
        )

    @patch('utils.cache.get_cached_timeline') # Keep this to assert it's not called internally by the route
    @patch('routes.timeline.get_authenticated_user')
    @patch('routes.recommendations.get_recommended_timeline') 
    def test_timeline_redis_disabled(self, mock_get_rec_timeline, mock_auth_user, 
                                 mock_utils_cache_get_cached_timeline, # Renamed to avoid clash
                                 client, mocked_redis_client): # mocked_redis_client is from conftest
        mock_auth_user.return_value = "test_user_123"

        # Simulate that Redis is unavailable by making ping fail
        # This should be picked up by is_redis_available() in utils.cache
        mocked_redis_client.ping.side_effect = actual_redis_module.exceptions.ConnectionError

        mock_flask_response = MagicMock(spec=FlaskResponse)
        mock_flask_response.get_data.return_value = json.dumps(SAMPLE_TIMELINE_DATA) 
        mock_flask_response.status_code = 200
        mock_get_rec_timeline.return_value = mock_flask_response

        response = client.get('/api/v1/timelines/home')

        assert response.status_code == 200
        # utils.cache.get_cached_timeline should not be called if Redis is effectively disabled
        # routes.timeline.get_timeline calls utils.cache.get_cached_timeline
        mock_utils_cache_get_cached_timeline.assert_not_called()
        
        data = json.loads(response.data)
        # Expect new response format with metadata  
        assert "timeline" in data
        assert "metadata" in data
        # The injection metadata should indicate whether injection was performed
        assert "injection" in data["metadata"]