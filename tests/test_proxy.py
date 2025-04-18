"""
Tests for the proxy middleware functionality.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask

from app import create_app
from routes.proxy import (
    get_user_instance, 
    get_authenticated_user, 
    blend_recommendations
)

@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()

class TestProxyHelpers:
    """Test helper functions for the proxy middleware."""
    
    def test_get_user_instance_from_header(self, app):
        """Test extracting instance from headers."""
        with app.test_request_context(headers={'X-Mastodon-Instance': 'mastodon.social'}):
            from flask import request
            instance = get_user_instance(request)
            assert instance == 'https://mastodon.social'
            
    def test_get_user_instance_from_query(self, app):
        """Test extracting instance from query parameters."""
        with app.test_request_context('/?instance=fosstodon.org'):
            from flask import request
            instance = get_user_instance(request)
            assert instance == 'https://fosstodon.org'
    
    def test_get_user_instance_default(self, app):
        """Test falling back to default instance."""
        app.config['DEFAULT_MASTODON_INSTANCE'] = 'https://mastodon.example'
        with app.test_request_context():
            from flask import request
            instance = get_user_instance(request)
            assert instance == 'https://mastodon.example'

    @patch('routes.proxy.get_user_by_token')
    def test_get_authenticated_user(self, mock_get_user, app):
        """Test extracting user ID from authentication header."""
        mock_get_user.return_value = {'user_id': 'user123', 'instance_url': 'https://example.org'}
        
        with app.test_request_context(headers={'Authorization': 'Bearer test_token'}):
            from flask import request
            user_id = get_authenticated_user(request)
            assert user_id == 'user123'
            mock_get_user.assert_called_once_with('test_token')
    
    def test_blend_recommendations(self):
        """Test blending recommendations into a timeline."""
        original_posts = [{'id': f'post{i}'} for i in range(10)]
        recommendations = [{'id': f'rec{i}', 'is_recommendation': True} for i in range(3)]
        
        blended = blend_recommendations(original_posts, recommendations, blend_ratio=0.3)
        
        # Check the length is as expected (should add recommendations)
        assert len(blended) == 13
        
        # Count recommendations in blended timeline
        rec_count = sum(1 for post in blended if post.get('is_recommendation'))
        assert rec_count == 3
        
        # Check ordering - recommendations should be distributed
        rec_positions = [i for i, post in enumerate(blended) if post.get('is_recommendation')]
        assert len(rec_positions) == 3
        
        # Check that recommendations are spaced out
        if len(rec_positions) >= 2:
            min_spacing = min(rec_positions[i+1] - rec_positions[i] for i in range(len(rec_positions)-1))
            assert min_spacing > 0

@pytest.mark.parametrize('path,instance,expected_url', [
    ('timelines/home', 'https://mastodon.social', 'https://mastodon.social/api/v1/timelines/home'),
    ('statuses/123', 'https://fosstodon.org', 'https://fosstodon.org/api/v1/statuses/123'),
])
@patch('routes.proxy.requests.request')
def test_proxy_forwarding(mock_request, client, path, instance, expected_url):
    """Test that requests are properly forwarded to the Mastodon instance."""
    # Mock the response from the proxied request
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = json.dumps([{'id': '123', 'content': 'Test post'}]).encode('utf-8')
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_request.return_value = mock_response
    
    # Make a request to the proxy
    headers = {'X-Mastodon-Instance': instance}
    response = client.get(f'/api/v1/{path}', headers=headers)
    
    # Check that the request was forwarded correctly
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert kwargs['url'] == expected_url
    
    # Check the response
    assert response.status_code == 200
    assert 'Content-Type' in response.headers

@patch('routes.proxy.requests.request')
@patch('routes.proxy.get_recommendations')
@patch('routes.proxy.get_authenticated_user')
@patch('routes.proxy.check_user_privacy')
def test_timeline_recommendation_injection(
    mock_check_privacy, mock_get_user, mock_get_recs, mock_request, client
):
    """Test that recommendations are injected into the home timeline."""
    # Set up mocks
    mock_get_user.return_value = 'user123'
    mock_check_privacy.return_value = True
    
    # Mock the Mastodon API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = json.dumps([
        {'id': 'post1', 'content': 'Original post 1'},
        {'id': 'post2', 'content': 'Original post 2'}
    ]).encode('utf-8')
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_request.return_value = mock_response
    
    # Mock recommendations
    mock_get_recs.return_value = [
        {'id': 'rec1', 'content': 'Recommended post 1', 'is_recommendation': True}
    ]
    
    # Make a request to the home timeline
    response = client.get('/api/v1/timelines/home')
    
    # Verify the response
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should have 3 posts (2 original + 1 recommendation)
    assert len(data) == 3
    
    # Verify that a recommendation was injected
    assert any(post.get('is_recommendation') for post in data)
    
    # Verify the header was added
    assert 'X-Corgi-Recommendations' in response.headers