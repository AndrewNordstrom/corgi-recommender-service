#!/usr/bin/env python3
"""Test script for request throttling system."""

import sys
import time

# Add current directory to path for imports
sys.path.append('.')

# Mock config for testing
class MockConfig:
    REDIS_URL = "redis://localhost:6379"
    REDIS_ENABLED = False

sys.modules['config'] = MockConfig()

from utils.request_throttling import ThrottleConfig, RequestThrottler, LogLevel

def test_throttling():
    """Test the request throttling system."""
    print("🧪 Testing Request Throttling System...")
    
    # Create test configuration
    config = ThrottleConfig(
        bucket_size=5,
        refill_rate=1.0,
        log_level=LogLevel.VERBOSE
    )
    
    throttler = RequestThrottler(config)
    
    print(f"📊 Configuration: Bucket size = {config.bucket_size}, Refill rate = {config.refill_rate}/sec")
    print()
    
    # Simulate rapid requests
    for i in range(10):
        should_throttle, reason, wait_time = throttler.should_throttle_request(
            "test_endpoint", f"user_{i % 3}"
        )
        
        if should_throttle:
            print(f"🚫 Request {i+1}: THROTTLED ({reason.value if reason else 'unknown'}) - wait {wait_time:.1f}s")
        else:
            print(f"✅ Request {i+1}: ALLOWED")
        
        time.sleep(0.1)  # Brief pause between requests
    
    print("\n📈 Getting throttling stats...")
    stats = throttler.get_throttle_stats()
    
    print(f"🪣 Active buckets: {len(stats['buckets'])}")
    for bucket_key, bucket_info in stats['buckets'].items():
        print(f"   - {bucket_key}: {bucket_info['current_tokens']:.1f}/{bucket_info['bucket_size']} tokens")
    
    print(f"🔧 Circuit breakers: {len(stats['circuit_breakers'])}")
    print(f"💻 System load: CPU={stats['system_load']['cpu']:.1f}%, Memory={stats['system_load']['memory']:.1f}%")
    
    print("\n✅ Throttling test completed successfully!")

if __name__ == "__main__":
    test_throttling() 