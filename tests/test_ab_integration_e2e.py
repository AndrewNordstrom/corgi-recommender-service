import os
import json
from unittest.mock import patch, MagicMock

import pytest

# Ensure in-memory DB
os.environ["USE_IN_MEMORY_DB"] = "true"

from app import create_app
from db.connection import init_db, in_memory_conn, get_cursor

app = create_app()
client = app.test_client()


@pytest.fixture(scope="module", autouse=True)
def setup_ab_tables():
    """Set up a RUNNING experiment with two variants in the in-memory DB."""
    init_db()
    cur = in_memory_conn.cursor()

    # Create minimal experiment & variants
    cur.execute("DROP TABLE IF EXISTS ab_experiments")
    cur.execute("DROP TABLE IF EXISTS ab_experiment_variants")
    cur.execute("DROP TABLE IF EXISTS ab_user_assignments")
    in_memory_conn.commit()

    cur.execute(
        """
        CREATE TABLE ab_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    cur.execute(
        """
        CREATE TABLE ab_experiment_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id INTEGER,
            name TEXT,
            traffic_allocation REAL,
            is_control BOOLEAN
        )
    """
    )
    cur.execute(
        """
        CREATE TABLE ab_user_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            experiment_id INTEGER,
            variant_id INTEGER,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, experiment_id)
        )
    """
    )
    # Insert RUNNING experiment and two variants
    cur.execute("INSERT INTO ab_experiments (id, name, status) VALUES (1, 'E2E Test', 'RUNNING')")
    cur.execute("INSERT INTO ab_experiment_variants (id, experiment_id, name, traffic_allocation, is_control) VALUES (1, 1, 'VariantA', 0.5, 1)")
    cur.execute("INSERT INTO ab_experiment_variants (id, experiment_id, name, traffic_allocation, is_control) VALUES (2, 1, 'VariantB', 0.5, 0)")
    in_memory_conn.commit()


@patch("routes.recommendations.generate_rankings_for_user")
def test_ab_assignment_and_ranking(mock_generate):
    """User should be assigned to variant and ranking called with model_id."""
    # Mock ranking function to return dummy list
    mock_generate.return_value = [{"id": "p1", "ranking_score": 1.0}]

    user_id = "e2e_user"
    resp = client.post(
        "/api/v1/recommendations/rankings/generate",
        json={"user_id": user_id, "force_refresh": True},
    )
    assert resp.status_code in (200, 201)
    mock_generate.assert_called_once()

    # Capture model_id argument (kwargs)
    _, kwargs = mock_generate.call_args
    variant_model_id = kwargs.get("model_id")
    assert variant_model_id in (1, 2)

    # Verify assignment stored in DB
    cur = in_memory_conn.cursor()
    cur.execute(
        "SELECT variant_id FROM ab_user_assignments WHERE user_id=? AND experiment_id=1",
        (user_id,),
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] == variant_model_id 