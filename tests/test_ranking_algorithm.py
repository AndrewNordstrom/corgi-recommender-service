"""
Tests for the ranking algorithm.
"""

import pytest
import json
from unittest.mock import patch, MagicMock

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


def test_get_user_interactions(mock_db_conn):
    """Test retrieving user interactions."""
    mock_conn, mock_cursor = mock_db_conn
    
    # Setup mock cursor description and data
    mock_cursor.description = [
        ('post_id', None, None, None, None, None, None),
        ('action_type', None, None, None, None, None, None),
        ('context', None, None, None, None, None, None),
        ('created_at', None, None, None, None, None, None)
    ]
    
    # Sample data
    from datetime import datetime, timedelta
    now = datetime.now()
    mock_cursor.fetchall.return_value = [
        ('post123', 'favorite', '{"source":"test"}', now - timedelta(days=1)),
        ('post456', 'reblog', '{}', now - timedelta(days=2))
    ]
    
    # Call the function
    user_id = 'user_hashed_id'
    result = get_user_interactions(mock_conn, user_id, days_limit=30)
    
    # Verify DB query
    mock_cursor.execute.assert_called_with(
        "SELECT post_id, action_type, context, created_at FROM interactions WHERE user_alias = %s AND created_at > NOW() - INTERVAL '%s days' ORDER BY created_at DESC",
        (user_id, 30)
    )
    
    # Verify result format
    assert len(result) == 2
    assert result[0]['post_id'] == 'post123'
    assert result[0]['action_type'] == 'favorite'
    assert result[1]['post_id'] == 'post456'


def test_get_candidate_posts(mock_db_conn):
    """Test retrieving candidate posts."""
    mock_conn, mock_cursor = mock_db_conn
    
    # Setup mock cursor description and data
    mock_cursor.description = [
        ('post_id', None, None, None, None, None, None),
        ('author_id', None, None, None, None, None, None),
        ('author_name', None, None, None, None, None, None),
        ('content', None, None, None, None, None, None),
        ('created_at', None, None, None, None, None, None),
        ('interaction_counts', None, None, None, None, None, None)
    ]
    
    # First return the real posts count
    mock_cursor.fetchone.return_value = (5,)
    
    # Sample data
    from datetime import datetime, timedelta
    now = datetime.now()
    
    # Mock for the actual query
    mock_cursor.fetchall.return_value = [
        ('post123', 'author1', 'Author One', 'Content 1', now - timedelta(days=1), '{"favorites":5}'),
        ('post456', 'author2', 'Author Two', 'Content 2', now - timedelta(days=2), '{"favorites":10}')
    ]
    
    # Call the function
    result = get_candidate_posts(mock_conn, limit=10, days_limit=7)
    
    # Verify result format
    assert len(result) == 2
    assert result[0]['post_id'] == 'post123'
    assert result[0]['author_id'] == 'author1'
    assert result[1]['post_id'] == 'post456'
    assert result[1]['author_id'] == 'author2'


def test_get_author_preference_score():
    """Test calculating author preference score."""
    # Create sample user interactions
    from datetime import datetime
    now = datetime.now()
    
    user_interactions = [
        {'post_id': 'post123', 'action_type': 'favorite', 'created_at': now},
        {'post_id': 'post456', 'action_type': 'reblog', 'created_at': now}
    ]
    
    # Test with a matching author - we expect a higher score
    with patch('core.ranking_algorithm.get_db_connection') as mock_get_conn:
        # Setup mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        # Mock cursor to return post-author mapping
        mock_cursor.fetchall.return_value = [
            ('post123', 'author1'),
            ('post456', 'author1')
        ]
        
        # Call the function with the same author
        score = get_author_preference_score(user_interactions, 'author1')
        
        # Score should be higher than baseline for matching author
        assert score >= 0.1
        
        # Now test with a different author - score should be baseline
        score = get_author_preference_score(user_interactions, 'author2')
        assert score == 0.1


