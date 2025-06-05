"""
Ranking Tasks for Celery Worker Queue.

This module contains Celery tasks for asynchronous ranking generation
and related recommendation processing tasks with comprehensive error handling.
"""

import time
import logging
import random
from typing import Dict, List, Optional

from celery import current_task
from celery.exceptions import Retry
from utils.celery_app import celery
from core.ranking_algorithm import generate_rankings_for_user

# Import our custom exceptions and validation
from tasks.exceptions import (
    RetryableError, PermanentError, 
    DatabaseConnectionError, RankingAlgorithmError, InsufficientDataError,
    InvalidUserError, UserAccessError, CacheError, ResourceExhaustionError,
    classify_exception, is_retryable, get_retry_delay
)
from tasks.validation import (
    validate_user_exists, check_sufficient_data, 
    validate_request_parameters, check_user_access_permissions,
    validate_system_health
)

# Set up logging
logger = logging.getLogger(__name__)

@celery.task(
    bind=True,
    name='generate_rankings_async',
    autoretry_for=(
        DatabaseConnectionError,
        RankingAlgorithmError,
        InsufficientDataError,
        CacheError,
        ResourceExhaustionError,
        ConnectionError,
        TimeoutError,
    ),
    retry_kwargs={
        'max_retries': 3,
        'countdown': 60,  # Base delay
    },
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=300,  # Max 5 minutes
    retry_jitter=True,  # Add randomness to avoid thundering herd
)
def generate_rankings_async(self, user_id: str, request_params: Optional[Dict] = None):
    """
    Asynchronously generate rankings for a user with comprehensive error handling.
    
    This task implements intelligent retry strategies, dead letter queue management,
    and comprehensive metrics tracking for production reliability.
    
    Args:
        user_id: User identifier for ranking generation
        request_params: Optional parameters (limit, force_refresh, etc.)
    
    Returns:
        Dict: Task result with rankings data and metadata
        
    Raises:
        PermanentError: For unrecoverable errors that should not be retried
        RetryableError: For transient errors that should trigger retries
    """
    task_start_time = time.time()
    attempt_number = self.request.retries + 1
    
    try:
        # Import metrics tracking
        from utils.worker_metrics import track_task_metrics, track_redis_operation
        
        # Update task state to PROGRESS
        self.update_state(
            state='PROGRESS',
            meta={
                'progress': 0, 
                'stage': 'Starting ranking generation',
                'user_id': user_id,
                'attempt': attempt_number,
                'max_retries': 3
            }
        )
        
        logger.info(f"Starting async ranking generation for user {user_id} (attempt {attempt_number})")
        
        # Validate system health before proceeding
        try:
            system_health = validate_system_health()
            logger.debug(f"System health check passed: {system_health}")
        except Exception as e:
            classified_error = classify_exception(e)
            logger.error(f"System health check failed: {classified_error}")
            raise classified_error
        
        # Validate and sanitize request parameters
        try:
            validated_params = validate_request_parameters(request_params or {})
            logger.debug(f"Request parameters validated: {validated_params}")
        except Exception as e:
            # Parameter validation errors are permanent
            logger.error(f"Parameter validation failed for user {user_id}: {e}")
            raise
        
        # Update progress - validating user
        self.update_state(
            state='PROGRESS',
            meta={
                'progress': 10, 
                'stage': 'Validating user',
                'user_id': user_id,
                'attempt': attempt_number
            }
        )
        
        # Validate user exists and has access permissions
        try:
            if not validate_user_exists(user_id):
                raise InvalidUserError(user_id, "User does not exist")
            
            if not check_user_access_permissions(user_id, 'ranking'):
                raise UserAccessError(user_id, "User does not have ranking permissions")
            
            logger.debug(f"User validation passed for {user_id}")
        except (InvalidUserError, UserAccessError):
            # These are permanent errors
            raise
        except Exception as e:
            # Database connection issues are retryable
            classified_error = classify_exception(e)
            logger.error(f"User validation failed for {user_id}: {classified_error}")
            raise classified_error
        
        # Update progress - checking data sufficiency
        self.update_state(
            state='PROGRESS', 
            meta={
                'progress': 20, 
                'stage': 'Checking data availability',
                'user_id': user_id,
                'attempt': attempt_number
            }
        )
        
        # Check if user has sufficient interaction data
        try:
            if not check_sufficient_data(user_id):
                raise InsufficientDataError(
                    f"User {user_id} has insufficient interaction data for ranking",
                    data_type="user_interactions"
                )
            logger.debug(f"Data sufficiency check passed for {user_id}")
        except InsufficientDataError:
            # This is retryable - more data might arrive later
            raise
        except Exception as e:
            classified_error = classify_exception(e)
            logger.error(f"Data sufficiency check failed for {user_id}: {classified_error}")
            raise classified_error
        
        # Update progress - generating rankings
        self.update_state(
            state='PROGRESS', 
            meta={
                'progress': 40, 
                'stage': 'Calculating ranking scores',
                'user_id': user_id,
                'attempt': attempt_number
            }
        )
        
        # Generate rankings using existing algorithm with error wrapping
        try:
            logger.debug(f"Calling generate_rankings_for_user for user {user_id}")
            ranking_start_time = time.time()
            ranked_posts = generate_rankings_for_user(user_id)
            ranking_duration = time.time() - ranking_start_time
            
            logger.debug(f"Ranking algorithm completed in {ranking_duration:.3f}s for user {user_id}")
            
        except Exception as e:
            # Classify and wrap algorithm errors appropriately
            exc_str = str(e).lower()
            
            if 'database' in exc_str or 'connection' in exc_str:
                raise DatabaseConnectionError(f"Database error during ranking: {e}")
            elif 'insufficient' in exc_str or 'no data' in exc_str or 'empty' in exc_str:
                raise InsufficientDataError(f"Insufficient data for ranking: {e}")
            elif 'memory' in exc_str or 'resource' in exc_str:
                raise ResourceExhaustionError('memory', f"Resource error during ranking: {e}")
            else:
                raise RankingAlgorithmError(f"Algorithm execution failed: {e}", algorithm_stage='ranking')
        
        # Validate that we got results
        if not ranked_posts:
            raise InsufficientDataError(f"No posts available for ranking for user {user_id}")
        
        # Update progress - storing results
        self.update_state(
            state='PROGRESS',
            meta={
                'progress': 80, 
                'stage': 'Storing results in cache',
                'user_id': user_id,
                'rankings_count': len(ranked_posts),
                'attempt': attempt_number
            }
        )
        
        # Store results in cache with Redis operation tracking
        cache_key = f"async_rankings:{user_id}"
        try:
            cache_start_time = time.time()
            
            from utils.cache import cache_set, cache_recommendations
            cache_data = {
                'rankings': ranked_posts,
                'timestamp': time.time(),
                'user_id': user_id,
                'request_params': validated_params,
                'task_id': self.request.id,
                'attempt': attempt_number
            }
            
            cache_result = cache_set(cache_key, cache_data, ttl=3600)  # 1 hour TTL
            if not cache_result:
                logger.warning(f"Cache set returned False for user {user_id}")
            
            # Also cache using existing function for compatibility
            cache_recommendations(user_id, ranked_posts)
            
            cache_duration = time.time() - cache_start_time
            track_redis_operation('cache_set', cache_duration, True)
            
            logger.debug(f"Successfully cached rankings for user {user_id}")
            
        except Exception as cache_error:
            cache_duration = time.time() - cache_start_time if 'cache_start_time' in locals() else 0
            track_redis_operation('cache_set', cache_duration, False)
            
            # Cache errors are retryable but don't fail the entire task
            logger.warning(f"Failed to cache rankings for user {user_id}: {cache_error}")
            cache_key = None  # Indicate caching failed
        
        # Calculate final metrics
        total_processing_time = time.time() - task_start_time
        
        # Track comprehensive metrics
        try:
            from utils.metrics import track_recommendation_processing_time
            from utils.worker_metrics import calculate_task_quality_score
            
            track_recommendation_processing_time(total_processing_time)
            
            quality_score = calculate_task_quality_score(ranked_posts, user_id)
            
            # Track detailed task metrics
            track_task_metrics(
                task_id=self.request.id,
                user_id=user_id,
                status='success',
                processing_time=total_processing_time,
                attempts=attempt_number,
                cache_hit=False,  # This is always a fresh generation
                quality_score=quality_score,
                result_size_bytes=len(str(ranked_posts).encode('utf-8')),
                queue_name='rankings'
            )
            
        except Exception as metrics_error:
            logger.warning(f"Failed to track metrics: {metrics_error}")
        
        # Build final result
        result = {
            'status': 'SUCCESS',
            'user_id': user_id,
            'rankings_count': len(ranked_posts),
            'processing_time': total_processing_time,
            'cache_key': cache_key,
            'timestamp': time.time(),
            'request_params': validated_params,
            'task_id': self.request.id,
            'attempts': attempt_number,
            'worker_id': self.request.hostname
        }
        
        logger.info(
            f"Successfully generated {len(ranked_posts)} rankings for user {user_id} "
            f"in {total_processing_time:.3f} seconds (attempt {attempt_number})"
        )
        
        return result
        
    except PermanentError as exc:
        # Don't retry permanent errors
        processing_time = time.time() - task_start_time
        
        logger.error(f"Permanent error for user {user_id} (attempt {attempt_number}): {exc}")
        
        # Track failure metrics
        try:
            from utils.worker_metrics import track_task_metrics, track_dlq_entry
            
            track_task_metrics(
                task_id=self.request.id,
                user_id=user_id,
                status='failure',
                processing_time=processing_time,
                attempts=attempt_number,
                error_type='permanent'
            )
            
            track_dlq_entry('permanent', user_id, self.request.id)
            
        except Exception as metrics_error:
            logger.warning(f"Failed to track failure metrics: {metrics_error}")
        
        # Send to dead letter queue
        try:
            from tasks.dead_letter_queue import send_to_dead_letter_queue
            send_to_dead_letter_queue.delay(
                task_id=self.request.id,
                user_id=user_id,
                error_type='permanent',
                error_message=str(exc),
                attempts=attempt_number,
                original_params=request_params
            )
        except Exception as dlq_error:
            logger.error(f"Failed to send task to DLQ: {dlq_error}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'error_type': 'permanent',
                'user_id': user_id,
                'attempts': attempt_number,
                'processing_time': processing_time
            }
        )
        raise
        
    except RetryableError as exc:
        # Handle retryable errors with intelligent backoff
        processing_time = time.time() - task_start_time
        
        logger.warning(f"Retryable error for user {user_id} (attempt {attempt_number}): {exc}")
        
        # Track retry metrics
        try:
            from utils.worker_metrics import track_task_metrics
            
            track_task_metrics(
                task_id=self.request.id,
                user_id=user_id,
                status='retry',
                processing_time=processing_time,
                attempts=attempt_number,
                error_type=type(exc).__name__
            )
            
        except Exception as metrics_error:
            logger.warning(f"Failed to track retry metrics: {metrics_error}")
        
        # Check if we've exceeded max retries
        if self.request.retries >= 3:
            logger.error(f"Max retries reached for user {user_id}: {exc}")
            
            try:
                from utils.worker_metrics import track_task_metrics, track_dlq_entry
                
                track_task_metrics(
                    task_id=self.request.id,
                    user_id=user_id,
                    status='failure',
                    processing_time=processing_time,
                    attempts=attempt_number,
                    error_type='max_retries'
                )
                
                track_dlq_entry('max_retries', user_id, self.request.id)
                
            except Exception as metrics_error:
                logger.warning(f"Failed to track max retries metrics: {metrics_error}")
            
            # Send to dead letter queue
            try:
                from tasks.dead_letter_queue import send_to_dead_letter_queue
                send_to_dead_letter_queue.delay(
                    task_id=self.request.id,
                    user_id=user_id,
                    error_type='max_retries',
                    error_message=str(exc),
                    attempts=attempt_number,
                    original_params=request_params
                )
            except Exception as dlq_error:
                logger.error(f"Failed to send task to DLQ: {dlq_error}")
            
            self.update_state(
                state='FAILURE',
                meta={
                    'error': str(exc),
                    'error_type': 'max_retries',
                    'user_id': user_id,
                    'attempts': attempt_number,
                    'processing_time': processing_time
                }
            )
            raise
        
        # Calculate backoff delay with jitter
        countdown = get_retry_delay(exc, attempt_number)
        
        logger.info(f"Retrying task for user {user_id} in {countdown} seconds (attempt {attempt_number})")
        
        self.update_state(
            state='RETRY',
            meta={
                'error': str(exc),
                'retry_in': countdown,
                'attempt': attempt_number,
                'user_id': user_id,
                'processing_time': processing_time
            }
        )
        
        raise self.retry(countdown=countdown, exc=exc)
        
    except Exception as exc:
        # Unexpected errors - classify and handle appropriately
        processing_time = time.time() - task_start_time
        
        logger.error(f"Unexpected error for user {user_id} (attempt {attempt_number}): {exc}")
        
        # Try to classify the error
        try:
            classified_error = classify_exception(exc)
            logger.info(f"Classified unexpected error as: {type(classified_error).__name__}")
            
            # If it's retryable and we haven't exhausted retries, retry it
            if isinstance(classified_error, RetryableError) and self.request.retries < 2:
                # Treat as retryable for first 2 attempts
                raise classified_error
            
        except Exception as classification_error:
            logger.error(f"Failed to classify error: {classification_error}")
        
        # Track as unexpected failure
        try:
            from utils.worker_metrics import track_task_metrics, track_dlq_entry
            
            track_task_metrics(
                task_id=self.request.id,
                user_id=user_id,
                status='failure',
                processing_time=processing_time,
                attempts=attempt_number,
                error_type='unexpected'
            )
            
            track_dlq_entry('unexpected', user_id, self.request.id)
            
        except Exception as metrics_error:
            logger.warning(f"Failed to track unexpected error metrics: {metrics_error}")
        
        # Send to dead letter queue
        try:
            from tasks.dead_letter_queue import send_to_dead_letter_queue
            send_to_dead_letter_queue.delay(
                task_id=self.request.id,
                user_id=user_id,
                error_type='unexpected',
                error_message=str(exc),
                attempts=attempt_number,
                original_params=request_params
            )
        except Exception as dlq_error:
            logger.error(f"Failed to send unexpected error to DLQ: {dlq_error}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'error_type': 'unexpected',
                'user_id': user_id,
                'attempts': attempt_number,
                'processing_time': processing_time
            }
        )
        raise

