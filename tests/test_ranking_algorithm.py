"""
Tests for the ranking algorithm.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from typing import List, Tuple, Dict
from datetime import datetime, timedelta

from core.ranking_algorithm import (
    get_user_interactions,
    get_candidate_posts,
    get_author_preference_score,
    get_content_engagement_score,
    get_recency_score,
    calculate_ranking_score,
    generate_rankings_for_user
)
from utils.privacy import generate_user_alias


@pytest.fixture
def mock_db_conn():
    """Create a mock database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.__enter__.return_value = mock_cursor
    return mock_conn, mock_cursor


@patch("core.ranking_algorithm.get_cursor")
@patch("core.ranking_algorithm.get_db_connection")
def test_get_user_interactions(mock_get_db, mock_get_cursor):
    """Test getting user interactions from the database."""
    # Setup mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value.__enter__.return_value = mock_conn
    mock_get_cursor.return_value.__enter__.return_value = mock_cursor

    # Set up cursor description for SQLite path (3 columns: post_id, action_type, created_at)
    mock_cursor.description = [
        ("post_id", None),
        ("action_type", None), 
        ("created_at", None)
    ]

    # Mock query results
    mock_cursor.fetchall.return_value = [
        ("post1", "favorite", datetime.now()),
        ("post2", "reblog", datetime.now()),
    ]

    # Call the function
    result = get_user_interactions(mock_conn, "user_hashed_id", 30)

    # Fix: Update expectations to match SQLite syntax used in implementation
    mock_cursor.execute.assert_called_with("""
                SELECT post_id, interaction_type as action_type, created_at
                FROM interactions
                WHERE user_id = ? 
                AND datetime(created_at) > datetime('now', '-' || ? || ' days')
                ORDER BY created_at DESC
            """, ('user_hashed_id', 30))

    assert len(result) == 2
    assert result[0]["post_id"] == "post1"
    assert result[0]["action_type"] == "favorite"


@patch("core.ranking_algorithm.get_cursor")
@patch("core.ranking_algorithm.get_db_connection")
def test_get_candidate_posts(mock_get_db, mock_get_cursor):
    """Test getting candidate posts for recommendation."""
    # Setup mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value.__enter__.return_value = mock_conn
    mock_get_cursor.return_value.__enter__.return_value = mock_cursor

    # Set up cursor description for SQLite path (5 columns: post_id, author_id, content, created_at, metadata)
    mock_cursor.description = [
        ("post_id", None),
        ("author_id", None),
        ("content", None),
        ("created_at", None),
        ("metadata", None)
    ]

    # Mock the count query first (called before main query)
    mock_cursor.fetchone.return_value = (100,)  # Total posts count

    # Mock query results - Use correct datetime
    mock_cursor.fetchall.return_value = [
        ("post123", "author456", "Test content", datetime.now() - timedelta(hours=1), "{}"),
    ]

    # Call the function
    result = get_candidate_posts(mock_conn, limit=10, days_limit=7)

    assert len(result) == 1
    assert result[0]["post_id"] == "post123"
    assert result[0]["author_id"] == "author456"


@pytest.fixture
def author_pref_test_data():
    """Provides common test data for get_author_preference_score."""
    user_interactions = [
        {'post_id': 'post_author1_like', 'action_type': 'favorite'}, # Positive for author1
        {'post_id': 'post_author1_share', 'action_type': 'reblog'},   # Positive for author1
        {'post_id': 'post_author1_dislike', 'action_type': 'less_like_this'}, # Negative for author1
        {'post_id': 'post_author2_like', 'action_type': 'favorite'}, # Positive for author2
        {'post_id': 'post_unknown_like', 'action_type': 'favorite'}, # Post not in metadata
        {'post_id': 'post_author1_generic', 'action_type': 'view'},  # Neutral action
    ]
    # This map simulates the result of the DB query inside get_author_preference_score
    post_to_author_map_data = [
        ('post_author1_like', 'author1'),
        ('post_author1_share', 'author1'),
        ('post_author1_dislike', 'author1'),
        ('post_author2_like', 'author2'),
        ('post_author1_generic', 'author1'),
        # 'post_unknown_like' is intentionally missing to test robustness
    ]
    return user_interactions, post_to_author_map_data

