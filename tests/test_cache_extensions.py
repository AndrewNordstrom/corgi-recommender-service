"""
Tests for the extended Redis caching module functionality.

This module tests the additional caching functions implemented for:
- Timeline caching
- Profile caching
- Post caching
- Health check caching
- Generic API response caching
"""

import pytest
import pickle
import json
import time
from unittest.mock import patch, MagicMock

from utils.cache import (
    get_redis_client, clear_cache, cache_key, create_params_hash,
    cache_timeline, get_cached_timeline, invalidate_user_timelines,
    cache_profile, get_cached_profile, invalidate_profile,
    cache_profile_statuses, get_cached_profile_statuses, invalidate_profile_statuses,
    cache_post, get_cached_post, invalidate_post,
    cache_post_context, get_cached_post_context, invalidate_post_context,
    cache_health_check, get_cached_health_check,
    cache_api_response, get_cached_api_response, invalidate_api_endpoint,
    invalidate_pattern
)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None  # Default behavior is cache miss
    mock_client.set.return_value = True  # Default behavior is successful set
    mock_client.delete.return_value = 1  # Default behavior is successful delete
    mock_client.keys.return_value = []   # Default behavior is no matching keys
    
    # Use a dictionary to simulate cache storage
    mock_client._data = {}
    
    # Override the get method to use the dictionary
    def mock_get(key):
        return mock_client._data.get(key)
    
    # Override the set method to use the dictionary
    def mock_set(key, value, ex=None):
        mock_client._data[key] = value
        return True
    
    # Override the delete method to use the dictionary
    def mock_delete(*keys):
        deleted = 0
        for key in keys:
            if key in mock_client._data:
                del mock_client._data[key]
                deleted += 1
        return deleted
    
    # Override the keys method to search the dictionary
    def mock_keys(pattern):
        import fnmatch
        matching_keys = [k for k in mock_client._data.keys() if fnmatch.fnmatch(k, pattern)]
        return matching_keys
    
    # Assign the mock methods
    mock_client.get.side_effect = mock_get
    mock_client.set.side_effect = mock_set
    mock_client.delete.side_effect = mock_delete
    mock_client.keys.side_effect = mock_keys
    
    return mock_client


@pytest.fixture
def sample_timeline_data():
    """Create a sample timeline data structure for testing."""
    return {
        "timeline": [
            {
                "id": "post_1",
                "content": "Timeline post 1",
                "created_at": "2025-05-01T12:00:00Z",
                "account": {
                    "id": "user_1",
                    "username": "user1",
                    "display_name": "User One"
                }
            },
            {
                "id": "post_2",
                "content": "Timeline post 2",
                "created_at": "2025-05-02T14:30:00Z",
                "account": {
                    "id": "user_2",
                    "username": "user2",
                    "display_name": "User Two"
                }
            }
        ],
        "metadata": {
            "injection": {
                "performed": True,
                "strategy": "tag_match",
                "injected_count": 1
            }
        }
    }


@pytest.fixture
def sample_profile_data():
    """Create a sample user profile data structure for testing."""
    return {
        "id": "user_123",
        "username": "testuser",
        "display_name": "Test User",
        "note": "This is a test user profile",
        "url": "https://example.com/@testuser",
        "avatar": "https://example.com/avatars/testuser.jpg",
        "header": "https://example.com/headers/testuser.jpg",
        "followers_count": 42,
        "following_count": 123,
        "statuses_count": 456
    }


@pytest.fixture
def sample_post_data():
    """Create a sample post data structure for testing."""
    return {
        "id": "post_123",
        "content": "This is a test post",
        "created_at": "2025-05-05T10:00:00Z",
        "account": {
            "id": "user_123",
            "username": "testuser",
            "display_name": "Test User"
        },
        "media_attachments": [],
        "mentions": [],
        "tags": ["test", "example"],
        "favourites_count": 10,
        "reblogs_count": 5,
        "replies_count": 2
    }


@pytest.fixture
def sample_post_context():
    """Create a sample post context data structure for testing."""
    return {
        "ancestors": [
            {
                "id": "post_121",
                "content": "Original post",
                "created_at": "2025-05-05T09:45:00Z",
                "account": {
                    "id": "user_456",
                    "username": "otheruser",
                    "display_name": "Other User"
                }
            }
        ],
        "descendants": [
            {
                "id": "post_125",
                "content": "Reply to the test post",
                "created_at": "2025-05-05T10:15:00Z",
                "account": {
                    "id": "user_789",
                    "username": "replier",
                    "display_name": "Reply User"
                }
            }
        ]
    }


