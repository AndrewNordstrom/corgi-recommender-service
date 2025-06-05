#!/usr/bin/env python3
"""
Instance Health Monitor for Responsible Crawling

Implements intelligent rate limiting, health tracking, and responsible crawling
practices to avoid overloading Mastodon instances and prevent bans.

Features:
- Per-instance response time tracking
- Error rate monitoring with exponential backoff
- Conditional request support (If-Modified-Since)
- Instance rotation and load balancing
- Health-based crawling decisions
"""

import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import redis
from threading import Lock

logger = logging.getLogger(__name__)

@dataclass
class InstanceHealthMetrics:
    """Health metrics for a Mastodon instance."""
    instance: str
    last_successful_request: Optional[datetime] = None
    last_failed_request: Optional[datetime] = None
    success_count_24h: int = 0
    failure_count_24h: int = 0
    average_response_time: float = 0.0
    consecutive_failures: int = 0
    rate_limit_reset_time: Optional[datetime] = None
    last_modified_etag: Optional[str] = None
    health_status: str = 'healthy'  # healthy, degraded, unhealthy, banned
    backoff_until: Optional[datetime] = None
    requests_in_window: int = 0
    window_start: datetime = None

    @property
    def error_rate(self) -> float:
        """Calculate 24h error rate."""
        total = self.success_count_24h + self.failure_count_24h
        return self.failure_count_24h / total if total > 0 else 0.0

    @property
    def is_healthy(self) -> bool:
        """Check if instance is healthy for crawling."""
        return (
            self.health_status == 'healthy' and
            self.consecutive_failures < 3 and
            self.error_rate < 0.3 and
            (self.backoff_until is None or datetime.now(timezone.utc) > self.backoff_until)
        )

