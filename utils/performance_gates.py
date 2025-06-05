"""
Performance Gates for A/B Testing Workflow Integration

This module provides automated performance validation during A/B testing,
ensuring that algorithm variants maintain acceptable performance characteristics
before being promoted to wider audiences.

TODO #27g: Integrate performance gates into A/B testing workflow
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

from db.connection import get_db_connection, get_cursor
import utils.metrics as prometheus_metrics
from utils.ab_performance import PerformanceTracker

logger = logging.getLogger(__name__)

class GateStatus(Enum):
    """Performance gate evaluation status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"
    DISABLED = "disabled"

class GateAction(Enum):
    """Actions to take when performance gates fail."""
    CONTINUE = "continue"          # Log warning but continue test
    PAUSE_VARIANT = "pause_variant"  # Pause the failing variant
    STOP_EXPERIMENT = "stop_experiment"  # Stop entire experiment
    REDUCE_TRAFFIC = "reduce_traffic"  # Reduce traffic to variant
    ALERT_ONLY = "alert_only"      # Send alert but take no action

@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_name: str
    threshold_value: float
    comparison_operator: str  # "lt", "gt", "lte", "gte", "eq"
    warning_multiplier: float = 0.8  # Warning at 80% of threshold
    aggregation_method: str = "avg"  # "avg", "p50", "p95", "p99", "max"
    sample_size_minimum: int = 50
    time_window_minutes: int = 15
    enabled: bool = True

@dataclass
class GateEvaluation:
    """Result of a performance gate evaluation."""
    gate_id: str
    experiment_id: int
    variant_id: int
    metric_name: str
    current_value: float
    threshold_value: float
    status: GateStatus
    confidence_level: float
    sample_size: int
    evaluation_timestamp: datetime
    message: str
    recommended_action: GateAction
    metadata: Dict[str, Any]

