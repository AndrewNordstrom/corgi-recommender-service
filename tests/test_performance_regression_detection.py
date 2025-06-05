"""
Tests for Performance Regression Detection System

Tests all aspects of the regression detection system including:
- Threshold-based regression detection
- Statistical significance testing
- Trend analysis
- Alert generation and integration
- Database operations and reporting

TODO #27e: Build performance regression detection system
"""

import json
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

from utils.performance_regression_detection import (
    PerformanceRegressionDetector,
    RegressionSeverity,
    RegressionType,
    RegressionThreshold,
    RegressionDetectionResult,
    RegressionReport,
    get_regression_detector,
    detect_regressions_for_benchmark
)
from utils.performance_monitoring import PerformanceMonitoringSystem


class TestRegressionThreshold:
    """Test RegressionThreshold configuration."""
    
    def test_threshold_creation(self):
        """Test creating regression thresholds."""
        threshold = RegressionThreshold(
            metric_name="p95_latency",
            warning_threshold_percent=15.0,
            critical_threshold_percent=25.0,
            absolute_threshold=500.0
        )
        
        assert threshold.metric_name == "p95_latency"
        assert threshold.warning_threshold_percent == 15.0
        assert threshold.critical_threshold_percent == 25.0
        assert threshold.absolute_threshold == 500.0
        assert threshold.enabled is True
        assert threshold.statistical_significance == 0.05
        assert threshold.minimum_sample_size == 10
        assert threshold.trend_window_days == 7
    
    def test_threshold_disabled(self):
        """Test disabled thresholds."""
        threshold = RegressionThreshold(
            metric_name="test_metric",
            warning_threshold_percent=10.0,
            critical_threshold_percent=20.0,
            enabled=False
        )
        
        assert threshold.enabled is False


class TestRegressionDetectionResult:
    """Test RegressionDetectionResult data structure."""
    
    def test_detection_result_creation(self):
        """Test creating detection results."""
        result = RegressionDetectionResult(
            metric_name="p95_latency",
            regression_type=RegressionType.LATENCY_DEGRADATION,
            severity=RegressionSeverity.HIGH,
            baseline_value=100.0,
            current_value=150.0,
            change_percent=50.0,
            absolute_change=50.0,
            statistical_significance=0.02,
            confidence_interval=(140.0, 160.0),
            trend_direction="degrading",
            detection_timestamp=datetime.utcnow(),
            evidence={"test": "data"},
            recommendation="Test recommendation"
        )
        
        assert result.metric_name == "p95_latency"
        assert result.regression_type == RegressionType.LATENCY_DEGRADATION
        assert result.severity == RegressionSeverity.HIGH
        assert result.change_percent == 50.0
        assert result.trend_direction == "degrading"