def test_get_content_engagement_score():
    """Test calculating content engagement score."""
    # Test with high engagement
    high_engagement_post = {
        'interaction_counts': {
            'favorites': 100,
            'reblogs': 50,
            'replies': 25
        }
    }
    high_score = get_content_engagement_score(high_engagement_post)
    
    # Test with low engagement
    low_engagement_post = {
        'interaction_counts': {
            'favorites': 1,
            'reblogs': 0,
            'replies': 0
        }
    }
    low_score = get_content_engagement_score(low_engagement_post)
    
    # Test with no engagement data
    no_engagement_post = {}
    no_score = get_content_engagement_score(no_engagement_post)
    
    # High engagement should have higher score than low
    assert high_score > low_score
    # No engagement should be zero
    assert no_score == 0.0


def test_get_recency_score():
    """Test calculating recency score."""
    from datetime import datetime, timedelta
    now = datetime.now()
    
    # Test with very recent post
    recent_post = {'created_at': now - timedelta(hours=1)}
    recent_score = get_recency_score(recent_post)
    
    # Test with older post
    old_post = {'created_at': now - timedelta(days=10)}
    old_score = get_recency_score(old_post)
    
    # Test with missing timestamp
    no_date_post = {}
    no_date_score = get_recency_score(no_date_post)
    
    # Recent post should have higher score
    assert recent_score > old_score
    # Missing date should use default
    assert no_date_score == 0.5


def test_calculate_ranking_score():
    """Test calculating overall ranking score."""
    from datetime import datetime
    now = datetime.now()
    
    # Sample post
    post = {
        'post_id': 'post123',
        'author_id': 'author1',
        'content': 'Test content',
        'created_at': now,
        'interaction_counts': {
            'favorites': 10,
            'reblogs': 5
        }
    }
    
    # Sample user interactions
    user_interactions = [
        {'post_id': 'other_post', 'action_type': 'favorite', 'created_at': now}
    ]
    
    # Calculate score with these mocks
    with patch('core.ranking_algorithm.get_author_preference_score') as mock_author_score:
        with patch('core.ranking_algorithm.get_content_engagement_score') as mock_engagement_score:
            with patch('core.ranking_algorithm.get_recency_score') as mock_recency_score:
                # Set mock return values
                mock_author_score.return_value = 0.5
                mock_engagement_score.return_value = 0.7
                mock_recency_score.return_value = 0.9
                
                # Calculate score
                score, reason = calculate_ranking_score(post, user_interactions)
                
                # Verify score is calculated
                assert 0 <= score <= 1
                # Verify reason is provided
                assert reason in [
                    "From an author you might like",
                    "Popular with other users",
                    "Recently posted"
                ]


@patch('core.ranking_algorithm.get_db_connection')
@patch('core.ranking_algorithm.generate_user_alias')
def test_generate_rankings_for_user(mock_generate_alias, mock_get_conn, mock_db_conn):
    """Test the full ranking generation process."""
    mock_conn, mock_cursor = mock_db_conn
    mock_get_conn.return_value = mock_conn
    
    # Mock the user alias
    user_alias = 'hashed_user_id'
    mock_generate_alias.return_value = user_alias
    
    # Mock interactions data
    from datetime import datetime
    now = datetime.now()
    
    # Setup for get_user_interactions
    mock_cursor.description = [
        ('post_id', None, None, None, None, None, None),
        ('action_type', None, None, None, None, None, None),
        ('context', None, None, None, None, None, None),
        ('created_at', None, None, None, None, None, None)
    ]
    mock_cursor.fetchall.side_effect = [
        # First for get_user_interactions
        [('seen_post1', 'favorite', '{}', now)],
        # Second for get_candidate_posts total count
        [],
        # Third for get_candidate_posts
        [
            ('post123', 'author1', 'Author One', 'Content 1', now, '{"favorites":5}', None),
            ('post456', 'author2', 'Author Two', 'Content 2', now, '{"favorites":10}', None)
        ]
    ]
    mock_cursor.fetchone.return_value = (5,)  # For real posts count
    
    # Mock post-author mapping in get_author_preference_score
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
                
                # Verify DB operations for storing rankings
                mock_cursor.execute.assert_any_call(
                    "INSERT INTO post_rankings (user_id, post_id, ranking_score, recommendation_reason) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id, post_id) DO UPDATE SET ranking_score = EXCLUDED.ranking_score, recommendation_reason = EXCLUDED.recommendation_reason, created_at = CURRENT_TIMESTAMP",
                    (user_alias, result[0]['post_id'], result[0]['ranking_score'], result[0]['recommendation_reason'])
                )