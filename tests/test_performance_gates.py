"""
Core Performance Gates Tests

Tests core aspects of the performance gates system:
- Basic gate validation and threshold evaluation
- Gate status and actions
- Core engine functionality

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


class TestPerformanceGatesEngine:
    """Test the core performance gates engine."""
    
    @pytest.fixture
    def engine(self):
        """Create performance gates engine instance."""
        return PerformanceGatesEngine()
    
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
    
    @patch('utils.performance_gates.get_cursor')
    @patch('utils.performance_gates.get_db_connection')
    def test_get_experiment_config(self, mock_db, mock_cursor_func, engine):
        """Test getting experiment configuration."""
        # Create mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Set up the database connection mock
        mock_db.return_value.__enter__.return_value = mock_conn
        
        # Set up the cursor function mock
        mock_cursor_func.return_value.__enter__.return_value = mock_cursor
        
        # Mock the database response with actual data (not MagicMock)
        mock_cursor.fetchone.return_value = (
            1, 'Test Experiment', 'running', 50.0, 
            datetime.now() - timedelta(days=1), None
        )
        
        config = engine._get_experiment_config(1)
        
        assert config is not None
        assert config['id'] == 1
        assert config['name'] == 'Test Experiment'
        assert config['status'] == 'running'


class TestGateEvaluation:
    """Test gate evaluation data structure."""
    
    def test_gate_evaluation_creation(self):
        """Test creating gate evaluation results."""
        evaluation = GateEvaluation(
            gate_id="test_gate_1",
            experiment_id=1,
            variant_id=2,
            metric_name="latency_p95",
            current_value=450.0,
            threshold_value=500.0,
            status=GateStatus.PASSED,
            confidence_level=0.95,
            sample_size=100,
            evaluation_timestamp=datetime.utcnow(),
            message="Performance within acceptable limits",
            recommended_action=GateAction.CONTINUE,
            metadata={}
        )
        
        assert evaluation.experiment_id == 1
        assert evaluation.variant_id == 2
        assert evaluation.metric_name == "latency_p95"
        assert evaluation.status == GateStatus.PASSED
        assert evaluation.recommended_action == GateAction.CONTINUE


class TestPerformanceGatesWorker:
    """Test performance gates worker functionality."""
    
    def test_worker_initialization(self):
        """Test worker initialization."""
        worker = PerformanceGatesWorker(evaluation_interval_seconds=30)
        
        assert worker.evaluation_interval == 30
        assert worker.running is False
        assert worker.worker_thread is None
    
    def test_worker_start_stop(self):
        """Test worker start and stop functionality."""
        worker = PerformanceGatesWorker(evaluation_interval_seconds=0.1)
        
        # Start worker
        worker.start()
        assert worker.running is True
        assert worker.worker_thread is not None
        assert worker.worker_thread.is_alive() is True
        
        # Stop worker
        worker.stop()
        # Note: worker_thread.join() is called inside stop() with timeout
        assert worker.running is False


class TestPerformanceGatesIntegration:
    """Test performance gates integration functions."""
    
    def test_evaluate_experiment_performance_gates_function(self):
        """Test the convenience function for gate evaluation."""
        with patch('utils.performance_gates.performance_gates') as mock_engine:
            mock_engine.evaluate_experiment_gates.return_value = []
            
            results = evaluate_experiment_performance_gates(1)
            
            mock_engine.evaluate_experiment_gates.assert_called_once_with(1, None)
            assert results == [] 