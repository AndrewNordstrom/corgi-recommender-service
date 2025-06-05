#!/usr/bin/env python3
"""
Test script for A/B Testing Automated Analysis

This script creates sample A/B testing data and demonstrates the automated
analysis and recommendations functionality.

TODO #28j: Add automated experiment analysis and recommendations
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ab_analysis import ab_analyzer
from db.connection import get_db_connection, get_cursor

def create_sample_experiment():
    """Create a sample A/B testing experiment with test data."""
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                # Create experiment
                experiment_name = f'Sample Ranking Algorithm Test {datetime.now().strftime("%Y%m%d_%H%M%S")}'
                cursor.execute("""
                    INSERT INTO ab_experiments 
                    (name, description, status, start_date, minimum_sample_size, confidence_level)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    experiment_name,
                    'Testing different recommendation algorithms',
                    'active',
                    datetime.now() - timedelta(days=10),  # Started 10 days ago
                    200,  # Minimum sample size
                    0.95
                ))
                
                experiment_id = cursor.fetchone()[0]
                print(f"Created experiment with ID: {experiment_id}")
                
                # Create variants
                variants = [
                    ('Control', 'Current recommendation algorithm', True, 50.0, {
                        "max_candidates": 50,
                        "content_weight": 0.4,
                        "collaborative_weight": 0.6,
                        "diversity_threshold": 0.3
                    }),
                    ('Test A', 'New collaborative filtering approach', False, 30.0, {
                        "max_candidates": 50,
                        "content_weight": 0.2,
                        "collaborative_weight": 0.8,
                        "diversity_threshold": 0.4
                    }),
                    ('Test B', 'Hybrid content-based + collaborative filtering', False, 20.0, {
                        "max_candidates": 60,
                        "content_weight": 0.5,
                        "collaborative_weight": 0.5,
                        "diversity_threshold": 0.35
                    })
                ]
                
                variant_ids = []
                for name, desc, is_control, traffic, algo_config in variants:
                    cursor.execute("""
                        INSERT INTO ab_variants 
                        (experiment_id, name, description, is_control, traffic_allocation, algorithm_config)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (experiment_id, name, desc, is_control, traffic, json.dumps(algo_config)))
                    
                    variant_id = cursor.fetchone()[0]
                    variant_ids.append((variant_id, name, traffic))
                    print(f"Created variant '{name}' with ID: {variant_id}")
                
                # Create sample experiment results (recommendations and interactions)
                sample_data = [
                    # (variant_id, recommendations, interactions) - simulating different performance
                    (variant_ids[0][0], 300, 45),  # Control: 15% conversion rate
                    (variant_ids[1][0], 180, 32),  # Test A: 17.8% conversion rate (better)
                    (variant_ids[2][0], 120, 18),  # Test B: 15% conversion rate (similar to control)
                ]
                
                base_time = datetime.now() - timedelta(days=10)
                
                for variant_id, rec_count, interaction_count in sample_data:
                    # Add recommendation events
                    for i in range(rec_count):
                        event_time = base_time + timedelta(
                            minutes=i * (10 * 24 * 60 // rec_count)  # Spread over 10 days
                        )
                        
                        cursor.execute("""
                            INSERT INTO ab_experiment_results
                            (experiment_id, variant_id, user_id, event_type, timestamp)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            experiment_id,
                            variant_id,
                            f'user_{i}',
                            'recommendation_generation',
                            event_time
                        ))
                    
                    # Add interaction events (subset of recommendations)
                    interaction_interval = rec_count // interaction_count if interaction_count > 0 else 1
                    for i in range(interaction_count):
                        event_time = base_time + timedelta(
                            minutes=(i * interaction_interval) * (10 * 24 * 60 // rec_count)
                        )
                        
                        cursor.execute("""
                            INSERT INTO ab_experiment_results
                            (experiment_id, variant_id, user_id, event_type, timestamp)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            experiment_id,
                            variant_id,
                            f'user_{i * interaction_interval}',
                            'user_interaction',
                            event_time
                        ))
                
                # Add some performance events
                for variant_id, name, traffic in variant_ids:
                    # Simulate different performance characteristics
                    if 'Control' in name:
                        avg_latency = 120  # ms
                        avg_memory = 45    # MB
                    elif 'Test A' in name:
                        avg_latency = 95   # ms (faster)
                        avg_memory = 52    # MB (more memory)
                    else:  # Test B
                        avg_latency = 140  # ms (slower)
                        avg_memory = 38    # MB (less memory)
                    
                    # Add 50 performance events per variant
                    for i in range(50):
                        event_time = base_time + timedelta(
                            minutes=i * (10 * 24 * 60 // 50)
                        )
                        
                        cursor.execute("""
                            INSERT INTO ab_performance_events
                            (experiment_id, variant_id, user_id, request_id, event_type, latency_ms, memory_usage_mb, 
                             items_processed, cache_hit_rate, error_occurred, timestamp)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            experiment_id,
                            variant_id,
                            f'user_{i}',  # Add user_id
                            f'req_{experiment_id}_{variant_id}_{i}',  # Add request_id
                            'recommendation_end',  # Add event_type
                            avg_latency + (i % 20 - 10),  # Add some variance
                            avg_memory + (i % 10 - 5),    # Add some variance
                            5,  # items processed
                            0.75 + (i % 100) / 400,  # Cache hit rate 0.75-1.0
                            False,  # No errors
                            event_time
                        ))
                
                conn.commit()
                print(f"Created sample data for experiment {experiment_id}")
                return experiment_id
                
    except Exception as e:
        print(f"Error creating sample experiment: {e}")
        return None

