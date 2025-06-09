"""
Tests for asynchronous recommendation functionality.

This module tests the async/await capabilities added to the recommendations system,
including task queuing, status polling, and hybrid response patterns.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from app import create_app
from routes.recommendations import ASYNC_TASKS_AVAILABLE

class TestAsyncRecommendations:
    """Test async recommendation functionality."""
    
    @pytest.fixture
    def app(self):
        """Create test app instance."""
        app = create_app()
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture  
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def test_recommendations_sync_fallback(self, client):
        """Test that recommendations work when async is disabled."""
        # Test sync behavior is preserved
        response = client.get('/api/v1/recommendations?user_id=test_user&async=false')
        
        # Should get some kind of response (200 or 404 if no data)
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.get_json()
            assert 'user_id' in data
            assert data['user_id'] == 'test_user'
            assert 'recommendations' in data
            assert 'source' in data
    
    def test_recommendations_parameters_validation(self, client):
        """Test parameter validation for the recommendations endpoint."""
        # Test missing user_id
        response = client.get('/api/v1/recommendations')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'user_id' in data['error']
        
        # Test invalid limit
        response = client.get('/api/v1/recommendations?user_id=test&limit=150')
        assert response.status_code == 400
        data = response.get_json()
        assert 'limit' in data['error']
        
        # Test valid parameters
        response = client.get('/api/v1/recommendations?user_id=test&limit=5')
        assert response.status_code in [200, 404]  # Valid request format
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_async_task_queuing(self, client):
        """Test async task queuing when async=true."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            # Mock the Celery task
            mock_result = Mock()
            mock_result.id = 'test-task-123'
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=test_user&async=true')
            
            # Should return 202 Accepted for async processing
            assert response.status_code == 202
            data = response.get_json()
            
            assert data['status'] == 'processing'
            assert data['task_id'] == 'test-task-123'
            assert 'status_url' in data
            assert data['user_id'] == 'test_user'
            assert data['async_enabled'] is True
            
            # Verify task was called
            mock_task.delay.assert_called_once()
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_task_status_endpoint(self, client):
        """Test the task status polling endpoint."""
        with patch('utils.celery_app.celery') as mock_celery:
            # Mock successful task
            mock_result = Mock()
            mock_result.state = 'SUCCESS'
            mock_result.result = {
                'user_id': 'test_user',
                'rankings_count': 10,
                'processing_time': 2.5,
                'cache_key': 'async_rankings:test_user'
            }
            mock_result.info = mock_result.result
            mock_celery.AsyncResult.return_value = mock_result
            
            response = client.get('/api/v1/recommendations/status/test-task-123')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['task_id'] == 'test-task-123'
            assert data['state'] == 'SUCCESS'
            assert data['status'] == 'completed'
            assert data['progress'] == 100
            assert data['user_id'] == 'test_user'
            assert data['rankings_count'] == 10
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_task_status_pending(self, client):
        """Test task status when task is pending."""
        with patch('utils.celery_app.celery') as mock_celery:
            mock_result = Mock()
            mock_result.state = 'PENDING'
            mock_celery.AsyncResult.return_value = mock_result
            
            response = client.get('/api/v1/recommendations/status/test-task-123')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['state'] == 'PENDING'
            assert data['status'] == 'queued'
            assert data['progress'] == 0
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")  
    def test_task_status_failure(self, client):
        """Test task status when task failed."""
        with patch('utils.celery_app.celery') as mock_celery:
            mock_result = Mock()
            mock_result.state = 'FAILURE'
            mock_result.info = {'error': 'Test error', 'user_id': 'test_user'}
            mock_celery.AsyncResult.return_value = mock_result
            
            response = client.get('/api/v1/recommendations/status/test-task-123')
            
            assert response.status_code == 500  # Failed tasks correctly return 500
            data = response.get_json()
            
            assert data['state'] == 'FAILURE'
            assert data['status'] == 'failed'
            assert data['progress'] == -1
            assert 'error' in data
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_task_cancellation(self, client):
        """Test task cancellation endpoint."""
        with patch('utils.celery_app.celery') as mock_celery:
            # Mock task that can be cancelled
            mock_result = Mock()
            mock_result.state = 'PENDING'
            mock_celery.AsyncResult.return_value = mock_result
            
            # Mock control.revoke
            mock_celery.control.revoke = Mock()
            
            response = client.delete('/api/v1/recommendations/status/test-task-123')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['task_id'] == 'test-task-123'
            assert data['state'] == 'REVOKED'
            assert 'cancelled successfully' in data['message']
            
            # Verify revoke was called
            mock_celery.control.revoke.assert_called_once_with('test-task-123', terminate=True)
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_task_cancel_completed(self, client):
        """Test attempting to cancel an already completed task."""
        with patch('utils.celery_app.celery') as mock_celery:
            mock_result = Mock()
            mock_result.state = 'SUCCESS'
            mock_result.result = {'user_id': 'test_user', 'rankings_count': 10}
            mock_celery.AsyncResult.return_value = mock_result
            
            response = client.delete('/api/v1/recommendations/status/test-task-123')
            
            assert response.status_code == 410  # Gone
            data = response.get_json()
            
            assert 'cannot be cancelled' in data['message']
            assert data['state'] == 'SUCCESS'
    
    def test_async_unavailable_fallback(self, client):
        """Test behavior when async functionality is not available."""
        if ASYNC_TASKS_AVAILABLE:
            # Mock async being unavailable
            with patch('routes.recommendations.ASYNC_TASKS_AVAILABLE', False):
                response = client.get('/api/v1/recommendations?user_id=test_user&async=true')
                
                # Should fall back to sync processing
                assert response.status_code in [200, 404]
                data = response.get_json()
                assert 'recommendations' in data or 'user_id' in data
                
                # Status endpoint should return 503
                response = client.get('/api/v1/recommendations/status/any-task')
                assert response.status_code == 503
                data = response.get_json()
                assert 'not available' in data['error']
    
    def test_hybrid_cache_behavior(self, client):
        """Test the hybrid cache behavior (stale cache + background refresh)."""
        with patch('utils.cache.get_cached_recommendations') as mock_get_cache:
            with patch('utils.cache.cache_get') as mock_cache_get:
                with patch('routes.recommendations.generate_rankings_async') as mock_task:
                    with patch('routes.recommendations.ASYNC_TASKS_AVAILABLE', True):
                        # Mock stale cache data - must be a list for recommendations
                        mock_get_cache.return_value = [{'id': 1, 'content': 'test'}]
                        mock_cache_get.return_value = {
                            'timestamp': time.time() - 7200  # 2 hours ago (stale)
                        }
                        
                        mock_result = Mock()
                        mock_result.id = 'refresh-task-123'
                        mock_task.delay.return_value = mock_result
                        
                        # Must explicitly request async for the new conservative logic
                        response = client.get('/api/v1/recommendations?user_id=test_user&cache_timeout=3600&async=true')
                        
                        # With async=true, should trigger async processing, not return stale cache
                        assert response.status_code == 202  # Async processing
                        data = response.get_json()
                        
                        assert data['status'] == 'processing'
                        assert 'task_id' in data
                        assert data['async_enabled'] is True
                        
                        # Async task should be triggered
                        mock_task.delay.assert_called_once()
    
    def test_processing_time_tracking(self, client):
        """Test that processing times are tracked in responses."""
        response = client.get('/api/v1/recommendations?user_id=test_user')
        
        if response.status_code == 200:
            data = response.get_json()
            assert 'processing_time_ms' in data
            assert isinstance(data['processing_time_ms'], (int, float))
            assert data['processing_time_ms'] >= 0

