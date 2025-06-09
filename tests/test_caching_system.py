"""
Comprehensive tests for the caching system.

This module consolidates tests for Redis caching, cache extensions, 
cache integration, and specialized caches (recommendations, timeline).
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock
import redis.exceptions
from redis import Redis as RealRedisClass_for_spec
from config import REDIS_TTL_RECOMMENDATIONS

from utils.cache import (
    get_redis_client, clear_cache, cache_key, cache_get, cache_set,
    cache_delete, invalidate_user_recommendations, cache_recommendations,
    get_cached_recommendations, REDIS_ENABLED as CACHE_REDIS_ENABLED
)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.delete.return_value = 1
    mock_client.flushdb.return_value = True
    
    # Simulate cache storage
    mock_client._data = {}
    
    def mock_get(key):
        return mock_client._data.get(key)
    
    def mock_set(key, value, ex=None):
        mock_client._data[key] = value
        return True
    
    def mock_delete(key):
        if key in mock_client._data:
            del mock_client._data[key]
            return 1
        return 0
    
    def mock_flushdb():
        mock_client._data.clear()
        return True
    
    mock_client.get.side_effect = mock_get
    mock_client.set.side_effect = mock_set
    mock_client.delete.side_effect = mock_delete
    mock_client.flushdb.side_effect = mock_flushdb
    
    return mock_client


@pytest.fixture
def sample_recommendations():
    """Create sample recommendation data for testing."""
    return [
        {
            "id": "post_1",
            "content": "Test post 1",
            "created_at": "2025-05-01T12:00:00Z",
            "account": {
                "id": "user_1", 
                "username": "user1",
                "display_name": "User One"
            },
            "injected": True,
            "injection_metadata": {
                "source": "recommendation_engine",
                "strategy": "personalized",
                "score": 0.85
            }
        }
    ]


@pytest.fixture
def sample_timeline_data():
    """Create sample timeline data for testing."""
    return [
        {
            "id": "timeline_post_1",
            "content": "Timeline post 1", 
            "created_at": "2025-05-01T10:00:00Z",
            "account": {"id": "author_1", "username": "author1"}
        },
        {
            "id": "timeline_post_2",
            "content": "Timeline post 2",
            "created_at": "2025-05-01T11:00:00Z", 
            "account": {"id": "author_2", "username": "author2"}
        }
    ]


class TestRedisClient:
    """Test Redis client connection and basic operations."""
    
    @patch('utils.cache.REDIS_ENABLED', True)
    def test_get_redis_client(self, mocker):
        """Test getting a Redis client instance."""
        mocker.patch('utils.cache._redis_client_instance', None)
        mock_redis_constructor = mocker.patch('redis.Redis')
        
        mock_created_instance = MagicMock(spec=RealRedisClass_for_spec)
        mock_created_instance.ping.return_value = True
        mock_redis_constructor.return_value = mock_created_instance
        
        # First call creates new client
        client = get_redis_client()
        assert client is mock_created_instance
        mock_redis_constructor.assert_called_once()
        
        # Second call returns existing client
        client2 = get_redis_client()
        assert client2 is mock_created_instance
    
    @patch('utils.cache.REDIS_ENABLED', True)
    def test_redis_connection_error(self, mocker):
        """Test handling Redis connection errors."""
        mocker.patch('utils.cache._redis_client_instance', None)
        mock_redis_constructor = mocker.patch('redis.Redis')
        
        mock_instance = MagicMock(spec=RealRedisClass_for_spec)
        mock_instance.ping.side_effect = redis.exceptions.RedisError("Connection failed")
        mock_redis_constructor.return_value = mock_instance
        
        with patch('utils.cache.logger.error'):
            client = get_redis_client()
            assert client is None
    
    @patch('utils.cache.REDIS_ENABLED', False)
    def test_redis_disabled(self):
        """Test behavior when Redis is disabled."""
        client = get_redis_client()
        assert client is None


class TestCacheOperations:
    """Test basic cache operations (get, set, delete)."""
    
    @patch('utils.cache.REDIS_ENABLED', True)
    @patch('utils.cache.get_redis_client')
    def test_cache_key_format(self, mock_get_client):
        """Test cache key generation."""
        key = cache_key("recommendations", "user123")
        assert key == "recommendations:user123"
        
        key = cache_key("timeline", "home:user456")
        assert key == "timeline:home:user456"
    
    @patch('utils.cache.REDIS_ENABLED', True)
    @patch('utils.cache.get_redis_client')
    def test_cache_get_set_delete(self, mock_get_client, mock_redis, sample_recommendations):
        """Test cache get, set, and delete operations."""
        mock_get_client.return_value = mock_redis
        
        # Test cache miss
        result = cache_get("test:key")
        assert result is None
        
        # Test cache set and hit
        value = sample_recommendations
        cache_set("test:key", value, ttl=300)
        
        result = cache_get("test:key")
        assert result == value
        
        # Test cache delete
        deleted_count = cache_delete("test:key")
        assert deleted_count == 1
        
        # Verify deletion
        result = cache_get("test:key")
        assert result is None
    
    @patch('utils.cache.REDIS_ENABLED', True)
    @patch('utils.cache.get_redis_client')
    def test_cache_set_non_serializable(self, mock_get_client, mock_redis):
        """Test caching non-serializable objects."""
        mock_get_client.return_value = mock_redis
        
        class NonSerializable:
            pass
        
        with patch('utils.cache.logger.error'):
            result = cache_set("test:key", NonSerializable())
            assert result is False
    
    @patch('utils.cache.REDIS_ENABLED', True)
    @patch('utils.cache.get_redis_client')
    def test_clear_cache(self, mock_get_client, mock_redis):
        """Test clearing all cache data."""
        mock_get_client.return_value = mock_redis
        
        result = clear_cache()
        assert result is True
        mock_redis.flushdb.assert_called_once()


class TestRecommendationCache:
    """Test recommendation-specific caching."""
    
    @patch('utils.cache.REDIS_ENABLED', True)
    @patch('utils.cache.cache_set')
    def test_cache_recommendations(self, mock_cache_set, sample_recommendations):
        """Test caching recommendations for a user."""
        user_id = "user123"
        cache_recommendations(user_id, sample_recommendations)
        
        expected_key = cache_key("recommendations", user_id)
        mock_cache_set.assert_called_once_with(
            expected_key, 
            sample_recommendations, 
            ttl=REDIS_TTL_RECOMMENDATIONS,
            cache_type='recommendations'
        )
    
    @patch('utils.cache.REDIS_ENABLED', True)
    @patch('utils.cache.cache_get')
    def test_get_cached_recommendations(self, mock_cache_get, sample_recommendations):
        """Test retrieving cached recommendations."""
        user_id = "user123"
        mock_cache_get.return_value = sample_recommendations
        
        result = get_cached_recommendations(user_id)
        
        expected_key = cache_key("recommendations", user_id)
        mock_cache_get.assert_called_once_with(expected_key, cache_type='recommendations', endpoint='recommendations')
        assert result == sample_recommendations
    
    @patch('utils.cache.REDIS_ENABLED', True)
    @patch('utils.cache.cache_delete')
    def test_invalidate_user_recommendations(self, mock_cache_delete):
        """Test invalidating user's cached recommendations."""
        user_id = "user123"
        invalidate_user_recommendations(user_id)
        
        expected_key = cache_key("recommendations", user_id)
        mock_cache_delete.assert_called_once_with(expected_key)


