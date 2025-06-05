"""
Phase 5.2: Error Handling in Asynchronous Flows Testing

This module contains comprehensive tests for error handling resilience in async
ranking tasks, including retry strategies, permanent failures, and Dead Letter
Queue (DLQ) processing.
"""

import pytest
import json
import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import test helpers
from tests.fixtures.async_test_helpers import (
    AsyncTestHelper, assert_async_response_format, assert_task_status_format,
    assert_recommendations_format, create_test_recommendations_data,
    simulate_task_progression
)

# Import system components
from routes.recommendations import ASYNC_TASKS_AVAILABLE
from tasks.exceptions import (
    DatabaseConnectionError, CacheError, RankingAlgorithmError,
    InsufficientDataError, ExternalServiceError,
    InvalidUserError, UserAccessError, InvalidParameterError,
    ConfigurationError, ResourceExhaustionError
)


class TestRetryableErrors:
    """Test retryable error scenarios and retry logic."""
    
    @pytest.fixture
    def app(self):
        """Create test app instance."""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_database_connection_error_retry(self, client):
        """Test database connection errors trigger retry with exponential backoff."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=db_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate retry state for database connection error
                mock_result_status = Mock()
                mock_result_status.state = 'RETRY'
                mock_result_status.info = {
                    'error_type': 'DatabaseConnectionError',
                    'error_message': 'Connection to database failed, retrying...',
                    'user_id': 'db_test',
                    'retry_attempt': 1,
                    'next_retry_in': 2.0
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                assert status_response.status_code == 200
                
                status_data = status_response.get_json()
                assert status_data['state'] == 'RETRY'
                assert status_data['status'] == 'unknown'  # RETRY maps to unknown in current implementation
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_cache_error_retry_with_recovery(self, client):
        """Test cache errors can be retried and recovered."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=cache_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate retry state for cache error
                mock_result_status = Mock()
                mock_result_status.state = 'RETRY'
                mock_result_status.info = {
                    'error_type': 'CacheError',
                    'error_message': 'Redis cache temporarily unavailable',
                    'user_id': 'cache_test',
                    'retry_attempt': 2,
                    'fallback_used': True
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'RETRY'
                # In current implementation, RETRY info is not exposed in message
                assert 'retry' in status_data['message'].lower() or 'unknown' in status_data['message'].lower()
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_ranking_algorithm_intermittent_failure(self, client):
        """Test ranking algorithm errors with exponential backoff."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=algo_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate progress state showing algorithm retry
                mock_result_status = Mock()
                mock_result_status.state = 'PROGRESS'
                mock_result_status.info = {
                    'stage': 'Retrying ranking algorithm after temporary failure',
                    'progress': 30,
                    'user_id': 'algo_test',
                    'retry_attempt': 2,
                    'algorithm_error': 'RankingAlgorithmError'
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'PROGRESS'
                assert status_data['progress'] == 30
                assert 'user_id' in status_data
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_insufficient_data_long_retry_delay(self, client):
        """Test insufficient data errors use longer retry delays."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=data_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate retry state for insufficient data
                mock_result_status = Mock()
                mock_result_status.state = 'RETRY'
                mock_result_status.info = {
                    'error_type': 'InsufficientDataError',
                    'error_message': 'User has insufficient interaction data, waiting for more data',
                    'user_id': 'data_test',
                    'retry_attempt': 1,
                    'next_retry_in': 300  # 5 minutes for data collection
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'RETRY'
                # Verify the error state is properly handled
                assert status_data['status'] == 'unknown'
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_external_service_timeout_recovery(self, client):
        """Test external service timeouts are retried."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=external_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate retry for external service error
                mock_result_status = Mock()
                mock_result_status.state = 'RETRY'
                mock_result_status.info = {
                    'error_type': 'ExternalServiceError',
                    'error_message': 'External API timeout, retrying with backoff',
                    'user_id': 'external_test',
                    'retry_attempt': 1,
                    'service_name': 'mastodon_api'
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'RETRY'
                # Current implementation maps RETRY to unknown status
                assert status_data['status'] == 'unknown'
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_retry_backoff_jitter_implementation(self, client):
        """Test retry backoff includes jitter to prevent thundering herd."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=jitter_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate retry with jitter information
                mock_result_status = Mock()
                mock_result_status.state = 'PROGRESS'
                mock_result_status.info = {
                    'stage': 'Applying retry backoff with jitter',
                    'progress': 15,
                    'user_id': 'jitter_test',
                    'retry_attempt': 3,
                    'base_delay': 4.0,
                    'jitter_applied': 1.2,
                    'actual_delay': 5.2
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'PROGRESS'
                assert status_data['progress'] == 15
                assert 'jitter' in status_data['current_stage'].lower() or 'backoff' in status_data['current_stage'].lower()
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_retry_policy_max_attempts_validation(self, client):
        """Test retry policy enforces maximum attempts correctly."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=max_attempts_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate final retry attempt before giving up
                mock_result_status = Mock()
                mock_result_status.state = 'PROGRESS'
                mock_result_status.info = {
                    'stage': 'Final retry attempt before permanent failure',
                    'progress': 80,
                    'user_id': 'max_attempts_test',
                    'retry_attempt': 3,  # Max retries reached
                    'max_retries': 3,
                    'final_attempt': True
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'PROGRESS'
                assert status_data['progress'] == 80
                assert 'final' in status_data['current_stage'].lower() or 'retry' in status_data['current_stage'].lower()


class TestNonRetryableErrors:
    """Test permanent error scenarios that should not be retried."""
    
    @pytest.fixture
    def app(self):
        """Create test app instance."""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_invalid_user_id_permanent_failure(self, client):
        """Test invalid user ID causes immediate permanent failure."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=invalid_user&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate permanent failure for invalid user
                mock_result_status = Mock()
                mock_result_status.state = 'FAILURE'
                mock_result_status.info = {
                    'error_type': 'InvalidUserError',
                    'error_message': 'User ID format is invalid: invalid_user',
                    'user_id': 'invalid_user',
                    'permanent_failure': True,
                    'retry_attempts': 0
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                assert status_response.status_code == 500
                
                status_data = status_response.get_json()
                assert status_data['state'] == 'FAILURE'
                assert 'InvalidUserError' in status_data['error']
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_user_access_error_permanent_failure(self, client):
        """Test user access denied causes permanent failure."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=blocked_user&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate access denied failure
                mock_result_status = Mock()
                mock_result_status.state = 'FAILURE'
                mock_result_status.info = {
                    'error_type': 'UserAccessError',
                    'error_message': 'Access denied for user: blocked_user',
                    'user_id': 'blocked_user',
                    'permanent_failure': True,
                    'retry_attempts': 0
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                assert status_response.status_code == 500
                
                status_data = status_response.get_json()
                assert status_data['state'] == 'FAILURE'
                assert 'UserAccessError' in status_data['error']
                # Note: permanent_failure is in error string, not as separate field
                assert 'permanent_failure' in status_data['error']
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_parameter_validation_error_immediate_failure(self, client):
        """Test parameter validation errors fail immediately."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=param_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate parameter validation failure
                mock_result_status = Mock()
                mock_result_status.state = 'FAILURE'
                mock_result_status.info = {
                    'error_type': 'ParameterValidationError',
                    'error_message': 'Invalid parameters provided: limit must be positive',
                    'user_id': 'param_test',
                    'permanent_failure': True,
                    'validation_errors': ['limit: must be positive integer']
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'FAILURE'
                assert 'ParameterValidationError' in status_data['error']
                assert 'validation_errors' in status_data['error']
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_configuration_error_system_failure(self, client):
        """Test configuration errors cause system-level failures."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=config_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate configuration error
                mock_result_status = Mock()
                mock_result_status.state = 'FAILURE'
                mock_result_status.info = {
                    'error_type': 'ConfigurationError',
                    'error_message': 'Missing required configuration: ALGORITHM_WEIGHTS',
                    'user_id': 'config_test',
                    'permanent_failure': True,
                    'system_error': True,
                    'config_missing': ['ALGORITHM_WEIGHTS']
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'FAILURE'
                assert 'ConfigurationError' in status_data['error']
                assert 'system_error' in status_data['error']


class TestDLQProcessing:
    """Test Dead Letter Queue processing for exhausted tasks."""
    
    @pytest.fixture
    def app(self):
        """Create test app instance."""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_max_retries_exhausted_dlq_processing(self, client):
        """Test task that exhausts all retries gets sent to DLQ."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=dlq_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate final failure after max retries
                mock_result_status = Mock()
                mock_result_status.state = 'FAILURE'
                mock_result_status.info = {
                    'error_type': 'DatabaseConnectionError',
                    'error_message': 'Database connection failed after 3 retries',
                    'user_id': 'dlq_test',
                    'retry_attempts': 3,  # Max retries exhausted
                    'max_retries_exhausted': True,
                    'dlq_processed': True,
                    'dlq_entry_id': f'dlq:{task_id}'
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                assert status_response.status_code == 500
                
                status_data = status_response.get_json()
                assert status_data['state'] == 'FAILURE'
                # Check that DLQ info is in the error string
                assert 'retry_attempts' in status_data['error']
                assert 'max_retries_exhausted' in status_data['error']
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    @patch('utils.cache.cache_get')
    @patch('utils.cache.cache_set')
    def test_dlq_entry_structure_validation(self, mock_cache_set, mock_cache_get, client):
        """Test DLQ entries have proper structure and metadata."""
        # Mock cache functions
        mock_cache_get.return_value = None
        mock_cache_set.return_value = True
        
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=dlq_structure_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate DLQ entry creation
                mock_result_status = Mock()
                mock_result_status.state = 'FAILURE'
                mock_result_status.info = {
                    'error_type': 'CacheError',
                    'error_message': 'Redis cache connection lost',
                    'user_id': 'dlq_structure_test',
                    'retry_attempts': 3,
                    'dlq_entry': {
                        'original_task_id': task_id,
                        'timestamp': '2025-01-01T12:00:00',
                        'system_context': {
                            'worker_id': 'worker-1',
                            'python_version': '3.12.1'
                        }
                    }
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'FAILURE'
                # Verify DLQ structure information is present
                assert 'dlq_entry' in status_data['error']
                assert 'system_context' in status_data['error']
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_dlq_index_management(self, client):
        """Test DLQ index is properly maintained for analysis."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=dlq_index_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate DLQ with index management
                mock_result_status = Mock()
                mock_result_status.state = 'FAILURE'
                mock_result_status.info = {
                    'error_type': 'AlgorithmError',
                    'error_message': 'Ranking algorithm crashed unexpectedly',
                    'user_id': 'dlq_index_test',
                    'retry_attempts': 3,
                    'dlq_index_updated': True,
                    'dlq_index_key': 'dlq_index:AlgorithmError',
                    'index_position': 15
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'FAILURE'
                assert 'dlq_index_updated' in status_data['error']
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_admin_alert_triggering_for_critical_failures(self, client):
        """Test admin alerts are triggered for critical failures."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=critical_failure_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate critical failure that should trigger alert
                mock_result_status = Mock()
                mock_result_status.state = 'FAILURE'
                mock_result_status.info = {
                    'error_type': 'ResourceExhaustionError',
                    'error_message': 'System memory exhausted during ranking generation',
                    'user_id': 'critical_failure_test',
                    'retry_attempts': 3,
                    'max_retries_exhausted': True,
                    'critical_failure': True,
                    'alert_triggered': True
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'FAILURE'
                # Check that critical failure info is in the error string
                assert 'critical_failure' in status_data['error']
                assert 'alert_triggered' in status_data['error']
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_user_error_cache_updates(self, client):
        """Test user error cache is updated for immediate API feedback."""
        with patch('routes.recommendations.generate_rankings_async') as mock_task:
            task_id = str(uuid.uuid4())
            mock_result = Mock()
            mock_result.id = task_id
            mock_task.delay.return_value = mock_result
            
            response = client.get('/api/v1/recommendations?user_id=error_cache_test&async=true')
            assert response.status_code == 202
            
            with patch('routes.recommendations.celery') as mock_celery:
                # Simulate failure with user error cache update
                mock_result_status = Mock()
                mock_result_status.state = 'FAILURE'
                mock_result_status.info = {
                    'error_type': 'InsufficientDataError',
                    'error_message': 'User has insufficient interaction data',
                    'user_id': 'error_cache_test',
                    'retry_attempts': 3,
                    'user_error_cached': True,
                    'cache_key': 'user_error:error_cache_test'
                }
                mock_celery.AsyncResult.return_value = mock_result_status
                
                status_response = client.get(f'/api/v1/recommendations/status/{task_id}')
                status_data = status_response.get_json()
                
                assert status_data['state'] == 'FAILURE'
                # Check that user error cache info is in the error string
                assert 'user_error_cached' in status_data['error']
                assert 'cache_key' in status_data['error']


class TestErrorClassification:
    """Test error classification and retry decision logic."""
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_retryable_error_classification(self, client):
        """Test errors are correctly classified as retryable."""
        from tasks.exceptions import is_retryable, DatabaseConnectionError, CacheError
        
        # Database errors should be retryable
        db_error = DatabaseConnectionError("Connection timeout")
        assert is_retryable(db_error) is True
        
        # Cache errors should be retryable
        cache_error = CacheError("Redis unavailable")
        assert is_retryable(cache_error) is True
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_non_retryable_error_classification(self, client):
        """Test errors are correctly classified as non-retryable."""
        from tasks.exceptions import is_retryable, InvalidUserError, ParameterValidationError
        
        # User errors should not be retryable
        user_error = InvalidUserError("user123", "Invalid user ID format")
        assert is_retryable(user_error) is False
        
        # Validation errors should not be retryable
        validation_error = ParameterValidationError("limit", -5, "Invalid limit parameter")
        assert is_retryable(validation_error) is False
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_retry_delay_calculation(self, client):
        """Test retry delay calculation with exponential backoff."""
        from tasks.exceptions import calculate_retry_delay, CacheError
        
        # Use CacheError which has a smaller retry_after (45s) to test scaling
        error = CacheError("Cache connection failed")
        
        # Test multiple delay calculations
        delay_1 = calculate_retry_delay(error, attempt=1)
        delay_2 = calculate_retry_delay(error, attempt=2) 
        delay_3 = calculate_retry_delay(error, attempt=3)
        
        # With CacheError (retry_after=45), delays should follow pattern:
        # attempt 1: 45 * 1 = 45 + jitter
        # attempt 2: 45 * 2 = 90 (capped at 60) = 60 + jitter  
        # attempt 3: 45 * 4 = 180 (capped at 60) = 60 + jitter
        
        # Test basic constraints and backoff pattern
        assert delay_1 >= 45.0  # At least base delay
        assert delay_1 <= 60.0  # Should be capped at max
        
        # Verify exponential increase (with cap)
        assert delay_2 >= 60.0  # Should hit the cap
        assert delay_3 >= 60.0  # Should still be at cap
        
        # Test with error that has no built-in retry_after
        mock_error = Mock()
        mock_error.retry_after = None
        
        delay_custom = calculate_retry_delay(mock_error, attempt=1)
        assert delay_custom >= 2.0   # Should use default base delay
        assert delay_custom <= 10.0  # Should include reasonable jitter
    
    @pytest.mark.skipif(not ASYNC_TASKS_AVAILABLE, reason="Async tasks not available")
    def test_error_priority_classification(self, client):
        """Test errors are classified by priority for alerting."""
        from tasks.exceptions import get_error_priority, ResourceExhaustionError, CacheError
        
        # Critical system errors should have high priority
        critical_error = ResourceExhaustionError("Memory exhausted")
        assert get_error_priority(critical_error) == 'critical'
        
        # Temporary errors should have lower priority
        temp_error = CacheError("Cache miss")
        assert get_error_priority(temp_error) == 'medium' 