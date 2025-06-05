#!/usr/bin/env python3
"""
Load Testing Framework for Concurrent Recommendations - TODO #27c

This module provides comprehensive load testing capabilities specifically designed for
recommendation algorithm performance under realistic production scenarios. It extends
the existing performance benchmarking infrastructure with advanced load patterns,
realistic user behavior simulation, and comprehensive metrics collection.

Key Features:
- Realistic load patterns (gradual ramp-up, burst traffic, sustained load)
- Multi-tier user simulation (new users, active users, premium users)
- Advanced metrics collection (latency percentiles, throughput, quality impact)
- Resource monitoring (CPU, memory, database connections)
- Integration with existing performance benchmarking system
- Production-grade reporting and visualization
"""

import asyncio
import time
import json
import logging
import statistics
import psutil
import random
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import requests
import threading
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.connection import get_db_connection, get_cursor
from core.ranking_algorithm import generate_rankings_for_user
from utils.performance_benchmarking import PerformanceBenchmark
from utils.recommendation_metrics import collect_recommendation_quality_metrics

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LoadTestConfiguration:
    """Configuration for load testing scenarios."""
    test_name: str
    test_type: str  # baseline, ramp_up, burst, sustained, stress
    duration_seconds: int
    
    # User configuration
    concurrent_users: int
    ramp_up_duration: int = 0  # Seconds to gradually reach max users
    user_spawn_rate: float = 1.0  # Users per second during ramp-up
    
    # Request patterns
    requests_per_user: int = 10
    request_interval_min: float = 1.0  # Minimum seconds between requests
    request_interval_max: float = 3.0  # Maximum seconds between requests
    think_time: float = 0.5  # Additional think time between requests
    
    # Algorithm parameters
    recommendation_limit: int = 20
    diversity_weight: float = 0.3
    recency_weight: float = 0.2
    
    # Quality settings
    collect_quality_metrics: bool = True
    quality_sampling_rate: float = 0.2  # Sample 20% of requests for quality
    
    # Resource monitoring
    resource_sampling_interval: float = 1.0  # Seconds between resource samples
    
    # Advanced settings
    enable_cache_warming: bool = True
    simulate_database_load: bool = True
    failure_injection_rate: float = 0.0  # Percentage of requests to artificially fail


@dataclass
class UserProfile:
    """Defines characteristics of different user types for realistic simulation."""
    profile_type: str  # new_user, casual_user, active_user, power_user
    interaction_count_range: Tuple[int, int]
    request_frequency_multiplier: float
    recommendation_limit_preference: int
    quality_sensitivity: float  # How much quality degradation affects user behavior


