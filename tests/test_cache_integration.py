"""
Integration tests for Redis caching with the recommendation engine.

These tests verify that Redis caching is properly integrated with the
recommendation engine, including cache hit/miss behavior, invalidation,
and performance improvements.
"""

import json
import pytest
import time
import pickle
from unittest.mock import patch, MagicMock

from config import API_PREFIX
from utils.cache import (
    cache_key, clear_cache, get_cached_recommendations,
    cache_recommendations, invalidate_user_recommendations
)
from utils.recommendation_engine import get_ranked_recommendations


@pytest.fixture
def redis_cache():
    """Create an in-memory mock Redis cache for testing."""
    # In-memory cache storage
    cache_data = {}
    
    # Mock Redis client
    with patch('utils.cache.get_redis_client') as mock_redis:
        mock_client = MagicMock()
        
        # Mock Redis operations with in-memory implementation
        def mock_get(key):
            return cache_data.get(key)
            
        def mock_set(key, value, ex=None):
            cache_data[key] = value
            return True
            
        def mock_delete(key):
            if key in cache_data:
                del cache_data[key]
                return 1
            return 0
            
        def mock_flushdb():
            cache_data.clear()
            return True
            
        # Set up mock methods
        mock_client.get.side_effect = mock_get
        mock_client.set.side_effect = mock_set
        mock_client.delete.side_effect = mock_delete
        mock_client.flushdb.side_effect = mock_flushdb
        mock_client.ping.return_value = True
        
        # Return the mock client
        mock_redis.return_value = mock_client
        
        # Enable Redis for testing
        with patch('utils.cache.REDIS_ENABLED', True), \
             patch('utils.recommendation_engine.REDIS_ENABLED', True):
            yield cache_data


@pytest.fixture
def test_recommendations():
    """Create test recommendation data."""
    return [
        {
            "id": "rec_1",
            "content": "Test recommendation 1",
            "created_at": "2025-05-17T10:00:00Z",
            "account": {
                "id": "unknown",
                "username": "unknown", 
                "display_name": "Unknown User",
                "url": "https://example.com/@unknown"
            },
            "media_attachments": [],
            "mentions": [],
            "tags": [],
            "emojis": [],
            "favourites_count": 0,
            "reblogs_count": 0,
            "replies_count": 0,
            "is_real_mastodon_post": False,
            "is_synthetic": True,
            "injected": True,
            "injection_metadata": {
                "source": "recommendation_engine",
                "strategy": "personalized",
                "score": 0.95,
                "explanation": "Recommended based on your interests"
            }
        },
        {
            "id": "rec_2",
            "content": "Test recommendation 2",
            "created_at": "2025-05-17T09:30:00Z",
            "account": {
                "id": "unknown",
                "username": "unknown",
                "display_name": "Unknown User", 
                "url": "https://example.com/@unknown"
            },
            "media_attachments": [],
            "mentions": [],
            "tags": [],
            "emojis": [],
            "favourites_count": 0,
            "reblogs_count": 0,
            "replies_count": 0,
            "is_real_mastodon_post": False,
            "is_synthetic": True,
            "injected": True,
            "injection_metadata": {
                "source": "recommendation_engine",
                "strategy": "personalized",
                "score": 0.85,
                "explanation": "Recommended based on your interests"
            }
        }
    ]


def test_recommendation_caching_flow(redis_cache, test_recommendations):
    """Test the complete flow of caching recommendations."""
    # Clear cache to start fresh
    clear_cache()
    assert len(redis_cache) == 0
    
    # Test user ID
    test_user_id = "test_user_123"
    
    # 1. Cache miss - no cached recommendations yet
    with patch('utils.metrics.CACHE_MISS_TOTAL.inc') as mock_miss_counter, \
         patch('utils.metrics.CACHE_HIT_TOTAL.inc') as mock_hit_counter:
        result = get_cached_recommendations(test_user_id)
        assert result is None
        mock_miss_counter.assert_called_once()
        mock_hit_counter.assert_not_called()
    
    # 2. Cache recommendations
    success = cache_recommendations(test_user_id, test_recommendations)
    assert success is True
    
    # Verify cache now contains the data
    cache_key_str = cache_key('recommendations', test_user_id)
    assert cache_key_str in redis_cache
    
    # 3. Cache hit - recommendations should be retrieved from cache
    with patch('utils.metrics.CACHE_MISS_TOTAL.inc') as mock_miss_counter, \
         patch('utils.metrics.CACHE_HIT_TOTAL.inc') as mock_hit_counter:
        result = get_cached_recommendations(test_user_id)
        assert result == test_recommendations
        mock_hit_counter.assert_called_once()
        mock_miss_counter.assert_not_called()
    
    # 4. Invalidate the cache
    success = invalidate_user_recommendations(test_user_id)
    assert success is True
    assert cache_key_str not in redis_cache
    
    # 5. Cache miss again after invalidation
    with patch('utils.metrics.CACHE_MISS_TOTAL.inc') as mock_miss_counter:
        result = get_cached_recommendations(test_user_id)
        assert result is None
        mock_miss_counter.assert_called_once()