class PerformanceGatesEngine:
    """
    Core engine for evaluating performance gates during A/B testing.
    
    Monitors experiment variants in real-time and takes automated actions
    when performance thresholds are breached.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.performance_tracker = PerformanceTracker()
        self._default_thresholds = self._load_default_thresholds()
        
    def _load_default_thresholds(self) -> Dict[str, PerformanceThreshold]:
        """Load default performance thresholds for common metrics."""
        return {
            "latency_p95": PerformanceThreshold(
                metric_name="latency_p95",
                threshold_value=500.0,  # 500ms
                comparison_operator="lt",
                warning_multiplier=0.8,
                aggregation_method="p95",
                time_window_minutes=10
            ),
            "latency_p99": PerformanceThreshold(
                metric_name="latency_p99", 
                threshold_value=1000.0,  # 1 second
                comparison_operator="lt",
                warning_multiplier=0.8,
                aggregation_method="p99",
                time_window_minutes=10
            ),
            "error_rate": PerformanceThreshold(
                metric_name="error_rate",
                threshold_value=0.05,  # 5%
                comparison_operator="lt",
                warning_multiplier=0.6,
                aggregation_method="avg",
                time_window_minutes=5
            ),
            "memory_usage": PerformanceThreshold(
                metric_name="memory_usage",
                threshold_value=1024.0,  # 1GB
                comparison_operator="lt",
                warning_multiplier=0.8,
                aggregation_method="p95",
                time_window_minutes=15
            ),
            "throughput": PerformanceThreshold(
                metric_name="requests_per_second",
                threshold_value=10.0,  # Minimum 10 RPS
                comparison_operator="gt",
                warning_multiplier=1.2,
                aggregation_method="avg",
                time_window_minutes=10
            ),
            "db_query_time": PerformanceThreshold(
                metric_name="db_query_time",
                threshold_value=100.0,  # 100ms
                comparison_operator="lt",
                warning_multiplier=0.8,
                aggregation_method="p95",
                time_window_minutes=10
            )
        }
    
    def evaluate_experiment_gates(self, experiment_id: int, 
                                variant_ids: Optional[List[int]] = None) -> List[GateEvaluation]:
        """
        Evaluate all performance gates for an experiment.
        
        Args:
            experiment_id: ID of the experiment to evaluate
            variant_ids: Optional list of variant IDs to evaluate (defaults to all)
            
        Returns:
            List of gate evaluation results
        """
        evaluations = []
        
        try:
            # Get experiment configuration
            experiment = self._get_experiment_config(experiment_id)
            if not experiment:
                self.logger.error(f"Experiment {experiment_id} not found")
                return evaluations
                
            # Get variants to evaluate
            if variant_ids is None:
                variant_ids = self._get_experiment_variant_ids(experiment_id)
                
            # Get performance gates configuration for this experiment
            gates_config = self._get_experiment_gates_config(experiment_id)
            
            # Evaluate each variant against each gate
            for variant_id in variant_ids:
                for gate_config in gates_config:
                    if gate_config.enabled:
                        evaluation = self._evaluate_single_gate(
                            experiment_id, variant_id, gate_config
                        )
                        if evaluation:
                            evaluations.append(evaluation)
                            
                            # Take automated action if needed
                            self._process_gate_evaluation(evaluation)
                            
        except Exception as e:
            self.logger.error(f"Error evaluating performance gates for experiment {experiment_id}: {e}")
            
        return evaluations
    
    def _evaluate_single_gate(self, experiment_id: int, variant_id: int, 
                            threshold: PerformanceThreshold) -> Optional[GateEvaluation]:
        """Evaluate a single performance gate for a variant."""
        try:
            # Get performance data for the time window
            performance_data = self._get_variant_performance_data(
                experiment_id, variant_id, threshold
            )
            
            if not performance_data or performance_data['sample_size'] < threshold.sample_size_minimum:
                return GateEvaluation(
                    gate_id=f"{experiment_id}_{variant_id}_{threshold.metric_name}",
                    experiment_id=experiment_id,
                    variant_id=variant_id,
                    metric_name=threshold.metric_name,
                    current_value=0.0,
                    threshold_value=threshold.threshold_value,
                    status=GateStatus.PENDING,
                    confidence_level=0.0,
                    sample_size=performance_data['sample_size'] if performance_data else 0,
                    evaluation_timestamp=datetime.utcnow(),
                    message=f"Insufficient data for {threshold.metric_name} evaluation (need {threshold.sample_size_minimum} samples)",
                    recommended_action=GateAction.CONTINUE,
                    metadata={'threshold_config': threshold.__dict__}
                )
            
            current_value = performance_data['value']
            sample_size = performance_data['sample_size']
            confidence = performance_data.get('confidence', 0.95)
            
            # Evaluate threshold
            status, recommended_action = self._evaluate_threshold(current_value, threshold)
            
            # Generate human-readable message
            message = self._generate_evaluation_message(
                threshold.metric_name, current_value, threshold, status
            )
            
            return GateEvaluation(
                gate_id=f"{experiment_id}_{variant_id}_{threshold.metric_name}",
                experiment_id=experiment_id,
                variant_id=variant_id,
                metric_name=threshold.metric_name,
                current_value=current_value,
                threshold_value=threshold.threshold_value,
                status=status,
                confidence_level=confidence,
                sample_size=sample_size,
                evaluation_timestamp=datetime.utcnow(),
                message=message,
                recommended_action=recommended_action,
                metadata={
                    'threshold_config': threshold.__dict__,
                    'performance_data': performance_data
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error evaluating gate {threshold.metric_name} for variant {variant_id}: {e}")
            return None
    
    def _evaluate_threshold(self, current_value: float, 
                          threshold: PerformanceThreshold) -> Tuple[GateStatus, GateAction]:
        """Evaluate if current value passes the threshold."""
        
        # Calculate warning threshold based on comparison operator
        if threshold.comparison_operator in ["lt", "lte"]:
            # For "less than" thresholds, warning occurs when we're close to exceeding
            # For example: threshold=500ms, warning_multiplier=0.8, warning at 400ms (500*0.8)
            warning_threshold = threshold.threshold_value * threshold.warning_multiplier
        else:
            # For "greater than" thresholds, warning occurs when we're below target  
            # For example: threshold=100 RPS, warning_multiplier=0.8, warning at 80 RPS (100*0.8)
            warning_threshold = threshold.threshold_value * threshold.warning_multiplier
        
        # Evaluate against main threshold
        passes_threshold = self._compare_values(
            current_value, threshold.threshold_value, threshold.comparison_operator
        )
        
        # Evaluate against warning threshold
        passes_warning = self._compare_values(
            current_value, warning_threshold, threshold.comparison_operator
        )
        
        # Determine status and action based on results
        if not passes_threshold:
            # Failed main threshold - take action based on metric severity
            if threshold.metric_name in ["error_rate", "latency_p99"]:
                return GateStatus.FAILED, GateAction.PAUSE_VARIANT
            elif threshold.metric_name in ["latency_p95", "memory_usage"]:
                return GateStatus.FAILED, GateAction.REDUCE_TRAFFIC
            else:
                return GateStatus.FAILED, GateAction.ALERT_ONLY
        elif passes_warning:
            # Passes both main and warning thresholds
            return GateStatus.PASSED, GateAction.CONTINUE
        else:
            # Passes main threshold but fails warning threshold  
            return GateStatus.WARNING, GateAction.ALERT_ONLY
    
    def _compare_values(self, current: float, threshold: float, operator: str) -> bool:
        """Compare current value against threshold using specified operator."""
        if operator == "lt":
            return current < threshold
        elif operator == "lte":
            return current <= threshold
        elif operator == "gt":
            return current > threshold
        elif operator == "gte":
            return current >= threshold
        elif operator == "eq":
            return abs(current - threshold) < 0.001  # Float equality with tolerance
        else:
            raise ValueError(f"Unknown comparison operator: {operator}")
    
    def _get_variant_performance_data(self, experiment_id: int, variant_id: int, 
                                    threshold: PerformanceThreshold) -> Optional[Dict[str, Any]]:
        """Get performance data for a variant within the specified time window."""
        try:
            time_cutoff = datetime.utcnow() - timedelta(minutes=threshold.time_window_minutes)
            
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Build query based on metric name and aggregation method
                    if threshold.metric_name == "error_rate":
                        cursor.execute("""
                            SELECT 
                                COUNT(CASE WHEN error_occurred THEN 1 END)::float / COUNT(*)::float as error_rate,
                                COUNT(*) as sample_size,
                                0.95 as confidence
                            FROM ab_performance_events
                            WHERE experiment_id = %s AND variant_id = %s 
                            AND timestamp >= %s
                        """, (experiment_id, variant_id, time_cutoff))
                        
                    elif threshold.metric_name.startswith("latency"):
                        percentile = 95 if "p95" in threshold.metric_name else 99
                        cursor.execute(f"""
                            SELECT 
                                PERCENTILE_CONT({percentile/100.0}) WITHIN GROUP (ORDER BY latency_ms) as latency,
                                COUNT(*) as sample_size,
                                0.95 as confidence
                            FROM ab_performance_events
                            WHERE experiment_id = %s AND variant_id = %s 
                            AND timestamp >= %s AND latency_ms IS NOT NULL
                        """, (experiment_id, variant_id, time_cutoff))
                        
                    elif threshold.metric_name == "memory_usage":
                        cursor.execute("""
                            SELECT 
                                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY memory_usage_mb) as memory_p95,
                                COUNT(*) as sample_size,
                                0.95 as confidence
                            FROM ab_performance_events
                            WHERE experiment_id = %s AND variant_id = %s 
                            AND timestamp >= %s AND memory_usage_mb IS NOT NULL
                        """, (experiment_id, variant_id, time_cutoff))
                        
                    elif threshold.metric_name == "requests_per_second":
                        cursor.execute("""
                            SELECT 
                                COUNT(*)::float / EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) as rps,
                                COUNT(*) as sample_size,
                                0.95 as confidence
                            FROM ab_performance_events
                            WHERE experiment_id = %s AND variant_id = %s 
                            AND timestamp >= %s
                        """, (experiment_id, variant_id, time_cutoff))
                        
                    else:
                        # Generic metric handling
                        cursor.execute("""
                            SELECT 
                                AVG(CAST(event_data->>'%s' AS NUMERIC)) as avg_value,
                                COUNT(*) as sample_size,
                                0.95 as confidence
                            FROM ab_performance_events
                            WHERE experiment_id = %s AND variant_id = %s 
                            AND timestamp >= %s AND event_data ? %s
                        """, (threshold.metric_name, experiment_id, variant_id, time_cutoff, threshold.metric_name))
                    
                    result = cursor.fetchone()
                    if result and result[0] is not None:
                        return {
                            'value': float(result[0]),
                            'sample_size': int(result[1]),
                            'confidence': float(result[2])
                        }
                    
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting performance data for variant {variant_id}: {e}")
            return None
    
    def _process_gate_evaluation(self, evaluation: GateEvaluation):
        """Process the results of a gate evaluation and take appropriate actions."""
        try:
            # Store evaluation result
            self._store_gate_evaluation(evaluation)
            
            # Update Prometheus metrics
            self._update_gate_metrics(evaluation)
            
            # Take automated action
            if evaluation.recommended_action != GateAction.CONTINUE:
                self._execute_gate_action(evaluation)
                
        except Exception as e:
            self.logger.error(f"Error processing gate evaluation {evaluation.gate_id}: {e}")
    
    def _execute_gate_action(self, evaluation: GateEvaluation):
        """Execute the recommended action for a failed gate."""
        try:
            action = evaluation.recommended_action
            
            if action == GateAction.PAUSE_VARIANT:
                self._pause_variant(evaluation.experiment_id, evaluation.variant_id, evaluation)
                
            elif action == GateAction.STOP_EXPERIMENT:
                self._stop_experiment(evaluation.experiment_id, evaluation)
                
            elif action == GateAction.REDUCE_TRAFFIC:
                self._reduce_variant_traffic(evaluation.experiment_id, evaluation.variant_id, evaluation)
                
            elif action == GateAction.ALERT_ONLY:
                self._send_performance_alert(evaluation)
                
            # Log the action taken
            self.logger.warning(
                f"Performance gate action executed: {action.value} for experiment {evaluation.experiment_id}, "
                f"variant {evaluation.variant_id}, metric {evaluation.metric_name}"
            )
            
        except Exception as e:
            self.logger.error(f"Error executing gate action {evaluation.recommended_action}: {e}")
    
    def _pause_variant(self, experiment_id: int, variant_id: int, evaluation: GateEvaluation):
        """Pause a variant that failed performance gates."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Update variant to paused status
                    cursor.execute("""
                        UPDATE ab_variants 
                        SET traffic_allocation = 0,
                            algorithm_config = algorithm_config || %s
                        WHERE id = %s AND experiment_id = %s
                    """, (
                        json.dumps({
                            'paused_by_performance_gate': True,
                            'paused_at': datetime.utcnow().isoformat(),
                            'gate_evaluation_id': evaluation.gate_id,
                            'failure_reason': evaluation.message
                        }),
                        variant_id, experiment_id
                    ))
                    
                    # Log the pausing event
                    cursor.execute("""
                        INSERT INTO ab_experiment_results 
                        (experiment_id, variant_id, user_id, event_type, event_data, timestamp)
                        VALUES (%s, %s, 'system', 'variant_paused_by_gate', %s, NOW())
                    """, (
                        experiment_id, variant_id,
                        json.dumps({
                            'gate_id': evaluation.gate_id,
                            'metric_name': evaluation.metric_name,
                            'current_value': evaluation.current_value,
                            'threshold_value': evaluation.threshold_value,
                            'message': evaluation.message
                        })
                    ))
                    
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Error pausing variant {variant_id}: {e}")
    
    def _reduce_variant_traffic(self, experiment_id: int, variant_id: int, evaluation: GateEvaluation):
        """Reduce traffic allocation for a variant that failed performance gates."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Reduce traffic by 50%
                    cursor.execute("""
                        UPDATE ab_variants 
                        SET traffic_allocation = traffic_allocation * 0.5,
                            algorithm_config = algorithm_config || %s
                        WHERE id = %s AND experiment_id = %s
                    """, (
                        json.dumps({
                            'traffic_reduced_by_performance_gate': True,
                            'reduced_at': datetime.utcnow().isoformat(),
                            'gate_evaluation_id': evaluation.gate_id,
                            'reduction_reason': evaluation.message
                        }),
                        variant_id, experiment_id
                    ))
                    
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Error reducing traffic for variant {variant_id}: {e}")
    
    def _stop_experiment(self, experiment_id: int, evaluation: GateEvaluation):
        """Stop an entire experiment due to critical performance issues."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        UPDATE ab_experiments 
                        SET status = 'stopped', end_date = NOW()
                        WHERE id = %s
                    """, (experiment_id,))
                    
                    # Log the stopping event
                    cursor.execute("""
                        INSERT INTO ab_experiment_results 
                        (experiment_id, variant_id, user_id, event_type, event_data, timestamp)
                        VALUES (%s, %s, 'system', 'experiment_stopped_by_gate', %s, NOW())
                    """, (
                        experiment_id, evaluation.variant_id,
                        json.dumps({
                            'gate_id': evaluation.gate_id,
                            'metric_name': evaluation.metric_name,
                            'current_value': evaluation.current_value,
                            'threshold_value': evaluation.threshold_value,
                            'message': evaluation.message
                        })
                    ))
                    
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Error stopping experiment {experiment_id}: {e}")
    
    def _send_performance_alert(self, evaluation: GateEvaluation):
        """Send performance alert for gate failures."""
        try:
            alert_data = {
                'alert_type': 'performance_gate_failure',
                'experiment_id': evaluation.experiment_id,
                'variant_id': evaluation.variant_id,
                'metric_name': evaluation.metric_name,
                'current_value': evaluation.current_value,
                'threshold_value': evaluation.threshold_value,
                'status': evaluation.status.value,
                'message': evaluation.message,
                'timestamp': evaluation.evaluation_timestamp.isoformat()
            }
            
            # Store alert in database
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        INSERT INTO ab_experiment_results 
                        (experiment_id, variant_id, user_id, event_type, event_data, timestamp)
                        VALUES (%s, %s, 'system', 'performance_alert', %s, NOW())
                    """, (
                        evaluation.experiment_id, evaluation.variant_id,
                        json.dumps(alert_data)
                    ))
                    conn.commit()
                    
            # Update Prometheus alert metrics
            prometheus_metrics.performance_gate_alerts_total.labels(
                experiment_id=evaluation.experiment_id,
                variant_id=evaluation.variant_id,
                metric_name=evaluation.metric_name,
                status=evaluation.status.value
            ).inc()
            
        except Exception as e:
            self.logger.error(f"Error sending performance alert: {e}")
    
    def _store_gate_evaluation(self, evaluation: GateEvaluation):
        """Store gate evaluation result in database."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        INSERT INTO performance_gate_evaluations 
                        (gate_id, experiment_id, variant_id, metric_name, current_value,
                         threshold_value, status, confidence_level, sample_size,
                         evaluation_timestamp, message, recommended_action, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        evaluation.gate_id,
                        evaluation.experiment_id,
                        evaluation.variant_id,
                        evaluation.metric_name,
                        evaluation.current_value,
                        evaluation.threshold_value,
                        evaluation.status.value,
                        evaluation.confidence_level,
                        evaluation.sample_size,
                        evaluation.evaluation_timestamp,
                        evaluation.message,
                        evaluation.recommended_action.value,
                        json.dumps(evaluation.metadata)
                    ))
                    conn.commit()
                    
        except Exception as e:
            # Table might not exist yet - this is expected during initial implementation
            self.logger.debug(f"Could not store gate evaluation (table may not exist): {e}")
    
    def _update_gate_metrics(self, evaluation: GateEvaluation):
        """Update Prometheus metrics for gate evaluation."""
        try:
            # Gate evaluation result
            prometheus_metrics.performance_gate_evaluations_total.labels(
                experiment_id=evaluation.experiment_id,
                variant_id=evaluation.variant_id,
                metric_name=evaluation.metric_name,
                status=evaluation.status.value
            ).inc()
            
            # Current metric value
            prometheus_metrics.performance_gate_current_value.labels(
                experiment_id=evaluation.experiment_id,
                variant_id=evaluation.variant_id,
                metric_name=evaluation.metric_name
            ).set(evaluation.current_value)
            
        except Exception as e:
            self.logger.error(f"Error updating gate metrics: {e}")
    
    def _generate_evaluation_message(self, metric_name: str, current_value: float,
                                   threshold: PerformanceThreshold, status: GateStatus) -> str:
        """Generate human-readable evaluation message."""
        
        if metric_name.startswith("latency"):
            current_str = f"{current_value:.1f}ms"
            threshold_str = f"{threshold.threshold_value:.1f}ms"
        elif metric_name == "error_rate":
            current_str = f"{current_value * 100:.2f}%"
            threshold_str = f"{threshold.threshold_value * 100:.2f}%"
        elif metric_name == "memory_usage":
            current_str = f"{current_value:.1f}MB"
            threshold_str = f"{threshold.threshold_value:.1f}MB"
        elif metric_name == "requests_per_second":
            current_str = f"{current_value:.1f} req/s"
            threshold_str = f"{threshold.threshold_value:.1f} req/s"
        else:
            current_str = f"{current_value:.2f}"
            threshold_str = f"{threshold.threshold_value:.2f}"
        
        if status == GateStatus.PASSED:
            return f"{metric_name} is within acceptable limits: {current_str} (threshold: {threshold_str})"
        elif status == GateStatus.WARNING:
            return f"{metric_name} approaching threshold: {current_str} (threshold: {threshold_str})"
        elif status == GateStatus.FAILED:
            return f"{metric_name} exceeded threshold: {current_str} > {threshold_str}"
        elif status == GateStatus.PENDING:
            return f"{metric_name} evaluation pending: insufficient data"
        else:
            return f"{metric_name} evaluation disabled"
    
    def configure_experiment_gates(self, experiment_id: int, 
                                 thresholds: List[PerformanceThreshold]) -> bool:
        """Configure performance gates for a specific experiment."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Store experiment-specific gate configuration
                    for threshold in thresholds:
                        cursor.execute("""
                            INSERT INTO experiment_performance_gates 
                            (experiment_id, metric_name, threshold_value, comparison_operator,
                             warning_multiplier, aggregation_method, sample_size_minimum,
                             time_window_minutes, enabled)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (experiment_id, metric_name) 
                            DO UPDATE SET
                                threshold_value = EXCLUDED.threshold_value,
                                comparison_operator = EXCLUDED.comparison_operator,
                                warning_multiplier = EXCLUDED.warning_multiplier,
                                aggregation_method = EXCLUDED.aggregation_method,
                                sample_size_minimum = EXCLUDED.sample_size_minimum,
                                time_window_minutes = EXCLUDED.time_window_minutes,
                                enabled = EXCLUDED.enabled
                        """, (
                            experiment_id,
                            threshold.metric_name,
                            threshold.threshold_value,
                            threshold.comparison_operator,
                            threshold.warning_multiplier,
                            threshold.aggregation_method,
                            threshold.sample_size_minimum,
                            threshold.time_window_minutes,
                            threshold.enabled
                        ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            self.logger.error(f"Error configuring gates for experiment {experiment_id}: {e}")
            return False
    
    # Helper methods for database queries
    
    def _get_experiment_config(self, experiment_id: int) -> Optional[Dict[str, Any]]:
        """Get experiment configuration."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT id, name, status, traffic_percentage, start_date, end_date
                        FROM ab_experiments 
                        WHERE id = %s
                    """, (experiment_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'id': row[0],
                            'name': row[1],
                            'status': row[2],
                            'traffic_percentage': float(row[3]),
                            'start_date': row[4],
                            'end_date': row[5]
                        }
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting experiment config {experiment_id}: {e}")
            return None
    
    def _get_experiment_variant_ids(self, experiment_id: int) -> List[int]:
        """Get all variant IDs for an experiment."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT id FROM ab_variants 
                        WHERE experiment_id = %s
                    """, (experiment_id,))
                    
                    return [row[0] for row in cursor.fetchall()]
                    
        except Exception as e:
            self.logger.error(f"Error getting variant IDs for experiment {experiment_id}: {e}")
            return []
    
    def _get_experiment_gates_config(self, experiment_id: int) -> List[PerformanceThreshold]:
        """Get performance gates configuration for an experiment."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT metric_name, threshold_value, comparison_operator,
                               warning_multiplier, aggregation_method, sample_size_minimum,
                               time_window_minutes, enabled
                        FROM experiment_performance_gates 
                        WHERE experiment_id = %s
                    """, (experiment_id,))
                    
                    gates = []
                    for row in cursor.fetchall():
                        gates.append(PerformanceThreshold(
                            metric_name=row[0],
                            threshold_value=float(row[1]),
                            comparison_operator=row[2],
                            warning_multiplier=float(row[3]),
                            aggregation_method=row[4],
                            sample_size_minimum=int(row[5]),
                            time_window_minutes=int(row[6]),
                            enabled=bool(row[7])
                        ))
                    
                    # If no experiment-specific gates, use defaults
                    if not gates:
                        gates = list(self._default_thresholds.values())
                    
                    return gates
                    
        except Exception as e:
            # If table doesn't exist, use default gates
            self.logger.debug(f"Using default gates for experiment {experiment_id}: {e}")
            return list(self._default_thresholds.values())


# Global performance gates engine instance
performance_gates = PerformanceGatesEngine()


def evaluate_experiment_performance_gates(experiment_id: int, 
                                        variant_ids: Optional[List[int]] = None) -> List[GateEvaluation]:
    """
    Convenience function to evaluate performance gates for an experiment.
    
    Args:
        experiment_id: ID of the experiment to evaluate
        variant_ids: Optional list of variant IDs to evaluate
        
    Returns:
        List of gate evaluation results
    """
    return performance_gates.evaluate_experiment_gates(experiment_id, variant_ids)


def configure_experiment_performance_gates(experiment_id: int, 
                                         thresholds: List[PerformanceThreshold]) -> bool:
    """
    Convenience function to configure performance gates for an experiment.
    
    Args:
        experiment_id: ID of the experiment
        thresholds: List of performance thresholds to configure
        
    Returns:
        True if configuration was successful
    """
    return performance_gates.configure_experiment_gates(experiment_id, thresholds) 