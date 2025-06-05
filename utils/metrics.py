"""
Metrics module for the Corgi Recommender Service.

This module provides Prometheus metrics collectors for tracking the performance
and quality of the recommendation and injection systems.
"""

import logging
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    REGISTRY,
    write_to_textfile,
)
from prometheus_client import start_http_server, push_to_gateway
import os
import time
import threading

# Create logger
logger = logging.getLogger(__name__)

# Define metrics
# Counters - track total numbers of events
INJECTED_POSTS_TOTAL = Counter(
    "corgi_injected_posts_total",
    "Total number of posts injected into timelines",
    ["strategy", "source"],
)

RECOMMENDATIONS_TOTAL = Counter(
    "corgi_recommendations_total",
    "Total number of recommendations generated",
    ["source", "user_type"],
)

FALLBACK_USAGE_TOTAL = Counter(
    "corgi_fallback_usage_total",
    "Number of times the system fell back to cold start",
    ["reason"],
)

RECOMMENDATION_INTERACTIONS = Counter(
    "corgi_recommendation_interactions_total",
    "User interactions with recommended posts",
    ["action_type", "post_type"],
)

# Cache metrics
CACHE_HIT_TOTAL = Counter(
    "corgi_cache_hit_total",
    "Total number of cache hits",
    ["cache_type", "endpoint"],
)

CACHE_MISS_TOTAL = Counter(
    "corgi_cache_miss_total", 
    "Total number of cache misses",
    ["cache_type", "endpoint"],
)

CACHE_ERROR_TOTAL = Counter(
    "corgi_cache_error_total",
    "Total number of cache errors", 
    ["cache_type", "error_type"],
)

CACHE_EVICTIONS_TOTAL = Counter(
    "corgi_cache_evictions_total",
    "Total number of cache evictions",
    ["cache_type", "reason"],
)

