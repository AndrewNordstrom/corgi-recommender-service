"""
Core Database Cleanup Tests

Essential tests for database cleanup functionality covering:
- Basic cleanup operations (rankings, quality metrics, orphaned data)
- Dry run modes and basic configuration
- Core error handling
- Basic health summary functionality
"""

import json
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Test the cleanup tasks
from tasks.database_cleanup import (
    cleanup_old_rankings,
    cleanup_old_quality_metrics, 
    cleanup_orphaned_data,
    comprehensive_database_cleanup,
    get_database_health_summary,
    track_cleanup_metrics
)

class TestDatabaseCleanupTasks:
    """Test suite for core database cleanup task functionality."""
    
    def setup_method(self):
        """Setup for each test method to ensure clean state."""
        # Reset any global state that might be contaminated by other tests
        # Note: Removed importlib.reload() calls that were causing ERRORs in full test suite
        # The test isolation via mocking should be sufficient for these tests
        pass
    
    def test_cleanup_old_rankings_no_data(self):
        """Test ranking cleanup when no old data exists."""
        # Use isolation to prevent interference from full test suite
        with patch('tasks.database_cleanup.get_db_connection') as mock_get_conn, \
             patch('tasks.database_cleanup.get_cursor') as mock_get_cursor, \
             patch('tasks.database_cleanup.USE_IN_MEMORY_DB', True), \
             patch('tasks.database_cleanup.track_cleanup_metrics') as mock_track:
            
            # Mock database connection and cursor
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            # Mock query results to simulate no old data
            mock_cursor.fetchone.return_value = [0]  # COUNT(*) returns 0
            
            result = cleanup_old_rankings(dry_run=True)
            
            assert result['success'] is True
            assert result['task_type'] == 'ranking_cleanup'
            assert result['dry_run'] is True
            assert result['cleaned_count'] == 0
            assert 'processing_time' in result
            assert result['cutoff_date'] is not None
    
    def test_cleanup_old_rankings_with_retention_days(self):
        """Test ranking cleanup with custom retention period."""
        # Use isolation to prevent interference from full test suite
        with patch('tasks.database_cleanup.get_db_connection') as mock_get_conn, \
             patch('tasks.database_cleanup.get_cursor') as mock_get_cursor, \
             patch('tasks.database_cleanup.USE_IN_MEMORY_DB', True), \
             patch('tasks.database_cleanup.track_cleanup_metrics') as mock_track:
            
            # Mock database connection and cursor
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            # Mock query results to simulate no old data
            mock_cursor.fetchone.return_value = [0]  # COUNT(*) returns 0
            
            result = cleanup_old_rankings(retention_days=60, dry_run=True)
        
        assert result['success'] is True
        assert result['retention_days'] == 60
        assert result['cleaned_count'] == 0
        
        # Verify cutoff date calculation
        cutoff_date = datetime.fromisoformat(result['cutoff_date'])
        expected_cutoff = datetime.now() - timedelta(days=60)
        time_diff = abs((cutoff_date - expected_cutoff).total_seconds())
        assert time_diff < 5  # Should be within 5 seconds
    
    def test_cleanup_old_quality_metrics_no_data(self):
        """Test quality metrics cleanup when no old data exists."""
        # Use isolation to prevent interference from full test suite
        with patch('tasks.database_cleanup.get_db_connection') as mock_get_conn, \
             patch('tasks.database_cleanup.get_cursor') as mock_get_cursor, \
             patch('tasks.database_cleanup.USE_IN_MEMORY_DB', True), \
             patch('tasks.database_cleanup.track_cleanup_metrics') as mock_track:
            
            # Mock database connection and cursor
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            # Mock query results to simulate no old data
            mock_cursor.fetchone.return_value = [0]  # COUNT(*) returns 0
            
            result = cleanup_old_quality_metrics(dry_run=True)
        
        assert result['success'] is True
        assert result['task_type'] == 'quality_metrics_cleanup'
        assert result['dry_run'] is True
        assert result['cleaned_count'] == 0
        assert 'processing_time' in result
    
    def test_cleanup_orphaned_data_no_data(self):
        """Test orphaned data cleanup when no orphaned data exists."""
        # Use isolation to prevent interference from full test suite
        with patch('tasks.database_cleanup.get_db_connection') as mock_get_conn, \
             patch('tasks.database_cleanup.get_cursor') as mock_get_cursor, \
             patch('tasks.database_cleanup.USE_IN_MEMORY_DB', True), \
             patch('tasks.database_cleanup.track_cleanup_metrics') as mock_track:
            
            # Mock database connection and cursor
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            # Mock query results to simulate no old data
            mock_cursor.fetchone.return_value = [0]  # COUNT(*) returns 0
            mock_cursor.fetchall.return_value = []  # No orphaned data
            
            result = cleanup_orphaned_data(dry_run=True)
        
        assert result['success'] is True
        assert result['task_type'] == 'orphaned_data_cleanup'
        assert result['dry_run'] is True
        assert result['total_cleaned'] == 0
        assert result['orphaned_interactions'] == 0
        assert result['orphaned_rankings'] == 0
        assert 'processing_time' in result
    
    def test_comprehensive_database_cleanup_dry_run(self):
        """Test comprehensive cleanup in dry-run mode."""
        # Use isolation to prevent interference from full test suite
        with patch('tasks.database_cleanup.get_db_connection') as mock_get_conn, \
             patch('tasks.database_cleanup.get_cursor') as mock_get_cursor, \
             patch('tasks.database_cleanup.USE_IN_MEMORY_DB', True), \
             patch('tasks.database_cleanup.track_cleanup_metrics') as mock_track:
            
            # Mock database connection and cursor
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            # Mock query results to simulate no old data
            mock_cursor.fetchone.return_value = [0]  # COUNT(*) returns 0
            mock_cursor.fetchall.return_value = []  # No orphaned data
            
            result = comprehensive_database_cleanup(dry_run=True)
        
        assert result['success'] is True
        assert result['dry_run'] is True
        assert 'total_processing_time' in result
        assert 'subtasks' in result
        assert len(result['subtasks']) >= 3  # rankings, quality_metrics, orphaned_data
        
        # Check that all subtasks succeeded in dry-run mode
        for subtask_name, subtask in result['subtasks'].items():
            assert subtask['success'] is True
            assert subtask['dry_run'] is True
    
    def test_get_database_health_summary(self):
        """Test database health summary functionality."""
        with patch('tasks.database_cleanup.get_db_connection') as mock_get_conn, \
             patch('tasks.database_cleanup.get_cursor') as mock_get_cursor, \
             patch('tasks.database_cleanup.USE_IN_MEMORY_DB', True):
            
            # Mock database connection and cursor
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            # Mock query results for health check
            # First set of queries: table counts for 'users', 'posts', 'interactions', 'recommendations', 'privacy_settings'
            # Then: ranking stats queries (total and old)
            mock_cursor.fetchone.side_effect = [
                [100],   # users table count
                [200],   # posts table count  
                [300],   # interactions table count
                [1000],  # recommendations table count (total rankings)
                [50],    # privacy_settings table count
                [1000],  # Total rankings (duplicate for stats section)
                [100],   # Old rankings
            ]
            
            result = get_database_health_summary()
        
        assert result['success'] is True
        assert 'ranking_stats' in result
        assert 'quality_metrics_stats' in result
        assert 'orphaned_data_stats' in result
        assert 'processing_time' in result
        
        # Check specific stats
        assert result['ranking_stats']['total'] == 1000
        assert result['ranking_stats']['old'] == 100
        # Quality metrics stats are mocked as 0 since table may not exist in test
        assert result['quality_metrics_stats']['total'] == 0
        assert result['quality_metrics_stats']['old'] == 0

    def test_cleanup_tasks_error_handling(self):
        """Test error handling in cleanup tasks."""
        with patch('tasks.database_cleanup.get_db_connection') as mock_get_conn:
            # Mock database connection to raise an exception
            mock_get_conn.side_effect = Exception("Database connection failed")
            
            result = cleanup_old_rankings(dry_run=True)
            
            assert result['success'] is False
            assert 'error' in result
            assert 'Database connection failed' in result['error']
            
    def test_track_cleanup_metrics(self):
        """Test cleanup metrics tracking functionality."""
        test_result = {
            'task_type': 'ranking_cleanup',
            'success': True,
            'cleaned_count': 100,
            'processing_time': 1.5
        }
        
        # track_cleanup_metrics should not raise exceptions
        try:
            track_cleanup_metrics(test_result)
            assert True  # If no exception raised, test passes
        except Exception as e:
            pytest.fail(f"track_cleanup_metrics raised an unexpected exception: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 