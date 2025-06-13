import os
import importlib
import math
import datetime
from datetime import timedelta

import pytest

# Step 1:   Prepare the in-memory database
os.environ["USE_IN_MEMORY_DB"] = "true"

import db.connection as dbc
importlib.reload(dbc)

# Make sure the tables exist
from db.connection import init_db, get_db_connection, get_cursor

init_db()

# Patch `core.ranking_algorithm` references so they use the *reloaded* db module
import core.ranking_algorithm as ra
ra.USE_IN_MEMORY_DB = True
ra.get_db_connection = dbc.get_db_connection
ra.get_cursor = dbc.get_cursor

from utils.privacy import generate_user_alias
from core.ranking_algorithm import generate_rankings_for_user


@pytest.fixture(scope="module")
def setup_test_data():
    """Populate the in-memory DB with deterministic test fixtures."""
    alias = generate_user_alias("userA")

    now = datetime.datetime.now()

    # Posts the user has *already* interacted with (will be excluded from candidates)
    seen_posts = [
        ("seen_x1", "Seen X1", "authorX", now - timedelta(hours=2)),
        ("seen_x2", "Seen X2", "authorX", now - timedelta(hours=3)),
        ("seen_x3", "Seen X3", "authorX", now - timedelta(hours=4)),
    ]

    # Fresh candidate posts that should be ranked
    candidate_posts = [
        ("cand_x1", "Candidate X1", "authorX", now - timedelta(minutes=1)),
        ("cand_y1", "Candidate Y1", "authorY", now - timedelta(minutes=1)),
    ]

    posts = seen_posts + candidate_posts

    with get_db_connection() as conn:
        cur = conn.cursor()

        for post_id, content, author_id, created_at in posts:
            cur.execute(
                """
                INSERT OR REPLACE INTO posts (post_id, content, author_id, created_at, metadata)
                VALUES (?, ?, ?, ?, '{}')
                """,
                (post_id, content, author_id, created_at.isoformat()),
            )

        # Interactions: user likes the *seen* AuthorX posts
        for post_id, *_ in seen_posts:
            cur.execute(
                """
                INSERT INTO interactions (user_id, post_id, interaction_type, created_at)
                VALUES (?, ?, 'favorite', ?)
                """,
                (alias, post_id, now.isoformat()),
            )

        conn.commit()

    return alias  # return for potential debugging


def test_generate_rankings_for_user_order(setup_test_data):
    """Run the full ranking pipeline and ensure AuthorX posts outrank AuthorY."""
    ranked_posts = generate_rankings_for_user("userA")

    # Ensure at least the two candidate posts are present
    assert len(ranked_posts) >= 2

    # Top post should be from AuthorX; AuthorY post should rank below it
    assert ranked_posts[0]["author_id"] == "authorX"

    # Find the first occurrence of the AuthorY candidate and ensure its index is greater than AuthorX
    index_author_y = next(i for i, p in enumerate(ranked_posts) if p["author_id"] == "authorY")
    assert index_author_y > 0

    scores = [p["ranking_score"] for p in ranked_posts]
    assert scores == sorted(scores, reverse=True) 