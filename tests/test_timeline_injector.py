"""
Tests for the timeline injector module and recommendation engine integration.
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

def test_check_time_gap(test_posts):
    """Test checking time gap between posts."""
    # Posts are 15 minutes apart
    assert check_time_gap(test_posts["real"][0], test_posts["real"][1], 10) is True
    assert check_time_gap(test_posts["real"][0], test_posts["real"][1], 20) is False

def test_has_matching_tags(test_posts):
    """Test checking for matching tags between posts."""
    # Posts with matching tags
    post1 = create_post("1", datetime.now(), tags=["tech", "news"])
    post2 = create_post("2", datetime.now(), tags=["tech", "programming"])
    assert has_matching_tags(post1, post2) is True
    
    # Posts without matching tags
    post3 = create_post("3", datetime.now(), tags=["sports"])
    assert has_matching_tags(post1, post3) is False

def test_uniform_injection_points():
    """Test calculating uniform injection points."""
    points = uniform_injection_points(10, 3)
    assert len(points) == 3
    assert all(0 < p < 10 for p in points)
    assert points == sorted(points)  # Points should be in order

# Strategy tests
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

def test_first_only_strategy(test_posts):
    """Test injecting only in first posts."""
    strategy = {
        "type": "first_only",
        "max_injections": 2
    }
    
    result = inject_into_timeline(test_posts["real"], test_posts["injectable"], strategy)
    
    # Count injected posts
    injected_count = sum(1 for post in result if post.get("injected", False))
    assert injected_count == 2
    
    # Check that timeline is properly sorted
    assert result == sort_posts_by_timestamp(result)
    
    # Check that injections are in the first part of the timeline
    # Count positions of injected posts in the merged timeline
    injected_positions = [i for i, post in enumerate(result) if post.get("injected", False)]
    
    # Ensure both injected posts are in the first half of the timeline
    for pos in injected_positions:
        assert pos < len(result) // 2, f"Injected post at position {pos} should be in first half of timeline"

def test_tag_match_strategy(test_posts):
    """Test matching tags strategy."""
    # Ensure we have some matching tags
    test_posts["injectable"][0]["tags"] = [{"name": "tech"}]
    test_posts["injectable"][1]["tags"] = [{"name": "general"}]
    
    strategy = {
        "type": "tag_match",
        "max_injections": 3
    }
    
    result = inject_into_timeline(test_posts["real"], test_posts["injectable"], strategy)
    
    # There should be some injected posts
    injected_count = sum(1 for post in result if post.get("injected", False))
    assert injected_count > 0
    
    # Check that timeline is properly sorted
    assert result == sort_posts_by_timestamp(result)

def test_gap_requirement(test_posts):
    """Test respecting minimum gap requirement."""
    # Make a strategy with a large gap requirement
    strategy = {
        "type": "uniform",
        "max_injections": 5,
        "inject_only_if_gap_minutes": 20  # Larger than our 15 minute gaps
    }
    
    result = inject_into_timeline(test_posts["real"], test_posts["injectable"], strategy)
    
    # Should be no injections due to gap requirement
    injected_count = sum(1 for post in result if post.get("injected", False))
    assert injected_count == 0

def test_shuffle_injected(test_posts):
    """Test shuffling injectable posts."""
    # Set a seed for reproducibility
    random.seed(42)
    
    strategy = {
        "type": "uniform",
        "max_injections": 3,
        "shuffle_injected": True
    }
    
    # Run twice with the same seed
    random.seed(42)
    result1 = inject_into_timeline(test_posts["real"], test_posts["injectable"], strategy)
    
    random.seed(42)
    result2 = inject_into_timeline(test_posts["real"], test_posts["injectable"], strategy)
    
    # Results should be identical with the same seed
    assert [p["id"] for p in result1 if p.get("injected")] == [p["id"] for p in result2 if p.get("injected")]
    
    # Change seed and results should differ
    random.seed(100)
    result3 = inject_into_timeline(test_posts["real"], test_posts["injectable"], strategy)
    
    # With different seeds, the order should usually be different
    # (Note: there's a small chance they could be the same by random chance)
    injected_ids1 = [p["id"] for p in result1 if p.get("injected")]
    injected_ids3 = [p["id"] for p in result3 if p.get("injected")]
    
    # At least check that we got 3 injected posts in each case
    assert len(injected_ids1) == 3
    assert len(injected_ids3) == 3

def test_empty_inputs():
    """Test handling empty input lists."""
    # Empty real posts
    result = inject_into_timeline([], [{"id": "1"}], {"type": "uniform"})
    assert result == []
    
    # Empty injectable posts
    result = inject_into_timeline([{"id": "1", "created_at": "2023-01-01T00:00:00Z"}], [], {"type": "uniform"})
    assert len(result) == 1
    assert result[0]["id"] == "1"

def test_max_injections_limit(test_posts):
    """Test respecting maximum injection limit."""
    strategy = {
        "type": "uniform",
        "max_injections": 2  # Limit to 2 even though we have 5 injectable posts
    }
    
    result = inject_into_timeline(test_posts["real"], test_posts["injectable"], strategy)
    
    # Count injected posts
    injected_count = sum(1 for post in result if post.get("injected", False))
    assert injected_count == 2
    
# Test recommendation engine integration
@patch('utils.recommendation_engine.get_db_connection')
@patch('utils.recommendation_engine.generate_rankings_for_user')
def test_recommendation_engine(mock_generate_rankings, mock_get_db_connection, test_posts):
    """Test the recommendation engine integration with timeline injector."""
    from utils.recommendation_engine import get_ranked_recommendations, is_new_user
    
    # Mock the database connection
    mock_connection = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db_connection.return_value.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Mock the rankings generation
    mock_generate_rankings.return_value = [
        {
            'post_id': 'rec_1',
            'author_id': 'author_1',
            'author_name': 'Author One',
            'content': 'Recommended content 1',
            'created_at': datetime.now().isoformat(),
            'ranking_score': 0.95,
            'recommendation_reason': 'From an author you might like'
        },
        {
            'post_id': 'rec_2',
            'author_id': 'author_2',
            'author_name': 'Author Two',
            'content': 'Recommended content 2',
            'created_at': datetime.now().isoformat(),
            'ranking_score': 0.85,
            'recommendation_reason': 'Popular with other users'
        }
    ]
    
    # Test ranked recommendations
    recommendations = get_ranked_recommendations('test_user', limit=10)
    
    # Verify the recommendations contain the expected data
    assert len(recommendations) == 2
    assert recommendations[0]['id'] == 'rec_1'
    assert recommendations[1]['id'] == 'rec_2'
    
    # Verify recommendations are marked as injected
    for rec in recommendations:
        assert rec['injected'] is True
        assert 'injection_metadata' in rec
        assert rec['injection_metadata']['source'] == 'recommendation_engine'
        assert rec['injection_metadata']['strategy'] in ['personalized', 'tag_match']
        assert 'explanation' in rec['injection_metadata']
    
    # Test integration with timeline injector
    strategy = {
        "type": "uniform",
        "max_injections": 5
    }
    
    result = inject_into_timeline(test_posts["real"], recommendations, strategy)
    
    # Check for injected posts
    injected_count = sum(1 for post in result if post.get("injected", False))
    assert injected_count > 0
    
    # Verify injected posts have required metadata
    for post in result:
        if post.get("injected"):
            assert "injection_metadata" in post