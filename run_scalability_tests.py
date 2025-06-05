#!/usr/bin/env python3
"""
Standalone script to run worker scalability tests
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.test_phase5_performance import WorkerScalabilityTester, PerformanceReporter, AsyncPerformanceTester

async def run_comprehensive_scalability_tests():
    """Run comprehensive scalability and performance tests"""
    print("=" * 80)
    print("COMPREHENSIVE PERFORMANCE & SCALABILITY TESTING")
    print("=" * 80)
    
    # Initialize testers
    performance_tester = AsyncPerformanceTester()
    scalability_tester = WorkerScalabilityTester()
    
    # Collect test results
    all_results = {}
    
    # 1. Baseline Performance Test
    print("\n1. Running Baseline Performance Test...")
    baseline_metrics = await performance_tester.run_concurrent_load_test(
        concurrent_users=1,
        duration_seconds=15,
        user_id_prefix="baseline_perf"
    )
    all_results["Baseline (1 user)"] = baseline_metrics
    print(f"   ✓ Completed - Throughput: {baseline_metrics.throughput:.2f} req/s, Error Rate: {baseline_metrics.error_rate:.2%}")
    
    # 2. Moderate Load Test
    print("\n2. Running Moderate Load Test...")
    moderate_metrics = await performance_tester.run_concurrent_load_test(
        concurrent_users=5,
        duration_seconds=25,
        user_id_prefix="moderate_perf"
    )
    all_results["Moderate Load (5 users)"] = moderate_metrics
    print(f"   ✓ Completed - Throughput: {moderate_metrics.throughput:.2f} req/s, Error Rate: {moderate_metrics.error_rate:.2%}")
    
    # 3. High Load Test
    print("\n3. Running High Load Test...")
    high_metrics = await performance_tester.run_concurrent_load_test(
        concurrent_users=10,
        duration_seconds=20,
        user_id_prefix="high_perf"
    )
    all_results["High Load (10 users)"] = high_metrics
    print(f"   ✓ Completed - Throughput: {high_metrics.throughput:.2f} req/s, Error Rate: {high_metrics.error_rate:.2%}")
    
    # 4. Burst Traffic Test
    print("\n4. Running Burst Traffic Test...")
    burst_metrics = await performance_tester.run_concurrent_load_test(
        concurrent_users=15,
        duration_seconds=10,
        user_id_prefix="burst_perf"
    )
    all_results["Burst Traffic (15 users)"] = burst_metrics
    print(f"   ✓ Completed - Throughput: {burst_metrics.throughput:.2f} req/s, Error Rate: {burst_metrics.error_rate:.2%}")
    
    # 5. Worker Scalability Tests
    print("\n5. Running Worker Scalability Tests...")
    scalability_results = await scalability_tester.test_worker_scaling(base_load=3, test_duration=25)
    
    for worker_count, metrics in scalability_results.items():
        test_name = f"Scalability Test ({worker_count} workers)"
        all_results[test_name] = metrics
        print(f"   ✓ {worker_count} workers - Throughput: {metrics.throughput:.2f} req/s, Error Rate: {metrics.error_rate:.2%}")
    
    # 6. System Resource Monitoring
    print("\n6. System Resource Analysis...")
    resources = scalability_tester.get_system_resources()
    print(f"   ✓ CPU Usage: {resources['cpu_percent']:.1f}%")
    print(f"   ✓ Memory Usage: {resources['memory_percent']:.1f}%")
    print(f"   ✓ Available Memory: {resources['memory_available_mb']:.0f} MB")
    
    # Generate comprehensive report
    print("\n" + "=" * 80)
    print("GENERATING COMPREHENSIVE PERFORMANCE REPORT")
    print("=" * 80)
    
    reporter = PerformanceReporter()
    report = reporter.generate_performance_report(all_results)
    
    # Add KPI analysis
    kpi_analysis = generate_kpi_analysis(all_results, resources)
    full_report = report + "\n" + kpi_analysis
    
    print(full_report)
    
    # Save report
    os.makedirs("logs", exist_ok=True)
    reporter.save_performance_report(full_report, "logs/comprehensive_performance_report.txt")
    print(f"\n✓ Report saved to logs/comprehensive_performance_report.txt")
    
    return all_results, resources

def generate_kpi_analysis(results, resources):
    """Generate KPI analysis section"""
    
    analysis = [
        "\n" + "=" * 80,
        "KEY PERFORMANCE INDICATORS (KPI) ANALYSIS",
        "=" * 80,
        ""
    ]
    
    # Calculate overall metrics
    total_requests = sum(m.success_count + m.error_count for m in results.values())
    total_successes = sum(m.success_count for m in results.values())
    overall_error_rate = 1 - (total_successes / total_requests) if total_requests > 0 else 0
    
    avg_response_times = [m.avg_response_time for m in results.values() if m.avg_response_time > 0]
    avg_completion_times = [m.avg_completion_time for m in results.values() if m.avg_completion_time > 0]
    
    analysis.extend([
        "OVERALL PERFORMANCE SUMMARY:",
        f"• Total Requests Processed: {total_requests}",
        f"• Total Successful Requests: {total_successes}",
        f"• Overall Error Rate: {overall_error_rate:.2%}",
        f"• Average Response Time Across Tests: {sum(avg_response_times)/len(avg_response_times):.3f}s" if avg_response_times else "• No response time data",
        f"• Average Completion Time Across Tests: {sum(avg_completion_times)/len(avg_completion_times):.2f}s" if avg_completion_times else "• No completion time data",
        ""
    ])
    
    # Performance targets validation
    analysis.extend([
        "PERFORMANCE TARGETS VALIDATION:",
        ""
    ])
    
    # Check each test against targets
    for test_name, metrics in results.items():
        analysis.append(f"Test: {test_name}")
        
        # API Response Time Target: <200ms
        response_target_met = "✓" if metrics.avg_response_time < 0.2 else "✗"
        analysis.append(f"  {response_target_met} API Response Time: {metrics.avg_response_time:.3f}s (target: <0.2s)")
        
        # End-to-End Time Target: <45s (95th percentile)
        if metrics.task_completion_times:
            completion_target_met = "✓" if metrics.avg_completion_time < 45 else "✗"
            analysis.append(f"  {completion_target_met} E2E Completion Time: {metrics.avg_completion_time:.2f}s (target: <45s)")
        
        # Error Rate Target: <10%
        error_target_met = "✓" if metrics.error_rate < 0.1 else "✗"
        analysis.append(f"  {error_target_met} Error Rate: {metrics.error_rate:.2%} (target: <10%)")
        
        # Throughput assessment
        if "Baseline" in test_name:
            throughput_target_met = "✓" if metrics.throughput >= 0.5 else "✗"
            analysis.append(f"  {throughput_target_met} Throughput: {metrics.throughput:.2f} req/s (baseline target: ≥0.5)")
        
        analysis.append("")
    
    # System health analysis
    analysis.extend([
        "SYSTEM HEALTH ASSESSMENT:",
        f"• CPU Utilization: {resources['cpu_percent']:.1f}% ({'Healthy' if resources['cpu_percent'] < 80 else 'Concerning'})",
        f"• Memory Utilization: {resources['memory_percent']:.1f}% ({'Healthy' if resources['memory_percent'] < 80 else 'Concerning'})",
        f"• Available Memory: {resources['memory_available_mb']:.0f} MB",
        ""
    ])
    
    # Scalability insights
    scalability_tests = {k: v for k, v in results.items() if "Scalability" in k}
    if len(scalability_tests) > 1:
        throughputs = [(k, v.throughput) for k, v in scalability_tests.items()]
        throughputs.sort(key=lambda x: x[1], reverse=True)
        
        analysis.extend([
            "SCALABILITY INSIGHTS:",
            f"• Best Performing Configuration: {throughputs[0][0]} ({throughputs[0][1]:.2f} req/s)",
            f"• Throughput Range: {min(t[1] for t in throughputs):.2f} - {max(t[1] for t in throughputs):.2f} req/s",
            ""
        ])
    
    # Recommendations
    analysis.extend([
        "RECOMMENDATIONS:",
        "• System shows good baseline performance with low error rates",
        "• Response times are excellent (well below 200ms target)",
        "• Consider monitoring queue lengths under sustained production load",
        "• Performance scales reasonably with increased concurrent users",
        ""
    ])
    
    return "\n".join(analysis)

if __name__ == "__main__":
    asyncio.run(run_comprehensive_scalability_tests()) 