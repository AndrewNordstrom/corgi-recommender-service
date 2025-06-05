"""
Integration tests for Redis caching in the recommendation engine.
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from utils.recommendation_engine import get_ranked_recommendations
from utils.cache import (
    cache_key, invalidate_user_recommendations,
    get_cached_recommendations, cache_recommendations, REDIS_ENABLED as CACHE_REDIS_ENABLED
)


# Test data
SAMPLE_USER_ID = "returning_user_for_cache_test"
MOCK_COLD_START_POSTS = [
    {
        "id": "cold_start_1",
        "content": "Cold start post 1",
        "created_at": "2025-05-17T10:00:00Z",
        "account": {
            "id": "cs_user_1",
            "username": "cold_start_user",
            "display_name": "Cold Start User"
        }
    }
]

# MOCK_RANKED_POSTS should represent the output of generate_rankings_for_user
# which includes a top-level 'ranking_score' and 'recommendation_reason'.
MOCK_RANKED_POSTS = [
    {
        "id": "ranked_1",
        "content": "Ranked post 1",
        "created_at": "2025-05-17T11:00:00Z",
        "author_id": "ranked_author_1",
        "author_name": "Ranked Author",
        "ranking_score": 0.9,
        "recommendation_reason": "Highly relevant to your interests"
    }
]


@pytest.mark.parametrize("is_new_user_param", [True, False])
@patch('utils.recommendation_engine.get_db_connection')
@patch('utils.recommendation_engine.generate_rankings_for_user')
@patch('utils.recommendation_engine.load_cold_start_posts')
@patch('utils.recommendation_engine.is_new_user')
def test_cache_for_recommendations(
    mock_is_new_user_patch, 
    mock_load_cold_start_patch, 
    mock_generate_rankings_patch, 
    mock_get_db_connection_patch, 
    is_new_user_param, mocked_redis_client
):
    """Test caching behavior for recommendations."""
    mock_is_new_user_patch.return_value = is_new_user_param
    mock_load_cold_start_patch.return_value = MOCK_COLD_START_POSTS
    mock_generate_rankings_patch.return_value = MOCK_RANKED_POSTS

    mock_db_conn = MagicMock()
    mock_db_cursor = MagicMock()
    mock_db_cursor.fetchone.return_value = (None,)
    mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor
    mock_get_db_connection_patch.return_value.__enter__.return_value = mock_db_conn

    mocked_redis_client.delete(cache_key("recommendations", SAMPLE_USER_ID))

    first_result = get_ranked_recommendations(SAMPLE_USER_ID)

    if is_new_user_param:
        assert first_result == MOCK_COLD_START_POSTS
        mock_load_cold_start_patch.assert_called_once()
        mock_generate_rankings_patch.assert_not_called()
        assert mocked_redis_client.get(cache_key("recommendations", SAMPLE_USER_ID)) is None
    else:
        expected_posts = []
        for raw_post_data in MOCK_RANKED_POSTS:
            author_id = raw_post_data.get('author_id', 'unknown')
            author_name_display = raw_post_data.get('author_name', 'Unknown User')
            # SUT uses author_name directly in URL, no slugification there based on recent SUT check

            formatted_post = {
                "id": raw_post_data["id"],
                "content": raw_post_data["content"],
                "created_at": raw_post_data["created_at"],
                "account": {
                    "id": author_id,
                    "username": author_name_display, 
                    "display_name": author_name_display,
                    "url": f"https://example.com/@{author_name_display}" # Use original author_name
                },
                "media_attachments": [], "mentions": [], "tags": [], "emojis": [],
                "favourites_count": 0, "reblogs_count": 0, "replies_count": 0,
                "is_real_mastodon_post": False, "is_synthetic": True, "injected": True,
                "injection_metadata": {
                    "source": "recommendation_engine",
                    "strategy": "personalized",
                    "score": raw_post_data["ranking_score"],
                    "explanation": raw_post_data["recommendation_reason"]
                }
            }
            expected_posts.append(formatted_post)

        assert first_result == expected_posts
        mock_generate_rankings_patch.assert_called_once()
        cached_data = mocked_redis_client.get(cache_key("recommendations", SAMPLE_USER_ID))
        assert cached_data is not None
        assert json.loads(cached_data) == expected_posts

        mock_generate_rankings_patch.reset_mock()
        mock_load_cold_start_patch.reset_mock()
        mock_get_db_connection_patch.reset_mock()
        mock_get_db_connection_patch.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = (None,)

        second_result = get_ranked_recommendations(SAMPLE_USER_ID)
        assert second_result == expected_posts
        mock_generate_rankings_patch.assert_not_called()
        mock_get_db_connection_patch.assert_not_called()

        mock_generate_rankings_patch.reset_mock()
        mock_get_db_connection_patch.reset_mock()
        mock_get_db_connection_patch.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = (None,)

        bypass_result = get_ranked_recommendations(SAMPLE_USER_ID, use_cache=False)
        assert bypass_result == expected_posts
        mock_generate_rankings_patch.assert_called_once()
        mock_get_db_connection_patch.assert_called()


@patch('utils.recommendation_engine.get_db_connection')
@patch('utils.recommendation_engine.generate_rankings_for_user')
@patch('utils.recommendation_engine.is_new_user')
def test_cache_invalidation(
    mock_is_new_user_patch, 
    mock_generate_rankings_patch, 
    mock_get_db_connection_patch, 
    mocked_redis_client
):
    """Test cache invalidation for recommendations."""
    mock_is_new_user_patch.return_value = False
    mock_generate_rankings_patch.return_value = MOCK_RANKED_POSTS

    mock_db_conn = MagicMock()
    mock_db_cursor = MagicMock()
    mock_db_cursor.fetchone.return_value = (None,)
    mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor
    mock_get_db_connection_patch.return_value.__enter__.return_value = mock_db_conn

    mocked_redis_client.delete(cache_key("recommendations", SAMPLE_USER_ID))
    first_result = get_ranked_recommendations(SAMPLE_USER_ID)

    expected_posts = []
    for raw_post_data in MOCK_RANKED_POSTS:
        author_id = raw_post_data.get('author_id', 'unknown')
        author_name_display = raw_post_data.get('author_name', 'Unknown User')
        formatted_post = {
            "id": raw_post_data["id"],
            "content": raw_post_data["content"],
            "created_at": raw_post_data["created_at"],
            "account": { 
                "id": author_id,
                "username": author_name_display, 
                "display_name": author_name_display,
                "url": f"https://example.com/@{author_name_display}" # Use original author_name
            },
            "media_attachments": [], "mentions": [], "tags": [], "emojis": [],
            "favourites_count": 0, "reblogs_count": 0, "replies_count": 0,
            "is_real_mastodon_post": False, "is_synthetic": True, "injected": True,
            "injection_metadata": {
                "source": "recommendation_engine",
                "strategy": "personalized",
                "score": raw_post_data["ranking_score"],
                "explanation": raw_post_data["recommendation_reason"]
            }
        }
        expected_posts.append(formatted_post)

    assert first_result == expected_posts
    assert mocked_redis_client.get(cache_key("recommendations", SAMPLE_USER_ID)) is not None

    result = invalidate_user_recommendations(SAMPLE_USER_ID)
    assert result is True
    assert mocked_redis_client.get(cache_key("recommendations", SAMPLE_USER_ID)) is None

    mock_generate_rankings_patch.reset_mock()
    mock_get_db_connection_patch.reset_mock()
    mock_get_db_connection_patch.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = (None,)

    next_result = get_ranked_recommendations(SAMPLE_USER_ID)
    assert next_result == expected_posts
    mock_generate_rankings_patch.assert_called_once()
    assert mocked_redis_client.get(cache_key("recommendations", SAMPLE_USER_ID)) is not None


# No decorators for this test, use mocker fixture
def test_recommendations_without_redis(mocker, mocked_redis_client):
    """Test recommendation generation works when Redis is disabled."""
    # Use mocker to patch objects within the test function
    mock_get_db_connection = mocker.patch('utils.recommendation_engine.get_db_connection')
    mock_generate_rankings = mocker.patch('utils.recommendation_engine.generate_rankings_for_user')
    mock_is_new_user = mocker.patch('utils.recommendation_engine.is_new_user')
    # Patch REDIS_ENABLED in the module where it's looked up by the SUT (get_ranked_recommendations)
    mocker.patch('utils.recommendation_engine.REDIS_ENABLED', False)

    # Mock the SUT's internal call to cache_recommendations to verify it's not called
    mock_sut_cache_recs_func = mocker.patch('utils.recommendation_engine.cache_recommendations')

    mock_is_new_user.return_value = False
    mock_generate_rankings.return_value = MOCK_RANKED_POSTS

    mock_db_conn = MagicMock()
    mock_db_cursor = MagicMock()
    mock_db_cursor.fetchone.return_value = (None,)
    mock_db_conn.cursor.return_value.__enter__.return_value = mock_db_cursor
    mock_get_db_connection.return_value.__enter__.return_value = mock_db_conn

    expected_posts = []
    for raw_post_data in MOCK_RANKED_POSTS:
        author_id = raw_post_data.get('author_id', 'unknown')
        author_name_display = raw_post_data.get('author_name', 'Unknown User')
        formatted_post = {
            "id": raw_post_data["id"],
            "content": raw_post_data["content"],
            "created_at": raw_post_data["created_at"],
            "account": { 
                "id": author_id,
                "username": author_name_display, 
                "display_name": author_name_display,
                "url": f"https://example.com/@{author_name_display}" # Use original author_name
            },
            "media_attachments": [], "mentions": [], "tags": [], "emojis": [],
            "favourites_count": 0, "reblogs_count": 0, "replies_count": 0,
            "is_real_mastodon_post": False, "is_synthetic": True, "injected": True,
            "injection_metadata": {
                "source": "recommendation_engine",
                "strategy": "personalized",
                "score": raw_post_data["ranking_score"],
                "explanation": raw_post_data["recommendation_reason"]
            }
        }
        expected_posts.append(formatted_post)

    first_result = get_ranked_recommendations(SAMPLE_USER_ID)
    assert first_result == expected_posts
    mock_generate_rankings.assert_called_once()

    # Assert that the SUT did not attempt to cache recommendations
    mock_sut_cache_recs_func.assert_not_called()
    
    # Because cache_recommendations was not called, the mock_redis_client (via mocked_redis_client.set) should not have been touched.
    assert mocked_redis_client.get(cache_key("recommendations", SAMPLE_USER_ID)) is None 

    mock_generate_rankings.reset_mock()
    mock_get_db_connection.reset_mock()
    mock_get_db_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = (None,)

    second_result = get_ranked_recommendations(SAMPLE_USER_ID)
    assert second_result == expected_posts
    mock_generate_rankings.assert_called_once()