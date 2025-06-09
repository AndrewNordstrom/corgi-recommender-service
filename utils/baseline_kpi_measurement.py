"""
Baseline KPI Measurement Module

This module implements comprehensive measurement functions for all baseline performance KPIs
defined for the Corgi Recommendation Service. It provides the foundation for establishing
performance baselines and conducting regression analysis.

Related to TODO #27a: Define baseline performance KPIs and measurement methodology
"""

import time
import statistics
import psutil
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import yaml

import requests
from db.connection import get_db_connection, get_cursor
from utils.performance_benchmarking import PerformanceBenchmark
from core.ranking_algorithm import generate_rankings_for_user
from utils.recommendation_metrics import collect_recommendation_quality_metrics

logger = logging.getLogger(__name__)

@dataclass
class KPIMeasurement:
    """Data class for storing KPI measurement results."""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    sample_size: int
    confidence_interval: Optional[Tuple[float, float]] = None
    metadata: Optional[Dict[str, Any]] = None

class BaselineKPIMeasurer:
    """Comprehensive KPI measurement system for performance baselines."""
    
    def __init__(self, config_path: str = "config/baseline_kpis.yaml"):
        """
        Initialize the KPI measurement system.
        
        Args:
            config_path: Path to the KPI configuration file
        """
        # Initialize logger FIRST before using it in other methods
        self.logger = logging.getLogger(__name__)
        self.config = self._load_kpi_config(config_path)
        self.base_url = "http://localhost:5011"  # Updated for current port
        
    def _load_kpi_config(self, config_path: str) -> Dict[str, Any]:
        """Load KPI configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"KPI config file not found: {config_path}. Using defaults.")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default KPI configuration if config file is not available."""
        return {
            'statistics': {
                'sample_size_minimum': 30,
                'confidence_level': 0.95,
                'outlier_threshold_std_dev': 3
            },
            'measurement': {
                'warmup_period_seconds': 60,
                'measurement_period_seconds': 300,
                'iterations': 10
            }
        }
    
    def measure_all_kpis(self, scenario: str = "standard") -> Dict[str, KPIMeasurement]:
        """
        Measure all defined KPIs for a given scenario.
        
        Args:
            scenario: Test scenario (light, standard, heavy, stress)
            
        Returns:
            Dictionary of KPI measurements
        """
        self.logger.info(f"Starting comprehensive KPI measurement for scenario: {scenario}")
        
        measurements = {}
        
        # 1. Latency Metrics
        latency_measurements = self._measure_latency_metrics(scenario)
        measurements.update(latency_measurements)
        
        # 2. Throughput Metrics
        throughput_measurements = self._measure_throughput_metrics(scenario)
        measurements.update(throughput_measurements)
        
        # 3. Resource Utilization Metrics
        resource_measurements = self._measure_resource_metrics(scenario)
        measurements.update(resource_measurements)
        
        # 4. Quality vs Performance Metrics
        quality_measurements = self._measure_quality_performance_metrics(scenario)
        measurements.update(quality_measurements)
        
        # 5. Reliability Metrics
        reliability_measurements = self._measure_reliability_metrics(scenario)
        measurements.update(reliability_measurements)
        
        self.logger.info(f"Completed KPI measurement. Collected {len(measurements)} metrics.")
        return measurements
    
    def _measure_latency_metrics(self, scenario: str) -> Dict[str, KPIMeasurement]:
        """Measure all latency-related KPIs."""
        self.logger.info("Measuring latency metrics...")
        measurements = {}
        
        # Get test users for the scenario
        test_users = self._get_scenario_test_users(scenario)
        sample_size = len(test_users)
        
        # Measure algorithm latency
        algorithm_latencies = []
        api_latencies = []
        db_query_latencies = []
        
        for user_id in test_users:
            # Algorithm-only latency
            algo_latency = self._measure_algorithm_latency_single(user_id)
            if algo_latency is not None:
                algorithm_latencies.append(algo_latency)
            
            # End-to-end API latency
            api_latency = self._measure_api_latency_single(user_id)
            if api_latency is not None:
                api_latencies.append(api_latency)
            
            # Database query latency (sampled)
            if len(db_query_latencies) < sample_size // 3:  # Sample 1/3 for efficiency
                db_latency = self._measure_db_query_latency_single(user_id)
                if db_latency is not None:
                    db_query_latencies.append(db_latency)
        
        # Calculate percentiles for algorithm latency
        if algorithm_latencies:
            measurements['algorithm_latency_p50'] = KPIMeasurement(
                metric_name='algorithm_latency_p50',
                value=statistics.quantiles(algorithm_latencies, n=2)[0],
                unit='milliseconds',
                timestamp=datetime.now(),
                sample_size=len(algorithm_latencies),
                confidence_interval=self._calculate_confidence_interval(algorithm_latencies, 0.50)
            )
            
            measurements['algorithm_latency_p95'] = KPIMeasurement(
                metric_name='algorithm_latency_p95',
                value=statistics.quantiles(algorithm_latencies, n=20)[18],  # 95th percentile
                unit='milliseconds',
                timestamp=datetime.now(),
                sample_size=len(algorithm_latencies),
                confidence_interval=self._calculate_confidence_interval(algorithm_latencies, 0.95)
            )
            
            measurements['algorithm_latency_p99'] = KPIMeasurement(
                metric_name='algorithm_latency_p99',
                value=statistics.quantiles(algorithm_latencies, n=100)[98],  # 99th percentile
                unit='milliseconds',
                timestamp=datetime.now(),
                sample_size=len(algorithm_latencies),
                confidence_interval=self._calculate_confidence_interval(algorithm_latencies, 0.99)
            )
        
        # Calculate percentiles for API latency
        if api_latencies:
            measurements['api_latency_p50'] = KPIMeasurement(
                metric_name='api_latency_p50',
                value=statistics.quantiles(api_latencies, n=2)[0],
                unit='milliseconds',
                timestamp=datetime.now(),
                sample_size=len(api_latencies)
            )
            
            measurements['api_latency_p95'] = KPIMeasurement(
                metric_name='api_latency_p95',
                value=statistics.quantiles(api_latencies, n=20)[18],
                unit='milliseconds',
                timestamp=datetime.now(),
                sample_size=len(api_latencies)
            )
            
            measurements['api_latency_p99'] = KPIMeasurement(
                metric_name='api_latency_p99',
                value=statistics.quantiles(api_latencies, n=100)[98],
                unit='milliseconds',
                timestamp=datetime.now(),
                sample_size=len(api_latencies)
            )
        
        # Calculate percentiles for database query latency
        if db_query_latencies:
            measurements['db_query_latency_p95'] = KPIMeasurement(
                metric_name='db_query_latency_p95',
                value=statistics.quantiles(db_query_latencies, n=20)[18],
                unit='milliseconds',
                timestamp=datetime.now(),
                sample_size=len(db_query_latencies)
            )
            
            measurements['db_query_latency_p99'] = KPIMeasurement(
                metric_name='db_query_latency_p99',
                value=statistics.quantiles(db_query_latencies, n=100)[98],
                unit='milliseconds',
                timestamp=datetime.now(),
                sample_size=len(db_query_latencies)
            )
        
        # Measure async task latencies (if applicable)
        async_measurements = self._measure_async_task_latencies(test_users[:10])  # Sample subset
        measurements.update(async_measurements)
        
        return measurements
    
    def _measure_throughput_metrics(self, scenario: str) -> Dict[str, KPIMeasurement]:
        """Measure all throughput-related KPIs."""
        self.logger.info("Measuring throughput metrics...")
        measurements = {}
        
        # API throughput measurement
        api_throughput = self._measure_api_throughput(scenario)
        if api_throughput:
            measurements['api_requests_per_second'] = KPIMeasurement(
                metric_name='api_requests_per_second',
                value=api_throughput['requests_per_second'],
                unit='requests_per_second',
                timestamp=datetime.now(),
                sample_size=api_throughput['total_requests']
            )
            
            measurements['api_recommendations_per_second'] = KPIMeasurement(
                metric_name='api_recommendations_per_second',
                value=api_throughput['recommendations_per_second'],
                unit='recommendations_per_second',
                timestamp=datetime.now(),
                sample_size=api_throughput['total_requests']
            )
        
        # Algorithm-only throughput
        algorithm_throughput = self._measure_algorithm_throughput(scenario)
        if algorithm_throughput:
            measurements['algorithm_executions_per_second'] = KPIMeasurement(
                metric_name='algorithm_executions_per_second',
                value=algorithm_throughput,
                unit='executions_per_second',
                timestamp=datetime.now(),
                sample_size=100  # Default sample size for algorithm test
            )
        
        # Celery throughput (if workers are available)
        celery_throughput = self._measure_celery_throughput(scenario)
        if celery_throughput:
            measurements.update(celery_throughput)
        
        return measurements
    
    def _measure_resource_metrics(self, scenario: str) -> Dict[str, KPIMeasurement]:
        """Measure all resource utilization KPIs."""
        self.logger.info("Measuring resource utilization metrics...")
        measurements = {}
        
        # Monitor resources during a representative workload
        with self._monitor_resources() as monitor:
            # Run representative workload
            test_users = self._get_scenario_test_users(scenario)[:20]  # Sample subset
            for user_id in test_users:
                try:
                    # Generate recommendations to simulate load
                    generate_rankings_for_user(user_id)
                    time.sleep(0.1)  # Small delay between requests
                except Exception as e:
                    self.logger.warning(f"Error generating recommendations for {user_id}: {e}")
        
        resource_data = monitor.get_metrics()
        
        # CPU Utilization
        if 'cpu_percent' in resource_data:
            measurements['cpu_usage_average'] = KPIMeasurement(
                metric_name='cpu_usage_average',
                value=statistics.mean(resource_data['cpu_percent']),
                unit='percentage',
                timestamp=datetime.now(),
                sample_size=len(resource_data['cpu_percent'])
            )
            
            measurements['cpu_usage_peak'] = KPIMeasurement(
                metric_name='cpu_usage_peak',
                value=max(resource_data['cpu_percent']),
                unit='percentage',
                timestamp=datetime.now(),
                sample_size=len(resource_data['cpu_percent'])
            )
        
        # Memory Utilization
        if 'memory_mb' in resource_data:
            measurements['memory_usage_peak'] = KPIMeasurement(
                metric_name='memory_usage_peak',
                value=max(resource_data['memory_mb']),
                unit='megabytes',
                timestamp=datetime.now(),
                sample_size=len(resource_data['memory_mb'])
            )
            
            # Calculate per-recommendation memory usage
            if len(test_users) > 0:
                memory_per_recommendation = statistics.mean(resource_data['memory_mb']) / len(test_users)
                measurements['memory_usage_per_recommendation'] = KPIMeasurement(
                    metric_name='memory_usage_per_recommendation',
                    value=memory_per_recommendation,
                    unit='megabytes',
                    timestamp=datetime.now(),
                    sample_size=len(test_users)
                )
        
        # Database resource utilization
        db_metrics = self._measure_database_resource_utilization()
        measurements.update(db_metrics)
        
        return measurements
    
    def _measure_quality_performance_metrics(self, scenario: str) -> Dict[str, KPIMeasurement]:
        """Measure quality vs performance trade-off KPIs."""
        self.logger.info("Measuring quality vs performance metrics...")
        measurements = {}
        
        # Measure quality computation overhead
        test_users = self._get_scenario_test_users(scenario)[:10]  # Sample subset
        
        # Measure without quality metrics
        latencies_without_quality = []
        for user_id in test_users:
            start_time = time.time()
            try:
                # Generate rankings without quality metrics collection
                generate_rankings_for_user(user_id)
            except Exception as e:
                self.logger.warning(f"Error in quality measurement for {user_id}: {e}")
                continue
            latencies_without_quality.append((time.time() - start_time) * 1000)
        
        # Measure with quality metrics
        latencies_with_quality = []
        for user_id in test_users:
            start_time = time.time()
            try:
                # Generate rankings and collect quality metrics
                rankings = generate_rankings_for_user(user_id)
                if rankings:
                    collect_recommendation_quality_metrics(user_id, rankings[:20])
            except Exception as e:
                self.logger.warning(f"Error in quality measurement for {user_id}: {e}")
                continue
            latencies_with_quality.append((time.time() - start_time) * 1000)
        
        # Calculate overhead
        if latencies_without_quality and latencies_with_quality:
            avg_without = statistics.mean(latencies_without_quality)
            avg_with = statistics.mean(latencies_with_quality)
            overhead_percentage = ((avg_with - avg_without) / avg_without) * 100
            
            measurements['quality_computation_overhead'] = KPIMeasurement(
                metric_name='quality_computation_overhead',
                value=overhead_percentage,
                unit='percentage_overhead',
                timestamp=datetime.now(),
                sample_size=len(test_users)
            )
            
            measurements['quality_latency_impact'] = KPIMeasurement(
                metric_name='quality_latency_impact',
                value=overhead_percentage,
                unit='percentage_increase',
                timestamp=datetime.now(),
                sample_size=len(test_users)
            )
        
        return measurements
    
    def _measure_reliability_metrics(self, scenario: str) -> Dict[str, KPIMeasurement]:
        """Measure reliability and error rate KPIs."""
        self.logger.info("Measuring reliability metrics...")
        measurements = {}
        
        # API error rate measurement
        test_users = self._get_scenario_test_users(scenario)
        total_requests = 0
        successful_requests = 0
        timeout_count = 0
        error_5xx_count = 0
        
        for user_id in test_users:
            try:
                start_time = time.time()
                response = requests.get(
                    f"{self.base_url}/api/recommendations/{user_id}",
                    timeout=30
                )
                duration = time.time() - start_time
                
                total_requests += 1
                
                if response.status_code == 200:
                    successful_requests += 1
                elif response.status_code >= 500:
                    error_5xx_count += 1
                    
            except requests.Timeout:
                timeout_count += 1
                total_requests += 1
            except Exception as e:
                total_requests += 1
                self.logger.warning(f"Request error for {user_id}: {e}")
        
        if total_requests > 0:
            error_rate = ((total_requests - successful_requests) / total_requests) * 100
            timeout_rate = (timeout_count / total_requests) * 100
            error_5xx_rate = (error_5xx_count / total_requests) * 100
            
            measurements['api_error_rate'] = KPIMeasurement(
                metric_name='api_error_rate',
                value=error_rate,
                unit='percentage',
                timestamp=datetime.now(),
                sample_size=total_requests
            )
            
            measurements['api_timeout_rate'] = KPIMeasurement(
                metric_name='api_timeout_rate',
                value=timeout_rate,
                unit='percentage',
                timestamp=datetime.now(),
                sample_size=total_requests
            )
            
            measurements['api_5xx_rate'] = KPIMeasurement(
                metric_name='api_5xx_rate',
                value=error_5xx_rate,
                unit='percentage',
                timestamp=datetime.now(),
                sample_size=total_requests
            )
        
        return measurements
    
    # Helper methods for individual KPI measurements
    
    def _measure_algorithm_latency_single(self, user_id: str) -> Optional[float]:
        """Measure latency for a single algorithm execution."""
        try:
            start_time = time.perf_counter()
            generate_rankings_for_user(user_id)
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000  # Convert to milliseconds
        except Exception as e:
            self.logger.warning(f"Algorithm latency measurement failed for {user_id}: {e}")
            return None
    
    def _measure_api_latency_single(self, user_id: str) -> Optional[float]:
        """Measure end-to-end API latency for a single request."""
        try:
            start_time = time.perf_counter()
            response = requests.get(
                f"{self.base_url}/api/recommendations/{user_id}",
                timeout=30
            )
            end_time = time.perf_counter()
            
            if response.status_code == 200:
                return (end_time - start_time) * 1000  # Convert to milliseconds
            else:
                return None
        except Exception as e:
            self.logger.warning(f"API latency measurement failed for {user_id}: {e}")
            return None
    
    def _measure_db_query_latency_single(self, user_id: str) -> Optional[float]:
        """Measure database query latency for recommendation-related queries."""
        try:
            start_time = time.perf_counter()
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Measure a representative query
                    cursor.execute("""
                        SELECT COUNT(*) FROM interactions 
                        WHERE user_alias = %s AND created_at >= NOW() - INTERVAL '7 days'
                    """, (user_id,))
                    cursor.fetchone()
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000  # Convert to milliseconds
        except Exception as e:
            self.logger.warning(f"DB query latency measurement failed for {user_id}: {e}")
            return None
    
    def _measure_async_task_latencies(self, test_users: List[str]) -> Dict[str, KPIMeasurement]:
        """Measure asynchronous task latencies."""
        # This is a placeholder - actual implementation would depend on Celery setup
        measurements = {}
        
        # For now, return placeholder measurements
        measurements['async_queue_latency_p95'] = KPIMeasurement(
            metric_name='async_queue_latency_p95',
            value=50.0,  # Placeholder
            unit='milliseconds',
            timestamp=datetime.now(),
            sample_size=len(test_users),
            metadata={'note': 'Placeholder - requires Celery integration'}
        )
        
        measurements['async_completion_latency_p95'] = KPIMeasurement(
            metric_name='async_completion_latency_p95',
            value=1200.0,  # Placeholder
            unit='milliseconds',
            timestamp=datetime.now(),
            sample_size=len(test_users),
            metadata={'note': 'Placeholder - requires Celery integration'}
        )
        
        return measurements
    
    def _measure_api_throughput(self, scenario: str) -> Optional[Dict[str, float]]:
        """Measure API throughput using concurrent requests."""
        test_users = self._get_scenario_test_users(scenario)[:50]  # Limit for throughput test
        duration = 60  # 1 minute test
        
        start_time = time.time()
        successful_requests = 0
        total_requests = 0
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            # Submit requests for the duration
            while time.time() - start_time < duration:
                for user_id in test_users[:10]:  # Rotate through subset
                    if time.time() - start_time >= duration:
                        break
                    future = executor.submit(self._single_api_request, user_id)
                    futures.append(future)
                    total_requests += 1
            
            # Collect results
            for future in as_completed(futures):
                if future.result():
                    successful_requests += 1
        
        actual_duration = time.time() - start_time
        
        if actual_duration > 0:
            return {
                'requests_per_second': successful_requests / actual_duration,
                'recommendations_per_second': successful_requests / actual_duration,  # 1:1 ratio
                'total_requests': total_requests,
                'successful_requests': successful_requests
            }
        
        return None
    
    def _measure_algorithm_throughput(self, scenario: str) -> Optional[float]:
        """Measure pure algorithm execution throughput."""
        test_users = self._get_scenario_test_users(scenario)[:100]
        duration = 30  # 30 second test
        
        start_time = time.time()
        executions = 0
        
        for user_id in test_users:
            if time.time() - start_time >= duration:
                break
            try:
                generate_rankings_for_user(user_id)
                executions += 1
            except Exception as e:
                self.logger.warning(f"Algorithm execution failed for {user_id}: {e}")
        
        actual_duration = time.time() - start_time
        
        if actual_duration > 0:
            return executions / actual_duration
        
        return None
    
    def _measure_celery_throughput(self, scenario: str) -> Dict[str, KPIMeasurement]:
        """Measure Celery task throughput."""
        # Placeholder - actual implementation would require Celery integration
        measurements = {}
        
        measurements['celery_tasks_per_second'] = KPIMeasurement(
            metric_name='celery_tasks_per_second',
            value=25.0,  # Placeholder
            unit='tasks_per_second',
            timestamp=datetime.now(),
            sample_size=100,
            metadata={'note': 'Placeholder - requires Celery integration'}
        )
        
        measurements['celery_recommendations_per_second'] = KPIMeasurement(
            metric_name='celery_recommendations_per_second',
            value=25.0,  # Placeholder
            unit='recommendations_per_second',
            timestamp=datetime.now(),
            sample_size=100,
            metadata={'note': 'Placeholder - requires Celery integration'}
        )
        
        return measurements
    
    def _measure_database_resource_utilization(self) -> Dict[str, KPIMeasurement]:
        """Measure database resource utilization."""
        measurements = {}
        
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Get connection count (PostgreSQL specific)
                    try:
                        cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
                        active_connections = cursor.fetchone()[0]
                        
                        measurements['db_connections_active'] = KPIMeasurement(
                            metric_name='db_connections_active',
                            value=float(active_connections),
                            unit='connections',
                            timestamp=datetime.now(),
                            sample_size=1
                        )
                    except Exception:
                        # Fallback for SQLite or other databases
                        measurements['db_connections_active'] = KPIMeasurement(
                            metric_name='db_connections_active',
                            value=1.0,  # Single connection for SQLite
                            unit='connections',
                            timestamp=datetime.now(),
                            sample_size=1
                        )
        except Exception as e:
            self.logger.warning(f"Database resource measurement failed: {e}")
        
        return measurements
    
    @contextmanager
    def _monitor_resources(self):
        """Context manager for monitoring system resources."""
        class ResourceMonitor:
            def __init__(self):
                self.cpu_data = []
                self.memory_data = []
                self.monitoring = True
                
            def start_monitoring(self):
                import threading
                def monitor():
                    while self.monitoring:
                        try:
                            self.cpu_data.append(psutil.cpu_percent(interval=0.1))
                            memory_info = psutil.virtual_memory()
                            self.memory_data.append(memory_info.used / (1024 * 1024))  # MB
                        except Exception:
                            pass
                        time.sleep(0.5)
                
                self.thread = threading.Thread(target=monitor)
                self.thread.start()
            
            def stop_monitoring(self):
                self.monitoring = False
                if hasattr(self, 'thread'):
                    self.thread.join()
            
            def get_metrics(self):
                return {
                    'cpu_percent': self.cpu_data,
                    'memory_mb': self.memory_data
                }
        
        monitor = ResourceMonitor()
        monitor.start_monitoring()
        try:
            yield monitor
        finally:
            monitor.stop_monitoring()
    
    def _single_api_request(self, user_id: str) -> bool:
        """Make a single API request and return success status."""
        try:
            response = requests.get(
                f"{self.base_url}/api/recommendations/{user_id}",
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _get_scenario_test_users(self, scenario: str) -> List[str]:
        """Get test users for a specific scenario."""
        scenario_config = self.config.get('test_scenarios', {}).get(scenario, {})
        user_count = scenario_config.get('users', 100)
        
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT DISTINCT user_alias 
                        FROM interactions 
                        WHERE created_at >= NOW() - INTERVAL '30 days'
                        ORDER BY RANDOM()
                        LIMIT %s
                    """, (user_count,))
                    
                    return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting test users: {e}")
            return []
    
    def _calculate_confidence_interval(self, data: List[float], percentile: float) -> Tuple[float, float]:
        """Calculate confidence interval for a given percentile."""
        if len(data) < 2:
            return (0.0, 0.0)
        
        try:
            # Simple bootstrap confidence interval
            import random
            bootstrap_samples = []
            for _ in range(1000):
                sample = random.choices(data, k=len(data))
                if percentile <= 0.5:
                    bootstrap_samples.append(statistics.quantiles(sample, n=2)[int(percentile * 2)])
                elif percentile <= 0.95:
                    bootstrap_samples.append(statistics.quantiles(sample, n=20)[int(percentile * 20) - 1])
                else:
                    bootstrap_samples.append(statistics.quantiles(sample, n=100)[int(percentile * 100) - 1])
            
            bootstrap_samples.sort()
            lower = bootstrap_samples[25]  # 2.5th percentile
            upper = bootstrap_samples[975]  # 97.5th percentile
            
            return (lower, upper)
        except Exception:
            return (0.0, 0.0)
    
    def generate_baseline_report(self, measurements: Dict[str, KPIMeasurement]) -> Dict[str, Any]:
        """Generate a comprehensive baseline report from measurements."""
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_kpis_measured': len(measurements),
                'measurement_tool': 'BaselineKPIMeasurer v1.0'
            },
            'kpi_results': {},
            'validation': {
                'all_kpis_within_targets': True,
                'failed_validations': [],
                'warnings': []
            },
            'recommendations': []
        }
        
        # Convert measurements to report format
        for metric_name, measurement in measurements.items():
            report['kpi_results'][metric_name] = {
                'value': measurement.value,
                'unit': measurement.unit,
                'sample_size': measurement.sample_size,
                'confidence_interval': measurement.confidence_interval,
                'metadata': measurement.metadata
            }
            
            # Validate against targets
            kpi_config = self._find_kpi_config(metric_name)
            if kpi_config:
                target = kpi_config.get('target_baseline')
                warning_threshold = kpi_config.get('warning_threshold')
                critical_threshold = kpi_config.get('critical_threshold')
                
                if critical_threshold and measurement.value > critical_threshold:
                    report['validation']['failed_validations'].append({
                        'metric': metric_name,
                        'value': measurement.value,
                        'threshold': critical_threshold,
                        'severity': 'critical'
                    })
                    report['validation']['all_kpis_within_targets'] = False
                elif warning_threshold and measurement.value > warning_threshold:
                    report['validation']['warnings'].append({
                        'metric': metric_name,
                        'value': measurement.value,
                        'threshold': warning_threshold,
                        'severity': 'warning'
                    })
        
        return report
    
    def _find_kpi_config(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Find configuration for a specific KPI metric."""
        kpis = self.config.get('kpis', {})
        for category in kpis.values():
            if isinstance(category, dict):
                for kpi_key, kpi_config in category.items():
                    if kpi_config.get('metric_name') == metric_name:
                        return kpi_config
        return None 