"""
Shared testing utilities for Phase 5 async flow testing.

This module provides common fixtures, helpers, and utilities for testing
the asynchronous worker queue system end-to-end.
"""

import json
import time
import uuid
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

# Test configuration
TEST_REDIS_PREFIX = "test:corgi:async:"
TEST_CELERY_QUEUE = "test_celery_queue"
DEFAULT_TIMEOUT = 30  # seconds


class AsyncTestHelper:
    """Helper class for async testing operations."""
    
    def __init__(self, client, redis_client=None):
        self.client = client
        self.redis_client = redis_client
        self.created_tasks = []
        self.created_cache_keys = []
    
    def cleanup(self):
        """Clean up test data created during testing."""
        # Cancel any created tasks
        for task_id in self.created_tasks:
            try:
                self.client.delete(f'/api/v1/recommendations/status/{task_id}')
            except:
                pass  # Ignore cleanup errors
        
        # Clear test cache keys
        if self.redis_client:
            for key in self.created_cache_keys:
                try:
                    self.redis_client.delete(key)
                except:
                    pass
        
        self.created_tasks.clear()
        self.created_cache_keys.clear()
    
    def make_async_request(self, user_id, **params):
        """Make an async recommendation request and track the task."""
        params['user_id'] = user_id
        params['async'] = 'true'
        
        response = self.client.get('/api/v1/recommendations', query_string=params)
        
        if response.status_code == 202:
            data = response.get_json()
            task_id = data.get('task_id')
            if task_id:
                self.created_tasks.append(task_id)
        
        return response
    
    def poll_task_status(self, task_id, timeout=DEFAULT_TIMEOUT, expected_state='SUCCESS'):
        """Poll task status until completion or timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = self.client.get(f'/api/v1/recommendations/status/{task_id}')
            
            if response.status_code != 200:
                return response
            
            data = response.get_json()
            state = data.get('state', 'UNKNOWN')
            
            # Return if we've reached the expected state
            if state == expected_state:
                return response
            
            # Return if we've reached a terminal state (even if not expected)
            if state in ['SUCCESS', 'FAILURE', 'REVOKED']:
                return response
            
            # Wait before next poll
            time.sleep(0.5)
        
        # Timeout reached
        raise TimeoutError(f"Task {task_id} did not reach {expected_state} within {timeout}s")
    
    def wait_for_cache_key(self, cache_key, timeout=DEFAULT_TIMEOUT):
        """Wait for a cache key to appear."""
        if not self.redis_client:
            return False
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.redis_client.exists(cache_key):
                return True
            time.sleep(0.5)
        
        return False
    
    def create_test_cache_key(self, suffix=""):
        """Create a test cache key and track it for cleanup."""
        key = f"{TEST_REDIS_PREFIX}{uuid.uuid4().hex}{suffix}"
        self.created_cache_keys.append(key)
        return key


@pytest.fixture
def async_test_helper(client):
    """Create an async test helper instance."""
    helper = AsyncTestHelper(client)
    yield helper
    helper.cleanup()


@pytest.fixture
def mock_celery_task():
    """Mock a Celery task for testing."""
    with patch('tasks.ranking_tasks.generate_rankings_async') as mock_task:
        # Create a mock result with a task ID
        mock_result = Mock()
        mock_result.id = f"test-task-{uuid.uuid4().hex[:8]}"
        mock_result.state = 'PENDING'
        mock_result.result = None
        
        # Configure the task mock
        mock_task.delay.return_value = mock_result
        mock_task.AsyncResult.return_value = mock_result
        
        yield mock_task, mock_result


@pytest.fixture
def mock_successful_task():
    """Mock a successfully completed Celery task."""
    with patch('utils.celery_app.celery') as mock_celery:
        # Create successful task result
        mock_result = Mock()
        mock_result.id = f"success-task-{uuid.uuid4().hex[:8]}"
        mock_result.state = 'SUCCESS'
        mock_result.result = {
            'user_id': 'test_user',
            'rankings_count': 15,
            'processing_time': 2.3,
            'cache_key': 'async_rankings:test_user',
            'generated_at': datetime.now().isoformat()
        }
        mock_result.info = mock_result.result
        
        mock_celery.AsyncResult.return_value = mock_result
        yield mock_celery, mock_result


@pytest.fixture
def mock_failed_task():
    """Mock a failed Celery task."""
    with patch('utils.celery_app.celery') as mock_celery:
        # Create failed task result
        mock_result = Mock()
        mock_result.id = f"failed-task-{uuid.uuid4().hex[:8]}"
        mock_result.state = 'FAILURE'
        mock_result.result = None
        mock_result.info = {
            'error': 'DatabaseConnectionError: Connection failed',
            'error_type': 'DatabaseConnectionError',
            'user_id': 'test_user',
            'attempts': 3,
            'timestamp': datetime.now().isoformat()
        }
        
        mock_celery.AsyncResult.return_value = mock_result
        yield mock_celery, mock_result


@contextmanager
def simulate_task_progression(mock_result, states=None, delays=None):
    """Simulate a task progressing through different states."""
    if states is None:
        states = ['PENDING', 'STARTED', 'SUCCESS']
    if delays is None:
        delays = [0.1, 0.2, 0.1]  # delays between state changes
    
    def get_state():
        return mock_result.state
    
    # Start in first state
    mock_result.state = states[0]
    
    # Yield control to test
    yield mock_result
    
    # Progress through states with delays
    for i, (state, delay) in enumerate(zip(states[1:], delays)):
        time.sleep(delay)
        mock_result.state = state
        
        # Update result based on state
        if state == 'SUCCESS':
            mock_result.result = {
                'user_id': 'test_user',
                'rankings_count': 10,
                'processing_time': sum(delays[:i+1]),
                'cache_key': 'async_rankings:test_user'
            }
            mock_result.info = mock_result.result
        elif state == 'FAILURE':
            mock_result.result = None
            mock_result.info = {
                'error': 'Test error',
                'user_id': 'test_user'
            }


def create_test_recommendations_data(user_id="test_user", count=10):
    """Create test recommendations data."""
    return {
        'user_id': user_id,
        'recommendations': [
            {
                'id': f'post_{i}',
                'score': 0.9 - (0.1 * i),
                'content': f'Test post content {i}',
                'created_at': datetime.now().isoformat(),
                'account': {
                    'id': f'account_{i}',
                    'username': f'user_{i}',
                    'display_name': f'Test User {i}'
                }
            }
            for i in range(count)
        ],
        'metadata': {
            'source': 'async_worker',
            'algorithm_version': '2.0',
            'generated_at': datetime.now().isoformat(),
            'processing_time': 2.5,
            'total_candidates': count * 2
        }
    }


def assert_async_response_format(response_data):
    """Assert that an async response has the correct format."""
    assert 'status' in response_data
    assert 'task_id' in response_data
    assert 'status_url' in response_data
    assert 'user_id' in response_data
    assert 'async_enabled' in response_data
    assert response_data['async_enabled'] is True
    assert response_data['status'] in ['processing', 'queued']


def assert_task_status_format(response_data):
    """Assert that a task status response has the correct format."""
    assert 'task_id' in response_data
    assert 'state' in response_data
    assert 'status' in response_data
    assert 'progress' in response_data
    
    # State should be a valid Celery state
    valid_states = ['PENDING', 'STARTED', 'SUCCESS', 'FAILURE', 'RETRY', 'REVOKED']
    assert response_data['state'] in valid_states
    
    # Progress should be a number
    assert isinstance(response_data['progress'], (int, float))


def assert_recommendations_format(response_data):
    """Assert that recommendations data has the correct format."""
    assert 'user_id' in response_data
    assert 'recommendations' in response_data
    assert 'metadata' in response_data
    
    # Check recommendations structure
    recommendations = response_data['recommendations']
    assert isinstance(recommendations, list)
    
    if recommendations:  # If we have recommendations
        for rec in recommendations:
            assert 'id' in rec
            assert 'score' in rec
            assert isinstance(rec['score'], (int, float))
            assert 0 <= rec['score'] <= 1


# Configuration helpers
def get_test_celery_config():
    """Get Celery configuration for testing."""
    return {
        'broker_url': 'redis://localhost:6379/15',  # Use test database
        'result_backend': 'redis://localhost:6379/15',
        'task_always_eager': True,  # Execute tasks synchronously for testing
        'task_eager_propagates': True,  # Propagate exceptions in eager mode
        'task_routes': {
            'tasks.ranking_tasks.generate_rankings_async': {'queue': TEST_CELERY_QUEUE}
        }
    }


def get_test_redis_config():
    """Get Redis configuration for testing."""
    return {
        'host': 'localhost',
        'port': 6379,
        'db': 15,  # Use test database
        'decode_responses': True,
        'prefix': TEST_REDIS_PREFIX
    } 