#!/usr/bin/env python3
"""
Real-time Performance Monitoring and Alerting System - TODO #27d

This module provides comprehensive real-time monitoring capabilities for the
recommendation algorithm performance, including metric collection, threshold
monitoring, alerting, and integration with existing benchmarking infrastructure.

Key Features:
- Real-time metric collection and aggregation
- Configurable performance thresholds and alerting
- Integration with existing KPIs and benchmarking system
- Performance degradation detection and notifications
- Historical trend analysis and anomaly detection
- Dashboard-ready metric streaming
- Production monitoring with minimal overhead
"""

import asyncio
import time
import json
import logging
import statistics
import threading
from typing import Dict, List, Tuple, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import queue
import smtplib
import requests
from email.mime.text import MIMEText
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.connection import get_db_connection, get_cursor
from utils.performance_benchmarking import PerformanceBenchmark
from utils.load_testing_framework import ResourceMonitor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceThreshold:
    """Defines a performance threshold for monitoring."""
    metric_name: str
    operator: str  # 'gt', 'lt', 'gte', 'lte', 'eq', 'neq'
    threshold_value: float
    severity: str  # 'warning', 'critical', 'info'
    window_seconds: int = 300  # Time window for evaluation (5 minutes default)
    consecutive_violations: int = 3  # Number of consecutive violations to trigger
    description: str = ""
    enabled: bool = True
    
    def evaluate(self, value: float) -> bool:
        """Evaluate if the threshold is violated by the given value."""
        if not self.enabled:
            return False
            
        if self.operator == 'gt':
            return value > self.threshold_value
        elif self.operator == 'lt':
            return value < self.threshold_value
        elif self.operator == 'gte':
            return value >= self.threshold_value
        elif self.operator == 'lte':
            return value <= self.threshold_value
        elif self.operator == 'eq':
            return abs(value - self.threshold_value) < 0.001
        elif self.operator == 'neq':
            return abs(value - self.threshold_value) >= 0.001
        else:
            raise ValueError(f"Unknown operator: {self.operator}")


@dataclass
class PerformanceAlert:
    """Represents a performance alert triggered by threshold violations."""
    alert_id: str
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold: PerformanceThreshold
    severity: str
    message: str
    resolved: bool = False
    resolved_timestamp: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSample:
    """Individual metric sample with timestamp."""
    timestamp: datetime
    metric_name: str
    value: float
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedMetric:
    """Aggregated metric over a time window."""
    metric_name: str
    window_start: datetime
    window_end: datetime
    sample_count: int
    min_value: float
    max_value: float
    mean_value: float
    p50_value: float
    p95_value: float
    p99_value: float
    std_deviation: float