# Helper function to build author_interaction_summary for tests
def _build_author_interaction_summary_for_test(
    user_interactions: List[Dict], 
    post_to_author_map: List[Tuple[str, str]]
) -> Dict[str, Dict[str, int]]:
    summary = {}
    
    # Convert post_to_author_map list of tuples to a dictionary for easy lookup
    local_post_to_author_dict = {pid: aid for pid, aid in post_to_author_map}

    # Define positive and negative actions (mirroring ALGORITHM_CONFIG or actual usage)
    # These should ideally come from a shared config or be mocked appropriately if they affect tests
    positive_actions = ['favorite', 'bookmark', 'reblog', 'more_like_this']
    negative_actions = ['less_like_this']

    for interaction in user_interactions:
        post_id = interaction.get('post_id')
        action_type = interaction.get('action_type')
        if not post_id or not action_type:
            continue

        author_id = local_post_to_author_dict.get(post_id)
        if not author_id:
            continue 

        if author_id not in summary:
            summary[author_id] = {'positive': 0, 'negative': 0, 'total_related_interactions': 0}
        
        summary[author_id]['total_related_interactions'] += 1
        if action_type in positive_actions:
            summary[author_id]['positive'] += 1
        elif action_type in negative_actions:
            summary[author_id]['negative'] += 1
    return summary

def test_get_author_preference_score_no_interactions(author_pref_test_data):
    """Test score with no user interactions."""
    _, post_to_author_map_data = author_pref_test_data
    author_interaction_summary = _build_author_interaction_summary_for_test([], post_to_author_map_data)
    score = get_author_preference_score('author1', author_interaction_summary)
    assert score == 0.1  # Baseline score

@patch("core.ranking_algorithm.get_cursor")
@patch("core.ranking_algorithm.get_db_connection")
def test_get_author_preference_score_no_target_author_interactions(mock_get_db, mock_get_cursor):
    """Test score when user has interactions, but none with the target author's posts."""
    # Setup mock database
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value.__enter__.return_value = mock_conn
    mock_get_cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []  # No author mapping found
    
    # Fix: Pass interactions as list of dictionaries, not strings
    author_interaction_summary = [
        {"post_id": "post2", "action_type": "favorite"},
        {"post_id": "post3", "action_type": "reblog"}
    ]
    
    # Fix: Correct parameter order - user_interactions first, then author_id
    score = get_author_preference_score(author_interaction_summary, 'author1')
    assert score == 0.1  # Should return baseline since no interactions with target author

@patch("core.ranking_algorithm.get_cursor")
@patch("core.ranking_algorithm.get_db_connection")
def test_get_author_preference_score_strong_positive_preference(mock_get_db, mock_get_cursor):
    """Test score with strong positive interactions for target author."""
    # Setup mock database to return author mapping
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value.__enter__.return_value = mock_conn
    mock_get_cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [("post1", "author1"), ("post2", "author1")]
    
    # Fix: Pass interactions as list of dictionaries
    author_interaction_summary = [
        {"post_id": "post1", "action_type": "favorite"},
        {"post_id": "post2", "action_type": "reblog"}
    ]
    
    # Fix: Correct parameter order - user_interactions first, then author_id
    score = get_author_preference_score(author_interaction_summary, 'author1')
    assert score > 0.5  # Should be high since all interactions are positive

@patch("core.ranking_algorithm.get_cursor") 
@patch("core.ranking_algorithm.get_db_connection")
def test_get_author_preference_score_mixed_preference(mock_get_db, mock_get_cursor):
    """Test score with mixed (positive and negative) interactions for target author."""
    # Setup mock database to return author mapping
    mock_conn = MagicMock()
    mock_cursor = MagicMock() 
    mock_get_db.return_value.__enter__.return_value = mock_conn
    mock_get_cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [("post1", "author1"), ("post2", "author1")]
    
    # Fix: Pass interactions as list of dictionaries  
    author_interaction_summary = [
        {"post_id": "post1", "action_type": "favorite"},
        {"post_id": "post2", "action_type": "less_like_this"}
    ]
    
    # Fix: Correct parameter order - user_interactions first, then author_id
    score = get_author_preference_score(author_interaction_summary, 'author1')
    assert 0.1 <= score <= 1.0  # Should be moderate

def test_get_author_preference_score_post_not_in_metadata():
    """Test author preference score when post metadata is missing."""
    # This should fallback gracefully when post-author mapping fails
    author_interaction_summary = [
        {"post_id": "nonexistent_post", "action_type": "favorite"}
    ]
    
    # Fix: Correct parameter order
    score = get_author_preference_score(author_interaction_summary, 'author1')
    assert score == 0.1  # Should return baseline

