#!/usr/bin/env python3
"""
Core Performance Monitoring System Tests

This module provides essential tests for the performance monitoring
and alerting system, focusing on core functionality.
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
    """Test core PerformanceThreshold functionality."""
    
    def test_threshold_creation_and_evaluation(self):
        """Test threshold creation and basic evaluation."""
        threshold = PerformanceThreshold(
            metric_name="test_metric",
            operator="gt",
            threshold_value=100.0,
            severity="warning",
            window_seconds=300,
            consecutive_violations=3
        )
        
        assert threshold.metric_name == "test_metric"
        assert threshold.operator == "gt"
        assert threshold.threshold_value == 100.0
        assert threshold.severity == "warning"
        
        # Test evaluation
        assert threshold.evaluate(120.0) is True
        assert threshold.evaluate(80.0) is False
    
    def test_threshold_operators(self):
        """Test essential threshold operators."""
        gt_threshold = PerformanceThreshold("test", "gt", 50.0, "warning")
        assert gt_threshold.evaluate(60.0) is True
        assert gt_threshold.evaluate(40.0) is False
        
        lt_threshold = PerformanceThreshold("test", "lt", 50.0, "warning")
        assert lt_threshold.evaluate(40.0) is True
        assert lt_threshold.evaluate(60.0) is False


class TestMetricCollector:
    """Test core MetricCollector functionality."""
    
    @pytest.fixture
    def collector(self):
        """Create MetricCollector for testing."""
        return MetricCollector(buffer_size=100)
    
    def test_basic_metric_recording(self, collector):
        """Test basic metric recording and retrieval."""
        collector.record_metric("test_metric", 100.0)
        collector.record_metric("test_metric", 150.0)
        
        samples = collector.get_recent_samples("test_metric")
        assert len(samples) == 2
        assert samples[0].value == 100.0
        assert samples[1].value == 150.0
    
    def test_metric_aggregation(self, collector):
        """Test basic metric aggregation."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            collector.record_metric("test_metric", value)
        
        aggregated = collector.aggregate_metric("test_metric", window_minutes=60)
        
        assert aggregated is not None
        assert aggregated.sample_count == 5
        assert aggregated.min_value == 10.0
        assert aggregated.max_value == 50.0
        assert aggregated.mean_value == 30.0


class TestThresholdMonitor:
    """Test core ThresholdMonitor functionality."""
    
    @pytest.fixture
    def monitor_setup(self):
        """Set up monitor with collector."""
        collector = MetricCollector()
        monitor = ThresholdMonitor(collector)
        return monitor, collector
    
    def test_threshold_management(self, monitor_setup):
        """Test adding and removing thresholds."""
        monitor, collector = monitor_setup
        
        threshold = PerformanceThreshold("test_metric", "gt", 100.0, "warning")
        monitor.add_threshold(threshold)
        
        assert len(monitor.thresholds) == 1
        assert "test_metric" in monitor.thresholds
        
        monitor.remove_threshold("test_metric", "gt", 100.0)
        assert len(monitor.thresholds) == 0
    
    def test_violation_detection(self, monitor_setup):
        """Test basic violation detection."""
        monitor, collector = monitor_setup
        
        threshold = PerformanceThreshold("test_metric", "gt", 100.0, "warning")
        monitor.add_threshold(threshold)
        
        # Record violation
        collector.record_metric("test_metric", 150.0)
        violations = monitor.check_violations()
        
        assert len(violations) == 1
        assert violations[0].metric_name == "test_metric"
    
    def test_alert_generation(self, monitor_setup):
        """Test alert generation and resolution."""
        monitor, collector = monitor_setup
        
        threshold = PerformanceThreshold("test_metric", "gt", 100.0, "warning")
        monitor.add_threshold(threshold)
        
        # Trigger alert
        collector.record_metric("test_metric", 150.0)
        violations = monitor.check_violations()
        
        assert len(violations) == 1
        alert = violations[0]
        assert alert.severity == "warning"
        assert alert.metric_name == "test_metric"