CACHE_OPERATION_SECONDS = Histogram(
    "corgi_cache_operation_seconds",
    "Time taken for cache operations",
    ["operation", "cache_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# Histograms - track distribution of values
RECOMMENDATION_SCORES = Histogram(
    "corgi_recommendation_scores",
    "Distribution of recommendation scores",
    ["strategy"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

INJECTION_PROCESSING_TIME = Histogram(
    "corgi_injection_processing_time_seconds",
    "Time taken to process timeline injection",
    ["strategy"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

RECOMMENDATION_PROCESSING_TIME = Histogram(
    "corgi_recommendation_processing_time_seconds",
    "Time taken to generate recommendations",
    ["source"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Gauges - track current values
CURRENT_RECOMMENDATION_CACHE_SIZE = Gauge(
    "corgi_recommendation_cache_size", "Current number of cached recommendation sets"
)

TIMELINE_POST_COUNT = Gauge(
    "corgi_timeline_post_count", "Number of posts in timeline responses", ["post_type"]
)

# Summaries - track averages and percentiles
INJECTION_RATIO = Summary(
    "corgi_injection_ratio",
    "Ratio of injected posts to total posts in timeline",
)

# Flag to track if we should use file-based metrics (useful if HTTP server can't be started)
USE_FILE_BASED_METRICS = os.getenv("USE_FILE_BASED_METRICS", "false").lower() == "true"
METRICS_FILE_PATH = os.getenv("METRICS_FILE_PATH", "/tmp/corgi_metrics.prom")
METRICS_PUSH_GATEWAY = os.getenv("METRICS_PUSH_GATEWAY", "")

# Background thread for periodically flushing metrics to file/gateway
metrics_thread = None
_should_stop = False


def periodic_metrics_flush():
    """Background thread function to periodically flush metrics."""
    while not _should_stop:
        try:
            # If file-based metrics is enabled, write to file
            if USE_FILE_BASED_METRICS:
                write_to_textfile(METRICS_FILE_PATH, REGISTRY)
                logger.debug(f"Metrics flushed to file: {METRICS_FILE_PATH}")

            # If push gateway is configured, push to it
            if METRICS_PUSH_GATEWAY:
                push_to_gateway(
                    METRICS_PUSH_GATEWAY, job="corgi_recommender", registry=REGISTRY
                )
                logger.debug(f"Metrics pushed to gateway: {METRICS_PUSH_GATEWAY}")

        except Exception as e:
            logger.error(f"Error flushing metrics: {e}")

        # Sleep for a while before next flush (10 seconds)
        time.sleep(10)


def start_metrics_server(port=9100):
    """
    Start the Prometheus metrics HTTP server.

    Args:
        port: Port number to serve metrics on (default: 9100)
    """
    global metrics_thread, _should_stop

    try:
        # Check if a server is already running on this port
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", port))
        sock.close()

        if result == 0:
            # Port is already in use
            logger.warning(
                f"Port {port} is already in use, metrics server may already be running"
            )
            logger.info(
                f"Metrics are still being collected and will be exported on port {port}"
            )
        else:
            # Start the HTTP server for metrics
            start_http_server(port)
            logger.info(f"Metrics server started on port {port}")

        # Start background flush thread if needed
        if (USE_FILE_BASED_METRICS or METRICS_PUSH_GATEWAY) and metrics_thread is None:
            _should_stop = False
            metrics_thread = threading.Thread(
                target=periodic_metrics_flush, daemon=True
            )
            metrics_thread.start()
            logger.info(f"Metrics background flush thread started")

    except Exception as e:
        logger.error(f"Failed to start metrics HTTP server: {e}")
        logger.warning("Falling back to file-based metrics collection")

        # Enable file-based metrics as fallback
        # No need for global declaration since it's module-level
        USE_FILE_BASED_METRICS = True

        # Start background flush thread if not already running
        if metrics_thread is None:
            _should_stop = False
            metrics_thread = threading.Thread(
                target=periodic_metrics_flush, daemon=True
            )
            metrics_thread.start()
            logger.info(
                f"Metrics fallback flush thread started, writing to {METRICS_FILE_PATH}"
            )


def track_injection(strategy, source, count=1):
    """
    Track a post injection event.

    Args:
        strategy: Injection strategy used (e.g., 'uniform', 'tag_match')
        source: Source of injected posts (e.g., 'cold_start', 'personalized')
        count: Number of posts injected (default: 1)
    """
    INJECTED_POSTS_TOTAL.labels(strategy=strategy, source=source).inc(count)


def track_recommendation_generation(source, user_type, count=1):
    """
    Track a recommendation generation event.

    Args:
        source: Source of recommendations (e.g., 'ranking_algorithm', 'cold_start')
        user_type: Type of user (e.g., 'new', 'returning', 'anonymous')
        count: Number of recommendations generated (default: 1)
    """
    RECOMMENDATIONS_TOTAL.labels(source=source, user_type=user_type).inc(count)


def track_fallback(reason):
    """
    Track a fallback to cold start.

    Args:
        reason: Reason for fallback (e.g., 'no_data', 'error', 'new_user')
    """
    FALLBACK_USAGE_TOTAL.labels(reason=reason).inc()


def track_recommendation_interaction(action_type, is_injected):
    """
    Track a user interaction with a recommended post.

    Args:
        action_type: Type of interaction (e.g., 'favorite', 'reblog', 'more_like_this')
        is_injected: Whether the post was injected (True) or organic (False)
    """
    post_type = "injected" if is_injected else "organic"
    RECOMMENDATION_INTERACTIONS.labels(
        action_type=action_type, post_type=post_type
    ).inc()


def track_recommendation_score(strategy, score):
    """
    Track a recommendation score.

    Args:
        strategy: Strategy used for recommendation
        score: Recommendation score (0-1)
    """
    RECOMMENDATION_SCORES.labels(strategy=strategy).observe(score)


def track_injection_processing_time(strategy, seconds):
    """
    Track time taken to process timeline injection.

    Args:
        strategy: Injection strategy used
        seconds: Processing time in seconds
    """
    INJECTION_PROCESSING_TIME.labels(strategy=strategy).observe(seconds)


def track_recommendation_processing_time(source, seconds):
    """
    Track time taken to generate recommendations.

    Args:
        source: Source of recommendations
        seconds: Processing time in seconds
    """
    RECOMMENDATION_PROCESSING_TIME.labels(source=source).observe(seconds)


def set_recommendation_cache_size(size):
    """
    Set the current recommendation cache size.

    Args:
        size: Current cache size
    """
    CURRENT_RECOMMENDATION_CACHE_SIZE.set(size)


def track_timeline_post_counts(real_count, injected_count):
    """
    Track counts of posts in timeline responses.

    Args:
        real_count: Number of real (non-injected) posts
        injected_count: Number of injected posts
    """
    TIMELINE_POST_COUNT.labels(post_type="real").set(real_count)
    TIMELINE_POST_COUNT.labels(post_type="injected").set(injected_count)

    # Also track the injection ratio
    if real_count + injected_count > 0:
        ratio = injected_count / (real_count + injected_count)
        INJECTION_RATIO.observe(ratio)


def force_metrics_flush():
    """
    Force a flush of metrics to the file or push gateway.

    This is primarily for debugging and testing purposes.
    """
    try:
        # If file-based metrics is enabled, write to file
        if USE_FILE_BASED_METRICS:
            write_to_textfile(METRICS_FILE_PATH, REGISTRY)
            logger.info(f"Metrics manually flushed to file: {METRICS_FILE_PATH}")

        # If push gateway is configured, push to it
        if METRICS_PUSH_GATEWAY:
            push_to_gateway(
                METRICS_PUSH_GATEWAY, job="corgi_recommender", registry=REGISTRY
            )
            logger.info(f"Metrics manually pushed to gateway: {METRICS_PUSH_GATEWAY}")

        # For test purposes, always write to a local file
        if os.getenv("TESTING", "false").lower() == "true":
            test_file = "/tmp/corgi_metrics_test.prom"
            write_to_textfile(test_file, REGISTRY)
            logger.debug(f"Metrics written to test file: {test_file}")

        return True
    except Exception as e:
        logger.error(f"Error manually flushing metrics: {e}")
        return False


def track_cache_hit(cache_type, endpoint):
    """
    Track a cache hit event.

    Args:
        cache_type: Type of cache (e.g., 'redis', 'memory')
        endpoint: API endpoint that was cached
    """
    CACHE_HIT_TOTAL.labels(cache_type=cache_type, endpoint=endpoint).inc()


def track_cache_miss(cache_type, endpoint):
    """
    Track a cache miss event.

    Args:
        cache_type: Type of cache (e.g., 'redis', 'memory')
        endpoint: API endpoint that missed cache
    """
    CACHE_MISS_TOTAL.labels(cache_type=cache_type, endpoint=endpoint).inc()


def track_cache_error(cache_type, error_type):
    """
    Track a cache error event.

    Args:
        cache_type: Type of cache (e.g., 'redis', 'memory')
        error_type: Type of error (e.g., 'connection', 'timeout')
    """
    CACHE_ERROR_TOTAL.labels(cache_type=cache_type, error_type=error_type).inc()


def track_cache_eviction(cache_type, reason):
    """
    Track a cache eviction event.

    Args:
        cache_type: Type of cache (e.g., 'redis', 'memory')
        reason: Reason for eviction (e.g., 'ttl_expired', 'memory_pressure')
    """
    CACHE_EVICTIONS_TOTAL.labels(cache_type=cache_type, reason=reason).inc()


def get_cache_hit_rate(cache_type, endpoint):
    """
    Calculate cache hit rate for a specific cache type and endpoint.

    Args:
        cache_type: Type of cache
        endpoint: API endpoint

    Returns:
        float: Hit rate as a percentage (0-100)
    """
    try:
        hits = CACHE_HIT_TOTAL.labels(cache_type=cache_type, endpoint=endpoint)._value._value
        misses = CACHE_MISS_TOTAL.labels(cache_type=cache_type, endpoint=endpoint)._value._value
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100
    except Exception as e:
        logger.error(f"Error calculating cache hit rate: {e}")
        return 0.0


def track_cache_operation_time(operation: str, cache_type: str, duration: float):
    """
    Track the time taken for a cache operation.

    Args:
        operation: Type of operation (e.g., 'get', 'set', 'delete')
        cache_type: Type of cache (e.g., 'redis', 'memory')
        duration: Duration in seconds
    """
    CACHE_OPERATION_SECONDS.labels(operation=operation, cache_type=cache_type).observe(duration)


def track_cache_ttl(cache_type: str, ttl_seconds: int):
    """
    Track cache TTL values for monitoring cache expiration patterns.

    Args:
        cache_type: Type of cache (e.g., 'redis', 'memory')
        ttl_seconds: TTL value in seconds
    """
    # For now, we'll just log this - could add a histogram if needed
    logger.debug(f"Cache TTL set: {cache_type} = {ttl_seconds}s")


def track_cache_size(cache_type: str, size_bytes: int):
    """
    Track cache size for monitoring memory usage.

    Args:
        cache_type: Type of cache (e.g., 'redis', 'memory')
        size_bytes: Size in bytes
    """
    # For now, we'll just log this - could add a gauge if needed
    logger.debug(f"Cache size: {cache_type} = {size_bytes} bytes")
