#!/usr/bin/env python3
"""
Test script for A/B Testing Performance Monitoring

Tests the performance monitoring capabilities of the A/B testing framework,
verifying metrics collection, storage, and analysis functionality.

Related to TODO #28i: Implement performance monitoring during A/B tests
"""

import sys
import os
import time
import random
import json
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ab_performance import PerformanceTracker, performance_tracker
from utils.ab_testing import ABTestingEngine
from db.connection import get_db_connection, get_cursor

def create_test_experiment() -> int:
    """Create a test experiment for performance monitoring."""
    print("Creating test experiment...")
    
    with get_db_connection() as conn:
        with get_cursor(conn) as cursor:
            # Create experiment
            cursor.execute("""
                INSERT INTO ab_experiments 
                (name, description, status, traffic_percentage, minimum_sample_size, confidence_level)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                f"Performance Test Experiment {int(time.time())}",
                "Testing performance monitoring capabilities",
                "active",
                100.0,
                100,
                0.95
            ))
            
            experiment_id = cursor.fetchone()[0]
            
            # Create variants
            variants_data = [
                ("Control Variant", "Baseline recommendation algorithm", 33.33, {"ranking_weights": {"engagement": 0.3, "relevance": 0.7}}, True),
                ("Variant A", "Enhanced engagement weighting", 33.33, {"ranking_weights": {"engagement": 0.5, "relevance": 0.5}}, False),
                ("Variant B", "Optimized relevance algorithm", 33.34, {"ranking_weights": {"engagement": 0.2, "relevance": 0.8}}, False)
            ]
            
            variant_ids = []
            for name, description, allocation, config, is_control in variants_data:
                cursor.execute("""
                    INSERT INTO ab_variants 
                    (experiment_id, name, description, traffic_allocation, algorithm_config, is_control)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (experiment_id, name, description, allocation, json.dumps(config), is_control))
                
                variant_ids.append(cursor.fetchone()[0])
            
            conn.commit()
            print(f"Created experiment {experiment_id} with variants: {variant_ids}")
            return experiment_id, variant_ids

def simulate_recommendation_performance(experiment_id: int, variant_ids: list, num_requests: int = 50):
    """Simulate recommendation requests with performance tracking."""
    print(f"Simulating {num_requests} recommendation requests with performance monitoring...")
    
    tracker = PerformanceTracker()
    
    for i in range(num_requests):
        # Randomly select a variant
        variant_id = random.choice(variant_ids)
        user_id = f"test_user_{random.randint(1, 20)}"
        request_id = f"req_{experiment_id}_{i}"
        
        # Simulate different performance characteristics per variant
        base_latency = random.uniform(50, 200)  # Base latency in ms
        if variant_id == variant_ids[1]:  # Variant A - slightly slower
            latency_multiplier = 1.2
        elif variant_id == variant_ids[2]:  # Variant B - slightly faster
            latency_multiplier = 0.9
        else:  # Control
            latency_multiplier = 1.0
            
        simulated_latency = base_latency * latency_multiplier
        
        # Use the performance tracking context manager
        with tracker.track_experiment_performance(
            experiment_id=experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            request_id=request_id,
            operation_type="recommendation_generation"
        ) as context:
            
            # Simulate recommendation generation work
            time.sleep(simulated_latency / 1000)  # Convert ms to seconds
            
            # Record additional metrics
            context.record_items_processed(random.randint(10, 100))
            context.record_cache_metrics(random.uniform(0.6, 0.95))
            
            # Occasionally simulate errors
            if random.random() < 0.05:  # 5% error rate
                context.record_error("Simulated timeout error", "timeout")
            
            # Add custom metrics
            context.record_custom_metric("db_queries", random.randint(2, 8))
            context.record_custom_metric("cache_hits", random.randint(5, 15))
        
        if (i + 1) % 10 == 0:
            print(f"Completed {i + 1}/{num_requests} requests")

def test_real_time_performance(experiment_id: int):
    """Test real-time performance metrics retrieval."""
    print("Testing real-time performance metrics...")
    
    tracker = PerformanceTracker()
    metrics = tracker.get_real_time_performance(experiment_id, time_window_minutes=5)
    
    print(f"Real-time metrics for experiment {experiment_id}:")
    print(f"  Time window: {metrics.get('time_window_minutes', 'N/A')} minutes")
    print(f"  Analysis timestamp: {metrics.get('timestamp', 'N/A')}")
    
    variants_data = metrics.get('variants', {})
    if variants_data:
        for variant_id, variant_metrics in variants_data.items():
            print(f"  Variant {variant_id}:")
            for metric_name, value in variant_metrics.items():
                if isinstance(value, float):
                    print(f"    {metric_name}: {value:.2f}")
                else:
                    print(f"    {metric_name}: {value}")
    else:
        print("  No performance data available for the specified time window")

