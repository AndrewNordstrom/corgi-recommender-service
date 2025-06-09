#!/usr/bin/env python3
"""
Core Load Testing Framework Tests

Essential tests for the load testing framework covering:
- Basic configuration and validation
- Core user profiles
- Essential test scenarios
- Basic framework functionality
"""

import pytest
import time
import json
import tempfile
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.load_testing_framework import (
    LoadTestingFramework,
    LoadTestConfiguration,
    LoadTestScenarios,
    UserProfile,
    LoadTestResult,
    ResourceMonitor
)


class TestLoadTestConfiguration:
    """Test core LoadTestConfiguration functionality."""
    
    def test_basic_configuration_creation(self):
        """Test basic configuration creation with required fields."""
        config = LoadTestConfiguration(
            test_name="test_basic",
            test_type="baseline",
            duration_seconds=60,
            concurrent_users=5
        )
        
        assert config.test_name == "test_basic"
        assert config.test_type == "baseline"
        assert config.duration_seconds == 60
        assert config.concurrent_users == 5
        
        # Test default values
        assert config.ramp_up_duration == 0
        assert config.requests_per_user == 10
        assert config.request_interval_min == 1.0
        assert config.collect_quality_metrics is True


class TestUserProfile:
    """Test core UserProfile functionality."""
    
    def test_user_profile_creation(self):
        """Test user profile creation with all attributes."""
        profile = UserProfile(
            profile_type="test_user",
            interaction_count_range=(10, 100),
            request_frequency_multiplier=1.5,
            recommendation_limit_preference=25,
            quality_sensitivity=0.8
        )
        
        assert profile.profile_type == "test_user"
        assert profile.interaction_count_range == (10, 100)
        assert profile.request_frequency_multiplier == 1.5
        assert profile.recommendation_limit_preference == 25
        assert profile.quality_sensitivity == 0.8


class TestLoadTestScenarios:
    """Test core predefined load test scenarios."""
    
    def test_baseline_performance_scenario(self):
        """Test baseline performance scenario configuration."""
        config = LoadTestScenarios.baseline_performance()
        
        assert config.test_name == "baseline_performance"
        assert config.test_type == "baseline"
        assert config.duration_seconds == 300
        assert config.concurrent_users == 10
        assert config.requests_per_user == 20
        assert config.collect_quality_metrics is True
    
    def test_stress_test_scenario(self):
        """Test stress test scenario."""
        config = LoadTestScenarios.stress_test()
        
        assert config.test_name == "stress_test"
        assert config.test_type == "stress"
        assert config.duration_seconds == 600
        assert config.concurrent_users == 200
        assert config.request_interval_min == 0.2
        assert config.collect_quality_metrics is False  # Performance focus


class TestResourceMonitor:
    """Test core ResourceMonitor functionality."""
    
    def test_resource_monitor_initialization(self):
        """Test resource monitor initialization."""
        monitor = ResourceMonitor(sampling_interval=0.5)
        
        assert monitor.sampling_interval == 0.5
        assert monitor.samples == []
        assert monitor.monitoring is False
        assert monitor.monitor_thread is None
    
    def test_resource_monitor_lifecycle(self):
        """Test resource monitor start/stop lifecycle."""
        monitor = ResourceMonitor(sampling_interval=0.1)
        
        # Start monitoring
        monitor.start_monitoring()
        assert monitor.monitoring is True
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        
        # Let it collect some samples
        time.sleep(0.3)
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert monitor.monitoring is False
        
        # Should have collected samples
        samples = monitor.get_samples()
        assert len(samples) > 0
        
        # Verify sample structure
        for sample in samples:
            assert 'timestamp' in sample
            assert 'cpu_percent' in sample
            assert 'memory_mb' in sample
            assert 'memory_percent' in sample
            assert sample['cpu_percent'] >= 0


class TestLoadTestingFramework:
    """Test core LoadTestingFramework functionality."""
    
    @pytest.fixture
    def framework(self):
        """Create framework instance for testing."""
        return LoadTestingFramework()
    
    def test_framework_initialization(self, framework):
        """Test framework initialization."""
        assert framework is not None
        assert hasattr(framework, 'run_load_test')
        assert hasattr(framework, 'save_test_result')
    
    @patch('utils.load_testing_framework.get_db_connection')
    def test_create_mixed_user_set(self, mock_db, framework):
        """Test creating mixed user sets for testing."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('user1', 50), ('user2', 100), ('user3', 200)
        ]
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        users = framework.create_mixed_user_set(
            total_users=10,
            user_profiles=[
                UserProfile("light_user", (1, 50), 0.5, 10, 0.3),
                UserProfile("heavy_user", (100, 500), 2.0, 50, 0.9)
            ]
        )
        
        assert isinstance(users, list)
        assert len(users) <= 10


@pytest.mark.integration
class TestLoadTestingIntegration:
    """Test core load testing integration."""
    
    @pytest.fixture
    def framework(self):
        """Create framework instance for integration testing."""
        return LoadTestingFramework()
    
    @patch('utils.load_testing_framework.generate_rankings_for_user')
    @patch('utils.load_testing_framework.get_db_connection')
    def test_baseline_load_test_execution(self, mock_db, mock_rankings, framework):
        """Test baseline load test execution."""
        # Mock database connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [('user1', 10), ('user2', 20)]
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock ranking generation
        mock_rankings.return_value = [{"post_id": "test1", "score": 0.9}]
        
        config = LoadTestConfiguration(
            test_name="integration_test",
            test_type="baseline", 
            duration_seconds=0.1,  # Ultra-short for testing speed
            concurrent_users=1,  # Minimal users for speed
            requests_per_user=1,
            ramp_up_duration=0  # No ramp-up for speed
        )
        
        result = framework.run_load_test(config)
        
        assert isinstance(result, LoadTestResult)
        assert result.test_name == "integration_test"
        assert result.total_requests >= 0
        assert result.successful_requests >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 