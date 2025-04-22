"""
Tests for the recommendations routes.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from config import API_PREFIX

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


@patch('routes.recommendations.get_db_connection')
def test_get_recommendations(mock_get_db, client, mock_db_conn):
    """Test getting recommendations for a user."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    
    # Mock database results
    mock_cursor.fetchone.return_value = (10,)  # 10 real posts in DB
    
    # Create sample mastodon post data
    mastodon_post1 = json.dumps({
        "id": "post123",
        "content": "<p>Recommended post 1</p>",
        "account": {"username": "author1"},
        "favourites_count": 15
    })
    mastodon_post2 = json.dumps({
        "id": "post456",
        "content": "<p>Recommended post 2</p>",
        "account": {"username": "author2"},
        "favourites_count": 8
    })
    
    # Mock ranking data with mastodon posts
    mock_cursor.fetchall.return_value = [
        ("post123", 0.9, "Recently posted", mastodon_post1),
        ("post456", 0.7, "Popular with other users", mastodon_post2)
    ]
    
    # Make request
    response = client.get(f'{API_PREFIX}/recommendations?user_id=user123')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["user_id"] == "user123"
    assert len(data["recommendations"]) == 2
    assert data["recommendations"][0]["id"] == "post123"
    assert data["recommendations"][0]["ranking_score"] == 0.9
    assert data["recommendations"][0]["recommendation_reason"] == "Recently posted"
    assert data["recommendations"][1]["id"] == "post456"
    
    # Verify DB operations
    user_alias = generate_user_alias("user123")
    mock_cursor.execute.assert_any_call(
        "SELECT COUNT(*) FROM post_metadata WHERE mastodon_post IS NOT NULL"
    )
    mock_cursor.execute.assert_any_call(
        "SELECT pr.post_id, pr.ranking_score, pr.recommendation_reason, pm.mastodon_post FROM post_rankings pr JOIN post_metadata pm ON pr.post_id = pm.post_id WHERE pr.user_id = %s ORDER BY pr.ranking_score DESC LIMIT %s",
        (user_alias, 10)
    )


@patch('routes.recommendations.get_db_connection')
def test_get_recommendations_no_rankings(mock_get_db, client, mock_db_conn):
    """Test getting recommendations when no rankings exist."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    
    # Mock database results
    mock_cursor.fetchone.return_value = (5,)  # 5 real posts in DB
    mock_cursor.fetchall.return_value = []  # No rankings
    
    # Make request
    response = client.get(f'{API_PREFIX}/recommendations?user_id=user123')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["user_id"] == "user123"
    assert len(data["recommendations"]) == 0
    assert "No recommendations found" in data["message"]
    assert data["debug_info"]["real_posts_in_db"] == 5
    
    # Verify DB operations
    user_alias = generate_user_alias("user123")
    mock_cursor.execute.assert_any_call(
        "SELECT COUNT(*) FROM post_metadata WHERE mastodon_post IS NOT NULL"
    )
    mock_cursor.execute.assert_any_call(
        "SELECT pr.post_id, pr.ranking_score, pr.recommendation_reason, pm.mastodon_post FROM post_rankings pr JOIN post_metadata pm ON pr.post_id = pm.post_id WHERE pr.user_id = %s ORDER BY pr.ranking_score DESC LIMIT %s",
        (user_alias, 10)
    )


@patch('routes.recommendations.generate_rankings_for_user')
@patch('routes.recommendations.get_db_connection')
def test_generate_rankings(mock_get_db, mock_generate_rankings, client, mock_db_conn):
    """Test generating rankings for a user."""
    # Setup mocks
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    
    # Mock no existing rankings
    mock_cursor.fetchone.return_value = (0,)  # No recent rankings
    
    # Mock ranking generation
    mock_generate_rankings.return_value = [
        {"post_id": "post123", "ranking_score": 0.9, "recommendation_reason": "Recently posted"},
        {"post_id": "post456", "ranking_score": 0.7, "recommendation_reason": "Popular with other users"}
    ]
    
    # Test data
    test_data = {"user_id": "user123"}
    
    # Make request
    response = client.post('/v1/recommendations/rankings/generate', 
                          json=test_data,
                          content_type='application/json')
    
    # Verify response
    assert response.status_code == 201
    data = json.loads(response.data)
    assert "Rankings generated successfully" in data["message"]
    assert data["count"] == 2
    
    # Verify DB operations
    user_alias = generate_user_alias("user123")
    mock_cursor.execute.assert_called_with(
        "SELECT COUNT(*) FROM post_rankings WHERE user_id = %s AND created_at > NOW() - INTERVAL '1 hour'",
        (user_alias,)
    )
    
    # Verify ranking generator was called
    mock_generate_rankings.assert_called_with("user123")


@patch('routes.recommendations.generate_rankings_for_user')
@patch('routes.recommendations.get_db_connection')
def test_generate_rankings_existing(mock_get_db, mock_generate_rankings, client, mock_db_conn):
    """Test generating rankings when recent rankings already exist."""
    # Setup mocks
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    
    # Mock existing rankings
    mock_cursor.fetchone.return_value = (10,)  # 10 recent rankings
    
    # Test data
    test_data = {"user_id": "user123"}
    
    # Make request
    response = client.post('/v1/recommendations/rankings/generate', 
                          json=test_data,
                          content_type='application/json')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "Using existing rankings" in data["message"]
    assert data["count"] == 10
    
    # Verify ranking generator was NOT called
    mock_generate_rankings.assert_not_called()


@patch('routes.recommendations.get_db_connection')
def test_get_real_posts(mock_get_db, client, mock_db_conn):
    """Test retrieving real Mastodon posts."""
    # Setup mock
    mock_conn, mock_cursor = mock_db_conn
    mock_get_db.return_value = mock_conn
    
    # Create sample mastodon post data
    mastodon_post1 = json.dumps({
        "id": "post123",
        "content": "<p>Real Mastodon post 1</p>",
        "account": {"username": "author1"},
        "favourites_count": 15
    })
    mastodon_post2 = json.dumps({
        "id": "post456",
        "content": "<p>Real Mastodon post 2</p>",
        "account": {"username": "author2"},
        "favourites_count": 8
    })
    
    # Mock database results
    mock_cursor.fetchall.return_value = [
        ("post123", mastodon_post1),
        ("post456", mastodon_post2)
    ]
    
    # Make request
    response = client.get('/v1/recommendations/real-posts')
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["posts"]) == 2
    assert data["posts"][0]["id"] == "post123"
    assert data["posts"][0]["is_real_mastodon_post"] is True
    assert data["posts"][0]["is_synthetic"] is False
    assert data["posts"][1]["id"] == "post456"
    
    # Verify DB query
    mock_cursor.execute.assert_called_with(
        "SELECT post_id, mastodon_post FROM post_metadata WHERE mastodon_post IS NOT NULL ORDER BY created_at DESC LIMIT %s",
        (20,)
    )