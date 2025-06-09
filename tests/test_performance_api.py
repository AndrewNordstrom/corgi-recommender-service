#!/usr/bin/env python3
"""
Core Performance API Tests

Tests core functionality of the Performance Benchmark API:
- Benchmark data retrieval endpoints
- Performance trend analysis
- Regression reporting
- Monitoring integration

TODO #27f: Performance benchmark reporting and visualization API
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from flask import Flask
from routes.performance import performance_bp


@pytest.fixture
def app():
    """Create test Flask application with performance blueprint."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.register_blueprint(performance_bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_benchmark_data():
    """Sample benchmark data for testing."""
    return [
        {
            'id': 1,
            'name': 'Test Benchmark 1',
            'description': 'Test description',
            'benchmark_type': 'baseline',
            'test_timestamp': datetime.utcnow(),
            'concurrent_users': 10,
            'test_duration_seconds': 60,
            'total_requests': 1000,
            'p50_latency': 50.0,
            'p95_latency': 95.0,
            'p99_latency': 150.0,
            'max_latency': 200.0,
            'requests_per_second': 16.67,
            'error_rate': 0.01,
            'avg_cpu_usage': 25.0,
            'peak_cpu_usage': 40.0,
            'avg_memory_mb': 256.0,
            'peak_memory_mb': 320.0,
            'avg_db_query_time': 10.0,
            'db_connections_used': 5,
            'quality_score_degradation': None,
            'algorithm_config': {},
            'environment_info': {}
        },
        {
            'id': 2,
            'name': 'Test Benchmark 2',
            'description': 'Test description 2',
            'benchmark_type': 'variant',
            'test_timestamp': datetime.utcnow() - timedelta(days=1),
            'concurrent_users': 20,
            'test_duration_seconds': 120,
            'total_requests': 2000,
            'p50_latency': 60.0,
            'p95_latency': 110.0,
            'p99_latency': 180.0,
            'max_latency': 250.0,
            'requests_per_second': 16.67,
            'error_rate': 0.02,
            'avg_cpu_usage': 35.0,
            'peak_cpu_usage': 55.0,
            'avg_memory_mb': 384.0,
            'peak_memory_mb': 480.0,
            'avg_db_query_time': 15.0,
            'db_connections_used': 8,
            'quality_score_degradation': 5.0,
            'algorithm_config': {},
            'environment_info': {}
        }
    ]


@pytest.fixture
def sample_regression_data():
    """Sample regression report data for testing."""
    return [
        {
            'report_id': 'reg-123',
            'test_name': 'Test Regression 1',
            'detection_timestamp': datetime.utcnow(),
            'overall_severity': 'medium',
            'baseline_benchmark_id': 1,
            'current_benchmark_id': 2,
            'detected_regressions': [],
            'performance_score': 75.0,
            'recommendations': ['Optimize database queries', 'Scale resources'],
            'alert_sent': True
        }
    ]


class TestGetBenchmarks:
    """Test benchmark retrieval endpoint."""
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_get_benchmarks_success(self, mock_cursor, mock_connection, client, sample_benchmark_data):
        """Test successful benchmark retrieval."""
        # Mock database interaction
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Mock count query
        mock_cur.fetchone.return_value = (2,)
        
        # Mock benchmark data query
        mock_cur.description = [
            ('id',), ('name',), ('description',), ('benchmark_type',), ('test_timestamp',),
            ('concurrent_users',), ('test_duration_seconds',), ('total_requests',),
            ('p50_latency',), ('p95_latency',), ('p99_latency',), ('max_latency',),
            ('requests_per_second',), ('error_rate',), ('avg_cpu_usage',), ('peak_cpu_usage',),
            ('avg_memory_mb',), ('peak_memory_mb',), ('avg_db_query_time',), ('db_connections_used',),
            ('quality_score_degradation',), ('algorithm_config',), ('environment_info',)
        ]
        
        mock_cur.fetchall.return_value = [tuple(benchmark.values()) for benchmark in sample_benchmark_data]
        
        response = client.get('/api/performance/benchmarks')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'benchmarks' in data['data']
        assert 'pagination' in data['data']
        assert len(data['data']['benchmarks']) == 2
        
    def test_get_benchmarks_with_filters(self, client):
        """Test benchmark retrieval with query filters."""
        with patch('routes.performance.get_db_connection'), \
             patch('routes.performance.get_cursor') as mock_cursor:
            
            mock_cur = MagicMock()
            mock_cursor.return_value.__enter__.return_value = mock_cur
            mock_cur.fetchone.return_value = (1,)
            mock_cur.description = [('id',), ('name',)]
            mock_cur.fetchall.return_value = [(1, 'Test')]
            
            response = client.get('/api/performance/benchmarks?benchmark_type=baseline&limit=10')
            
            assert response.status_code == 200
            # Verify that the filter parameters were processed
            assert mock_cur.execute.called
            
    def test_get_benchmarks_database_error(self, client):
        """Test benchmark retrieval with database error."""
        with patch('routes.performance.get_db_connection', side_effect=Exception("DB Error")):
            response = client.get('/api/performance/benchmarks')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data