class ResponsibleCrawler:
    """
    Responsible crawling manager that implements best practices for
    Fediverse instance interaction to prevent abuse and bans.
    """
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client or redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self.instance_metrics = {}
        self.response_times = defaultdict(lambda: deque(maxlen=100))  # Last 100 response times
        self.lock = Lock()
        
        # Rate limiting configuration
        self.max_requests_per_minute = {
            'default': 30,  # Conservative default
            'mastodon.social': 20,  # Main instance - more conservative
            'fosstodon.org': 25,
            'hachyderm.io': 25,
            'mas.to': 30,
            'mstdn.jp': 35,
            'mastodon.world': 25
        }
        
        # Health thresholds
        self.health_thresholds = {
            'max_error_rate': 0.3,
            'max_consecutive_failures': 3,
            'max_response_time': 5.0,
            'min_success_rate': 0.7
        }
        
    def get_instance_health(self, instance: str) -> InstanceHealthMetrics:
        """Get current health metrics for an instance."""
        if instance not in self.instance_metrics:
            self.instance_metrics[instance] = InstanceHealthMetrics(
                instance=instance,
                window_start=datetime.now(timezone.utc)
            )
        return self.instance_metrics[instance]
    
    def can_make_request(self, instance: str) -> Tuple[bool, str]:
        """
        Check if we can make a request to the instance based on health and rate limits.
        
        Returns:
            (can_make_request, reason)
        """
        metrics = self.get_instance_health(instance)
        now = datetime.now(timezone.utc)
        
        # Check if instance is in backoff period
        if metrics.backoff_until and now < metrics.backoff_until:
            return False, f"Instance in backoff until {metrics.backoff_until}"
        
        # Check health status
        if not metrics.is_healthy:
            return False, f"Instance unhealthy: {metrics.health_status} (errors: {metrics.consecutive_failures})"
        
        # Check rate limits
        rate_limit = self.max_requests_per_minute.get(instance, self.max_requests_per_minute['default'])
        
        # Reset window if needed
        if not metrics.window_start or (now - metrics.window_start).total_seconds() >= 60:
            metrics.window_start = now
            metrics.requests_in_window = 0
        
        if metrics.requests_in_window >= rate_limit:
            return False, f"Rate limit reached ({metrics.requests_in_window}/{rate_limit} per minute)"
        
        return True, "OK"
    
    def record_request_start(self, instance: str) -> datetime:
        """Record the start of a request."""
        metrics = self.get_instance_health(instance)
        metrics.requests_in_window += 1
        return datetime.now(timezone.utc)
    
    def record_request_success(self, instance: str, start_time: datetime, response_headers: Dict = None):
        """Record a successful request."""
        metrics = self.get_instance_health(instance)
        now = datetime.now(timezone.utc)
        
        # Calculate response time
        response_time = (now - start_time).total_seconds()
        self.response_times[instance].append(response_time)
        
        # Update metrics
        metrics.last_successful_request = now
        metrics.success_count_24h += 1
        metrics.consecutive_failures = 0
        
        # Update average response time
        avg_times = list(self.response_times[instance])
        metrics.average_response_time = sum(avg_times) / len(avg_times)
        
        # Process response headers for rate limiting info
        if response_headers:
            self._process_rate_limit_headers(metrics, response_headers)
        
        # Update health status
        self._update_health_status(metrics)
        
        # Store metrics in Redis for persistence
        self._store_metrics_redis(metrics)
        
        logger.debug(f"✅ {instance}: Success in {response_time:.2f}s (avg: {metrics.average_response_time:.2f}s)")
    
    def record_request_failure(self, instance: str, start_time: datetime, error: Exception, status_code: int = None):
        """Record a failed request with intelligent backoff."""
        metrics = self.get_instance_health(instance)
        now = datetime.now(timezone.utc)
        
        response_time = (now - start_time).total_seconds()
        metrics.last_failed_request = now
        metrics.failure_count_24h += 1
        metrics.consecutive_failures += 1
        
        # Determine severity and backoff
        backoff_seconds = self._calculate_backoff(metrics, error, status_code)
        if backoff_seconds > 0:
            metrics.backoff_until = now + timedelta(seconds=backoff_seconds)
        
        # Update health status
        self._update_health_status(metrics)
        
        # Store metrics
        self._store_metrics_redis(metrics)
        
        logger.warning(f"❌ {instance}: {error} (failures: {metrics.consecutive_failures}, backoff: {backoff_seconds}s)")
    
    def _calculate_backoff(self, metrics: InstanceHealthMetrics, error: Exception, status_code: int = None) -> int:
        """Calculate exponential backoff time in seconds."""
        base_backoff = 60  # Start with 1 minute
        failure_count = max(1, metrics.consecutive_failures + 1)  # Ensure at least 1 for meaningful backoff
        
        # Different backoff strategies based on error type
        if status_code == 429:  # Rate limited
            return 900  # 15 minutes for rate limiting
        elif status_code in [502, 503, 504]:  # Server errors
            return min(base_backoff * (2 ** (failure_count - 1)), 3600)  # Max 1 hour
        elif status_code in [400, 401, 403]:  # Client errors (possible ban)
            return min(1800 * failure_count, 7200)  # Up to 2 hours
        elif "timeout" in str(error).lower():
            return min(base_backoff * failure_count, 1800)  # Max 30 minutes
        else:
            return min(int(base_backoff * (1.5 ** (failure_count - 1))), 3600)
    
    def _process_rate_limit_headers(self, metrics: InstanceHealthMetrics, headers: Dict):
        """Process Mastodon rate limit headers."""
        # Mastodon rate limiting headers
        if 'x-ratelimit-reset' in headers:
            try:
                reset_timestamp = int(headers['x-ratelimit-reset'])
                metrics.rate_limit_reset_time = datetime.fromtimestamp(reset_timestamp, tz=timezone.utc)
            except ValueError:
                pass
        
        # ETag for conditional requests
        if 'etag' in headers:
            metrics.last_modified_etag = headers['etag']
    
    def _update_health_status(self, metrics: InstanceHealthMetrics):
        """Update health status based on current metrics."""
        if metrics.consecutive_failures >= 5:
            metrics.health_status = 'banned'
        elif metrics.error_rate > 0.5 or metrics.consecutive_failures >= 3:
            metrics.health_status = 'unhealthy'
        elif metrics.error_rate > 0.3 or metrics.average_response_time > 3.0:
            metrics.health_status = 'degraded'
        else:
            metrics.health_status = 'healthy'
    
    def _store_metrics_redis(self, metrics: InstanceHealthMetrics):
        """Store metrics in Redis for persistence across workers."""
        try:
            key = f"instance_health:{metrics.instance}"
            data = asdict(metrics)
            
            # Convert datetime objects to ISO strings
            for field in ['last_successful_request', 'last_failed_request', 'rate_limit_reset_time', 'backoff_until', 'window_start']:
                if data[field]:
                    data[field] = data[field].isoformat()
            
            self.redis_client.setex(key, 7200, json.dumps(data))  # Store for 2 hours
            
        except Exception as e:
            logger.warning(f"Failed to store metrics for {metrics.instance}: {e}")
    
    def get_healthy_instances(self, preferred_instances: List[str]) -> List[str]:
        """
        Get list of healthy instances for crawling, ordered by health score.
        
        Args:
            preferred_instances: List of preferred instances to check
            
        Returns:
            List of healthy instances ordered by health score (best first)
        """
        healthy_instances = []
        
        for instance in preferred_instances:
            can_request, reason = self.can_make_request(instance)
            if can_request:
                metrics = self.get_instance_health(instance)
                health_score = self._calculate_health_score(metrics)
                healthy_instances.append((instance, health_score))
        
        # Sort by health score (higher is better)
        healthy_instances.sort(key=lambda x: x[1], reverse=True)
        
        return [instance for instance, score in healthy_instances]
    
    def _calculate_health_score(self, metrics: InstanceHealthMetrics) -> float:
        """Calculate a health score for instance ranking."""
        score = 100.0
        
        # Penalize for errors
        score -= metrics.error_rate * 50
        score -= metrics.consecutive_failures * 10
        
        # Penalize for slow response times
        if metrics.average_response_time > 2.0:
            score -= (metrics.average_response_time - 2.0) * 10
        
        # Bonus for recent successful requests
        if metrics.last_successful_request:
            time_since_success = (datetime.now(timezone.utc) - metrics.last_successful_request).total_seconds()
            if time_since_success < 300:  # Within 5 minutes
                score += 10
        
        return max(0.0, score)
    
    def get_conditional_headers(self, instance: str) -> Dict[str, str]:
        """Get conditional request headers to minimize bandwidth."""
        headers = {}
        metrics = self.get_instance_health(instance)
        
        if metrics.last_modified_etag:
            headers['If-None-Match'] = metrics.last_modified_etag
        
        if metrics.last_successful_request:
            # Add If-Modified-Since header
            headers['If-Modified-Since'] = metrics.last_successful_request.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        return headers
    
    def get_health_summary(self) -> Dict:
        """Get overall health summary for monitoring."""
        summary = {
            'total_instances': len(self.instance_metrics),
            'healthy_instances': 0,
            'degraded_instances': 0,
            'unhealthy_instances': 0,
            'banned_instances': 0,
            'instances_in_backoff': 0,
            'average_response_time': 0.0,
            'overall_error_rate': 0.0
        }
        
        total_requests = 0
        total_failures = 0
        total_response_time = 0.0
        
        for metrics in self.instance_metrics.values():
            # Count by status
            if metrics.health_status == 'healthy':
                summary['healthy_instances'] += 1
            elif metrics.health_status == 'degraded':
                summary['degraded_instances'] += 1
            elif metrics.health_status == 'unhealthy':
                summary['unhealthy_instances'] += 1
            elif metrics.health_status == 'banned':
                summary['banned_instances'] += 1
            
            # Count backoff instances
            if metrics.backoff_until and datetime.now(timezone.utc) < metrics.backoff_until:
                summary['instances_in_backoff'] += 1
            
            # Aggregate metrics
            instance_total = metrics.success_count_24h + metrics.failure_count_24h
            total_requests += instance_total
            total_failures += metrics.failure_count_24h
            total_response_time += metrics.average_response_time
        
        # Calculate averages
        if len(self.instance_metrics) > 0:
            summary['average_response_time'] = total_response_time / len(self.instance_metrics)
        
        if total_requests > 0:
            summary['overall_error_rate'] = total_failures / total_requests
        
        return summary

# Global instance for use across the application
crawler_health_monitor = ResponsibleCrawler() 