class TestTimelineCache:
    """Test timeline-specific caching."""
    
    @patch('utils.cache.REDIS_ENABLED', True)
    def test_timeline_cache_key_generation(self):
        """Test timeline cache key generation."""
        user_id = "user123"
        timeline_type = "home"
        
        key = cache_key("timeline", f"{timeline_type}:{user_id}")
        assert key == "timeline:home:user123"
    
    @patch('utils.cache.REDIS_ENABLED', True)
    @patch('utils.cache.get_redis_client')
    def test_cache_timeline_data(self, mock_get_client, sample_timeline_data):
        """Test caching timeline data."""
        # Mock Redis client to avoid connection issues
        mock_redis = MagicMock()
        mock_redis.set.return_value = True
        mock_get_client.return_value = mock_redis
        
        user_id = "user123"
        timeline_type = "home"
        timeline_key = cache_key("timeline", f"{timeline_type}:{user_id}")
        
        # Simulate caching timeline data
        result = cache_set(timeline_key, sample_timeline_data, ttl=300)
        
        # Verify that cache_set succeeded
        assert result is True
        
        # Verify that Redis client set was called with correct parameters
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == timeline_key  # key
        assert call_args[1]['ex'] == 300  # ttl


class TestCacheIntegration:
    """Test cache integration scenarios."""
    
    @patch('utils.cache.REDIS_ENABLED', True)
    @patch('utils.cache.get_redis_client')
    def test_cache_performance_under_load(self, mock_get_client, mock_redis):
        """Test cache performance with multiple operations."""
        mock_get_client.return_value = mock_redis
        
        # Simulate multiple cache operations
        for i in range(10):
            key = f"test:key:{i}"
            value = {"id": i, "data": f"test_data_{i}"}
            
            # Set data
            result = cache_set(key, value, ttl=300)
            assert result is True
            
            # Get data
            cached_value = cache_get(key)
            assert cached_value == value
        
        # Verify all keys are cached
        assert len(mock_redis._data) == 10
    
    @patch('utils.cache.REDIS_ENABLED', True)
    def test_cache_key_collision_prevention(self):
        """Test that cache keys are unique and don't collide."""
        user1_rec_key = cache_key("recommendations", "user1")
        user2_rec_key = cache_key("recommendations", "user2")
        user1_timeline_key = cache_key("timeline", "home:user1")
        
        assert user1_rec_key != user2_rec_key
        assert user1_rec_key != user1_timeline_key
        assert user2_rec_key != user1_timeline_key
    
    @patch('utils.cache.REDIS_ENABLED', True)
    @patch('utils.cache.get_redis_client')
    def test_cache_error_recovery(self, mock_get_client, mock_redis):
        """Test cache error handling and recovery."""
        mock_get_client.return_value = mock_redis
        
        # Test Redis error during get
        mock_redis.get.side_effect = redis.exceptions.RedisError("Redis error")
        
        with patch('utils.cache.logger.error'):
            result = cache_get("test:key")
            assert result is None
        
        # Test Redis error during set
        mock_redis.set.side_effect = redis.exceptions.RedisError("Redis error")
        
        with patch('utils.cache.logger.error'):
            result = cache_set("test:key", {"data": "test"})
            assert result is False


class TestCacheDisabled:
    """Test cache behavior when Redis is disabled."""
    
    @patch('utils.cache.REDIS_ENABLED', False)
    def test_cache_operations_when_disabled(self):
        """Test that cache operations handle disabled Redis gracefully."""
        # Test get returns None
        result = cache_get("test:key")
        assert result is None
        
        # Test set returns False
        result = cache_set("test:key", {"data": "test"})
        assert result is False
        
        # Test delete returns 0
        result = cache_delete("test:key")
        assert result == 0
        
        # Test clear returns False
        result = clear_cache()
        assert result is False
    
    @patch('utils.cache.REDIS_ENABLED', False)
    def test_recommendation_cache_when_disabled(self):
        """Test recommendation caching when Redis is disabled."""
        user_id = "user123"
        
        # Test get recommendations returns None
        result = get_cached_recommendations(user_id)
        assert result is None
        
        # Test cache and invalidate operations don't error
        cache_recommendations(user_id, [{"id": "test"}])
        invalidate_user_recommendations(user_id) 