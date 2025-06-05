#!/usr/bin/env python3
"""
Test Suite for Responsible Crawling System

Tests the health monitoring, rate limiting, and responsible crawling
practices implemented for the Active Content Crawling System.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from utils.instance_health_monitor import ResponsibleCrawler, InstanceHealthMetrics

class TestInstanceHealthMonitor:
    """Test the instance health monitoring system."""
    
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
            (Exception("error"), 403, 1800),   # Possible ban
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
        assert metrics.last_modified_etag == 'test-etag'
        
        # Test failed request
        self.crawler.record_request_failure(
            self.test_instance,
            start_time,
            Exception("test error"),
            500
        )
        
        assert metrics.failure_count_24h == 1
        assert metrics.consecutive_failures == 1
    
    def test_healthy_instance_selection(self):
        """Test intelligent instance selection."""
        instances = ['instance1.example', 'instance2.example', 'instance3.example']
        
        # Make instance2 unhealthy
        metrics2 = self.crawler.get_instance_health('instance2.example')
        metrics2.consecutive_failures = 5
        metrics2.health_status = 'banned'
        
        # Make instance3 degraded but usable
        metrics3 = self.crawler.get_instance_health('instance3.example')
        metrics3.average_response_time = 4.0
        metrics3.health_status = 'degraded'
        
        healthy_instances = self.crawler.get_healthy_instances(instances)
        
        # Should only return healthy instances, ordered by health score
        assert 'instance2.example' not in healthy_instances
        assert 'instance1.example' in healthy_instances
    
    def test_conditional_headers(self):
        """Test conditional request headers generation."""
        metrics = self.crawler.get_instance_health(self.test_instance)
        
        # No previous requests - no headers
        headers = self.crawler.get_conditional_headers(self.test_instance)
        assert len(headers) == 0
        
        # Set ETag and last successful request
        metrics.last_modified_etag = 'test-etag'
        metrics.last_successful_request = datetime.now(timezone.utc)
        
        headers = self.crawler.get_conditional_headers(self.test_instance)
        assert 'If-None-Match' in headers
        assert 'If-Modified-Since' in headers
        assert headers['If-None-Match'] == 'test-etag'
    
    def test_health_summary(self):
        """Test overall health summary generation."""
        # Create instances with different health states
        instances = [
            ('healthy.example', 'healthy'),
            ('degraded.example', 'degraded'), 
            ('unhealthy.example', 'unhealthy'),
            ('banned.example', 'banned')
        ]
        
        for instance, status in instances:
            metrics = self.crawler.get_instance_health(instance)
            metrics.health_status = status
            if status == 'banned':
                metrics.consecutive_failures = 5
        
        summary = self.crawler.get_health_summary()
        
        assert summary['total_instances'] == 4
        assert summary['healthy_instances'] == 1
        assert summary['degraded_instances'] == 1
        assert summary['unhealthy_instances'] == 1
        assert summary['banned_instances'] == 1

class TestResponsibleCrawlingIntegration:
    """Test integration with the content crawler."""
    
    @patch('utils.instance_health_monitor.redis.Redis')
    def test_redis_persistence(self, mock_redis):
        """Test Redis persistence of health metrics."""
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        crawler = ResponsibleCrawler(mock_redis_client)
        metrics = crawler.get_instance_health('test.example')
        
        # Simulate storing metrics
        crawler._store_metrics_redis(metrics)
        
        # Verify Redis was called
        mock_redis_client.setex.assert_called_once()
        args = mock_redis_client.setex.call_args[0]
        assert args[0] == 'instance_health:test.example'
        assert args[1] == 7200  # 2 hours TTL
    
    def test_rate_limit_window_reset(self):
        """Test rate limiting window reset."""
        crawler = ResponsibleCrawler()
        instance = 'test.example'
        
        # Fill up the rate limit
        metrics = crawler.get_instance_health(instance)
        metrics.requests_in_window = 30
        metrics.window_start = datetime.now(timezone.utc) - timedelta(seconds=70)  # Old window
        
        # Should reset window and allow request
        can_request, reason = crawler.can_make_request(instance)
        assert can_request is True
        assert metrics.requests_in_window == 0
    
    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        crawler = ResponsibleCrawler()
        metrics = crawler.get_instance_health('test.example')
        
        # No requests yet
        assert metrics.error_rate == 0.0
        
        # Add some requests
        metrics.success_count_24h = 70
        metrics.failure_count_24h = 30
        
        assert metrics.error_rate == 0.3  # 30/100
        
        # Test health assessment
        assert not metrics.is_healthy  # Error rate too high (>= 0.3)

def test_crawler_configuration():
    """Test crawler configuration values."""
    crawler = ResponsibleCrawler()
    
    # Check rate limits are reasonable
    assert crawler.max_requests_per_minute['default'] <= 60
    assert crawler.max_requests_per_minute['mastodon.social'] <= 30
    
    # Check health thresholds are appropriate
    assert crawler.health_thresholds['max_error_rate'] <= 0.5
    assert crawler.health_thresholds['max_consecutive_failures'] >= 3

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 