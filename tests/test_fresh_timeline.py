"""
Core Fresh Timeline Tests

Essential tests for the /timelines/fresh endpoint covering:
- Basic parameter validation
- Successful timeline retrieval
- Core error handling
- Basic API functionality
"""

import pytest
import json
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from app import create_app
from db.connection import get_db_connection, USE_IN_MEMORY_DB


class TestFreshTimelineEndpoint:
    """Test core functionality of the /timelines/fresh endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.test_user_id = "test_user_123"
        
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
    
    def test_successful_fresh_timeline(self):
        """Test successful fresh timeline retrieval."""
        with self.app.app_context():
            # First, create some recommendations in the database
            from db.connection import get_db_connection, get_cursor
            from utils.privacy import generate_user_alias
            
            user_alias = generate_user_alias(self.test_user_id)
            
            with get_db_connection() as conn:
                with get_cursor(conn) as cur:
                    # Insert test recommendations
                    cur.execute(
                        "INSERT INTO recommendations (user_id, post_id, score, reason) VALUES (?, ?, ?, ?)",
                        (user_alias, "112345678901234567", 0.95, "High engagement content")
                    )
                    cur.execute(
                        "INSERT INTO recommendations (user_id, post_id, score, reason) VALUES (?, ?, ?, ?)",
                        (user_alias, "112345678901234568", 0.88, "Similar topic interest")
                    )
                    conn.commit()
            
            response = self.client.get(f'/api/v1/recommendations/timelines/fresh?user_id={self.test_user_id}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Should return the recommendations with fallback data (since no Mastodon API)
            assert len(data) >= 1
            assert data[0]['id'] in ["112345678901234567", "112345678901234568"]
            assert data[0]['is_recommendation'] is True
            assert data[0]['ranking_score'] in [0.95, 0.88]
            assert 'recommendation_metadata' in data[0]
            
            # Verify custom headers
            assert 'X-Corgi-Processing-Time' in response.headers
            assert 'X-Corgi-Source' in response.headers
            assert response.headers['X-Corgi-Source'] == 'fresh_mastodon_api'
    
    @patch('utils.mastodon_api.get_user_token_data')
    @patch('utils.mastodon_api.mastodon_client.get_fresh_status')
    def test_no_recommendations_returns_404(self, mock_get_fresh_status, mock_get_token):
        """Test fresh timeline with no recommendations returns 404."""
        with self.app.app_context():
            # Clean up any existing recommendations first
            from db.connection import get_db_connection, get_cursor
            from utils.privacy import generate_user_alias
            
            user_alias = generate_user_alias(self.test_user_id)
            
            with get_db_connection() as conn:
                with get_cursor(conn) as cur:
                    # Clear any existing recommendations
                    cur.execute("DELETE FROM recommendations WHERE user_id = ?", (user_alias,))
                    conn.commit()
            
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
    
    def test_error_handling(self):
        """Test error handling for API failures."""
        with self.app.app_context():
            # Clean up any existing recommendations first
            from db.connection import get_db_connection, get_cursor
            from utils.privacy import generate_user_alias
            
            user_alias = generate_user_alias(self.test_user_id)
            
            with get_db_connection() as conn:
                with get_cursor(conn) as cur:
                    # Clear any existing recommendations
                    cur.execute("DELETE FROM recommendations WHERE user_id = ?", (user_alias,))
                    
                    # Insert test recommendations
                    cur.execute(
                        "INSERT INTO recommendations (user_id, post_id, score, reason) VALUES (?, ?, ?, ?)",
                        (user_alias, "112345678901234567", 0.95, "High engagement content")
                    )
                    conn.commit()
            
            # Test with invalid user_id to trigger error path
            response = self.client.get('/api/v1/recommendations/timelines/fresh?user_id=')
            
            # Should handle error gracefully
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 