class TestGetBenchmarkDetails:
    """Test individual benchmark details endpoint."""
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_get_benchmark_details_success(self, mock_cursor, mock_connection, client, sample_benchmark_data):
        """Test successful benchmark detail retrieval."""
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = tuple(sample_benchmark_data[0].values())
        mock_cur.description = [(key,) for key in sample_benchmark_data[0].keys()]
        
        response = client.get('/api/performance/benchmarks/1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['benchmark']['id'] == 1
    
    def test_get_benchmark_details_not_found(self, client):
        """Test benchmark details for non-existent benchmark."""
        with patch('routes.performance.get_db_connection'), \
             patch('routes.performance.get_cursor') as mock_cursor:
            
            mock_cur = MagicMock()
            mock_cursor.return_value.__enter__.return_value = mock_cur
            mock_cur.fetchone.return_value = None
            
            response = client.get('/api/performance/benchmarks/999')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False


class TestCompareBenchmarks:
    """Test benchmark comparison endpoint."""
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_compare_benchmarks_success(self, mock_cursor, mock_connection, client, sample_benchmark_data):
        """Test successful benchmark comparison."""
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Return both benchmarks for comparison
        mock_cur.fetchall.return_value = [tuple(benchmark.values()) for benchmark in sample_benchmark_data]
        mock_cur.description = [(key,) for key in sample_benchmark_data[0].keys()]
        
        response = client.get('/api/performance/benchmarks/compare?baseline=1&comparison=2')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'comparison' in data['data']
        assert 'baseline' in data['data']['comparison']
        assert 'comparison_benchmark' in data['data']['comparison']


class TestGetPerformanceTrends:
    """Test performance trends endpoint."""
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_get_trends_success(self, mock_cursor, mock_connection, client):
        """Test successful trend data retrieval."""
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Mock trend data
        trend_data = [
            (datetime.utcnow() - timedelta(days=1), 95.0, 16.5, 0.01),
            (datetime.utcnow(), 100.0, 16.0, 0.015)
        ]
        mock_cur.fetchall.return_value = trend_data
        mock_cur.description = [('timestamp',), ('p95_latency',), ('requests_per_second',), ('error_rate',)]
        
        response = client.get('/api/performance/trends')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'trends' in data['data']


class TestGetRegressionReports:
    """Test regression reports endpoint."""
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_get_regressions_success(self, mock_cursor, mock_connection, client, sample_regression_data):
        """Test successful regression report retrieval."""
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [tuple(regression.values()) for regression in sample_regression_data]
        mock_cur.description = [(key,) for key in sample_regression_data[0].keys()]
        
        response = client.get('/api/performance/regressions')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'regressions' in data['data']


class TestAnalyzeBenchmarkRegression:
    """Test regression analysis endpoint."""
    
    @patch('routes.performance.detect_regressions_for_benchmark')
    def test_analyze_regression_success(self, mock_detect, client):
        """Test successful regression analysis."""
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {
            'report_id': 'test-123',
            'overall_severity': 'medium',
            'performance_score': 75.0,
            'detected_regressions': [],
            'recommendations': ['Optimize queries']
        }
        mock_detect.return_value = mock_report
        
        response = client.post('/api/performance/benchmarks/1/analyze-regression', 
                             json={'baseline_id': 2})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'regression_report' in data['data']


class TestMonitoringEndpoints:
    """Test monitoring integration endpoints."""
    
    @patch('routes.performance.get_global_monitor')
    def test_get_monitoring_status_success(self, mock_get_monitor, client):
        """Test monitoring status retrieval."""
        mock_monitor = MagicMock()
        mock_monitor.get_performance_summary.return_value = {
            'latency_ms': {'mean': 50.0, 'p95': 95.0},
            'throughput_requests': {'mean': 100.0, 'total': 1000},
            'error_rate_percent': {'mean': 1.0}
        }
        mock_get_monitor.return_value = mock_monitor
        
        response = client.get('/api/performance/monitoring/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'monitoring' in data['data']
        
    @patch('routes.performance.get_global_monitor')
    def test_create_monitoring_snapshot_success(self, mock_get_monitor, client):
        """Test creating monitoring snapshot."""
        mock_monitor = MagicMock()
        mock_monitor.save_performance_snapshot.return_value = 123
        mock_get_monitor.return_value = mock_monitor
        
        response = client.post('/api/performance/monitoring/snapshot')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['snapshot_id'] == 123


class TestStatsAndExport:
    """Test statistics and export endpoints."""
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_get_stats_summary_success(self, mock_cursor, mock_connection, client):
        """Test performance statistics summary."""
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Mock stats data
        stats_data = (2, 102.5, 16.67, 0.015)  # count, avg_p95, avg_rps, avg_error_rate
        mock_cur.fetchone.return_value = stats_data
        
        response = client.get('/api/performance/stats')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'stats' in data['data']
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_export_benchmarks_csv(self, mock_cursor, mock_connection, client, sample_benchmark_data):
        """Test CSV export functionality."""
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [tuple(benchmark.values()) for benchmark in sample_benchmark_data]
        mock_cur.description = [(key,) for key in sample_benchmark_data[0].keys()]
        
        response = client.get('/api/performance/export/csv')
        
        assert response.status_code == 200
        assert response.content_type == 'text/csv; charset=utf-8'


class TestErrorHandling:
    """Test API error handling."""
    
    def test_500_error_handler(self, client):
        """Test 500 error handling."""
        with patch('routes.performance.get_db_connection', side_effect=Exception("Critical Error")):
            response = client.get('/api/performance/benchmarks')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 