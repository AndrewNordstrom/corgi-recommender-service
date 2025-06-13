import datetime
import json
from unittest.mock import patch, MagicMock

from app import create_app


class _Cursor(MagicMock):
    """Simple MagicMock that also acts as a context manager."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


@patch("routes.recommendations.USE_IN_MEMORY_DB", True)
@patch("routes.recommendations.fetch_real_mastodon_data", return_value=None)
@patch("routes.recommendations.get_cursor")
@patch("routes.recommendations.get_db_connection")
def test_recommendations_timeline_endpoint(mock_get_db, mock_get_cursor, _mock_fetch_rt):
    """Call the /api/v1/recommendations/timeline endpoint and validate the schema of the response."""

    # Create a deterministic fake DB row for the SQLite query (5 columns)
    row = (
        "42",  # post_id
        "Hello world",  # content
        "999",  # author_id
        datetime.datetime.now().isoformat(),  # created_at
        json.dumps({"favourites_count": 5, "reblogs_count": 1, "replies_count": 0}),  # metadata (JSON string)
    )

    cursor = _Cursor()
    cursor.fetchall.side_effect = lambda *args, **kwargs: [row]
    cursor.execute.return_value = None

    # get_cursor should ignore the connection and return our cursor
    mock_get_cursor.side_effect = lambda conn: cursor

    # get_db_connection yields a dummy connection usable in a `with` block
    dummy_conn = MagicMock()
    dummy_conn.__enter__.return_value = dummy_conn
    dummy_conn.__exit__.return_value = False
    mock_get_db.return_value = dummy_conn

    # Build Flask test client
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/api/v1/recommendations/timeline?fetch_real_time=false")
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, list)

    # If mock DB returned results, validate structure of the first post
    if data:
        post = data[0]
        assert "account" in post and "avatar" in post["account"]
        assert "favourites_count" in post
        assert "reblogs_count" in post
        assert "replies_count" in post
        assert "media_attachments" in post 