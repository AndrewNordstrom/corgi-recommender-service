"""
Tests for the Mastodon API Client functionality.

This module tests the fresh status fetching implementation for Option A.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import the modules we're testing
from utils.mastodon_api import MastodonAPIClient, fetch_fresh_mastodon_statuses, mastodon_client
from utils.token_refresh import get_user_token_data, is_token_expired, refresh_access_token


class TestMastodonAPIClient:
    """Test the MastodonAPIClient class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = MastodonAPIClient()
        self.test_post_id = "112345678901234567"
        self.test_instance_url = "https://mastodon.social"
        self.test_access_token = "test_access_token_123"
        
        # Sample Mastodon status object
        self.sample_status = {
            "id": self.test_post_id,
            "created_at": "2024-01-15T10:30:00.000Z",
            "account": {
                "id": "123456",
                "username": "testuser",
                "display_name": "Test User",
                "url": "https://mastodon.social/@testuser"
            },
            "content": "<p>This is a test post</p>",
            "favourites_count": 5,
            "reblogs_count": 2,
            "replies_count": 1,
            "language": "en",
            "url": f"https://mastodon.social/@testuser/{self.test_post_id}"
        }
    
    @patch('utils.mastodon_api.requests.Session.get')
    def test_get_fresh_status_success(self, mock_get):
        """Test successful fresh status retrieval."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_status
        mock_get.return_value = mock_response
        
        # Test the method
        result = self.client.get_fresh_status(
            self.test_post_id, 
            self.test_instance_url, 
            self.test_access_token
        )
        
        # Verify result
        assert result == self.sample_status
        
        # Verify API call was made correctly
        mock_get.assert_called_once_with(
            f"{self.test_instance_url}/api/v1/statuses/{self.test_post_id}",
            headers={'Authorization': f'Bearer {self.test_access_token}'},
            timeout=10
        )
    
    @patch('utils.mastodon_api.requests.Session.get')
    def test_get_fresh_status_not_found(self, mock_get):
        """Test handling of 404 Not Found responses."""
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        # Test the method
        result = self.client.get_fresh_status(
            self.test_post_id, 
            self.test_instance_url, 
            self.test_access_token
        )
        
        # Should return None for 404
        assert result is None
    
    @patch('utils.mastodon_api.requests.Session.get')
    def test_get_fresh_status_unauthorized(self, mock_get):
        """Test handling of 401 Unauthorized responses."""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        # Test the method
        result = self.client.get_fresh_status(
            self.test_post_id, 
            self.test_instance_url, 
            self.test_access_token
        )
        
        # Should return None for 401
        assert result is None
    
    @patch('utils.mastodon_api.requests.Session.get')
    def test_get_fresh_status_timeout(self, mock_get):
        """Test handling of request timeouts."""
        # Mock timeout exception
        from requests import Timeout
        mock_get.side_effect = Timeout("Request timed out")
        
        # Test the method
        result = self.client.get_fresh_status(
            self.test_post_id, 
            self.test_instance_url, 
            self.test_access_token
        )
        
        # Should return None for timeout
        assert result is None
    
    def test_instance_url_normalization(self):
        """Test that instance URLs are properly normalized."""
        with patch('utils.mastodon_api.requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = self.sample_status
            mock_get.return_value = mock_response
            
            # Test with URL without scheme
            self.client.get_fresh_status(
                self.test_post_id, 
                "mastodon.social",  # No https://
                self.test_access_token
            )
            
            # Should have added https://
            mock_get.assert_called_with(
                f"https://mastodon.social/api/v1/statuses/{self.test_post_id}",
                headers={'Authorization': f'Bearer {self.test_access_token}'},
                timeout=10
            )
    
    @patch('utils.mastodon_api.cache_get')
    def test_get_cached_status_hit(self, mock_cache_get):
        """Test cache hit scenario."""
        # Mock cache hit
        mock_cache_get.return_value = self.sample_status
        
        result = self.client.get_cached_status(self.test_post_id, self.test_instance_url)
        
        assert result == self.sample_status
        mock_cache_get.assert_called_once_with(f"mastodon_status:{self.test_instance_url}:{self.test_post_id}")
    
    @patch('utils.mastodon_api.cache_get')
    def test_get_cached_status_miss(self, mock_cache_get):
        """Test cache miss scenario."""
        # Mock cache miss
        mock_cache_get.return_value = None
        
        result = self.client.get_cached_status(self.test_post_id, self.test_instance_url)
        
        assert result is None
    
    @patch('utils.mastodon_api.cache_set')
    def test_cache_status_success(self, mock_cache_set):
        """Test successful status caching."""
        # Mock successful cache set
        mock_cache_set.return_value = True
        
        result = self.client.cache_status(
            self.test_post_id, 
            self.test_instance_url, 
            self.sample_status,
            ttl=300
        )
        
        assert result is True
        mock_cache_set.assert_called_once_with(
            f"mastodon_status:{self.test_instance_url}:{self.test_post_id}",
            self.sample_status,
            ttl=300
        )


class TestFetchFreshMastodonStatuses:
    """Test the main fetch_fresh_mastodon_statuses function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_user_id = "test_user_123"
        self.test_recommendations = [
            {
                'post_id': '112345678901234567',
                'ranking_score': 0.95,
                'recommendation_reason': 'High engagement content'
            },
            {
                'post_id': '112345678901234568', 
                'ranking_score': 0.88,
                'recommendation_reason': 'Similar topic interest'
            }
        ]
        
        self.test_token_data = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'token_expires_at': datetime.utcnow() + timedelta(hours=1),
            'instance_url': 'https://mastodon.social',
            'user_id': self.test_user_id
        }
    
    @patch('utils.mastodon_api.get_user_token_data')
    def test_no_token_data(self, mock_get_token_data):
        """Test handling when no token data is found."""
        mock_get_token_data.return_value = None
        
        result = fetch_fresh_mastodon_statuses(self.test_recommendations, self.test_user_id)
        
        assert result == []
        mock_get_token_data.assert_called_once_with(self.test_user_id)
    
    def test_empty_recommendations(self):
        """Test handling of empty recommendations list."""
        result = fetch_fresh_mastodon_statuses([], self.test_user_id)
        assert result == []
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.is_token_expired')
    @patch('utils.mastodon_api.mastodon_client.get_cached_status')
    @patch('utils.mastodon_api.mastodon_client.get_fresh_status')
    @patch('utils.mastodon_api.mastodon_client.cache_status')
    def test_successful_fresh_fetch(self, mock_cache_status, mock_get_fresh, 
                                  mock_get_cached, mock_is_expired, mock_get_token_data):
        """Test successful fresh status fetching."""
        # Setup mocks
        mock_get_token_data.return_value = self.test_token_data
        mock_is_expired.return_value = False
        mock_get_cached.return_value = None  # Cache miss
        
        # Mock fresh status responses
        fresh_statuses = []
        for i, rec in enumerate(self.test_recommendations):
            status = {
                "id": rec['post_id'],
                "content": f"Test content {i}",
                "account": {"username": f"user{i}"},
                "created_at": datetime.utcnow().isoformat()
            }
            fresh_statuses.append(status)
        
        mock_get_fresh.side_effect = fresh_statuses
        mock_cache_status.return_value = True
        
        # Test the function
        result = fetch_fresh_mastodon_statuses(self.test_recommendations, self.test_user_id)
        
        # Verify results
        assert len(result) == 2
        
        for i, status in enumerate(result):
            # Check that recommendation metadata was added
            assert status['is_recommendation'] is True
            assert status['ranking_score'] == self.test_recommendations[i]['ranking_score']
            assert status['recommendation_reason'] == self.test_recommendations[i]['recommendation_reason']
            assert 'recommendation_metadata' in status
            assert status['recommendation_metadata']['source'] == 'corgi_recommendation_engine'
            assert status['recommendation_metadata']['fetched_from_cache'] is False
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.is_token_expired')
    @patch('utils.mastodon_api.mastodon_client.get_cached_status')
    def test_cache_hit_scenario(self, mock_get_cached, mock_is_expired, mock_get_token_data):
        """Test cache hit scenario."""
        # Setup mocks
        mock_get_token_data.return_value = self.test_token_data
        mock_is_expired.return_value = False
        
        # Mock cache hit
        cached_status = {
            "id": self.test_recommendations[0]['post_id'],
            "content": "Cached content",
            "account": {"username": "cached_user"}
        }
        mock_get_cached.return_value = cached_status
        
        # Test with single recommendation
        result = fetch_fresh_mastodon_statuses([self.test_recommendations[0]], self.test_user_id)
        
        # Verify cache was used
        assert len(result) == 1
        assert result[0]['recommendation_metadata']['fetched_from_cache'] is True
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.is_token_expired')
    @patch('utils.mastodon_api.refresh_access_token')
    def test_token_refresh_success(self, mock_refresh_token, mock_is_expired, mock_get_token_data):
        """Test successful token refresh."""
        # Setup initial expired token
        expired_token_data = self.test_token_data.copy()
        expired_token_data['token_expires_at'] = datetime.utcnow() - timedelta(hours=1)
        
        # Mock calls
        mock_get_token_data.side_effect = [
            expired_token_data,  # First call returns expired token
            self.test_token_data  # Second call returns refreshed token
        ]
        mock_is_expired.return_value = True
        mock_refresh_token.return_value = {'success': True}
        
        with patch('utils.mastodon_api.mastodon_client.get_cached_status') as mock_cached:
            mock_cached.return_value = None
            with patch('utils.mastodon_api.mastodon_client.get_fresh_status') as mock_fresh:
                mock_fresh.return_value = None  # Simulate post not found
                
                # Test the function
                result = fetch_fresh_mastodon_statuses([self.test_recommendations[0]], self.test_user_id)
                
                # Verify refresh was attempted
                mock_refresh_token.assert_called_once()
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.is_token_expired')
    @patch('utils.mastodon_api.refresh_access_token')
    def test_token_refresh_failure(self, mock_refresh_token, mock_is_expired, mock_get_token_data):
        """Test token refresh failure."""
        # Setup expired token
        expired_token_data = self.test_token_data.copy()
        expired_token_data['token_expires_at'] = datetime.utcnow() - timedelta(hours=1)
        
        mock_get_token_data.return_value = expired_token_data
        mock_is_expired.return_value = True
        mock_refresh_token.return_value = {'success': False, 'message': 'Refresh failed'}
        
        # Test the function
        result = fetch_fresh_mastodon_statuses(self.test_recommendations, self.test_user_id)
        
        # Should return empty list on refresh failure
        assert result == []
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.is_token_expired')
    @patch('utils.mastodon_api.mastodon_client.get_cached_status')
    @patch('utils.mastodon_api.mastodon_client.get_fresh_status')
    def test_missing_post_omitted(self, mock_get_fresh, mock_get_cached, 
                                mock_is_expired, mock_get_token_data):
        """Test that missing posts are omitted from results."""
        mock_get_token_data.return_value = self.test_token_data
        mock_is_expired.return_value = False
        mock_get_cached.return_value = None
        
        # First post exists, second doesn't
        mock_get_fresh.side_effect = [
            {"id": "112345678901234567", "content": "Exists"},
            None  # Second post doesn't exist
        ]
        
        result = fetch_fresh_mastodon_statuses(self.test_recommendations, self.test_user_id)
        
        # Should only have the one existing post
        assert len(result) == 1
        assert result[0]['id'] == "112345678901234567"
    
    def test_custom_cache_ttl(self):
        """Test that custom cache TTL is passed through correctly."""
        with patch('utils.mastodon_api.get_user_token_data') as mock_get_token_data:
            mock_get_token_data.return_value = self.test_token_data
            
            with patch('utils.mastodon_api.is_token_expired') as mock_is_expired:
                mock_is_expired.return_value = False
                
                with patch('utils.mastodon_api.mastodon_client.get_cached_status') as mock_get_cached:
                    mock_get_cached.return_value = None
                    
                    with patch('utils.mastodon_api.mastodon_client.get_fresh_status') as mock_get_fresh:
                        mock_get_fresh.return_value = {"id": "123", "content": "test"}
                        
                        with patch('utils.mastodon_api.mastodon_client.cache_status') as mock_cache_status:
                            mock_cache_status.return_value = True
                            
                            # Test with custom TTL
                            result = fetch_fresh_mastodon_statuses(
                                [self.test_recommendations[0]],
                                self.test_user_id,
                                cache_ttl=600
                            )
                            
                            # Verify custom TTL was used for cache get
                            mock_get_cached.assert_called_with(
                                self.test_recommendations[0]['post_id'],
                                self.test_token_data['instance_url'],
                                ttl=600
                            )
                            
                            # The cached status should have recommendation metadata added
                            # Get the actual cached object to verify
                            cache_call_args = mock_cache_status.call_args
                            cached_status = cache_call_args[0][2]  # Third argument
                            
                            # Verify the cache call had custom TTL
                            assert cache_call_args[1]['ttl'] == 600
                            
                            # Verify recommendation metadata was added
                            assert 'recommendation_metadata' in cached_status
                            assert cached_status['recommendation_metadata']['source'] == 'corgi_recommendation_engine'
                            assert cached_status['recommendation_metadata']['score'] == 0.95 