class TestNotificationManager:
    """Test core NotificationManager functionality."""
    
    @pytest.fixture
    def notification_manager(self):
        """Create NotificationManager for testing."""
        return NotificationManager()
    
    def test_notification_processing(self, notification_manager):
        """Test basic notification processing."""
        received_alerts = []
        
        def test_handler(alert):
            received_alerts.append(alert)
        
        notification_manager.add_handler("test_channel", test_handler)
        
        alert = PerformanceAlert(
            metric_name="test_metric",
            severity="warning", 
            current_value=150.0,
            threshold_value=100.0,
            message="Test alert"
        )
        
        notification_manager.process_alert(alert)
        
        assert len(received_alerts) == 1
        assert received_alerts[0].metric_name == "test_metric"


class TestPerformanceMonitoringSystem:
    """Test core PerformanceMonitoringSystem functionality."""
    
    @pytest.fixture
    def monitoring_system(self):
        """Create monitoring system for testing."""
        return PerformanceMonitoringSystem()
    
    def test_system_initialization(self, monitoring_system):
        """Test system initialization."""
        assert monitoring_system.collector is not None
        assert monitoring_system.threshold_monitor is not None
        assert monitoring_system.notification_manager is not None
    
    def test_request_monitoring(self, monitoring_system):
        """Test request monitoring context manager."""
        with monitoring_system.monitor_request("test_operation") as context:
            time.sleep(0.01)  # Simulate work
            context.set_quality_metric("accuracy", 0.95)
        
        # Check that metrics were recorded
        latency_samples = monitoring_system.collector.get_recent_samples("latency_ms")
        assert len(latency_samples) > 0
        assert latency_samples[-1].value > 0
    
    def test_throughput_recording(self, monitoring_system):
        """Test throughput metric recording."""
        monitoring_system.record_throughput_metric("api_requests", 5)
        
        samples = monitoring_system.collector.get_recent_samples("throughput_api_requests")
        assert len(samples) == 1
        assert samples[0].value == 5
    
    def test_error_rate_calculation(self, monitoring_system):
        """Test error rate calculation."""
        # Record some successful and failed requests
        for _ in range(8):
            monitoring_system.record_throughput_metric("requests", 1)
        for _ in range(2):
            monitoring_system.record_throughput_metric("errors", 1)
        
        error_rate = monitoring_system.calculate_error_rate(window_minutes=1)
        assert 0.15 <= error_rate <= 0.25  # Approximately 20%
    
    def test_performance_summary(self, monitoring_system):
        """Test performance summary generation."""
        # Record some test metrics
        monitoring_system.collector.record_metric("latency_ms", 100.0)
        monitoring_system.collector.record_metric("latency_ms", 120.0)
        monitoring_system.record_throughput_metric("requests", 10)
        
        summary = monitoring_system.get_performance_summary(window_minutes=5)
        
        assert "latency_ms" in summary
        assert "throughput_requests" in summary
        assert summary["latency_ms"]["sample_count"] == 2


class TestGlobalMonitorFunctions:
    """Test global monitor functions."""
    
    def test_global_monitor_singleton(self):
        """Test global monitor singleton pattern."""
        monitor1 = get_global_monitor()
        monitor2 = get_global_monitor()
        assert monitor1 is monitor2
    
    def test_monitor_decorator(self):
        """Test monitoring decorator functionality."""
        @monitor_recommendation_request({"test": "context"})
        def test_function():
            time.sleep(0.01)
            return "success"
        
        result = test_function()
        assert result == "success"
        
        # Verify monitoring occurred
        global_monitor = get_global_monitor()
        latency_samples = global_monitor.collector.get_recent_samples("latency_ms")
        assert len(latency_samples) > 0


@pytest.mark.integration
class TestPerformanceMonitoringIntegration:
    """Test core integration scenarios."""
    
    def test_end_to_end_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        system = PerformanceMonitoringSystem()
        
        # Set up threshold
        threshold = PerformanceThreshold("latency_ms", "gt", 50.0, "warning")
        system.threshold_monitor.add_threshold(threshold)
        
        # Set up notification
        alerts_received = []
        def alert_handler(alert):
            alerts_received.append(alert)
        
        system.notification_manager.add_handler("test", alert_handler)
        
        # Trigger violation
        system.collector.record_metric("latency_ms", 75.0)
        violations = system.threshold_monitor.check_violations()
        
        if violations:
            for alert in violations:
                system.notification_manager.process_alert(alert)
        
        # Verify end-to-end flow
        assert len(violations) == 1
        assert len(alerts_received) == 1
        assert alerts_received[0].metric_name == "latency_ms"


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