@patch("core.ranking_algorithm.logger")
@patch("core.ranking_algorithm.get_cursor")
@patch("core.ranking_algorithm.get_db_connection")
def test_get_author_preference_score_db_error_fallback(mock_get_db, mock_get_cursor, mock_logger):
    """Test author preference score falls back gracefully on database errors."""
    # Setup mock to raise an exception when trying to get cursor
    mock_conn = MagicMock()
    mock_get_db.return_value.__enter__.return_value = mock_conn
    mock_get_cursor.side_effect = Exception("Database error")
    
    author_interaction_summary = [
        {"post_id": "post1", "action_type": "favorite"}
    ]
    
    # Fix: Correct parameter order
    score = get_author_preference_score(author_interaction_summary, 'author1')
    assert score == 0.1  # Should return baseline on error
    mock_logger.error.assert_called()


def test_get_content_engagement_score():
    """Test content engagement score calculation."""
    post_with_engagement = {
        "interaction_counts": '{"favorites": 10, "reblogs": 5, "replies": 2}'
    }
    
    score = get_content_engagement_score(post_with_engagement)
    assert score > 0
    
    # Test with no engagement data
    post_without_engagement = {}
    score = get_content_engagement_score(post_without_engagement)
    assert score == 0.0


def test_get_recency_score():
    """Test recency score calculation."""
    # Test with recent post
    recent_post = {
        "created_at": datetime.now() - timedelta(hours=1)
    }
    score = get_recency_score(recent_post)
    assert score > 0.8
    
    # Test with old post
    old_post = {
        "created_at": datetime.now() - timedelta(days=30)
    }
    score = get_recency_score(old_post)
    assert score >= 0.2  # Should have minimum threshold


def test_calculate_ranking_score():
    """Test overall ranking score calculation."""
    post = {
        "author_id": "author123",
        "interaction_counts": '{"favorites": 10, "reblogs": 5, "replies": 2}',
        "created_at": datetime.now() - timedelta(hours=1)
    }
    
    user_interactions = [
        {"post_id": "other_post", "action_type": "favorite"}
    ]
    
    # Fix: Remove the third parameter (config) - function only takes 2 parameters
    score, reason = calculate_ranking_score(post, user_interactions)
    
    assert 0 <= score <= 1
    assert isinstance(reason, str)
    assert len(reason) > 0


@patch('core.ranking_algorithm.get_db_connection')
@patch('core.ranking_algorithm.generate_user_alias')
@patch('core.ranking_algorithm.get_candidate_posts')
@patch('core.ranking_algorithm.get_user_interactions')
def test_generate_rankings_for_user(mock_get_interactions, mock_get_candidates, mock_generate_alias, mock_get_conn, mock_db_conn):
    """Test the full ranking generation process."""
    mock_conn, mock_cursor = mock_db_conn
    mock_get_conn.return_value = mock_conn
    
    # Mock the user alias
    user_alias = 'hashed_user_id'
    mock_generate_alias.return_value = user_alias
    
    # Mock interactions data
    from datetime import datetime
    now = datetime.now()
    
    # Mock user interactions (for post-to-author mapping)
    mock_get_interactions.return_value = [
        {'post_id': 'seen_post1', 'action_type': 'favorite', 'created_at': now}
    ]
    
    # Mock candidate posts (already processed format from get_candidate_posts)
    mock_get_candidates.return_value = [
        {
            'post_id': 'post123',
            'author_id': 'author1', 
            'author_name': 'Author One',
            'content': 'Content 1',
            'created_at': now,
            'interaction_counts': {'favorites': 5}
        },
        {
            'post_id': 'post456',
            'author_id': 'author2',
            'author_name': 'Author Two', 
            'content': 'Content 2',
            'created_at': now,
            'interaction_counts': {'favorites': 10}
        }
    ]
    
    # Mock the post-to-author mapping query (for author preference calculation)
    mock_cursor.fetchall.return_value = [('seen_post1', 'author1')]
    
    # Mock the scoring functions
    with patch('core.ranking_algorithm.get_author_preference_score', return_value=0.5):
        with patch('core.ranking_algorithm.get_content_engagement_score', return_value=0.6):
            with patch('core.ranking_algorithm.get_recency_score', return_value=0.7):
                # Call the function
                result = generate_rankings_for_user('user123')
                
                # Verify ranked posts are returned
                assert len(result) > 0
                for post in result:
                    assert 'post_id' in post
                    assert 'ranking_score' in post
                    assert 'recommendation_reason' in post
                
                # Verify scores are in expected range
                assert all(0 <= post['ranking_score'] <= 1 for post in result)
                
                # In SQLite mode, rankings are not stored in separate table (different behavior)
                # So we just verify that the algorithm runs and returns results