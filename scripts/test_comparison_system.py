#!/usr/bin/env python3
"""
Test script for the Model Performance Comparison Dashboard system.

This script tests the complete end-to-end functionality:
1. Model variant activation
2. Interaction logging with model tracking
3. Performance data aggregation
4. Comparison API endpoint
5. Statistical analysis
"""

import requests
import json
import time
import random
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:5002"  # Adjust if needed
API_KEY = "demo-token"
TEST_USER_IDS = ["test_user_1", "test_user_2", "test_user_3", "test_user_4", "test_user_5"]
TEST_POST_IDS = ["post_001", "post_002", "post_003", "post_004", "post_005"]
MODEL_VARIANTS = [1, 2, 3, 4, 5, 6]  # All 6 variants

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_model_activation():
    """Test model variant activation for users."""
    print("\n=== Testing Model Activation ===")
    
    for i, user_id in enumerate(TEST_USER_IDS):
        # Activate different models for different users
        variant_id = MODEL_VARIANTS[i % len(MODEL_VARIANTS)]
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/analytics/models/variants/{variant_id}/activate",
                headers=headers,
                json={"user_id": user_id}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Activated variant {variant_id} for user {user_id}: {result['variant']['name']}")
            else:
                print(f"✗ Failed to activate variant {variant_id} for user {user_id}: {response.text}")
                
        except Exception as e:
            print(f"✗ Error activating variant {variant_id} for user {user_id}: {e}")
    
    print("Model activation test completed")

def test_interaction_logging():
    """Test logging interactions with model variant tracking."""
    print("\n=== Testing Interaction Logging with Model Tracking ===")
    
    action_types = ["favorite", "click", "bookmark", "reblog", "view"]
    success_count = 0
    total_count = 0
    
    # Generate test interactions for each user/model combination
    for user_id in TEST_USER_IDS:
        user_variant = MODEL_VARIANTS[TEST_USER_IDS.index(user_id) % len(MODEL_VARIANTS)]
        
        for post_id in TEST_POST_IDS:
            for action_type in random.sample(action_types, k=random.randint(1, 3)):
                total_count += 1
                
                interaction_data = {
                    "user_id": user_id,
                    "post_id": post_id,
                    "action_type": action_type,
                    "model_variant_id": user_variant,
                    "recommendation_id": f"rec_{user_id}_{post_id}_{int(time.time())}",
                    "context": {
                        "source": "test_comparison_system",
                        "response_time": random.randint(50, 300),
                        "injected": True
                    }
                }
                
                try:
                    response = requests.post(
                        f"{BASE_URL}/api/v1/interactions",
                        headers=headers,
                        json=interaction_data
                    )
                    
                    if response.status_code in [200, 201]:
                        success_count += 1
                        if total_count <= 5:  # Show first few
                            print(f"✓ Logged {action_type} interaction for user {user_id}, post {post_id}, variant {user_variant}")
                    else:
                        if total_count <= 5:
                            print(f"✗ Failed to log interaction: {response.text}")
                        
                except Exception as e:
                    if total_count <= 5:
                        print(f"✗ Error logging interaction: {e}")
                
                # Small delay to avoid overwhelming the server
                time.sleep(0.01)
    
    print(f"Interaction logging test completed: {success_count}/{total_count} successful")

def test_performance_aggregation():
    """Test performance data aggregation task."""
    print("\n=== Testing Performance Aggregation ===")
    
    try:
        # Try to trigger aggregation manually if endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/v1/analytics/aggregate",
            headers=headers,
            json={"hours_back": 1}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Aggregation completed: {result}")
        else:
            print(f"ℹ Manual aggregation endpoint not available (expected): {response.status_code}")
            
    except Exception as e:
        print(f"ℹ Manual aggregation not available (expected): {e}")
    
    # Wait a moment for any background aggregation
    print("Waiting 3 seconds for potential background aggregation...")
    time.sleep(3)
    print("Performance aggregation test completed")

