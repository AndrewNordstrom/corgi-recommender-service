"""
Tests for the enhanced database connection pool.
"""

import pytest
import threading
import time
import os
from unittest.mock import patch, MagicMock
import psycopg2
from psycopg2.extensions import connection as pg_connection
import queue

from db.connection_pool import (
    EnhancedConnectionPool, 
    ConnectionHealth,
    initialize_connection_pool,
    get_connection_pool,
    get_pg_connection,
    close_connection_pool,
    get_pool_stats
)

# Skip PostgreSQL-specific tests if SQLite is used
SKIP_PG_TESTS = os.getenv("USE_IN_MEMORY_DB", "false").lower() == "true"

# Test ConnectionHealth
def test_connection_health():
    """Test the ConnectionHealth class."""
    conn_id = "test-conn-123"
    health = ConnectionHealth(conn_id)
    
    # Test initialization
    assert health.conn_id == conn_id
    assert health.total_uses == 0
    assert health.errors == 0
    assert health.is_healthy == True
    
    # Test mark_used
    health.mark_used()
    assert health.total_uses == 1
    
    # Test mark_checked
    error = Exception("Test error")
    health.mark_checked(False, error)
    assert health.is_healthy == False
    assert health.errors == 1
    assert health.last_error == error
    
    # Test age and idle time
    assert health.get_age() > 0
    assert health.get_idle_time() > 0
    
    # Test to_dict
    data = health.to_dict()
    assert data["conn_id"] == conn_id
    assert data["total_uses"] == 1
    assert data["errors"] == 1
    assert data["is_healthy"] == False
    assert "last_error" in data

@pytest.mark.skipif(SKIP_PG_TESTS, reason="PostgreSQL tests skipped in SQLite mode")
class TestEnhancedConnectionPool:
    """Tests for the EnhancedConnectionPool class."""
    
    @pytest.fixture
    def mock_pg_pool(self):
        """Create a mock for psycopg2 pool."""
        with patch('psycopg2.pool.ThreadedConnectionPool') as mock_pool:
            # Mock connection
            mock_conn = MagicMock(spec=pg_connection)
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (1,)
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            
            # Configure pool methods
            mock_pool.return_value.getconn.return_value = mock_conn
            mock_pool.return_value.putconn.return_value = None
            mock_pool.return_value.closeall.return_value = None
            
            yield mock_pool
    
    @pytest.fixture
    def pool(self, mock_pg_pool):
        """Create an EnhancedConnectionPool instance with mocked internals."""
        db_config = {
            'host': 'localhost',
            'port': '5432',
            'user': 'test',
            'password': 'test',
            'dbname': 'test_db'
        }
        
        pool = EnhancedConnectionPool(
            db_config=db_config,
            min_connections=1,
            max_connections=5,
            health_check_interval=0  # Disable health check thread for testing
        )
        
        yield pool
        
        # Cleanup
        pool.close()
    
    def test_connection_pool_initialization(self, mock_pg_pool, pool):
        """Test connection pool initialization."""
        assert pool is not None
        assert pool.min_connections == 1
        assert pool.max_connections == 5
        assert mock_pg_pool.called
    
    def test_get_connection(self, pool):
        """Test getting a connection from the pool."""
        conn = pool.get_connection()
        assert conn is not None
        
        # Check that connection health is tracked
        conn_id = pool._get_connection_id(conn)
        assert conn_id in pool.connection_health
        assert pool.connection_health[conn_id].total_uses == 1
        
        # Return connection to pool
        pool.return_connection(conn)
    
    def test_connection_reuse(self, pool):
        """Test connection reuse."""
        conn1 = pool.get_connection()
        conn_id = pool._get_connection_id(conn1)
        pool.return_connection(conn1)
        
        # Get another connection (should be the same one)
        conn2 = pool.get_connection()
        assert pool._get_connection_id(conn2) == conn_id
        assert pool.connection_health[conn_id].total_uses == 2
        
        pool.return_connection(conn2)
    
    def test_connection_close(self, pool, mock_pg_pool):
        """Test closing a connection."""
        conn = pool.get_connection()
        conn_id = pool._get_connection_id(conn)
        
        # Close connection instead of returning to pool
        pool.return_connection(conn, close=True)
        
        # Connection health should be removed
        assert conn_id not in pool.connection_health
        
        # Check that putconn was called with close=True
        mock_pg_pool.return_value.putconn.assert_called_with(conn, close=True)
    
    def test_test_connection(self, pool):
        """Test the connection test functionality."""
        assert pool.test_connection() == True
    
    def test_get_stats(self, pool):
        """Test getting pool statistics."""
        # Get a connection to generate some stats
        conn = pool.get_connection()
        pool.return_connection(conn)
        
        stats = pool.get_stats()
        assert stats["name"] == "corgi-db-pool"
        assert stats["min_connections"] == 1
        assert stats["max_connections"] == 5
        assert stats["created_connections"] >= 1
        assert stats["reused_connections"] >= 0
        assert len(stats["connections"]) >= 1
    
    def test_recreate_pool(self, pool, mock_pg_pool):
        """Test recreating the connection pool."""
        # Get a connection first
        conn = pool.get_connection()
        pool.return_connection(conn)
        
        # Recreate the pool
        result = pool.recreate_pool()
        assert result == True
        
        # Verify that closeall was called
        mock_pg_pool.return_value.closeall.assert_called_once()
        
        # Verify that pool was reinitialized
        assert mock_pg_pool.call_count == 2

