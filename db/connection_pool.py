"""
Enhanced database connection pool for the Corgi Recommender Service.

This module provides robust PostgreSQL connection pooling with:
- Connection health monitoring
- Automatic recovery from failed connections
- Connection lifecycle management
- Resource cleanup and monitoring
"""

import logging
import time
import threading
import queue
import psycopg2
from psycopg2 import pool
from psycopg2.extensions import connection as pg_connection
from typing import Optional, Dict, Any, List, Callable
from contextlib import contextmanager

# Set up logging
logger = logging.getLogger(__name__)

class ConnectionHealth:
    """Track connection health and status information."""
    
    def __init__(self, conn_id: str):
        self.conn_id = conn_id
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.last_checked_at = time.time()
        self.total_uses = 0
        self.errors = 0
        self.is_healthy = True
        self.last_error = None
    
    def mark_used(self):
        """Mark the connection as being used."""
        self.last_used_at = time.time()
        self.total_uses += 1
    
    def mark_checked(self, is_healthy: bool, error: Optional[Exception] = None):
        """Mark the connection as checked with health status."""
        self.last_checked_at = time.time()
        self.is_healthy = is_healthy
        if not is_healthy:
            self.errors += 1
            self.last_error = error
    
    def get_age(self) -> float:
        """Get the age of the connection in seconds."""
        return time.time() - self.created_at
    
    def get_idle_time(self) -> float:
        """Get the time since the connection was last used in seconds."""
        return time.time() - self.last_used_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health information to dictionary."""
        return {
            "conn_id": self.conn_id,
            "age_seconds": self.get_age(),
            "last_used_seconds_ago": self.get_idle_time(),
            "total_uses": self.total_uses,
            "errors": self.errors,
            "is_healthy": self.is_healthy,
            "last_error": str(self.last_error) if self.last_error else None
        }

class EnhancedConnectionPool:
    """
    Enhanced PostgreSQL connection pool with health checks and automatic recovery.
    
    Features:
    - Connection health monitoring
    - Automatic recovery from failed connections
    - Stale connection detection and renewal
    - Pool statistics and diagnostics
    """
    
    def __init__(
        self,
        db_config: Dict[str, Any],
        min_connections: int = 1,
        max_connections: int = 10,
        connection_timeout: float = 5.0,
        max_age: int = 3600,  # 1 hour max age
        health_check_interval: int = 300,  # 5 minutes
        name: str = "corgi-db-pool"
    ):
        """
        Initialize the enhanced connection pool.
        
        Args:
            db_config: Database connection parameters
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            connection_timeout: Connection timeout in seconds
            max_age: Maximum age of connections in seconds
            health_check_interval: Interval between health checks in seconds
            name: Name of the connection pool
        """
        self.db_config = db_config
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.max_age = max_age
        self.health_check_interval = health_check_interval
        self.name = name
        
        # Pool statistics
        self.created_connections = 0
        self.failed_connections = 0
        self.reused_connections = 0
        self.connection_errors = 0
        
        # Initialize PostgreSQL threaded connection pool
        self._init_pool()
        
        # Connection health tracking by connection ID
        self.connection_health: Dict[str, ConnectionHealth] = {}
        
        # Lock for thread-safe operations
        self._lock = threading.RLock()
        
        # Start health check thread if interval > 0
        if self.health_check_interval > 0:
            self._start_health_check_thread()
        
        logger.info(f"Enhanced connection pool '{self.name}' initialized with {min_connections}-{max_connections} connections")
    
    def _init_pool(self):
        """Initialize the underlying PostgreSQL connection pool."""
        try:
            self.pool = pool.ThreadedConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections,
                **self.db_config
            )
            logger.info(f"Pool '{self.name}' initialized with {self.min_connections}-{self.max_connections} connections")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            self.pool = None
            raise
    
    def _start_health_check_thread(self):
        """Start background thread for periodic health checks."""
        self.health_check_stop_event = threading.Event()
        self.health_check_thread = threading.Thread(
            target=self._health_check_worker,
            name=f"{self.name}-health-checker",
            daemon=True
        )
        self.health_check_thread.start()
        logger.info(f"Health check thread started for pool '{self.name}' (interval: {self.health_check_interval}s)")
    
    def _health_check_worker(self):
        """Background worker for periodic health checks of idle connections."""
        while not self.health_check_stop_event.is_set():
            try:
                # Sleep first to allow initial connections to be established
                self.health_check_stop_event.wait(self.health_check_interval)
                if self.health_check_stop_event.is_set():
                    break
                
                self._perform_health_check()
            except Exception as e:
                logger.error(f"Error in health check worker: {e}")
        
        logger.info(f"Health check thread for pool '{self.name}' stopped")
    
    def _perform_health_check(self):
        """Perform health check on idle connections."""
        with self._lock:
            # Create copy of health data to iterate safely
            connections_to_check = list(self.connection_health.items())
        
        checked_count = 0
        renewed_count = 0
        
        for conn_id, health in connections_to_check:
            # Skip recently used connections
            if health.get_idle_time() < self.health_check_interval / 2:
                continue
            
            # Check if connection is too old
            if health.get_age() > self.max_age:
                logger.info(f"Connection {conn_id} exceeded max age ({self.max_age}s), marking for renewal")
                with self._lock:
                    if conn_id in self.connection_health:
                        health.mark_checked(False, Exception("Connection exceeded maximum age"))
                renewed_count += 1
                continue
            
            # Try to get the connection for health check
            conn = None
            try:
                conn = self.get_connection(for_health_check=True, specific_conn_id=conn_id)
                if not conn:
                    continue  # Connection wasn't available for health check
                
                # Run simple query to check health
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                
                if result and result[0] == 1:
                    # Connection is healthy
                    with self._lock:
                        if conn_id in self.connection_health:
                            health.mark_checked(True)
                    checked_count += 1
                else:
                    # Query didn't return expected result
                    with self._lock:
                        if conn_id in self.connection_health:
                            health.mark_checked(False, Exception("Health check query returned unexpected result"))
                    renewed_count += 1
            except Exception as e:
                # Connection is unhealthy
                logger.warning(f"Health check failed for connection {conn_id}: {e}")
                with self._lock:
                    if conn_id in self.connection_health:
                        health.mark_checked(False, e)
                renewed_count += 1
            finally:
                if conn:
                    try:
                        self.return_connection(conn)
                    except Exception as e:
                        logger.error(f"Error returning connection after health check: {e}")
        
        if checked_count > 0 or renewed_count > 0:
            logger.info(f"Health check completed: {checked_count} healthy, {renewed_count} renewed")
    
    def _get_connection_id(self, conn: pg_connection) -> str:
        """Get a unique identifier for a connection."""
        return str(id(conn))
    
    def get_connection(self, for_health_check: bool = False, specific_conn_id: Optional[str] = None) -> Optional[pg_connection]:
        """
        Get a connection from the pool.
        
        Args:
            for_health_check: Whether this connection is for a health check
            specific_conn_id: Request a specific connection by ID (for health checks)
            
        Returns:
            A PostgreSQL connection or None if unavailable
        """
        if self.pool is None:
            try:
                self._init_pool()
            except Exception as e:
                logger.error(f"Cannot get connection - pool initialization failed: {e}")
                self.connection_errors += 1
                return None
        
        try:
            conn = self.pool.getconn(key=specific_conn_id)
            conn_id = self._get_connection_id(conn)
            
            # Track connection health
            with self._lock:
                if conn_id not in self.connection_health:
                    self.connection_health[conn_id] = ConnectionHealth(conn_id)
                    self.created_connections += 1
                else:
                    self.reused_connections += 1
                
                # Mark as used
                self.connection_health[conn_id].mark_used()
            
            return conn
        except pool.PoolError as e:
            logger.warning(f"Connection pool error: {e}")
            self.connection_errors += 1
            return None
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            self.connection_errors += 1
            return None
    
    def return_connection(self, conn: pg_connection, close: bool = False):
        """
        Return a connection to the pool.
        
        Args:
            conn: The connection to return
            close: Whether to close this connection instead of returning to pool
        """
        if self.pool is None or conn is None:
            return
        
        conn_id = self._get_connection_id(conn)
        
        try:
            if close:
                # Close this specific connection
                self.pool.putconn(conn, close=True)
                with self._lock:
                    if conn_id in self.connection_health:
                        del self.connection_health[conn_id]
                logger.debug(f"Connection {conn_id} closed and removed from pool")
            else:
                # Return to pool
                self.pool.putconn(conn)
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            self.connection_errors += 1
    
    def test_connection(self) -> bool:
        """
        Test getting a connection from the pool.
        
        Returns:
            Boolean indicating success
        """
        conn = None
        try:
            conn = self.get_connection()
            if conn is None:
                return False
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
            return result is not None and result[0] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
        finally:
            if conn:
                self.return_connection(conn)
    
    def recreate_pool(self):
        """Close all connections and recreate the pool."""
        try:
            old_pool = self.pool
            self.pool = None
            
            # Close all existing connections
            if old_pool:
                old_pool.closeall()
            
            # Clear health tracking
            with self._lock:
                self.connection_health.clear()
            
            # Recreate the pool
            self._init_pool()
            logger.info(f"Connection pool '{self.name}' recreated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to recreate connection pool: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics.
        
        Returns:
            Dictionary with pool statistics
        """
        with self._lock:
            active_connections = len(self.connection_health)
            active_conn_details = [
                health.to_dict() for health in self.connection_health.values()
            ]
        
        return {
            "name": self.name,
            "min_connections": self.min_connections,
            "max_connections": self.max_connections,
            "active_connections": active_connections,
            "created_connections": self.created_connections,
            "reused_connections": self.reused_connections,
            "connection_errors": self.connection_errors,
            "connections": active_conn_details
        }
    
    def close(self):
        """Close the connection pool and cleanup resources."""
        if self.health_check_interval > 0:
            # Stop health check thread
            self.health_check_stop_event.set()
            if self.health_check_thread.is_alive():
                self.health_check_thread.join(timeout=1.0)
        
        # Close all connections
        if self.pool:
            try:
                self.pool.closeall()
                logger.info(f"Connection pool '{self.name}' closed")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")
        
        # Clear health tracking
        with self._lock:
            self.connection_health.clear()

