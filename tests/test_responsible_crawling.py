#!/usr/bin/env python3
"""
Core Responsible Crawling System Tests

Essential tests for health monitoring, rate limiting, and responsible 
crawling practices for the Active Content Crawling System.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from utils.instance_health_monitor import ResponsibleCrawler, InstanceHealthMetrics

class TestInstanceHealthMonitor:
    """Test core instance health monitoring functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.crawler = ResponsibleCrawler()
        self.test_instance = 'test.mastodon.example'
    
    def test_initial_health_metrics(self):
        """Test initial health metrics creation."""
        metrics = self.crawler.get_instance_health(self.test_instance)
        
        assert metrics.instance == self.test_instance
        assert metrics.health_status == 'healthy'
        assert metrics.consecutive_failures == 0
        assert metrics.error_rate == 0.0
        assert metrics.is_healthy is True
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        # Should allow initial requests
        can_request, reason = self.crawler.can_make_request(self.test_instance)
        assert can_request is True
        assert reason == "OK"
        
        # Simulate hitting rate limit
        metrics = self.crawler.get_instance_health(self.test_instance)
        metrics.requests_in_window = 30  # Hit default limit
        
        can_request, reason = self.crawler.can_make_request(self.test_instance)
        assert can_request is False
        assert "Rate limit reached" in reason
    
    def test_backoff_mechanism(self):
        """Test exponential backoff for failures."""
        metrics = self.crawler.get_instance_health(self.test_instance)
        
        # Test different error scenarios
        test_cases = [
            (Exception("timeout"), None, 60),  # Basic timeout
            (Exception("error"), 429, 900),    # Rate limited
            (Exception("error"), 503, 60),     # Server error  
        ]
        
        for error, status_code, expected_min_backoff in test_cases:
            backoff = self.crawler._calculate_backoff(metrics, error, status_code)
            assert backoff >= expected_min_backoff
    
    def test_health_status_updates(self):
        """Test health status transitions."""
        metrics = self.crawler.get_instance_health(self.test_instance)
        
        # Start healthy
        assert metrics.health_status == 'healthy'
        
        # Simulate failures
        metrics.consecutive_failures = 3
        metrics.failure_count_24h = 10
        metrics.success_count_24h = 20
        
        self.crawler._update_health_status(metrics)
        assert metrics.health_status == 'unhealthy'
        
        # Simulate recovery
        metrics.consecutive_failures = 0
        metrics.failure_count_24h = 2
        metrics.success_count_24h = 30
        
        self.crawler._update_health_status(metrics)
        assert metrics.health_status == 'healthy'
    
    def test_request_tracking(self):
        """Test request success/failure tracking."""
        start_time = datetime.now(timezone.utc)
        
        # Test successful request
        self.crawler.record_request_success(
            self.test_instance, 
            start_time,
            {'etag': 'test-etag'}
        )
        
        metrics = self.crawler.get_instance_health(self.test_instance)
        assert metrics.success_count_24h == 1
        assert metrics.consecutive_failures == 0
        
        # Test failed request
        self.crawler.record_request_failure(
            self.test_instance,
            start_time,
            Exception("test error"),
            500
        )
        
        assert metrics.failure_count_24h == 1
        assert metrics.consecutive_failures == 1


class TestResponsibleCrawlingIntegration:
    """Test core integration scenarios."""
    
    def test_healthy_instance_selection(self):
        """Test intelligent instance selection."""
        crawler = ResponsibleCrawler()
        instances = ['instance1.example', 'instance2.example', 'instance3.example']
        
        # Make instance2 unhealthy
        metrics2 = crawler.get_instance_health('instance2.example')
        metrics2.consecutive_failures = 5
        metrics2.health_status = 'banned'
        
        healthy_instances = crawler.get_healthy_instances(instances)
        
        # Should only return healthy instances
        assert 'instance2.example' not in healthy_instances
        assert 'instance1.example' in healthy_instances


def test_crawler_configuration():
    """Test basic crawler configuration setup."""
    crawler = ResponsibleCrawler()
    
    # Test default configuration values
    assert hasattr(crawler, 'instance_health_cache')
    assert hasattr(crawler, 'get_instance_health')
    assert callable(crawler.can_make_request)


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 