import math
import datetime
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest

from core.ranking_algorithm import (
    get_author_preference_score,
    get_content_engagement_score,
    get_recency_score,
)

# ---------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------

class _DummyCursor(MagicMock):
    """A very small helper class that can be used in a Python `with` block."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False  # propagate exceptions if any


class _DummyConnection(MagicMock):
    """Connection wrapper that works with `with get_db_connection() as conn:`"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


# ---------------------------------------------------------
# get_author_preference_score
# ---------------------------------------------------------

@patch("core.ranking_algorithm.get_db_connection")
@patch("core.ranking_algorithm.get_cursor")
def test_get_author_preference_score_exact(mock_get_cursor, mock_get_db):
    """Ensure get_author_preference_score follows the documented logistic formula exactly."""

    # --------------------------------------------------
    # Prepare dummy DB plumbing so that the internal SQL
    # query that maps post_id -> author_id returns the
    # mapping we control.
    # --------------------------------------------------
    cursor = _DummyCursor()
    # Each tuple is (post_id, author_id)
    cursor.fetchall.return_value = [
        ("p1", "authorX"),
        ("p2", "authorX"),
        ("p3", "authorX"),
    ]

    # Set up context manager mock for get_cursor
    mock_cursor_context = MagicMock()
    mock_cursor_context.__enter__.return_value = cursor
    mock_cursor_context.__exit__.return_value = None
    mock_get_cursor.return_value = mock_cursor_context
    
    # Set up context manager mock for get_db_connection
    mock_conn_context = MagicMock()
    mock_conn_context.__enter__.return_value = _DummyConnection()
    mock_conn_context.__exit__.return_value = None
    mock_get_db.return_value = mock_conn_context

    # Three positive interactions for authorX, zero negatives
    interactions = [
        {"post_id": "p1", "action_type": "favorite"},
        {"post_id": "p2", "action_type": "reblog"},
        {"post_id": "p3", "action_type": "favorite"},
    ]

    # According to the implementation the logistic formula is:
    # preference_score = 1 / (1 + exp(-5 * (positive_ratio - 0.5)))
    positive_ratio = 3 / 3  # 1.0
    expected_score = 1 / (1 + math.exp(-5 * (positive_ratio - 0.5)))

    score = get_author_preference_score(interactions, "authorX")

    assert math.isclose(score, expected_score, rel_tol=1e-6)


# ---------------------------------------------------------
# get_content_engagement_score
# ---------------------------------------------------------

def test_get_content_engagement_score_exact():
    """Ensure engagement score matches log(total + 1) / 10.0 exactly."""
    post = {"interaction_counts": {"favorites": 9, "reblogs": 3, "replies": 2}}
    total = 9 + 3 + 2  # 14
    expected_score = math.log(total + 1) / 10.0

    score = get_content_engagement_score(post)

    assert math.isclose(score, expected_score, rel_tol=1e-6)


# ---------------------------------------------------------
# get_recency_score
# ---------------------------------------------------------

def test_get_recency_score_exact():
    """Ensure recency score obeys exp(-age_days / decay_factor)."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from config import ALGORITHM_CONFIG

    decay_factor = ALGORITHM_CONFIG["time_decay_days"]
    created_at = datetime.datetime.now() - timedelta(days=2)
    post = {"created_at": created_at}

    age_days = 2
    expected_score = math.exp(-age_days / decay_factor)

    score = get_recency_score(post)

    assert math.isclose(score, expected_score, rel_tol=1e-6)


# Also verify the floor behaviour for very old posts

def test_get_recency_score_floor():
    old_post = {"created_at": datetime.datetime.now() - timedelta(days=365)}
    score = get_recency_score(old_post)
    assert math.isclose(score, 0.2, rel_tol=1e-9) 