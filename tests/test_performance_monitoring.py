#!/usr/bin/env python3
"""
Test Suite for Performance Monitoring System - TODO #27d

This module provides comprehensive tests for the real-time performance monitoring
and alerting system, including metric collection, threshold evaluation, 
notification handling, and integration with existing infrastructure.
"""

import pytest
import time
import json
import threading
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.performance_monitoring import (
    PerformanceMonitoringSystem,
    MetricCollector,
    ThresholdMonitor,
    NotificationManager,
    PerformanceThreshold,
    PerformanceAlert,
    MetricSample,
    AggregatedMetric,
    get_global_monitor,
    monitor_recommendation_request
)


class TestPerformanceThreshold:
    """Test PerformanceThreshold dataclass and evaluation logic."""
    
    def test_threshold_creation(self):
        """Test threshold creation with all parameters."""
        threshold = PerformanceThreshold(
            metric_name="test_metric",
            operator="gt",
            threshold_value=100.0,
            severity="warning",
            window_seconds=300,
            consecutive_violations=3,
            description="test threshold",
            enabled=True
        )
        
        assert threshold.metric_name == "test_metric"
        assert threshold.operator == "gt"
        assert threshold.threshold_value == 100.0
        assert threshold.severity == "warning"
        assert threshold.window_seconds == 300
        assert threshold.consecutive_violations == 3
        assert threshold.description == "test threshold"
        assert threshold.enabled is True
    
    def test_threshold_evaluation_operators(self):
        """Test all threshold operator evaluations."""
        # Greater than
        gt_threshold = PerformanceThreshold("test", "gt", 50.0, "warning")
        assert gt_threshold.evaluate(60.0) is True
        assert gt_threshold.evaluate(40.0) is False
        assert gt_threshold.evaluate(50.0) is False
        
        # Less than
        lt_threshold = PerformanceThreshold("test", "lt", 50.0, "warning")
        assert lt_threshold.evaluate(40.0) is True
        assert lt_threshold.evaluate(60.0) is False
        assert lt_threshold.evaluate(50.0) is False
        
        # Greater than or equal
        gte_threshold = PerformanceThreshold("test", "gte", 50.0, "warning")
        assert gte_threshold.evaluate(60.0) is True
        assert gte_threshold.evaluate(50.0) is True
        assert gte_threshold.evaluate(40.0) is False
        
        # Less than or equal
        lte_threshold = PerformanceThreshold("test", "lte", 50.0, "warning")
        assert lte_threshold.evaluate(40.0) is True
        assert lte_threshold.evaluate(50.0) is True
        assert lte_threshold.evaluate(60.0) is False
        
        # Equal (with small tolerance)
        eq_threshold = PerformanceThreshold("test", "eq", 50.0, "warning")
        assert eq_threshold.evaluate(50.0) is True
        assert eq_threshold.evaluate(49.9999) is True
        assert eq_threshold.evaluate(51.0) is False
        
        # Not equal
        neq_threshold = PerformanceThreshold("test", "neq", 50.0, "warning")
        assert neq_threshold.evaluate(51.0) is True
        assert neq_threshold.evaluate(49.0) is True
        assert neq_threshold.evaluate(50.0) is False
    
    def test_threshold_disabled(self):
        """Test that disabled thresholds never trigger."""
        threshold = PerformanceThreshold("test", "gt", 50.0, "warning", enabled=False)
        assert threshold.evaluate(100.0) is False
        assert threshold.evaluate(0.0) is False
    
    def test_threshold_invalid_operator(self):
        """Test invalid operator raises error."""
        threshold = PerformanceThreshold("test", "invalid", 50.0, "warning")
        with pytest.raises(ValueError):
            threshold.evaluate(60.0)


