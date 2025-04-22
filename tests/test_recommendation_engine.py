"""
Tests for the recommendation engine module.
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from utils.recommendation_engine import (
    get_ranked_recommendations,
    load_cold_start_posts,
    is_new_user
)

# Create test fixture for recommendation data
@pytest.fixture
def mock_ranking_data():
    """
    Generate mock ranking data for testing.
    """
    return [
        {
            'post_id': 'post1',
            'author_id': 'user1',
            'author_name': 'Test User 1',
            'content': 'This is a test post with high engagement',
            'created_at': (datetime.now() - timedelta(hours=2)).isoformat(),
            'ranking_score': 0.95,
            'recommendation_reason': 'Popular with other users'
        },
        {
            'post_id': 'post2',
            'author_id': 'user2',
            'author_name': 'Test User 2',
            'content': 'This is a test post with medium engagement',
            'created_at': (datetime.now() - timedelta(hours=4)).isoformat(),
            'ranking_score': 0.75,
            'recommendation_reason': 'From an author you might like'
        },
        {
            'post_id': 'post3',
            'author_id': 'user3',
            'author_name': 'Test User 3',
            'content': 'This is a test post with low engagement',
            'created_at': (datetime.now() - timedelta(hours=6)).isoformat(),
            'ranking_score': 0.55,
            'recommendation_reason': 'Recently posted'
        }
    ]

@pytest.fixture
def mock_cold_start_data():
    """
    Generate mock cold start data for testing.
    """
    return [
        {
            'id': 'cold1',
            'content': 'Cold start post 1',
            'created_at': datetime.now().isoformat(),
            'account': {
                'id': 'cold_user1',
                'username': 'colduser1',
                'display_name': 'Cold User 1'
            }
        },
        {
            'id': 'cold2',
            'content': 'Cold start post 2',
            'created_at': datetime.now().isoformat(),
            'account': {
                'id': 'cold_user2',
                'username': 'colduser2',
                'display_name': 'Cold User 2'
            }
        }
    ]

# Test loading cold start posts
@patch('utils.recommendation_engine.open')
def test_load_cold_start_posts(mock_open, mock_cold_start_data):
    """Test loading cold start posts from JSON file."""
    # Configure the mock to return appropriate data
    mock_file = MagicMock()
    mock_file.__enter__.return_value.read.return_value = json.dumps(mock_cold_start_data)
    mock_open.return_value = mock_file
    
    # Call the function
    posts = load_cold_start_posts()
    
    # Assertions
    assert mock_open.called
    assert len(posts) == 2
    assert posts[0]['id'] == 'cold1'
    assert posts[1]['id'] == 'cold2'

# Test checking if user is new
@patch('utils.recommendation_engine.get_db_connection')
@patch('utils.recommendation_engine.generate_user_alias')
def test_is_new_user(mock_generate_alias, mock_get_db_connection):
    """Test determining if a user is new based on interaction history."""
    # Setup mocks
    mock_generate_alias.return_value = 'hashed_user123'
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Test anonymous user
    assert is_new_user('anonymous') is True
    assert is_new_user(None) is True
    
    # Test synthetic user
    assert is_new_user('corgi_validator_123') is True
    assert is_new_user('test_user456') is True
    
    # Test user with no interactions
    mock_cursor.fetchone.return_value = (0,)
    assert is_new_user('regular_user') is True
    
    # Test user with few interactions
    mock_cursor.fetchone.return_value = (3,)
    assert is_new_user('regular_user') is True
    
    # Test user with sufficient interactions
    mock_cursor.fetchone.return_value = (10,)
    assert is_new_user('regular_user') is False

# Test getting ranked recommendations
@patch('utils.recommendation_engine.generate_rankings_for_user')
@patch('utils.recommendation_engine.get_db_connection')
@patch('utils.recommendation_engine.is_new_user')
@patch('utils.recommendation_engine.load_cold_start_posts')
def test_get_ranked_recommendations(mock_load_cold_start, mock_is_new_user, 
                                    mock_get_db_connection, mock_generate_rankings,
                                    mock_ranking_data, mock_cold_start_data):
    """Test getting ranked recommendations for users."""
    # Setup mocks
    mock_load_cold_start.return_value = mock_cold_start_data
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (None,)  # No Mastodon post found
    
    # Test anonymous user
    posts = get_ranked_recommendations(None, 5)
    assert len(posts) == 2
    assert posts[0]['id'] == 'cold1'
    
    # Test synthetic user
    posts = get_ranked_recommendations('corgi_validator_123', 5)
    assert len(posts) == 2
    assert posts[0]['id'] == 'cold1'
    
    # Test new user
    mock_is_new_user.return_value = True
    posts = get_ranked_recommendations('new_user', 5)
    assert len(posts) == 2
    assert posts[0]['id'] == 'cold1'
    
    # Test returning user with recommendations
    mock_is_new_user.return_value = False
    mock_generate_rankings.return_value = mock_ranking_data
    
    posts = get_ranked_recommendations('returning_user', 5)
    
    # Verify post properties
    assert len(posts) == 3
    assert posts[0]['id'] == 'post1'  # Highest ranked post
    assert posts[0]['injected'] is True
    assert posts[0]['injection_metadata']['source'] == 'recommendation_engine'
    assert posts[0]['injection_metadata']['explanation'] == 'Popular with other users'
    
    # Verify ranking order
    assert posts[0]['injection_metadata']['score'] > posts[1]['injection_metadata']['score']
    assert posts[1]['injection_metadata']['score'] > posts[2]['injection_metadata']['score']
    
    # Test falling back when no rankings are generated
    mock_generate_rankings.return_value = []
    posts = get_ranked_recommendations('returning_user', 5)
    assert len(posts) == 2  # Cold start fallback
    assert posts[0]['id'] == 'cold1'
    
    # Test handling DB errors
    mock_generate_rankings.side_effect = Exception("DB Error")
    posts = get_ranked_recommendations('returning_user', 5)
    assert len(posts) == 2  # Cold start fallback
    assert posts[0]['id'] == 'cold1'

# Test integration with real Mastodon post data
@patch('utils.recommendation_engine.generate_rankings_for_user')
@patch('utils.recommendation_engine.get_db_connection')
@patch('utils.recommendation_engine.is_new_user')
def test_recommendations_with_mastodon_data(mock_is_new_user, mock_get_db_connection,
                                           mock_generate_rankings, mock_ranking_data):
    """Test that recommendations correctly use Mastodon post data when available."""
    # Setup mocks
    mock_is_new_user.return_value = False
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Create a mock Mastodon post in the database
    mastodon_post = {
        "id": "post1",
        "content": "<p>Real Mastodon post content</p>",
        "created_at": datetime.now().isoformat(),
        "account": {
            "id": "mastodon_user1",
            "username": "mastodon_user",
            "display_name": "Mastodon User",
            "url": "https://mastodon.social/@mastodon_user"
        },
        "media_attachments": [
            {
                "id": "media1",
                "type": "image",
                "url": "https://example.com/image.jpg"
            }
        ],
        "favourites_count": 42,
        "reblogs_count": 12,
        "replies_count": 7
    }
    
    # First post has Mastodon data, second doesn't
    mock_cursor.fetchone.side_effect = [
        (mastodon_post,),  # Return the Mastodon post for first post_id
        (None,),           # Return None for second post_id
        (None,)            # Return None for third post_id
    ]
    
    mock_generate_rankings.return_value = mock_ranking_data
    
    # Get recommendations
    posts = get_ranked_recommendations('returning_user', 5)
    
    # Verify results
    assert len(posts) == 3
    
    # First post should use the Mastodon post data
    assert posts[0]['id'] == 'post1'
    assert posts[0]['content'] == "<p>Real Mastodon post content</p>"
    assert posts[0]['account']['username'] == "mastodon_user"
    assert len(posts[0]['media_attachments']) == 1
    assert posts[0]['favourites_count'] == 42
    
    # All posts should have injection metadata
    for post in posts:
        assert post['injected'] is True
        assert 'injection_metadata' in post
        assert post['injection_metadata']['source'] == 'recommendation_engine'