@celery.task(bind=True, name='generate_rankings_batch')
def generate_rankings_batch(self, user_ids: List[str], request_params: Optional[Dict] = None):
    """
    Generate rankings for multiple users in batch.
    
    This task is useful for pre-warming caches or bulk processing.
    
    Args:
        user_ids: List of user identifiers
        request_params: Optional parameters applied to all users
        
    Returns:
        Dict: Batch processing results
    """
    try:
        self.update_state(
            state='PROGRESS',
            meta={
                'progress': 0,
                'stage': 'Starting batch processing',
                'total_users': len(user_ids),
                'completed_users': 0
            }
        )
        
        logger.info(f"Starting batch ranking generation for {len(user_ids)} users")
        start_time = time.time()
        
        results = []
        failed_users = []
        
        for i, user_id in enumerate(user_ids):
            try:
                # Update progress
                progress = int((i / len(user_ids)) * 100)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'progress': progress,
                        'stage': f'Processing user {i+1}/{len(user_ids)}',
                        'current_user': user_id,
                        'total_users': len(user_ids),
                        'completed_users': i,
                        'failed_users': len(failed_users)
                    }
                )
                
                # Generate rankings for this user
                ranked_posts = generate_rankings_for_user(user_id)
                
                # Cache the results
                try:
                    from utils.cache import cache_set
                    cache_key = f"async_rankings:{user_id}"
                    cache_data = {
                        'rankings': ranked_posts,
                        'timestamp': time.time(),
                        'user_id': user_id,
                        'request_params': request_params or {},
                        'batch_processed': True
                    }
                    cache_set(cache_key, cache_data, ttl=3600)
                except Exception as cache_error:
                    logger.warning(f"Failed to cache rankings for user {user_id}: {cache_error}")
                
                results.append({
                    'user_id': user_id,
                    'status': 'success',
                    'rankings_count': len(ranked_posts)
                })
                
            except Exception as user_error:
                logger.error(f"Failed to process user {user_id}: {user_error}")
                failed_users.append(user_id)
                results.append({
                    'user_id': user_id,
                    'status': 'failed',
                    'error': str(user_error)
                })
        
        processing_time = time.time() - start_time
        
        batch_result = {
            'status': 'COMPLETED',
            'total_users': len(user_ids),
            'successful_users': len(user_ids) - len(failed_users),
            'failed_users': len(failed_users),
            'processing_time': processing_time,
            'results': results,
            'timestamp': time.time()
        }
        
        logger.info(
            f"Batch processing completed: {len(user_ids) - len(failed_users)}/{len(user_ids)} "
            f"users successful in {processing_time:.3f} seconds"
        )
        
        return batch_result
        
    except Exception as exc:
        logger.error(f"Batch task failed: {exc}")
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'stage': 'Batch processing failed'
            }
        )
        raise 