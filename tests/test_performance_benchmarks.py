#!/usr/bin/env python3
"""
Automated Benchmark Test Suite for Ranking Algorithm - TODO #27b

This module provides comprehensive automated benchmarks specifically focused on the
core ranking algorithm performance, building on the existing performance infrastructure
to provide dedicated algorithm testing capabilities.

Key Features:
- Isolated algorithm performance testing
- Standardized test scenarios and data sets
- Resource utilization monitoring
- Performance regression detection
- Integration with existing benchmarking infrastructure
"""

import pytest
import time
import statistics
import psutil
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from contextlib import contextmanager
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

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
class AlgorithmBenchmarkResult:
    """Container for algorithm-specific benchmark results."""
    test_name: str
    test_timestamp: datetime
    user_count: int
    iterations: int
    
    # Latency metrics (milliseconds)
    mean_latency: float
    p50_latency: float
    p90_latency: float
    p95_latency: float
    p99_latency: float
    max_latency: float
    
    # Throughput metrics
    requests_per_second: float
    posts_processed_per_second: float
    
    # Resource metrics
    avg_cpu_percent: float
    peak_cpu_percent: float
    avg_memory_mb: float
    peak_memory_mb: float
    memory_delta_mb: float
    
    # Quality metrics
    avg_diversity_score: float
    avg_freshness_score: float
    avg_engagement_score: float
    
    # Error metrics
    error_count: int
    success_rate: float
    
    # Algorithm-specific metrics
    cache_hit_rate: float
    posts_considered: int
    avg_ranking_size: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'test_name': self.test_name,
            'test_timestamp': self.test_timestamp.isoformat(),
            'user_count': self.user_count,
            'iterations': self.iterations,
            'mean_latency': self.mean_latency,
            'p50_latency': self.p50_latency,
            'p90_latency': self.p90_latency,
            'p95_latency': self.p95_latency,
            'p99_latency': self.p99_latency,
            'max_latency': self.max_latency,
            'requests_per_second': self.requests_per_second,
            'posts_processed_per_second': self.posts_processed_per_second,
            'avg_cpu_percent': self.avg_cpu_percent,
            'peak_cpu_percent': self.peak_cpu_percent,
            'avg_memory_mb': self.avg_memory_mb,
            'peak_memory_mb': self.peak_memory_mb,
            'memory_delta_mb': self.memory_delta_mb,
            'avg_diversity_score': self.avg_diversity_score,
            'avg_freshness_score': self.avg_freshness_score,
            'avg_engagement_score': self.avg_engagement_score,
            'error_count': self.error_count,
            'success_rate': self.success_rate,
            'cache_hit_rate': self.cache_hit_rate,
            'posts_considered': self.posts_considered,
            'avg_ranking_size': self.avg_ranking_size
        }