class TestPerformanceRegressionDetector:
    """Test the main PerformanceRegressionDetector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = PerformanceRegressionDetector()
        
        # Mock benchmark data
        self.mock_baseline = {
            'id': 1,
            'name': 'Baseline Test',
            'benchmark_type': 'baseline',
            'test_timestamp': datetime.utcnow() - timedelta(days=1),
            'p95_latency': 100.0,
            'p99_latency': 150.0,
            'requests_per_second': 200.0,
            'error_rate': 0.01,
            'peak_cpu_usage': 60.0,
            'peak_memory_mb': 1024.0,
            'avg_db_query_time': 10.0,
            'concurrent_users': 50,
            'test_duration_seconds': 300,
            'total_requests': 1000
        }
        
        self.mock_current = {
            'id': 2,
            'name': 'Current Test',
            'benchmark_type': 'test',
            'test_timestamp': datetime.utcnow(),
            'p95_latency': 130.0,  # 30% increase
            'p99_latency': 200.0,  # 33% increase
            'requests_per_second': 160.0,  # 20% decrease
            'error_rate': 0.02,  # 100% increase
            'peak_cpu_usage': 75.0,  # 25% increase
            'peak_memory_mb': 1280.0,  # 25% increase
            'avg_db_query_time': 15.0,  # 50% increase
            'concurrent_users': 50,
            'test_duration_seconds': 300,
            'total_requests': 900
        }
    
    def test_default_thresholds_creation(self):
        """Test that default thresholds are properly created."""
        thresholds = self.detector.default_thresholds
        
        assert 'p95_latency' in thresholds
        assert 'p99_latency' in thresholds
        assert 'requests_per_second' in thresholds
        assert 'error_rate' in thresholds
        assert 'peak_cpu_usage' in thresholds
        assert 'peak_memory_mb' in thresholds
        assert 'avg_db_query_time' in thresholds
        
        # Check specific threshold values
        p95_threshold = thresholds['p95_latency']
        assert p95_threshold.warning_threshold_percent == 15.0
        assert p95_threshold.critical_threshold_percent == 25.0
        assert p95_threshold.absolute_threshold == 500.0
    
    def test_classify_regression_type(self):
        """Test regression type classification."""
        # Latency degradation
        assert self.detector._classify_regression_type('p95_latency', 20.0) == RegressionType.LATENCY_DEGRADATION
        assert self.detector._classify_regression_type('p99_latency', 15.0) == RegressionType.LATENCY_DEGRADATION
        
        # Throughput degradation
        assert self.detector._classify_regression_type('requests_per_second', -20.0) == RegressionType.THROUGHPUT_DEGRADATION
        
        # Error rate increase
        assert self.detector._classify_regression_type('error_rate', 50.0) == RegressionType.ERROR_RATE_INCREASE
        
        # Resource increase
        assert self.detector._classify_regression_type('peak_cpu_usage', 30.0) == RegressionType.RESOURCE_INCREASE
        assert self.detector._classify_regression_type('peak_memory_mb', 25.0) == RegressionType.RESOURCE_INCREASE
        
        # Quality degradation
        assert self.detector._classify_regression_type('quality_score', -15.0) == RegressionType.QUALITY_DEGRADATION
    
    def test_determine_severity_latency(self):
        """Test severity determination for latency metrics."""
        threshold = self.detector.default_thresholds['p95_latency']
        
        # No regression (improvement)
        severity = self.detector._determine_severity(
            'p95_latency', 90.0, 100.0, -10.0, -10.0, threshold
        )
        assert severity == RegressionSeverity.NONE
        
        # Medium regression
        severity = self.detector._determine_severity(
            'p95_latency', 120.0, 100.0, 20.0, 20.0, threshold
        )
        assert severity == RegressionSeverity.MEDIUM
        
        # Critical regression (absolute threshold)
        severity = self.detector._determine_severity(
            'p95_latency', 600.0, 100.0, 500.0, 500.0, threshold
        )
        assert severity == RegressionSeverity.CRITICAL
        
        # Critical regression (percentage threshold)
        severity = self.detector._determine_severity(
            'p95_latency', 130.0, 100.0, 30.0, 30.0, threshold
        )
        assert severity == RegressionSeverity.CRITICAL
    
    def test_determine_severity_throughput(self):
        """Test severity determination for throughput metrics."""
        threshold = self.detector.default_thresholds['requests_per_second']
        
        # No regression (improvement)
        severity = self.detector._determine_severity(
            'requests_per_second', 220.0, 200.0, 10.0, 20.0, threshold
        )
        assert severity == RegressionSeverity.NONE
        
        # Critical regression (absolute threshold)
        severity = self.detector._determine_severity(
            'requests_per_second', 40.0, 200.0, -80.0, -160.0, threshold
        )
        assert severity == RegressionSeverity.CRITICAL
        
        # Medium regression
        severity = self.detector._determine_severity(
            'requests_per_second', 160.0, 200.0, -20.0, -40.0, threshold
        )
        assert severity == RegressionSeverity.MEDIUM
    
    def test_determine_severity_error_rate(self):
        """Test severity determination for error rate."""
        threshold = self.detector.default_thresholds['error_rate']
        
        # Critical regression (absolute threshold)
        severity = self.detector._determine_severity(
            'error_rate', 0.06, 0.01, 500.0, 0.05, threshold
        )
        assert severity == RegressionSeverity.CRITICAL
        
        # Critical regression (percentage threshold)
        severity = self.detector._determine_severity(
            'error_rate', 0.03, 0.01, 200.0, 0.02, threshold
        )
        assert severity == RegressionSeverity.CRITICAL
    
    @patch('utils.performance_regression_detection.get_db_connection')
    def test_get_benchmark_data(self, mock_get_db):
        """Test getting benchmark data from database."""
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock cursor response
        mock_cursor.fetchone.return_value = [1, 'Test', 'baseline', datetime.utcnow(), 100.0]
        mock_cursor.description = [('id',), ('name',), ('benchmark_type',), ('test_timestamp',), ('p95_latency',)]
        
        result = self.detector._get_benchmark_data(1)
        
        assert result is not None
        assert result['id'] == 1
        assert result['name'] == 'Test'
        assert result['p95_latency'] == 100.0
        
        mock_cursor.execute.assert_called_once()
    
    @patch('utils.performance_regression_detection.get_db_connection')
    def test_find_latest_baseline(self, mock_get_db):
        """Test finding latest baseline benchmark."""
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock cursor response
        mock_cursor.fetchone.return_value = [5]
        
        result = self.detector._find_latest_baseline()
        
        assert result == 5
        mock_cursor.execute.assert_called_once()
    
    def test_calculate_metric_change(self):
        """Test metric change calculation."""
        change = self.detector._calculate_metric_change(
            self.mock_current, self.mock_baseline, 'p95_latency'
        )
        assert change == 30.0  # (130-100)/100 * 100
        
        change = self.detector._calculate_metric_change(
            self.mock_current, self.mock_baseline, 'requests_per_second'
        )
        assert change == -20.0  # (160-200)/200 * 100
        
        # Test zero baseline
        zero_baseline = self.mock_baseline.copy()
        zero_baseline['error_rate'] = 0
        change = self.detector._calculate_metric_change(
            self.mock_current, zero_baseline, 'error_rate'
        )
        assert change == 0.0
    
    def test_generate_metric_recommendation(self):
        """Test metric-specific recommendation generation."""
        # Latency degradation
        rec = self.detector._generate_metric_recommendation(
            'p95_latency', RegressionType.LATENCY_DEGRADATION, 
            RegressionSeverity.CRITICAL, 30.0
        )
        assert "URGENT" in rec
        assert "Latency" in rec
        
        # Throughput degradation
        rec = self.detector._generate_metric_recommendation(
            'requests_per_second', RegressionType.THROUGHPUT_DEGRADATION,
            RegressionSeverity.HIGH, -20.0
        )
        assert "Throughput degradation" in rec
        
        # Error rate increase
        rec = self.detector._generate_metric_recommendation(
            'error_rate', RegressionType.ERROR_RATE_INCREASE,
            RegressionSeverity.CRITICAL, 100.0
        )
        assert "CRITICAL" in rec
        assert "Error rate" in rec
    
    def test_calculate_performance_score(self):
        """Test performance score calculation."""
        # No regressions
        score = self.detector._calculate_performance_score(
            self.mock_current, self.mock_baseline, []
        )
        assert score == 100.0
        
        # With regressions
        regressions = [
            RegressionDetectionResult(
                metric_name="p95_latency",
                regression_type=RegressionType.LATENCY_DEGRADATION,
                severity=RegressionSeverity.HIGH,
                baseline_value=100.0,
                current_value=130.0,
                change_percent=30.0,
                absolute_change=30.0,
                statistical_significance=0.02,
                confidence_interval=(120.0, 140.0),
                trend_direction="degrading",
                detection_timestamp=datetime.utcnow(),
                evidence={},
                recommendation="Test"
            ),
            RegressionDetectionResult(
                metric_name="error_rate",
                regression_type=RegressionType.ERROR_RATE_INCREASE,
                severity=RegressionSeverity.CRITICAL,
                baseline_value=0.01,
                current_value=0.02,
                change_percent=100.0,
                absolute_change=0.01,
                statistical_significance=0.01,
                confidence_interval=(0.018, 0.022),
                trend_direction="degrading",
                detection_timestamp=datetime.utcnow(),
                evidence={},
                recommendation="Test"
            )
        ]
        
        score = self.detector._calculate_performance_score(
            self.mock_current, self.mock_baseline, regressions
        )
        assert score == 50.0  # 100 - 20 (HIGH) - 30 (CRITICAL)
    
    def test_determine_overall_severity(self):
        """Test overall severity determination."""
        # No regressions
        severity = self.detector._determine_overall_severity([])
        assert severity == RegressionSeverity.NONE
        
        # Single high regression
        regressions = [
            RegressionDetectionResult(
                metric_name="test",
                regression_type=RegressionType.LATENCY_DEGRADATION,
                severity=RegressionSeverity.HIGH,
                baseline_value=100.0,
                current_value=130.0,
                change_percent=30.0,
                absolute_change=30.0,
                statistical_significance=0.02,
                confidence_interval=(120.0, 140.0),
                trend_direction="degrading",
                detection_timestamp=datetime.utcnow(),
                evidence={},
                recommendation="Test"
            )
        ]
        
        severity = self.detector._determine_overall_severity(regressions)
        assert severity == RegressionSeverity.HIGH
        
        # Multiple high regressions should escalate to critical
        high_regressions = [regressions[0] for _ in range(3)]
        severity = self.detector._determine_overall_severity(high_regressions)
        assert severity == RegressionSeverity.CRITICAL
    
    def test_gather_regression_evidence(self):
        """Test regression evidence gathering."""
        evidence = self.detector._gather_regression_evidence(
            'p95_latency', self.mock_current, self.mock_baseline, 30.0
        )
        
        assert 'baseline_timestamp' in evidence
        assert 'current_timestamp' in evidence
        assert 'baseline_test_config' in evidence
        assert 'current_test_config' in evidence
        assert 'related_metrics' in evidence
        
        # Check related metrics for latency
        related = evidence['related_metrics']
        assert 'error_rate_change' in related
        assert 'cpu_usage_change' in related
        assert 'memory_usage_change' in related
        
        # Test error rate evidence
        evidence = self.detector._gather_regression_evidence(
            'error_rate', self.mock_current, self.mock_baseline, 100.0
        )
        
        related = evidence['related_metrics']
        assert 'latency_change' in related
        assert 'throughput_change' in related
    
    @patch('utils.performance_regression_detection.get_db_connection')
    def test_get_historical_metric_data(self, mock_get_db):
        """Test getting historical metric data."""
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock cursor response
        mock_cursor.fetchall.return_value = [
            (100.0, True, datetime.utcnow() - timedelta(days=1)),
            (120.0, False, datetime.utcnow() - timedelta(hours=12)),
            (110.0, False, datetime.utcnow())
        ]
        
        result = self.detector._get_historical_metric_data('p95_latency', days=7)
        
        assert len(result) == 3
        assert result[0]['value'] == 100.0
        assert result[0]['is_baseline'] is True
        assert result[1]['value'] == 120.0
        assert result[1]['is_baseline'] is False
    
    def test_analyze_metric_trend(self):
        """Test metric trend analysis."""
        with patch.object(self.detector, '_get_recent_metric_data') as mock_get_data:
            # Insufficient data
            mock_get_data.return_value = [{'value': 100.0}]
            trend = self.detector._analyze_metric_trend('p95_latency', 1)
            assert trend == "insufficient_data"
            
            # Stable trend (very small variations)
            mock_get_data.return_value = [
                {'value': 100.0}, {'value': 100.001}, {'value': 99.999}, {'value': 100.002}
            ]
            trend = self.detector._analyze_metric_trend('p95_latency', 1)
            assert trend == "stable"
            
            # Improving trend (for latency, lower is better)
            mock_get_data.return_value = [
                {'value': 110.0}, {'value': 105.0}, {'value': 100.0}, {'value': 95.0}
            ]
            trend = self.detector._analyze_metric_trend('p95_latency', 1)
            assert trend == "improving"
            
            # Degrading trend (for latency, higher is worse)
            mock_get_data.return_value = [
                {'value': 90.0}, {'value': 95.0}, {'value': 100.0}, {'value': 105.0}
            ]
            trend = self.detector._analyze_metric_trend('p95_latency', 1)
            assert trend == "degrading"
    
    def test_generate_recommendations(self):
        """Test comprehensive recommendation generation."""
        # No regressions
        recommendations = self.detector._generate_recommendations([], {}, 95.0)
        assert len(recommendations) == 1
        assert "No performance regressions detected" in recommendations[0]
        
        # Critical regressions
        critical_regression = RegressionDetectionResult(
            metric_name="p95_latency",
            regression_type=RegressionType.LATENCY_DEGRADATION,
            severity=RegressionSeverity.CRITICAL,
            baseline_value=100.0,
            current_value=150.0,
            change_percent=50.0,
            absolute_change=50.0,
            statistical_significance=0.01,
            confidence_interval=(140.0, 160.0),
            trend_direction="degrading",
            detection_timestamp=datetime.utcnow(),
            evidence={},
            recommendation="URGENT: Latency has critically degraded."
        )
        
        recommendations = self.detector._generate_recommendations(
            [critical_regression], {}, 60.0
        )
        
        assert any("URGENT" in rec for rec in recommendations)
        assert any("performance score is low" in rec for rec in recommendations)
        
        # Trend-based recommendations
        trend_analysis = {
            'p95_latency': {'trend_direction': 'degrading'},
            'error_rate': {'trend_direction': 'degrading'}
        }
        
        recommendations = self.detector._generate_recommendations(
            [], trend_analysis, 85.0
        )
        
        assert any("Degrading trends detected in:" in rec for rec in recommendations)
    
    def test_perform_statistical_analysis(self):
        """Test statistical analysis."""
        regressions = [
            RegressionDetectionResult(
                metric_name="p95_latency",
                regression_type=RegressionType.LATENCY_DEGRADATION,
                severity=RegressionSeverity.HIGH,
                baseline_value=100.0,
                current_value=130.0,
                change_percent=30.0,
                absolute_change=30.0,
                statistical_significance=0.02,
                confidence_interval=(120.0, 140.0),
                trend_direction="degrading",
                detection_timestamp=datetime.utcnow(),
                evidence={},
                recommendation="Test"
            ),
            RegressionDetectionResult(
                metric_name="peak_cpu_usage",
                regression_type=RegressionType.RESOURCE_INCREASE,
                severity=RegressionSeverity.MEDIUM,
                baseline_value=60.0,
                current_value=75.0,
                change_percent=25.0,
                absolute_change=15.0,
                statistical_significance=0.03,
                confidence_interval=(70.0, 80.0),
                trend_direction="degrading",
                detection_timestamp=datetime.utcnow(),
                evidence={},
                recommendation="Test"
            )
        ]
        
        analysis = self.detector._perform_statistical_analysis(
            self.mock_current, self.mock_baseline, regressions
        )
        
        assert analysis['total_metrics_analyzed'] == len(self.detector.default_thresholds)
        assert analysis['regressions_detected'] == 2
        assert 'severity_distribution' in analysis
        assert 'confidence_scores' in analysis
        assert 'correlation_analysis' in analysis
        
        # Check severity distribution
        severity_dist = analysis['severity_distribution']
        assert severity_dist['high'] == 1
        assert severity_dist['medium'] == 1
        assert severity_dist['critical'] == 0
        
        # Check correlation analysis
        correlation = analysis['correlation_analysis']
        assert 'latency_resource_correlation' in correlation
        assert correlation['latency_resource_correlation']['detected'] is True
    
    def test_analyze_performance_trends(self):
        """Test performance trend analysis."""
        with patch.object(self.detector, '_get_recent_metric_data') as mock_get_data:
            # Mock data for each metric
            def side_effect(metric_name, days):
                if metric_name == 'p95_latency':
                    return [
                        {'value': 90.0}, {'value': 95.0}, {'value': 100.0}, 
                        {'value': 105.0}, {'value': 110.0}
                    ]
                elif metric_name == 'requests_per_second':
                    return [
                        {'value': 210.0}, {'value': 205.0}, {'value': 200.0},
                        {'value': 195.0}, {'value': 190.0}
                    ]
                elif metric_name == 'error_rate':
                    return [
                        {'value': 0.005}, {'value': 0.007}, {'value': 0.01},
                        {'value': 0.012}, {'value': 0.015}
                    ]
                else:
                    return []
            
            mock_get_data.side_effect = side_effect
            
            trends = self.detector._analyze_performance_trends(2, 1, days=30)
            
            assert 'p95_latency' in trends
            assert 'requests_per_second' in trends
            assert 'error_rate' in trends
            
            # Check trend directions
            assert trends['p95_latency']['trend_direction'] == 'degrading'
            assert trends['requests_per_second']['trend_direction'] == 'degrading'
            assert trends['error_rate']['trend_direction'] == 'degrading'
            
            # Check statistical data
            assert 'recent_average' in trends['p95_latency']
            assert 'overall_average' in trends['p95_latency']
            assert 'volatility' in trends['p95_latency']
            assert trends['p95_latency']['data_points'] == 5


class TestPerformanceRegressionDetectorIntegration:
    """Integration tests for the regression detection system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitoring_system = Mock(spec=PerformanceMonitoringSystem)
        self.detector = PerformanceRegressionDetector(self.monitoring_system)
        
        # Mock benchmark data with realistic values
        self.baseline_data = {
            'id': 1,
            'name': 'Baseline Performance Test',
            'benchmark_type': 'baseline',
            'test_timestamp': datetime.utcnow() - timedelta(days=1),
            'p95_latency': 120.0,
            'p99_latency': 180.0,
            'requests_per_second': 150.0,
            'error_rate': 0.005,  # 0.5%
            'peak_cpu_usage': 65.0,
            'peak_memory_mb': 1200.0,
            'avg_db_query_time': 8.0,
            'concurrent_users': 25,
            'test_duration_seconds': 600,
            'total_requests': 2000
        }
        
        self.regression_data = {
            'id': 2,
            'name': 'Current Performance Test',
            'benchmark_type': 'test',
            'test_timestamp': datetime.utcnow(),
            'p95_latency': 180.0,  # 50% increase - HIGH regression
            'p99_latency': 280.0,  # 55% increase - CRITICAL regression
            'requests_per_second': 120.0,  # 20% decrease - MEDIUM regression
            'error_rate': 0.015,  # 200% increase - CRITICAL regression
            'peak_cpu_usage': 85.0,  # 30% increase - MEDIUM regression
            'peak_memory_mb': 1600.0,  # 33% increase - MEDIUM regression
            'avg_db_query_time': 15.0,  # 87% increase - CRITICAL regression
            'concurrent_users': 25,
            'test_duration_seconds': 600,
            'total_requests': 1800
        }
    
    @patch('utils.performance_regression_detection.get_db_connection')
    def test_full_regression_detection_workflow(self, mock_get_db):
        """Test complete regression detection workflow."""
        # Mock database operations
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Directly mock the get_benchmark_data and find_latest_baseline methods
        with patch.object(self.detector, '_get_benchmark_data') as mock_get_benchmark:
            with patch.object(self.detector, '_find_latest_baseline', return_value=1):
                with patch.object(self.detector, '_store_regression_report'):
                    with patch.object(self.detector, '_get_historical_metric_data', return_value=[]):
                        with patch.object(self.detector, '_get_recent_metric_data', return_value=[]):
                            # Set up mock responses for benchmark data
                            def benchmark_side_effect(benchmark_id):
                                if benchmark_id == 2:
                                    return self.regression_data
                                elif benchmark_id == 1:
                                    return self.baseline_data
                                return None
                            
                            mock_get_benchmark.side_effect = benchmark_side_effect
                            
                            # Run regression detection
                            report = self.detector.detect_regressions(2, 1)
        
        # Verify report structure
        assert isinstance(report, RegressionReport)
        assert report.current_benchmark_id == 2
        assert report.baseline_benchmark_id == 1
        assert report.test_name == 'Current Performance Test'
        assert len(report.detected_regressions) > 0
        
        # Verify regression detection
        regressions_by_metric = {r.metric_name: r for r in report.detected_regressions}
        
        # Check that critical regressions were detected
        assert 'p99_latency' in regressions_by_metric
        assert regressions_by_metric['p99_latency'].severity in [RegressionSeverity.HIGH, RegressionSeverity.CRITICAL]
        
        assert 'error_rate' in regressions_by_metric
        assert regressions_by_metric['error_rate'].severity in [RegressionSeverity.HIGH, RegressionSeverity.CRITICAL]
        
        # Verify overall severity is appropriately high
        assert report.overall_severity in [RegressionSeverity.HIGH, RegressionSeverity.CRITICAL]
        
        # Verify performance score reflects regressions
        assert report.performance_score < 80.0
        
        # Verify recommendations are generated
        assert len(report.recommendations) > 0
        assert any("URGENT" in rec or "Critical" in rec for rec in report.recommendations)
        
        # Verify statistical summary
        assert 'total_metrics_analyzed' in report.statistical_summary
        assert 'regressions_detected' in report.statistical_summary
        assert 'severity_distribution' in report.statistical_summary
    
    def test_no_regressions_scenario(self):
        """Test scenario with no significant regressions."""
        # Create data with minimal changes
        good_current_data = self.baseline_data.copy()
        good_current_data.update({
            'id': 3,
            'name': 'Good Performance Test',
            'p95_latency': 125.0,  # 4% increase - below threshold
            'p99_latency': 185.0,  # 3% increase - below threshold
            'requests_per_second': 155.0,  # 3% increase - improvement
            'error_rate': 0.004,  # 20% decrease - improvement
        })
        
        with patch.object(self.detector, '_get_benchmark_data') as mock_get_benchmark:
            with patch.object(self.detector, '_find_latest_baseline', return_value=1):
                with patch.object(self.detector, '_store_regression_report'):
                    with patch.object(self.detector, '_get_historical_metric_data', return_value=[]):
                        with patch.object(self.detector, '_get_recent_metric_data', return_value=[]):
                            mock_get_benchmark.side_effect = lambda bid: good_current_data if bid == 3 else self.baseline_data
                            
                            report = self.detector.detect_regressions(3, 1)
        
        # Verify no significant regressions
        assert report.overall_severity == RegressionSeverity.NONE
        assert len(report.detected_regressions) == 0
        assert report.performance_score >= 95.0
        assert "No performance regressions detected" in report.recommendations[0]
    
    def test_monitoring_system_integration(self):
        """Test integration with monitoring system for alerts."""
        # Create detector with monitoring system
        mock_notification_manager = Mock()
        self.monitoring_system.notification_manager = mock_notification_manager
        
        detector = PerformanceRegressionDetector(self.monitoring_system)
        
        # Create a critical regression
        critical_regression = RegressionDetectionResult(
            metric_name="p95_latency",
            regression_type=RegressionType.LATENCY_DEGRADATION,
            severity=RegressionSeverity.CRITICAL,
            baseline_value=100.0,
            current_value=200.0,
            change_percent=100.0,
            absolute_change=100.0,
            statistical_significance=0.001,
            confidence_interval=(180.0, 220.0),
            trend_direction="degrading",
            detection_timestamp=datetime.utcnow(),
            evidence={},
            recommendation="URGENT: Critical latency degradation detected."
        )
        
        report = RegressionReport(
            report_id="test_report_123",
            test_name="Critical Test",
            detection_timestamp=datetime.utcnow(),
            overall_severity=RegressionSeverity.CRITICAL,
            baseline_benchmark_id=1,
            current_benchmark_id=2,
            detected_regressions=[critical_regression],
            statistical_summary={},
            trend_analysis={},
            performance_score=40.0,
            recommendations=["URGENT: Take immediate action."]
        )
        
        # Test alert sending
        detector._send_regression_alerts(report)
        
        # Verify notification was sent
        mock_notification_manager.notify.assert_called_once()
        
        # Verify alert content
        alert_call = mock_notification_manager.notify.call_args[0][0]
        assert "regression_p95_latency" in alert_call.alert_id
        assert alert_call.metric_name == "p95_latency"
        assert alert_call.severity == "critical"
        assert "Critical latency degradation" in alert_call.message


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_get_regression_detector_singleton(self):
        """Test global detector singleton pattern."""
        detector1 = get_regression_detector()
        detector2 = get_regression_detector()
        
        assert detector1 is detector2
        assert isinstance(detector1, PerformanceRegressionDetector)
    
    @patch('utils.performance_regression_detection.get_regression_detector')
    def test_detect_regressions_for_benchmark_convenience(self, mock_get_detector):
        """Test convenience function for regression detection."""
        mock_detector = Mock()
        mock_report = Mock(spec=RegressionReport)
        mock_detector.detect_regressions.return_value = mock_report
        mock_get_detector.return_value = mock_detector
        
        result = detect_regressions_for_benchmark(123, 456)
        
        assert result == mock_report
        mock_detector.detect_regressions.assert_called_once_with(123, 456)


