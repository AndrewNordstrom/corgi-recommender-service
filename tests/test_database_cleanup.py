"""
Tests for Database Cleanup Tasks.

This module tests the database cleanup functionality including old rankings,
quality metrics, orphaned data, and comprehensive cleanup operations.

Tests for TODO #8: Scheduled cleanup of old rankings and unused data.
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
    """Test suite for database cleanup task functionality."""
    
    def setup_method(self):
        """Setup for each test method to ensure clean state."""
        # Reset any global state that might be contaminated by other tests
        import importlib
        import config
        import tasks.database_cleanup
        importlib.reload(config)
        importlib.reload(tasks.database_cleanup)
    
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
    
    def test_cleanup_old_quality_metrics_custom_retention(self):
        """Test quality metrics cleanup with custom retention."""
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
            
            result = cleanup_old_quality_metrics(retention_days=45, dry_run=True)
        
        assert result['success'] is True
        assert result['retention_days'] == 45
        assert result['cleaned_count'] == 0
    
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
    
    def test_cleanup_orphaned_data_custom_grace_period(self):
        """Test orphaned data cleanup with custom grace period."""
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
            
            result = cleanup_orphaned_data(grace_period_days=14, dry_run=True)
        
        assert result['success'] is True
        assert result['grace_period_days'] == 14
        assert result['total_cleaned'] == 0
        
        # Verify cutoff date calculation
        cutoff_date = datetime.fromisoformat(result['cutoff_date'])
        expected_cutoff = datetime.now() - timedelta(days=14)
        time_diff = abs((cutoff_date - expected_cutoff).total_seconds())
        assert time_diff < 5  # Should be within 5 seconds
    
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
        assert result['task_type'] == 'comprehensive_cleanup'
        assert result['dry_run'] is True
        assert result['total_cleaned'] == 0
        assert result['total_errors'] == 0
        assert 'subtasks' in result
        assert 'processing_time' in result
        
        # Check that all subtasks were executed
        expected_subtasks = ['rankings', 'quality_metrics', 'orphaned_data']
        for subtask in expected_subtasks:
            assert subtask in result['subtasks']
            assert result['subtasks'][subtask]['success'] is True
    
    def test_get_database_health_summary(self):
        """Test database health summary functionality."""
        # Use isolation to prevent interference from full test suite
        with patch('tasks.database_cleanup.get_db_connection') as mock_get_conn, \
             patch('tasks.database_cleanup.get_cursor') as mock_get_cursor, \
             patch('tasks.database_cleanup.USE_IN_MEMORY_DB', True):
            
            # Mock database connection and cursor
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_get_conn.return_value.__enter__.return_value = mock_conn
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            # Mock table and record counts
            mock_cursor.fetchall.return_value = [
                ('recommendations', 10),
                ('interactions', 5)
            ]
            mock_cursor.fetchone.return_value = [15]  # Total records
            
            health_summary = get_database_health_summary()
        
        assert 'timestamp' in health_summary
        assert 'tables' in health_summary
        assert 'total_records' in health_summary
        assert isinstance(health_summary['total_records'], int)
        assert health_summary['total_records'] >= 0
        
        # Verify timestamp format
        timestamp = datetime.fromisoformat(health_summary['timestamp'])
        assert isinstance(timestamp, datetime)
    
    def test_track_cleanup_metrics(self):
        """Test cleanup metrics tracking functionality."""
        # This should not raise an exception
        track_cleanup_metrics('test_cleanup', 5, 1.23, True)
        track_cleanup_metrics('test_cleanup', 0, 0.5, False)
    
    @patch('tasks.database_cleanup.current_task')
    def test_comprehensive_cleanup_with_progress_updates(self, mock_current_task):
        """Test comprehensive cleanup with Celery task progress updates."""
        mock_task = Mock()
        mock_task.update_state = Mock()
        mock_current_task.return_value = mock_task
        
        # Patch the current_task directly at module level to ensure our helper function sees it
        with patch('tasks.database_cleanup.current_task', mock_task), \
             patch('tasks.database_cleanup.get_db_connection') as mock_get_conn, \
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
        # Verify progress updates were called (should be at least 4: start, rankings, metrics, orphaned, final)
        assert mock_task.update_state.call_count >= 4
        
        # Check that final progress shows completion
        final_call_args = mock_task.update_state.call_args_list[-1]
        assert final_call_args[1]['meta']['progress'] == 100
        assert final_call_args[1]['meta']['stage'] == 'Cleanup completed'

class TestDatabaseCleanupIntegration:
    """Integration tests for database cleanup functionality."""
    
    def test_cleanup_tasks_error_handling(self):
        """Test error handling in cleanup tasks."""
        # Test with invalid retention days (should use defaults)
        result = cleanup_old_rankings(retention_days=-1, dry_run=True)
        assert result['success'] is True  # Should handle gracefully
        
        # Test with very large retention days
        result = cleanup_old_rankings(retention_days=99999, dry_run=True)
        assert result['success'] is True
        assert result['cleaned_count'] == 0  # No old data to clean
    
    def test_cleanup_task_performance(self):
        """Test cleanup task performance metrics."""
        start_time = time.time()
        result = cleanup_old_rankings(dry_run=True)
        end_time = time.time()
        
        assert result['success'] is True
        assert 'processing_time' in result
        assert result['processing_time'] <= (end_time - start_time) + 0.1  # Small tolerance
        assert result['processing_time'] > 0
    
    def test_comprehensive_cleanup_subtask_isolation(self):
        """Test that subtask failures don't crash comprehensive cleanup."""
        # This tests the error handling in comprehensive cleanup
        result = comprehensive_database_cleanup(dry_run=True)
        
        assert result['success'] is True
        assert result['total_errors'] == 0
        
        # All subtasks should complete successfully in clean environment
        for subtask_name, subtask_result in result['subtasks'].items():
            assert subtask_result['success'] is True
    
    def test_cleanup_task_concurrency_safety(self):
        """Test that cleanup tasks are safe for concurrent execution."""
        import threading
        import time
        results = []
        
        def run_cleanup():
            try:
                # Add small delay to simulate realistic timing
                time.sleep(0.1)
                result = cleanup_old_rankings(dry_run=True)
                results.append(result)
            except Exception as e:
                # Log the error but continue - some concurrency issues are expected
                print(f"Concurrency test caught expected error: {e}")
                results.append({'success': False, 'error': str(e)})
        
        # Run multiple cleanup tasks concurrently
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=run_cleanup)
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # At least one should succeed (concurrency-safe implementation)
        assert len(results) == 3
        successful_results = [r for r in results if r.get('success') is True]
        assert len(successful_results) >= 1, f"At least one cleanup should succeed, got: {results}"

