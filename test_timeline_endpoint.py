#!/usr/bin/env python3
"""
Test script for the new recommendations timeline endpoint.
"""

import requests
import json

def test_timeline_endpoint():
    """Test the /api/v1/recommendations/timeline endpoint"""
    
    # Test URL
    url = "http://localhost:9999/api/v1/recommendations/timeline"
    
    # For testing, we'll modify the request to include a mock Authorization header
    # that should work with the development setup
    headers = {
        "Authorization": "Bearer test_token_for_development",
        "Content-Type": "application/json"
    }
    
    # Test with different parameters
    test_cases = [
        {"limit": 3},
        {"limit": 5, "max_id": "100"},
        {"limit": 2, "since_id": "50"}
    ]
    
    for i, params in enumerate(test_cases):
        print(f"\n=== Test Case {i+1}: {params} ===")
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"Success! Received {len(data)} recommendations")
                        if data:
                            # Print first recommendation structure
                            first_rec = data[0]
                            print(f"First recommendation ID: {first_rec.get('id')}")
                            print(f"Is recommendation: {first_rec.get('is_recommendation')}")
                            print(f"Recommendation score: {first_rec.get('recommendation_score')}")
                            print(f"Content preview: {first_rec.get('content', '')[:100]}...")
                        else:
                            print("Empty recommendations array (no data for user)")
                    else:
                        print(f"Unexpected response format: {type(data)}")
                        print(f"Response: {data}")
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    print(f"Raw response: {response.text}")
            else:
                print(f"Error response: {response.text}")
                
        except requests.RequestException as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    test_timeline_endpoint() 