@pytest.fixture
def sample_health_data():
    """Create a sample health check data structure for testing."""
    return {
        "status": "healthy",
        "timestamp": "2025-05-17T14:30:00Z",
        "version": "1.0.0",
        "hostname": "test-host",
        "platform": "Linux-5.10.0-x86_64",
        "database": "connected",
        "cached": False
    }


@patch('utils.cache.REDIS_ENABLED', True)
class TestExtendedCache:
    """Test suite for the extended Redis cache functions."""
    
    def test_create_params_hash(self):
        """Test creating parameter hashes for cache keys."""
        # Empty params - should produce consistent SHA-256 hash
        empty_hash = create_params_hash({})
        assert len(empty_hash) == 8  # Should be 8 characters (truncated SHA-256)
        assert empty_hash == "e3b0c442"  # SHA-256 of empty string, truncated
        
        # Simple params
        simple_params = {"limit": 20, "type": "home"}
        simple_hash = create_params_hash(simple_params)
        assert len(simple_hash) == 8
        assert simple_hash == create_params_hash(simple_params)  # Should be deterministic
        
        # Different order, same hash
        reordered_params = {"type": "home", "limit": 20}
        assert create_params_hash(reordered_params) == simple_hash
        
        # Different values, different hash
        different_params = {"limit": 50, "type": "home"}
        assert create_params_hash(different_params) != simple_hash
        
        # Exclude non-cacheable params
        non_cacheable_params = {
            "limit": 20, 
            "type": "home", 
            "_": "excluded_param", 
            "timestamp": "12345",
            "nonce": "random123"
        }
        non_cacheable_hash = create_params_hash(non_cacheable_params)
        assert non_cacheable_hash == simple_hash  # Should ignore _, timestamp, and nonce
        
        # Handle complex values
        complex_params = {"ids": ["1", "2", "3"], "nested": {"key": "value"}}
        complex_hash = create_params_hash(complex_params)
        assert len(complex_hash) == 8
        assert complex_hash == create_params_hash(complex_params)  # Should be deterministic
    
    @patch('utils.cache._redis_client_instance', None)
    @patch('utils.cache.get_redis_client')
    def test_cache_timeline(self, mock_get_client, mock_redis, sample_timeline_data):
        """Test caching a timeline response."""
        mock_get_client.return_value = mock_redis
        user_id = "user123"
        timeline_type = "home"
        params = {"limit": 20, "max_id": None}
        
        # Test successful caching
        result = cache_timeline(user_id, timeline_type, params, sample_timeline_data)
        assert result is True
        mock_redis.set.assert_called_once()
        
        # Verify correct key construction
        args, kwargs = mock_redis.set.call_args
        key = args[0]
        assert key.startswith("timeline:home:user123:")
        
        # Test with different params
        mock_redis.set.reset_mock()
        params2 = {"limit": 50}
        result = cache_timeline(user_id, timeline_type, params2, sample_timeline_data)
        assert result is True
        
        # Should have different cache key
        args, kwargs = mock_redis.set.call_args
        key2 = args[0]
        assert key2 != key
    
    @patch('utils.cache.cache_get')
    def test_get_cached_timeline(self, mock_cache_get, sample_timeline_data):
        """Test retrieving a cached timeline."""
        user_id = "user123"
        timeline_type = "home"
        params = {"limit": 20, "max_id": None}
        
        # Test cache miss
        mock_cache_get.return_value = None
        result = get_cached_timeline(user_id, timeline_type, params)
        assert result is None
        
        # Test cache hit
        mock_cache_get.return_value = sample_timeline_data
        result = get_cached_timeline(user_id, timeline_type, params)
        assert result == sample_timeline_data
    
    @patch('utils.cache.invalidate_pattern')
    def test_invalidate_user_timelines(self, mock_invalidate_pattern):
        """Test invalidating all cached timelines for a user."""
        user_id = "user123"
        
        # Test no keys match (should return True)
        mock_invalidate_pattern.return_value = True
        result = invalidate_user_timelines(user_id)
        assert result is True
        mock_invalidate_pattern.assert_called_with(f"timeline:*:{user_id}:*")
        
        # Test keys found and deleted
        mock_invalidate_pattern.return_value = True
        result = invalidate_user_timelines(user_id)
        assert result is True
        
        # Test Redis error
        mock_invalidate_pattern.return_value = False
        result = invalidate_user_timelines(user_id)
        assert result is False
    
    @patch('utils.cache.cache_set')
    def test_cache_profile(self, mock_cache_set, sample_profile_data):
        """Test caching a user profile."""
        account_id = "user123"
        
        # Test successful caching
        mock_cache_set.return_value = True
        result = cache_profile(account_id, sample_profile_data)
        assert result is True
        mock_cache_set.assert_called_once()
        
        # Verify correct key construction
        args, kwargs = mock_cache_set.call_args
        key = args[0]
        assert key == "profile:user123"
        
        # Test Redis error
        mock_cache_set.reset_mock()
        mock_cache_set.return_value = False
        result = cache_profile(account_id, sample_profile_data)
        assert result is False
    
    @patch('utils.cache.cache_get')
    def test_get_cached_profile(self, mock_cache_get, sample_profile_data):
        """Test retrieving a cached user profile."""
        account_id = "user123"
        
        # Test cache miss
        mock_cache_get.return_value = None
        result = get_cached_profile(account_id)
        assert result is None
        
        # Test cache hit
        mock_cache_get.return_value = sample_profile_data
        result = get_cached_profile(account_id)
        assert result == sample_profile_data
    
    @patch('utils.cache._redis_client_instance', None)
    @patch('utils.cache.cache_delete')
    def test_invalidate_profile(self, mock_cache_delete):
        """Test invalidating a cached user profile."""
        account_id = "user123"
        
        # Test successful invalidation
        mock_cache_delete.return_value = True
        result = invalidate_profile(account_id)
        assert result is True
        mock_cache_delete.assert_called_with("profile:user123")
        
        # Test failed invalidation
        mock_cache_delete.return_value = False
        result = invalidate_profile(account_id)
        assert result is False
    
    @patch('utils.cache.cache_delete')
    @patch('utils.cache.cache_get')
    @patch('utils.cache.cache_set')
    def test_cache_and_get_post(self, mock_cache_set, mock_cache_get, mock_cache_delete, sample_post_data):
        """Test caching and retrieving a post."""
        post_id = "post123"
        
        # Test caching
        mock_cache_set.return_value = True
        result = cache_post(post_id, sample_post_data)
        assert result is True
        mock_cache_set.assert_called_once()
        
        # Verify correct key construction by checking the call args
        args, kwargs = mock_cache_set.call_args
        key = args[0]
        assert key == "post:post123"
        
        # Test retrieval cache miss
        mock_cache_get.return_value = None
        result = get_cached_post(post_id)
        assert result is None
        
        # Test retrieval cache hit
        mock_cache_get.return_value = sample_post_data
        result = get_cached_post(post_id)
        assert result == sample_post_data
        
        # Test invalidation
        mock_cache_delete.return_value = True
        result = invalidate_post(post_id)
        assert result is True
        mock_cache_delete.assert_called_with("post:post123")
    
    @patch('utils.cache.cache_delete')
    @patch('utils.cache.cache_get')
    @patch('utils.cache.cache_set')
    def test_cache_and_get_post_context(self, mock_cache_set, mock_cache_get, mock_cache_delete, sample_post_context):
        """Test caching and retrieving a post context."""
        post_id = "post123"
        
        # Test caching
        mock_cache_set.return_value = True
        result = cache_post_context(post_id, sample_post_context)
        assert result is True
        mock_cache_set.assert_called_once()
        
        # Verify correct key construction
        args, kwargs = mock_cache_set.call_args
        key = args[0]
        assert key == "post:context:post123"
        
        # Test retrieval cache miss
        mock_cache_get.return_value = None
        result = get_cached_post_context(post_id)
        assert result is None
        
        # Test retrieval cache hit
        mock_cache_get.return_value = sample_post_context
        result = get_cached_post_context(post_id)
        assert result == sample_post_context
        
        # Test invalidation
        mock_cache_delete.return_value = True
        result = invalidate_post_context(post_id)
        assert result is True
        mock_cache_delete.assert_called_with("post:context:post123")
    
    @patch('utils.cache.cache_get')
    @patch('utils.cache.cache_set')
    def test_cache_and_get_health_check(self, mock_cache_set, mock_cache_get, sample_health_data):
        """Test caching and retrieving health check data."""
        service_name = "api"
        
        # Test caching
        mock_cache_set.return_value = True
        result = cache_health_check(service_name, sample_health_data)
        assert result is True
        mock_cache_set.assert_called_once()
        
        # Verify correct key construction
        args, kwargs = mock_cache_set.call_args
        key = args[0]
        assert key == "health:api"
        
        # Test retrieval cache miss
        mock_cache_get.return_value = None
        result = get_cached_health_check(service_name)
        assert result is None
        
        # Test retrieval cache hit
        mock_cache_get.return_value = sample_health_data
        result = get_cached_health_check(service_name)
        assert result == sample_health_data
    
    @patch('utils.cache.invalidate_pattern')
    @patch('utils.cache.cache_get')
    @patch('utils.cache.cache_set')
    def test_cache_and_get_api_response(self, mock_cache_set, mock_cache_get, mock_invalidate_pattern, sample_profile_data):
        """Test caching and retrieving generic API responses."""
        endpoint = "accounts/verify_credentials"
        params = {"user_id": "user123"}
        
        # Test caching
        mock_cache_set.return_value = True
        result = cache_api_response(endpoint, params, sample_profile_data)
        assert result is True
        mock_cache_set.assert_called_once()
        
        # Verify correct key construction
        args, kwargs = mock_cache_set.call_args
        key = args[0]
        assert key.startswith("api:accounts/verify_credentials:")
        
        # Test retrieval cache miss
        mock_cache_get.return_value = None
        result = get_cached_api_response(endpoint, params)
        assert result is None
        
        # Test retrieval cache hit
        mock_cache_get.return_value = sample_profile_data
        result = get_cached_api_response(endpoint, params)
        assert result == sample_profile_data
        
        # Test invalidation
        mock_invalidate_pattern.return_value = True
        result = invalidate_api_endpoint(endpoint)
        assert result is True
        mock_invalidate_pattern.assert_called_once()
    
    @patch('utils.cache._redis_client_instance', None)
    @patch('utils.cache.get_redis_client')
    def test_invalidate_pattern(self, mock_get_client):
        """Test invalidating cache entries by pattern."""
        # Create a fresh mock Redis client for this test
        mock_redis = MagicMock()
        mock_get_client.return_value = mock_redis
        
        # Test no keys match
        mock_redis.keys.return_value = []
        result = invalidate_pattern("test:*")
        assert result is True
        mock_redis.delete.assert_not_called()
        
        # Test keys found and deleted
        mock_redis.reset_mock()
        mock_redis.keys.return_value = ["test:1", "test:2", "test:3"]
        result = invalidate_pattern("test:*")
        assert result is True
        mock_redis.delete.assert_called_once_with("test:1", "test:2", "test:3")
        
        # Test Redis error - need to import redis to use the right exception type
        import redis
        mock_redis.reset_mock()
        mock_redis.keys.side_effect = redis.RedisError("Redis connection failed")
        result = invalidate_pattern("test:*")
        assert result is False
        mock_redis.delete.assert_not_called()


