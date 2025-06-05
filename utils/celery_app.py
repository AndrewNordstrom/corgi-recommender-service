"""
Celery Application Factory for Corgi Recommender Service.

This module provides the Celery application configuration for asynchronous 
task processing, primarily for ranking generation tasks.
"""

import os
from celery import Celery
from config import REDIS_URL
import logging

logger = logging.getLogger(__name__)

def create_celery_app(app=None):
    """Create and configure Celery app."""
    celery = Celery('corgi_recommender')
    
    # Basic Celery configuration
    celery.conf.update(
        broker_url=REDIS_URL,
        result_backend=REDIS_URL,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        include=['tasks.ranking_tasks', 'tasks.dead_letter_queue', 'tasks.monitoring_tasks']
    )
    
    # Import beat configuration
    try:
        from utils.celery_beat_config import (
            CELERY_BEAT_SCHEDULE, CELERY_TASK_ROUTES, CELERY_TASK_ANNOTATIONS,
            CELERY_WORKER_PREFETCH_MULTIPLIER, CELERY_WORKER_MAX_TASKS_PER_CHILD,
            CELERY_BEAT_SCHEDULER, CELERY_BEAT_SCHEDULE_FILENAME
        )
        
        # Apply beat schedule configuration
        celery.conf.beat_schedule = CELERY_BEAT_SCHEDULE
        celery.conf.task_routes = CELERY_TASK_ROUTES
        celery.conf.task_annotations = CELERY_TASK_ANNOTATIONS
        celery.conf.worker_prefetch_multiplier = CELERY_WORKER_PREFETCH_MULTIPLIER
        celery.conf.worker_max_tasks_per_child = CELERY_WORKER_MAX_TASKS_PER_CHILD
        celery.conf.beat_scheduler = CELERY_BEAT_SCHEDULER
        celery.conf.beat_schedule_filename = CELERY_BEAT_SCHEDULE_FILENAME
        
        logger.info("Celery beat schedule and routing configuration loaded successfully")
        
    except ImportError as e:
        logger.warning(f"Could not load beat configuration: {e}")
    
    # Additional Celery configuration
    celery.conf.update(
        # Task execution settings
        task_track_started=True,
        task_ignore_result=False,
        result_expires=3600,  # 1 hour
        task_acks_late=True,
        worker_disable_rate_limits=False,
        
        # Queue configuration
        task_default_queue='rankings',
        
        # Worker configuration
        worker_max_tasks_per_child=100,
        worker_time_limit=300,  # 5 minutes
        worker_soft_time_limit=240,  # 4 minutes
        
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        
        # Error handling
        task_reject_on_worker_lost=True,
    )
    
    # Flask integration
    if app:
        class ContextTask(celery.Task):
            """Make celery tasks work with Flask app context."""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery

# Backward compatibility function
def make_celery(app=None):
    """Backward compatibility wrapper for create_celery_app."""
    return create_celery_app(app)

# Create a global celery instance for import in tasks
celery = create_celery_app() 