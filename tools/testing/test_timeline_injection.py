#!/usr/bin/env python3
"""
Simple test script to verify the timeline injection functionality works correctly.
"""

import json
import logging
from datetime import datetime, timedelta
from utils.timeline_injector import inject_into_timeline

# Setup logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_test_posts():
    """Create sample posts for testing."""
    # Create real posts
    now = datetime.now()
    real_posts = []
    for i in range(3):
        real_posts.append(
            {
                "id": f"real_post_{i}",
                "content": f"Real post {i} content",
                "created_at": (now - timedelta(minutes=i * 15)).isoformat(),
                "account": {
                    "id": f"user_{i}",
                    "username": f"user{i}",
                    "display_name": f"User {i}",
                    "url": f"https://example.com/@user{i}",
                },
                "tags": [{"name": "test"}, {"name": f"tag{i}"}],
            }
        )

    # Create injectable posts
    injectable_posts = []
    for i in range(2):
        injectable_posts.append(
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

    return real_posts, injectable_posts


def test_uniform_injection():
    """Test uniform injection strategy."""
    real_posts, injectable_posts = create_test_posts()

    print(
        f"Starting with {len(real_posts)} real posts and {len(injectable_posts)} injectable posts"
    )

    # Define uniform strategy
    strategy = {"type": "uniform", "max_injections": 2, "shuffle_injected": False}

    # Perform injection
    merged_timeline = inject_into_timeline(real_posts, injectable_posts, strategy)

    # Count injected posts
    injected_count = sum(1 for post in merged_timeline if post.get("injected") is True)

    print(
        f"After injection: {len(merged_timeline)} total posts, {injected_count} injected posts"
    )

    # Print the merged timeline for inspection
    print("\nMerged Timeline:")
    for i, post in enumerate(merged_timeline):
        post_type = "INJECTED" if post.get("injected") else "REAL"
        print(
            f"{i+1}. [{post_type}] ID: {post['id']}, Created At: {post['created_at']}"
        )


def test_empty_real_posts():
    """Test injection when real_posts is empty."""
    _, injectable_posts = create_test_posts()

    print(f"Starting with 0 real posts and {len(injectable_posts)} injectable posts")

    # Define strategy
    strategy = {"type": "uniform", "max_injections": 2, "shuffle_injected": False}

    # Perform injection
    merged_timeline = inject_into_timeline([], injectable_posts, strategy)

    # Count injected posts
    injected_count = sum(1 for post in merged_timeline if post.get("injected") is True)

    print(
        f"After injection: {len(merged_timeline)} total posts, {injected_count} injected posts"
    )

    # Print the merged timeline for inspection
    print("\nMerged Timeline:")
    for i, post in enumerate(merged_timeline):
        post_type = "INJECTED" if post.get("injected") else "REAL"
        print(
            f"{i+1}. [{post_type}] ID: {post['id']}, Created At: {post['created_at']}"
        )


def test_tag_match_injection():
    """Test tag matching injection strategy."""
    real_posts, injectable_posts = create_test_posts()

    # Add matching tags
    real_posts[0]["tags"].append({"name": "match"})
    injectable_posts[0]["tags"].append({"name": "match"})

    print(
        f"Starting with {len(real_posts)} real posts and {len(injectable_posts)} injectable posts"
    )

    # Define tag match strategy
    strategy = {"type": "tag_match", "max_injections": 2, "shuffle_injected": False}

    # Perform injection
    merged_timeline = inject_into_timeline(real_posts, injectable_posts, strategy)

    # Count injected posts
    injected_count = sum(1 for post in merged_timeline if post.get("injected") is True)

    print(
        f"After injection: {len(merged_timeline)} total posts, {injected_count} injected posts"
    )

    # Print the merged timeline for inspection
    print("\nMerged Timeline:")
    for i, post in enumerate(merged_timeline):
        post_type = "INJECTED" if post.get("injected") else "REAL"
        print(
            f"{i+1}. [{post_type}] ID: {post['id']}, Created At: {post['created_at']}"
        )


if __name__ == "__main__":
    print("\n=== Testing Uniform Injection ===")
    test_uniform_injection()

    print("\n\n=== Testing Empty Real Posts ===")
    test_empty_real_posts()

    print("\n\n=== Testing Tag Match Injection ===")
    test_tag_match_injection()
