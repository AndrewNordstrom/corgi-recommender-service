"""
Performance Benchmarking System - Core Module

This module provides automated performance testing, regression detection,
and optimization guidance for the Corgi Recommender Service.

TODO #27: Create performance benchmarks for recommendation algorithm
"""

import json
import logging
import psutil
import time
import statistics
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from db.connection import get_db_connection, get_cursor
import utils.metrics as metrics

logger = logging.getLogger(__name__)

class PerformanceBenchmark:
    """Core performance benchmarking system for recommendation algorithm."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        
    def establish_baseline_performance(self, test_name: str = "baseline") -> Dict:
        """
        Establish baseline performance profile for current recommendation system.
        
        Args:
            test_name: Name for the baseline test
            
        Returns:
            Dictionary containing comprehensive baseline metrics
        """
        try:
            self.logger.info(f"Starting baseline performance test: {test_name}")
            
            # Default baseline test configuration
            test_config = {
                'concurrent_users': 10,
                'test_duration_seconds': 300,  # 5 minutes
                'ramp_up_time': 60,           # 1 minute
                'requests_per_user': 30,
                'endpoint': '/api/v1/recommendations'
            }
            
            # Run comprehensive baseline test
            baseline_results = self.run_performance_test(
                test_name=test_name,
                test_config=test_config,
                benchmark_type='baseline'
            )
            
            # Store baseline in database
            self._store_benchmark_results(baseline_results)
            
            self.logger.info(f"Baseline performance established: {baseline_results['summary']}")
            return baseline_results
            
        except Exception as e:
            self.logger.error(f"Error establishing baseline performance: {e}")
            raise
    
    def run_performance_test(self, test_name: str, test_config: Dict, 
                           benchmark_type: str = 'test') -> Dict:
        """
        Run a comprehensive performance test with the given configuration.
        
        Args:
            test_name: Name of the test
            test_config: Test configuration parameters
            benchmark_type: Type of benchmark (baseline, variant, regression)
            
        Returns:
            Comprehensive performance test results
        """
        try:
            start_time = time.time()
            
            # Initialize metrics tracking
            test_results = {
                'test_name': test_name,
                'benchmark_type': benchmark_type,
                'test_config': test_config,
                'start_time': datetime.utcnow().isoformat(),
                'latency_measurements': [],
                'error_count': 0,
                'total_requests': 0
            }
            
            # Monitor system resources during test
            with self._monitor_system_resources() as resource_monitor:
                # Execute load test
                load_test_results = self._execute_load_test(test_config)
                test_results.update(load_test_results)
            
            # Add resource utilization data
            test_results['resource_utilization'] = resource_monitor.get_metrics()
            
            # Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(test_results)
            test_results['performance_metrics'] = performance_metrics
            
            # Calculate quality impact if applicable
            quality_impact = self._measure_quality_impact(test_config)
            if quality_impact:
                test_results['quality_impact'] = quality_impact
            
            # Create summary
            test_results['summary'] = self._create_performance_summary(test_results)
            test_results['end_time'] = datetime.utcnow().isoformat()
            test_results['total_duration'] = time.time() - start_time
            
            return test_results
            
        except Exception as e:
            self.logger.error(f"Error running performance test {test_name}: {e}")
            raise
    
    def check_performance_regression(self, new_results: Dict, 
                                   baseline_name: str = "baseline") -> Dict:
        """
        Check for performance regression against baseline.
        
        Args:
            new_results: Recent test results to compare
            baseline_name: Name of baseline to compare against
            
        Returns:
            Regression analysis results
        """
        try:
            # Get baseline results from database
            baseline = self._get_baseline_benchmark(baseline_name)
            if not baseline:
                return {
                    'has_regression': False,
                    'error': f"No baseline found with name: {baseline_name}"
                }
            
            alerts = []
            
            # Check latency regression thresholds
            new_p95 = new_results['performance_metrics']['p95_latency']
            baseline_p95 = baseline['p95_latency']
            
            if new_p95 > baseline_p95 * 1.2:  # 20% degradation threshold
                alerts.append({
                    'type': 'latency_regression',
                    'severity': 'high',
                    'metric': 'p95_latency',
                    'baseline_value': baseline_p95,
                    'current_value': new_p95,
                    'degradation_percent': ((new_p95 / baseline_p95) - 1) * 100,
                    'message': f"P95 latency increased by {((new_p95 / baseline_p95) - 1) * 100:.1f}%"
                })
            
            # Check throughput regression
            new_rps = new_results['performance_metrics']['requests_per_second']
            baseline_rps = baseline['requests_per_second']
            
            if new_rps < baseline_rps * 0.8:  # 20% degradation threshold
                alerts.append({
                    'type': 'throughput_regression',
                    'severity': 'medium',
                    'metric': 'requests_per_second',
                    'baseline_value': baseline_rps,
                    'current_value': new_rps,
                    'degradation_percent': ((baseline_rps / new_rps) - 1) * 100,
                    'message': f"RPS decreased by {((baseline_rps / new_rps) - 1) * 100:.1f}%"
                })
            
            # Check error rate increase
            new_error_rate = new_results['performance_metrics']['error_rate']
            baseline_error_rate = baseline['error_rate']
            
            if new_error_rate > baseline_error_rate + 0.05:  # 5% absolute increase
                alerts.append({
                    'type': 'error_rate_increase',
                    'severity': 'high',
                    'metric': 'error_rate',
                    'baseline_value': baseline_error_rate,
                    'current_value': new_error_rate,
                    'message': f"Error rate increased from {baseline_error_rate:.2%} to {new_error_rate:.2%}"
                })
            
            # Check resource utilization
            if 'resource_utilization' in new_results:
                resource_alerts = self._check_resource_regression(
                    new_results['resource_utilization'],
                    baseline
                )
                alerts.extend(resource_alerts)
            
            regression_analysis = {
                'has_regression': len(alerts) > 0,
                'alerts': alerts,
                'baseline_comparison': {
                    'baseline_name': baseline_name,
                    'baseline_timestamp': baseline.get('test_timestamp'),
                    'current_timestamp': new_results.get('start_time'),
                    'metrics_comparison': self._compare_metrics(new_results, baseline)
                },
                'recommendation': self._generate_performance_recommendation(alerts),
                'overall_score': self._calculate_performance_score(new_results, baseline)
            }
            
            return regression_analysis
            
        except Exception as e:
            self.logger.error(f"Error checking performance regression: {e}")
            return {'has_regression': False, 'error': str(e)}
    
    def _execute_load_test(self, test_config: Dict) -> Dict:
        """Execute concurrent load test against the recommendation endpoint."""
        try:
            concurrent_users = test_config['concurrent_users']
            test_duration = test_config['test_duration_seconds']
            requests_per_user = test_config.get('requests_per_user', 30)
            endpoint = test_config.get('endpoint', '/api/v1/recommendations')
            
            results = {
                'latency_measurements': [],
                'error_count': 0,
                'total_requests': 0,
                'successful_requests': 0
            }
            
            # Generate test user IDs
            test_users = [f"perf_test_user_{i}" for i in range(concurrent_users)]
            
            def make_requests_for_user(user_id: str) -> List[float]:
                """Make requests for a single test user."""
                user_latencies = []
                
                for _ in range(requests_per_user):
                    try:
                        start_time = time.time()
                        
                        response = requests.get(
                            f"{self.base_url}{endpoint}",
                            params={'user_id': user_id, 'limit': 10},
                            headers={'Authorization': 'Bearer test_token'},
                            timeout=30
                        )
                        
                        latency = (time.time() - start_time) * 1000  # Convert to milliseconds
                        user_latencies.append(latency)
                        
                        if response.status_code == 200:
                            results['successful_requests'] += 1
                        else:
                            results['error_count'] += 1
                            
                        results['total_requests'] += 1
                        
                        # Small delay between requests from same user
                        time.sleep(0.1)
                        
                    except Exception as e:
                        results['error_count'] += 1
                        results['total_requests'] += 1
                        self.logger.warning(f"Request failed for user {user_id}: {e}")
                
                return user_latencies
            
            # Execute concurrent requests
            all_latencies = []
            
            with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                future_to_user = {
                    executor.submit(make_requests_for_user, user_id): user_id 
                    for user_id in test_users
                }
                
                for future in as_completed(future_to_user):
                    user_id = future_to_user[future]
                    try:
                        user_latencies = future.result()
                        all_latencies.extend(user_latencies)
                    except Exception as e:
                        self.logger.error(f"Error in requests for user {user_id}: {e}")
            
            results['latency_measurements'] = all_latencies
            return results
            
        except Exception as e:
            self.logger.error(f"Error executing load test: {e}")
            raise
    
    def _calculate_performance_metrics(self, test_results: Dict) -> Dict:
        """Calculate comprehensive performance metrics from test results."""
        try:
            latencies = test_results['latency_measurements']
            total_requests = test_results['total_requests']
            error_count = test_results['error_count']
            successful_requests = test_results['successful_requests']
            test_duration = test_results['test_config']['test_duration_seconds']
            
            if not latencies:
                return {
                    'error': 'No latency measurements available',
                    'total_requests': total_requests,
                    'error_count': error_count
                }
            
            # Calculate latency percentiles
            sorted_latencies = sorted(latencies)
            
            metrics = {
                'p50_latency': statistics.median(sorted_latencies),
                'p95_latency': sorted_latencies[int(0.95 * len(sorted_latencies))],
                'p99_latency': sorted_latencies[int(0.99 * len(sorted_latencies))],
                'max_latency': max(sorted_latencies),
                'min_latency': min(sorted_latencies),
                'avg_latency': statistics.mean(sorted_latencies),
                
                # Throughput metrics
                'requests_per_second': successful_requests / test_duration if test_duration > 0 else 0,
                'error_rate': error_count / total_requests if total_requests > 0 else 0,
                'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
                
                # Summary statistics
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'error_count': error_count,
                'test_duration_seconds': test_duration
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {'error': str(e)}
    
    @contextmanager
    def _monitor_system_resources(self):
        """Context manager to monitor system resource usage during tests."""
        class ResourceMonitor:
            def __init__(self):
                self.start_time = time.time()
                self.cpu_readings = []
                self.memory_readings = []
                self.monitoring = True
                
            def collect_metrics(self):
                """Collect resource metrics periodically."""
                while self.monitoring:
                    try:
                        cpu_percent = psutil.cpu_percent(interval=1)
                        memory_info = psutil.virtual_memory()
                        
                        self.cpu_readings.append(cpu_percent)
                        self.memory_readings.append(memory_info.used / (1024 * 1024))  # MB
                        
                        time.sleep(2)  # Collect every 2 seconds
                    except:
                        break
            
            def get_metrics(self):
                """Get aggregated resource metrics."""
                self.monitoring = False
                
                if not self.cpu_readings or not self.memory_readings:
                    return {
                        'avg_cpu_usage': 0,
                        'peak_cpu_usage': 0,
                        'avg_memory_mb': 0,
                        'peak_memory_mb': 0
                    }
                
                return {
                    'avg_cpu_usage': statistics.mean(self.cpu_readings),
                    'peak_cpu_usage': max(self.cpu_readings),
                    'avg_memory_mb': statistics.mean(self.memory_readings),
                    'peak_memory_mb': max(self.memory_readings),
                    'monitoring_duration': time.time() - self.start_time
                }
        
        monitor = ResourceMonitor()
        
        # Start monitoring in background thread
        import threading
        monitor_thread = threading.Thread(target=monitor.collect_metrics, daemon=True)
        monitor_thread.start()
        
        try:
            yield monitor
        finally:
            monitor.monitoring = False
            if monitor_thread.is_alive():
                monitor_thread.join(timeout=2)
    
    def _measure_quality_impact(self, test_config: Dict) -> Optional[Dict]:
        """Measure impact on recommendation quality during load testing."""
        try:
            # This would integrate with the quality metrics system
            # For now, return placeholder data
            return {
                'quality_score_degradation': 0.0,
                'diversity_impact': 0.0,
                'freshness_impact': 0.0,
                'note': 'Quality impact measurement not yet implemented'
            }
        except Exception as e:
            self.logger.error(f"Error measuring quality impact: {e}")
            return None
    
    def _store_benchmark_results(self, results: Dict):
        """Store benchmark results in database."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    metrics = results['performance_metrics']
                    resource_util = results.get('resource_utilization', {})
                    
                    cursor.execute("""
                        INSERT INTO performance_benchmarks 
                        (name, description, benchmark_type, concurrent_users, 
                         test_duration_seconds, total_requests, p50_latency, p95_latency, 
                         p99_latency, max_latency, requests_per_second, error_rate,
                         avg_cpu_usage, peak_cpu_usage, avg_memory_mb, peak_memory_mb,
                         avg_db_query_time, db_connections_used, quality_score_degradation,
                         algorithm_config, environment_info)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        results['test_name'],
                        f"Performance test: {results['test_name']}",
                        results['benchmark_type'],
                        results['test_config']['concurrent_users'],
                        results['test_config']['test_duration_seconds'],
                        metrics.get('total_requests', 0),
                        metrics.get('p50_latency', 0),
                        metrics.get('p95_latency', 0),
                        metrics.get('p99_latency', 0),
                        metrics.get('max_latency', 0),
                        metrics.get('requests_per_second', 0),
                        metrics.get('error_rate', 0),
                        resource_util.get('avg_cpu_usage', 0),
                        resource_util.get('peak_cpu_usage', 0),
                        resource_util.get('avg_memory_mb', 0),
                        resource_util.get('peak_memory_mb', 0),
                        0,  # avg_db_query_time - to be implemented
                        0,  # db_connections_used - to be implemented
                        results.get('quality_impact', {}).get('quality_score_degradation'),
                        json.dumps(results['test_config']),
                        json.dumps({'platform': 'development'})
                    ))
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Error storing benchmark results: {e}")
    
    def _get_baseline_benchmark(self, baseline_name: str) -> Optional[Dict]:
        """Get baseline benchmark from database."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT * FROM performance_benchmarks 
                        WHERE name = %s AND benchmark_type = 'baseline'
                        ORDER BY test_timestamp DESC 
                        LIMIT 1
                    """, (baseline_name,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    # Map row to dictionary (column names to values)
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                    
        except Exception as e:
            self.logger.error(f"Error getting baseline benchmark: {e}")
            return None
    
    def _create_performance_summary(self, results: Dict) -> Dict:
        """Create human-readable performance summary."""
        try:
            metrics = results['performance_metrics']
            
            return {
                'test_name': results['test_name'],
                'duration': f"{results.get('total_duration', 0):.1f} seconds",
                'requests_per_second': f"{metrics.get('requests_per_second', 0):.1f} RPS",
                'p95_latency': f"{metrics.get('p95_latency', 0):.1f}ms",
                'error_rate': f"{metrics.get('error_rate', 0):.2%}",
                'success_rate': f"{metrics.get('success_rate', 0):.2%}",
                'total_requests': metrics.get('total_requests', 0),
                'peak_cpu': f"{results.get('resource_utilization', {}).get('peak_cpu_usage', 0):.1f}%",
                'peak_memory': f"{results.get('resource_utilization', {}).get('peak_memory_mb', 0):.1f}MB"
            }
            
        except Exception as e:
            self.logger.error(f"Error creating performance summary: {e}")
            return {'error': str(e)}
    
    def _check_resource_regression(self, current_resources: Dict, baseline: Dict) -> List[Dict]:
        """Check for resource utilization regression."""
        alerts = []
        
        try:
            # CPU regression check
            current_cpu = current_resources.get('peak_cpu_usage', 0)
            baseline_cpu = baseline.get('peak_cpu_usage', 0)
            
            if current_cpu > baseline_cpu * 1.3:  # 30% increase threshold
                alerts.append({
                    'type': 'cpu_regression',
                    'severity': 'medium',
                    'metric': 'peak_cpu_usage',
                    'baseline_value': baseline_cpu,
                    'current_value': current_cpu,
                    'message': f"Peak CPU usage increased from {baseline_cpu:.1f}% to {current_cpu:.1f}%"
                })
            
            # Memory regression check
            current_memory = current_resources.get('peak_memory_mb', 0)
            baseline_memory = baseline.get('peak_memory_mb', 0)
            
            if current_memory > baseline_memory * 1.3:  # 30% increase threshold
                alerts.append({
                    'type': 'memory_regression',
                    'severity': 'medium', 
                    'metric': 'peak_memory_mb',
                    'baseline_value': baseline_memory,
                    'current_value': current_memory,
                    'message': f"Peak memory usage increased from {baseline_memory:.1f}MB to {current_memory:.1f}MB"
                })
                
        except Exception as e:
            self.logger.error(f"Error checking resource regression: {e}")
            
        return alerts
    
    def _compare_metrics(self, current: Dict, baseline: Dict) -> Dict:
        """Compare current metrics against baseline."""
        try:
            current_metrics = current['performance_metrics']
            
            comparison = {}
            
            for metric in ['p50_latency', 'p95_latency', 'p99_latency', 'requests_per_second', 'error_rate']:
                current_val = current_metrics.get(metric, 0)
                baseline_val = baseline.get(metric, 0)
                
                if baseline_val > 0:
                    change_percent = ((current_val - baseline_val) / baseline_val) * 100
                else:
                    change_percent = 0
                
                comparison[metric] = {
                    'current': current_val,
                    'baseline': baseline_val,
                    'change_percent': change_percent,
                    'improved': change_percent < 0 if 'latency' in metric or 'error' in metric else change_percent > 0
                }
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Error comparing metrics: {e}")
            return {}
    
    def _generate_performance_recommendation(self, alerts: List[Dict]) -> str:
        """Generate performance optimization recommendation based on alerts."""
        if not alerts:
            return "Performance is within acceptable thresholds. No immediate action required."
        
        high_severity_alerts = [a for a in alerts if a.get('severity') == 'high']
        
        if high_severity_alerts:
            return "URGENT: Significant performance regression detected. Consider reverting changes or investigating algorithm modifications."
        else:
            return "Performance degradation detected. Monitor closely and consider optimization if trend continues."
    
    def _calculate_performance_score(self, current: Dict, baseline: Dict) -> float:
        """Calculate overall performance score (0-100) comparing current to baseline."""
        try:
            current_metrics = current['performance_metrics']
            
            # Weighted scoring based on key metrics
            latency_score = max(0, 100 - ((current_metrics.get('p95_latency', 0) / baseline.get('p95_latency', 1) - 1) * 100))
            throughput_score = min(100, (current_metrics.get('requests_per_second', 0) / baseline.get('requests_per_second', 1)) * 100)
            error_score = max(0, 100 - (current_metrics.get('error_rate', 0) * 1000))  # Heavily penalize errors
            
            # Weighted average
            overall_score = (latency_score * 0.4 + throughput_score * 0.4 + error_score * 0.2)
            
            return max(0, min(100, overall_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating performance score: {e}")
            return 0.0


# Global instance for use throughout the application
performance_benchmark = PerformanceBenchmark() 