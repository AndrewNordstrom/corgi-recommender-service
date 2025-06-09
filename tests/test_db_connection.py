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
@patch('db.connection.USE_IN_MEMORY_DB', False)  # Test PostgreSQL path
def test_initialize_connection_pool_success(mock_pool_class):
    """Test successful connection pool initialization."""
    # Setup mock pool
    mock_pool = MagicMock()
    mock_pool_class.return_value = mock_pool
    
    # Call the function
    result = initialize_connection_pool()
    
    # Verify success
    assert result is True
    mock_pool_class.assert_called_once()


@patch('db.connection.SimpleConnectionPool')
@patch('db.connection.USE_IN_MEMORY_DB', False)  # Test PostgreSQL path
def test_initialize_connection_pool_failure(mock_pool_class):
    """Test handling of connection pool initialization failure."""
    # Setup mock to raise exception
    mock_pool_class.side_effect = Exception("Connection error")
    
    # Call the function
    result = initialize_connection_pool()
    
    # Verify failure
    assert result is False
    mock_pool_class.assert_called_once()


@patch('db.connection.pool')
@patch('db.connection.initialize_connection_pool')
@patch('db.connection.USE_IN_MEMORY_DB', False)  # Test PostgreSQL path
def test_get_db_connection_retry_success(mock_initialize_pool, mock_pool):
    """Test connection retry when pool initialization is needed."""
    # Setup successful initialization
    mock_initialize_pool.return_value = True
    
    # Create a mock connection
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    
    # Use the connection
    with get_db_connection() as conn:
        assert conn is mock_conn
    
    # Verify connection operations
    mock_pool.getconn.assert_called_once()
    mock_pool.putconn.assert_called_once_with(mock_conn)


@patch('time.sleep')
@patch('db.connection.initialize_connection_pool')
@patch('db.connection.USE_IN_MEMORY_DB', False)  # Test PostgreSQL path
def test_get_db_connection_retry_failure(mock_initialize_pool, mock_sleep):
    """Test connection retry failure after multiple attempts."""
    # Setup initialization to fail
    mock_initialize_pool.return_value = False
    
    # Set pool to None to simulate failed initialization
    db.connection.pool = None
    
    # Try to get a connection - should raise exception
    with pytest.raises(Exception) as exc_info:
        with get_db_connection() as conn:
            pass
    
    # Verify exception was raised with proper message
    assert "Database connection failed" in str(exc_info.value)
    
    # Verify that initialization was attempted (part of error recovery)
    assert mock_initialize_pool.call_count >= 1


@patch('db.schema.create_tables')
@patch('db.schema.create_sqlite_tables')
@patch('db.connection.get_db_connection')
@patch('db.connection.USE_IN_MEMORY_DB', False)  # Test PostgreSQL path
def test_init_db_success(mock_get_conn, mock_create_sqlite, mock_create_tables):
    """Test successful database initialization for PostgreSQL."""
    # Setup mock connection context manager
    mock_conn = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_conn
    mock_context.__exit__.return_value = None
    mock_get_conn.return_value = mock_context
    
    # Call init_db
    init_db()
    
    # Verify calls for PostgreSQL path
    mock_get_conn.assert_called_once()
    mock_create_tables.assert_called_once_with(mock_conn)
    # SQLite function should not be called in PostgreSQL mode
    mock_create_sqlite.assert_not_called()


@patch('db.schema.create_tables')
@patch('db.schema.create_sqlite_tables')
@patch('db.connection.get_db_connection')
@patch('db.connection.USE_IN_MEMORY_DB', False)  # Test PostgreSQL path
def test_init_db_error(mock_get_conn, mock_create_sqlite, mock_create_tables):
    """Test error handling in database initialization."""
    # Setup mock connection context manager
    mock_conn = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_conn
    mock_context.__exit__.return_value = None
    mock_get_conn.return_value = mock_context
    
    # Setup mock to raise exception
    mock_create_tables.side_effect = Exception("Schema error")
    
    # Call init_db - should propagate the exception
    with pytest.raises(Exception) as exc_info:
        init_db()
    
    # Verify error was raised
    assert "Schema error" in str(exc_info.value)