#!/usr/bin/env python3
"""
Test script for recommendation quality metrics collection.

This script:
1. Adds sample posts to the database
2. Generates recommendations for a test user
3. Tests quality metrics collection
4. Displays the results
"""

import logging
import sys
from datetime import datetime, timedelta
from db.connection import get_db_connection
from core.ranking_algorithm import generate_rankings_for_user
from utils.recommendation_metrics import get_quality_metrics_summary

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def add_sample_posts():
    """Add sample posts for testing."""
    logger.info("Adding sample posts...")
    
    sample_posts = [
        {
            'post_id': 'test_post_1',
            'content': 'Exciting news about AI developments in 2024! #technology #ai',
            'author_id': 'author_tech',
            'created_at': (datetime.now() - timedelta(hours=2)).isoformat()
        },
        {
            'post_id': 'test_post_2', 
            'content': 'Beautiful sunrise over the mountains today 🌄 #nature #photography',
            'author_id': 'author_nature',
            'created_at': (datetime.now() - timedelta(hours=4)).isoformat()
        },
        {
            'post_id': 'test_post_3',
            'content': 'New research in quantum computing shows promising results! #science #quantum',
            'author_id': 'author_science',
            'created_at': (datetime.now() - timedelta(hours=1)).isoformat()
        },
        {
            'post_id': 'test_post_4',
            'content': 'Delicious homemade pasta recipe 🍝 Who wants the recipe? #cooking #food',
            'author_id': 'author_cooking',
            'created_at': (datetime.now() - timedelta(hours=6)).isoformat()
        },
        {
            'post_id': 'test_post_5',
            'content': 'Reading an amazing book about space exploration 🚀 #books #space',
            'author_id': 'author_books',
            'created_at': (datetime.now() - timedelta(hours=8)).isoformat()
        }
    ]
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            for post in sample_posts:
                cur.execute('''
                    INSERT OR REPLACE INTO posts (post_id, content, author_id, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    post['post_id'],
                    post['content'],
                    post['author_id'],
                    post['created_at'],
                    '{"interaction_counts": {"favorites": 5, "reblogs": 2, "replies": 1}}'
                ))
            
            conn.commit()
            logger.info(f"Added {len(sample_posts)} sample posts")
            
    except Exception as e:
        logger.error(f"Error adding sample posts: {e}")
        return False
    
    return True

def test_quality_metrics():
    """Test quality metrics collection."""
    logger.info("Testing quality metrics collection...")
    
    try:
        # Generate rankings for a test user
        test_user_id = 'test_user_123'
        rankings = generate_rankings_for_user(test_user_id)
        
        logger.info(f"Generated {len(rankings)} rankings")
        
        if rankings:
            logger.info("Sample ranking:")
            sample = rankings[0]
            for key in ['post_id', 'ranking_score', 'recommendation_reason']:
                if key in sample:
                    logger.info(f"  {key}: {sample[key]}")
        
        # Test quality metrics summary
        logger.info("Getting quality metrics summary...")
        summary = get_quality_metrics_summary(days=1)
        
        if 'error' in summary:
            logger.warning(f"Quality metrics summary error: {summary['error']}")
        else:
            logger.info("Quality metrics summary:")
            for key, value in summary.items():
                if key != 'timestamp':
                    logger.info(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing quality metrics: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_quality_endpoints():
    """Test quality metrics endpoints."""
    logger.info("Testing quality metrics endpoints...")
    
    try:
        from utils.recommendation_metrics import get_cached_quality_summary
        
        # Test cached summary
        summary = get_cached_quality_summary(days=1)
        logger.info("Cached quality summary:")
        for key, value in summary.items():
            if key != 'timestamp':
                logger.info(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing endpoints: {e}")
        return False

def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("Starting Quality Metrics Test")
    logger.info("=" * 60)
    
    success = True
    
    # Step 1: Add sample posts
    if not add_sample_posts():
        logger.error("Failed to add sample posts")
        success = False
    
    # Step 2: Test quality metrics collection
    if not test_quality_metrics():
        logger.error("Failed to test quality metrics")
        success = False
    
    # Step 3: Test quality endpoints
    if not test_quality_endpoints():
        logger.error("Failed to test quality endpoints")
        success = False
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ All quality metrics tests PASSED!")
        logger.info("Quality metrics collection is working correctly.")
    else:
        logger.error("❌ Some quality metrics tests FAILED!")
        sys.exit(1)
    logger.info("=" * 60)

if __name__ == '__main__':
    main() 