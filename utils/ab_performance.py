"""
A/B Testing Performance Monitoring Module

This module provides performance tracking capabilities for A/B testing,
measuring algorithm variant performance characteristics like latency,
resource usage, and throughput.

TODO #28i: Implement performance monitoring during A/B tests
"""

import time
import psutil
import logging
import threading
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from decimal import Decimal
import json
import statistics

from db.connection import get_db_connection, get_cursor
import utils.metrics as prometheus_metrics

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

class PerformanceTracker:
    """
    Thread-safe performance tracking for A/B testing experiments.
    
    Tracks metrics like latency, memory usage, throughput, and resource utilization
    per experiment variant, providing both real-time monitoring and historical analysis.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
        self._active_requests = {}  # Track ongoing performance measurements
        self._metric_buffers = defaultdict(lambda: deque(maxlen=1000))  # In-memory buffer for real-time metrics
        
    @contextmanager
    def track_experiment_performance(self, experiment_id: int, variant_id: int, 
                                   user_id: str, request_id: str = None,
                                   operation_type: str = "recommendation_generation"):
        """
        Context manager for tracking performance of an A/B test operation.
        
        Args:
            experiment_id: ID of the A/B test experiment
            variant_id: ID of the specific variant being tested
            user_id: User for whom the operation is being performed
            request_id: Optional request identifier for correlation
            operation_type: Type of operation being measured
            
        Yields:
            PerformanceContext: Context object for additional metric collection
        """
        context = PerformanceContext(
            experiment_id=experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            request_id=request_id,
            operation_type=operation_type
        )
        
        # Record start metrics
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            # Track active request
            with self._lock:
                self._active_requests[request_id or id(context)] = context
                
            context._start_time = start_time
            context._start_memory = start_memory
            
            yield context
            
        except Exception as e:
            context.record_error(str(e))
            raise
            
        finally:
            # Calculate final metrics
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            total_latency = (end_time - start_time) * 1000  # Convert to milliseconds
            memory_delta = end_memory - start_memory if end_memory and start_memory else None
            
            # Update context with final measurements
            context.latency_ms = total_latency
            context.memory_delta_mb = memory_delta
            
            # Record the performance event
            self._record_performance_event(context)
            
            # Update Prometheus metrics
            self._update_prometheus_metrics(context)
            
            # Remove from active requests
            with self._lock:
                self._active_requests.pop(request_id or id(context), None)
    
    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert bytes to MB
        except Exception:
            return None
    
    def _record_performance_event(self, context: 'PerformanceContext'):
        """Record a performance event to the database."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        INSERT INTO ab_performance_events 
                        (experiment_id, variant_id, user_id, request_id, event_type,
                         latency_ms, memory_usage_mb, items_processed, cache_hit_rate,
                         error_occurred, event_data, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        context.experiment_id,
                        context.variant_id,
                        context.user_id,
                        context.request_id,
                        context.operation_type,
                        context.latency_ms,
                        context.memory_delta_mb,
                        context.items_processed,
                        context.cache_hit_rate,
                        context.has_error,
                        json.dumps(context.get_event_data()) if context.get_event_data() else None
                    ))
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Error recording performance event: {e}")
    
    def _update_prometheus_metrics(self, context: 'PerformanceContext'):
        """Update Prometheus metrics with performance data."""
        try:
            # Latency histogram
            prometheus_metrics.ab_test_latency_histogram.labels(
                experiment_id=context.experiment_id,
                variant_id=context.variant_id,
                operation_type=context.operation_type
            ).observe(context.latency_ms / 1000)  # Prometheus expects seconds
            
            # Memory usage gauge
            if context.memory_delta_mb is not None:
                prometheus_metrics.ab_test_memory_usage.labels(
                    experiment_id=context.experiment_id,
                    variant_id=context.variant_id
                ).set(context.memory_delta_mb)
                
            # Items processed counter
            if context.items_processed:
                prometheus_metrics.ab_test_items_processed.labels(
                    experiment_id=context.experiment_id,
                    variant_id=context.variant_id
                ).inc(context.items_processed)
                
            # Cache hit rate gauge
            if context.cache_hit_rate is not None:
                prometheus_metrics.ab_test_cache_hit_rate.labels(
                    experiment_id=context.experiment_id,
                    variant_id=context.variant_id
                ).set(context.cache_hit_rate)
                
            # Error counter
            if context.has_error:
                prometheus_metrics.ab_test_errors_total.labels(
                    experiment_id=context.experiment_id,
                    variant_id=context.variant_id,
                    error_type=context.error_type or "unknown"
                ).inc()
                
        except Exception as e:
            self.logger.error(f"Error updating Prometheus metrics: {e}")
    
    def get_real_time_performance(self, experiment_id: int, 
                                time_window_minutes: int = 5) -> Dict[str, Any]:
        """
        Get real-time performance metrics for an experiment.
        
        Args:
            experiment_id: Experiment to get metrics for
            time_window_minutes: Time window for metrics calculation
            
        Returns:
            Dictionary containing performance metrics per variant
        """
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT 
                            variant_id,
                            COUNT(*) as request_count,
                            AVG(latency_ms) as avg_latency,
                            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) as p50_latency,
                            PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY latency_ms) as p90_latency,
                            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99_latency,
                            AVG(memory_usage_mb) as avg_memory,
                            SUM(items_processed) as total_items,
                            AVG(cache_hit_rate) as avg_cache_hit_rate,
                            COUNT(CASE WHEN error_occurred THEN 1 END) as error_count
                        FROM ab_performance_events
                        WHERE experiment_id = %s 
                        AND timestamp >= NOW() - INTERVAL '%s minutes'
                        GROUP BY variant_id
                        ORDER BY variant_id
                    """, (experiment_id, time_window_minutes))
                    
                    results = {}
                    for row in cursor.fetchall():
                        variant_id = row[0]
                        results[variant_id] = {
                            'request_count': row[1],
                            'avg_latency_ms': float(row[2]) if row[2] else 0,
                            'p50_latency_ms': float(row[3]) if row[3] else 0,
                            'p90_latency_ms': float(row[4]) if row[4] else 0,
                            'p99_latency_ms': float(row[5]) if row[5] else 0,
                            'avg_memory_mb': float(row[6]) if row[6] else 0,
                            'total_items_processed': row[7] or 0,
                            'avg_cache_hit_rate': float(row[8]) if row[8] else 0,
                            'error_count': row[9] or 0,
                            'error_rate': (row[9] or 0) / max(row[1], 1),
                            'throughput_per_second': row[1] / (time_window_minutes * 60) if row[1] else 0
                        }
                    
                    return {
                        'experiment_id': experiment_id,
                        'time_window_minutes': time_window_minutes,
                        'timestamp': datetime.now().isoformat(),
                        'variants': results
                    }
                    
        except Exception as e:
            self.logger.error(f"Error getting real-time performance metrics: {e}")
            return {}
    
    def compute_performance_comparison(self, experiment_id: int, 
                                     time_period_hours: int = 24) -> Dict[str, Any]:
        """
        Compute statistical performance comparison between variants.
        
        Args:
            experiment_id: Experiment to analyze
            time_period_hours: Time period for analysis
            
        Returns:
            Statistical comparison results
        """
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Get raw performance data for statistical analysis
                    cursor.execute("""
                        SELECT variant_id, latency_ms, memory_usage_mb, error_occurred
                        FROM ab_performance_events
                        WHERE experiment_id = %s 
                        AND timestamp >= NOW() - INTERVAL '%s hours'
                        AND latency_ms IS NOT NULL
                        ORDER BY variant_id, timestamp
                    """, (experiment_id, time_period_hours))
                    
                    # Group data by variant
                    variant_data = defaultdict(lambda: {
                        'latencies': [],
                        'memory_usage': [],
                        'error_count': 0,
                        'total_requests': 0
                    })
                    
                    for row in cursor.fetchall():
                        variant_id, latency, memory, error = row
                        variant_data[variant_id]['latencies'].append(latency)
                        if memory:
                            variant_data[variant_id]['memory_usage'].append(memory)
                        if error:
                            variant_data[variant_id]['error_count'] += 1
                        variant_data[variant_id]['total_requests'] += 1
                    
                    # Compute statistical comparison
                    comparison_result = self._compute_statistical_comparison(variant_data)
                    comparison_result.update({
                        'experiment_id': experiment_id,
                        'time_period_hours': time_period_hours,
                        'analysis_timestamp': datetime.now().isoformat()
                    })
                    
                    # Store comparison results
                    self._store_performance_comparison(experiment_id, comparison_result, time_period_hours)
                    
                    return comparison_result
                    
        except Exception as e:
            self.logger.error(f"Error computing performance comparison: {e}")
            return {}
    
    def _compute_statistical_comparison(self, variant_data: Dict) -> Dict[str, Any]:
        """Compute statistical comparison between variants."""
        results = {
            'variants': {},
            'performance_ranking': [],
            'significant_differences': []
        }
        
        for variant_id, data in variant_data.items():
            if data['latencies']:
                results['variants'][variant_id] = {
                    'avg_latency_ms': statistics.mean(data['latencies']),
                    'median_latency_ms': statistics.median(data['latencies']),
                    'p95_latency_ms': self._percentile(data['latencies'], 0.95),
                    'p99_latency_ms': self._percentile(data['latencies'], 0.99),
                    'latency_std_dev': statistics.stdev(data['latencies']) if len(data['latencies']) > 1 else 0,
                    'avg_memory_mb': statistics.mean(data['memory_usage']) if data['memory_usage'] else 0,
                    'error_rate': data['error_count'] / max(data['total_requests'], 1),
                    'sample_size': len(data['latencies'])
                }
        
        # Rank variants by average latency (lower is better)
        ranked_variants = sorted(
            results['variants'].items(),
            key=lambda x: x[1]['avg_latency_ms']
        )
        results['performance_ranking'] = [{'variant_id': v[0], **v[1]} for v in ranked_variants]
        
        return results
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(percentile * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _store_performance_comparison(self, experiment_id: int, comparison_data: Dict, 
                                    time_period_hours: int):
        """Store performance comparison results in database."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Determine performance winner (lowest average latency)
                    performance_winner = None
                    if comparison_data.get('performance_ranking'):
                        performance_winner = comparison_data['performance_ranking'][0]['variant_id']
                    
                    cursor.execute("""
                        INSERT INTO ab_performance_comparisons 
                        (experiment_id, metric_name, time_period_hours, comparison_data, 
                         performance_winner, last_updated)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (experiment_id, metric_name, time_period_hours)
                        DO UPDATE SET 
                            comparison_data = EXCLUDED.comparison_data,
                            performance_winner = EXCLUDED.performance_winner,
                            last_updated = NOW()
                    """, (
                        experiment_id,
                        'overall_performance',
                        time_period_hours,
                        json.dumps(comparison_data, cls=DecimalEncoder),
                        performance_winner
                    ))
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Error storing performance comparison: {e}")

    def _record_performance_event_direct(self, experiment_id: int, variant_id: int, 
                                        user_id: str, performance_metrics: Dict):
        """
        Directly record performance metrics from external sources.
        
        Args:
            experiment_id: A/B test experiment ID
            variant_id: Variant ID
            user_id: User ID
            performance_metrics: Dictionary containing performance data
        """
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        INSERT INTO ab_performance_events 
                        (experiment_id, variant_id, user_id, request_id, event_type,
                         latency_ms, memory_usage_mb, items_processed, cache_hit_rate,
                         error_occurred, event_data, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        experiment_id,
                        variant_id,
                        user_id,
                        performance_metrics.get('request_id'),
                        performance_metrics.get('operation_type', 'recommendation_generation'),
                        performance_metrics.get('latency_ms'),
                        performance_metrics.get('memory_usage_mb'),
                        performance_metrics.get('items_processed'),
                        performance_metrics.get('cache_hit_rate'),
                        performance_metrics.get('error_occurred', False),
                        json.dumps(performance_metrics.get('additional_data', {}))
                    ))
                    conn.commit()
                    
                    # Update Prometheus metrics
                    if performance_metrics.get('latency_ms'):
                        prometheus_metrics.ab_test_latency_histogram.labels(
                            experiment_id=experiment_id,
                            variant_id=variant_id,
                            operation_type=performance_metrics.get('operation_type', 'recommendation_generation')
                        ).observe(performance_metrics['latency_ms'] / 1000)
                    
                    if performance_metrics.get('memory_usage_mb'):
                        prometheus_metrics.ab_test_memory_usage.labels(
                            experiment_id=experiment_id,
                            variant_id=variant_id
                        ).set(performance_metrics['memory_usage_mb'])
                    
                    if performance_metrics.get('items_processed'):
                        prometheus_metrics.ab_test_items_processed.labels(
                            experiment_id=experiment_id,
                            variant_id=variant_id
                        ).inc(performance_metrics['items_processed'])
                        
        except Exception as e:
            self.logger.error(f"Error recording performance event directly: {e}")


