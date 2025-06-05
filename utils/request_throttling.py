#!/usr/bin/env python3
"""
Advanced Request Throttling for High-Volume Deployments

Provides sophisticated request throttling beyond basic rate limiting,
including burst control, adaptive throttling, circuit breakers,
and granular logging controls.

Features:
- Burst protection with token bucket algorithm
- Adaptive throttling based on system load
- Circuit breaker pattern for upstream failures
- Per-endpoint and per-user throttling
- Granular logging with configurable verbosity
- Metrics integration for monitoring

This implements TODO #46: Add request throttling for high-volume deployments
This implements TODO #47: Create more granular logging controls
"""

import json
import logging
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
import os

from flask import request, jsonify, g
import redis

from config import REDIS_URL, REDIS_ENABLED

logger = logging.getLogger(__name__)

class LogLevel(Enum):
    """Granular logging levels for different components."""
    MINIMAL = 0      # Only critical errors and blocks
    STANDARD = 1     # Basic throttling decisions 
    DETAILED = 2     # Full request analysis
    VERBOSE = 3      # Debug-level diagnostics
    TRACE = 4        # Every throttling check

class ThrottleReason(Enum):
    """Reasons for throttling requests."""
    BURST_LIMIT = "burst_limit"
    SYSTEM_LOAD = "system_load"
    ENDPOINT_OVERLOAD = "endpoint_overload"
    USER_ABUSE = "user_abuse"
    CIRCUIT_BREAKER = "circuit_breaker"
    UPSTREAM_ERRORS = "upstream_errors"

@dataclass
class ThrottleConfig:
    """Configuration for request throttling."""
    # Token bucket settings
    bucket_size: int = 100           # Maximum burst requests
    refill_rate: float = 10.0        # Tokens per second
    
    # System load thresholds
    cpu_threshold: float = 80.0      # CPU usage percentage
    memory_threshold: float = 85.0   # Memory usage percentage
    
    # Circuit breaker settings
    failure_threshold: int = 10      # Failures before circuit opens
    timeout_seconds: int = 60        # Circuit breaker timeout
    
    # Per-endpoint limits
    endpoint_limits: Dict[str, int] = field(default_factory=dict)
    
    # Logging configuration
    log_level: LogLevel = LogLevel.STANDARD
    log_blocked_only: bool = False   # Only log when requests are blocked
    log_include_headers: bool = False # Include request headers in logs
    log_include_user_agent: bool = True # Include User-Agent in logs

class TokenBucket:
    """Token bucket implementation for burst control."""
    
    def __init__(self, bucket_size: int, refill_rate: float):
        self.bucket_size = bucket_size
        self.refill_rate = refill_rate
        self.tokens = bucket_size
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            bool: True if tokens were consumed, False if insufficient
        """
        with self.lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * self.refill_rate
            self.tokens = min(self.bucket_size, self.tokens + tokens_to_add)
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get estimated wait time for tokens to be available."""
        with self.lock:
            if self.tokens >= tokens:
                return 0.0
            
            needed_tokens = tokens - self.tokens
            return needed_tokens / self.refill_rate