@pytest.mark.skipif(SKIP_PG_TESTS, reason="PostgreSQL tests skipped in SQLite mode")
class TestGlobalPoolFunctions:
    """Tests for global connection pool utility functions."""
    
    @pytest.fixture
    def mock_enhanced_pool(self):
        """Create a mock for EnhancedConnectionPool."""
        with patch('db.connection_pool.EnhancedConnectionPool') as mock_pool_class:
            pool_instance = MagicMock()
            pool_instance.test_connection.return_value = True
            pool_instance.get_stats.return_value = {"name": "test-pool"}
            mock_pool_class.return_value = pool_instance
            
            yield mock_pool_class
    
    def test_initialize_connection_pool(self, mock_enhanced_pool):
        """Test initializing the global connection pool."""
        db_config = {
            'host': 'localhost',
            'port': '5432',
            'user': 'test',
            'password': 'test',
            'dbname': 'test_db'
        }
        
        # Reset global state
        close_connection_pool()
        
        # Initialize pool
        result = initialize_connection_pool(db_config)
        assert result == True
        mock_enhanced_pool.assert_called_once()
        
        # Check that global pool was set
        assert get_connection_pool() is not None
    
    def test_get_pg_connection(self, mock_enhanced_pool):
        """Test the get_pg_connection context manager."""
        db_config = {
            'host': 'localhost',
            'port': '5432',
            'user': 'test',
            'password': 'test',
            'dbname': 'test_db'
        }
        
        # Initialize pool first
        initialize_connection_pool(db_config)
        
        # Mock the get_connection method on the pool instance
        mock_conn = MagicMock()
        mock_enhanced_pool.return_value.get_connection.return_value = mock_conn
        
        # Use the context manager
        with get_pg_connection() as conn:
            assert conn is mock_conn
        
        # Verify connection was returned to pool
        mock_enhanced_pool.return_value.return_connection.assert_called_once_with(mock_conn)
    
    def test_get_pool_stats(self, mock_enhanced_pool):
        """Test getting pool statistics."""
        db_config = {
            'host': 'localhost',
            'port': '5432',
            'user': 'test',
            'password': 'test',
            'dbname': 'test_db'
        }
        
        # Initialize pool first
        initialize_connection_pool(db_config)
        
        stats = get_pool_stats()
        assert stats == {"name": "test-pool"}
        mock_enhanced_pool.return_value.get_stats.assert_called_once()
    
    def test_close_connection_pool(self, mock_enhanced_pool):
        """Test closing the global connection pool."""
        db_config = {
            'host': 'localhost',
            'port': '5432',
            'user': 'test',
            'password': 'test',
            'dbname': 'test_db'
        }
        
        # Initialize pool first
        initialize_connection_pool(db_config)
        
        # Close pool
        close_connection_pool()
        
        # Verify close was called
        mock_enhanced_pool.return_value.close.assert_called_once()
        
        # Verify global pool is None
        assert get_connection_pool() is None