class PerformanceContext:
    """Context object for tracking performance metrics during an operation."""
    
    def __init__(self, experiment_id: int, variant_id: int, user_id: str, 
                 request_id: str = None, operation_type: str = "recommendation_generation"):
        self.experiment_id = experiment_id
        self.variant_id = variant_id
        self.user_id = user_id
        self.request_id = request_id
        self.operation_type = operation_type
        
        # Performance metrics
        self.latency_ms = None
        self.memory_delta_mb = None
        self.items_processed = None
        self.cache_hit_rate = None
        self.has_error = False
        self.error_type = None
        self.error_message = None
        
        # Additional context data
        self._custom_metrics = {}
        self._start_time = None
        self._start_memory = None
    
    def record_items_processed(self, count: int):
        """Record the number of items processed during the operation."""
        self.items_processed = count
    
    def record_cache_metrics(self, hit_rate: float):
        """Record cache hit rate for the operation."""
        self.cache_hit_rate = hit_rate
    
    def record_custom_metric(self, name: str, value: Any):
        """Record a custom metric for this operation."""
        self._custom_metrics[name] = value
    
    def record_error(self, error_message: str, error_type: str = None):
        """Record an error that occurred during the operation."""
        self.has_error = True
        self.error_message = error_message
        self.error_type = error_type or "unknown"
    
    def get_event_data(self) -> Dict[str, Any]:
        """Get all event data for database storage."""
        data = {
            'custom_metrics': self._custom_metrics,
            'operation_type': self.operation_type
        }
        
        if self.has_error:
            data['error'] = {
                'type': self.error_type,
                'message': self.error_message
            }
            
        return data


# Global performance tracker instance
performance_tracker = PerformanceTracker() 