class AlgorithmBenchmarkSuite:
    """Comprehensive automated benchmark suite for the ranking algorithm."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.performance_benchmarker = PerformanceBenchmark()
        
    @contextmanager
    def _resource_monitor(self):
        """Context manager for monitoring system resources during benchmarks."""
        class ResourceTracker:
            def __init__(self):
                self.cpu_readings = []
                self.memory_readings = []
                self.start_memory = psutil.virtual_memory().used / (1024 * 1024)  # MB
                self.start_time = time.time()
                
            def record_reading(self):
                self.cpu_readings.append(psutil.cpu_percent(interval=None))
                self.memory_readings.append(psutil.virtual_memory().used / (1024 * 1024))
                
            def get_final_metrics(self):
                end_memory = psutil.virtual_memory().used / (1024 * 1024)
                return {
                    'avg_cpu': statistics.mean(self.cpu_readings) if self.cpu_readings else 0,
                    'peak_cpu': max(self.cpu_readings) if self.cpu_readings else 0,
                    'avg_memory': statistics.mean(self.memory_readings) if self.memory_readings else 0,
                    'peak_memory': max(self.memory_readings) if self.memory_readings else 0,
                    'memory_delta': end_memory - self.start_memory
                }
        
        tracker = ResourceTracker()
        try:
            yield tracker
        finally:
            pass
    
    def _get_test_users(self, user_type: str = "mixed", count: int = 50) -> List[str]:
        """Get test users based on specified criteria."""
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                if user_type == "high_activity":
                    # Users with many interactions
                    cursor.execute("""
                        SELECT user_alias 
                        FROM interactions 
                        WHERE created_at >= NOW() - INTERVAL '7 days'
                        GROUP BY user_alias 
                        HAVING COUNT(*) >= 10
                        ORDER BY COUNT(*) DESC 
                        LIMIT %s
                    """, (count,))
                elif user_type == "low_activity":
                    # Users with few interactions (cold start scenario)
                    cursor.execute("""
                        SELECT user_alias 
                        FROM interactions 
                        WHERE created_at >= NOW() - INTERVAL '30 days'
                        GROUP BY user_alias 
                        HAVING COUNT(*) BETWEEN 1 AND 5
                        ORDER BY RANDOM() 
                        LIMIT %s
                    """, (count,))
                else:  # mixed
                    # Random mix of users
                    cursor.execute("""
                        SELECT user_alias 
                        FROM (
                            SELECT DISTINCT user_alias 
                            FROM interactions 
                            WHERE created_at >= NOW() - INTERVAL '30 days'
                        ) AS users 
                        ORDER BY RANDOM() 
                        LIMIT %s
                    """, (count,))
                
                return [row[0] for row in cursor.fetchall()]
    
    def benchmark_single_user_performance(self, iterations: int = 100) -> AlgorithmBenchmarkResult:
        """Benchmark single user ranking performance with multiple iterations."""
        self.logger.info(f"Running single user benchmark with {iterations} iterations")
        
        # Get a representative test user
        test_users = self._get_test_users("mixed", 1)
        if not test_users:
            raise ValueError("No test users available")
        
        test_user = test_users[0]
        latencies = []
        quality_scores = []
        errors = 0
        posts_processed = []
        ranking_sizes = []
        
        with self._resource_monitor() as monitor:
            for i in range(iterations):
                try:
                    monitor.record_reading()
                    
                    # Measure ranking generation time
                    start_time = time.time()
                    rankings = generate_rankings_for_user(test_user, limit=20)
                    end_time = time.time()
                    
                    latency_ms = (end_time - start_time) * 1000
                    latencies.append(latency_ms)
                    
                    if rankings:
                        ranking_sizes.append(len(rankings))
                        posts_processed.append(len(rankings))
                        
                        # Collect quality metrics if available
                        try:
                            quality_metrics = collect_recommendation_quality_metrics(
                                test_user, rankings, "benchmark"
                            )
                            if quality_metrics:
                                quality_scores.append(quality_metrics)
                        except Exception as e:
                            self.logger.debug(f"Quality metrics collection failed: {e}")
                    
                except Exception as e:
                    errors += 1
                    self.logger.error(f"Error in iteration {i}: {e}")
        
        # Calculate final metrics
        resource_metrics = monitor.get_final_metrics()
        total_time = sum(latencies) / 1000  # Convert to seconds
        
        # Quality averages
        avg_diversity = 0.0
        avg_freshness = 0.0
        avg_engagement = 0.0
        
        if quality_scores:
            avg_diversity = statistics.mean([q.get('diversity_score', 0) for q in quality_scores])
            avg_freshness = statistics.mean([q.get('freshness_score', 0) for q in quality_scores])
            avg_engagement = statistics.mean([q.get('engagement_score', 0) for q in quality_scores])
        
        return AlgorithmBenchmarkResult(
            test_name="single_user_baseline",
            test_timestamp=datetime.utcnow(),
            user_count=1,
            iterations=iterations,
            mean_latency=statistics.mean(latencies),
            p50_latency=statistics.quantiles(latencies, n=2)[0] if len(latencies) >= 2 else 0,
            p90_latency=statistics.quantiles(latencies, n=10)[8] if len(latencies) >= 10 else 0,
            p95_latency=statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else 0,
            p99_latency=statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else 0,
            max_latency=max(latencies) if latencies else 0,
            requests_per_second=(iterations - errors) / total_time if total_time > 0 else 0,
            posts_processed_per_second=sum(posts_processed) / total_time if total_time > 0 else 0,
            avg_cpu_percent=resource_metrics['avg_cpu'],
            peak_cpu_percent=resource_metrics['peak_cpu'],
            avg_memory_mb=resource_metrics['avg_memory'],
            peak_memory_mb=resource_metrics['peak_memory'],
            memory_delta_mb=resource_metrics['memory_delta'],
            avg_diversity_score=avg_diversity,
            avg_freshness_score=avg_freshness,
            avg_engagement_score=avg_engagement,
            error_count=errors,
            success_rate=(iterations - errors) / iterations if iterations > 0 else 0,
            cache_hit_rate=0.0,  # TODO: Implement cache monitoring
            posts_considered=sum(posts_processed),
            avg_ranking_size=statistics.mean(ranking_sizes) if ranking_sizes else 0
        )
    
    def benchmark_concurrent_users(self, user_count: int = 10, 
                                   iterations_per_user: int = 10) -> AlgorithmBenchmarkResult:
        """Benchmark algorithm performance with concurrent user requests."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        self.logger.info(f"Running concurrent user benchmark: {user_count} users, {iterations_per_user} iterations each")
        
        test_users = self._get_test_users("mixed", user_count)
        all_latencies = []
        all_quality_scores = []
        total_errors = 0
        total_posts_processed = []
        total_ranking_sizes = []
        
        def benchmark_user(user_id: str) -> Tuple[List[float], List[Dict], int]:
            """Benchmark a single user's performance."""
            latencies = []
            quality_scores = []
            errors = 0
            
            for _ in range(iterations_per_user):
                try:
                    start_time = time.time()
                    rankings = generate_rankings_for_user(user_id, limit=20)
                    end_time = time.time()
                    
                    latency_ms = (end_time - start_time) * 1000
                    latencies.append(latency_ms)
                    
                    if rankings:
                        total_posts_processed.append(len(rankings))
                        total_ranking_sizes.append(len(rankings))
                        
                        try:
                            quality_metrics = collect_recommendation_quality_metrics(
                                user_id, rankings, "concurrent_benchmark"
                            )
                            if quality_metrics:
                                quality_scores.append(quality_metrics)
                        except Exception:
                            pass  # Quality metrics optional for this test
                
                except Exception as e:
                    errors += 1
                    self.logger.debug(f"Error for user {user_id}: {e}")
            
            return latencies, quality_scores, errors
        
        start_time = time.time()
        
        with self._resource_monitor() as monitor:
            with ThreadPoolExecutor(max_workers=user_count) as executor:
                # Submit all user benchmark tasks
                future_to_user = {
                    executor.submit(benchmark_user, user): user 
                    for user in test_users
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_user):
                    try:
                        monitor.record_reading()
                        latencies, quality_scores, errors = future.result()
                        all_latencies.extend(latencies)
                        all_quality_scores.extend(quality_scores)
                        total_errors += errors
                    except Exception as e:
                        total_errors += 1
                        self.logger.error(f"Future execution error: {e}")
        
        total_time = time.time() - start_time
        resource_metrics = monitor.get_final_metrics()
        total_requests = len(all_latencies) + total_errors
        
        # Quality averages
        avg_diversity = statistics.mean([q.get('diversity_score', 0) for q in all_quality_scores]) if all_quality_scores else 0
        avg_freshness = statistics.mean([q.get('freshness_score', 0) for q in all_quality_scores]) if all_quality_scores else 0
        avg_engagement = statistics.mean([q.get('engagement_score', 0) for q in all_quality_scores]) if all_quality_scores else 0
        
        return AlgorithmBenchmarkResult(
            test_name="concurrent_users",
            test_timestamp=datetime.utcnow(),
            user_count=user_count,
            iterations=total_requests,
            mean_latency=statistics.mean(all_latencies) if all_latencies else 0,
            p50_latency=statistics.quantiles(all_latencies, n=2)[0] if len(all_latencies) >= 2 else 0,
            p90_latency=statistics.quantiles(all_latencies, n=10)[8] if len(all_latencies) >= 10 else 0,
            p95_latency=statistics.quantiles(all_latencies, n=20)[18] if len(all_latencies) >= 20 else 0,
            p99_latency=statistics.quantiles(all_latencies, n=100)[98] if len(all_latencies) >= 100 else 0,
            max_latency=max(all_latencies) if all_latencies else 0,
            requests_per_second=(total_requests - total_errors) / total_time if total_time > 0 else 0,
            posts_processed_per_second=sum(total_posts_processed) / total_time if total_time > 0 else 0,
            avg_cpu_percent=resource_metrics['avg_cpu'],
            peak_cpu_percent=resource_metrics['peak_cpu'],
            avg_memory_mb=resource_metrics['avg_memory'],
            peak_memory_mb=resource_metrics['peak_memory'],
            memory_delta_mb=resource_metrics['memory_delta'],
            avg_diversity_score=avg_diversity,
            avg_freshness_score=avg_freshness,
            avg_engagement_score=avg_engagement,
            error_count=total_errors,
            success_rate=(total_requests - total_errors) / total_requests if total_requests > 0 else 0,
            cache_hit_rate=0.0,  # TODO: Implement cache monitoring
            posts_considered=sum(total_posts_processed),
            avg_ranking_size=statistics.mean(total_ranking_sizes) if total_ranking_sizes else 0
        )
    
    def benchmark_cold_start_performance(self, user_count: int = 20) -> AlgorithmBenchmarkResult:
        """Benchmark algorithm performance for cold start users (minimal interaction history)."""
        self.logger.info(f"Running cold start benchmark with {user_count} users")
        
        test_users = self._get_test_users("low_activity", user_count)
        latencies = []
        quality_scores = []
        errors = 0
        posts_processed = []
        ranking_sizes = []
        
        with self._resource_monitor() as monitor:
            for user in test_users:
                try:
                    monitor.record_reading()
                    
                    start_time = time.time()
                    rankings = generate_rankings_for_user(user, limit=20)
                    end_time = time.time()
                    
                    latency_ms = (end_time - start_time) * 1000
                    latencies.append(latency_ms)
                    
                    if rankings:
                        ranking_sizes.append(len(rankings))
                        posts_processed.append(len(rankings))
                        
                        try:
                            quality_metrics = collect_recommendation_quality_metrics(
                                user, rankings, "cold_start_benchmark"
                            )
                            if quality_metrics:
                                quality_scores.append(quality_metrics)
                        except Exception:
                            pass
                
                except Exception as e:
                    errors += 1
                    self.logger.error(f"Error processing cold start user {user}: {e}")
        
        resource_metrics = monitor.get_final_metrics()
        total_time = sum(latencies) / 1000  # Convert to seconds
        
        # Quality averages
        avg_diversity = statistics.mean([q.get('diversity_score', 0) for q in quality_scores]) if quality_scores else 0
        avg_freshness = statistics.mean([q.get('freshness_score', 0) for q in quality_scores]) if quality_scores else 0
        avg_engagement = statistics.mean([q.get('engagement_score', 0) for q in quality_scores]) if quality_scores else 0
        
        return AlgorithmBenchmarkResult(
            test_name="cold_start_users",
            test_timestamp=datetime.utcnow(),
            user_count=user_count,
            iterations=len(latencies) + errors,
            mean_latency=statistics.mean(latencies) if latencies else 0,
            p50_latency=statistics.quantiles(latencies, n=2)[0] if len(latencies) >= 2 else 0,
            p90_latency=statistics.quantiles(latencies, n=10)[8] if len(latencies) >= 10 else 0,
            p95_latency=statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else 0,
            p99_latency=statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else 0,
            max_latency=max(latencies) if latencies else 0,
            requests_per_second=len(latencies) / total_time if total_time > 0 else 0,
            posts_processed_per_second=sum(posts_processed) / total_time if total_time > 0 else 0,
            avg_cpu_percent=resource_metrics['avg_cpu'],
            peak_cpu_percent=resource_metrics['peak_cpu'],
            avg_memory_mb=resource_metrics['avg_memory'],
            peak_memory_mb=resource_metrics['peak_memory'],
            memory_delta_mb=resource_metrics['memory_delta'],
            avg_diversity_score=avg_diversity,
            avg_freshness_score=avg_freshness,
            avg_engagement_score=avg_engagement,
            error_count=errors,
            success_rate=len(latencies) / (len(latencies) + errors) if (len(latencies) + errors) > 0 else 0,
            cache_hit_rate=0.0,
            posts_considered=sum(posts_processed),
            avg_ranking_size=statistics.mean(ranking_sizes) if ranking_sizes else 0
        )
    
    def benchmark_high_activity_users(self, user_count: int = 15) -> AlgorithmBenchmarkResult:
        """Benchmark algorithm performance for high-activity users (many interactions)."""
        self.logger.info(f"Running high activity user benchmark with {user_count} users")
        
        test_users = self._get_test_users("high_activity", user_count)
        latencies = []
        quality_scores = []
        errors = 0
        posts_processed = []
        ranking_sizes = []
        
        with self._resource_monitor() as monitor:
            for user in test_users:
                try:
                    monitor.record_reading()
                    
                    start_time = time.time()
                    rankings = generate_rankings_for_user(user, limit=20)
                    end_time = time.time()
                    
                    latency_ms = (end_time - start_time) * 1000
                    latencies.append(latency_ms)
                    
                    if rankings:
                        ranking_sizes.append(len(rankings))
                        posts_processed.append(len(rankings))
                        
                        try:
                            quality_metrics = collect_recommendation_quality_metrics(
                                user, rankings, "high_activity_benchmark"
                            )
                            if quality_metrics:
                                quality_scores.append(quality_metrics)
                        except Exception:
                            pass
                
                except Exception as e:
                    errors += 1
                    self.logger.error(f"Error processing high activity user {user}: {e}")
        
        resource_metrics = monitor.get_final_metrics()
        total_time = sum(latencies) / 1000  # Convert to seconds
        
        # Quality averages
        avg_diversity = statistics.mean([q.get('diversity_score', 0) for q in quality_scores]) if quality_scores else 0
        avg_freshness = statistics.mean([q.get('freshness_score', 0) for q in quality_scores]) if quality_scores else 0
        avg_engagement = statistics.mean([q.get('engagement_score', 0) for q in quality_scores]) if quality_scores else 0
        
        return AlgorithmBenchmarkResult(
            test_name="high_activity_users",
            test_timestamp=datetime.utcnow(),
            user_count=user_count,
            iterations=len(latencies) + errors,
            mean_latency=statistics.mean(latencies) if latencies else 0,
            p50_latency=statistics.quantiles(latencies, n=2)[0] if len(latencies) >= 2 else 0,
            p90_latency=statistics.quantiles(latencies, n=10)[8] if len(latencies) >= 10 else 0,
            p95_latency=statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else 0,
            p99_latency=statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else 0,
            max_latency=max(latencies) if latencies else 0,
            requests_per_second=len(latencies) / total_time if total_time > 0 else 0,
            posts_processed_per_second=sum(posts_processed) / total_time if total_time > 0 else 0,
            avg_cpu_percent=resource_metrics['avg_cpu'],
            peak_cpu_percent=resource_metrics['peak_cpu'],
            avg_memory_mb=resource_metrics['avg_memory'],
            peak_memory_mb=resource_metrics['peak_memory'],
            memory_delta_mb=resource_metrics['memory_delta'],
            avg_diversity_score=avg_diversity,
            avg_freshness_score=avg_freshness,
            avg_engagement_score=avg_engagement,
            error_count=errors,
            success_rate=len(latencies) / (len(latencies) + errors) if (len(latencies) + errors) > 0 else 0,
            cache_hit_rate=0.0,
            posts_considered=sum(posts_processed),
            avg_ranking_size=statistics.mean(ranking_sizes) if ranking_sizes else 0
        )
    
    def store_benchmark_result(self, result: AlgorithmBenchmarkResult) -> int:
        """Store benchmark result in the performance_benchmarks table."""
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
                    result.test_name,
                    f"Automated benchmark: {result.test_name}",
                    "algorithm_benchmark",
                    result.test_timestamp,
                    result.user_count,
                    int(sum([result.mean_latency]) / 1000),  # Rough duration estimate
                    result.iterations,
                    result.p50_latency,
                    result.p95_latency,
                    result.p99_latency,
                    result.max_latency,
                    result.requests_per_second,
                    1.0 - result.success_rate,  # error_rate
                    result.avg_cpu_percent,
                    result.peak_cpu_percent,
                    result.avg_memory_mb,
                    result.peak_memory_mb,
                    0.0,  # avg_db_query_time - TODO: implement
                    1,    # db_connections_used - TODO: implement  
                    json.dumps({
                        'avg_ranking_size': result.avg_ranking_size,
                        'avg_diversity_score': result.avg_diversity_score,
                        'avg_freshness_score': result.avg_freshness_score,
                        'avg_engagement_score': result.avg_engagement_score
                    }),
                    json.dumps({
                        'python_version': sys.version,
                        'posts_considered': result.posts_considered,
                        'memory_delta_mb': result.memory_delta_mb
                    })
                ))
                
                benchmark_id = cursor.fetchone()[0]
                conn.commit()
                return benchmark_id
    
    def run_comprehensive_benchmark_suite(self) -> Dict[str, AlgorithmBenchmarkResult]:
        """Run the complete automated benchmark suite."""
        self.logger.info("Starting comprehensive algorithm benchmark suite")
        
        results = {}
        
        # 1. Single user baseline performance
        try:
            self.logger.info("Running single user baseline benchmark...")
            results['single_user'] = self.benchmark_single_user_performance(iterations=100)
            self.store_benchmark_result(results['single_user'])
        except Exception as e:
            self.logger.error(f"Single user benchmark failed: {e}")
        
        # 2. Concurrent users performance
        try:
            self.logger.info("Running concurrent users benchmark...")
            results['concurrent'] = self.benchmark_concurrent_users(user_count=10, iterations_per_user=10)
            self.store_benchmark_result(results['concurrent'])
        except Exception as e:
            self.logger.error(f"Concurrent users benchmark failed: {e}")
        
        # 3. Cold start performance
        try:
            self.logger.info("Running cold start benchmark...")
            results['cold_start'] = self.benchmark_cold_start_performance(user_count=20)
            self.store_benchmark_result(results['cold_start'])
        except Exception as e:
            self.logger.error(f"Cold start benchmark failed: {e}")
        
        # 4. High activity users performance
        try:
            self.logger.info("Running high activity users benchmark...")
            results['high_activity'] = self.benchmark_high_activity_users(user_count=15)
            self.store_benchmark_result(results['high_activity'])
        except Exception as e:
            self.logger.error(f"High activity benchmark failed: {e}")
        
        self.logger.info(f"Comprehensive benchmark suite completed. {len(results)} tests successful.")
        return results