@dataclass
class LoadTestResult:
    """Comprehensive results from a load test execution."""
    test_config: LoadTestConfiguration
    start_time: datetime
    end_time: datetime
    
    # Request metrics
    total_requests: int
    successful_requests: int
    failed_requests: int
    
    # Latency metrics (milliseconds)
    latencies: List[float] = field(default_factory=list)
    mean_latency: float = 0.0
    p50_latency: float = 0.0
    p90_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    max_latency: float = 0.0
    
    # Throughput metrics
    requests_per_second: float = 0.0
    peak_requests_per_second: float = 0.0
    
    # Resource metrics
    resource_samples: List[Dict[str, float]] = field(default_factory=list)
    avg_cpu_percent: float = 0.0
    peak_cpu_percent: float = 0.0
    avg_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    memory_delta_mb: float = 0.0
    
    # Quality metrics
    quality_measurements: List[Dict[str, float]] = field(default_factory=list)
    avg_diversity_score: float = 0.0
    avg_freshness_score: float = 0.0
    avg_engagement_score: float = 0.0
    quality_degradation_rate: float = 0.0
    
    # Advanced metrics
    user_satisfaction_score: float = 0.0
    cache_hit_rate: float = 0.0
    database_query_count: int = 0
    error_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Time series data for visualization
    throughput_timeline: List[Tuple[datetime, float]] = field(default_factory=list)
    latency_timeline: List[Tuple[datetime, float]] = field(default_factory=list)
    resource_timeline: List[Tuple[datetime, Dict[str, float]]] = field(default_factory=list)
    
    def calculate_derived_metrics(self):
        """Calculate derived metrics from collected data."""
        # Latency percentiles
        if self.latencies:
            self.mean_latency = statistics.mean(self.latencies)
            self.latencies.sort()
            n = len(self.latencies)
            
            if n >= 2:
                self.p50_latency = self.latencies[int(n * 0.5)]
            if n >= 10:
                self.p90_latency = self.latencies[int(n * 0.9)]
            if n >= 20:
                self.p95_latency = self.latencies[int(n * 0.95)]
            if n >= 100:
                self.p99_latency = self.latencies[int(n * 0.99)]
            
            self.max_latency = max(self.latencies)
        
        # Throughput
        test_duration = (self.end_time - self.start_time).total_seconds()
        if test_duration > 0:
            self.requests_per_second = self.successful_requests / test_duration
        
        # Resource metrics
        if self.resource_samples:
            self.avg_cpu_percent = statistics.mean([s.get('cpu_percent', 0) for s in self.resource_samples])
            self.peak_cpu_percent = max([s.get('cpu_percent', 0) for s in self.resource_samples])
            self.avg_memory_mb = statistics.mean([s.get('memory_mb', 0) for s in self.resource_samples])
            self.peak_memory_mb = max([s.get('memory_mb', 0) for s in self.resource_samples])
            
            if len(self.resource_samples) >= 2:
                initial_memory = self.resource_samples[0].get('memory_mb', 0)
                final_memory = self.resource_samples[-1].get('memory_mb', 0)
                self.memory_delta_mb = final_memory - initial_memory
        
        # Quality metrics
        if self.quality_measurements:
            self.avg_diversity_score = statistics.mean([q.get('diversity_score', 0) for q in self.quality_measurements])
            self.avg_freshness_score = statistics.mean([q.get('freshness_score', 0) for q in self.quality_measurements])
            self.avg_engagement_score = statistics.mean([q.get('engagement_score', 0) for q in self.quality_measurements])
        
        # Calculate user satisfaction (composite metric)
        self.user_satisfaction_score = self._calculate_user_satisfaction()
    
    def _calculate_user_satisfaction(self) -> float:
        """Calculate composite user satisfaction score based on performance and quality."""
        # Performance component (0-1, higher is better)
        performance_score = 0.0
        if self.mean_latency > 0:
            # Score decreases exponentially with latency
            performance_score = max(0, min(1, 2.0 - (self.mean_latency / 100.0)))
        
        # Quality component (0-1, higher is better)
        quality_score = (self.avg_diversity_score + self.avg_freshness_score + self.avg_engagement_score) / 3.0
        
        # Reliability component (0-1, higher is better)
        reliability_score = self.successful_requests / max(self.total_requests, 1)
        
        # Weighted composite score
        return (performance_score * 0.4 + quality_score * 0.3 + reliability_score * 0.3)


class ResourceMonitor:
    """Real-time system resource monitoring during load tests."""
    
    def __init__(self, sampling_interval: float = 1.0):
        self.sampling_interval = sampling_interval
        self.samples: List[Dict[str, float]] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
    def start_monitoring(self):
        """Start resource monitoring in background thread."""
        self.monitoring = True
        self.samples.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring:
            try:
                sample = {
                    'timestamp': time.time(),
                    'cpu_percent': psutil.cpu_percent(interval=None),
                    'memory_mb': psutil.virtual_memory().used / (1024 * 1024),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_io_read_mb': psutil.disk_io_counters().read_bytes / (1024 * 1024) if psutil.disk_io_counters() else 0,
                    'disk_io_write_mb': psutil.disk_io_counters().write_bytes / (1024 * 1024) if psutil.disk_io_counters() else 0,
                    'network_sent_mb': psutil.net_io_counters().bytes_sent / (1024 * 1024) if psutil.net_io_counters() else 0,
                    'network_recv_mb': psutil.net_io_counters().bytes_recv / (1024 * 1024) if psutil.net_io_counters() else 0
                }
                self.samples.append(sample)
                time.sleep(self.sampling_interval)
            except Exception as e:
                logger.warning(f"Error collecting resource sample: {e}")
                time.sleep(self.sampling_interval)
    
    def get_samples(self) -> List[Dict[str, float]]:
        """Get all collected resource samples."""
        return self.samples.copy()


