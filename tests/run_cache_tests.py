#!/usr/bin/env python3
"""
Simple test runner script that runs the cache tests with mocked dependencies
"""

import sys
import pytest

# Add a mock for Redis to avoid errors
class MockRedis:
    pass

# Add mocks to avoid importing problematic modules
sys.modules['redis'] = type('MockRedisModule', (), {'Redis': MockRedis})

# Run the tests
if __name__ == "__main__":
    sys.exit(pytest.main(["-xvs", "tests/test_cache.py::TestCacheDisabled"]))