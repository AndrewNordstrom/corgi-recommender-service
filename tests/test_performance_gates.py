"""
Test suite for Performance Gates system

Tests all aspects of the performance gates integration with A/B testing workflow.

TODO #27g: Integrate performance gates into A/B testing workflow
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from utils.performance_gates import (
    PerformanceGatesEngine,
    PerformanceThreshold,
    GateStatus,
    GateAction,
    GateEvaluation,
    performance_gates,
    evaluate_experiment_performance_gates,
    configure_experiment_performance_gates
)
from tasks.performance_gates_worker import (
    PerformanceGatesWorker,
    start_performance_gates_worker,
    stop_performance_gates_worker,
    get_worker_status
)

class TestPerformanceThreshold:
    """Test performance threshold configuration."""
    
    def test_threshold_creation(self):
        """Test creating a performance threshold."""
        threshold = PerformanceThreshold(
            metric_name="latency_p95",
            threshold_value=500.0,
            comparison_operator="lt"
        )
        
        assert threshold.metric_name == "latency_p95"
        assert threshold.threshold_value == 500.0
        assert threshold.comparison_operator == "lt"
        assert threshold.warning_multiplier == 0.8  # default
        assert threshold.enabled is True  # default
        
    def test_threshold_with_all_params(self):
        """Test creating threshold with all parameters."""
        threshold = PerformanceThreshold(
            metric_name="error_rate",
            threshold_value=0.05,
            comparison_operator="lt",
            warning_multiplier=0.6,
            aggregation_method="avg",
            sample_size_minimum=100,
            time_window_minutes=10,
            enabled=False
        )
        
        assert threshold.metric_name == "error_rate"
        assert threshold.threshold_value == 0.05
        assert threshold.warning_multiplier == 0.6
        assert threshold.aggregation_method == "avg"
        assert threshold.sample_size_minimum == 100
        assert threshold.time_window_minutes == 10
        assert threshold.enabled is False


class TestPerformanceGatesEngine:
    """Test the core performance gates engine."""
    
    @pytest.fixture
    def engine(self):
        """Create performance gates engine instance."""
        return PerformanceGatesEngine()
    
    @pytest.fixture
    def mock_db_data(self):
        """Mock database data for testing."""
        return {
            'experiment': {
                'id': 1,
                'name': 'Test Experiment',
                'status': 'running',
                'traffic_percentage': 50.0,
                'start_date': datetime.now() - timedelta(days=1),
                'end_date': None
            },
            'variants': [
                {'id': 1, 'name': 'Control'},
                {'id': 2, 'name': 'Variant A'}
            ],
            'gates': [
                PerformanceThreshold(
                    metric_name="latency_p95",
                    threshold_value=500.0,
                    comparison_operator="lt"
                )
            ],
            'performance_data': {
                'value': 450.0,
                'sample_size': 100,
                'confidence': 0.95
            }
        }
    
    @patch('utils.performance_gates.get_db_connection')
    def test_get_experiment_config(self, mock_db, engine, mock_db_data):
        """Test getting experiment configuration."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            mock_db_data['experiment']['id'],
            mock_db_data['experiment']['name'],
            mock_db_data['experiment']['status'],
            mock_db_data['experiment']['traffic_percentage'],
            mock_db_data['experiment']['start_date'],
            mock_db_data['experiment']['end_date']
        )
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        config = engine._get_experiment_config(1)
        
        assert config is not None
        assert config['id'] == 1
        assert config['name'] == 'Test Experiment'
        assert config['status'] == 'running'
        assert config['traffic_percentage'] == 50.0
    
    @patch('utils.performance_gates.get_db_connection')
    def test_get_experiment_variant_ids(self, mock_db, engine, mock_db_data):
        """Test getting experiment variant IDs."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1,), (2,)]
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        variant_ids = engine._get_experiment_variant_ids(1)
        
        assert variant_ids == [1, 2]
    
    def test_compare_values(self, engine):
        """Test value comparison logic."""
        # Less than
        assert engine._compare_values(450.0, 500.0, "lt") is True
        assert engine._compare_values(550.0, 500.0, "lt") is False
        
        # Greater than
        assert engine._compare_values(15.0, 10.0, "gt") is True
        assert engine._compare_values(5.0, 10.0, "gt") is False
        
        # Equality (with tolerance)
        assert engine._compare_values(10.0, 10.0, "eq") is True
        assert engine._compare_values(10.0001, 10.0, "eq") is True
        assert engine._compare_values(10.1, 10.0, "eq") is False
    
    def test_evaluate_threshold_passed(self, engine):
        """Test threshold evaluation - passed case."""
        threshold = PerformanceThreshold(
            metric_name="latency_p95",
            threshold_value=500.0,
            comparison_operator="lt"
        )
        
        # Use 350.0 which should pass both main (350 < 500) and warning (350 < 400) thresholds
        status, action = engine._evaluate_threshold(350.0, threshold)
        
        assert status == GateStatus.PASSED
        assert action == GateAction.CONTINUE
    
    def test_evaluate_threshold_warning(self, engine):
        """Test threshold evaluation - warning case."""
        threshold = PerformanceThreshold(
            metric_name="latency_p95",
            threshold_value=500.0,
            comparison_operator="lt",
            warning_multiplier=0.8  # Warning at 400ms
        )
        
        status, action = engine._evaluate_threshold(420.0, threshold)
        
        assert status == GateStatus.WARNING
        assert action == GateAction.ALERT_ONLY
    
    def test_evaluate_threshold_failed(self, engine):
        """Test threshold evaluation - failed case."""
        threshold = PerformanceThreshold(
            metric_name="latency_p95",
            threshold_value=500.0,
            comparison_operator="lt"
        )
        
        status, action = engine._evaluate_threshold(600.0, threshold)
        
        assert status == GateStatus.FAILED
        assert action == GateAction.REDUCE_TRAFFIC  # For latency_p95
    
    def test_generate_evaluation_message(self, engine):
        """Test evaluation message generation."""
        threshold = PerformanceThreshold(
            metric_name="latency_p95",
            threshold_value=500.0,
            comparison_operator="lt"
        )
        
        # Passed message
        message = engine._generate_evaluation_message(
            "latency_p95", 450.0, threshold, GateStatus.PASSED
        )
        assert "within acceptable limits" in message
        assert "450.0ms" in message
        
        # Failed message
        message = engine._generate_evaluation_message(
            "latency_p95", 600.0, threshold, GateStatus.FAILED
        )
        assert "exceeded threshold" in message
        assert "600.0ms" in message
    
    @patch('utils.performance_gates.get_db_connection')
    def test_configure_experiment_gates(self, mock_db, engine):
        """Test configuring performance gates for an experiment."""
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        thresholds = [
            PerformanceThreshold(
                metric_name="latency_p95",
                threshold_value=500.0,
                comparison_operator="lt"
            ),
            PerformanceThreshold(
                metric_name="error_rate",
                threshold_value=0.05,
                comparison_operator="lt"
            )
        ]
        
        result = engine.configure_experiment_gates(1, thresholds)
        
        assert result is True
        assert mock_cursor.execute.call_count == 2  # Two thresholds
    
    @patch('utils.performance_gates.get_db_connection')
    def test_get_variant_performance_data_latency(self, mock_db, engine):
        """Test getting performance data for latency metrics."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (450.0, 100, 0.95)
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        threshold = PerformanceThreshold(
            metric_name="latency_p95",
            threshold_value=500.0,
            comparison_operator="lt",
            time_window_minutes=15
        )
        
        data = engine._get_variant_performance_data(1, 1, threshold)
        
        assert data is not None
        assert data['value'] == 450.0
        assert data['sample_size'] == 100
        assert data['confidence'] == 0.95
    
    @patch('utils.performance_gates.get_db_connection')
    def test_get_variant_performance_data_error_rate(self, mock_db, engine):
        """Test getting performance data for error rate metrics."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0.02, 500, 0.95)  # 2% error rate
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        threshold = PerformanceThreshold(
            metric_name="error_rate",
            threshold_value=0.05,
            comparison_operator="lt"
        )
        
        data = engine._get_variant_performance_data(1, 1, threshold)
        
        assert data is not None
        assert data['value'] == 0.02
        assert data['sample_size'] == 500


class TestGateEvaluation:
    """Test gate evaluation functionality."""
    
    def test_gate_evaluation_creation(self):
        """Test creating a gate evaluation result."""
        evaluation = GateEvaluation(
            gate_id="1_1_latency_p95",
            experiment_id=1,
            variant_id=1,
            metric_name="latency_p95",
            current_value=450.0,
            threshold_value=500.0,
            status=GateStatus.PASSED,
            confidence_level=0.95,
            sample_size=100,
            evaluation_timestamp=datetime.now(),
            message="Performance within limits",
            recommended_action=GateAction.CONTINUE,
            metadata={}
        )
        
        assert evaluation.gate_id == "1_1_latency_p95"
        assert evaluation.experiment_id == 1
        assert evaluation.variant_id == 1
        assert evaluation.metric_name == "latency_p95"
        assert evaluation.current_value == 450.0
        assert evaluation.status == GateStatus.PASSED
        assert evaluation.recommended_action == GateAction.CONTINUE


class TestPerformanceGatesWorker:
    """Test the performance gates worker."""
    
    def test_worker_initialization(self):
        """Test worker initialization."""
        worker = PerformanceGatesWorker(evaluation_interval_seconds=60)
        
        assert worker.evaluation_interval == 60
        assert worker.running is False
        assert worker.worker_thread is None
    
    def test_worker_start_stop(self):
        """Test starting and stopping worker."""
        worker = PerformanceGatesWorker(evaluation_interval_seconds=1)
        
        # Start worker
        worker.start()
        assert worker.running is True
        assert worker.worker_thread is not None
        
        # Give it a moment to start
        time.sleep(0.1)
        assert worker.worker_thread.is_alive()
        
        # Stop worker
        worker.stop()
        assert worker.running is False
    
    @patch('tasks.performance_gates_worker.get_db_connection')
    def test_get_active_experiments(self, mock_db):
        """Test getting active experiments."""
        worker = PerformanceGatesWorker()
        
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, 'Test Experiment', 'running', 50.0, datetime.now())
        ]
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        experiments = worker._get_active_experiments()
        
        assert len(experiments) == 1
        assert experiments[0]['id'] == 1
        assert experiments[0]['name'] == 'Test Experiment'
        assert experiments[0]['status'] == 'running'
    
    @patch('tasks.performance_gates_worker.performance_gates')
    def test_evaluate_experiment_gates(self, mock_gates):
        """Test evaluating gates for an experiment."""
        worker = PerformanceGatesWorker()
        
        mock_evaluation = Mock()
        mock_evaluation.status.value = 'passed'
        mock_evaluation.metric_name = 'latency_p95'
        mock_evaluation.variant_id = 1
        
        mock_gates.evaluate_experiment_gates.return_value = [mock_evaluation]
        
        experiment = {'id': 1, 'name': 'Test'}
        worker._evaluate_experiment_gates(experiment)
        
        mock_gates.evaluate_experiment_gates.assert_called_once_with(1)


class TestPerformanceGatesIntegration:
    """Test integration between performance gates and A/B testing."""
    
    def test_evaluate_experiment_performance_gates_function(self):
        """Test the convenience function for evaluating gates."""
        with patch('utils.performance_gates.performance_gates') as mock_gates:
            mock_gates.evaluate_experiment_gates.return_value = []
            
            result = evaluate_experiment_performance_gates(1)
            
            assert result == []
            mock_gates.evaluate_experiment_gates.assert_called_once_with(1, None)
    
    def test_configure_experiment_performance_gates_function(self):
        """Test the convenience function for configuring gates."""
        with patch('utils.performance_gates.performance_gates') as mock_gates:
            mock_gates.configure_experiment_gates.return_value = True
            
            thresholds = [
                PerformanceThreshold(
                    metric_name="latency_p95",
                    threshold_value=500.0,
                    comparison_operator="lt"
                )
            ]
            
            result = configure_experiment_performance_gates(1, thresholds)
            
            assert result is True
            mock_gates.configure_experiment_gates.assert_called_once_with(1, thresholds)
    
    def test_worker_status_functions(self):
        """Test worker status and control functions."""
        # Test getting status when not initialized
        status = get_worker_status()
        assert status['status'] == 'not_initialized'
        
        # Test starting worker
        worker = start_performance_gates_worker(evaluation_interval_seconds=1)
        assert worker is not None
        
        status = get_worker_status()
        assert status['status'] == 'running'
        assert status['evaluation_interval_seconds'] == 1
        
        # Test stopping worker
        stop_performance_gates_worker()
        
        status = get_worker_status()
        assert status['status'] == 'stopped'


class TestPerformanceGatesActions:
    """Test automated actions taken by performance gates."""
    
    @pytest.fixture
    def engine(self):
        """Create performance gates engine instance."""
        return PerformanceGatesEngine()
    
    @patch('utils.performance_gates.get_db_connection')
    def test_pause_variant_action(self, mock_db, engine):
        """Test pausing a variant due to gate failure."""
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        evaluation = GateEvaluation(
            gate_id="1_1_latency_p95",
            experiment_id=1,
            variant_id=1,
            metric_name="latency_p95",
            current_value=800.0,
            threshold_value=500.0,
            status=GateStatus.FAILED,
            confidence_level=0.95,
            sample_size=100,
            evaluation_timestamp=datetime.now(),
            message="Latency exceeded threshold",
            recommended_action=GateAction.PAUSE_VARIANT,
            metadata={}
        )
        
        engine._pause_variant(1, 1, evaluation)
        
        # Verify database calls
        assert mock_cursor.execute.call_count == 2  # Update variant + log event
    
    @patch('utils.performance_gates.get_db_connection')
    def test_reduce_traffic_action(self, mock_db, engine):
        """Test reducing traffic to a variant."""
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        evaluation = GateEvaluation(
            gate_id="1_1_latency_p95",
            experiment_id=1,
            variant_id=1,
            metric_name="latency_p95",
            current_value=600.0,
            threshold_value=500.0,
            status=GateStatus.FAILED,
            confidence_level=0.95,
            sample_size=100,
            evaluation_timestamp=datetime.now(),
            message="Latency exceeded threshold",
            recommended_action=GateAction.REDUCE_TRAFFIC,
            metadata={}
        )
        
        engine._reduce_variant_traffic(1, 1, evaluation)
        
        # Verify database update to reduce traffic
        mock_cursor.execute.assert_called()
    
    @patch('utils.performance_gates.get_db_connection')
    def test_send_alert_action(self, mock_db, engine):
        """Test sending performance alert."""
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        evaluation = GateEvaluation(
            gate_id="1_1_latency_p95",
            experiment_id=1,
            variant_id=1,
            metric_name="latency_p95",
            current_value=520.0,
            threshold_value=500.0,
            status=GateStatus.WARNING,
            confidence_level=0.95,
            sample_size=100,
            evaluation_timestamp=datetime.now(),
            message="Latency approaching threshold",
            recommended_action=GateAction.ALERT_ONLY,
            metadata={}
        )
        
        engine._send_performance_alert(evaluation)
        
        # Verify alert stored in database
        mock_cursor.execute.assert_called()


class TestDefaultThresholds:
    """Test default performance thresholds."""
    
    def test_default_thresholds_loaded(self):
        """Test that default thresholds are properly loaded."""
        engine = PerformanceGatesEngine()
        
        assert 'latency_p95' in engine._default_thresholds
        assert 'latency_p99' in engine._default_thresholds
        assert 'error_rate' in engine._default_thresholds
        assert 'memory_usage' in engine._default_thresholds
        assert 'throughput' in engine._default_thresholds
        
        # Check specific threshold values
        latency_threshold = engine._default_thresholds['latency_p95']
        assert latency_threshold.threshold_value == 500.0
        assert latency_threshold.comparison_operator == "lt"
        
        error_threshold = engine._default_thresholds['error_rate']
        assert error_threshold.threshold_value == 0.05
        assert error_threshold.comparison_operator == "lt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 