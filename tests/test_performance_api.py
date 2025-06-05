#!/usr/bin/env python3
"""
Test suite for Performance Benchmark Reporting and Visualization API - TODO #27f

This test suite covers:
1. Benchmark data retrieval and filtering endpoints
2. Performance trend analysis endpoints
3. Regression report access endpoints
4. Real-time monitoring integration endpoints
5. Comparative analysis tools
6. Export and reporting functionality
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


@pytest.fixture
def sample_stats_data():
    """Sample performance stats data for testing."""
    return {
        'total_benchmarks': 2,
        'benchmark_types': 2,
        'avg_p95_latency': 102.5,
        'avg_requests_per_second': 16.67,
        'avg_error_rate': 0.015,
        'earliest_test': (datetime.utcnow() - timedelta(days=1)).isoformat(),
        'latest_test': datetime.utcnow().isoformat(),
        'benchmark_type_counts': {'baseline': 1, 'variant': 1},
        'regression_severity_counts': {'medium': 1},
        'analysis_period_days': 7
    }


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
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Mock benchmark data
        benchmark = sample_benchmark_data[0]
        mock_cur.fetchone.return_value = tuple(benchmark.values())
        mock_cur.description = [(key,) for key in benchmark.keys()]
        
        response = client.get('/api/performance/benchmarks/1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['id'] == 1
        assert data['data']['name'] == 'Test Benchmark 1'
        
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_get_benchmark_details_not_found(self, mock_cursor, mock_connection, client):
        """Test benchmark detail retrieval when benchmark not found."""
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = None
        
        response = client.get('/api/performance/benchmarks/999')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error'].lower()


class TestCompareBenchmarks:
    """Test benchmark comparison endpoint."""
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_compare_benchmarks_success(self, mock_cursor, mock_connection, client, sample_benchmark_data):
        """Test successful benchmark comparison."""
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Mock benchmark data for comparison
        mock_cur.fetchall.return_value = [tuple(benchmark.values()) for benchmark in sample_benchmark_data]
        mock_cur.description = [(key,) for key in sample_benchmark_data[0].keys()]
        
        response = client.get('/api/performance/benchmarks/2/compare/1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'current_benchmark' in data['data']
        assert 'baseline_benchmark' in data['data']
        assert 'metrics_comparison' in data['data']
        assert 'overall_assessment' in data['data']
        
        # Check that comparison calculations are present
        metrics = data['data']['metrics_comparison']
        assert 'p95_latency' in metrics
        assert 'change_percent' in metrics['p95_latency']
        assert 'is_better' in metrics['p95_latency']


class TestGetPerformanceTrends:
    """Test performance trends endpoint."""
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_get_trends_success(self, mock_cursor, mock_connection, client):
        """Test successful trend retrieval."""
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Mock trend data
        trend_data = [
            (datetime.utcnow().date(), 5, 100.0, 80.0, 120.0, 15.0)
        ]
        mock_cur.fetchall.return_value = trend_data
        
        response = client.get('/api/performance/trends?days=7&granularity=daily')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'trends' in data['data']
        assert 'period' in data['data']
        
    def test_get_trends_with_filters(self, client):
        """Test trend retrieval with filters."""
        with patch('routes.performance.get_db_connection'), \
             patch('routes.performance.get_cursor') as mock_cursor:
            
            mock_cur = MagicMock()
            mock_cursor.return_value.__enter__.return_value = mock_cur
            mock_cur.fetchall.return_value = []
            
            response = client.get('/api/performance/trends?days=30&metric=p95_latency&benchmark_type=baseline')
            
            assert response.status_code == 200
            # Verify filter parameters were processed
            assert mock_cur.execute.called


class TestGetRegressionReports:
    """Test regression reports endpoint."""
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_get_regressions_success(self, mock_cursor, mock_connection, client, sample_regression_data):
        """Test successful regression report retrieval."""
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Mock table existence check
        mock_cur.fetchone.side_effect = [(True,)] + [tuple(regression.values()) for regression in sample_regression_data]
        mock_cur.description = [(key,) for key in sample_regression_data[0].keys()]
        mock_cur.fetchall.return_value = [tuple(regression.values()) for regression in sample_regression_data]
        
        response = client.get('/api/performance/regressions')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'regression_reports' in data['data']
        
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_get_regressions_no_table(self, mock_cursor, mock_connection, client):
        """Test regression retrieval when table doesn't exist."""
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = (False,)  # Table doesn't exist
        
        response = client.get('/api/performance/regressions')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['regression_reports'] == []
        assert 'No regression reports table found' in data['data']['message']


