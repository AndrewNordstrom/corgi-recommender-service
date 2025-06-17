"""
Tests for the health check endpoints.
"""

import json
import pytest
from unittest.mock import patch
from config import API_PREFIX


def test_health_check_route(client):
    """Test that the health check route responds."""
    response = client.get('/health')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert 'hostname' in data


def test_versioned_health_check_route(client):
    """Test that the versioned health check route responds."""
    response = client.get(f'{API_PREFIX}/health')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


@patch('routes.health.get_db_connection')
def test_health_check_db_error(mock_get_db_connection, client):
    """Test that the health check properly reports database errors."""
    # Mock the database connection to raise an exception
    mock_get_db_connection.side_effect = Exception("Test database error")
    
    response = client.get('/health')
    
    assert response.status_code == 503
    data = json.loads(response.data)
    assert data['status'] == 'unhealthy'
    assert data['database'] == 'error'


def test_request_id_header_added(client):
    """Test that a request ID header is added to responses."""
    response = client.get('/health')
    
    assert response.status_code == 200
    assert 'X-Request-ID' in response.headers
    assert response.headers['X-Request-ID'] is not None
    
    # Test that incoming request IDs are preserved
    custom_request_id = 'test-request-id-123'
    response = client.get('/health', headers={'X-Request-ID': custom_request_id})
    
    assert response.status_code == 200
    assert response.headers['X-Request-ID'] == custom_request_id