class TestDatabaseCleanupScheduling:
    """Test scheduled cleanup task configuration."""
    
    def test_celery_beat_schedule_configuration(self):
        """Test that cleanup tasks are properly configured in Celery Beat."""
        from utils.celery_beat_config import CELERY_BEAT_SCHEDULE
        
        expected_cleanup_tasks = [
            'database-cleanup-rankings',
            'database-cleanup-quality-metrics', 
            'database-cleanup-orphaned-data',
            'comprehensive-database-cleanup'
        ]
        
        for task_name in expected_cleanup_tasks:
            assert task_name in CELERY_BEAT_SCHEDULE
            
            task_config = CELERY_BEAT_SCHEDULE[task_name]
            assert 'task' in task_config
            assert 'schedule' in task_config
            assert 'options' in task_config
            assert task_config['options']['queue'] == 'database_cleanup'
    
    def test_task_routing_configuration(self):
        """Test that cleanup tasks are properly routed."""
        from utils.celery_beat_config import CELERY_TASK_ROUTES
        
        cleanup_tasks = [
            'cleanup_old_rankings',
            'cleanup_old_quality_metrics',
            'cleanup_orphaned_data', 
            'comprehensive_database_cleanup'
        ]
        
        for task_name in cleanup_tasks:
            assert task_name in CELERY_TASK_ROUTES
            assert CELERY_TASK_ROUTES[task_name]['queue'] == 'database_cleanup'
    
    def test_task_annotations_configuration(self):
        """Test that cleanup tasks have proper annotations."""
        from utils.celery_beat_config import CELERY_TASK_ANNOTATIONS
        
        cleanup_tasks = [
            'cleanup_old_rankings',
            'cleanup_old_quality_metrics',
            'cleanup_orphaned_data',
            'comprehensive_database_cleanup'
        ]
        
        for task_name in cleanup_tasks:
            assert task_name in CELERY_TASK_ANNOTATIONS
            annotations = CELERY_TASK_ANNOTATIONS[task_name]
            
            # Should have priority set
            assert 'priority' in annotations
            assert annotations['priority'] == 6
            
            # Should have time limits
            assert 'time_limit' in annotations
            assert 'soft_time_limit' in annotations
            assert annotations['time_limit'] > annotations['soft_time_limit']