class TestMetricCollector:
    """Test MetricCollector for real-time metric collection."""
    
    @pytest.fixture
    def collector(self):
        """Create MetricCollector for testing."""
        return MetricCollector(buffer_size=100)
    
    def test_metric_recording(self, collector):
        """Test basic metric recording functionality."""
        # Record some metrics
        collector.record_metric("test_metric", 100.0)
        collector.record_metric("test_metric", 150.0)
        collector.record_metric("another_metric", 200.0)
        
        # Verify metrics were recorded
        test_samples = collector.get_recent_samples("test_metric")
        assert len(test_samples) == 2
        assert test_samples[0].value == 100.0
        assert test_samples[1].value == 150.0
        assert all(sample.metric_name == "test_metric" for sample in test_samples)
        
        another_samples = collector.get_recent_samples("another_metric")
        assert len(another_samples) == 1
        assert another_samples[0].value == 200.0
    
    def test_metric_recording_with_context(self, collector):
        """Test metric recording with context information."""
        context = {"user_id": "test_user", "request_type": "recommendation"}
        collector.record_metric("latency_ms", 50.0, context)
        
        samples = collector.get_recent_samples("latency_ms")
        assert len(samples) == 1
        assert samples[0].context == context
    
    def test_get_recent_samples_with_time_filter(self, collector):
        """Test filtering samples by time."""
        # Record metrics with slight delays
        collector.record_metric("test_metric", 100.0)
        time.sleep(0.1)
        cutoff_time = datetime.utcnow()
        time.sleep(0.1)
        collector.record_metric("test_metric", 200.0)
        
        # Get all samples
        all_samples = collector.get_recent_samples("test_metric")
        assert len(all_samples) == 2
        
        # Get samples since cutoff
        recent_samples = collector.get_recent_samples("test_metric", since=cutoff_time)
        assert len(recent_samples) == 1
        assert recent_samples[0].value == 200.0
    
    def test_get_recent_samples_with_limit(self, collector):
        """Test limiting number of returned samples."""
        # Record many metrics
        for i in range(10):
            collector.record_metric("test_metric", float(i))
        
        # Get limited samples
        limited_samples = collector.get_recent_samples("test_metric", limit=5)
        assert len(limited_samples) == 5
        
        # Should get the most recent 5
        expected_values = [5.0, 6.0, 7.0, 8.0, 9.0]
        actual_values = [s.value for s in limited_samples]
        assert actual_values == expected_values
    
    def test_metric_aggregation(self, collector):
        """Test metric aggregation over time windows."""
        # Record a series of metrics
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        for value in values:
            collector.record_metric("test_metric", value)
        
        # Aggregate metrics
        aggregated = collector.aggregate_metric("test_metric", window_minutes=60)
        
        assert aggregated is not None
        assert aggregated.metric_name == "test_metric"
        assert aggregated.sample_count == 10
        assert aggregated.min_value == 10.0
        assert aggregated.max_value == 100.0
        assert aggregated.mean_value == 55.0
        assert aggregated.p50_value == 50.0  # Median
        assert aggregated.std_deviation > 0
    
    def test_metric_aggregation_empty(self, collector):
        """Test aggregation with no samples."""
        aggregated = collector.aggregate_metric("nonexistent_metric")
        assert aggregated is None
    
    def test_buffer_size_limit(self, collector):
        """Test that buffer respects size limits."""
        # Record more metrics than buffer size
        for i in range(150):  # Buffer size is 100
            collector.record_metric("test_metric", float(i))
        
        samples = collector.get_recent_samples("test_metric")
        assert len(samples) == 100  # Should be limited to buffer size
        
        # Should contain the most recent 100 values
        expected_values = list(range(50, 150))  # Values 50-149
        actual_values = [int(s.value) for s in samples]
        assert actual_values == expected_values
    
    def test_clear_old_samples(self, collector):
        """Test clearing old samples."""
        # Record metrics and manually set old timestamps
        collector.record_metric("test_metric", 100.0)
        collector.record_metric("test_metric", 200.0)
        
        # Manually age one sample
        old_time = datetime.utcnow() - timedelta(hours=25)
        collector.metrics_buffer["test_metric"][0].timestamp = old_time
        
        # Clear old samples
        collector.clear_old_samples(older_than_hours=24)
        
        # Should only have recent sample
        samples = collector.get_recent_samples("test_metric")
        assert len(samples) == 1
        assert samples[0].value == 200.0
    
    def test_get_metric_names(self, collector):
        """Test getting all tracked metric names."""
        collector.record_metric("metric_1", 100.0)
        collector.record_metric("metric_2", 200.0)
        collector.record_metric("metric_3", 300.0)
        
        metric_names = collector.get_metric_names()
        assert set(metric_names) == {"metric_1", "metric_2", "metric_3"}