def test_performance_comparison(experiment_id: int):
    """Test performance comparison capabilities."""
    print("Testing performance comparison analysis...")
    
    tracker = PerformanceTracker()
    comparison = tracker.compute_performance_comparison(experiment_id, time_period_hours=1)
    
    print(f"Performance comparison for experiment {experiment_id}:")
    print(f"Analysis period: {comparison.get('analysis_period')}")
    print(f"Statistical significance: {comparison.get('statistical_significance', {})}")
    
    variants_data = comparison.get('variants', {})
    for variant_id, metrics in variants_data.items():
        print(f"  Variant {variant_id}:")
        for metric_name, stats in metrics.items():
            if isinstance(stats, dict):
                print(f"    {metric_name}: mean={stats.get('mean', 'N/A'):.2f}, "
                      f"p95={stats.get('p95', 'N/A'):.2f}, "
                      f"samples={stats.get('sample_count', 0)}")

def test_prometheus_metrics():
    """Test Prometheus metrics integration."""
    print("Testing Prometheus metrics integration...")
    
    try:
        import utils.metrics as prometheus_metrics
        
        # Check if A/B testing metrics are available
        metrics_to_check = [
            'ab_test_latency_histogram',
            'ab_test_memory_usage',
            'ab_test_items_processed',
            'ab_test_cache_hit_rate',
            'ab_test_errors_total'
        ]
        
        for metric_name in metrics_to_check:
            if hasattr(prometheus_metrics, metric_name):
                print(f"  ✓ {metric_name} metric available")
            else:
                print(f"  ✗ {metric_name} metric missing")
                
    except Exception as e:
        print(f"Error checking Prometheus metrics: {e}")

def verify_database_schema():
    """Verify that performance monitoring tables exist."""
    print("Verifying database schema for performance monitoring...")
    
    with get_db_connection() as conn:
        with get_cursor(conn) as cursor:
            # Check for required tables
            tables_to_check = [
                'ab_performance_events',
                'ab_performance_metrics', 
                'ab_performance_comparisons'
            ]
            
            for table_name in tables_to_check:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = %s
                """, (table_name,))
                
                if cursor.fetchone():
                    print(f"  ✓ Table {table_name} exists")
                else:
                    print(f"  ✗ Table {table_name} missing")

def cleanup_test_data(experiment_id: int):
    """Clean up test data."""
    print(f"Cleaning up test experiment {experiment_id}...")
    
    with get_db_connection() as conn:
        with get_cursor(conn) as cursor:
            # Delete performance events
            cursor.execute("DELETE FROM ab_performance_events WHERE experiment_id = %s", (experiment_id,))
            
            # Delete experiment results
            cursor.execute("DELETE FROM ab_experiment_results WHERE experiment_id = %s", (experiment_id,))
            
            # Delete user assignments
            cursor.execute("DELETE FROM ab_user_assignments WHERE experiment_id = %s", (experiment_id,))
            
            # Delete variants
            cursor.execute("DELETE FROM ab_variants WHERE experiment_id = %s", (experiment_id,))
            
            # Delete experiment
            cursor.execute("DELETE FROM ab_experiments WHERE id = %s", (experiment_id,))
            
            conn.commit()
            print(f"Cleaned up experiment {experiment_id}")

def main():
    """Main test function."""
    print("=" * 60)
    print("A/B Testing Performance Monitoring Test")
    print("=" * 60)
    
    try:
        # 1. Verify database schema
        verify_database_schema()
        print()
        
        # 2. Test Prometheus metrics integration
        test_prometheus_metrics()
        print()
        
        # 3. Create test experiment
        experiment_id, variant_ids = create_test_experiment()
        print()
        
        # 4. Simulate recommendation requests with performance tracking
        simulate_recommendation_performance(experiment_id, variant_ids, num_requests=30)
        print()
        
        # 5. Test real-time performance metrics
        test_real_time_performance(experiment_id)
        print()
        
        # 6. Test performance comparison
        test_performance_comparison(experiment_id)
        print()
        
        print("=" * 60)
        print("Performance monitoring test completed successfully!")
        print("=" * 60)
        
        # Ask if user wants to clean up test data
        cleanup = input("Clean up test data? (y/n): ").lower().strip()
        if cleanup == 'y':
            cleanup_test_data(experiment_id)
        else:
            print(f"Test experiment {experiment_id} preserved for manual inspection")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 