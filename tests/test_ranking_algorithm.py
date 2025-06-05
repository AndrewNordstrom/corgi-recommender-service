"""
Tests for the ranking algorithm.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from typing import List, Tuple, Dict

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
    
    # Setup mock cursor description for PostgreSQL mode - 4 fields returned  
    mock_cursor.description = [
        ('post_id', None, None, None, None, None, None),
        ('action_type', None, None, None, None, None, None),
        ('context', None, None, None, None, None, None),
        ('created_at', None, None, None, None, None, None)
    ]
    
    # Sample data for PostgreSQL mode (4 fields: post_id, action_type, context, created_at)
    mock_cursor.fetchall.return_value = [
        ('post123', 'favorite', 'context1', '2023-01-01 12:00:00'),
        ('post456', 'reblog', 'context2', '2023-01-01 11:00:00')
    ]
    
    user_id = 'user_hashed_id'
    
    # Call the function
    result = get_user_interactions(mock_conn, user_id, days_limit=30)
    
    # Verify DB query - match the actual PostgreSQL format
    mock_cursor.execute.assert_called_with("""
                SELECT post_id, action_type, context, created_at
                FROM interactions
                WHERE user_alias = %s
                AND created_at > NOW() - INTERVAL '%s days'
                ORDER BY created_at DESC
            """, (user_id, 30))
    
    # Verify result format - check that the function properly converts PostgreSQL results to the expected format
    assert len(result) == 2
    assert result[0]['post_id'] == 'post123'
    assert result[0]['action_type'] == 'favorite'
    assert result[1]['post_id'] == 'post456'


def test_get_candidate_posts(mock_db_conn):
    """Test retrieving candidate posts."""
    mock_conn, mock_cursor = mock_db_conn
    
    # Sample data for PostgreSQL mode (6 fields: post_id, author_id, author_name, content, created_at, interaction_counts)
    from datetime import datetime, timedelta
    import json
    now = datetime.now()
    
    # Mock for PostgreSQL query - provide 6 values to match the PostgreSQL schema
    interaction_counts_1 = {"favorites": 5, "reblogs": 2}
    interaction_counts_2 = {"favorites": 10, "reblogs": 5}
    
    # Setup mock cursor description for PostgreSQL mode - 6 fields returned
    mock_cursor.description = [
        ('post_id', None, None, None, None, None, None),
        ('author_id', None, None, None, None, None, None),
        ('author_name', None, None, None, None, None, None),
        ('content', None, None, None, None, None, None),
        ('created_at', None, None, None, None, None, None),
        ('interaction_counts', None, None, None, None, None, None)
    ]
    
    # Mock two fetchone calls for the count queries at the beginning
    mock_cursor.fetchone.side_effect = [
        (100,),  # total_real_posts count  
        (50,),   # total_synthetic_posts count
        # Note: No more fetchone calls needed as the main query uses fetchall
    ]
    
    mock_cursor.fetchall.return_value = [
        ('post123', 'author1', 'Author One', 'Content 1', now - timedelta(days=1), interaction_counts_1),
        ('post456', 'author2', 'Author Two', 'Content 2', now - timedelta(days=2), interaction_counts_2)
    ]
    
    # Call the function
    result = get_candidate_posts(mock_conn, limit=10, days_limit=7)
    
    # Verify result format - check that the function properly converts PostgreSQL results to the expected format
    assert len(result) == 2
    assert result[0]['post_id'] == 'post123'
    assert result[0]['author_id'] == 'author1'
    assert result[0]['author_name'] == 'Author One'
    assert result[0]['content'] == 'Content 1'
    assert result[0]['interaction_counts'] == {'favorites': 5, 'reblogs': 2}
    assert result[1]['post_id'] == 'post456'
    assert result[1]['author_id'] == 'author2'
    assert result[1]['author_name'] == 'Author Two'


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

def test_get_author_preference_score_no_target_author_interactions(author_pref_test_data):
    """Test score when user has interactions, but none with the target author's posts."""
    user_interactions, post_to_author_map_data = author_pref_test_data
    interactions_for_others = [
        ui for ui in user_interactions if ui['post_id'] == 'post_author2_like' or ui['post_id'] == 'post_unknown_like'
    ]
    author_interaction_summary = _build_author_interaction_summary_for_test(interactions_for_others, post_to_author_map_data)
    score = get_author_preference_score('author1', author_interaction_summary)
    assert score == 0.1 

