#!/usr/bin/env python3
"""Test the recommendation engine directly"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.recommendation_engine import get_ranked_recommendations

def test_recommendation_engine():
    print("Testing recommendation engine...")
    
    # Test with a fake user ID that doesn't start with 'test_' or 'corgi_validator_'
    user_id = "real_user_123"
    
    try:
        recommendations = get_ranked_recommendations(user_id, limit=3, languages=['en'])
        print(f"Got {len(recommendations)} recommendations")
        
        for i, rec in enumerate(recommendations):
            print(f"Recommendation {i+1}:")
            print(f"  ID: {rec.get('id', 'unknown')}")
            print(f"  Content: {rec.get('content', '')[:100]}...")
            print(f"  Author: {rec.get('account', {}).get('username', 'unknown')}")
            print(f"  Source instance: {rec.get('_corgi_source_instance', 'unknown')}")
            print(f"  Is real Mastodon post: {rec.get('is_real_mastodon_post', False)}")
            print()
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_recommendation_engine() 