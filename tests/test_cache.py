"""
Tests for the Redis caching module.
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
    mock_client.get.return_value = None  # Default behavior is cache miss
    mock_client.set.return_value = True  # Default behavior is successful set
    mock_client.delete.return_value = 1  # Default behavior is successful delete
    mock_client.flushdb.return_value = True  # Default behavior is successful flush
    
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
    def mock_delete(key):
        if key in mock_client._data:
            del mock_client._data[key]
            return 1
        return 0
    
    # Override the flushdb method to clear the dictionary
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
                "display_name": "User One",
                "url": "https://example.com/@user1"
            },
            "injected": True,
            "injection_metadata": {
                "source": "recommendation_engine",
                "strategy": "personalized",
                "score": 0.85
            }
        },
        {
            "id": "post_2",
            "content": "Test post 2",
            "created_at": "2025-05-02T14:30:00Z",
            "account": {
                "id": "user_2",
                "username": "user2",
                "display_name": "User Two",
                "url": "https://example.com/@user2"
            },
            "injected": True,
            "injection_metadata": {
                "source": "recommendation_engine",
                "strategy": "personalized",
                "score": 0.75
            }
        }
    ]


@patch('utils.cache.REDIS_ENABLED', True)
class TestCache:
    """Test suite for the Redis cache module."""
    
    def test_get_redis_client(self, mocker):
        """Test getting a Redis client instance."""
        mocker.patch('utils.cache._redis_client_instance', None)
        mock_redis_constructor = mocker.patch('redis.Redis')
        
        mock_created_instance = MagicMock(spec=RealRedisClass_for_spec)
        mock_created_instance.ping.return_value = True
        mock_redis_constructor.return_value = mock_created_instance
        
        # First call should create a new client
        client = get_redis_client()
        assert client is mock_created_instance
        mock_redis_constructor.assert_called_once()
        mock_created_instance.ping.assert_called_once()
        
        # Reset mocks for second call verification
        mock_redis_constructor.reset_mock()
        mock_created_instance.ping.reset_mock()
        
        # Second call should return existing client
        client2 = get_redis_client()
        assert client2 is mock_created_instance
        mock_redis_constructor.assert_not_called()
        mock_created_instance.ping.assert_not_called()
    
    def test_get_redis_client_connection_error(self, mocker):
        """Test handling Redis connection errors."""
        mocker.patch('utils.cache._redis_client_instance', None)
        mock_redis_constructor = mocker.patch('redis.Redis')
        
        mock_created_instance = MagicMock(spec=RealRedisClass_for_spec)
        mock_created_instance.ping.side_effect = redis.exceptions.RedisError("Simulated connection error")
        mock_redis_constructor.return_value = mock_created_instance
        
        with patch('utils.cache.logger.error') as mock_logger_error:
            client = get_redis_client()
            assert client is None
            mock_redis_constructor.assert_called_once()
            mock_created_instance.ping.assert_called_once()
            mock_logger_error.assert_called_once_with("Redis connection failed: Simulated connection error")
    
    @patch('utils.cache._redis_client_instance', None)
    @patch('utils.cache.get_redis_client')
    def test_clear_cache(self, mock_get_client_func, mock_redis):
        """Test clearing all cache data."""
        mock_get_client_func.return_value = mock_redis
        
        # Test successful cache clear
        result = clear_cache()
        assert result is True
        mock_redis.flushdb.assert_called_once()
        
        # Test cache clear with client error
        mock_redis.flushdb.reset_mock()
        mock_redis.flushdb.side_effect = redis.exceptions.RedisError("Flush failed")
        with patch('utils.cache.logger.error') as mock_logger_error:
            result = clear_cache()
            assert result is False
            mock_logger_error.assert_called_once_with("Error clearing cache: Flush failed")
        
        # Test cache clear with no client
        mock_redis.flushdb.reset_mock()
        mock_redis.flushdb.side_effect = None
        mock_get_client_func.return_value = None
        result = clear_cache()
        assert result is False
    
    def test_cache_key_format(self):
        """Test cache key generation."""
        key = cache_key("recommendations", "user123")
        assert key == "recommendations:user123"
        
        key = cache_key("timeline", "home:user456")
        assert key == "timeline:home:user456"
    
    @patch('utils.cache._redis_client_instance', None)
    @patch('utils.cache.get_redis_client')
    def test_cache_get(self, mock_get_client_func, mock_redis, sample_recommendations):
        """Test retrieving values from cache."""
        mock_get_client_func.return_value = mock_redis
        
        # Test cache miss
        result = cache_get("test:key")
        assert result is None
        mock_redis.get.assert_called_with("test:key")
        
        # Test cache hit
        value = sample_recommendations
        json_value = json.dumps(value)
        mock_redis._data["test:key"] = json_value
        
        result = cache_get("test:key")
        assert result == value
        
        # Test Redis error
        mock_redis.get.reset_mock()
        mock_redis.get.side_effect = redis.exceptions.RedisError("Redis error")
        with patch('utils.cache.logger.error') as mock_logger_error:
            result = cache_get("test:key")
            assert result is None
            mock_logger_error.assert_called_once_with("Error retrieving from cache: Redis error")
        
        # Test JSON decoding error
        mock_redis.get.reset_mock()
        mock_redis.get.side_effect = None
        mock_redis.get.return_value = "invalid json data"
        result = cache_get("test:key")
        assert result is None
        
        # Test no Redis client
        mock_get_client_func.return_value = None
        result = cache_get("test:key")
        assert result is None
    
    @patch('utils.cache._redis_client_instance', None)
    @patch('utils.cache.get_redis_client')
    def test_cache_set(self, mock_get_client_func, mock_redis, sample_recommendations):
        """Test storing values in cache."""
        mock_get_client_func.return_value = mock_redis
        
        # Test successful cache set
        result = cache_set("test:key", sample_recommendations, 3600)
        assert result is True
        mock_redis.set.assert_called_once()
        args, kwargs = mock_redis.set.call_args
        assert args[0] == "test:key"
        assert isinstance(args[1], str)  # Should be JSON string
        assert kwargs['ex'] == 3600
        
        # Test Redis error
        mock_redis.set.reset_mock()
        mock_redis.set.side_effect = redis.exceptions.RedisError("Redis error")
        with patch('utils.cache.logger.error') as mock_logger_error:
            result = cache_set("test:key", sample_recommendations)
            assert result is False
            mock_logger_error.assert_called_once_with("Error setting cache: Redis error")
        
        # Test JSON serialization error (using a non-serializable object)
        mock_redis.set.reset_mock()
        mock_redis.set.side_effect = None
        
        class NonSerializable:
            pass
        
        with patch('utils.cache.logger.error') as mock_logger_error:
            result = cache_set("test:key", NonSerializable())
            assert result is False
            mock_logger_error.assert_called_once()
            args, _ = mock_logger_error.call_args
            assert "Error setting cache:" in args[0]
        
        # Test no Redis client
        mock_get_client_func.return_value = None
        result = cache_set("test:key", sample_recommendations)
        assert result is False
    
    @patch('utils.cache._redis_client_instance', None)
    @patch('utils.cache.get_redis_client')
    def test_cache_delete(self, mock_get_client_func, mock_redis):
        """Test deleting values from cache."""
        mock_get_client_func.return_value = mock_redis
        
        # Test successful delete (key exists)
        mock_redis._data["test:key"] = json.dumps("some dummy data")
        result = cache_delete("test:key")
        assert result is True
        mock_redis.delete.assert_called_with("test:key")
        
        # Test key not found
        mock_redis.delete.return_value = 0
        result = cache_delete("test:key")
        assert result is False
        
        # Test Redis error
        mock_redis.delete.reset_mock()
        mock_redis.delete.side_effect = redis.exceptions.RedisError("Redis error")
        with patch('utils.cache.logger.error') as mock_logger_error:
            result = cache_delete("test:key")
            assert result is False
            mock_logger_error.assert_called_once_with("Error deleting from cache: Redis error")
        
        # Test no Redis client
        mock_get_client_func.return_value = None
        result = cache_delete("test:key")
        assert result is False
    
    @patch('utils.cache._redis_client_instance', None)
    @patch('utils.cache.cache_delete')
    def test_invalidate_user_recommendations(self, mock_cache_delete):
        """Test invalidating a user's cached recommendations."""
        user_id = "user123"
        
        # Test successful invalidation
        mock_cache_delete.return_value = True
        result = invalidate_user_recommendations(user_id)
        assert result is True
        mock_cache_delete.assert_called_with("recommendations:user123")
        
        # Test failed invalidation
        mock_cache_delete.return_value = False
        result = invalidate_user_recommendations(user_id)
        assert result is False
    
    @patch('utils.cache._redis_client_instance', None)
    @patch('utils.cache.cache_set')
    def test_cache_recommendations(self, mock_cache_set_func, sample_recommendations):
        """Test caching user recommendations."""
        user_id = "user123"
        
        # Test successful caching
        mock_cache_set_func.return_value = True
        result = cache_recommendations(user_id, sample_recommendations)
        assert result is True
        expected_key = cache_key("recommendations", user_id)
        mock_cache_set_func.assert_called_once_with(expected_key, sample_recommendations, ttl=REDIS_TTL_RECOMMENDATIONS)
        
        # Test failed caching
        mock_cache_set_func.reset_mock()
        mock_cache_set_func.return_value = False
        result = cache_recommendations(user_id, sample_recommendations)
        assert result is False
    
    @patch('utils.cache._redis_client_instance', None)
    @patch('utils.cache.cache_get')
    def test_get_cached_recommendations(self, mock_cache_get_func, sample_recommendations):
        """Test retrieving cached user recommendations."""
        user_id = "user123"
        
        # Test successful retrieval
        mock_cache_get_func.return_value = sample_recommendations
        result = get_cached_recommendations(user_id)
        assert result == sample_recommendations
        expected_key = cache_key("recommendations", "user123")
        mock_cache_get_func.assert_called_once_with(expected_key)
        
        # Test cache miss
        mock_cache_get_func.reset_mock()
        mock_cache_get_func.return_value = None
        result = get_cached_recommendations(user_id)
        assert result is None


@patch('utils.cache.REDIS_ENABLED', False)
class TestCacheDisabled:
    """Test suite for Redis cache module when Redis is disabled."""
    
    def test_get_redis_client_disabled(self):
        """Test client returns None when Redis is disabled."""
        client = get_redis_client()
        assert client is None
    
    def test_cache_operations_disabled(self):
        """Test cache operations return appropriate values when Redis is disabled."""
        # All operations should fail gracefully
        assert clear_cache() is False
        assert cache_get("test:key") is None
        assert cache_set("test:key", "value") is False
        assert cache_delete("test:key") is False
        assert invalidate_user_recommendations("user123") is False
        assert cache_recommendations("user123", []) is False
        assert get_cached_recommendations("user123") is None