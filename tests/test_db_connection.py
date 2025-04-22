"""
Tests for the database connection module.
"""

import pytest
from unittest.mock import patch, MagicMock, call

import db.connection
from db.connection import initialize_connection_pool, get_db_connection, init_db


@pytest.fixture
def mock_pool():
    """Create a mock connection pool."""
    return MagicMock()


@patch('db.connection.SimpleConnectionPool')
def test_initialize_connection_pool_success(mock_simple_pool):
    """Test successful connection pool initialization."""
    # Setup mock
    mock_simple_pool.return_value = MagicMock()
    
    # Call the function
    result = initialize_connection_pool()
    
    # Verify success
    assert result is True
    mock_simple_pool.assert_called_once()


@patch('db.connection.SimpleConnectionPool')
def test_initialize_connection_pool_failure(mock_simple_pool):
    """Test handling of connection pool initialization failure."""
    # Setup mock to raise exception
    mock_simple_pool.side_effect = Exception("Connection error")
    
    # Call the function
    result = initialize_connection_pool()
    
    # Verify failure
    assert result is False
    mock_simple_pool.assert_called_once()


@patch('db.connection.initialize_connection_pool')
@patch('db.connection.pool', None)  # Start with no pool
def test_get_db_connection_retry_success(mock_initialize_pool):
    """Test connection retry when pool is None."""
    # Setup to succeed on first retry
    mock_initialize_pool.return_value = True
    
    # Create a mock pool and connection
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    
    # Patch the pool to use our mock
    with patch('db.connection.pool', mock_pool):
        # Use the connection
        with get_db_connection() as conn:
            assert conn is mock_conn
    
    # Verify pool operations
    mock_initialize_pool.assert_called_once()
    mock_pool.getconn.assert_called_once()
    mock_pool.putconn.assert_called_once_with(mock_conn)


@patch('time.sleep')
@patch('db.connection.initialize_connection_pool')
@patch('db.connection.pool', None)  # Start with no pool
def test_get_db_connection_retry_failure(mock_initialize_pool, mock_sleep):
    """Test connection retry failure after multiple attempts."""
    # Setup to fail on all retries
    mock_initialize_pool.return_value = False
    
    # Try to get a connection - should raise exception
    with pytest.raises(Exception) as exc_info:
        with get_db_connection() as conn:
            pass
    
    # Verify retries happened
    assert mock_initialize_pool.call_count == 3  # 3 attempts
    assert mock_sleep.call_count == 2  # 2 sleeps between attempts
    assert "Database connection failed" in str(exc_info.value)


@patch('db.connection.create_tables')
@patch('db.connection.get_db_connection')
def test_init_db_success(mock_get_conn, mock_create_tables):
    """Test successful database initialization."""
    # Setup mock
    mock_conn = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    
    # Call init_db
    init_db()
    
    # Verify calls
    mock_get_conn.assert_called_once()
    mock_create_tables.assert_called_once_with(mock_conn)


@patch('db.connection.create_tables')
@patch('db.connection.get_db_connection')
def test_init_db_error(mock_get_conn, mock_create_tables):
    """Test error handling in database initialization."""
    # Setup mock to raise exception
    mock_create_tables.side_effect = Exception("Schema error")
    
    # Call init_db - should propagate the exception
    with pytest.raises(Exception) as exc_info:
        init_db()
    
    # Verify error was raised
    assert "Schema error" in str(exc_info.value)