# Pytest test cases for the benchmark suite
class TestAlgorithmBenchmarks:
    """Test cases for the automated benchmark suite."""
    
    @pytest.fixture
    def benchmark_suite(self):
        """Create a benchmark suite instance for testing."""
        return AlgorithmBenchmarkSuite()
    
    @patch('tests.test_performance_benchmarks.collect_recommendation_quality_metrics')
    @patch('tests.test_performance_benchmarks.generate_rankings_for_user')
    @patch('tests.test_performance_benchmarks.get_db_connection')
    @patch('tests.test_performance_benchmarks.get_cursor')
    def test_single_user_benchmark(self, mock_cursor, mock_connection, mock_generate_rankings, mock_quality_metrics, benchmark_suite):
        """Test single user baseline benchmark."""
        # Mock database interaction
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = [123]  # Mock benchmark ID
        
        # Mock user data for _get_test_users
        mock_cur.fetchall.return_value = [('test_user_1',)]
        
        # Mock ranking algorithm to return consistent results
        mock_generate_rankings.return_value = {
            'rankings': [{'post_id': '1', 'score': 0.8}, {'post_id': '2', 'score': 0.6}],
            'metadata': {'cache_hit': False, 'posts_considered': 10}
        }
        
        # Mock quality metrics to return consistent results
        mock_quality_metrics.return_value = {
            'diversity_score': 0.75,
            'freshness_score': 0.85,
            'engagement_score': 0.65
        }
        
        result = benchmark_suite.benchmark_single_user_performance(iterations=5)
        
        assert result.test_name == "single_user_baseline"
        assert result.user_count == 1
        assert result.iterations == 5
        assert result.mean_latency >= 0
        assert result.success_rate >= 0
        assert result.success_rate <= 1.0
        
        # Store result in database
        benchmark_id = benchmark_suite.store_benchmark_result(result)
        assert benchmark_id == 123
    
    @patch('tests.test_performance_benchmarks.collect_recommendation_quality_metrics')
    @patch('tests.test_performance_benchmarks.generate_rankings_for_user')
    @patch('tests.test_performance_benchmarks.get_db_connection')
    @patch('tests.test_performance_benchmarks.get_cursor')
    def test_concurrent_users_benchmark(self, mock_cursor, mock_connection, mock_generate_rankings, mock_quality_metrics, benchmark_suite):
        """Test concurrent users benchmark."""
        # Mock database interaction
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = [456]  # Mock benchmark ID
        
        # Mock user data for _get_test_users
        mock_cur.fetchall.return_value = [('test_user_1',), ('test_user_2',), ('test_user_3',)]
        
        # Mock ranking algorithm to return consistent results
        mock_generate_rankings.return_value = {
            'rankings': [{'post_id': '1', 'score': 0.8}, {'post_id': '2', 'score': 0.6}],
            'metadata': {'cache_hit': False, 'posts_considered': 10}
        }
        
        # Mock quality metrics to return consistent results
        mock_quality_metrics.return_value = {
            'diversity_score': 0.75,
            'freshness_score': 0.85,
            'engagement_score': 0.65
        }
        
        result = benchmark_suite.benchmark_concurrent_users(user_count=3, iterations_per_user=3)
        
        assert result.test_name == "concurrent_users"
        assert result.user_count == 3
        assert result.mean_latency >= 0
        assert result.success_rate >= 0
        assert result.success_rate <= 1.0
        
        # Store result in database
        benchmark_id = benchmark_suite.store_benchmark_result(result)
        assert benchmark_id == 456
    
    @patch('tests.test_performance_benchmarks.collect_recommendation_quality_metrics')
    @patch('tests.test_performance_benchmarks.generate_rankings_for_user')
    @patch('tests.test_performance_benchmarks.get_db_connection')
    @patch('tests.test_performance_benchmarks.get_cursor')
    def test_cold_start_benchmark(self, mock_cursor, mock_connection, mock_generate_rankings, mock_quality_metrics, benchmark_suite):
        """Test cold start users benchmark."""
        # Mock database interaction
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Mock user data for _get_test_users
        mock_cur.fetchall.return_value = [('test_user_1',), ('test_user_2',), ('test_user_3',), ('test_user_4',), ('test_user_5',)]
        
        # Mock ranking algorithm to return consistent results
        mock_generate_rankings.return_value = {
            'rankings': [{'post_id': '1', 'score': 0.8}, {'post_id': '2', 'score': 0.6}],
            'metadata': {'cache_hit': False, 'posts_considered': 10}
        }
        
        # Mock quality metrics to return consistent results
        mock_quality_metrics.return_value = {
            'diversity_score': 0.75,
            'freshness_score': 0.85,
            'engagement_score': 0.65
        }
        
        result = benchmark_suite.benchmark_cold_start_performance(user_count=5)
        
        assert result.test_name == "cold_start_users"
        assert result.user_count == 5
        assert result.mean_latency >= 0
        assert result.success_rate >= 0
        assert result.success_rate <= 1.0
    
    @patch('tests.test_performance_benchmarks.collect_recommendation_quality_metrics')
    @patch('tests.test_performance_benchmarks.generate_rankings_for_user')
    @patch('tests.test_performance_benchmarks.get_db_connection')  
    @patch('tests.test_performance_benchmarks.get_cursor')
    def test_high_activity_benchmark(self, mock_cursor, mock_connection, mock_generate_rankings, mock_quality_metrics, benchmark_suite):
        """Test high activity users benchmark."""
        # Mock database interaction
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Mock user data for _get_test_users
        mock_cur.fetchall.return_value = [('test_user_1',), ('test_user_2',), ('test_user_3',), ('test_user_4',), ('test_user_5',)]
        
        # Mock ranking algorithm to return consistent results
        mock_generate_rankings.return_value = {
            'rankings': [{'post_id': '1', 'score': 0.8}, {'post_id': '2', 'score': 0.6}],
            'metadata': {'cache_hit': False, 'posts_considered': 10}
        }
        
        # Mock quality metrics to return consistent results
        mock_quality_metrics.return_value = {
            'diversity_score': 0.75,
            'freshness_score': 0.85,
            'engagement_score': 0.65
        }
        
        result = benchmark_suite.benchmark_high_activity_users(user_count=5)
        
        assert result.test_name == "high_activity_users"
        assert result.user_count == 5
        assert result.mean_latency >= 0
        assert result.success_rate >= 0
        assert result.success_rate <= 1.0
    
    @pytest.mark.slow
    @patch('tests.test_performance_benchmarks.collect_recommendation_quality_metrics')
    @patch('tests.test_performance_benchmarks.generate_rankings_for_user')
    @patch('tests.test_performance_benchmarks.get_db_connection')
    @patch('tests.test_performance_benchmarks.get_cursor')
    def test_comprehensive_benchmark_suite(self, mock_cursor, mock_connection, mock_generate_rankings, mock_quality_metrics, benchmark_suite):
        """Test the complete comprehensive benchmark suite."""
        # Mock database interaction
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = [789]  # Mock benchmark ID
        
        # Mock user data for _get_test_users - return different users for different calls
        mock_cur.fetchall.side_effect = [
            [('test_user_1',)],  # single user
            [('test_user_1',), ('test_user_2',), ('test_user_3',)],  # concurrent users  
            [('test_user_1',), ('test_user_2',), ('test_user_3',), ('test_user_4',), ('test_user_5',)],  # cold start
            [('test_user_1',), ('test_user_2',), ('test_user_3',), ('test_user_4',), ('test_user_5',)]   # high activity
        ]
        
        # Mock ranking algorithm to return consistent results
        mock_generate_rankings.return_value = {
            'rankings': [{'post_id': '1', 'score': 0.8}, {'post_id': '2', 'score': 0.6}],
            'metadata': {'cache_hit': False, 'posts_considered': 10}
        }
        
        # Mock quality metrics to return consistent results
        mock_quality_metrics.return_value = {
            'diversity_score': 0.75,
            'freshness_score': 0.85,
            'engagement_score': 0.65
        }
        
        results = benchmark_suite.run_comprehensive_benchmark_suite()
        
        # Should have at least one successful benchmark
        assert len(results) >= 1
        
        # Each result should be valid
        for test_name, result in results.items():
            assert isinstance(result, AlgorithmBenchmarkResult)
            assert result.success_rate >= 0
            assert result.success_rate <= 1.0
            assert result.mean_latency >= 0


