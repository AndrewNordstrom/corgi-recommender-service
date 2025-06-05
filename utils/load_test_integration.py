#!/usr/bin/env python3
"""
Load Testing Integration Framework

This module provides integration between Locust load testing and the Corgi Recommendation Service
benchmark system, enabling automated load testing with result capture and analysis.

Related to TODO #27c: Implement load testing framework for concurrent recommendations

Usage:
    from utils.load_test_integration import LoadTestRunner, LoadTestAnalyzer
    
    runner = LoadTestRunner()
    results = runner.run_load_test('standard', duration_minutes=10)
    analyzer = LoadTestAnalyzer(results)
    report = analyzer.generate_report()
"""

import os
import sys
import json
import time
import subprocess
import statistics
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import yaml

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.baseline_kpi_measurement import BaselineKPIMeasurer
from db.connection import get_db_connection, get_cursor


@dataclass
class LoadTestConfiguration:
    """Configuration for load test execution"""
    scenario: str
    users: int
    spawn_rate: int
    duration_minutes: int
    host: str = "http://localhost:5011"
    user_class: str = "RecommendationUser"
    description: str = ""
    
    def to_locust_args(self) -> List[str]:
        """Convert configuration to Locust command line arguments"""
        locust_file = Path(__file__).parent.parent / "tests" / "locustfile_recommendations.py"
        
        args = [
            "locust",
            "-f", str(locust_file),
            "--host", self.host,
            "--users", str(self.users),
            "--spawn-rate", str(self.spawn_rate),
            "--run-time", f"{self.duration_minutes}m",
            "--headless",  # Run without web UI
            "--print-stats",
            "--csv", "load_test_results",  # Generate CSV output
        ]
        
        # Add user class if specified
        if self.user_class != "RecommendationUser":
            args.extend(["--tags", self.user_class])
        
        return args


@dataclass 
class LoadTestMetrics:
    """Comprehensive metrics from load test execution"""
    # Basic test info
    test_name: str
    scenario: str
    configuration: LoadTestConfiguration
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    
    # Request metrics
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    failure_rate: float
    
    # Latency metrics (milliseconds)
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    
    # Async task metrics
    total_async_tasks: int
    completed_async_tasks: int
    failed_async_tasks: int
    avg_task_completion_time: float
    p95_task_completion_time: float
    
    # Error analysis
    error_patterns: Dict[str, int]
    timeout_count: int
    connection_errors: int
    
    # Resource utilization (if available)
    peak_cpu_usage: Optional[float] = None
    peak_memory_usage: Optional[float] = None
    avg_queue_length: Optional[float] = None
    
    # KPI validation results
    kpi_violations: List[str] = None
    
    def __post_init__(self):
        if self.kpi_violations is None:
            self.kpi_violations = []


