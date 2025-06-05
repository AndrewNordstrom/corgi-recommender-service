"""
Tests for the fresh Mastodon timeline endpoint.

This module tests the /timelines/fresh endpoint that implements Option A.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from app import create_app
from db.connection import get_db_connection, USE_IN_MEMORY_DB


class TestFreshTimelineEndpoint:
    """Test the /timelines/fresh endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.test_user_id = "test_user_123"
        
        # Sample recommendations data
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
        
        # Sample fresh Mastodon statuses
        self.fresh_statuses = [
            {
                "id": "112345678901234567",
                "created_at": "2024-01-15T10:30:00.000Z",
                "account": {
                    "id": "123456",
                    "username": "testuser",
                    "display_name": "Test User"
                },
                "content": "<p>This is fresh content!</p>",
                "favourites_count": 5,
                "reblogs_count": 2,
                "replies_count": 1,
                "language": "en",
                "is_recommendation": True,
                "ranking_score": 0.95,
                "recommendation_reason": "High engagement content",
                "recommendation_metadata": {
                    "source": "corgi_recommendation_engine",
                    "score": 0.95,
                    "reason": "High engagement content",
                    "fetched_from_cache": False,
                    "fetched_at": "2024-01-15T10:30:00.000Z"
                }
            }
        ]
        
        # Sample OAuth token data
        self.mock_token_data = {
            'instance_url': 'https://mastodon.example.com',
            'access_token': 'mock_access_token_123',
            'refresh_token': 'mock_refresh_token_123',
            'token_expires_at': (datetime.utcnow() + timedelta(hours=6)).isoformat()
        }
    
    def test_missing_user_id(self):
        """Test that missing user_id returns 400."""
        response = self.client.get('/api/v1/recommendations/timelines/fresh')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Missing required parameter: user_id'
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.mastodon_client.get_cached_status')
    @patch('utils.mastodon_api.mastodon_client.get_fresh_status')
    @patch('routes.recommendations.get_cursor')
    def test_successful_fresh_timeline(self, mock_get_cursor, mock_get_fresh_status, mock_get_cached_status, mock_get_token):
        """Test successful fresh timeline retrieval."""
        with self.app.app_context():
            # Mock token data
            mock_get_token.return_value = self.mock_token_data
            
            # Mock cache to return None (cache miss) so it falls through to get_fresh_status
            mock_get_cached_status.return_value = None
            
            # Mock the Mastodon API client to return status data
            mock_get_fresh_status.return_value = {
                "id": "112345678901234567",
                "created_at": "2024-01-01T12:00:00.000Z",
                "content": "Test post content",
                "account": {
                    "id": "1",
                    "username": "testuser",
                    "display_name": "Test User"
                }
            }
            
            # Mock cursor and database results
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [
                ('112345678901234567', 0.95, 'High engagement content'),
                ('112345678901234568', 0.88, 'Similar topic interest')
            ]
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_get_cursor.return_value = mock_cursor
            
            response = self.client.get(f'/api/v1/recommendations/timelines/fresh?user_id={self.test_user_id}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Should return just the fresh statuses (Mastodon-compatible)
            assert len(data) >= 1
            assert data[0]['id'] == "112345678901234567"
            assert data[0]['is_recommendation'] is True
            assert data[0]['ranking_score'] in [0.95, 0.88]  # Either post can be first
            assert 'recommendation_metadata' in data[0]
            
            # Verify custom headers
            assert 'X-Corgi-Processing-Time' in response.headers
            assert 'X-Corgi-Source' in response.headers
            assert response.headers['X-Corgi-Source'] == 'fresh_mastodon_api'
            assert 'X-Corgi-Success-Rate' in response.headers
            
            # Verify the token was looked up and get_fresh_status was called
            mock_get_token.assert_called_with(self.test_user_id)
            assert mock_get_fresh_status.call_count >= 1
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.mastodon_client.get_fresh_status')
    def test_successful_fresh_timeline_simple(self, mock_get_fresh_status, mock_get_token):
        """Test fresh timeline with no recommendations returns 404."""
        # Mock token data (won't be called in this case)
        mock_get_token.return_value = self.mock_token_data
        
        # Mock the fetch function to return our test data (won't be called)
        mock_get_fresh_status.return_value = None
        
        response = self.client.get(
            '/api/v1/recommendations/timelines/fresh',
            query_string={'user_id': self.test_user_id}
        )
        
        # With no recommendations in DB, this should return 404
        assert response.status_code == 404
        data = response.get_json()
        assert data['message'] == 'No recommendations found. Try generating rankings first.'
        
        # No OAuth token lookup should be called since we return early with no recommendations
        mock_get_token.assert_not_called()
        
        # get_fresh_status should not be called when no recommendations exist
        mock_get_fresh_status.assert_not_called()
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.mastodon_client.get_cached_status')
    @patch('utils.mastodon_api.mastodon_client.get_fresh_status')
    @patch('routes.recommendations.get_cursor')
    def test_custom_cache_ttl(self, mock_get_cursor, mock_get_fresh_status, mock_get_cached_status, mock_get_token):
        """Test that custom cache TTL is passed through."""
        with self.app.app_context():
            # Mock token data
            mock_get_token.return_value = self.mock_token_data
            
            # Mock cache to return None (cache miss) so it falls through to get_fresh_status
            mock_get_cached_status.return_value = None
            
            # Mock the Mastodon API client to return status data
            mock_get_fresh_status.return_value = {
                "id": "112345678901234567",
                "created_at": "2024-01-01T12:00:00.000Z",
                "content": "Test post content",
                "account": {
                    "id": "1",
                    "username": "testuser",
                    "display_name": "Test User"
                }
            }
            
            # Mock cursor and database results
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [
                ('112345678901234567', 0.95, 'High engagement content')
            ]
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_get_cursor.return_value = mock_cursor
            
            response = self.client.get(
                f'/api/v1/recommendations/timelines/fresh?user_id={self.test_user_id}&cache_ttl=600'
            )
            
            assert response.status_code == 200
            
            # Verify token lookup and get_fresh_status were called
            mock_get_token.assert_called_with(self.test_user_id)
            assert mock_get_fresh_status.call_count >= 1
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.mastodon_client.get_fresh_status')
    @patch('routes.recommendations.get_cursor')
    def test_pagination_headers(self, mock_get_cursor, mock_get_fresh_status, mock_get_token):
        """Test that pagination headers are included."""
        with self.app.app_context():
            # Mock token data
            mock_get_token.return_value = self.mock_token_data
            
            # Mock the Mastodon API client to return different status data for each call
            def side_effect(*args, **kwargs):
                post_id = args[0]  # First argument is post_id
                return {
                    "id": post_id,
                    "created_at": "2024-01-01T12:00:00.000Z",
                    "content": f"Test post content for {post_id}",
                    "account": {
                        "id": "1",
                        "username": "testuser",
                        "display_name": "Test User"
                    }
                }
            
            mock_get_fresh_status.side_effect = side_effect
            
            # Mock cursor and database results
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [
                ('112345678901234567', 0.95, 'High engagement content'),
                ('112345678901234568', 0.88, 'Similar topic interest')
            ]
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_get_cursor.return_value = mock_cursor
            
            response = self.client.get(f'/api/v1/recommendations/timelines/fresh?user_id={self.test_user_id}')
            
            assert response.status_code == 200
            
            # Should have Link header for pagination
            assert 'Link' in response.headers
            link_header = response.headers['Link']
            assert 'rel="next"' in link_header
            assert 'rel="prev"' in link_header
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.mastodon_client.get_fresh_status')
    @patch('routes.recommendations.get_cursor')
    def test_filtering_parameters(self, mock_get_cursor, mock_get_fresh_status, mock_get_token):
        """Test that filtering parameters are applied correctly."""
        with self.app.app_context():
            # Mock token data
            mock_get_token.return_value = self.mock_token_data
            
            # Mock the Mastodon API client to return status data
            mock_get_fresh_status.return_value = {
                "id": "112345678901234567",
                "created_at": "2024-01-01T12:00:00.000Z",
                "content": "Test post content",
                "account": {
                    "id": "1",
                    "username": "testuser",
                    "display_name": "Test User"
                }
            }
            
            # Mock cursor and database results
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [
                ('112345678901234567', 0.95, 'High engagement content')
            ]
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_get_cursor.return_value = mock_cursor
            
            # Test with min_score filter
            response = self.client.get(
                f'/api/v1/recommendations/timelines/fresh?user_id={self.test_user_id}&min_score=0.9&limit=10'
            )
            
            assert response.status_code == 200
            
            # Verify that query was executed with filters
            mock_cursor.execute.assert_called()
            executed_query = mock_cursor.execute.call_args[0][0]
            
            # Should include score filter
            assert "score >=" in executed_query or "ranking_score >=" in executed_query
            assert "LIMIT" in executed_query
    
    @patch('utils.mastodon_api.get_user_token_data') 
    @patch('utils.mastodon_api.mastodon_client.get_fresh_status')
    @patch('routes.recommendations.get_cursor')
    def test_error_handling(self, mock_get_cursor, mock_get_fresh_status, mock_get_token):
        """Test error handling in the endpoint."""
        with self.app.app_context():
            # Mock token data
            mock_get_token.return_value = self.mock_token_data
            
            # Mock cursor to raise an exception
            mock_get_cursor.side_effect = Exception("Database connection failed")
            
            response = self.client.get(f'/api/v1/recommendations/timelines/fresh?user_id={self.test_user_id}')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert "Failed to retrieve fresh Mastodon timeline" in data['error']
            assert data['user_id'] == self.test_user_id
            assert 'processing_time_ms' in data
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.mastodon_client.get_cached_status')
    @patch('utils.mastodon_api.mastodon_client.get_fresh_status')
    @patch('routes.recommendations.get_cursor')
    def test_partial_success_scenario(self, mock_get_cursor, mock_get_fresh_status, mock_get_cached_status, mock_get_token):
        """Test when some posts can't be fetched fresh."""
        with self.app.app_context():
            # Mock token data
            mock_get_token.return_value = self.mock_token_data
            
            # Mock cache to return None (cache miss) so it falls through to get_fresh_status
            mock_get_cached_status.return_value = None
            
            # Mock get_fresh_status to return None for second post (simulating deleted/private post)
            def side_effect(*args, **kwargs):
                post_id = args[0]  # First argument is post_id
                if post_id == '112345678901234567':
                    return {
                        "id": post_id,
                        "created_at": "2024-01-01T12:00:00.000Z",
                        "content": "Test post content",
                        "account": {
                            "id": "1",
                            "username": "testuser",
                            "display_name": "Test User"
                        }
                    }
                return None  # Second post fails to fetch
            
            mock_get_fresh_status.side_effect = side_effect
            
            # Mock cursor and database results
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [
                ('112345678901234567', 0.95, 'High engagement content'),
                ('112345678901234568', 0.88, 'Similar topic interest')
            ]
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_get_cursor.return_value = mock_cursor
            
            response = self.client.get(f'/api/v1/recommendations/timelines/fresh?user_id={self.test_user_id}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Should only have the successfully fetched post
            assert len(data) == 1
            assert data[0]['id'] == "112345678901234567"
            
            # Success rate should be 50% (1 out of 2)
            assert 'X-Corgi-Success-Rate' in response.headers
            success_rate = float(response.headers['X-Corgi-Success-Rate'])
            assert success_rate == 50.0

    def test_skip_cache_parameter(self):
        """Test the skip_cache parameter (for debugging)."""
        with self.app.app_context():
            with patch('routes.recommendations.get_db_connection') as mock_get_db_connection:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = []
                mock_conn.__enter__ = Mock(return_value=mock_conn)
                mock_conn.__exit__ = Mock(return_value=None)
                mock_cursor.__enter__ = Mock(return_value=mock_cursor)
                mock_cursor.__exit__ = Mock(return_value=None)
                
                mock_get_db_connection.return_value = mock_conn
                
                with patch('routes.recommendations.get_cursor') as mock_get_cursor:
                    mock_get_cursor.return_value = mock_cursor
                    
                    response = self.client.get(
                        f'/api/v1/recommendations/timelines/fresh?user_id={self.test_user_id}&skip_cache=true'
                    )
                    
                    # Should still work (even with no results)
                    assert response.status_code == 404  # No recommendations found
                    data = json.loads(response.data)
                    assert data['debug_info']['recommendations_found'] == 0 