class TestThresholdMonitor:
    """Test ThresholdMonitor for threshold evaluation and alerting."""
    
    @pytest.fixture
    def monitor_setup(self):
        """Create collector and monitor for testing."""
        collector = MetricCollector()
        monitor = ThresholdMonitor(collector)
        return collector, monitor
    
    def test_add_threshold(self, monitor_setup):
        """Test adding thresholds to monitor."""
        collector, monitor = monitor_setup
        
        threshold = PerformanceThreshold(
            metric_name="test_metric",
            operator="gt",
            threshold_value=100.0,
            severity="warning",
            description="test_threshold"
        )
        
        monitor.add_threshold(threshold)
        assert len(monitor.thresholds["test_metric"]) == 1
        assert monitor.thresholds["test_metric"][0] == threshold
    
    def test_remove_threshold(self, monitor_setup):
        """Test removing thresholds from monitor."""
        collector, monitor = monitor_setup
        
        threshold1 = PerformanceThreshold("test_metric", "gt", 100.0, "warning", description="threshold1")
        threshold2 = PerformanceThreshold("test_metric", "gt", 200.0, "critical", description="threshold2")
        
        monitor.add_threshold(threshold1)
        monitor.add_threshold(threshold2)
        assert len(monitor.thresholds["test_metric"]) == 2
        
        monitor.remove_threshold("test_metric", "threshold1")
        assert len(monitor.thresholds["test_metric"]) == 1
        assert monitor.thresholds["test_metric"][0].description == "threshold2"
    
    def test_threshold_violation_detection(self, monitor_setup):
        """Test detection of threshold violations."""
        collector, monitor = monitor_setup
        
        # Add threshold
        threshold = PerformanceThreshold(
            metric_name="test_metric",
            operator="gt",
            threshold_value=100.0,
            severity="warning",
            description="test_threshold",
            consecutive_violations=1  # Trigger immediately
        )
        monitor.add_threshold(threshold)
        
        # Record violating metrics
        for i in range(5):
            collector.record_metric("test_metric", 150.0)  # Above threshold
        
        # Check thresholds
        alerts = monitor.check_thresholds()
        
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.metric_name == "test_metric"
        assert alert.current_value == 150.0
        assert alert.severity == "warning"
        assert alert.threshold == threshold
    
    def test_consecutive_violations_requirement(self, monitor_setup):
        """Test that consecutive violations are required for alerting."""
        collector, monitor = monitor_setup
        
        # Add threshold requiring 3 consecutive violations
        threshold = PerformanceThreshold(
            metric_name="test_metric",
            operator="gt",
            threshold_value=100.0,
            severity="warning",
            description="test_threshold",
            consecutive_violations=3
        )
        monitor.add_threshold(threshold)
        
        # Record 2 violating metrics
        collector.record_metric("test_metric", 150.0)
        collector.record_metric("test_metric", 150.0)
        
        # Should not trigger alert yet
        alerts = monitor.check_thresholds()
        assert len(alerts) == 0
        
        # Add third violation
        collector.record_metric("test_metric", 150.0)
        alerts = monitor.check_thresholds()
        
        # Should trigger alert now
        assert len(alerts) == 1
    
    def test_alert_resolution(self, monitor_setup):
        """Test alert resolution when threshold is no longer violated."""
        collector, monitor = monitor_setup
        
        threshold = PerformanceThreshold(
            metric_name="test_metric",
            operator="gt",
            threshold_value=100.0,
            severity="warning",
            description="test_threshold",
            consecutive_violations=1
        )
        monitor.add_threshold(threshold)
        
        # Trigger alert
        collector.record_metric("test_metric", 150.0)
        alerts = monitor.check_thresholds()
        assert len(alerts) == 1
        assert len(monitor.get_active_alerts()) == 1
        
        # Resolve alert with normal value
        collector.record_metric("test_metric", 50.0)
        alerts = monitor.check_thresholds()
        assert len(alerts) == 0
        assert len(monitor.get_active_alerts()) == 0
        
        # Verify alert was marked as resolved
        resolved_alert = monitor.alert_history[-1]
        assert resolved_alert.resolved is True
        assert resolved_alert.resolved_timestamp is not None
    
    def test_latency_metric_uses_p95(self, monitor_setup):
        """Test that latency metrics use P95 value for evaluation."""
        collector, monitor = monitor_setup
        
        threshold = PerformanceThreshold(
            metric_name="recommendation_latency_ms",
            operator="gt",
            threshold_value=100.0,
            severity="warning",
            description="latency_threshold",
            consecutive_violations=1
        )
        monitor.add_threshold(threshold)
        
        # Record metrics with a high P95 but low mean
        values = [10.0] * 95 + [200.0] * 5  # Mean ~19.5, P95 = 200
        for value in values:
            collector.record_metric("recommendation_latency_ms", value)
        
        # Should trigger alert based on P95, not mean
        alerts = monitor.check_thresholds()
        assert len(alerts) == 1
        assert alerts[0].current_value == 200.0  # P95 value
    
    def test_get_alert_history(self, monitor_setup):
        """Test getting alert history with time filtering."""
        collector, monitor = monitor_setup
        
        threshold = PerformanceThreshold(
            metric_name="test_metric",
            operator="gt",
            threshold_value=100.0,
            severity="warning",
            description="test_threshold",
            consecutive_violations=1
        )
        monitor.add_threshold(threshold)
        
        # Generate some alerts
        collector.record_metric("test_metric", 150.0)
        monitor.check_thresholds()
        
        # Manually set old timestamp on alert
        old_alert = monitor.alert_history[0]
        old_alert.timestamp = datetime.utcnow() - timedelta(hours=25)
        
        # Generate new alert
        collector.record_metric("test_metric", 50.0)  # Reset
        monitor.check_thresholds()
        collector.record_metric("test_metric", 150.0)  # Trigger again
        monitor.check_thresholds()
        
        # Get recent history
        recent_alerts = monitor.get_alert_history(hours=24)
        assert len(recent_alerts) == 1
        
        # Get all history
        all_alerts = monitor.get_alert_history(hours=48)
        assert len(all_alerts) == 2


