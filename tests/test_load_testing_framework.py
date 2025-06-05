#!/usr/bin/env python3
"""
Test Suite for Load Testing Framework - TODO #27c

This module provides comprehensive tests for the load testing framework,
including scenario validation, performance monitoring, user simulation,
and integration with the existing benchmarking infrastructure.
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
    """Test LoadTestConfiguration dataclass and validation."""
    
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
        assert config.enable_cache_warming is True
    
    def test_advanced_configuration_options(self):
        """Test advanced configuration options."""
        config = LoadTestConfiguration(
            test_name="test_advanced",
            test_type="stress",
            duration_seconds=300,
            concurrent_users=100,
            ramp_up_duration=60,
            requests_per_user=50,
            request_interval_min=0.5,
            request_interval_max=2.0,
            think_time=0.2,
            recommendation_limit=30,
            diversity_weight=0.4,
            quality_sampling_rate=0.3,
            failure_injection_rate=0.05
        )
        
        assert config.ramp_up_duration == 60
        assert config.requests_per_user == 50
        assert config.recommendation_limit == 30
        assert config.diversity_weight == 0.4
        assert config.quality_sampling_rate == 0.3
        assert config.failure_injection_rate == 0.05


class TestUserProfile:
    """Test UserProfile dataclass and user classification."""
    
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
    """Test predefined load test scenarios."""
    
    def test_baseline_performance_scenario(self):
        """Test baseline performance scenario configuration."""
        config = LoadTestScenarios.baseline_performance()
        
        assert config.test_name == "baseline_performance"
        assert config.test_type == "baseline"
        assert config.duration_seconds == 300
        assert config.concurrent_users == 10
        assert config.requests_per_user == 20
        assert config.collect_quality_metrics is True
        assert config.quality_sampling_rate == 0.5
    
    def test_peak_hour_simulation_scenario(self):
        """Test peak hour simulation scenario."""
        config = LoadTestScenarios.peak_hour_simulation()
        
        assert config.test_name == "peak_hour_simulation"
        assert config.test_type == "sustained"
        assert config.duration_seconds == 1800  # 30 minutes
        assert config.concurrent_users == 50
        assert config.requests_per_user == 40
    
    def test_viral_content_burst_scenario(self):
        """Test viral content burst scenario."""
        config = LoadTestScenarios.viral_content_burst()
        
        assert config.test_name == "viral_content_burst"
        assert config.test_type == "burst"
        assert config.duration_seconds == 600  # 10 minutes
        assert config.concurrent_users == 100
        assert config.request_interval_min == 0.5
        assert config.request_interval_max == 2.0
    
    def test_gradual_ramp_up_scenario(self):
        """Test gradual ramp-up scenario."""
        config = LoadTestScenarios.gradual_ramp_up()
        
        assert config.test_name == "gradual_ramp_up"
        assert config.test_type == "ramp_up"
        assert config.duration_seconds == 900  # 15 minutes
        assert config.concurrent_users == 75
        assert config.ramp_up_duration == 300  # 5 minute ramp
    
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
    """Test ResourceMonitor for system resource tracking."""
    
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
            assert sample['memory_mb'] > 0


class TestLoadTestResult:
    """Test LoadTestResult dataclass and metric calculations."""
    
    def create_sample_result(self) -> LoadTestResult:
        """Create a sample load test result for testing."""
        config = LoadTestConfiguration(
            test_name="test_result",
            test_type="baseline",
            duration_seconds=60,
            concurrent_users=5
        )
        
        result = LoadTestResult(
            test_config=config,
            start_time=datetime.utcnow() - timedelta(seconds=60),
            end_time=datetime.utcnow(),
            total_requests=100,
            successful_requests=95,
            failed_requests=5
        )
        
        # Add sample latencies
        result.latencies = [10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0, 100.0, 200.0]
        
        # Add sample resource data
        result.resource_samples = [
            {'cpu_percent': 25.0, 'memory_mb': 500.0},
            {'cpu_percent': 30.0, 'memory_mb': 520.0},
            {'cpu_percent': 35.0, 'memory_mb': 540.0},
            {'cpu_percent': 40.0, 'memory_mb': 560.0}
        ]
        
        # Add sample quality data
        result.quality_measurements = [
            {'diversity_score': 0.8, 'freshness_score': 0.7, 'engagement_score': 0.9},
            {'diversity_score': 0.75, 'freshness_score': 0.65, 'engagement_score': 0.85}
        ]
        
        return result
    
    def test_result_derived_metrics_calculation(self):
        """Test calculation of derived metrics from raw data."""
        result = self.create_sample_result()
        
        # Calculate derived metrics
        result.calculate_derived_metrics()
        
        # Test latency metrics
        assert result.mean_latency == 52.5  # Mean of sample latencies
        assert result.p50_latency == 35.0   # 50th percentile (5th element in sorted list)
        assert result.p90_latency == 200.0  # 90th percentile (last element for small sample)
        assert result.max_latency == 200.0
        
        # Test throughput metrics
        assert result.requests_per_second > 0
        
        # Test resource metrics
        assert result.avg_cpu_percent == 32.5
        assert result.peak_cpu_percent == 40.0
        assert result.avg_memory_mb == 530.0
        assert result.peak_memory_mb == 560.0
        assert result.memory_delta_mb == 60.0  # 560 - 500
        
        # Test quality metrics
        assert result.avg_diversity_score == 0.775
        assert result.avg_freshness_score == 0.675
        assert result.avg_engagement_score == 0.875
        
        # Test user satisfaction score
        assert 0 <= result.user_satisfaction_score <= 1
    
    def test_user_satisfaction_calculation(self):
        """Test user satisfaction score calculation logic."""
        result = self.create_sample_result()
        result.calculate_derived_metrics()
        
        # User satisfaction should be reasonable for good performance
        assert result.user_satisfaction_score > 0.5
        
        # Test with poor performance
        result.latencies = [1000.0, 2000.0, 3000.0]  # Very high latencies
        result.failed_requests = 50  # High failure rate
        result.successful_requests = 50
        result.calculate_derived_metrics()
        
        # Should have lower satisfaction
        assert result.user_satisfaction_score < 0.5


class TestLoadTestingFramework:
    """Test main LoadTestingFramework class and functionality."""
    
    @pytest.fixture
    def framework(self):
        """Create a LoadTestingFramework instance for testing."""
        return LoadTestingFramework()
    
    def test_framework_initialization(self, framework):
        """Test framework initialization and user profiles."""
        assert hasattr(framework, 'user_profiles')
        assert len(framework.user_profiles) == 4
        assert 'new_user' in framework.user_profiles
        assert 'casual_user' in framework.user_profiles
        assert 'active_user' in framework.user_profiles
        assert 'power_user' in framework.user_profiles
        
        # Test user profile characteristics
        new_user = framework.user_profiles['new_user']
        assert new_user.interaction_count_range == (0, 5)
        assert new_user.request_frequency_multiplier == 0.5
        
        power_user = framework.user_profiles['power_user']
        assert power_user.interaction_count_range == (200, 1000)
        assert power_user.request_frequency_multiplier == 2.0
    
    @patch('utils.load_testing_framework.get_db_connection')
    def test_get_test_users_by_profile(self, mock_db, framework):
        """Test getting test users by profile type."""
        # Mock database response
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('user1',), ('user2',), ('user3',)
        ]
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        users = framework.get_test_users_by_profile('casual_user', 3)
        
        assert len(users) == 3
        assert users == ['user1', 'user2', 'user3']
        
        # Verify SQL query was called with correct parameters
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert 'BETWEEN %s AND %s' in call_args[0]
        assert call_args[1] == (5, 50, 3)  # casual_user range + count
    
    @patch('utils.load_testing_framework.get_db_connection')
    def test_create_mixed_user_set(self, mock_db, framework):
        """Test creating mixed user set with realistic distribution."""
        # Mock database to return users for each profile
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [('new_user_1',), ('new_user_2',)],      # new users (20%)
            [('casual_user_1',), ('casual_user_2',), ('casual_user_3',), ('casual_user_4',)],  # casual (40%)
            [('active_user_1',), ('active_user_2',), ('active_user_3',)],  # active (30%)
            [('power_user_1',)]  # power (10%)
        ]
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        users_with_profiles = framework.create_mixed_user_set(10)
        
        assert len(users_with_profiles) == 10
        
        # Verify distribution
        profile_counts = {}
        for user_id, profile_type in users_with_profiles:
            profile_counts[profile_type] = profile_counts.get(profile_type, 0) + 1
        
        assert profile_counts.get('new_user', 0) == 2      # 20%
        assert profile_counts.get('casual_user', 0) == 4   # 40%
        assert profile_counts.get('active_user', 0) == 3   # 30%
        assert profile_counts.get('power_user', 0) == 1    # 10%
    
    @patch('utils.load_testing_framework.generate_rankings_for_user')
    @patch('utils.load_testing_framework.collect_recommendation_quality_metrics')
    def test_simulate_user_session(self, mock_quality, mock_rankings, framework):
        """Test user session simulation with different profiles."""
        # Mock ranking generation
        mock_rankings.return_value = [
            {'post_id': '1', 'score': 0.9},
            {'post_id': '2', 'score': 0.8}
        ]
        
        # Mock quality metrics
        mock_quality.return_value = {
            'diversity_score': 0.8,
            'freshness_score': 0.7,
            'engagement_score': 0.9
        }
        
        # Create test configuration
        config = LoadTestConfiguration(
            test_name="test_session",
            test_type="baseline",
            duration_seconds=10,  # Short test
            concurrent_users=1,
            requests_per_user=3,
            request_interval_min=0.1,
            request_interval_max=0.2,
            think_time=0.1,
            collect_quality_metrics=True,
            quality_sampling_rate=1.0  # Collect from all requests
        )
        
        # Create result container
        result = LoadTestResult(
            test_config=config,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            total_requests=0,
            successful_requests=0,
            failed_requests=0
        )
        
        # Simulate session for casual user
        session_result = framework.simulate_user_session(
            'test_user', 'casual_user', config, result
        )
        
        # Verify session results
        assert session_result['user_id'] == 'test_user'
        assert session_result['profile_type'] == 'casual_user'
        assert session_result['requests_made'] >= 1
        assert session_result['requests_successful'] >= 1
        assert len(session_result['latencies']) >= 1
        assert len(session_result['quality_samples']) >= 1
        
        # Verify ranking calls were made
        assert mock_rankings.call_count >= 1
        
        # Verify quality metrics collection
        assert mock_quality.call_count >= 1
    
    @patch('utils.load_testing_framework.generate_rankings_for_user')
    def test_simulate_user_session_with_errors(self, mock_rankings, framework):
        """Test user session simulation with ranking errors."""
        # Mock ranking generation to raise exceptions
        mock_rankings.side_effect = Exception("Database connection failed")
        
        config = LoadTestConfiguration(
            test_name="test_errors",
            test_type="baseline",
            duration_seconds=5,
            concurrent_users=1,
            requests_per_user=2,
            request_interval_min=0.1,
            request_interval_max=0.2
        )
        
        result = LoadTestResult(
            test_config=config,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            total_requests=0,
            successful_requests=0,
            failed_requests=0
        )
        
        # Simulate session with errors
        session_result = framework.simulate_user_session(
            'test_user', 'casual_user', config, result
        )
        
        # Should handle errors gracefully
        assert session_result['requests_made'] >= 1
        assert session_result['requests_successful'] == 0
        assert result.failed_requests >= 1
        assert len(result.error_distribution) >= 1
    
    @patch('utils.load_testing_framework.get_db_connection')
    def test_save_test_result(self, mock_db, framework):
        """Test saving load test results to database."""
        # Mock database response
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (123,)  # Mock returned ID
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Create test result
        result = self.create_sample_result()
        result.calculate_derived_metrics()
        
        # Save result
        test_id = framework.save_test_result(result)
        
        assert test_id == 123
        
        # Verify database insert was called
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert 'INSERT INTO performance_benchmarks' in call_args[0]
        
        # Verify correct number of parameters
        assert len(call_args[1]) == 21  # Should match number of columns
    
    def create_sample_result(self) -> LoadTestResult:
        """Helper method to create sample test result."""
        config = LoadTestConfiguration(
            test_name="test_save",
            test_type="baseline",
            duration_seconds=60,
            concurrent_users=5
        )
        
        result = LoadTestResult(
            test_config=config,
            start_time=datetime.utcnow() - timedelta(seconds=60),
            end_time=datetime.utcnow(),
            total_requests=100,
            successful_requests=95,
            failed_requests=5
        )
        
        result.latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
        result.resource_samples = [
            {'cpu_percent': 30.0, 'memory_mb': 500.0}
        ]
        result.quality_measurements = [
            {'diversity_score': 0.8, 'freshness_score': 0.7, 'engagement_score': 0.9}
        ]
        
        return result


@pytest.mark.integration
class TestLoadTestingIntegration:
    """Integration tests for the complete load testing framework."""
    
    @pytest.fixture
    def framework(self):
        """Create framework instance for integration tests."""
        return LoadTestingFramework()
    
    @patch('utils.load_testing_framework.generate_rankings_for_user')
    @patch('utils.load_testing_framework.get_db_connection')
    def test_baseline_load_test_execution(self, mock_db, mock_rankings, framework):
        """Test complete baseline load test execution."""
        # Mock successful ranking generation
        mock_rankings.return_value = [
            {'post_id': '1', 'score': 0.9},
            {'post_id': '2', 'score': 0.8}
        ]
        
        # Mock user database queries
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [('user1',)],           # new users
            [('user2',), ('user3',)],  # casual users  
            [],                     # active users (empty)
            []                      # power users (empty)
        ]
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Create short test configuration
        config = LoadTestConfiguration(
            test_name="integration_baseline",
            test_type="baseline",
            duration_seconds=5,  # Very short for testing
            concurrent_users=3,
            requests_per_user=2,
            request_interval_min=0.1,
            request_interval_max=0.2,
            collect_quality_metrics=False  # Skip for faster testing
        )
        
        # Execute load test
        result = framework.execute_load_test(config)
        
        # Verify test execution
        assert result.test_config.test_name == "integration_baseline"
        assert result.total_requests >= 1
        assert result.successful_requests >= 1
        assert len(result.latencies) >= 1
        assert len(result.resource_samples) >= 1
        
        # Verify derived metrics were calculated
        assert result.mean_latency > 0
        assert result.requests_per_second > 0
        assert result.avg_cpu_percent >= 0
    
    @patch('utils.load_testing_framework.generate_rankings_for_user')
    @patch('utils.load_testing_framework.get_db_connection')
    def test_ramp_up_load_test_execution(self, mock_db, mock_rankings, framework):
        """Test ramp-up load test with gradual user introduction."""
        # Mock successful ranking generation
        mock_rankings.return_value = [{'post_id': '1', 'score': 0.9}]
        
        # Mock user database
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [],                     # new users
            [('user1',), ('user2',)],  # casual users
            [],                     # active users
            []                      # power users
        ]
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Create ramp-up test configuration
        config = LoadTestConfiguration(
            test_name="integration_ramp_up",
            test_type="ramp_up",
            duration_seconds=5,
            concurrent_users=2,
            ramp_up_duration=2,  # 2 second ramp
            requests_per_user=1,
            request_interval_min=0.1,
            request_interval_max=0.2,
            collect_quality_metrics=False
        )
        
        # Execute ramp-up test
        result = framework.execute_load_test(config)
        
        # Verify test execution
        assert result.test_config.test_type == "ramp_up"
        assert result.total_requests >= 1
        assert result.successful_requests >= 1
    
    @patch('utils.load_testing_framework.generate_rankings_for_user')
    @patch('utils.load_testing_framework.get_db_connection')
    def test_burst_load_test_execution(self, mock_db, mock_rankings, framework):
        """Test burst load test with rapid user introduction."""
        # Mock ranking generation
        mock_rankings.return_value = [{'post_id': '1', 'score': 0.9}]
        
        # Mock user database
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [],                     # new users
            [],                     # casual users
            [('user1',), ('user2',), ('user3',)],  # active users
            []                      # power users
        ]
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Create burst test configuration
        config = LoadTestConfiguration(
            test_name="integration_burst",
            test_type="burst",
            duration_seconds=5,
            concurrent_users=3,
            requests_per_user=1,
            request_interval_min=0.1,
            request_interval_max=0.2,
            collect_quality_metrics=False
        )
        
        # Execute burst test
        result = framework.execute_load_test(config)
        
        # Verify test execution
        assert result.test_config.test_type == "burst"
        assert result.total_requests >= 1


@pytest.mark.slow
class TestLoadTestingPerformance:
    """Performance tests for the load testing framework itself."""
    
    @pytest.fixture
    def framework(self):
        """Create framework for performance testing."""
        return LoadTestingFramework()
    
    @patch('utils.load_testing_framework.generate_rankings_for_user')
    @patch('utils.load_testing_framework.get_db_connection')
    def test_framework_overhead_measurement(self, mock_db, mock_rankings, framework):
        """Test that the framework itself doesn't add significant overhead."""
        # Mock very fast ranking generation
        mock_rankings.return_value = [{'post_id': '1', 'score': 0.9}]
        
        # Mock user database
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [],                     # new users
            [('user1',)],          # casual users
            [],                     # active users
            []                      # power users
        ]
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Measure framework overhead
        start_time = time.time()
        
        config = LoadTestConfiguration(
            test_name="overhead_test",
            test_type="baseline",
            duration_seconds=3,
            concurrent_users=1,
            requests_per_user=5,
            request_interval_min=0.1,
            request_interval_max=0.1,
            collect_quality_metrics=False,
            enable_cache_warming=False
        )
        
        result = framework.execute_load_test(config)
        
        total_time = time.time() - start_time
        
        # Framework overhead should be minimal compared to test duration
        assert total_time < config.duration_seconds * 2  # Less than 2x test duration
        assert result.total_requests >= 1
        
        # Latency measurements should be reasonable
        if result.latencies:
            assert all(latency < 1000 for latency in result.latencies)  # Under 1 second each


if __name__ == "__main__":
    # Run specific test suites
    import argparse
    
    parser = argparse.ArgumentParser(description="Run load testing framework tests")
    parser.add_argument("--suite", choices=["unit", "integration", "performance", "all"], 
                       default="all", help="Which test suite to run")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    pytest_args = []
    if args.verbose:
        pytest_args.append("-v")
    
    if args.suite == "unit":
        pytest_args.extend(["-k", "not integration and not slow"])
    elif args.suite == "integration":
        pytest_args.extend(["-m", "integration"])
    elif args.suite == "performance":
        pytest_args.extend(["-m", "slow"])
    
    pytest_args.append(__file__)
    
    import subprocess
    subprocess.run(["python", "-m", "pytest"] + pytest_args) 