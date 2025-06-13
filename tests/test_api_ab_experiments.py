import os
import json
import importlib

import pytest

# Ensure in-memory SQLite DB for tests
os.environ["USE_IN_MEMORY_DB"] = "true"

from app import create_app  # Import after env var so DB init picks SQLite

app = create_app()
client = app.test_client()

API_URL = "/api/v1/analytics/experiments"
ADMIN_HEADERS = {"X-API-Key": "admin-key", "Content-Type": "application/json"}


@pytest.fixture(autouse=True)
def _init_db():
    """Re-initialize in-memory database before each test to ensure isolation."""
    from db.connection import init_db, in_memory_conn
    init_db()
    # Clean up AB tables
    cur = in_memory_conn.cursor()
    cur.execute("DROP TABLE IF EXISTS ab_experiments")
    cur.execute("DROP TABLE IF EXISTS ab_experiment_variants")
    in_memory_conn.commit()


def test_create_experiment_success():
    payload = {
        "name": "Recency vs Engagement",
        "description": "Test different ranking strategies",
        "variants": [
            {"model_variant_id": 1, "traffic_allocation": 0.6},
            {"model_variant_id": 2, "traffic_allocation": 0.4},
        ],
    }

    resp = client.post(API_URL, data=json.dumps(payload), headers=ADMIN_HEADERS)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == payload["name"]
    assert len(data["variants"]) == 2


def test_create_experiment_invalid_allocation_sum():
    payload = {
        "name": "Invalid Sum Test",
        "description": "Allocation sum != 1",
        "variants": [
            {"model_variant_id": 1, "traffic_allocation": 0.7},
            {"model_variant_id": 2, "traffic_allocation": 0.2},
        ],
    }

    resp = client.post(API_URL, data=json.dumps(payload), headers=ADMIN_HEADERS)
    assert resp.status_code == 400
    assert "Sum of traffic_allocation" in resp.get_json().get("error", "")


def test_create_experiment_unauthorized():
    payload = {
        "name": "No Auth",
        "description": "Should fail",
        "variants": [
            {"model_variant_id": 1, "traffic_allocation": 1.0}
        ],
    }

    resp = client.post(API_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})
    assert resp.status_code == 403  # Forbidden due to missing admin role


# ------------------------------------------------------------------
# Management API tests
# ------------------------------------------------------------------


def _create_experiment(name: str):
    payload = {
        "name": name,
        "description": "desc",
        "variants": [
            {"model_variant_id": 1, "traffic_allocation": 1.0},
        ],
    }
    return client.post(API_URL, data=json.dumps(payload), headers=ADMIN_HEADERS).get_json()


def test_list_experiments():
    _create_experiment("List Test")
    resp = client.get(API_URL, headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["experiments"]) >= 1


def test_start_stop_experiment_success_and_conflict():
    exp1 = _create_experiment("Exp1")
    exp2 = _create_experiment("Exp2")

    # Start first experiment
    start_resp = client.post(f"{API_URL}/{exp1['id']}/start", headers=ADMIN_HEADERS)
    assert start_resp.status_code == 200
    assert start_resp.get_json()["status"] == "RUNNING"

    # Attempt to start second -> should conflict
    conflict = client.post(f"{API_URL}/{exp2['id']}/start", headers=ADMIN_HEADERS)
    assert conflict.status_code == 409

    # Stop first experiment
    stop_resp = client.post(f"{API_URL}/{exp1['id']}/stop", headers=ADMIN_HEADERS)
    assert stop_resp.status_code == 200
    assert stop_resp.get_json()["status"] == "COMPLETED" 