class LoadTestingFramework:
    """Comprehensive load testing framework for recommendation algorithms."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # User profiles for realistic simulation
        self.user_profiles = {
            'new_user': UserProfile(
                profile_type='new_user',
                interaction_count_range=(0, 5),
                request_frequency_multiplier=0.5,
                recommendation_limit_preference=10,
                quality_sensitivity=0.3
            ),
            'casual_user': UserProfile(
                profile_type='casual_user', 
                interaction_count_range=(5, 50),
                request_frequency_multiplier=1.0,
                recommendation_limit_preference=15,
                quality_sensitivity=0.6
            ),
            'active_user': UserProfile(
                profile_type='active_user',
                interaction_count_range=(50, 200),
                request_frequency_multiplier=1.5,
                recommendation_limit_preference=20,
                quality_sensitivity=0.8
            ),
            'power_user': UserProfile(
                profile_type='power_user',
                interaction_count_range=(200, 1000),
                request_frequency_multiplier=2.0,
                recommendation_limit_preference=30,
                quality_sensitivity=0.9
            )
        }
    
    def get_test_users_by_profile(self, profile_type: str, count: int) -> List[str]:
        """Get test users matching the specified profile characteristics."""
        profile = self.user_profiles.get(profile_type)
        if not profile:
            raise ValueError(f"Unknown profile type: {profile_type}")
        
        min_interactions, max_interactions = profile.interaction_count_range
        
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                cursor.execute("""
                    SELECT user_alias, COUNT(*) as interaction_count
                    FROM interactions 
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY user_alias 
                    HAVING COUNT(*) BETWEEN %s AND %s
                    ORDER BY RANDOM() 
                    LIMIT %s
                """, (min_interactions, max_interactions, count))
                
                return [row[0] for row in cursor.fetchall()]
    
    def create_mixed_user_set(self, total_users: int) -> List[Tuple[str, str]]:
        """Create a realistic mix of user profiles for load testing."""
        # Distribution: 20% new, 40% casual, 30% active, 10% power
        new_count = int(total_users * 0.2)
        casual_count = int(total_users * 0.4)
        active_count = int(total_users * 0.3)
        power_count = total_users - new_count - casual_count - active_count
        
        users_with_profiles = []
        
        for profile_type, count in [
            ('new_user', new_count),
            ('casual_user', casual_count),
            ('active_user', active_count),
            ('power_user', power_count)
        ]:
            if count > 0:
                profile_users = self.get_test_users_by_profile(profile_type, count)
                for user_id in profile_users:
                    users_with_profiles.append((user_id, profile_type))
        
        # Fill any gaps with casual users
        while len(users_with_profiles) < total_users:
            users_with_profiles.append((f"fallback_user_{len(users_with_profiles)}", 'casual_user'))
        
        return users_with_profiles[:total_users]
    
    @contextmanager
    def _performance_monitoring(self, config: LoadTestConfiguration):
        """Context manager for comprehensive performance monitoring."""
        resource_monitor = ResourceMonitor(config.resource_sampling_interval)
        
        # Prepare result container
        result = LoadTestResult(
            test_config=config,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            total_requests=0,
            successful_requests=0,
            failed_requests=0
        )
        
        # Start monitoring
        resource_monitor.start_monitoring()
        
        try:
            yield result, resource_monitor
        finally:
            # Stop monitoring and collect final data
            resource_monitor.stop_monitoring()
            result.resource_samples = resource_monitor.get_samples()
            result.end_time = datetime.utcnow()
            result.calculate_derived_metrics()
    
    def simulate_user_session(self, user_id: str, profile_type: str, 
                             config: LoadTestConfiguration, 
                             result: LoadTestResult) -> Dict[str, Any]:
        """Simulate a realistic user session with the recommendation system."""
        profile = self.user_profiles[profile_type]
        session_results = {
            'user_id': user_id,
            'profile_type': profile_type,
            'requests_made': 0,
            'requests_successful': 0,
            'latencies': [],
            'quality_samples': []
        }
        
        # Adjust request count based on user profile
        adjusted_requests = int(config.requests_per_user * profile.request_frequency_multiplier)
        adjusted_limit = min(profile.recommendation_limit_preference, config.recommendation_limit)
        
        for request_num in range(adjusted_requests):
            try:
                # Simulate thinking time
                think_time = random.uniform(
                    config.request_interval_min, 
                    config.request_interval_max
                ) + config.think_time
                time.sleep(think_time)
                
                # Check if test should continue
                test_elapsed = (datetime.utcnow() - result.start_time).total_seconds()
                if test_elapsed >= config.duration_seconds:
                    break
                
                # Make recommendation request
                start_time = time.perf_counter()
                
                try:
                    rankings = generate_rankings_for_user(
                        user_id, 
                        limit=adjusted_limit,
                        diversity_weight=config.diversity_weight,
                        recency_weight=config.recency_weight
                    )
                    
                    request_latency = (time.perf_counter() - start_time) * 1000  # Convert to ms
                    
                    # Record successful request
                    session_results['requests_successful'] += 1
                    session_results['latencies'].append(request_latency)
                    result.latencies.append(request_latency)
                    
                    # Quality metrics sampling
                    if (config.collect_quality_metrics and 
                        random.random() < config.quality_sampling_rate and 
                        rankings):
                        
                        try:
                            quality_metrics = collect_recommendation_quality_metrics(
                                user_id, rankings, f"load_test_{config.test_name}"
                            )
                            if quality_metrics:
                                session_results['quality_samples'].append(quality_metrics)
                                result.quality_measurements.append(quality_metrics)
                        except Exception as e:
                            self.logger.debug(f"Quality metrics collection failed for {user_id}: {e}")
                
                except Exception as e:
                    # Record failed request
                    result.failed_requests += 1
                    error_type = type(e).__name__
                    result.error_distribution[error_type] = result.error_distribution.get(error_type, 0) + 1
                    self.logger.debug(f"Request failed for {user_id}: {e}")
                
                session_results['requests_made'] += 1
                result.total_requests += 1
                
                # Failure injection for testing error handling
                if random.random() < config.failure_injection_rate:
                    result.failed_requests += 1
                    result.error_distribution['injected_failure'] = result.error_distribution.get('injected_failure', 0) + 1
                
            except Exception as e:
                self.logger.error(f"Unexpected error in user session {user_id}: {e}")
                break
        
        return session_results
    
    def execute_load_test(self, config: LoadTestConfiguration) -> LoadTestResult:
        """Execute a comprehensive load test with the given configuration."""
        self.logger.info(f"Starting load test: {config.test_name} ({config.test_type})")
        
        with self._performance_monitoring(config) as (result, resource_monitor):
            # Initialize counters
            result.total_requests = 0
            result.successful_requests = 0
            result.failed_requests = 0
            
            # Create user set
            users_with_profiles = self.create_mixed_user_set(config.concurrent_users)
            self.logger.info(f"Created user set: {len(users_with_profiles)} users across profiles")
            
            # Cache warming if enabled
            if config.enable_cache_warming:
                self._warm_cache(users_with_profiles[:5])  # Warm with small subset
            
            # Execute load test pattern based on type
            if config.test_type == "ramp_up":
                user_sessions = self._execute_ramp_up_test(config, users_with_profiles, result)
            elif config.test_type == "burst":
                user_sessions = self._execute_burst_test(config, users_with_profiles, result)
            elif config.test_type == "sustained":
                user_sessions = self._execute_sustained_test(config, users_with_profiles, result)
            elif config.test_type == "stress":
                user_sessions = self._execute_stress_test(config, users_with_profiles, result)
            else:  # baseline
                user_sessions = self._execute_baseline_test(config, users_with_profiles, result)
            
            # Calculate final metrics
            result.successful_requests = result.total_requests - result.failed_requests
            
            self.logger.info(f"Load test completed: {result.successful_requests}/{result.total_requests} successful requests")
            
        return result
    
    def _warm_cache(self, warm_up_users: List[Tuple[str, str]]):
        """Warm up caches with representative requests."""
        self.logger.info("Warming caches...")
        for user_id, profile_type in warm_up_users:
            try:
                generate_rankings_for_user(user_id, limit=10)
            except Exception as e:
                self.logger.debug(f"Cache warming failed for {user_id}: {e}")
    
    def _execute_baseline_test(self, config: LoadTestConfiguration, 
                              users_with_profiles: List[Tuple[str, str]], 
                              result: LoadTestResult) -> List[Dict]:
        """Execute baseline test with all users starting simultaneously."""
        with ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
            futures = [
                executor.submit(self.simulate_user_session, user_id, profile_type, config, result)
                for user_id, profile_type in users_with_profiles
            ]
            
            return [future.result() for future in as_completed(futures)]
    
    def _execute_ramp_up_test(self, config: LoadTestConfiguration, 
                             users_with_profiles: List[Tuple[str, str]], 
                             result: LoadTestResult) -> List[Dict]:
        """Execute ramp-up test with gradual user introduction."""
        self.logger.info(f"Ramp-up test: {config.concurrent_users} users over {config.ramp_up_duration} seconds")
        
        user_sessions = []
        spawn_interval = config.ramp_up_duration / max(config.concurrent_users, 1)
        
        with ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
            futures = []
            
            for i, (user_id, profile_type) in enumerate(users_with_profiles):
                # Calculate spawn time
                spawn_delay = i * spawn_interval
                
                # Submit user session with delay
                future = executor.submit(self._delayed_user_session, spawn_delay, user_id, profile_type, config, result)
                futures.append(future)
            
            user_sessions = [future.result() for future in as_completed(futures)]
        
        return user_sessions
    
    def _delayed_user_session(self, delay: float, user_id: str, profile_type: str, 
                             config: LoadTestConfiguration, result: LoadTestResult) -> Dict:
        """Execute user session after specified delay."""
        time.sleep(delay)
        return self.simulate_user_session(user_id, profile_type, config, result)
    
    def _execute_burst_test(self, config: LoadTestConfiguration, 
                           users_with_profiles: List[Tuple[str, str]], 
                           result: LoadTestResult) -> List[Dict]:
        """Execute burst test with rapid user introduction."""
        self.logger.info(f"Burst test: {config.concurrent_users} users in rapid succession")
        
        # Start with small number, then burst to full capacity
        initial_users = min(2, config.concurrent_users)
        burst_users = config.concurrent_users - initial_users
        
        with ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
            futures = []
            
            # Start initial users immediately
            for user_id, profile_type in users_with_profiles[:initial_users]:
                future = executor.submit(self.simulate_user_session, user_id, profile_type, config, result)
                futures.append(future)
            
            # Brief delay before burst
            time.sleep(2)
            
            # Burst the remaining users
            for user_id, profile_type in users_with_profiles[initial_users:]:
                future = executor.submit(self.simulate_user_session, user_id, profile_type, config, result)
                futures.append(future)
            
            return [future.result() for future in as_completed(futures)]
    
    def _execute_sustained_test(self, config: LoadTestConfiguration, 
                               users_with_profiles: List[Tuple[str, str]], 
                               result: LoadTestResult) -> List[Dict]:
        """Execute sustained load test with consistent user activity."""
        self.logger.info(f"Sustained test: {config.concurrent_users} users for {config.duration_seconds} seconds")
        
        # For sustained tests, we want continuous activity
        # Increase requests per user and extend intervals
        sustained_config = LoadTestConfiguration(
            **{**config.__dict__, 
               'requests_per_user': max(config.requests_per_user, config.duration_seconds // 10),
               'request_interval_min': max(config.request_interval_min, 2.0),
               'request_interval_max': max(config.request_interval_max, 5.0)}
        )
        
        return self._execute_baseline_test(sustained_config, users_with_profiles, result)
    
    def _execute_stress_test(self, config: LoadTestConfiguration, 
                            users_with_profiles: List[Tuple[str, str]], 
                            result: LoadTestResult) -> List[Dict]:
        """Execute stress test to find system breaking points."""
        self.logger.info(f"Stress test: {config.concurrent_users} users with aggressive patterns")
        
        # For stress tests, increase request frequency and reduce think time
        stress_config = LoadTestConfiguration(
            **{**config.__dict__, 
               'requests_per_user': config.requests_per_user * 2,
               'request_interval_min': 0.1,
               'request_interval_max': 0.5,
               'think_time': 0.1}
        )
        
        return self._execute_baseline_test(stress_config, users_with_profiles, result)
    
    def save_test_result(self, result: LoadTestResult) -> int:
        """Save load test result to the performance_benchmarks table."""
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                cursor.execute("""
                    INSERT INTO performance_benchmarks (
                        name, description, benchmark_type, test_timestamp,
                        concurrent_users, test_duration_seconds, total_requests,
                        p50_latency, p95_latency, p99_latency, max_latency,
                        requests_per_second, error_rate,
                        avg_cpu_usage, peak_cpu_usage, avg_memory_mb, peak_memory_mb,
                        avg_db_query_time, db_connections_used,
                        algorithm_config, environment_info
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id
                """, (
                    result.test_config.test_name,
                    f"Load test: {result.test_config.test_type}",
                    "load_test",
                    result.start_time,
                    result.test_config.concurrent_users,
                    result.test_config.duration_seconds,
                    result.total_requests,
                    result.p50_latency,
                    result.p95_latency,
                    result.p99_latency,
                    result.max_latency,
                    result.requests_per_second,
                    result.failed_requests / max(result.total_requests, 1),
                    result.avg_cpu_percent,
                    result.peak_cpu_percent,
                    result.avg_memory_mb,
                    result.peak_memory_mb,
                    0.0,  # avg_db_query_time - TODO: implement
                    1,    # db_connections_used - TODO: implement
                    json.dumps({
                        'diversity_weight': result.test_config.diversity_weight,
                        'recency_weight': result.test_config.recency_weight,
                        'recommendation_limit': result.test_config.recommendation_limit,
                        'avg_diversity_score': result.avg_diversity_score,
                        'avg_freshness_score': result.avg_freshness_score,
                        'user_satisfaction_score': result.user_satisfaction_score
                    }),
                    json.dumps({
                        'test_type': result.test_config.test_type,
                        'ramp_up_duration': result.test_config.ramp_up_duration,
                        'memory_delta_mb': result.memory_delta_mb,
                        'quality_measurements_count': len(result.quality_measurements),
                        'error_distribution': result.error_distribution
                    })
                ))
                
                test_id = cursor.fetchone()[0]
                conn.commit()
                return test_id


# Predefined load test scenarios
class LoadTestScenarios:
    """Collection of predefined load test scenarios for common use cases."""
    
    @staticmethod
    def baseline_performance() -> LoadTestConfiguration:
        """Standard baseline performance test."""
        return LoadTestConfiguration(
            test_name="baseline_performance",
            test_type="baseline",
            duration_seconds=300,  # 5 minutes
            concurrent_users=10,
            requests_per_user=20,
            request_interval_min=2.0,
            request_interval_max=5.0,
            collect_quality_metrics=True,
            quality_sampling_rate=0.5
        )
    
    @staticmethod
    def peak_hour_simulation() -> LoadTestConfiguration:
        """Simulate peak usage hours."""
        return LoadTestConfiguration(
            test_name="peak_hour_simulation",
            test_type="sustained",
            duration_seconds=1800,  # 30 minutes
            concurrent_users=50,
            requests_per_user=40,
            request_interval_min=1.0,
            request_interval_max=3.0,
            collect_quality_metrics=True,
            quality_sampling_rate=0.3
        )
    
    @staticmethod
    def viral_content_burst() -> LoadTestConfiguration:
        """Simulate viral content causing traffic burst."""
        return LoadTestConfiguration(
            test_name="viral_content_burst",
            test_type="burst",
            duration_seconds=600,  # 10 minutes
            concurrent_users=100,
            requests_per_user=15,
            request_interval_min=0.5,
            request_interval_max=2.0,
            collect_quality_metrics=True,
            quality_sampling_rate=0.2
        )
    
    @staticmethod
    def gradual_ramp_up() -> LoadTestConfiguration:
        """Gradual traffic increase simulation."""
        return LoadTestConfiguration(
            test_name="gradual_ramp_up",
            test_type="ramp_up",
            duration_seconds=900,  # 15 minutes
            concurrent_users=75,
            ramp_up_duration=300,  # 5 minute ramp
            requests_per_user=25,
            request_interval_min=1.5,
            request_interval_max=4.0,
            collect_quality_metrics=True,
            quality_sampling_rate=0.4
        )
    
    @staticmethod
    def stress_test() -> LoadTestConfiguration:
        """Stress test to find breaking points."""
        return LoadTestConfiguration(
            test_name="stress_test",
            test_type="stress",
            duration_seconds=600,  # 10 minutes
            concurrent_users=200,
            requests_per_user=30,
            request_interval_min=0.2,
            request_interval_max=1.0,
            think_time=0.1,
            collect_quality_metrics=False,  # Skip quality to focus on performance
            enable_cache_warming=True
        )


if __name__ == "__main__":
    # Command line interface for running load tests
    import argparse
    
    parser = argparse.ArgumentParser(description="Run load tests for recommendation algorithm")
    parser.add_argument("--scenario", choices=["baseline", "peak", "burst", "ramp", "stress", "all"], 
                       default="baseline", help="Load test scenario to run")
    parser.add_argument("--users", type=int, help="Override concurrent users count")
    parser.add_argument("--duration", type=int, help="Override test duration in seconds")
    parser.add_argument("--save", action="store_true", help="Save results to database")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    framework = LoadTestingFramework()
    
    # Map scenario names to configurations
    scenarios = {
        "baseline": LoadTestScenarios.baseline_performance(),
        "peak": LoadTestScenarios.peak_hour_simulation(),
        "burst": LoadTestScenarios.viral_content_burst(),
        "ramp": LoadTestScenarios.gradual_ramp_up(),
        "stress": LoadTestScenarios.stress_test()
    }
    
    if args.scenario == "all":
        test_configs = list(scenarios.values())
    else:
        test_configs = [scenarios[args.scenario]]
    
    # Apply overrides
    for config in test_configs:
        if args.users:
            config.concurrent_users = args.users
        if args.duration:
            config.duration_seconds = args.duration
    
    # Execute tests
    results = []
    for config in test_configs:
        try:
            logger.info(f"Running load test: {config.test_name}")
            result = framework.execute_load_test(config)
            results.append(result)
            
            # Print summary
            print(f"\n{config.test_name} Results:")
            print(f"  Total Requests: {result.total_requests}")
            print(f"  Success Rate: {result.successful_requests/max(result.total_requests,1):.1%}")
            print(f"  Average Latency: {result.mean_latency:.1f}ms")
            print(f"  P95 Latency: {result.p95_latency:.1f}ms")
            print(f"  Throughput: {result.requests_per_second:.1f} req/s")
            print(f"  User Satisfaction: {result.user_satisfaction_score:.2f}")
            
            if args.save:
                test_id = framework.save_test_result(result)
                print(f"  Saved to database with ID: {test_id}")
                
        except Exception as e:
            logger.error(f"Load test {config.test_name} failed: {e}")
    
    if len(results) > 1:
        print(f"\nCompleted {len(results)} load test scenarios") 