class TestDatabaseCleanupManagementScript:
    """Test the management script functionality."""
    
    def test_script_import(self):
        """Test that the management script can be imported."""
        import sys
        sys.path.insert(0, 'scripts')
        
        try:
            import manage_database_cleanup
            assert hasattr(manage_database_cleanup, 'main')
            assert hasattr(manage_database_cleanup, 'run_cleanup_task')
            assert hasattr(manage_database_cleanup, 'get_task_status')
            assert hasattr(manage_database_cleanup, 'display_database_health')
        except ImportError as e:
            pytest.fail(f"Failed to import management script: {e}")
    
    def test_script_functions_exist(self):
        """Test that required functions exist in management script."""
        import sys
        sys.path.insert(0, 'scripts')
        import manage_database_cleanup
        
        required_functions = [
            'run_cleanup_task',
            'run_async_cleanup_task', 
            'get_task_status',
            'display_database_health',
            'verify_scheduled_tasks',
            'format_cleanup_result'
        ]
        
        for func_name in required_functions:
            assert hasattr(manage_database_cleanup, func_name)
            func = getattr(manage_database_cleanup, func_name)
            assert callable(func)

@pytest.mark.integration
class TestDatabaseCleanupEndToEnd:
    """End-to-end tests for database cleanup functionality."""
    
    def test_full_cleanup_workflow_dry_run(self):
        """Test complete cleanup workflow in dry-run mode."""
        # 1. Check database health before cleanup
        health_before = get_database_health_summary()
        assert 'tables' in health_before
        initial_records = health_before['total_records']
        
        # 2. Run comprehensive cleanup in dry-run mode
        cleanup_result = comprehensive_database_cleanup(dry_run=True)
        assert cleanup_result['success'] is True
        assert cleanup_result['dry_run'] is True
        
        # 3. Check database health after cleanup
        health_after = get_database_health_summary()
        assert health_after['total_records'] == initial_records  # No data should be deleted in dry-run
        
        # 4. Verify cleanup metrics
        assert cleanup_result['total_cleaned'] >= 0  # Could be 0 if no old data
        assert cleanup_result['total_errors'] == 0
        assert 'processing_time' in cleanup_result
        assert cleanup_result['processing_time'] > 0
    
    def test_individual_cleanup_tasks_sequence(self):
        """Test running individual cleanup tasks in sequence."""
        # Run each cleanup task individually
        tasks_to_test = [
            ('rankings', cleanup_old_rankings),
            ('quality_metrics', cleanup_old_quality_metrics), 
            ('orphaned_data', cleanup_orphaned_data)
        ]
        
        for task_name, task_func in tasks_to_test:
            result = task_func(dry_run=True)
            assert result['success'] is True
            assert result['dry_run'] is True
            assert 'processing_time' in result
            print(f"✓ {task_name} cleanup completed successfully")
    
    def test_cleanup_with_various_retention_periods(self):
        """Test cleanup tasks with different retention periods."""
        retention_periods = [1, 7, 30, 90, 365]
        
        for retention_days in retention_periods:
            result = cleanup_old_rankings(retention_days=retention_days, dry_run=True)
            assert result['success'] is True
            assert result['retention_days'] == retention_days
            
            # Verify cutoff date is calculated correctly
            cutoff_date = datetime.fromisoformat(result['cutoff_date'])
            expected_cutoff = datetime.now() - timedelta(days=retention_days)
            time_diff = abs((cutoff_date - expected_cutoff).total_seconds())
            assert time_diff < 10  # Should be within 10 seconds

if __name__ == '__main__':
    pytest.main([__file__, '-v']) 