class TestAsyncIntegration:
    """Integration tests for async functionality."""
    
    @pytest.fixture
    def app(self):
        """Create test app instance."""
        app = create_app()
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def test_end_to_end_async_flow(self, client):
        """Test complete async flow from request to completion."""
        if not ASYNC_TASKS_AVAILABLE:
            pytest.skip("Async tasks not available")
        
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            with patch('utils.celery_app.celery') as mock_celery:
                # Step 1: Queue async task
                mock_result = Mock()
                mock_result.id = 'integration-test-123'
                mock_task.delay.return_value = mock_result
                
                response = client.get('/api/v1/recommendations?user_id=integration_test&async=true')
                
                assert response.status_code == 202
                data = response.get_json()
                assert data['status'] == 'processing'
                assert 'task_id' in data
                
                task_id = data['task_id']
                
                # Step 2: Check task status (pending)
                mock_pending = Mock()
                mock_pending.state = 'PENDING'
                mock_celery.AsyncResult.return_value = mock_pending
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                
                assert status_response.status_code == 200
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'PENDING'
                assert status_data['status'] == 'queued'  # PENDING tasks show as 'queued', not 'processing'
                assert status_data['progress'] == 0
    
    def test_backwards_compatibility(self, client):
        """Test that existing sync behavior is preserved."""
        # Test the old parameter format
        response = client.get('/api/v1/recommendations?user_id=compat_test&skip_cache=true')
        
        # Should still work (though skip_cache maps to force_refresh now)
        assert response.status_code in [200, 404]
        
        # Test without any async parameters
        response = client.get('/api/v1/recommendations?user_id=compat_test')
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.get_json()
            assert 'recommendations' in data
            assert 'user_id' in data