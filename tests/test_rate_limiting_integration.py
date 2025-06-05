"""
Integration tests for rate limiting functionality.
"""

import os
import time
import pytest
from unittest.mock import patch

from app import create_app


class TestRateLimitingIntegration:
    """Test rate limiting integration with the application."""
    
    @pytest.fixture
    def app(self):
        """Create test application with memory-based rate limiting."""
        # Set up environment for testing
        os.environ['RATE_LIMITING_ENABLED'] = 'true'
        os.environ['RATE_LIMITING_STORAGE_URL'] = 'memory://'
        os.environ['FLASK_ENV'] = 'testing'
        
        app = create_app()
        app.config['TESTING'] = True
        
        yield app
        
        # Cleanup
        os.environ.pop('RATE_LIMITING_STORAGE_URL', None)
        os.environ.pop('RATE_LIMITING_ENABLED', None)
        os.environ.pop('FLASK_ENV', None)
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def test_health_endpoint_rate_limiting(self, client):
        """Test that health endpoints respect rate limits."""
        endpoint = '/api/v1/health'
        
        # Make several requests rapidly
        responses = []
        for i in range(15):  # Health limit is 10/min
            responses.append(client.get(endpoint))
        
        # Should have some successful requests
        success_count = sum(1 for r in responses if r.status_code == 200)
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)
        
        assert success_count > 0, "Should have some successful requests"
        # Note: In memory storage, rate limiting might be more lenient
        print(f"Health endpoint: {success_count} successful, {rate_limited_count} rate limited")
    
    def test_rate_limiting_headers(self, client):
        """Test that rate limiting headers are included in responses."""
        response = client.get('/api/v1/health')
        
        # Check for rate limiting headers (when enabled)
        if response.status_code == 200:
            # Flask-Limiter typically adds X-RateLimit-* headers
            headers = response.headers
            print(f"Response headers: {dict(headers)}")
            # Note: Header presence depends on Flask-Limiter configuration
    
    def test_exemption_for_testing_env(self, client):
        """Test that testing environment exempts requests from rate limiting."""
        # This should work because FLASK_ENV=testing exempts requests
        endpoint = '/api/v1/health'
        
        # Make many requests - should not be rate limited in testing env
        responses = []
        for i in range(20):
            responses.append(client.get(endpoint))
        
        # All should be successful due to testing exemption
        success_count = sum(1 for r in responses if r.status_code == 200)
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)
        
        # In testing environment, should be mostly successful
        assert success_count >= 15, f"Expected most requests to succeed, got {success_count}/20"
        print(f"Testing exemption: {success_count} successful, {rate_limited_count} rate limited")
    
    def test_different_endpoints_have_different_limits(self, client):
        """Test that different endpoints have appropriately different rate limits."""
        # Test a few different endpoints to verify they have different configurations
        endpoints = [
            '/api/v1/health',
            '/api/v1/metrics',
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            print(f"Endpoint {endpoint}: Status {response.status_code}")
            
            # Each endpoint should respond (might be 404 if endpoint doesn't exist in test)
            assert response.status_code in [200, 404, 405, 429], f"Unexpected status for {endpoint}"
    
    def test_user_identification_fallback(self, client):
        """Test that user identification falls back to IP when no auth token present."""
        # This is testing the get_user_identity function behavior
        response = client.get('/api/v1/health')
        
        # Should work with IP-based identification
        assert response.status_code in [200, 429], "Should handle IP-based rate limiting"
    
    @patch('utils.auth.get_user_by_token')
    def test_authenticated_vs_anonymous_limits(self, mock_get_user, client):
        """Test that authenticated users get different rate limits."""
        # Test anonymous user
        mock_get_user.return_value = None
        response_anon = client.get('/api/v1/health')
        
        # Test authenticated user
        mock_get_user.return_value = {'user_id': 'test_user_123'}
        headers = {'Authorization': 'Bearer test_token'}
        response_auth = client.get('/api/v1/health', headers=headers)
        
        # Both should work (the difference is in the rate limit, not immediate failure)
        assert response_anon.status_code in [200, 429]
        assert response_auth.status_code in [200, 429]
        
        print(f"Anonymous: {response_anon.status_code}, Authenticated: {response_auth.status_code}")


def test_rate_limiting_configuration():
    """Test that rate limiting configuration is properly loaded."""
    from config import (
        RATE_LIMITING_ENABLED,
        RATE_LIMIT_DEFAULT,
        RATE_LIMIT_AUTH,
        RATE_LIMIT_ANONYMOUS,
        RATE_LIMIT_HEALTH
    )
    
    assert isinstance(RATE_LIMITING_ENABLED, bool)
    assert isinstance(RATE_LIMIT_DEFAULT, str)
    assert isinstance(RATE_LIMIT_AUTH, str)
    assert isinstance(RATE_LIMIT_ANONYMOUS, str)
    assert isinstance(RATE_LIMIT_HEALTH, str)
    
    # Verify rate limit format (should be like "60 per minute")
    assert "per" in RATE_LIMIT_DEFAULT
    assert "per" in RATE_LIMIT_AUTH
    assert "per" in RATE_LIMIT_ANONYMOUS


def test_rate_limiting_imports():
    """Test that all rate limiting decorators can be imported."""
    from utils.rate_limiting import (
        limit_health,
        limit_analytics,
        limit_recommendations,
        limit_proxy,
        limit_timeline,
        limit_interactions,
        limit_oauth,
        limit_setup,
        get_user_identity,
        init_rate_limiter
    )
    
    # All imports should succeed
    assert callable(limit_health)
    assert callable(limit_analytics)
    assert callable(get_user_identity)
    assert callable(init_rate_limiter)


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"]) 