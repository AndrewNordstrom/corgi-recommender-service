#!/usr/bin/env python3
"""
Test Metrics Exporter for Prometheus

This script collects test suite metrics and exports them to Prometheus
for monitoring and alerting via Grafana dashboards.
"""

import json
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import re

try:
    from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram, start_http_server, write_to_textfile
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("⚠️  prometheus_client not available. Install with: pip install prometheus_client")


class TestMetricsCollector:
    """Collect and export test suite metrics."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.metrics_file = Path("test-metrics.json")
        
        # Define Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            self._setup_prometheus_metrics()
    
    def _setup_prometheus_metrics(self):
        """Set up Prometheus metrics."""
        # Test Suite Health Metrics
        self.test_suite_success_rate = Gauge(
            'test_suite_success_rate',
            'Percentage of tests passing',
            registry=self.registry
        )
        
        self.test_suite_passed_total = Gauge(
            'test_suite_passed_total',
            'Total number of passed tests',
            registry=self.registry
        )
        
        self.test_suite_failed_total = Gauge(
            'test_suite_failed_total',
            'Total number of failed tests',
            registry=self.registry
        )
        
        self.test_suite_skipped_total = Gauge(
            'test_suite_skipped_total',
            'Total number of skipped tests',
            registry=self.registry
        )
        
        self.test_suite_duration_seconds = Gauge(
            'test_suite_duration_seconds',
            'Total test suite execution time in seconds',
            registry=self.registry
        )
        
        # Performance Metrics
        self.test_performance_duration_seconds = Histogram(
            'test_performance_duration_seconds',
            'Individual test execution times',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.test_regressions_detected_total = Counter(
            'test_regressions_detected_total',
            'Number of performance regressions detected',
            registry=self.registry
        )
        
        self.test_improvements_detected_total = Counter(
            'test_improvements_detected_total',
            'Number of performance improvements detected',
            registry=self.registry
        )
        
        # Quality Metrics
        self.test_warnings_total = Gauge(
            'test_warnings_total',
            'Total number of test warnings',
            registry=self.registry
        )
        
        self.test_coverage_percentage = Gauge(
            'test_coverage_percentage',
            'Test coverage percentage',
            registry=self.registry
        )
        
        # Security Metrics
        self.security_vulnerabilities_total = Gauge(
            'security_vulnerabilities_total',
            'Total security vulnerabilities detected',
            registry=self.registry
        )
    
    def run_test_suite_analysis(self) -> Dict:
        """Run comprehensive test suite analysis."""
        print("🔍 Running test suite analysis...")
        
        metrics = {
            'timestamp': time.time(),
            'test_results': self._collect_test_results(),
            'performance_metrics': self._collect_performance_metrics(),
            'quality_metrics': self._collect_quality_metrics(),
            'security_metrics': self._collect_security_metrics()
        }
        
        return metrics
    
    def _collect_test_results(self) -> Dict:
        """Collect basic test results."""
        print("📊 Collecting test results...")
        
        # Run pytest with json output
        result = subprocess.run([
            "python", "-m", "pytest", 
            "--tb=no", 
            "-q",
            "--json-report",
            "--json-report-file=test-results.json"
        ], capture_output=True, text=True)
        
        # Parse pytest output
        output_lines = result.stdout.strip().split('\n')
        summary_line = output_lines[-1] if output_lines else ""
        
        # Extract test counts using regex
        passed = failed = skipped = 0
        
        # Look for pattern like "397 passed, 6 failed, 17 skipped"
        if "passed" in summary_line:
            passed_match = re.search(r'(\d+) passed', summary_line)
            if passed_match:
                passed = int(passed_match.group(1))
        
        if "failed" in summary_line:
            failed_match = re.search(r'(\d+) failed', summary_line)
            if failed_match:
                failed = int(failed_match.group(1))
        
        if "skipped" in summary_line:
            skipped_match = re.search(r'(\d+) skipped', summary_line)
            if skipped_match:
                skipped = int(skipped_match.group(1))
        
        total = passed + failed + skipped
        success_rate = (passed / total * 100) if total > 0 else 0
        
        return {
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'total': total,
            'success_rate': success_rate,
            'summary': summary_line
        }
    
    def _collect_performance_metrics(self) -> Dict:
        """Collect performance metrics."""
        print("⚡ Collecting performance metrics...")
        
        # Run tests with timing
        result = subprocess.run([
            "python", "-m", "pytest", 
            "--durations=0",
            "--tb=no", 
            "-q"
        ], capture_output=True, text=True)
        
        durations = []
        total_duration = 0
        
        # Parse timing output
        for line in result.stdout.split('\n'):
            if 's call' in line and '::' in line:
                parts = line.strip().split()
                if len(parts) >= 3:
                    duration_str = parts[0].replace('s', '')
                    try:
                        duration = float(duration_str)
                        durations.append(duration)
                        total_duration += duration
                    except ValueError:
                        continue
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Calculate percentiles
        sorted_durations = sorted(durations)
        p50 = sorted_durations[len(sorted_durations)//2] if sorted_durations else 0
        p95 = sorted_durations[int(len(sorted_durations)*0.95)] if sorted_durations else 0
        
        return {
            'total_duration': total_duration,
            'average_duration': avg_duration,
            'median_duration': p50,
            'p95_duration': p95,
            'test_count': len(durations),
            'slowest_tests': sorted_durations[-5:] if sorted_durations else []
        }
    
    def _collect_quality_metrics(self) -> Dict:
        """Collect code quality metrics."""
        print("📈 Collecting quality metrics...")
        
        # Count warnings
        result = subprocess.run([
            "python", "-m", "pytest", 
            "--tb=no", 
            "-q"
        ], capture_output=True, text=True)
        
        warning_count = result.stderr.count("warning")
        
        # Get coverage if available
        coverage_percentage = 0
        try:
            cov_result = subprocess.run([
                "python", "-m", "pytest", 
                "--cov=.", 
                "--cov-report=term-missing",
                "--tb=no"
            ], capture_output=True, text=True)
            
            # Parse coverage from output
            for line in cov_result.stdout.split('\n'):
                if "TOTAL" in line and "%" in line:
                    # Extract percentage from line like "TOTAL     20407  19442     5%"
                    parts = line.split()
                    for part in parts:
                        if '%' in part:
                            coverage_percentage = float(part.replace('%', ''))
                            break
        except Exception:
            pass
        
        return {
            'warning_count': warning_count,
            'coverage_percentage': coverage_percentage,
            'deprecation_warnings': result.stderr.count("DeprecationWarning")
        }
    
    def _collect_security_metrics(self) -> Dict:
        """Collect security metrics."""
        print("🔒 Collecting security metrics...")
        
        vulnerability_count = 0
        
        # Check for pip-audit results
        try:
            result = subprocess.run([
                "pip-audit", "--format=json", "--progress-spinner=off"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                try:
                    audit_data = json.loads(result.stdout)
                    vulnerability_count = len(audit_data.get('vulnerabilities', []))
                except json.JSONDecodeError:
                    pass
        except FileNotFoundError:
            print("⚠️  pip-audit not available")
        
        return {
            'vulnerability_count': vulnerability_count
        }
    
    def update_prometheus_metrics(self, metrics: Dict):
        """Update Prometheus metrics with collected data."""
        if not PROMETHEUS_AVAILABLE:
            return
        
        print("📊 Updating Prometheus metrics...")
        
        # Test Results
        test_results = metrics['test_results']
        self.test_suite_success_rate.set(test_results['success_rate'])
        self.test_suite_passed_total.set(test_results['passed'])
        self.test_suite_failed_total.set(test_results['failed'])
        self.test_suite_skipped_total.set(test_results['skipped'])
        
        # Performance Metrics
        perf_metrics = metrics['performance_metrics']
        self.test_suite_duration_seconds.set(perf_metrics['total_duration'])
        
        # Record individual test durations as histogram
        for duration in perf_metrics.get('slowest_tests', []):
            self.test_performance_duration_seconds.observe(duration)
        
        # Quality Metrics
        quality_metrics = metrics['quality_metrics']
        self.test_warnings_total.set(quality_metrics['warning_count'])
        self.test_coverage_percentage.set(quality_metrics['coverage_percentage'])
        
        # Security Metrics
        security_metrics = metrics['security_metrics']
        self.security_vulnerabilities_total.set(security_metrics['vulnerability_count'])
    
    def save_metrics(self, metrics: Dict):
        """Save metrics to JSON file."""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            print(f"💾 Metrics saved to {self.metrics_file}")
        except IOError as e:
            print(f"❌ Failed to save metrics: {e}")
    
    def export_to_prometheus_file(self, metrics: Dict, filename: str = "test_metrics.prom"):
        """Export metrics to Prometheus text file format."""
        if not PROMETHEUS_AVAILABLE:
            return
        
        try:
            write_to_textfile(filename, self.registry)
            print(f"📤 Metrics exported to {filename}")
        except Exception as e:
            print(f"❌ Failed to export metrics: {e}")
    
    def run_metrics_collection(self):
        """Run complete metrics collection process."""
        print("🚀 Starting test metrics collection...")
        
        # Collect all metrics
        metrics = self.run_test_suite_analysis()
        
        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            self.update_prometheus_metrics(metrics)
        
        # Save to file
        self.save_metrics(metrics)
        
        # Export to Prometheus format
        if PROMETHEUS_AVAILABLE:
            self.export_to_prometheus_file(metrics)
        
        # Print summary
        self._print_summary(metrics)
    
    def _print_summary(self, metrics: Dict):
        """Print metrics summary."""
        print("\n" + "="*60)
        print("📊 TEST METRICS SUMMARY")
        print("="*60)
        
        test_results = metrics['test_results']
        perf_metrics = metrics['performance_metrics']
        quality_metrics = metrics['quality_metrics']
        security_metrics = metrics['security_metrics']
        
        print(f"✅ Test Results:")
        print(f"   • Success Rate: {test_results['success_rate']:.1f}%")
        print(f"   • Passed: {test_results['passed']}")
        print(f"   • Failed: {test_results['failed']}")
        print(f"   • Skipped: {test_results['skipped']}")
        
        print(f"\n⚡ Performance:")
        print(f"   • Total Duration: {perf_metrics['total_duration']:.2f}s")
        print(f"   • Average Test: {perf_metrics['average_duration']:.3f}s")
        print(f"   • 95th Percentile: {perf_metrics['p95_duration']:.3f}s")
        
        print(f"\n📈 Quality:")
        print(f"   • Coverage: {quality_metrics['coverage_percentage']:.1f}%")
        print(f"   • Warnings: {quality_metrics['warning_count']}")
        
        print(f"\n🔒 Security:")
        print(f"   • Vulnerabilities: {security_metrics['vulnerability_count']}")
        
        print("\n✅ Metrics collection completed!")


def main():
    """Main entry point."""
    collector = TestMetricsCollector()
    collector.run_metrics_collection()


if __name__ == "__main__":
    main() 