# Global pool instance
_pool_instance: Optional[EnhancedConnectionPool] = None

def initialize_connection_pool(
    db_config: Dict[str, Any],
    min_connections: int = 1,
    max_connections: int = 10
) -> bool:
    """
    Initialize the global connection pool.
    
    Args:
        db_config: Database connection parameters
        min_connections: Minimum number of connections to maintain
        max_connections: Maximum number of connections allowed
        
    Returns:
        Boolean indicating success
    """
    global _pool_instance
    
    try:
        if _pool_instance is not None:
            _pool_instance.close()
        
        _pool_instance = EnhancedConnectionPool(
            db_config=db_config,
            min_connections=min_connections,
            max_connections=max_connections
        )
        
        # Test the connection
        if not _pool_instance.test_connection():
            logger.error("Failed to establish initial test connection")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error initializing connection pool: {e}")
        return False

def get_connection_pool() -> Optional[EnhancedConnectionPool]:
    """
    Get the global connection pool instance.
    
    Returns:
        The connection pool or None if not initialized
    """
    return _pool_instance

@contextmanager
def get_pg_connection():
    """
    Context manager for getting a PostgreSQL connection.
    
    Yields:
        A PostgreSQL connection
        
    Raises:
        Exception if connection fails
    """
    global _pool_instance
    
    if _pool_instance is None:
        raise Exception("Connection pool not initialized")
    
    conn = None
    try:
        conn = _pool_instance.get_connection()
        if conn is None:
            raise Exception("Failed to get connection from pool")
        
        yield conn
    finally:
        if conn:
            _pool_instance.return_connection(conn)

def close_connection_pool():
    """Close the global connection pool."""
    global _pool_instance
    
    if _pool_instance is not None:
        _pool_instance.close()
        _pool_instance = None
        logger.info("Global connection pool closed")

def get_pool_stats() -> Dict[str, Any]:
    """
    Get statistics about the connection pool.
    
    Returns:
        Dictionary with pool statistics or error message
    """
    global _pool_instance
    
    if _pool_instance is None:
        return {"error": "Connection pool not initialized"}
    
    return _pool_instance.get_stats()