@patch('utils.cache.REDIS_ENABLED', False)
class TestExtendedCacheDisabled:
    """Test suite for extended Redis cache module when Redis is disabled."""
    
    def test_timeline_functions_disabled(self):
        """Test timeline cache functions return appropriate values when Redis is disabled."""
        assert cache_timeline("user123", "home", {}, {}) is False
        assert get_cached_timeline("user123", "home", {}) is None
        assert invalidate_user_timelines("user123") is False
    
    def test_profile_functions_disabled(self):
        """Test profile cache functions return appropriate values when Redis is disabled."""
        assert cache_profile("user123", {}) is False
        assert get_cached_profile("user123") is None
        assert invalidate_profile("user123") is False
        assert cache_profile_statuses("user123", {}, []) is False
        assert get_cached_profile_statuses("user123", {}) is None
        assert invalidate_profile_statuses("user123") is False
    
    def test_post_functions_disabled(self):
        """Test post cache functions return appropriate values when Redis is disabled."""
        assert cache_post("post123", {}) is False
        assert get_cached_post("post123") is None
        assert invalidate_post("post123") is False
        assert cache_post_context("post123", {}) is False
        assert get_cached_post_context("post123") is None
        assert invalidate_post_context("post123") is False
    
    def test_health_check_functions_disabled(self):
        """Test health check cache functions return appropriate values when Redis is disabled."""
        assert cache_health_check("service", {}) is False
        assert get_cached_health_check("service") is None
    
    def test_api_response_functions_disabled(self):
        """Test API response cache functions return appropriate values when Redis is disabled."""
        assert cache_api_response("endpoint", {}, {}) is False
        assert get_cached_api_response("endpoint", {}) is None
        assert invalidate_api_endpoint("endpoint") is False
        assert invalidate_pattern("pattern") is False