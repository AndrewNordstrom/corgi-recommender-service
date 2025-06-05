#!/usr/bin/env python3
"""
Test script that verifies timeline injection with an empty real timeline.
"""

import json
import logging
from datetime import datetime, timedelta
from copy import deepcopy
from utils.timeline_injector import inject_into_timeline

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_injectable_posts(count=5):
    """Create sample injectable posts for testing."""
    now = datetime.now()
    posts = []

    for i in range(count):
        posts.append(
            {
                "id": f"inject_post_{i}",
                "content": f"Injectable post {i} content",
                "created_at": (now - timedelta(hours=24)).isoformat(),  # Old timestamp
                "account": {
                    "id": f"inject_user_{i}",
                    "username": f"inject_user{i}",
                    "display_name": f"Inject User {i}",
                    "url": f"https://example.com/@inject_user{i}",
                },
                "tags": [{"name": "test"}, {"name": f"injecttag{i}"}],
            }
        )

    return posts


def test_empty_timeline_injection():
    """Test injection with an empty real posts list."""
    logger.info("Testing empty timeline injection")

    # Create injectable posts
    injectable_posts = create_injectable_posts(5)
    logger.info(f"Created {len(injectable_posts)} injectable posts")

    # Define strategy for injection
    strategy = {"type": "uniform", "max_injections": 3, "shuffle_injected": True}

    # Call injection function with empty real posts
    logger.info("Calling inject_into_timeline with empty real posts")
    result = inject_into_timeline([], injectable_posts, strategy)

    # Count injected posts
    injected_count = sum(1 for post in result if post.get("injected") is True)

    # Print results
    logger.info(f"Result: {len(result)} total posts, {injected_count} injected posts")

    for i, post in enumerate(result):
        logger.info(f"Post {i+1}: id={post.get('id')}, injected={post.get('injected')}")

    # Verify results
    assert len(result) > 0, "Result should not be empty"
    assert injected_count > 0, "Should have injected posts"
    assert injected_count == len(result), "All posts should be injected"

    logger.info("✅ Test passed: Empty timeline injection works correctly")
    return result


def test_stub_post_injection():
    """Test injection with a stub post that should be ignored."""
    logger.info("Testing stub post injection")

    # Create injectable posts
    injectable_posts = create_injectable_posts(5)

    # Create a stub post
    stub_post = {
        "id": "stub_post",
        "content": "Stub post for injection",
        "created_at": datetime.now().isoformat(),
        "account": {
            "id": "stub_account",
            "username": "stub",
            "display_name": "Stub Account",
            "url": "https://example.com/@stub",
        },
        "stub_for_injection": True,
    }

    # Define strategy for injection
    strategy = {"type": "uniform", "max_injections": 3, "shuffle_injected": True}

    # Call injection function with stub post
    logger.info("Calling inject_into_timeline with stub post")
    result = inject_into_timeline([stub_post], injectable_posts, strategy)

    # Count injected posts
    injected_count = sum(1 for post in result if post.get("injected") is True)
    stub_count = sum(1 for post in result if post.get("stub_for_injection") is True)

    # Print results
    logger.info(
        f"Result: {len(result)} total posts, {injected_count} injected posts, {stub_count} stub posts"
    )

    # Verify results
    assert len(result) > 0, "Result should not be empty"
    assert injected_count > 0, "Should have injected posts"
    assert stub_count == 0, "Stub post should be ignored"

    logger.info("✅ Test passed: Stub post injection works correctly")
    return result


if __name__ == "__main__":
    print("\n=== Testing Empty Timeline Injection ===")
    empty_result = test_empty_timeline_injection()

    print("\n=== Testing Stub Post Injection ===")
    stub_result = test_stub_post_injection()

    print("\n=== Summary ===")
    print(f"Empty timeline: {len(empty_result)} posts injected")
    print(f"Stub post: {len(stub_result)} posts injected")