def test_comparison_api():
    """Test the model comparison API endpoint."""
    print("\n=== Testing Model Comparison API ===")
    
    # Test with different combinations of variants
    test_cases = [
        [1, 2],          # Two variants
        [1, 3, 5],       # Three variants
        [2, 4, 5, 6],    # Four variants
    ]
    
    for i, variant_ids in enumerate(test_cases):
        print(f"\nTest case {i+1}: Comparing variants {variant_ids}")
        
        try:
            params = {
                "days": 1  # Look at last day
            }
            for variant_id in variant_ids:
                params[f"ids"] = variant_id
            
            # Build URL with multiple ids parameters
            url = f"{BASE_URL}/api/v1/analytics/comparison?"
            url += "&".join([f"ids={vid}" for vid in variant_ids])
            url += "&days=1"
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Comparison API successful")
                
                # Validate response structure
                required_keys = ["status", "period", "variants", "time_series", "summary", "comparisons"]
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    print(f"⚠ Missing keys in response: {missing_keys}")
                else:
                    print(f"✓ Response structure valid")
                    
                    # Check if we have data
                    if data.get("summary"):
                        print(f"✓ Performance data found for {len(data['summary'])} variants")
                        
                        # Show summary statistics
                        for variant_id, summary in data["summary"].items():
                            variant_name = data["variants"].get(int(variant_id), {}).get("name", f"Variant {variant_id}")
                            engagement = summary.get("avg_engagement_rate", 0) * 100
                            interactions = summary.get("total_interactions", 0)
                            print(f"  - {variant_name}: {engagement:.2f}% engagement, {interactions} interactions")
                    else:
                        print("ℹ No performance data found (expected for recent test data)")
                        
                    # Check comparisons
                    if data.get("comparisons"):
                        print(f"✓ Statistical comparisons generated: {len(data['comparisons'])} comparisons")
                        
                        for comp_key, comparison in data["comparisons"].items():
                            variant_a = comparison["variant_a"]["name"]
                            variant_b = comparison["variant_b"]["name"]
                            print(f"  - {variant_a} vs {variant_b}")
                            
                            for metric, metric_data in comparison["metrics"].items():
                                lift = metric_data["lift_percent"]
                                winner = metric_data["winner"]
                                significant = metric_data["statistical_significance"]["is_significant"]
                                sig_marker = " (significant)" if significant else ""
                                print(f"    {metric}: {lift:+.1f}% lift, winner: {winner}{sig_marker}")
                    else:
                        print("ℹ No statistical comparisons available (expected for sparse test data)")
                        
                    # Check best variant
                    if data.get("best_variant"):
                        best = data["best_variant"]
                        print(f"✓ Best variant identified: {best['name']} (score: {best['score']:.3f})")
                    else:
                        print("ℹ No best variant identified (expected for limited test data)")
                        
            else:
                print(f"✗ Comparison API failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"✗ Error testing comparison API: {e}")

def test_error_cases():
    """Test error handling in the comparison API."""
    print("\n=== Testing Error Cases ===")
    
    # Test case 1: No authentication
    print("Test 1: No authentication")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/analytics/comparison?ids=1&ids=2")
        print(f"✓ No auth response: {response.status_code}")
    except Exception as e:
        print(f"✗ Error testing no auth: {e}")
    
    # Test case 2: Only one variant
    print("Test 2: Only one variant (should fail)")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/analytics/comparison?ids=1", headers=headers)
        print(f"✓ Single variant response: {response.status_code}")
    except Exception as e:
        print(f"✗ Error testing single variant: {e}")
    
    # Test case 3: Non-existent variant
    print("Test 3: Non-existent variant")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/analytics/comparison?ids=1&ids=999", headers=headers)
        print(f"✓ Non-existent variant response: {response.status_code}")
    except Exception as e:
        print(f"✗ Error testing non-existent variant: {e}")

def test_frontend_integration():
    """Test that the frontend can access the comparison endpoint."""
    print("\n=== Testing Frontend Integration ===")
    
    try:
        # Test the main dashboard page loads
        response = requests.get(f"{BASE_URL}/dashboard")
        if response.status_code == 200:
            print("✓ Dashboard page accessible")
        else:
            print(f"⚠ Dashboard page status: {response.status_code}")
            
    except Exception as e:
        print(f"ℹ Frontend test skipped (expected in API-only test): {e}")

def generate_sample_data():
    """Generate more sample data for better testing."""
    print("\n=== Generating Additional Sample Data ===")
    
    # Create more interactions with different patterns per variant
    variant_behaviors = {
        1: {"engagement_rate": 0.15, "response_time_range": (100, 200)},  # Collaborative Filtering
        2: {"engagement_rate": 0.22, "response_time_range": (150, 300)},  # Neural Collaborative
        3: {"engagement_rate": 0.18, "response_time_range": (80, 150)},   # Content-Based
        4: {"engagement_rate": 0.25, "response_time_range": (50, 120)},   # Multi-Armed Bandit
        5: {"engagement_rate": 0.28, "response_time_range": (200, 400)},  # Hybrid Ensemble
        6: {"engagement_rate": 0.20, "response_time_range": (120, 250)},  # Graph Neural Network
    }
    
    action_types = ["favorite", "click", "bookmark", "reblog"]
    
    for variant_id, behavior in variant_behaviors.items():
        print(f"Generating data for variant {variant_id} (engagement: {behavior['engagement_rate']:.1%})")
        
        for _ in range(50):  # 50 interactions per variant
            user_id = random.choice(TEST_USER_IDS)
            post_id = random.choice(TEST_POST_IDS)
            
            # Simulate variant-specific engagement patterns
            if random.random() < behavior["engagement_rate"]:
                action_type = random.choice(action_types)
                response_time = random.randint(*behavior["response_time_range"])
                
                interaction_data = {
                    "user_id": user_id,
                    "post_id": post_id,
                    "action_type": action_type,
                    "model_variant_id": variant_id,
                    "recommendation_id": f"rec_{variant_id}_{user_id}_{int(time.time())}_{random.randint(1000, 9999)}",
                    "context": {
                        "source": "sample_data_generator",
                        "response_time": response_time,
                        "injected": True,
                        "variant_engagement_rate": behavior["engagement_rate"]
                    }
                }
                
                try:
                    response = requests.post(
                        f"{BASE_URL}/api/v1/interactions",
                        headers=headers,
                        json=interaction_data
                    )
                    
                    if response.status_code not in [200, 201]:
                        print(f"Failed to create sample interaction: {response.text}")
                        
                except Exception as e:
                    print(f"Error creating sample interaction: {e}")
                    
                time.sleep(0.005)  # Small delay
    
    print("Sample data generation completed")

def main():
    """Run all tests in sequence."""
    print("🧪 Model Performance Comparison System Test Suite")
    print("=" * 60)
    
    try:
        # Test basic connectivity
        response = requests.get(f"{BASE_URL}/health")
        print(f"✓ API server connectivity: {response.status_code}")
    except Exception as e:
        print(f"✗ Cannot connect to API server at {BASE_URL}: {e}")
        print("Please ensure the API server is running")
        return
    
    # Run test sequence
    test_model_activation()
    generate_sample_data()
    test_interaction_logging()
    test_performance_aggregation()
    test_comparison_api()
    test_error_cases()
    test_frontend_integration()
    
    print("\n" + "=" * 60)
    print("🎉 Test suite completed!")
    print("\nNext steps:")
    print("1. Visit http://localhost:3000/dashboard and click 'Model Comparison'")
    print("2. Select 2-4 models to compare")
    print("3. Click 'Compare Models' to see the analysis")
    print("4. Review the statistical comparisons and performance charts")
    print("\nNote: It may take a few minutes for aggregated data to appear.")

if __name__ == "__main__":
    main() 