#!/usr/bin/env python3
"""
Test script for the Corgi Recommender Service database layer.
"""

import os
import logging
import datetime
from pprint import pprint

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Force use of the file-based SQLite database (not in-memory)
os.environ["USE_IN_MEMORY_DB"] = "false"
os.environ["USE_SQLITE"] = "true"
os.environ["SQLITE_DB_PATH"] = "sqlite:///data/corgi_recommender.db"

# Import modules from the database package
from db.models import InteractionType, PrivacyLevel
from db.session import db_session
from db.crud import (
    record_interaction_with_context,
    get_user_interactions,
    get_recent_posts
)
from db.privacy import generate_user_alias
from db.recommendations import get_recommendations, get_cold_start_recommendations

def test_record_and_get_interaction():
    """Test recording and retrieving interactions."""
    # Generate a test user alias
    test_user = generate_user_alias("test_user_123", "example.com")
    
    # Record a sample interaction
    interaction = record_interaction_with_context(
        alias_id=test_user,
        post_id="post1",  # Use a post ID that exists from our seed data
        interaction_type=InteractionType.FAVORITE,
        context={"source": "timeline", "position": 3}
    )
    
    logger.info(f"Recorded interaction: {interaction}")
    
    # Retrieve interactions for the user
    with db_session() as session:
        user_interactions = get_user_interactions(session, test_user)
        logger.info(f"Found {len(user_interactions)} interactions for user {test_user}")
        
        for i, interaction in enumerate(user_interactions):
            logger.info(f"Interaction {i+1}: {interaction.interaction_type.value} on post {interaction.post_id}")

def test_get_recommendations():
    """Test getting personalized recommendations."""
    # Generate a test user alias
    test_user = generate_user_alias("test_user_123", "example.com")
    
    # Get recommendations for the user
    recommendations = get_recommendations(test_user, max_recommendations=5)
    
    logger.info(f"Found {len(recommendations)} recommendations for user {test_user}")
    if recommendations:
        logger.info("Top recommendation:")
        pprint(recommendations[0])

def test_cold_start_recommendations():
    """Test getting cold start recommendations."""
    # Get cold start recommendations
    recommendations = get_cold_start_recommendations(max_recommendations=3)
    
    logger.info(f"Found {len(recommendations)} cold start recommendations")
    if recommendations:
        logger.info("Sample cold start recommendation:")
        pprint(recommendations[0])

def test_recent_posts():
    """Test retrieving recent posts."""
    with db_session() as session:
        posts = get_recent_posts(session, limit=5)
        
        logger.info(f"Found {len(posts)} recent posts")
        for i, post in enumerate(posts):
            logger.info(f"Post {i+1}: {post.post_id} by {post.author_name} ({post.created_at.isoformat()})")

def main():
    """Run all tests."""
    logger.info("Testing Corgi Recommender Service database layer...")
    
    # Run tests
    test_record_and_get_interaction()
    test_get_recommendations()
    test_cold_start_recommendations()
    test_recent_posts()
    
    logger.info("All tests completed!")

if __name__ == "__main__":
    main()