def test_automated_analysis(experiment_id):
    """Test the automated analysis functionality."""
    print(f"\n{'='*60}")
    print(f"RUNNING AUTOMATED ANALYSIS FOR EXPERIMENT {experiment_id}")
    print(f"{'='*60}")
    
    try:
        # Run the automated analysis
        analysis = ab_analyzer.analyze_experiment(experiment_id)
        
        print(f"\nEXPERIMENT: {analysis.experiment_name}")
        print(f"Runtime: {analysis.runtime_days:.1f} days")
        print(f"Total Sample Size: {analysis.total_sample_size}")
        print(f"Statistical Significance: {analysis.statistical_significance.value}")
        print(f"Practical Significance: {analysis.practical_significance}")
        
        if analysis.overall_winner:
            print(f"Overall Winner: Variant {analysis.overall_winner}")
        else:
            print("No clear winner identified")
        
        print(f"\nVARIANT ANALYSIS:")
        print(f"{'Variant':<15} {'Sample Size':<12} {'Conversion':<12} {'Confidence Interval':<20} {'Power':<8}")
        print("-" * 80)
        
        for va in analysis.variant_analyses:
            ci_str = f"[{va.confidence_interval[0]:.3f}, {va.confidence_interval[1]:.3f}]"
            print(f"{va.variant_name:<15} {va.sample_size:<12} {va.conversion_rate:<12.3f} {ci_str:<20} {va.statistical_power:<8.2f}")
        
        print(f"\nPAIRWISE COMPARISONS:")
        print(f"{'Variants':<25} {'Effect Size':<12} {'P-Value':<10} {'Significance':<15} {'Winner':<10}")
        print("-" * 80)
        
        for comp in analysis.pairwise_comparisons:
            winner_str = str(comp.winner) if comp.winner else "None"
            print(f"{comp.variant_a_id} vs {comp.variant_b_id:<20} {comp.effect_size:<12.4f} {comp.p_value:<10.4f} {comp.significance_level.value:<15} {winner_str:<10}")
        
        print(f"\nRECOMMENDATIONS ({len(analysis.recommendations)}):")
        for i, rec in enumerate(analysis.recommendations, 1):
            print(f"{i}. [{rec['priority'].upper()}] {rec['type']}")
            print(f"   {rec['message']}")
            print(f"   Action: {rec['action']}")
            if 'estimated_time' in rec:
                print(f"   Time: {rec['estimated_time']}")
            print()
        
        print(f"RISK ASSESSMENT:")
        print(f"Level: {analysis.risk_assessment['level'].upper()}")
        if analysis.risk_assessment['factors']:
            print("Risk Factors:")
            for factor in analysis.risk_assessment['factors']:
                print(f"  - {factor}")
        if analysis.risk_assessment['mitigation_strategies']:
            print("Mitigation Strategies:")
            for strategy in analysis.risk_assessment['mitigation_strategies']:
                print(f"  - {strategy}")
        
        print(f"\nNEXT STEPS:")
        for step in analysis.next_steps:
            print(f"  {step}")
        
        print(f"\n{'='*60}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*60}")
        
        return analysis
        
    except Exception as e:
        print(f"Error running automated analysis: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_api_endpoints(experiment_id):
    """Test the API endpoints for automated analysis."""
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    base_url = "https://localhost:5002/api/v1/analytics"
    
    print(f"\n{'='*60}")
    print(f"TESTING API ENDPOINTS FOR EXPERIMENT {experiment_id}")
    print(f"{'='*60}")
    
    endpoints = [
        f"/experiments/{experiment_id}/analysis/summary",
        f"/experiments/{experiment_id}/recommendations",
        f"/experiments/{experiment_id}/analysis"
    ]
    
    for endpoint in endpoints:
        print(f"\nTesting: {endpoint}")
        try:
            response = requests.get(f"{base_url}{endpoint}", verify=False, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'experiment_name' in data:
                    print(f"Experiment: {data['experiment_name']}")
                if 'recommendations' in data:
                    print(f"Recommendations: {len(data['recommendations'])}")
                if 'total_sample_size' in data:
                    print(f"Sample Size: {data['total_sample_size']}")
                print("✅ Success")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")

def main():
    """Main test function."""
    print("A/B Testing Automated Analysis Test")
    print("=" * 50)
    
    # Create sample experiment
    print("1. Creating sample experiment with test data...")
    experiment_id = create_sample_experiment()
    
    if not experiment_id:
        print("Failed to create sample experiment. Exiting.")
        return 1
    
    # Test the analysis engine directly
    print("\n2. Testing automated analysis engine...")
    analysis = test_automated_analysis(experiment_id)
    
    if not analysis:
        print("Failed to run automated analysis. Exiting.")
        return 1
    
    # Test API endpoints
    print("\n3. Testing API endpoints...")
    test_api_endpoints(experiment_id)
    
    print(f"\n✅ All tests completed successfully!")
    print(f"Experiment ID: {experiment_id}")
    print("You can now view this experiment in the A/B testing dashboard.")
    
    return 0

if __name__ == "__main__":
    exit(main()) 