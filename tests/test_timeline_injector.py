"""
Core Timeline Injector Tests

Essential tests for timeline injection functionality covering:
- Basic post manipulation functions
- Timestamp handling and harmonization
- Core injection strategies (uniform, after_n)
- Basic validation
"""

import pytest
from datetime import datetime, timedelta
import random
import json
import os
from unittest.mock import patch, MagicMock

from utils.timeline_injector import (
    inject_into_timeline,
    harmonize_timestamp,
    check_time_gap,
    has_matching_tags,
    uniform_injection_points,
    get_post_timestamp,
    sort_posts_by_timestamp,
    extract_tags,
    tag_as_injected
)

# Import the function we'll be testing more directly now
from utils.recommendation_engine import get_ranked_recommendations 

# Helper function to create test posts
def create_post(post_id, created_at, tags=None, content="Test content"):
    """Create a test post with the given parameters."""
    if tags is None:
        tags = []
    
    # Convert tags to Mastodon format
    formatted_tags = [{"name": tag} for tag in tags]
    
    return {
        "id": post_id,
        "created_at": created_at.isoformat() + "Z",
        "content": content,
        "tags": formatted_tags,
        "account": {
            "id": "user123",
            "username": "testuser",
            "display_name": "Test User"
        }
    }

# Test data setup
@pytest.fixture
def test_posts():
    """Create a fixture with test posts."""
    now = datetime.now()
    
    # Create 10 real posts with descending timestamps
    real_posts = [
        create_post(f"real_{i}", now - timedelta(minutes=i*15), 
                   tags=["tech", "programming"] if i % 3 == 0 else ["general"])
        for i in range(10)
    ]
    
    # Create 5 injectable posts
    injectable_posts = [
        create_post(f"inject_{i}", now - timedelta(hours=24), 
                   tags=["tech", "ai"] if i % 2 == 0 else ["news"])
        for i in range(5)
    ]
    
    return {"real": real_posts, "injectable": injectable_posts}

# Basic functionality tests
def test_get_post_timestamp():
    """Test timestamp extraction from post."""
    from datetime import timezone
    now = datetime.now(timezone.utc)  # Make it timezone-aware
    post = {"created_at": now.isoformat()}
    extracted = get_post_timestamp(post)
    assert abs((extracted - now).total_seconds()) < 1  # Allow for slight formatting differences

def test_sort_posts_by_timestamp(test_posts):
    """Test sorting posts by timestamp."""
    # Shuffle posts
    shuffled = test_posts["real"].copy()
    random.shuffle(shuffled)
    
    # Sort them
    sorted_posts = sort_posts_by_timestamp(shuffled)
    
    # Verify order (most recent first)
    for i in range(len(sorted_posts) - 1):
        assert get_post_timestamp(sorted_posts[i]) >= get_post_timestamp(sorted_posts[i+1])

def test_extract_tags():
    """Test extracting hashtags from a post."""
    post = {
        "tags": [
            {"name": "tech"},
            {"name": "programming"}
        ]
    }
    tags = extract_tags(post)
    assert set(tags) == {"tech", "programming"}

def test_tag_as_injected():
    """Test marking a post as injected."""
    post = {"id": "123"}
    marked = tag_as_injected(post)
    assert marked["injected"] is True
    assert marked["id"] == "123"  # Original data preserved

def test_harmonize_timestamp(test_posts):
    """Test timestamp harmonization between posts."""
    before_post = test_posts["real"][0]  # Most recent
    after_post = test_posts["real"][1]  # Second most recent
    inject_post = test_posts["injectable"][0]
    
    # Harmonize timestamp
    harmonized = harmonize_timestamp(inject_post, before_post, after_post)
    
    # Check that timestamp is between the two posts
    harmonized_time = get_post_timestamp(harmonized)
    before_time = get_post_timestamp(before_post)
    after_time = get_post_timestamp(after_post)
    
    assert after_time < harmonized_time < before_time

def test_uniform_strategy(test_posts):
    """Test uniform distribution strategy."""
    strategy = {
        "type": "uniform",
        "max_injections": 3
    }
    
    result = inject_into_timeline(test_posts["real"], test_posts["injectable"], strategy)
    
    # Count injected posts
    injected_count = sum(1 for post in result if post.get("injected", False))
    assert injected_count == 3
    
    # Check that timeline is properly sorted
    assert result == sort_posts_by_timestamp(result)
    
    # Check that injection_metadata is present in injected posts
    for post in result:
        if post.get("injected", False):
            assert "injection_metadata" in post or post.get("is_real_mastodon_post") is False

def test_after_n_strategy(test_posts):
    """Test injecting after every N posts."""
    strategy = {
        "type": "after_n",
        "n": 2,
        "max_injections": 4
    }
    
    result = inject_into_timeline(test_posts["real"], test_posts["injectable"], strategy)
    
    # Count injected posts
    injected_count = sum(1 for post in result if post.get("injected", False))
    assert injected_count == 4
    
    # Check that timeline is properly sorted
    assert result == sort_posts_by_timestamp(result)

def test_empty_inputs():
    """Test handling of empty inputs."""
    strategy = {"type": "uniform", "max_injections": 3}
    
    # Empty real posts
    result = inject_into_timeline([], [{"id": "1"}], strategy)
    assert len(result) == 1
    assert result[0]["injected"] is True
    
    # Empty injectable posts
    real_posts = [{"id": "real1", "created_at": datetime.now().isoformat()}]
    result = inject_into_timeline(real_posts, [], strategy)
    assert len(result) == 1
    assert result[0]["id"] == "real1"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])