class TestNotificationManager:
    """Test NotificationManager for alert notifications."""
    
    @pytest.fixture
    def notification_manager(self):
        """Create NotificationManager for testing."""
        return NotificationManager()
    
    def test_add_notification_channel(self, notification_manager):
        """Test adding notification channel handlers."""
        handler_called = []
        
        def test_handler(alert):
            handler_called.append(alert)
        
        notification_manager.add_notification_channel(test_handler)
        assert len(notification_manager.notification_channels) == 1
    
    def test_notification_processing(self, notification_manager):
        """Test notification processing with handlers."""
        handler_calls = []
        
        def test_handler(alert):
            handler_calls.append(alert.message)
        
        notification_manager.add_notification_channel(test_handler)
        notification_manager.start()
        
        # Create test alert
        threshold = PerformanceThreshold("test", "gt", 100.0, "warning")
        alert = PerformanceAlert(
            alert_id="test_alert",
            timestamp=datetime.utcnow(),
            metric_name="test_metric",
            current_value=150.0,
            threshold=threshold,
            severity="warning",
            message="Test alert message"
        )
        
        # Send notification
        notification_manager.send_notification(alert)
        
        # Wait for processing
        time.sleep(0.1)
        notification_manager.stop()
        
        # Verify handler was called
        assert len(handler_calls) == 1
        assert handler_calls[0] == "Test alert message"
    
    def test_notification_handler_error_handling(self, notification_manager):
        """Test that handler errors don't break notification processing."""
        successful_calls = []
        
        def failing_handler(alert):
            raise Exception("Handler failed")
        
        def working_handler(alert):
            successful_calls.append(alert.message)
        
        notification_manager.add_notification_channel(failing_handler)
        notification_manager.add_notification_channel(working_handler)
        notification_manager.start()
        
        # Create test alert
        threshold = PerformanceThreshold("test", "gt", 100.0, "warning")
        alert = PerformanceAlert(
            alert_id="test_alert",
            timestamp=datetime.utcnow(),
            metric_name="test_metric",
            current_value=150.0,
            threshold=threshold,
            severity="warning",
            message="Test alert message"
        )
        
        # Send notification
        notification_manager.send_notification(alert)
        
        # Wait for processing
        time.sleep(0.1)
        notification_manager.stop()
        
        # Working handler should still be called despite failing handler
        assert len(successful_calls) == 1
        assert successful_calls[0] == "Test alert message"