class CircuitBreaker:
    """Circuit breaker for upstream failure detection."""
    
    def __init__(self, failure_threshold: int = 10, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self.lock = threading.Lock()
    
    def record_success(self):
        """Record a successful request."""
        with self.lock:
            self.failure_count = 0
            if self.state == "half-open":
                self.state = "closed"
    
    def record_failure(self):
        """Record a failed request."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
    
    def should_allow_request(self) -> bool:
        """Check if request should be allowed through."""
        with self.lock:
            if self.state == "closed":
                return True
            
            if self.state == "open":
                # Check if timeout has elapsed
                if (time.time() - self.last_failure_time) > self.timeout_seconds:
                    self.state = "half-open"
                    return True
                return False
            
            # Half-open state - allow one request to test
            return True

class RequestThrottler:
    """
    Advanced request throttling system for high-volume deployments.
    """
    
    def __init__(self, config: ThrottleConfig = None):
        self.config = config or ThrottleConfig()
        self.buckets: Dict[str, TokenBucket] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.endpoint_stats: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.user_stats: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self.lock = threading.Lock()
        
        # Redis connection for distributed throttling
        self.redis_client = None
        if REDIS_ENABLED:
            try:
                import redis
                self.redis_client = redis.from_url(REDIS_URL)
                self.redis_client.ping()  # Test connection
            except Exception as e:
                logger.warning(f"Redis connection for throttling failed: {e}")
        
        # Initialize logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup granular logging based on configuration."""
        self.throttle_logger = logging.getLogger("request_throttling")
        
        # Set log level based on configuration
        log_levels = {
            LogLevel.MINIMAL: logging.ERROR,
            LogLevel.STANDARD: logging.INFO,
            LogLevel.DETAILED: logging.INFO,
            LogLevel.VERBOSE: logging.DEBUG,
            LogLevel.TRACE: logging.DEBUG
        }
        
        self.throttle_logger.setLevel(log_levels.get(self.config.log_level, logging.INFO))
        
        # Create dedicated file handler if it doesn't exist
        if not self.throttle_logger.handlers:
            try:
                handler = logging.FileHandler('logs/throttling.log')
                formatter = logging.Formatter(
                    '%(asctime)s [%(levelname)s] %(message)s'
                )
                handler.setFormatter(formatter)
                self.throttle_logger.addHandler(handler)
            except Exception as e:
                logger.warning(f"Could not setup throttling log file: {e}")
    
    def _get_bucket_key(self, identifier: str, bucket_type: str = "global") -> str:
        """Generate bucket key for token bucket."""
        return f"throttle:{bucket_type}:{identifier}"
    
    def _get_or_create_bucket(self, key: str) -> TokenBucket:
        """Get or create a token bucket for the given key."""
        if key not in self.buckets:
            with self.lock:
                if key not in self.buckets:
                    self.buckets[key] = TokenBucket(
                        self.config.bucket_size,
                        self.config.refill_rate
                    )
        return self.buckets[key]
    
    def _get_system_load(self) -> Dict[str, float]:
        """Get current system load metrics."""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            return {
                'cpu': cpu_percent,
                'memory': memory.percent,
                'load_avg': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0.0
            }
        except ImportError:
            # psutil not available, return safe defaults
            return {'cpu': 0.0, 'memory': 0.0, 'load_avg': 0.0}
        except Exception as e:
            logger.warning(f"Error getting system load: {e}")
            return {'cpu': 0.0, 'memory': 0.0, 'load_avg': 0.0}
    
    def _should_throttle_by_load(self) -> Optional[ThrottleReason]:
        """Check if request should be throttled based on system load."""
        load = self._get_system_load()
        
        if load['cpu'] > self.config.cpu_threshold:
            return ThrottleReason.SYSTEM_LOAD
        
        if load['memory'] > self.config.memory_threshold:
            return ThrottleReason.SYSTEM_LOAD
        
        return None
    
    def _log_throttle_decision(self, allowed: bool, reason: Optional[ThrottleReason] = None, 
                             endpoint: str = None, user_id: str = None, 
                             wait_time: float = 0.0, additional_info: Dict = None):
        """Log throttling decisions with configurable detail levels."""
        if self.config.log_blocked_only and allowed:
            return
            
        # Build log context
        context = {
            'timestamp': datetime.now().isoformat(),
            'action': 'allowed' if allowed else 'throttled',
            'endpoint': endpoint or 'unknown',
            'user_id': user_id or 'anonymous',
        }
        
        if reason:
            context['reason'] = reason.value
        if wait_time > 0:
            context['wait_time_seconds'] = round(wait_time, 2)
        if additional_info:
            context.update(additional_info)
        
        # Add request information if available and configured
        try:
            from flask import has_request_context, request
            if has_request_context():
                if self.config.log_level.value >= LogLevel.VERBOSE.value:
                    context['remote_addr'] = getattr(request, 'remote_addr', 'unknown')
                    context['method'] = getattr(request, 'method', 'unknown')
                    context['path'] = getattr(request, 'path', 'unknown')
                
                if self.config.log_include_user_agent:
                    context['user_agent'] = request.headers.get('User-Agent', 'unknown')
                
                if self.config.log_include_headers and self.config.log_level.value >= LogLevel.TRACE.value:
                    context['headers'] = dict(request.headers)
        except (ImportError, RuntimeError):
            # Flask not available or no request context - this is fine
            pass
        
        # Log based on configured level
        if self.config.log_level.value >= LogLevel.MINIMAL.value:
            if not allowed:
                self.throttle_logger.warning(f"Request throttled: {json.dumps(context)}")
        
        if self.config.log_level.value >= LogLevel.STANDARD.value:
            if not allowed or self.config.log_level.value >= LogLevel.DETAILED.value:
                self.throttle_logger.info(f"Throttle decision: {json.dumps(context)}")
        
        if self.config.log_level.value >= LogLevel.VERBOSE.value:
            self.throttle_logger.debug(f"Throttle analysis: {json.dumps(context, indent=2)}")
        
        if self.config.log_level.value >= LogLevel.TRACE.value:
            self.throttle_logger.debug(f"Full throttle trace: {json.dumps(context, indent=2)}")
    
    def should_throttle_request(self, endpoint: str = None, user_id: str = None) -> tuple[bool, Optional[ThrottleReason], float]:
        """
        Check if a request should be throttled.
        
        Args:
            endpoint: API endpoint being accessed
            user_id: User making the request
            
        Returns:
            tuple: (should_throttle, reason, wait_time_seconds)
        """
        start_time = time.time()
        additional_info = {}
        
        # Check system load first
        load_reason = self._should_throttle_by_load()
        if load_reason:
            self._log_throttle_decision(
                False, load_reason, endpoint, user_id, 
                additional_info={'check_time': f"{(time.time() - start_time)*1000:.1f}ms"}
            )
            return True, load_reason, 5.0  # 5 second wait for system load
        
        # Check global token bucket
        global_key = self._get_bucket_key("global", "global")
        global_bucket = self._get_or_create_bucket(global_key)
        
        if not global_bucket.consume():
            wait_time = global_bucket.get_wait_time()
            self._log_throttle_decision(
                False, ThrottleReason.BURST_LIMIT, endpoint, user_id, wait_time,
                additional_info={'bucket': 'global', 'check_time': f"{(time.time() - start_time)*1000:.1f}ms"}
            )
            return True, ThrottleReason.BURST_LIMIT, wait_time
        
        # Check endpoint-specific limits
        if endpoint and endpoint in self.config.endpoint_limits:
            endpoint_key = self._get_bucket_key(endpoint, "endpoint")
            endpoint_bucket = self._get_or_create_bucket(endpoint_key)
            
            if not endpoint_bucket.consume():
                wait_time = endpoint_bucket.get_wait_time()
                self._log_throttle_decision(
                    False, ThrottleReason.ENDPOINT_OVERLOAD, endpoint, user_id, wait_time,
                    additional_info={'bucket': 'endpoint', 'check_time': f"{(time.time() - start_time)*1000:.1f}ms"}
                )
                return True, ThrottleReason.ENDPOINT_OVERLOAD, wait_time
        
        # Check user-specific limits
        if user_id:
            user_key = self._get_bucket_key(user_id, "user")
            user_bucket = self._get_or_create_bucket(user_key)
            
            if not user_bucket.consume():
                wait_time = user_bucket.get_wait_time()
                self._log_throttle_decision(
                    False, ThrottleReason.USER_ABUSE, endpoint, user_id, wait_time,
                    additional_info={'bucket': 'user', 'check_time': f"{(time.time() - start_time)*1000:.1f}ms"}
                )
                return True, ThrottleReason.USER_ABUSE, wait_time
        
        # Check circuit breaker for endpoint
        if endpoint:
            if endpoint not in self.circuit_breakers:
                self.circuit_breakers[endpoint] = CircuitBreaker(
                    self.config.failure_threshold,
                    self.config.timeout_seconds
                )
            
            if not self.circuit_breakers[endpoint].should_allow_request():
                self._log_throttle_decision(
                    False, ThrottleReason.CIRCUIT_BREAKER, endpoint, user_id,
                    additional_info={'circuit_state': 'open', 'check_time': f"{(time.time() - start_time)*1000:.1f}ms"}
                )
                return True, ThrottleReason.CIRCUIT_BREAKER, self.config.timeout_seconds
        
        # Request allowed
        self._log_throttle_decision(
            True, None, endpoint, user_id,
            additional_info={'check_time': f"{(time.time() - start_time)*1000:.1f}ms"}
        )
        return False, None, 0.0
    
    def record_request_result(self, endpoint: str, success: bool):
        """Record the result of a request for circuit breaker logic."""
        if endpoint not in self.circuit_breakers:
            return
        
        if success:
            self.circuit_breakers[endpoint].record_success()
        else:
            self.circuit_breakers[endpoint].record_failure()
    
    def get_throttle_stats(self) -> Dict[str, Any]:
        """Get current throttling statistics."""
        stats = {
            'config': {
                'bucket_size': self.config.bucket_size,
                'refill_rate': self.config.refill_rate,
                'log_level': self.config.log_level.name
            },
            'buckets': {},
            'circuit_breakers': {},
            'system_load': self._get_system_load()
        }
        
        # Bucket stats
        for key, bucket in self.buckets.items():
            stats['buckets'][key] = {
                'current_tokens': bucket.tokens,
                'bucket_size': bucket.bucket_size,
                'refill_rate': bucket.refill_rate
            }
        
        # Circuit breaker stats
        for key, cb in self.circuit_breakers.items():
            stats['circuit_breakers'][key] = {
                'state': cb.state,
                'failure_count': cb.failure_count,
                'failure_threshold': cb.failure_threshold
            }
        
        return stats

# Global throttler instance
_global_throttler: Optional[RequestThrottler] = None

def get_throttler() -> RequestThrottler:
    """Get the global throttler instance."""
    global _global_throttler
    if _global_throttler is None:
        _global_throttler = RequestThrottler()
    return _global_throttler

def configure_throttling(config: ThrottleConfig):
    """Configure the global throttling system."""
    global _global_throttler
    _global_throttler = RequestThrottler(config)

def throttle_request(endpoint: str = None, user_id_func: Callable = None):
    """
    Decorator to add request throttling to Flask routes.
    
    Args:
        endpoint: Endpoint name for throttling (defaults to route path)
        user_id_func: Function to extract user ID from request
        
    Usage:
        @app.route('/api/expensive')
        @throttle_request(endpoint='expensive_api')
        def expensive_endpoint():
            return jsonify({'result': 'expensive computation'})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            throttler = get_throttler()
            
            # Determine endpoint name
            ep_name = endpoint or getattr(request, 'endpoint', f.__name__)
            
            # Extract user ID if function provided
            user_id = None
            if user_id_func:
                try:
                    user_id = user_id_func()
                except Exception as e:
                    logger.warning(f"Error extracting user ID: {e}")
            
            # Check if request should be throttled
            should_throttle, reason, wait_time = throttler.should_throttle_request(ep_name, user_id)
            
            if should_throttle:
                response_data = {
                    'error': 'Request throttled',
                    'reason': reason.value if reason else 'unknown',
                    'retry_after': wait_time,
                    'message': f'Please wait {wait_time:.1f} seconds before retrying'
                }
                
                response = jsonify(response_data)
                response.status_code = 429
                response.headers['Retry-After'] = str(int(wait_time))
                response.headers['X-RateLimit-Limit'] = str(throttler.config.bucket_size)
                response.headers['X-RateLimit-Remaining'] = '0'
                
                return response
            
            # Execute the original function
            try:
                result = f(*args, **kwargs)
                throttler.record_request_result(ep_name, True)
                return result
            except Exception as e:
                throttler.record_request_result(ep_name, False)
                raise
        
        return decorated_function
    return decorator

# Environment-based configuration
def load_throttling_config_from_env() -> ThrottleConfig:
    """Load throttling configuration from environment variables."""
    config = ThrottleConfig()
    
    # Basic settings
    config.bucket_size = int(os.getenv('THROTTLE_BUCKET_SIZE', '100'))
    config.refill_rate = float(os.getenv('THROTTLE_REFILL_RATE', '10.0'))
    
    # System load thresholds
    config.cpu_threshold = float(os.getenv('THROTTLE_CPU_THRESHOLD', '80.0'))
    config.memory_threshold = float(os.getenv('THROTTLE_MEMORY_THRESHOLD', '85.0'))
    
    # Circuit breaker settings
    config.failure_threshold = int(os.getenv('THROTTLE_FAILURE_THRESHOLD', '10'))
    config.timeout_seconds = int(os.getenv('THROTTLE_TIMEOUT_SECONDS', '60'))
    
    # Logging configuration
    log_level_str = os.getenv('THROTTLE_LOG_LEVEL', 'STANDARD').upper()
    try:
        config.log_level = LogLevel[log_level_str]
    except KeyError:
        config.log_level = LogLevel.STANDARD
    
    config.log_blocked_only = os.getenv('THROTTLE_LOG_BLOCKED_ONLY', 'false').lower() == 'true'
    config.log_include_headers = os.getenv('THROTTLE_LOG_INCLUDE_HEADERS', 'false').lower() == 'true'
    config.log_include_user_agent = os.getenv('THROTTLE_LOG_INCLUDE_USER_AGENT', 'true').lower() == 'true'
    
    # Endpoint limits from environment (JSON format)
    endpoint_limits_str = os.getenv('THROTTLE_ENDPOINT_LIMITS', '{}')
    try:
        config.endpoint_limits = json.loads(endpoint_limits_str)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in THROTTLE_ENDPOINT_LIMITS, using defaults")
        config.endpoint_limits = {}
    
    return config

# CLI for testing throttling
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test the throttling system
        config = ThrottleConfig(
            bucket_size=5,
            refill_rate=1.0,
            log_level=LogLevel.VERBOSE
        )
        
        throttler = RequestThrottler(config)
        
        print("Testing request throttling...")
        print(f"Bucket size: {config.bucket_size}, Refill rate: {config.refill_rate}/sec")
        
        # Simulate rapid requests
        for i in range(10):
            should_throttle, reason, wait_time = throttler.should_throttle_request(
                "test_endpoint", f"user_{i % 3}"
            )
            
            if should_throttle:
                print(f"Request {i+1}: THROTTLED ({reason.value if reason else 'unknown'}) - wait {wait_time:.1f}s")
            else:
                print(f"Request {i+1}: ALLOWED")
            
            time.sleep(0.1)  # Brief pause between requests
        
        print("\nThrottling stats:")
        stats = throttler.get_throttle_stats()
        print(json.dumps(stats, indent=2, default=str)) 