class TestAnalyzeBenchmarkRegression:
    """Test benchmark regression analysis endpoint."""
    
    @patch('routes.performance.detect_regressions_for_benchmark')
    def test_analyze_regression_success(self, mock_detect, client):
        """Test successful regression analysis."""
        # Mock regression detection result
        mock_report = MagicMock()
        mock_report.report_id = 'test-report-123'
        mock_report.test_name = 'Test Analysis'
        mock_report.detection_timestamp = datetime.utcnow()
        mock_report.overall_severity.value = 'medium'
        mock_report.baseline_benchmark_id = 1
        mock_report.current_benchmark_id = 2
        mock_report.performance_score = 75.0
        mock_report.recommendations = ['Test recommendation']
        mock_report.alert_sent = True
        mock_report.detected_regressions = []
        mock_report.statistical_summary = {}
        mock_report.trend_analysis = {}
        
        mock_detect.return_value = mock_report
        
        response = client.post('/api/performance/analyze/2', 
                              json={'baseline_id': 1})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['report_id'] == 'test-report-123'
        assert data['data']['overall_severity'] == 'medium'
        
    @patch('routes.performance.detect_regressions_for_benchmark')
    def test_analyze_regression_error(self, mock_detect, client):
        """Test regression analysis with error."""
        mock_detect.side_effect = Exception("Analysis failed")
        
        response = client.post('/api/performance/analyze/2')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Analysis failed' in data['error']


class TestMonitoringEndpoints:
    """Test real-time monitoring integration endpoints."""
    
    @patch('routes.performance.get_global_monitor')
    def test_get_monitoring_status_success(self, mock_get_monitor, client):
        """Test successful monitoring status retrieval."""
        # Mock monitoring system
        mock_monitor = MagicMock()
        mock_monitor.monitoring_active = True
        mock_monitor.get_performance_summary.return_value = {
            'avg_latency': 100.0,
            'requests_per_second': 50.0
        }
        
        # Mock active alerts
        mock_alert = MagicMock()
        mock_alert.alert_id = 'alert-123'
        mock_alert.timestamp = datetime.utcnow()
        mock_alert.metric_name = 'latency'
        mock_alert.current_value = 150.0
        mock_alert.severity = 'high'
        mock_alert.message = 'High latency detected'
        
        mock_monitor.threshold_monitor.get_active_alerts.return_value = [mock_alert]
        mock_get_monitor.return_value = mock_monitor
        
        response = client.get('/api/performance/monitoring/current')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['monitoring_active'] is True
        assert 'performance_summary' in data['data']
        assert 'active_alerts' in data['data']
        assert len(data['data']['active_alerts']) == 1
        
    @patch('routes.performance.get_global_monitor')
    def test_create_monitoring_snapshot_success(self, mock_get_monitor, client):
        """Test successful monitoring snapshot creation."""
        mock_monitor = MagicMock()
        mock_monitor.save_performance_snapshot.return_value = 'snapshot-123'
        mock_get_monitor.return_value = mock_monitor
        
        response = client.post('/api/performance/monitoring/snapshot')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['snapshot_id'] == 'snapshot-123'