@patch('utils.recommendation_engine.is_new_user')
@patch('utils.recommendation_engine.generate_rankings_for_user')
def test_get_ranked_recommendations_with_cache(
    mock_generate_rankings, mock_is_new, redis_cache, test_recommendations
):
    """Test get_ranked_recommendations with caching."""
    # Setup mocks
    mock_is_new.return_value = False  # Not a new user
    
    # Create raw ranking data (what generate_rankings_for_user should return)
    raw_ranking_data = [
        {
            "id": "rec_1",
            "content": "Test recommendation 1",
            "created_at": "2025-05-17T10:00:00Z",
            "author_id": "unknown",
            "author_name": "unknown",
            "ranking_score": 0.95,
            "recommendation_reason": "Recommended based on your interests"
        },
        {
            "id": "rec_2",
            "content": "Test recommendation 2", 
            "created_at": "2025-05-17T09:30:00Z",
            "author_id": "unknown",
            "author_name": "unknown",
            "ranking_score": 0.85,
            "recommendation_reason": "Recommended based on your interests"
        }
    ]
    mock_generate_rankings.return_value = raw_ranking_data
    
    # Clear cache and prepare test data
    clear_cache()
    test_user_id = "returning_user_456"
    
    # First call should generate rankings and cache them
    with patch('utils.metrics.RECOMMENDATIONS_TOTAL.labels') as mock_metrics:
        result1 = get_ranked_recommendations(test_user_id)
        
        # Verify results are transformed to Mastodon format
        assert len(result1) == 2
        assert result1[0]["id"] == "rec_1"
        assert result1[0]["injection_metadata"]["score"] == 0.95
        assert result1[1]["id"] == "rec_2"
        assert result1[1]["injection_metadata"]["score"] == 0.85
        mock_generate_rankings.assert_called_once()
        
        # Verify cache was populated
        cache_key_str = cache_key('recommendations', test_user_id)
        assert cache_key_str in redis_cache
    
    # Reset mocks for second call
    mock_generate_rankings.reset_mock()
    
    # Second call should use cache
    with patch('utils.metrics.RECOMMENDATIONS_TOTAL.labels') as mock_metrics:
        result2 = get_ranked_recommendations(test_user_id)
        
        # Verify results are identical to first call
        assert len(result2) == 2
        assert result2[0]["id"] == "rec_1"
        assert result2[0]["injection_metadata"]["score"] == 0.95
        assert result2[1]["id"] == "rec_2" 
        assert result2[1]["injection_metadata"]["score"] == 0.85
        mock_generate_rankings.assert_not_called()  # Should not generate new rankings
    
    # Try with cache bypass
    mock_generate_rankings.reset_mock()
    
    # Call with use_cache=False should bypass cache
    with patch('utils.metrics.RECOMMENDATIONS_TOTAL.labels') as mock_metrics:
        result3 = get_ranked_recommendations(test_user_id, use_cache=False)
        
        # Verify results are transformed properly
        assert len(result3) == 2
        assert result3[0]["id"] == "rec_1"
        assert result3[0]["injection_metadata"]["score"] == 0.95
        assert result3[1]["id"] == "rec_2"
        assert result3[1]["injection_metadata"]["score"] == 0.85
        mock_generate_rankings.assert_called_once()  # Should generate new rankings