if __name__ == "__main__":
    # Command line interface for running benchmarks
    import argparse
    
    parser = argparse.ArgumentParser(description="Run algorithm performance benchmarks")
    parser.add_argument("--test", choices=["single", "concurrent", "cold", "high", "all"], 
                       default="all", help="Which benchmark to run")
    parser.add_argument("--iterations", type=int, default=100, 
                       help="Number of iterations for single user test")
    parser.add_argument("--users", type=int, default=10, 
                       help="Number of users for concurrent test")
    
    args = parser.parse_args()
    
    suite = AlgorithmBenchmarkSuite()
    
    if args.test == "single":
        result = suite.benchmark_single_user_performance(iterations=args.iterations)
        print(f"Single user benchmark result: {result.to_dict()}")
    elif args.test == "concurrent":
        result = suite.benchmark_concurrent_users(user_count=args.users, iterations_per_user=10)
        print(f"Concurrent users benchmark result: {result.to_dict()}")
    elif args.test == "cold":
        result = suite.benchmark_cold_start_performance(user_count=20)
        print(f"Cold start benchmark result: {result.to_dict()}")
    elif args.test == "high":
        result = suite.benchmark_high_activity_users(user_count=15)
        print(f"High activity benchmark result: {result.to_dict()}")
    else:  # all
        results = suite.run_comprehensive_benchmark_suite()
        print("Comprehensive benchmark results:")
        for test_name, result in results.items():
            print(f"{test_name}: {json.dumps(result.to_dict(), indent=2)}") 