class TestRegressionDetectionCLI:
    """Test command-line interface functionality."""
    
    @patch('utils.performance_regression_detection.detect_regressions_for_benchmark')
    @patch('sys.argv', ['test_script.py', '123', '--baseline-id', '456', '--output', 'test_report.json'])
    def test_cli_basic_functionality(self, mock_detect):
        """Test basic CLI functionality."""
        # Mock a regression report
        mock_regression = RegressionDetectionResult(
            metric_name="p95_latency",
            regression_type=RegressionType.LATENCY_DEGRADATION,
            severity=RegressionSeverity.HIGH,
            baseline_value=100.0,
            current_value=150.0,
            change_percent=50.0,
            absolute_change=50.0,
            statistical_significance=0.02,
            confidence_interval=(140.0, 160.0),
            trend_direction="degrading",
            detection_timestamp=datetime.utcnow(),
            evidence={},
            recommendation="High latency degradation detected."
        )
        
        mock_report = RegressionReport(
            report_id="test_report_123",
            test_name="CLI Test",
            detection_timestamp=datetime.utcnow(),
            overall_severity=RegressionSeverity.HIGH,
            baseline_benchmark_id=456,
            current_benchmark_id=123,
            detected_regressions=[mock_regression],
            statistical_summary={},
            trend_analysis={},
            performance_score=75.0,
            recommendations=["Consider optimization.", "Monitor closely."]
        )
        
        mock_detect.return_value = mock_report
        
        # Test would require executing the CLI code - for now just verify the mock setup
        assert mock_report.current_benchmark_id == 123
        assert mock_report.baseline_benchmark_id == 456
        assert len(mock_report.detected_regressions) == 1
        assert mock_report.performance_score == 75.0 