class TestStatsAndExport:
    """Test statistics and export endpoints."""
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_get_stats_summary_success(self, mock_cursor, mock_connection, client, sample_stats_data):
        """Test successful stats summary retrieval."""
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Mock stats query results
        stats_row = (
            sample_stats_data['total_benchmarks'],
            sample_stats_data['benchmark_types'],
            sample_stats_data['avg_p95_latency'],
            sample_stats_data['avg_requests_per_second'],
            sample_stats_data['avg_error_rate'],
            datetime.fromisoformat(sample_stats_data['earliest_test']),
            datetime.fromisoformat(sample_stats_data['latest_test'])
        )
        
        # Mock the fetchone calls for different queries
        mock_cur.fetchone.side_effect = [stats_row, (True,)]  # stats, then table exists check
        mock_cur.fetchall.side_effect = [
            list(sample_stats_data['benchmark_type_counts'].items()),
            list(sample_stats_data['regression_severity_counts'].items())
        ]
        
        response = client.get('/api/performance/stats/summary?days=7')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['total_benchmarks'] == 2
        assert data['data']['avg_p95_latency'] == 102.5
        
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_export_benchmarks_csv(self, mock_cursor, mock_connection, client, sample_benchmark_data):
        """Test CSV export functionality."""
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        
        # Mock CSV export data
        export_data = [
            (1, 'Test Benchmark 1', 'baseline', datetime.utcnow(), 10, 60, 1000,
             50.0, 95.0, 150.0, 200.0, 16.67, 0.01, 25.0, 40.0, 256.0, 320.0, 10.0, None)
        ]
        mock_cur.fetchall.return_value = export_data
        mock_cur.description = [
            ('id',), ('name',), ('benchmark_type',), ('test_timestamp',), ('concurrent_users',),
            ('test_duration_seconds',), ('total_requests',), ('p50_latency',), ('p95_latency',),
            ('p99_latency',), ('max_latency',), ('requests_per_second',), ('error_rate',),
            ('avg_cpu_usage',), ('peak_cpu_usage',), ('avg_memory_mb',), ('peak_memory_mb',),
            ('avg_db_query_time',), ('quality_score_degradation',)
        ]
        
        response = client.get('/api/performance/export/benchmarks')
        
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
        assert 'attachment' in response.headers['Content-Disposition']


class TestHelperFunctions:
    """Test helper functions used in the API."""
    
    def test_is_metric_improvement(self):
        """Test metric improvement determination."""
        from routes.performance import _is_metric_improvement
        
        # Test latency (lower is better)
        assert _is_metric_improvement('p95_latency', -10.0) is True
        assert _is_metric_improvement('p95_latency', 10.0) is False
        
        # Test throughput (higher is better)
        assert _is_metric_improvement('requests_per_second', 10.0) is True
        assert _is_metric_improvement('requests_per_second', -10.0) is False
        
        # Test error rate (lower is better)
        assert _is_metric_improvement('error_rate', -5.0) is True
        assert _is_metric_improvement('error_rate', 5.0) is False
        
    def test_assess_overall_performance(self):
        """Test overall performance assessment."""
        from routes.performance import _assess_overall_performance
        
        # Test improvement scenario
        metrics_comparison = {
            'p95_latency': {'change_percent': -10.0, 'is_better': True},
            'requests_per_second': {'change_percent': 15.0, 'is_better': True},
            'error_rate': {'change_percent': -20.0, 'is_better': True}
        }
        
        assessment = _assess_overall_performance(metrics_comparison)
        assert assessment['assessment'] == 'improved'
        assert assessment['improvements'] == 3
        assert assessment['degradations'] == 0
        
        # Test degradation scenario
        metrics_comparison = {
            'p95_latency': {'change_percent': 20.0, 'is_better': False},
            'requests_per_second': {'change_percent': -15.0, 'is_better': False},
            'error_rate': {'change_percent': 10.0, 'is_better': False}
        }
        
        assessment = _assess_overall_performance(metrics_comparison)
        assert assessment['assessment'] == 'degraded'
        assert assessment['improvements'] == 0
        assert assessment['degradations'] == 3


class TestErrorHandling:
    """Test error handling in API endpoints."""
    
    @patch('routes.performance.get_db_connection')
    @patch('routes.performance.get_cursor')
    def test_404_error_handler(self, mock_cursor, mock_connection, client):
        """Test 404 error handling."""
        # Mock database interaction to return no results (benchmark not found)
        mock_conn = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        mock_cur = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = None  # Simulate benchmark not found
        
        # Test using an existing endpoint that can return 404 (benchmark not found)
        response = client.get('/api/performance/benchmarks/999999')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error'].lower()
        
    def test_500_error_handler(self, client):
        """Test 500 error handling."""
        with patch('routes.performance.get_db_connection', side_effect=Exception("Critical error")):
            response = client.get('/api/performance/benchmarks')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 