class TestPerformanceMonitoringSystem:
    """Test main PerformanceMonitoringSystem integration."""
    
    @pytest.fixture
    def monitoring_system(self):
        """Create PerformanceMonitoringSystem for testing."""
        return PerformanceMonitoringSystem({'monitoring_interval_seconds': 1})
    
    def test_system_initialization(self, monitoring_system):
        """Test monitoring system initialization."""
        assert monitoring_system.metric_collector is not None
        assert monitoring_system.threshold_monitor is not None
        assert monitoring_system.notification_manager is not None
        assert monitoring_system.monitoring_active is False
        
        # Should have default thresholds configured
        assert len(monitoring_system.threshold_monitor.thresholds) > 0
    
    def test_monitor_request_context_manager_success(self, monitoring_system):
        """Test monitor_request context manager with successful request."""
        # Mock function to monitor
        def mock_request():
            time.sleep(0.1)  # Simulate processing time
            return "success"
        
        # Monitor the request
        with monitoring_system.monitor_request({"user_id": "test_user"}):
            result = mock_request()
        
        assert result == "success"
        
        # Verify metrics were recorded
        latency_samples = monitoring_system.metric_collector.get_recent_samples("recommendation_latency_ms")
        success_samples = monitoring_system.metric_collector.get_recent_samples("request_success")
        
        assert len(latency_samples) == 1
        assert len(success_samples) == 1
        assert latency_samples[0].value >= 100.0  # At least 100ms from sleep
        assert success_samples[0].value == 1.0
    
    def test_monitor_request_context_manager_failure(self, monitoring_system):
        """Test monitor_request context manager with failed request."""
        def mock_failing_request():
            time.sleep(0.05)
            raise ValueError("Request failed")
        
        # Monitor the failing request
        with pytest.raises(ValueError):
            with monitoring_system.monitor_request():
                mock_failing_request()
        
        # Verify error metrics were recorded
        latency_samples = monitoring_system.metric_collector.get_recent_samples("recommendation_latency_ms")
        error_samples = monitoring_system.metric_collector.get_recent_samples("request_error")
        error_type_samples = monitoring_system.metric_collector.get_recent_samples("error_by_type")
        
        assert len(latency_samples) == 1
        assert len(error_samples) == 1
        assert len(error_type_samples) == 1
        assert error_samples[0].value == 1.0
        assert error_type_samples[0].context['error_type'] == 'ValueError'
    
    def test_record_throughput_metric(self, monitoring_system):
        """Test recording throughput metrics."""
        monitoring_system.record_throughput_metric(150.0)
        
        samples = monitoring_system.metric_collector.get_recent_samples("requests_per_second")
        assert len(samples) == 1
        assert samples[0].value == 150.0
    
    def test_record_quality_metric(self, monitoring_system):
        """Test recording quality metrics."""
        monitoring_system.record_quality_metric(0.85, {"algorithm": "collaborative"})
        
        samples = monitoring_system.metric_collector.get_recent_samples("recommendation_quality_score")
        assert len(samples) == 1
        assert samples[0].value == 0.85
        assert samples[0].context["algorithm"] == "collaborative"
    
    def test_calculate_error_rate(self, monitoring_system):
        """Test error rate calculation."""
        # Record success and error metrics
        monitoring_system.metric_collector.record_metric("request_success", 1)
        monitoring_system.metric_collector.record_metric("request_success", 1)
        monitoring_system.metric_collector.record_metric("request_success", 1)
        monitoring_system.metric_collector.record_metric("request_error", 1)
        
        error_rate = monitoring_system.calculate_error_rate()
        assert error_rate == 25.0  # 1 error out of 4 total requests
        
        # Verify error rate metric was recorded
        error_rate_samples = monitoring_system.metric_collector.get_recent_samples("error_rate_percent")
        assert len(error_rate_samples) == 1
        assert error_rate_samples[0].value == 25.0
    
    def test_calculate_error_rate_no_requests(self, monitoring_system):
        """Test error rate calculation with no requests."""
        error_rate = monitoring_system.calculate_error_rate()
        assert error_rate == 0.0
    
    @patch('utils.performance_monitoring.get_db_connection')
    def test_save_performance_snapshot(self, mock_db, monitoring_system):
        """Test saving performance snapshot to database."""
        # Mock database response
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (456,)
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Record some sample metrics
        monitoring_system.metric_collector.record_metric("recommendation_latency_ms", 50.0)
        monitoring_system.metric_collector.record_metric("requests_per_second", 100.0)
        
        # Save snapshot
        snapshot_id = monitoring_system.save_performance_snapshot()
        
        assert snapshot_id == 456
        
        # Verify database insert was called
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert 'INSERT INTO performance_benchmarks' in call_args[0]
    
    def test_get_performance_summary(self, monitoring_system):
        """Test getting performance summary."""
        # Record some metrics
        monitoring_system.metric_collector.record_metric("recommendation_latency_ms", 75.0)
        monitoring_system.metric_collector.record_metric("requests_per_second", 120.0)
        monitoring_system.metric_collector.record_metric("error_rate_percent", 1.5)
        
        summary = monitoring_system.get_performance_summary()
        
        assert 'timestamp' in summary
        assert 'active_alerts' in summary
        assert 'metrics' in summary
        
        # Should include aggregated metrics
        assert 'recommendation_latency_ms' in summary['metrics']
        assert 'requests_per_second' in summary['metrics']
        
        latency_metrics = summary['metrics']['recommendation_latency_ms']
        assert latency_metrics['mean'] == 75.0
        assert latency_metrics['sample_count'] == 1
    
    def test_add_email_notifications(self, monitoring_system):
        """Test adding email notification channel."""
        # This test verifies the channel is added, but doesn't test actual email sending
        monitoring_system.add_email_notifications(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="test@example.com",
            password="password",
            from_email="alerts@example.com",
            to_emails=["admin@example.com"]
        )
        
        # Should have added one more notification channel
        assert len(monitoring_system.notification_manager.notification_channels) == 3  # 2 default + 1 email
    
    def test_add_webhook_notifications(self, monitoring_system):
        """Test adding webhook notification channel."""
        monitoring_system.add_webhook_notifications(
            webhook_url="https://hooks.example.com/alerts",
            webhook_headers={"Authorization": "Bearer token123"}
        )
        
        # Should have added one more notification channel
        assert len(monitoring_system.notification_manager.notification_channels) == 3  # 2 default + 1 webhook