@patch('utils.recommendation_engine.load_cold_start_posts')
def test_cold_start_recommendations_not_cached(mock_load_cold_start, redis_cache):
    """Test that cold start recommendations are not cached."""
    # Set up mock cold start data
    cold_start_data = [
        {"id": "cold_1", "content": "Cold start post 1"},
        {"id": "cold_2", "content": "Cold start post 2"}
    ]
    mock_load_cold_start.return_value = cold_start_data
    
    # Clear cache
    clear_cache()
    
    # Test for different types of users that should get cold start recommendations
    test_cases = [
        None,  # Anonymous user
        "anonymous",  # Explicit anonymous user
        "test_validator_123",  # Validator user
        "corgi_validator_456"  # Corgi validator user
    ]
    
    for user_id in test_cases:
        # Get recommendations
        result = get_ranked_recommendations(user_id)
        
        # Verify cold start data was returned
        assert result == cold_start_data
        
        # Verify nothing was cached
        if user_id:
            cache_key_str = cache_key('recommendations', user_id)
            assert cache_key_str not in redis_cache
    
    # Verify load_cold_start_posts was called for each test case
    assert mock_load_cold_start.call_count == len(test_cases)


@patch('utils.recommendation_engine.is_new_user')
def test_new_user_with_cache(mock_is_new, redis_cache):
    """Test that new users get cold start recommendations (not cached)."""
    # Setup mock
    mock_is_new.return_value = True  # This is a new user
    
    # Set up cold start data
    cold_start_data = [
        {"id": "cold_1", "content": "Cold start post 1"},
        {"id": "cold_2", "content": "Cold start post 2"}
    ]
    
    # Clear cache
    clear_cache()
    test_user_id = "new_user_789"
    
    # Mock load_cold_start_posts to return our test data
    with patch('utils.recommendation_engine.load_cold_start_posts') as mock_load_cold:
        mock_load_cold.return_value = cold_start_data
        
        # Get recommendations for new user
        result = get_ranked_recommendations(test_user_id)
        
        # Verify cold start data was returned
        assert result == cold_start_data
        
        # Verify nothing was cached for this user
        cache_key_str = cache_key('recommendations', test_user_id)
        assert cache_key_str not in redis_cache
        
        # Verify generate_rankings_for_user was not called
        # (cold start data was used instead)
        with patch('utils.recommendation_engine.generate_rankings_for_user') as mock_generate:
            get_ranked_recommendations(test_user_id)
            mock_generate.assert_not_called()


@patch('utils.recommendation_engine.is_new_user')
def test_cache_performance(mock_is_new, redis_cache):
    """Test performance improvements from caching."""
    # Setup mocks
    mock_is_new.return_value = False  # Not a new user
    
    # Clear cache and prepare test data
    clear_cache()
    test_user_id = "performance_test_user"
    
    # Create complex recommendations data in the raw ranking algorithm output format
    # This is what generate_rankings_for_user should return (before Mastodon transformation)
    complex_recommendations = [
        {
            "id": f"rec_{i}",
            "content": f"Complex recommendation content {i}",
            "created_at": "2025-05-17T10:00:00Z",
            "author_id": "unknown",
            "author_name": "unknown",
            "ranking_score": 0.95 - (i * 0.01),  # This is the key field the recommendation engine expects
            "recommendation_reason": "Recommended based on your interests"
        }
        for i in range(10)  # Create 10 complex recommendations
    ]
    
    # Slow ranking generation function
    def slow_ranking_generation(user_id):
        # Simulate complex computation
        time.sleep(0.1)  # 100ms delay
        return complex_recommendations
    
    # First call - without cache
    with patch('utils.recommendation_engine.generate_rankings_for_user',
               side_effect=slow_ranking_generation):
        start_time = time.time()
        result1 = get_ranked_recommendations(test_user_id)
        uncached_time = time.time() - start_time
        
        # Verify results - should be transformed to Mastodon format
        assert len(result1) == 10
        for i, post in enumerate(result1):
            assert post["id"] == f"rec_{i}"
            assert post["content"] == f"Complex recommendation content {i}"
            assert post["injection_metadata"]["score"] == 0.95 - (i * 0.01)
            assert post["is_synthetic"] == True
            assert post["injected"] == True
        
    # Second call - with cache
    start_time = time.time()
    result2 = get_ranked_recommendations(test_user_id)
    cached_time = time.time() - start_time
    
    # Verify results - should be identical to first call
    assert len(result2) == 10
    for i, post in enumerate(result2):
        assert post["id"] == f"rec_{i}"
        assert post["content"] == f"Complex recommendation content {i}"
        assert post["injection_metadata"]["score"] == 0.95 - (i * 0.01)
        assert post["is_synthetic"] == True
        assert post["injected"] == True
    
    # Verify cache is significantly faster
    assert cached_time < uncached_time
    assert cached_time < 0.05  # Should be very fast (< 50ms)
    
    # Verify ratio improvement
    speed_improvement = uncached_time / max(cached_time, 0.001)  # Avoid division by zero
    assert speed_improvement > 2.0  # At least 2x faster