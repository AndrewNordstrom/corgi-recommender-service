"""
Custom exceptions for task processing.
"""

import time
import random


class TaskExecutionError(Exception):
    """Raised when a task fails to execute properly."""
    pass


class RetryableError(TaskExecutionError):
    """Raised when a task fails but can be retried."""
    pass


class PermanentError(TaskExecutionError):
    """Raised when a task fails and should not be retried."""
    pass


class DatabaseConnectionError(RetryableError):
    """Raised when database connection fails."""
    pass


class RankingAlgorithmError(RetryableError):
    """Raised when ranking algorithm fails."""
    def __init__(self, message, algorithm_stage=None):
        super().__init__(message)
        self.algorithm_stage = algorithm_stage


class InsufficientDataError(RetryableError):
    """Raised when insufficient data is available."""
    def __init__(self, message, data_type=None):
        super().__init__(message)
        self.data_type = data_type


class InvalidUserError(PermanentError):
    """Raised when user is invalid."""
    def __init__(self, user_id, message):
        super().__init__(message)
        self.user_id = user_id


class UserAccessError(PermanentError):
    """Raised when user lacks access permissions."""
    def __init__(self, user_id, message):
        super().__init__(message)
        self.user_id = user_id


class CacheError(RetryableError):
    """Raised when cache operations fail."""
    pass


class ResourceExhaustionError(RetryableError):
    """Raised when system resources are exhausted."""
    def __init__(self, resource_type, message):
        super().__init__(message)
        self.resource_type = resource_type


def classify_exception(exception):
    """Classify an exception as retryable or permanent."""
    exc_str = str(exception).lower()
    
    if 'database' in exc_str or 'connection' in exc_str:
        return DatabaseConnectionError(f"Database error: {exception}")
    elif 'insufficient' in exc_str or 'no data' in exc_str:
        return InsufficientDataError(f"Data error: {exception}")
    elif 'memory' in exc_str or 'resource' in exc_str:
        return ResourceExhaustionError('memory', f"Resource error: {exception}")
    elif 'user' in exc_str and 'not found' in exc_str:
        return InvalidUserError('unknown', f"User error: {exception}")
    else:
        return RetryableError(f"General error: {exception}")


def is_retryable(exception):
    """Check if an exception is retryable."""
    return isinstance(exception, RetryableError)


def get_retry_delay(attempt_number, base_delay=60, max_delay=300):
    """Calculate retry delay with exponential backoff and jitter."""
    delay = min(base_delay * (2 ** (attempt_number - 1)), max_delay)
    jitter = random.uniform(0.8, 1.2)
    return delay * jitter 