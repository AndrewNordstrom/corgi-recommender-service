#!/usr/bin/env python3

"""
Test script to verify all Phase 3 features of the Corgi Agent Framework.

This script performs a series of tests to ensure that all Phase 3 features
are working correctly, including:
- Token usage tracking
- Browser interaction limits
- Fast agent mode (no LLM)
- Selective tool activation
- API call optimization
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, List

# Add the parent directory to the path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.browser_agent import BrowserAgent
from agents.token_tracker import TokenTracker
from agents.user_profiles import get_profile_by_name, list_available_profiles
from agents.interaction_logger import InteractionLogger
from agents.feedback_module import FeedbackModule


def setup_logging() -> logging.Logger:
    """Set up logging for the test script."""
    logger = logging.getLogger("phase3_test")
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def test_token_tracking(logger):
    """Test token usage tracking features."""
    logger.info("=== Testing Token Tracking ===")
    
    # Create token tracker with a small limit for testing
    token_tracker = TokenTracker(max_tokens=5000)
    
    # Simulate a few token usage records
    token_tracker.record_usage(
        model="claude-sonnet-4-20250514",
        input_tokens=1000,
        output_tokens=500,
        request_duration=1.5
    )
    
    token_tracker.record_usage(
        model="claude-sonnet-4-20250514",
        input_tokens=800,
        output_tokens=300,
        request_duration=0.8
    )
    
    # Get and log the usage summary
    summary = token_tracker.get_usage_summary()
    logger.info(f"Total tokens tracked: {summary['total_tokens']}")
    logger.info(f"Total cost: ${summary['total_cost']:.6f}")
    
    # Test save to file
    output_file = token_tracker.save_usage_to_file()
    logger.info(f"Token usage saved to: {output_file}")
    
    # Log the summary
    token_tracker.log_summary()
    
    return summary


def test_browser_agent_no_llm(logger):
    """Test the browser agent in no-LLM (heuristic) mode."""
    logger.info("=== Testing No-LLM Mode ===")
    
    # Create interaction logger and feedback module
    interaction_logger = InteractionLogger()
    feedback_module = FeedbackModule()
    
    # Create browser agent in no-LLM mode
    agent = BrowserAgent(
        base_url="http://localhost:5001",
        logger=interaction_logger,
        feedback_module=feedback_module,
        no_llm=True
    )
    
    # Get a test profile
    try:
        profile = get_profile_by_name("tech_fan")
        logger.info(f"Using profile: {profile.name}")
    except ValueError as e:
        logger.error(f"Error getting profile: {str(e)}")
        return None
    
    # Run the agent in no-LLM mode
    results = agent.run_interaction(
        goal="Test the no-LLM mode", 
        max_turns=3,
        user_profile=profile
    )
    
    logger.info(f"No-LLM test completed with success={results['success']}")
    logger.info(f"Interactions used: {results['interactions_used']}")
    
    return results


def test_browser_agent_with_tools(logger):
    """Test the browser agent with tool access control."""
    logger.info("=== Testing Tool Access Control ===")
    
    # Create interaction logger and feedback module
    interaction_logger = InteractionLogger()
    feedback_module = FeedbackModule()
    token_tracker = TokenTracker(max_tokens=10000)
    
    # Create browser agent with tools enabled
    agent = BrowserAgent(
        base_url="http://localhost:5001",
        logger=interaction_logger,
        feedback_module=feedback_module,
        token_tracker=token_tracker,
        tools_enabled=True,
        max_interactions=5
    )
    
    # Get a test profile
    try:
        profile = get_profile_by_name("privacy_tester")
        logger.info(f"Using profile: {profile.name}")
    except ValueError as e:
        logger.error(f"Error getting profile: {str(e)}")
        return None
    
    # Run the agent with tools
    results = agent.run_interaction(
        goal="Test the privacy settings", 
        max_turns=5,
        user_profile=profile,
        test_goal="Test the Corgi Recommender with privacy_level=limited"
    )
    
    logger.info(f"Tool access test completed with success={results['success']}")
    if 'token_usage' in results:
        logger.info(f"Token usage: {results['token_usage']['total_tokens']} tokens")
    
    return results


def test_batch_processing(logger):
    """Test batch processing of posts."""
    logger.info("=== Testing Batch Processing ===")
    
    # Create interaction logger and feedback module
    interaction_logger = InteractionLogger()
    feedback_module = FeedbackModule()
    
    # Create browser agent in no-LLM mode (for speed)
    agent = BrowserAgent(
        base_url="http://localhost:5001",
        logger=interaction_logger,
        feedback_module=feedback_module,
        no_llm=True
    )
    
    # Get a test profile
    try:
        profile = get_profile_by_name("meme_lover")
        logger.info(f"Using profile: {profile.name}")
    except ValueError as e:
        logger.error(f"Error getting profile: {str(e)}")
        return None
    
    # Generate some test posts
    test_posts = [
        "Check out this cute corgi learning to code Python! #CodingPets",
        "OPINION: Are corgis the most politically neutral pets? Our analysis says YES! #ControversialTake",
        "Just posted a new privacy guide featuring my corgi as the mascot. #DigitalPrivacy"
    ]
    
    # Test batch processing using profile
    batch_results = profile.handle_post_batch(test_posts)
    logger.info(f"Batch processed {len(batch_results)} posts")
    for post, feedback in batch_results.items():
        logger.info(f"Post feedback: {feedback[:50]}...")
    
    return batch_results


def test_interaction_limits(logger):
    """Test browser interaction limits."""
    logger.info("=== Testing Interaction Limits ===")
    
    # Create interaction logger and feedback module
    interaction_logger = InteractionLogger()
    feedback_module = FeedbackModule()
    
    # Create browser agent with very low interaction limit
    agent = BrowserAgent(
        base_url="http://localhost:5001",
        logger=interaction_logger,
        feedback_module=feedback_module,
        max_interactions=2,  # Very low limit to trigger the cutoff
        tools_enabled=True
    )
    
    # Get a test profile
    try:
        profile = get_profile_by_name("news_skeptic")
        logger.info(f"Using profile: {profile.name}")
    except ValueError as e:
        logger.error(f"Error getting profile: {str(e)}")
        return None
    
    # Run the agent with a low interaction limit
    results = agent.run_interaction(
        goal="Test the interaction limits", 
        max_turns=10,  # Higher turn limit than interaction limit
        user_profile=profile
    )
    
    logger.info(f"Interaction limit test completed with success={results['success']}")
    logger.info(f"Interactions used: {results['interactions_used']}/{agent.max_interactions}")
    logger.info(f"Message: {results['message']}")
    
    # Check if the limit was reached
    if results['interactions_used'] >= agent.max_interactions:
        logger.info("✅ Interaction limit correctly enforced")
    else:
        logger.warning("❌ Interaction limit not reached or enforced")
    
    return results


def main():
    """Main entry point for the test script."""
    logger = setup_logging()
    logger.info("Starting Phase 3 feature tests...")
    
    parser = argparse.ArgumentParser(description="Test Phase 3 features of the Corgi Agent Framework.")
    parser.add_argument(
        "--feature", 
        choices=["token_tracking", "no_llm", "tools", "batch", "limits", "all"],
        default="all",
        help="Specific feature to test"
    )
    args = parser.parse_args()
    
    results = {}
    
    try:
        # Run the requested tests
        if args.feature in ["token_tracking", "all"]:
            results["token_tracking"] = test_token_tracking(logger)
        
        if args.feature in ["no_llm", "all"]:
            results["no_llm"] = test_browser_agent_no_llm(logger)
        
        if args.feature in ["tools", "all"]:
            results["tools"] = test_browser_agent_with_tools(logger)
        
        if args.feature in ["batch", "all"]:
            results["batch"] = test_batch_processing(logger)
        
        if args.feature in ["limits", "all"]:
            results["limits"] = test_interaction_limits(logger)
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}", exc_info=True)
    
    # Print summary
    logger.info("\n=== Test Summary ===")
    for feature, result in results.items():
        if result:
            logger.info(f"✅ {feature}: Success")
        else:
            logger.info(f"❌ {feature}: Failed or incomplete")
    
    logger.info("Phase 3 feature tests completed.")


if __name__ == "__main__":
    main()