#!/usr/bin/env python3
"""
Load Testing Runner Script

Comprehensive command-line interface for running concurrent load tests on the 
Corgi Recommendation Service using Locust integration framework.

Related to TODO #27c: Implement load testing framework for concurrent recommendations

Usage:
    python3 scripts/run_load_tests.py --scenario standard
    python3 scripts/run_load_tests.py --scenario heavy --duration 20 --users 75
    python3 scripts/run_load_tests.py --ramp-up-test --max-users 200
    python3 scripts/run_load_tests.py --compare-scenarios light,standard,heavy
"""

import argparse
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.load_test_integration import LoadTestRunner, LoadTestAnalyzer, LoadTestMetrics


class LoadTestCLI:
    """Command-line interface for load testing"""
    
    def __init__(self):
        self.runner = LoadTestRunner()
        
    def run_single_scenario(self, scenario: str, users: Optional[int] = None,
                          duration_minutes: Optional[int] = None, 
                          spawn_rate: Optional[int] = None,
                          host: str = "http://localhost:5011",
                          generate_report: bool = False) -> LoadTestMetrics:
        """Run a single load test scenario"""
        
        print(f"🎯 Running Load Test Scenario: {scenario.upper()}")
        print("=" * 60)
        
        # Execute load test
        metrics = self.runner.run_load_test(
            scenario=scenario,
            duration_minutes=duration_minutes,
            users=users,
            spawn_rate=spawn_rate,
            host=host
        )
        
        # Generate report if requested
        if generate_report:
            analyzer = LoadTestAnalyzer(metrics)
            report = analyzer.generate_report()
            report_path = self._save_report(report, f"load_test_{scenario}")
            print(f"📄 Detailed report saved to: {report_path}")
        
        # Print summary
        self._print_metrics_summary(metrics)
        
        return metrics
    
    def run_ramp_up_test(self, max_users: int = 100, step_size: int = 5, 
                        step_duration: int = 2, host: str = "http://localhost:5011") -> List[LoadTestMetrics]:
        """Run ramp-up load test to find breaking point"""
        
        print(f"🚀 Running Ramp-up Load Test")
        print(f"📈 Ramping from 1 to {max_users} users in steps of {step_size}")
        print("=" * 60)
        
        results = []
        current_users = 1
        
        while current_users <= max_users:
            print(f"\n🔄 Testing with {current_users} concurrent users...")
            
            try:
                # Run test with current user count
                metrics = self.runner.run_load_test(
                    scenario='custom',
                    users=current_users,
                    spawn_rate=min(current_users, 10),  # Reasonable spawn rate
                    duration_minutes=step_duration,
                    host=host
                )
                
                results.append(metrics)
                
                # Check if we're hitting performance limits
                if (metrics.failure_rate > 0.05 or  # > 5% failure rate
                    metrics.p95_response_time > 5000 or  # > 5 second P95
                    len(metrics.kpi_violations) > 2):  # Multiple KPI violations
                    
                    print(f"⚠️  Performance degradation detected at {current_users} users")
                    print(f"   Failure Rate: {metrics.failure_rate:.2%}")
                    print(f"   P95 Latency: {metrics.p95_response_time:.1f}ms")
                    print(f"   KPI Violations: {len(metrics.kpi_violations)}")
                    
                    # Continue but warn we're approaching limits
                    if metrics.failure_rate > 0.15 or metrics.p95_response_time > 10000:
                        print(f"🛑 Severe performance degradation - stopping ramp-up test")
                        break
                
                current_users += step_size
                
                # Brief pause between tests to let system recover
                if current_users <= max_users:
                    print(f"⏸️  Brief cooldown period...")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"❌ Load test failed at {current_users} users: {e}")
                break
        
        # Analyze ramp-up results
        self._analyze_ramp_up_results(results)
        
        return results
    
    def compare_scenarios(self, scenarios: List[str], host: str = "http://localhost:5011") -> Dict:
        """Run and compare multiple load test scenarios"""
        
        print(f"🔄 Running Comparative Load Test")
        print(f"📊 Scenarios: {', '.join(scenarios)}")
        print("=" * 60)
        
        results = []
        
        for scenario in scenarios:
            print(f"\n🎯 Running scenario: {scenario}")
            try:
                metrics = self.runner.run_load_test(scenario=scenario, host=host)
                results.append(metrics)
                print(f"✅ Completed {scenario}: {metrics.requests_per_second:.1f} RPS, "
                      f"{metrics.failure_rate:.2%} failure rate")
                
                # Cooldown between scenarios
                if scenario != scenarios[-1]:  # Not the last scenario
                    print("⏸️  Cooldown between scenarios...")
                    time.sleep(15)
                    
            except Exception as e:
                print(f"❌ Scenario {scenario} failed: {e}")
        
        # Generate comparison report
        if len(results) >= 2:
            comparison = LoadTestAnalyzer.compare_load_tests(results)
            self._print_comparison_results(comparison, results)
            
            # Save comparison report
            report_data = {
                'comparison': comparison,
                'individual_results': [
                    LoadTestAnalyzer(metrics).generate_report() 
                    for metrics in results
                ]
            }
            report_path = self._save_report(report_data, "load_test_comparison")
            print(f"📄 Comparison report saved to: {report_path}")
            
            return comparison
        else:
            print("⚠️  Need at least 2 successful scenarios for comparison")
            return {}
    
    def run_burst_traffic_test(self, baseline_users: int = 10, burst_users: int = 50,
                             burst_duration: int = 3, total_duration: int = 15,
                             host: str = "http://localhost:5011") -> LoadTestMetrics:
        """Run burst traffic test to simulate traffic spikes"""
        
        print(f"💥 Running Burst Traffic Test")
        print(f"📊 Baseline: {baseline_users} users, Burst: {burst_users} users for {burst_duration}min")
        print("=" * 60)
        
        # Run burst traffic test using BurstTrafficUser
        metrics = self.runner.run_load_test(
            scenario='burst',
            users=burst_users,
            duration_minutes=total_duration,
            spawn_rate=min(burst_users // 2, 20),  # Rapid spawn for burst
            host=host
        )
        
        print(f"💥 Burst test completed")
        self._print_metrics_summary(metrics)
        
        return metrics
    
    def _print_metrics_summary(self, metrics: LoadTestMetrics):
        """Print formatted summary of load test metrics"""
        
        print(f"\n📊 LOAD TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"Test: {metrics.test_name}")
        print(f"Scenario: {metrics.scenario}")
        print(f"Duration: {metrics.duration_seconds / 60:.1f} minutes")
        print(f"Configuration: {metrics.configuration.users} users, {metrics.configuration.spawn_rate} spawn rate")
        
        print(f"\n📈 Request Metrics:")
        print(f"  Total Requests: {metrics.total_requests:,}")
        print(f"  Successful: {metrics.successful_requests:,} ({metrics.successful_requests/metrics.total_requests*100:.1f}%)")
        print(f"  Failed: {metrics.failed_requests:,} ({metrics.failure_rate:.2%})")
        print(f"  Throughput: {metrics.requests_per_second:.1f} requests/second")
        
        print(f"\n⏱️  Response Time Metrics:")
        print(f"  Average: {metrics.avg_response_time:.1f}ms")
        print(f"  Median (P50): {metrics.p50_response_time:.1f}ms")
        print(f"  P95: {metrics.p95_response_time:.1f}ms")
        print(f"  P99: {metrics.p99_response_time:.1f}ms")
        print(f"  Min/Max: {metrics.min_response_time:.1f}ms / {metrics.max_response_time:.1f}ms")
        
        if metrics.total_async_tasks > 0:
            print(f"\n🔄 Async Task Metrics:")
            print(f"  Total Tasks: {metrics.total_async_tasks:,}")
            print(f"  Completed: {metrics.completed_async_tasks:,}")
            print(f"  Failed: {metrics.failed_async_tasks:,}")
            completion_rate = metrics.completed_async_tasks / metrics.total_async_tasks * 100
            print(f"  Completion Rate: {completion_rate:.1f}%")
            print(f"  Avg Completion Time: {metrics.avg_task_completion_time:.1f}ms")
            print(f"  P95 Completion Time: {metrics.p95_task_completion_time:.1f}ms")
        
        if metrics.peak_cpu_usage or metrics.peak_memory_usage:
            print(f"\n💻 Resource Utilization:")
            if metrics.peak_cpu_usage:
                print(f"  Peak CPU: {metrics.peak_cpu_usage:.1f}%")
            if metrics.peak_memory_usage:
                print(f"  Peak Memory: {metrics.peak_memory_usage:.1f}%")
        
        if metrics.error_patterns:
            print(f"\n❌ Error Patterns:")
            for error, count in metrics.error_patterns.items():
                print(f"  {error}: {count} occurrences")
        
        # KPI Assessment
        print(f"\n🎯 KPI Assessment:")
        if metrics.kpi_violations:
            print(f"  ❌ KPI Violations ({len(metrics.kpi_violations)}):")
            for violation in metrics.kpi_violations:
                print(f"    • {violation}")
        else:
            print(f"  ✅ All KPIs within acceptable thresholds")
        
        # Performance score
        analyzer = LoadTestAnalyzer(metrics)
        score = analyzer._calculate_performance_score()
        print(f"  📊 Performance Score: {score:.1f}/100")
        
        print("=" * 60)
    
    def _analyze_ramp_up_results(self, results: List[LoadTestMetrics]):
        """Analyze ramp-up test results to identify capacity limits"""
        
        print(f"\n📈 RAMP-UP TEST ANALYSIS")
        print("=" * 60)
        
        if not results:
            print("No results to analyze")
            return
        
        # Find optimal capacity point
        optimal_users = 0
        optimal_rps = 0
        degradation_start = None
        
        for metrics in results:
            users = metrics.configuration.users
            rps = metrics.requests_per_second
            failure_rate = metrics.failure_rate
            
            print(f"Users: {users:3d} | RPS: {rps:6.1f} | Failure Rate: {failure_rate:5.2%} | "
                  f"P95: {metrics.p95_response_time:6.1f}ms")
            
            # Track optimal point (before significant degradation)
            if failure_rate < 0.02 and metrics.p95_response_time < 2000:  # Good performance
                optimal_users = users
                optimal_rps = rps
            elif degradation_start is None and (failure_rate > 0.05 or metrics.p95_response_time > 3000):
                degradation_start = users
        
        print(f"\n🎯 Capacity Analysis:")
        print(f"  Optimal Capacity: ~{optimal_users} concurrent users ({optimal_rps:.1f} RPS)")
        if degradation_start:
            print(f"  Degradation Starts: ~{degradation_start} users")
            print(f"  Recommended Max Load: {int(optimal_users * 0.8)} users (80% of optimal)")
        else:
            print(f"  No significant degradation observed in test range")
    
    def _print_comparison_results(self, comparison: Dict, results: List[LoadTestMetrics]):
        """Print formatted comparison results"""
        
        print(f"\n🔄 SCENARIO COMPARISON RESULTS")
        print("=" * 60)
        
        scenarios = comparison['scenarios']
        
        print(f"📊 Throughput Comparison:")
        throughput_values = comparison['throughput_comparison']['values']
        for i, scenario in enumerate(scenarios):
            print(f"  {scenario:10s}: {throughput_values[i]:8.1f} RPS")
        print(f"  {'Best':10s}: {comparison['throughput_comparison']['max']:8.1f} RPS")
        
        print(f"\n⏱️  Latency Comparison (P95):")
        latency_values = comparison['latency_comparison']['p95_values']
        for i, scenario in enumerate(scenarios):
            print(f"  {scenario:10s}: {latency_values[i]:8.1f}ms")
        print(f"  {'Best':10s}: {comparison['latency_comparison']['p95_min']:8.1f}ms")
        
        print(f"\n❌ Error Rate Comparison:")
        error_values = comparison['error_rate_comparison']['values']
        for i, scenario in enumerate(scenarios):
            print(f"  {scenario:10s}: {error_values[i]:8.2%}")
        print(f"  {'Best':10s}: {comparison['error_rate_comparison']['min']:8.2%}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        best_throughput_idx = throughput_values.index(comparison['throughput_comparison']['max'])
        best_latency_idx = latency_values.index(comparison['latency_comparison']['p95_min'])
        best_error_idx = error_values.index(comparison['error_rate_comparison']['min'])
        
        print(f"  Best Throughput: {scenarios[best_throughput_idx]} scenario")
        print(f"  Best Latency: {scenarios[best_latency_idx]} scenario")
        print(f"  Best Reliability: {scenarios[best_error_idx]} scenario")
        
        # Overall winner (simple scoring)
        scores = []
        for i in range(len(scenarios)):
            score = 0
            if i == best_throughput_idx:
                score += 3
            if i == best_latency_idx:
                score += 3
            if i == best_error_idx:
                score += 4  # Reliability is most important
            scores.append(score)
        
        best_overall_idx = scores.index(max(scores))
        print(f"  Overall Recommended: {scenarios[best_overall_idx]} scenario")
    
    def _save_report(self, report_data: Dict, prefix: str) -> str:
        """Save report to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.json"
        filepath = Path("logs") / filename
        
        # Ensure logs directory exists
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        return str(filepath)


def main():
    """Main entry point for load testing CLI"""
    
    parser = argparse.ArgumentParser(
        description="Load Testing Runner for Corgi Recommendation Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --scenario standard                               # Run standard load test
  %(prog)s --scenario heavy --duration 20 --users 75        # Custom heavy test
  %(prog)s --ramp-up-test --max-users 200                    # Find capacity limits
  %(prog)s --compare-scenarios light,standard,heavy         # Compare scenarios
  %(prog)s --burst-test --baseline-users 20 --burst-users 80 # Burst traffic test
        """
    )
    
    # Primary test modes (mutually exclusive)
    test_mode = parser.add_mutually_exclusive_group(required=True)
    
    test_mode.add_argument(
        '--scenario',
        choices=['light', 'standard', 'heavy', 'burst', 'sustained', 'stress'],
        help='Run single load test scenario'
    )
    
    test_mode.add_argument(
        '--ramp-up-test',
        action='store_true',
        help='Run ramp-up test to find capacity limits'
    )
    
    test_mode.add_argument(
        '--compare-scenarios',
        help='Compare multiple scenarios (comma-separated list)'
    )
    
    test_mode.add_argument(
        '--burst-test',
        action='store_true',
        help='Run burst traffic test'
    )
    
    # Configuration options
    parser.add_argument(
        '--users',
        type=int,
        help='Override number of concurrent users'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        help='Override test duration in minutes'
    )
    
    parser.add_argument(
        '--spawn-rate',
        type=int,
        help='Override user spawn rate (users per second)'
    )
    
    parser.add_argument(
        '--host',
        default='http://localhost:5011',
        help='Target host for load testing (default: http://localhost:5011)'
    )
    
    # Ramp-up test specific options
    parser.add_argument(
        '--max-users',
        type=int,
        default=100,
        help='Maximum users for ramp-up test (default: 100)'
    )
    
    parser.add_argument(
        '--step-size',
        type=int,
        default=5,
        help='User increment for ramp-up test (default: 5)'
    )
    
    parser.add_argument(
        '--step-duration',
        type=int,
        default=2,
        help='Duration per step in ramp-up test in minutes (default: 2)'
    )
    
    # Burst test specific options
    parser.add_argument(
        '--baseline-users',
        type=int,
        default=10,
        help='Baseline users for burst test (default: 10)'
    )
    
    parser.add_argument(
        '--burst-users',
        type=int,
        default=50,
        help='Peak users during burst (default: 50)'
    )
    
    parser.add_argument(
        '--burst-duration',
        type=int,
        default=3,
        help='Burst duration in minutes (default: 3)'
    )
    
    # Output options
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate detailed JSON report'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimize output verbosity'
    )
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = LoadTestCLI()
    
    try:
        # Execute based on selected test mode
        if args.scenario:
            metrics = cli.run_single_scenario(
                scenario=args.scenario,
                users=args.users,
                duration_minutes=args.duration,
                spawn_rate=args.spawn_rate,
                host=args.host,
                generate_report=args.report
            )
            
            # Exit with error code if test failed
            if metrics.failure_rate > 0.1 or len(metrics.kpi_violations) > 0:
                print(f"\n⚠️  Load test completed with issues - check results above")
                sys.exit(1)
            
        elif args.ramp_up_test:
            results = cli.run_ramp_up_test(
                max_users=args.max_users,
                step_size=args.step_size,
                step_duration=args.step_duration,
                host=args.host
            )
            
            if not results:
                print(f"❌ Ramp-up test failed")
                sys.exit(1)
                
        elif args.compare_scenarios:
            scenarios = [s.strip() for s in args.compare_scenarios.split(',')]
            comparison = cli.compare_scenarios(scenarios, host=args.host)
            
            if not comparison:
                print(f"❌ Scenario comparison failed")
                sys.exit(1)
                
        elif args.burst_test:
            metrics = cli.run_burst_traffic_test(
                baseline_users=args.baseline_users,
                burst_users=args.burst_users,
                burst_duration=args.burst_duration,
                total_duration=args.duration or 15,
                host=args.host
            )
            
            if metrics.failure_rate > 0.2:  # Higher tolerance for burst tests
                print(f"\n⚠️  Burst test completed with high failure rate")
                sys.exit(1)
        
        print(f"\n✅ Load testing completed successfully")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Load testing interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
        
    except Exception as e:
        print(f"\n❌ Load testing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 