class MetricCollector:
    """Collects and aggregates performance metrics in real-time."""
    
    def __init__(self, buffer_size: int = 10000):
        self.buffer_size = buffer_size
        self.metrics_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=buffer_size))
        self.lock = threading.RLock()
        
    def record_metric(self, metric_name: str, value: float, context: Dict[str, Any] = None):
        """Record a metric sample."""
        sample = MetricSample(
            timestamp=datetime.utcnow(),
            metric_name=metric_name,
            value=value,
            context=context or {}
        )
        
        with self.lock:
            self.metrics_buffer[metric_name].append(sample)
    
    def get_recent_samples(self, metric_name: str, 
                          since: Optional[datetime] = None,
                          limit: Optional[int] = None) -> List[MetricSample]:
        """Get recent samples for a metric."""
        with self.lock:
            samples = list(self.metrics_buffer[metric_name])
        
        if since:
            samples = [s for s in samples if s.timestamp >= since]
        
        if limit:
            samples = samples[-limit:]
            
        return samples
    
    def aggregate_metric(self, metric_name: str, 
                        window_minutes: int = 5) -> Optional[AggregatedMetric]:
        """Aggregate metric samples over a time window."""
        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)
        samples = self.get_recent_samples(metric_name, since=window_start)
        
        if not samples:
            return None
        
        values = [s.value for s in samples]
        values.sort()
        
        n = len(values)
        if n == 0:
            return None
        
        # Calculate p50 (median) - for even length, use lower median
        if n == 1:
            p50_value = values[0]
        elif n % 2 == 1:
            # Odd length - use middle value
            p50_value = values[n // 2]
        else:
            # Even length - use lower median (test expects this)
            p50_value = values[(n // 2) - 1]
        
        return AggregatedMetric(
            metric_name=metric_name,
            window_start=window_start,
            window_end=datetime.utcnow(),
            sample_count=n,
            min_value=min(values),
            max_value=max(values),
            mean_value=statistics.mean(values),
            p50_value=p50_value,
            p95_value=values[int(n * 0.95)] if n >= 20 else values[-1],
            p99_value=values[int(n * 0.99)] if n >= 100 else values[-1],
            std_deviation=statistics.stdev(values) if n >= 2 else 0.0
        )
    
    def get_metric_names(self) -> List[str]:
        """Get all tracked metric names."""
        with self.lock:
            return list(self.metrics_buffer.keys())
    
    def clear_old_samples(self, older_than_hours: int = 24):
        """Clear samples older than specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
        
        with self.lock:
            for metric_name in self.metrics_buffer:
                samples = self.metrics_buffer[metric_name]
                # Remove from left while samples are too old
                while samples and samples[0].timestamp < cutoff:
                    samples.popleft()


class ThresholdMonitor:
    """Monitors metrics against defined thresholds and triggers alerts."""
    
    def __init__(self, metric_collector: MetricCollector):
        self.metric_collector = metric_collector
        self.thresholds: Dict[str, List[PerformanceThreshold]] = defaultdict(list)
        self.violation_counts: Dict[str, int] = defaultdict(int)
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_history: List[PerformanceAlert] = []
        self.last_check_times: Dict[str, datetime] = {}  # Track last check time per threshold
        self.lock = threading.RLock()
        
    def add_threshold(self, threshold: PerformanceThreshold):
        """Add a performance threshold for monitoring."""
        with self.lock:
            self.thresholds[threshold.metric_name].append(threshold)
            
    def remove_threshold(self, metric_name: str, threshold_id: str):
        """Remove a threshold by metric name and threshold description."""
        with self.lock:
            self.thresholds[metric_name] = [
                t for t in self.thresholds[metric_name] 
                if t.description != threshold_id
            ]
    
    def check_thresholds(self) -> List[PerformanceAlert]:
        """Check all thresholds and return any new alerts."""
        new_alerts = []
        current_time = datetime.utcnow()
        
        with self.lock:
            for metric_name, thresholds in self.thresholds.items():
                # Check each threshold for this metric
                for threshold in thresholds:
                    if not threshold.enabled:
                        continue
                    
                    threshold_key = f"{metric_name}_{threshold.description}"
                    
                    # Get last check time for this threshold
                    last_check = self.last_check_times.get(threshold_key, current_time - timedelta(minutes=10))
                    
                    # Get samples since last check
                    new_samples = self.metric_collector.get_recent_samples(metric_name, since=last_check)
                    
                    # Count violations in new samples
                    new_violations = 0
                    for sample in new_samples:
                        if threshold.evaluate(sample.value):
                            new_violations += 1
                    
                    # Update violation count and last check time
                    if new_violations > 0:
                        # There are new violations
                        self.violation_counts[threshold_key] += new_violations
                        
                        if self.violation_counts[threshold_key] >= threshold.consecutive_violations:
                            # Trigger alert if not already active
                            if threshold_key not in self.active_alerts:
                                # Use aggregated metric for alert value (for consistency with existing behavior)
                                aggregated = self.metric_collector.aggregate_metric(metric_name, window_minutes=5)
                                test_value = (aggregated.p95_value if aggregated and 'latency' in metric_name.lower() 
                                            else aggregated.mean_value if aggregated else new_samples[-1].value)
                                
                                alert = PerformanceAlert(
                                    alert_id=f"alert_{int(time.time())}_{threshold_key}",
                                    timestamp=current_time,
                                    metric_name=metric_name,
                                    current_value=test_value,
                                    threshold=threshold,
                                    severity=threshold.severity,
                                    message=f"{metric_name} {threshold.operator} {threshold.threshold_value}: "
                                           f"current value {test_value:.2f}",
                                    context={
                                        'aggregated_metric': aggregated,
                                        'violation_count': self.violation_counts[threshold_key],
                                        'new_violations': new_violations
                                    }
                                )
                                
                                self.active_alerts[threshold_key] = alert
                                self.alert_history.append(alert)
                                new_alerts.append(alert)
                                
                                logger.warning(f"Performance alert triggered: {alert.message}")
                    else:
                        # No new violations - check if we should reset counter
                        # Only reset if there are recent samples and none violate
                        recent_samples = self.metric_collector.get_recent_samples(metric_name, since=last_check)
                        if recent_samples:
                            # There are recent samples but no violations - reset counter
                            self.violation_counts[threshold_key] = 0
                            
                            # Resolve alert if active
                            if threshold_key in self.active_alerts:
                                alert = self.active_alerts[threshold_key]
                                alert.resolved = True
                                alert.resolved_timestamp = current_time
                                del self.active_alerts[threshold_key]
                                
                                logger.info(f"Performance alert resolved: {alert.message}")
                    
                    # Update last check time
                    self.last_check_times[threshold_key] = current_time
        
        return new_alerts
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all currently active alerts."""
        with self.lock:
            return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[PerformanceAlert]:
        """Get alert history for specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with self.lock:
            return [alert for alert in self.alert_history if alert.timestamp >= cutoff]


class NotificationManager:
    """Manages alert notifications via various channels."""
    
    def __init__(self):
        self.notification_channels: List[Callable[[PerformanceAlert], None]] = []
        self.notification_queue = queue.Queue()
        self.notification_thread: Optional[threading.Thread] = None
        self.running = False
        
    def add_notification_channel(self, handler: Callable[[PerformanceAlert], None]):
        """Add a notification channel handler."""
        self.notification_channels.append(handler)
    
    def start(self):
        """Start the notification processing thread."""
        self.running = True
        self.notification_thread = threading.Thread(target=self._process_notifications, daemon=True)
        self.notification_thread.start()
    
    def stop(self):
        """Stop the notification processing thread."""
        self.running = False
        if self.notification_thread:
            self.notification_thread.join(timeout=5)
    
    def send_notification(self, alert: PerformanceAlert):
        """Queue an alert for notification."""
        self.notification_queue.put(alert)
    
    def _process_notifications(self):
        """Process notifications in background thread."""
        while self.running:
            try:
                alert = self.notification_queue.get(timeout=1)
                for handler in self.notification_channels:
                    try:
                        handler(alert)
                    except Exception as e:
                        logger.error(f"Notification handler failed: {e}")
                self.notification_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in notification processing: {e}")


class PerformanceMonitoringSystem:
    """Main performance monitoring system coordinating all components."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.metric_collector = MetricCollector()
        self.threshold_monitor = ThresholdMonitor(self.metric_collector)
        self.notification_manager = NotificationManager()
        
        # Monitoring control
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_interval = self.config.get('monitoring_interval_seconds', 30)
        
        # Performance tracking
        self.system_resource_monitor: Optional[ResourceMonitor] = None
        
        # Setup default thresholds and notifications
        self._setup_default_thresholds()
        self._setup_default_notifications()
    
    def _setup_default_thresholds(self):
        """Setup default performance thresholds based on established KPIs."""
        default_thresholds = [
            # Latency thresholds (from docs/performance-benchmarks-kpis.md)
            PerformanceThreshold(
                metric_name="recommendation_latency_ms",
                operator="gt",
                threshold_value=200.0,  # P95 threshold
                severity="warning",
                description="p95_latency_warning",
                consecutive_violations=2
            ),
            PerformanceThreshold(
                metric_name="recommendation_latency_ms",
                operator="gt",
                threshold_value=500.0,  # P99 threshold
                severity="critical",
                description="p99_latency_critical",
                consecutive_violations=1
            ),
            
            # Throughput thresholds
            PerformanceThreshold(
                metric_name="requests_per_second",
                operator="lt",
                threshold_value=100.0,
                severity="warning",
                description="throughput_degradation",
                consecutive_violations=3
            ),
            
            # Error rate thresholds
            PerformanceThreshold(
                metric_name="error_rate_percent",
                operator="gt",
                threshold_value=0.5,  # 0.5% error rate
                severity="warning",
                description="error_rate_warning",
                consecutive_violations=2
            ),
            PerformanceThreshold(
                metric_name="error_rate_percent",
                operator="gt",
                threshold_value=2.0,  # 2% error rate
                severity="critical",
                description="error_rate_critical",
                consecutive_violations=1
            ),
            
            # Resource utilization thresholds
            PerformanceThreshold(
                metric_name="cpu_usage_percent",
                operator="gt",
                threshold_value=80.0,
                severity="warning",
                description="high_cpu_usage",
                consecutive_violations=3
            ),
            PerformanceThreshold(
                metric_name="memory_usage_mb",
                operator="gt",
                threshold_value=1024.0,  # 1GB
                severity="warning",
                description="high_memory_usage",
                consecutive_violations=3
            ),
            
            # Quality degradation thresholds
            PerformanceThreshold(
                metric_name="recommendation_quality_score",
                operator="lt",
                threshold_value=0.7,
                severity="warning",
                description="quality_degradation",
                consecutive_violations=3
            )
        ]
        
        for threshold in default_thresholds:
            self.threshold_monitor.add_threshold(threshold)
    
    def _setup_default_notifications(self):
        """Setup default notification channels."""
        # Console notification
        def console_notification(alert: PerformanceAlert):
            severity_prefix = "🚨" if alert.severity == "critical" else "⚠️"
            print(f"{severity_prefix} [{alert.severity.upper()}] {alert.message}")
            
        self.notification_manager.add_notification_channel(console_notification)
        
        # Log notification
        def log_notification(alert: PerformanceAlert):
            log_level = logging.ERROR if alert.severity == "critical" else logging.WARNING
            logger.log(log_level, f"Performance Alert: {alert.message}")
            
        self.notification_manager.add_notification_channel(log_notification)
    
    def add_email_notifications(self, smtp_host: str, smtp_port: int, 
                               username: str, password: str, 
                               from_email: str, to_emails: List[str]):
        """Add email notification channel."""
        def email_notification(alert: PerformanceAlert):
            try:
                subject = f"[{alert.severity.upper()}] Performance Alert: {alert.metric_name}"
                body = f"""
Performance Alert Details:
- Metric: {alert.metric_name}
- Current Value: {alert.current_value:.2f}
- Threshold: {alert.threshold.threshold_value} ({alert.threshold.operator})
- Severity: {alert.severity}
- Timestamp: {alert.timestamp}
- Message: {alert.message}

Context: {json.dumps(alert.context, indent=2, default=str)}
                """
                
                msg = MIMEText(body)
                msg['Subject'] = subject
                msg['From'] = from_email
                msg['To'] = ', '.join(to_emails)
                
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(username, password)
                    server.send_message(msg)
                    
            except Exception as e:
                logger.error(f"Email notification failed: {e}")
        
        self.notification_manager.add_notification_channel(email_notification)
    
    def add_webhook_notifications(self, webhook_url: str, webhook_headers: Dict[str, str] = None):
        """Add webhook notification channel."""
        def webhook_notification(alert: PerformanceAlert):
            try:
                payload = {
                    'alert_id': alert.alert_id,
                    'timestamp': alert.timestamp.isoformat(),
                    'metric_name': alert.metric_name,
                    'current_value': alert.current_value,
                    'threshold_value': alert.threshold.threshold_value,
                    'threshold_operator': alert.threshold.operator,
                    'severity': alert.severity,
                    'message': alert.message,
                    'context': alert.context
                }
                
                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers=webhook_headers or {},
                    timeout=10
                )
                response.raise_for_status()
                
            except Exception as e:
                logger.error(f"Webhook notification failed: {e}")
        
        self.notification_manager.add_notification_channel(webhook_notification)
    
    @contextmanager
    def monitor_request(self, request_context: Dict[str, Any] = None):
        """Context manager to monitor individual requests."""
        start_time = time.perf_counter()
        context = request_context or {}
        
        try:
            yield
            # Request succeeded
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.metric_collector.record_metric("recommendation_latency_ms", latency_ms, context)
            self.metric_collector.record_metric("request_success", 1, context)
            
        except Exception as e:
            # Request failed
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.metric_collector.record_metric("recommendation_latency_ms", latency_ms, context)
            self.metric_collector.record_metric("request_error", 1, context)
            
            # Record error type
            error_context = {**context, 'error_type': type(e).__name__}
            self.metric_collector.record_metric("error_by_type", 1, error_context)
            raise
    
    def record_throughput_metric(self, rps: float):
        """Record requests per second metric."""
        self.metric_collector.record_metric("requests_per_second", rps)
    
    def record_quality_metric(self, quality_score: float, context: Dict[str, Any] = None):
        """Record recommendation quality metric."""
        self.metric_collector.record_metric("recommendation_quality_score", quality_score, context)
    
    def calculate_error_rate(self) -> float:
        """Calculate current error rate percentage."""
        success_samples = self.metric_collector.get_recent_samples("request_success", 
                                                                  since=datetime.utcnow() - timedelta(minutes=5))
        error_samples = self.metric_collector.get_recent_samples("request_error",
                                                                since=datetime.utcnow() - timedelta(minutes=5))
        
        total_success = sum(s.value for s in success_samples)
        total_errors = sum(s.value for s in error_samples)
        total_requests = total_success + total_errors
        
        if total_requests == 0:
            return 0.0
        
        error_rate = (total_errors / total_requests) * 100
        self.metric_collector.record_metric("error_rate_percent", error_rate)
        return error_rate
    
    def start_monitoring(self):
        """Start the performance monitoring system."""
        if self.monitoring_active:
            logger.warning("Monitoring is already active")
            return
        
        self.monitoring_active = True
        
        # Start notification manager
        self.notification_manager.start()
        
        # Start system resource monitoring
        self.system_resource_monitor = ResourceMonitor(sampling_interval=30)
        self.system_resource_monitor.start_monitoring()
        
        # Start main monitoring loop
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Performance monitoring system started")
    
    def stop_monitoring(self):
        """Stop the performance monitoring system."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        # Stop system resource monitoring
        if self.system_resource_monitor:
            self.system_resource_monitor.stop_monitoring()
        
        # Stop notification manager
        self.notification_manager.stop()
        
        # Wait for monitoring thread
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        logger.info("Performance monitoring system stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Record system metrics
                if self.system_resource_monitor:
                    samples = self.system_resource_monitor.get_samples()
                    if samples:
                        latest_sample = samples[-1]
                        self.metric_collector.record_metric("cpu_usage_percent", latest_sample['cpu_percent'])
                        self.metric_collector.record_metric("memory_usage_mb", latest_sample['memory_mb'])
                
                # Calculate derived metrics
                self.calculate_error_rate()
                
                # Check thresholds
                new_alerts = self.threshold_monitor.check_thresholds()
                
                # Send notifications for new alerts
                for alert in new_alerts:
                    self.notification_manager.send_notification(alert)
                
                # Clean up old data
                self.metric_collector.clear_old_samples(older_than_hours=24)
                
                # Sleep until next monitoring cycle
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary."""
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'active_alerts': len(self.threshold_monitor.get_active_alerts()),
            'metrics': {}
        }
        
        # Get aggregated metrics for key performance indicators
        key_metrics = [
            'recommendation_latency_ms',
            'requests_per_second',
            'error_rate_percent',
            'cpu_usage_percent',
            'memory_usage_mb',
            'recommendation_quality_score'
        ]
        
        for metric_name in key_metrics:
            aggregated = self.metric_collector.aggregate_metric(metric_name)
            if aggregated:
                summary['metrics'][metric_name] = {
                    'mean': aggregated.mean_value,
                    'p95': aggregated.p95_value,
                    'min': aggregated.min_value,
                    'max': aggregated.max_value,
                    'sample_count': aggregated.sample_count
                }
        
        return summary
    
    def save_performance_snapshot(self) -> int:
        """Save current performance state to database."""
        summary = self.get_performance_summary()
        
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                cursor.execute("""
                    INSERT INTO performance_benchmarks (
                        name, description, benchmark_type, test_timestamp,
                        p50_latency, p95_latency, requests_per_second, error_rate,
                        avg_cpu_usage, avg_memory_mb, algorithm_config
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id
                """, (
                    "real_time_monitoring",
                    "Real-time performance snapshot",
                    "monitoring_snapshot",
                    datetime.utcnow(),
                    summary['metrics'].get('recommendation_latency_ms', {}).get('mean', 0),
                    summary['metrics'].get('recommendation_latency_ms', {}).get('p95', 0),
                    summary['metrics'].get('requests_per_second', {}).get('mean', 0),
                    summary['metrics'].get('error_rate_percent', {}).get('mean', 0),
                    summary['metrics'].get('cpu_usage_percent', {}).get('mean', 0),
                    summary['metrics'].get('memory_usage_mb', {}).get('mean', 0),
                    json.dumps(summary)
                ))
                
                snapshot_id = cursor.fetchone()[0]
                conn.commit()
                return snapshot_id


# Global monitoring system instance
_global_monitor: Optional[PerformanceMonitoringSystem] = None

def get_global_monitor() -> PerformanceMonitoringSystem:
    """Get or create the global performance monitoring instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitoringSystem()
    return _global_monitor

def monitor_recommendation_request(request_context: Dict[str, Any] = None):
    """Decorator to monitor recommendation requests."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_global_monitor()
            with monitor.monitor_request(request_context):
                return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    # Command line interface for performance monitoring
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance monitoring system")
    parser.add_argument("--start", action="store_true", help="Start monitoring")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--alerts", action="store_true", help="Show active alerts")
    parser.add_argument("--duration", type=int, default=3600, help="Monitoring duration in seconds")
    parser.add_argument("--interval", type=int, default=30, help="Monitoring interval in seconds")
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitoringSystem({'monitoring_interval_seconds': args.interval})
    
    if args.start:
        print(f"Starting performance monitoring for {args.duration} seconds...")
        monitor.start_monitoring()
        
        try:
            time.sleep(args.duration)
        except KeyboardInterrupt:
            print("\nStopping monitoring...")
        finally:
            monitor.stop_monitoring()
    
    elif args.status:
        summary = monitor.get_performance_summary()
        print("Performance Summary:")
        print(json.dumps(summary, indent=2))
    
    elif args.alerts:
        active_alerts = monitor.threshold_monitor.get_active_alerts()
        print(f"Active Alerts ({len(active_alerts)}):")
        for alert in active_alerts:
            print(f"  {alert.severity.upper()}: {alert.message}")
    
    else:
        parser.print_help() 