class LoadTestRunner:
    """Main class for executing load tests and capturing results"""
    
    def __init__(self):
        self.kpi_measurer = BaselineKPIMeasurer()
        self.load_test_scenarios = self._load_scenarios()
        
    def _load_scenarios(self) -> Dict[str, Dict]:
        """Load predefined load test scenarios from configuration"""
        scenarios = {
            'light': {
                'users': 10,
                'spawn_rate': 2,
                'duration_minutes': 5,
                'description': 'Light load for quick validation'
            },
            'standard': {
                'users': 25,
                'spawn_rate': 5,
                'duration_minutes': 10,
                'description': 'Standard production-like load'
            },
            'heavy': {
                'users': 50,
                'spawn_rate': 10,
                'duration_minutes': 15,
                'description': 'Heavy load stress testing'
            },
            'burst': {
                'users': 30,
                'spawn_rate': 15,
                'duration_minutes': 8,
                'user_class': 'BurstTrafficUser',
                'description': 'Burst traffic pattern testing'
            },
            'sustained': {
                'users': 40,
                'spawn_rate': 8,
                'duration_minutes': 20,
                'user_class': 'SustainedLoadUser',
                'description': 'Sustained concurrent load testing'
            },
            'stress': {
                'users': 100,
                'spawn_rate': 20,
                'duration_minutes': 10,
                'description': 'Maximum stress testing'
            }
        }
        return scenarios
    
    def run_load_test(self, scenario: str, duration_minutes: Optional[int] = None,
                     users: Optional[int] = None, spawn_rate: Optional[int] = None,
                     host: str = "http://localhost:5011") -> LoadTestMetrics:
        """
        Execute a load test scenario and return comprehensive metrics
        
        Args:
            scenario: Predefined scenario name or 'custom'
            duration_minutes: Override default duration
            users: Override default user count
            spawn_rate: Override default spawn rate
            host: Target host for testing
            
        Returns:
            LoadTestMetrics object with comprehensive results
        """
        # Get scenario configuration
        if scenario in self.load_test_scenarios:
            config_data = self.load_test_scenarios[scenario].copy()
        else:
            raise ValueError(f"Unknown scenario: {scenario}. Available: {list(self.load_test_scenarios.keys())}")
        
        # Apply overrides
        if duration_minutes:
            config_data['duration_minutes'] = duration_minutes
        if users:
            config_data['users'] = users
        if spawn_rate:
            config_data['spawn_rate'] = spawn_rate
        
        config = LoadTestConfiguration(
            scenario=scenario,
            host=host,
            **config_data
        )
        
        print(f"🚀 Starting Load Test: {scenario}")
        print(f"📊 Configuration: {config.users} users, {config.spawn_rate} spawn rate, {config.duration_minutes}min")
        print(f"🎯 Target: {config.host}")
        
        # Execute load test
        start_time = datetime.now()
        
        try:
            # Run Locust load test
            locust_results = self._execute_locust_test(config)
            
            # Capture system metrics during test
            system_metrics = self._capture_system_metrics()
            
            # Parse and analyze results
            metrics = self._parse_load_test_results(
                config, start_time, datetime.now(), locust_results, system_metrics
            )
            
            # Validate against KPIs
            self._validate_against_kpis(metrics)
            
            # Store results in database
            self._store_load_test_results(metrics)
            
            print(f"✅ Load Test Completed: {metrics.test_name}")
            print(f"📈 Results: {metrics.successful_requests}/{metrics.total_requests} successful, "
                  f"{metrics.requests_per_second:.1f} RPS, {metrics.failure_rate:.2%} failure rate")
            
            return metrics
            
        except Exception as e:
            print(f"❌ Load Test Failed: {e}")
            # Return minimal metrics object with error information
            return LoadTestMetrics(
                test_name=f"failed_load_test_{scenario}_{int(time.time())}",
                scenario=scenario,
                configuration=config,
                start_time=start_time,
                end_time=datetime.now(),
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                requests_per_second=0,
                failure_rate=1.0,
                avg_response_time=0,
                min_response_time=0,
                max_response_time=0,
                p50_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                total_async_tasks=0,
                completed_async_tasks=0,
                failed_async_tasks=0,
                avg_task_completion_time=0,
                p95_task_completion_time=0,
                error_patterns={"load_test_execution_error": 1},
                timeout_count=0,
                connection_errors=0,
                kpi_violations=[f"Load test execution failed: {str(e)}"]
            )
    
    def _execute_locust_test(self, config: LoadTestConfiguration) -> Dict[str, Any]:
        """Execute Locust load test and capture results"""
        # Create temporary directory for results
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory for CSV output
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Build Locust command
                cmd = config.to_locust_args()
                print(f"🔧 Executing: {' '.join(cmd)}")
                
                # Run Locust
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=config.duration_minutes * 60 + 120  # Add 2min buffer
                )
                
                # Parse output and CSV files
                stdout_output = result.stdout if result.stdout else ""
                stderr_output = result.stderr if result.stderr else ""
                
                # Read CSV files if they exist
                csv_data = {}
                for csv_file in ["load_test_results_stats.csv", "load_test_results_stats_history.csv"]:
                    csv_path = Path(temp_dir) / csv_file
                    if csv_path.exists():
                        with open(csv_path, 'r') as f:
                            csv_data[csv_file] = f.read()
                
                return {
                    'return_code': result.returncode,
                    'stdout': stdout_output,
                    'stderr': stderr_output,
                    'csv_data': csv_data
                }
                
            finally:
                os.chdir(original_cwd)
    
    def _capture_system_metrics(self) -> Dict[str, Any]:
        """Capture system metrics during load test"""
        try:
            import psutil
            
            # Get current system state
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            return {
                'peak_cpu_usage': cpu_percent,
                'peak_memory_usage': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'cpu_count': psutil.cpu_count()
            }
        except ImportError:
            return {}
    
    def _parse_load_test_results(self, config: LoadTestConfiguration, start_time: datetime,
                               end_time: datetime, locust_results: Dict[str, Any],
                               system_metrics: Dict[str, Any]) -> LoadTestMetrics:
        """Parse Locust results and create LoadTestMetrics object"""
        
        # Parse CSV data for detailed metrics
        stats_data = self._parse_locust_csv(locust_results.get('csv_data', {}))
        
        # Parse stdout for summary statistics
        stdout_stats = self._parse_locust_stdout(locust_results.get('stdout', ''))
        
        # Combine all metrics
        test_name = f"load_test_{config.scenario}_{int(start_time.timestamp())}"
        duration = (end_time - start_time).total_seconds()
        
        # Extract key metrics with defaults
        total_requests = stats_data.get('total_requests', 0)
        failed_requests = stats_data.get('failed_requests', 0)
        successful_requests = total_requests - failed_requests
        
        metrics = LoadTestMetrics(
            test_name=test_name,
            scenario=config.scenario,
            configuration=config,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            requests_per_second=total_requests / duration if duration > 0 else 0,
            failure_rate=failed_requests / total_requests if total_requests > 0 else 0,
            avg_response_time=stats_data.get('avg_response_time', 0),
            min_response_time=stats_data.get('min_response_time', 0),
            max_response_time=stats_data.get('max_response_time', 0),
            p50_response_time=stats_data.get('median_response_time', 0),
            p95_response_time=stats_data.get('p95_response_time', 0),
            p99_response_time=stats_data.get('p99_response_time', 0),
            total_async_tasks=stats_data.get('total_async_tasks', 0),
            completed_async_tasks=stats_data.get('completed_async_tasks', 0),
            failed_async_tasks=stats_data.get('failed_async_tasks', 0),
            avg_task_completion_time=stats_data.get('avg_task_completion_time', 0),
            p95_task_completion_time=stats_data.get('p95_task_completion_time', 0),
            error_patterns=stats_data.get('error_patterns', {}),
            timeout_count=stats_data.get('timeout_count', 0),
            connection_errors=stats_data.get('connection_errors', 0),
            peak_cpu_usage=system_metrics.get('peak_cpu_usage'),
            peak_memory_usage=system_metrics.get('peak_memory_usage'),
            avg_queue_length=stats_data.get('avg_queue_length')
        )
        
        return metrics
    
    def _parse_locust_csv(self, csv_data: Dict[str, str]) -> Dict[str, Any]:
        """Parse Locust CSV output for detailed metrics"""
        parsed_data = {}
        
        if 'load_test_results_stats.csv' in csv_data:
            # Parse main stats CSV
            lines = csv_data['load_test_results_stats.csv'].strip().split('\n')
            if len(lines) > 1:  # Has header + data
                header = lines[0].split(',')
                
                # Parse each row (each represents different endpoint)
                total_requests = 0
                total_failures = 0
                response_times = []
                
                for line in lines[1:]:
                    if line.strip() and not line.startswith('Aggregated'):
                        values = line.split(',')
                        if len(values) >= len(header):
                            row_data = dict(zip(header, values))
                            
                            # Accumulate totals
                            total_requests += int(row_data.get('Request Count', 0))
                            total_failures += int(row_data.get('Failure Count', 0))
                            
                            # Collect response times
                            try:
                                avg_rt = float(row_data.get('Average Response Time', 0))
                                if avg_rt > 0:
                                    response_times.append(avg_rt)
                            except (ValueError, TypeError):
                                pass
                
                parsed_data.update({
                    'total_requests': total_requests,
                    'failed_requests': total_failures,
                    'avg_response_time': statistics.mean(response_times) if response_times else 0,
                    'median_response_time': statistics.median(response_times) if response_times else 0,
                })
        
        return parsed_data
    
    def _parse_locust_stdout(self, stdout: str) -> Dict[str, Any]:
        """Parse Locust stdout for additional metrics"""
        parsed_data = {}
        
        # Look for summary statistics in stdout
        lines = stdout.split('\n')
        for line in lines:
            line = line.strip()
            
            # Parse different types of output
            if 'requests/s' in line.lower():
                # Extract RPS information
                pass
            elif 'response time' in line.lower():
                # Extract response time percentiles
                pass
        
        return parsed_data
    
    def _validate_against_kpis(self, metrics: LoadTestMetrics):
        """Validate load test results against defined KPIs"""
        violations = []
        
        try:
            # Use the measurer's config which is already loaded
            kpi_config = self.kpi_measurer.config
            
            # Check if we have a proper KPI config structure
            if 'kpis' not in kpi_config:
                # Use default thresholds if config structure is not available
                self._validate_with_default_thresholds(metrics, violations)
                return
            
            # Check API latency thresholds
            if metrics.p95_response_time > 0:
                try:
                    api_p95_threshold = kpi_config['kpis']['latency']['api_latency_p95']['critical_threshold']
                    if metrics.p95_response_time > api_p95_threshold:
                        violations.append(f"P95 API latency {metrics.p95_response_time:.2f}ms exceeds critical threshold {api_p95_threshold}ms")
                except KeyError:
                    # Use default threshold if not in config
                    if metrics.p95_response_time > 5000:  # 5 seconds default
                        violations.append(f"P95 API latency {metrics.p95_response_time:.2f}ms exceeds default threshold 5000ms")
            
            # Check error rate thresholds
            try:
                error_rate_threshold = kpi_config['kpis']['reliability']['api_error_rate']['critical_threshold'] / 100
                if metrics.failure_rate > error_rate_threshold:
                    violations.append(f"Error rate {metrics.failure_rate:.2%} exceeds critical threshold {error_rate_threshold:.2%}")
            except KeyError:
                # Use default threshold if not in config
                if metrics.failure_rate > 0.05:  # 5% default
                    violations.append(f"Error rate {metrics.failure_rate:.2%} exceeds default threshold 5%")
            
            # Check throughput thresholds
            try:
                min_throughput = kpi_config['kpis']['throughput']['api_requests_per_second']['critical_threshold']
                if metrics.requests_per_second < min_throughput:
                    violations.append(f"Throughput {metrics.requests_per_second:.1f} RPS below critical threshold {min_throughput} RPS")
            except KeyError:
                # Use default threshold if not in config
                if metrics.requests_per_second < 10:  # 10 RPS default
                    violations.append(f"Throughput {metrics.requests_per_second:.1f} RPS below default threshold 10 RPS")
            
            # Check resource utilization if available
            if metrics.peak_cpu_usage:
                try:
                    cpu_threshold = kpi_config['kpis']['resources']['cpu_usage_peak']['critical_threshold']
                    if metrics.peak_cpu_usage > cpu_threshold:
                        violations.append(f"Peak CPU usage {metrics.peak_cpu_usage:.1f}% exceeds critical threshold {cpu_threshold}%")
                except KeyError:
                    # Use default threshold if not in config
                    if metrics.peak_cpu_usage > 90:  # 90% default
                        violations.append(f"Peak CPU usage {metrics.peak_cpu_usage:.1f}% exceeds default threshold 90%")
            
        except Exception as e:
            violations.append(f"KPI validation error: {str(e)}")
        
        metrics.kpi_violations = violations
    
    def _validate_with_default_thresholds(self, metrics: LoadTestMetrics, violations: List[str]):
        """Validate against default thresholds when KPI config is not available"""
        # Default thresholds for load testing
        if metrics.p95_response_time > 5000:  # 5 seconds
            violations.append(f"P95 latency {metrics.p95_response_time:.2f}ms exceeds default threshold 5000ms")
        
        if metrics.failure_rate > 0.05:  # 5%
            violations.append(f"Error rate {metrics.failure_rate:.2%} exceeds default threshold 5%")
        
        if metrics.requests_per_second < 10:  # 10 RPS
            violations.append(f"Throughput {metrics.requests_per_second:.1f} RPS below default threshold 10 RPS")
        
        if metrics.peak_cpu_usage and metrics.peak_cpu_usage > 90:  # 90%
            violations.append(f"Peak CPU usage {metrics.peak_cpu_usage:.1f}% exceeds default threshold 90%")
    
    def _store_load_test_results(self, metrics: LoadTestMetrics):
        """Store load test results in database"""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Convert metrics to JSON for the results_json column
                    results_json = json.dumps({
                        'configuration': asdict(metrics.configuration),
                        'metrics': {
                            'total_requests': metrics.total_requests,
                            'successful_requests': metrics.successful_requests,
                            'failed_requests': metrics.failed_requests,
                            'requests_per_second': metrics.requests_per_second,
                            'failure_rate': metrics.failure_rate,
                            'avg_response_time': metrics.avg_response_time,
                            'p50_response_time': metrics.p50_response_time,
                            'p95_response_time': metrics.p95_response_time,
                            'p99_response_time': metrics.p99_response_time,
                            'total_async_tasks': metrics.total_async_tasks,
                            'completed_async_tasks': metrics.completed_async_tasks,
                            'avg_task_completion_time': metrics.avg_task_completion_time,
                            'p95_task_completion_time': metrics.p95_task_completion_time,
                            'peak_cpu_usage': metrics.peak_cpu_usage,
                            'peak_memory_usage': metrics.peak_memory_usage,
                            'error_patterns': metrics.error_patterns,
                            'kpi_violations': metrics.kpi_violations
                        },
                        'test_summary': {
                            'duration_seconds': metrics.duration_seconds,
                            'start_time': metrics.start_time.isoformat(),
                            'end_time': metrics.end_time.isoformat(),
                            'scenario': metrics.scenario
                        }
                    }, default=str)
                    
                    # Insert into performance_benchmarks table with existing schema compatibility
                    cursor.execute("""
                        INSERT INTO performance_benchmarks 
                        (name, description, benchmark_type, test_timestamp, 
                         concurrent_users, test_duration_seconds, total_requests,
                         p50_latency, p95_latency, p99_latency, max_latency,
                         requests_per_second, error_rate, peak_cpu_usage, peak_memory_mb,
                         test_name, test_type, results_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        metrics.test_name,  # name
                        f"Load test {metrics.scenario} scenario with {metrics.configuration.users} users",  # description
                        'load_test',  # benchmark_type  
                        metrics.start_time,  # test_timestamp
                        metrics.configuration.users,  # concurrent_users
                        int(metrics.duration_seconds),  # test_duration_seconds
                        metrics.total_requests,  # total_requests
                        metrics.p50_response_time,  # p50_latency
                        metrics.p95_response_time,  # p95_latency
                        metrics.p99_response_time,  # p99_latency
                        metrics.max_response_time,  # max_latency
                        metrics.requests_per_second,  # requests_per_second
                        metrics.failure_rate,  # error_rate
                        metrics.peak_cpu_usage,  # peak_cpu_usage
                        metrics.peak_memory_usage,  # peak_memory_mb
                        metrics.test_name,  # test_name (new column)
                        'load_test',  # test_type (new column)
                        results_json  # results_json (new column)
                    ))
                    
                    conn.commit()
                    
        except Exception as e:
            print(f"Warning: Could not store load test results in database: {e}")


class LoadTestAnalyzer:
    """Analyzer for load test results and trend analysis"""
    
    def __init__(self, metrics: LoadTestMetrics = None):
        self.metrics = metrics
        
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive load test report"""
        if not self.metrics:
            return {'error': 'No metrics provided'}
        
        # Calculate performance score
        performance_score = self._calculate_performance_score()
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        report = {
            'test_summary': {
                'test_name': self.metrics.test_name,
                'scenario': self.metrics.scenario,
                'duration_minutes': self.metrics.duration_seconds / 60,
                'users': self.metrics.configuration.users,
                'spawn_rate': self.metrics.configuration.spawn_rate
            },
            'performance_metrics': {
                'requests': {
                    'total': self.metrics.total_requests,
                    'successful': self.metrics.successful_requests,
                    'failed': self.metrics.failed_requests,
                    'requests_per_second': self.metrics.requests_per_second,
                    'failure_rate': self.metrics.failure_rate
                },
                'response_times': {
                    'average': self.metrics.avg_response_time,
                    'median': self.metrics.p50_response_time,
                    'p95': self.metrics.p95_response_time,
                    'p99': self.metrics.p99_response_time,
                    'min': self.metrics.min_response_time,
                    'max': self.metrics.max_response_time
                },
                'async_tasks': {
                    'total': self.metrics.total_async_tasks,
                    'completed': self.metrics.completed_async_tasks,
                    'failed': self.metrics.failed_async_tasks,
                    'completion_rate': (
                        self.metrics.completed_async_tasks / self.metrics.total_async_tasks 
                        if self.metrics.total_async_tasks > 0 else 0
                    ),
                    'avg_completion_time': self.metrics.avg_task_completion_time,
                    'p95_completion_time': self.metrics.p95_task_completion_time
                }
            },
            'resource_utilization': {
                'peak_cpu_usage': self.metrics.peak_cpu_usage,
                'peak_memory_usage': self.metrics.peak_memory_usage,
                'avg_queue_length': self.metrics.avg_queue_length
            },
            'error_analysis': {
                'error_patterns': self.metrics.error_patterns,
                'timeout_count': self.metrics.timeout_count,
                'connection_errors': self.metrics.connection_errors
            },
            'kpi_assessment': {
                'violations': self.metrics.kpi_violations,
                'passed': len(self.metrics.kpi_violations) == 0,
                'performance_score': performance_score
            },
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-100)"""
        score = 100.0
        
        # Deduct points for high failure rate
        score -= (self.metrics.failure_rate * 100) * 0.5
        
        # Deduct points for high response times
        if self.metrics.p95_response_time > 2000:  # 2 seconds
            score -= 20
        elif self.metrics.p95_response_time > 1000:  # 1 second
            score -= 10
        
        # Deduct points for low throughput
        if self.metrics.requests_per_second < 10:
            score -= 20
        elif self.metrics.requests_per_second < 50:
            score -= 10
        
        # Deduct points for KPI violations
        score -= len(self.metrics.kpi_violations) * 10
        
        return max(0, min(100, score))
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        if self.metrics.failure_rate > 0.01:  # > 1%
            recommendations.append("High error rate detected - investigate error patterns and system logs")
        
        if self.metrics.p95_response_time > 2000:  # > 2 seconds
            recommendations.append("High P95 response time - consider optimizing database queries or adding caching")
        
        if self.metrics.requests_per_second < 50:
            recommendations.append("Low throughput - consider increasing worker processes or optimizing algorithm")
        
        if self.metrics.peak_cpu_usage and self.metrics.peak_cpu_usage > 80:
            recommendations.append("High CPU usage detected - consider horizontal scaling or code optimization")
        
        if self.metrics.peak_memory_usage and self.metrics.peak_memory_usage > 80:
            recommendations.append("High memory usage detected - investigate for memory leaks or optimize data structures")
        
        if self.metrics.kpi_violations:
            recommendations.append("KPI violations detected - review system performance and consider scaling")
        
        if not recommendations:
            recommendations.append("Performance looks good - system is handling the load well")
        
        return recommendations
    
    @staticmethod
    def compare_load_tests(metrics_list: List[LoadTestMetrics]) -> Dict[str, Any]:
        """Compare multiple load test results"""
        if len(metrics_list) < 2:
            return {'error': 'Need at least 2 test results for comparison'}
        
        comparison = {
            'test_count': len(metrics_list),
            'scenarios': [m.scenario for m in metrics_list],
            'throughput_comparison': {
                'values': [m.requests_per_second for m in metrics_list],
                'min': min(m.requests_per_second for m in metrics_list),
                'max': max(m.requests_per_second for m in metrics_list),
                'avg': statistics.mean(m.requests_per_second for m in metrics_list)
            },
            'latency_comparison': {
                'p95_values': [m.p95_response_time for m in metrics_list],
                'p95_min': min(m.p95_response_time for m in metrics_list),
                'p95_max': max(m.p95_response_time for m in metrics_list),
                'p95_avg': statistics.mean(m.p95_response_time for m in metrics_list)
            },
            'error_rate_comparison': {
                'values': [m.failure_rate for m in metrics_list],
                'min': min(m.failure_rate for m in metrics_list),
                'max': max(m.failure_rate for m in metrics_list),
                'avg': statistics.mean(m.failure_rate for m in metrics_list)
            }
        }
        
        return comparison 