class TestGlobalMonitorFunctions:
    """Test global monitor functions and decorators."""
    
    def test_get_global_monitor_singleton(self):
        """Test that get_global_monitor returns singleton instance."""
        monitor1 = get_global_monitor()
        monitor2 = get_global_monitor()
        
        assert monitor1 is monitor2
    
    def test_monitor_recommendation_request_decorator(self):
        """Test the decorator for monitoring recommendation requests."""
        @monitor_recommendation_request({"test": "context"})
        def test_function():
            time.sleep(0.05)
            return "result"
        
        result = test_function()
        assert result == "result"
        
        # Verify metrics were recorded in global monitor
        global_monitor = get_global_monitor()
        latency_samples = global_monitor.metric_collector.get_recent_samples("recommendation_latency_ms")
        success_samples = global_monitor.metric_collector.get_recent_samples("request_success")
        
        assert len(latency_samples) >= 1
        assert len(success_samples) >= 1


@pytest.mark.integration
class TestPerformanceMonitoringIntegration:
    """Integration tests for complete monitoring system."""
    
    def test_end_to_end_monitoring_workflow(self):
        """Test complete monitoring workflow from metric collection to alerting."""
        # Create monitoring system with fast intervals for testing
        system = PerformanceMonitoringSystem({'monitoring_interval_seconds': 0.1})
        
        # Add test threshold with immediate triggering
        test_threshold = PerformanceThreshold(
            metric_name="test_metric",
            operator="gt",
            threshold_value=100.0,
            severity="warning",
            description="integration_test",
            consecutive_violations=1
        )
        system.threshold_monitor.add_threshold(test_threshold)
        
        # Track notifications
        notifications_received = []
        def test_notification_handler(alert):
            notifications_received.append(alert)
        
        system.notification_manager.add_notification_channel(test_notification_handler)
        
        # Start monitoring
        system.start_monitoring()
        
        try:
            # Record violating metric
            system.metric_collector.record_metric("test_metric", 150.0)
            
            # Wait for monitoring cycle to process
            time.sleep(0.3)
            
            # Verify alert was triggered and notification sent
            active_alerts = system.threshold_monitor.get_active_alerts()
            assert len(active_alerts) >= 1
            assert len(notifications_received) >= 1
            
            # Verify alert details
            alert = notifications_received[0]
            assert alert.metric_name == "test_metric"
            assert alert.current_value == 150.0
            assert alert.severity == "warning"
            
        finally:
            system.stop_monitoring()
    
    @patch('utils.performance_monitoring.ResourceMonitor')
    def test_system_resource_monitoring_integration(self, mock_resource_monitor):
        """Test integration with system resource monitoring."""
        # Mock resource monitor
        mock_monitor_instance = MagicMock()
        mock_monitor_instance.get_samples.return_value = [
            {'cpu_percent': 75.0, 'memory_mb': 512.0, 'timestamp': time.time()}
        ]
        mock_resource_monitor.return_value = mock_monitor_instance
        
        system = PerformanceMonitoringSystem({'monitoring_interval_seconds': 0.1})
        system.start_monitoring()
        
        try:
            # Wait for monitoring cycle
            time.sleep(0.2)
            
            # Verify system metrics were recorded
            cpu_samples = system.metric_collector.get_recent_samples("cpu_usage_percent")
            memory_samples = system.metric_collector.get_recent_samples("memory_usage_mb")
            
            assert len(cpu_samples) >= 1
            assert len(memory_samples) >= 1
            assert cpu_samples[0].value == 75.0
            assert memory_samples[0].value == 512.0
            
        finally:
            system.stop_monitoring()


if __name__ == "__main__":
    # Run specific test suites
    import argparse
    
    parser = argparse.ArgumentParser(description="Run performance monitoring tests")
    parser.add_argument("--suite", choices=["unit", "integration", "all"], 
                       default="all", help="Which test suite to run")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    pytest_args = []
    if args.verbose:
        pytest_args.append("-v")
    
    if args.suite == "unit":
        pytest_args.extend(["-k", "not integration"])
    elif args.suite == "integration":
        pytest_args.extend(["-m", "integration"])
    
    pytest_args.append(__file__)
    
    import subprocess
    subprocess.run(["python", "-m", "pytest"] + pytest_args) 