def test_get_author_preference_score_strong_positive_preference(author_pref_test_data):
    """Test score with strong positive interactions for target author."""
    user_interactions, post_to_author_map_data = author_pref_test_data
    positive_author1_interactions = [
        ui for ui in user_interactions if ui['post_id'] in ('post_author1_like', 'post_author1_share')
    ]
    author_interaction_summary = _build_author_interaction_summary_for_test(positive_author1_interactions, post_to_author_map_data)
    score = get_author_preference_score('author1', author_interaction_summary)
    assert score == 1.0 # Expect a significantly higher score

def test_get_author_preference_score_mixed_preference(author_pref_test_data):
    """Test score with mixed (positive and negative) interactions for target author."""
    user_interactions, post_to_author_map_data = author_pref_test_data
    all_author1_interactions = [
        ui for ui in user_interactions if ui['post_id'] in ('post_author1_like', 'post_author1_share', 'post_author1_dislike', 'post_author1_generic')
    ] # Includes: 2 positive ('favorite', 'reblog'), 1 negative ('less_like_this'), 1 neutral ('view') for author1 posts
    
    author_interaction_summary = _build_author_interaction_summary_for_test(all_author1_interactions, post_to_author_map_data)
    score = get_author_preference_score('author1', author_interaction_summary)
    assert 0.583 < score < 0.584

def test_get_author_preference_score_post_not_in_metadata(author_pref_test_data):
    """Test behavior when an interacted post_id is not in the post_to_author_map."""
    user_interactions, post_to_author_map_data = author_pref_test_data
    unknown_post_interaction = [ui for ui in user_interactions if ui['post_id'] == 'post_unknown_like']
    
    author_interaction_summary = _build_author_interaction_summary_for_test(unknown_post_interaction, post_to_author_map_data)
    score_for_author1 = get_author_preference_score('author1', author_interaction_summary)
    assert score_for_author1 == 0.1

def test_get_author_preference_score_db_error_fallback(author_pref_test_data):
    """Test that the function returns baseline if author_interaction_summary is missing data for target author."""
    _, _post_to_author_map = author_pref_test_data # Not directly used
    
    # Simulate a scenario where author_interaction_summary is built but 'author1' is missing,
    # or an error prevented its inclusion.
    empty_summary_for_author1 = {} 
    score = get_author_preference_score('author1', empty_summary_for_author1)
    assert score == 0.1 # Should fallback to baseline


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

    # Sample author interaction summary (correct format)
    author_interaction_summary = {
        'author1': {
            'positive': 5,
            'negative': 1,
            'total': 6
        }
    }

    # Sample config with weights
    config = {
        'weights': {
            'author_preference': 0.4,
            'content_engagement': 0.3,
            'recency': 0.3
        }
    }

    # Calculate score with these mocks
    with patch('core.ranking_algorithm.get_author_preference_score') as mock_author_score:
        with patch('core.ranking_algorithm.get_content_engagement_score') as mock_engagement_score:
            with patch('core.ranking_algorithm.get_recency_score') as mock_recency_score:
                # Set mock return values
                mock_author_score.return_value = 0.5
                mock_engagement_score.return_value = 0.7
                mock_recency_score.return_value = 0.9
                
                # Calculate score with correct parameters
                score, reason = calculate_ranking_score(post, author_interaction_summary, config)
                
                # Verify score is calculated
                assert 0 <= score <= 1
                # Verify reason is provided
                assert reason in [
                    "From an author you might like",
                    "Popular with other users",
                    "Recently posted",
                    "Recommended for you"  # Added default reason
                ]


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