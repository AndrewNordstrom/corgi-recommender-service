"""
A/B Testing Framework - Core Module

This module provides the foundational A/B testing functionality for the Corgi
Recommender Service, enabling systematic algorithm variant testing with
integrated quality metrics collection and statistical analysis.

TODO #28: Implement A/B testing framework for algorithm variations
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from db.connection import get_db_connection, get_cursor
import utils.metrics as metrics
from utils.ab_performance import performance_tracker
from utils.performance_gates import (
    performance_gates,
    evaluate_experiment_performance_gates,
    GateStatus
)

logger = logging.getLogger(__name__)

class ABTestingEngine:
    """Core A/B testing engine for managing experiments and user assignments."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def assign_user_to_variant(self, user_id: str, experiment_id: int) -> Optional[int]:
        """
        Deterministic user assignment to experiment variant using consistent hashing.
        
        Ensures users always get the same variant for the duration of an experiment,
        providing consistent experience and valid statistical analysis.
        
        Args:
            user_id: Unique identifier for the user
            experiment_id: ID of the experiment to assign for
            
        Returns:
            variant_id if user should be included in experiment, None if excluded
        """
        try:
            # Get experiment configuration
            experiment = self.get_experiment(experiment_id)
            if not experiment or experiment['status'] != 'active':
                return None
            
            # Check if user is eligible for this experiment
            if not self._is_user_eligible(user_id, experiment):
                return None
            
            # Check if user is already assigned
            existing_assignment = self.get_user_assignment(user_id, experiment_id)
            if existing_assignment:
                return existing_assignment['variant_id']
            
            # Create deterministic assignment using consistent hashing
            hash_input = f"{user_id}_{experiment_id}"
            hash_value = hashlib.md5(hash_input.encode()).hexdigest()
            numeric_hash = int(hash_value[:8], 16) % 100
            
            # Apply traffic percentage filter
            if numeric_hash >= experiment['traffic_percentage']:
                return None  # User not in experiment traffic
            
            # Map to variant based on traffic allocation percentages
            variants = self.get_experiment_variants(experiment_id)
            cumulative_allocation = 0
            
            for variant in variants:
                cumulative_allocation += float(variant['traffic_allocation'])
                if numeric_hash < cumulative_allocation:
                    # Check performance gates before assignment
                    if not self._check_performance_gates(experiment_id, variant['id']):
                        self.logger.info(f"Assignment blocked by performance gates for experiment {experiment_id}, variant {variant['id']}")
                        return None  # Block assignment due to performance issues
                    
                    # Store assignment in database
                    self._store_user_assignment(user_id, experiment_id, variant['id'])
                    
                    # Track assignment event
                    self.track_experiment_event(
                        experiment_id=experiment_id,
                        variant_id=variant['id'],
                        user_id=user_id,
                        event_type='user_assignment',
                        event_data={'assignment_method': 'consistent_hashing'}
                    )
                    
                    return variant['id']
            
            # Fallback to control variant if traffic allocation doesn't sum to 100
            control_variant = next((v for v in variants if v['is_control']), variants[0])
            
            # Check performance gates for control variant
            if not self._check_performance_gates(experiment_id, control_variant['id']):
                self.logger.info(f"Control variant assignment blocked by performance gates for experiment {experiment_id}")
                return None
            
            self._store_user_assignment(user_id, experiment_id, control_variant['id'])
            return control_variant['id']
            
        except Exception as e:
            self.logger.error(f"Error assigning user {user_id} to experiment {experiment_id}: {e}")
            return None
    
    def get_active_experiments_for_user(self, user_id: str) -> List[Dict]:
        """Get all active experiments that this user could participate in."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT id, name, traffic_percentage, targeting_rules, exclusion_rules
                        FROM ab_experiments 
                        WHERE status = 'active' 
                        AND (start_date IS NULL OR start_date <= NOW())
                        AND (end_date IS NULL OR end_date >= NOW())
                        ORDER BY created_at
                    """)
                    
                    experiments = []
                    for row in cursor.fetchall():
                        experiment = {
                            'id': row[0],
                            'name': row[1],
                            'traffic_percentage': float(row[2]),
                            'targeting_rules': row[3],
                            'exclusion_rules': row[4]
                        }
                        
                        if self._is_user_eligible(user_id, experiment):
                            experiments.append(experiment)
                    
                    return experiments
                    
        except Exception as e:
            self.logger.error(f"Error getting active experiments for user {user_id}: {e}")
            return []
    
    def get_user_assignments(self, user_id: str, experiment_ids: List[int] = None) -> Dict[int, int]:
        """Get user's current variant assignments for specified experiments."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    if experiment_ids:
                        placeholders = ','.join(['%s'] * len(experiment_ids))
                        cursor.execute(f"""
                            SELECT experiment_id, variant_id 
                            FROM ab_user_assignments 
                            WHERE user_id = %s AND experiment_id IN ({placeholders})
                        """, [user_id] + experiment_ids)
                    else:
                        cursor.execute("""
                            SELECT experiment_id, variant_id 
                            FROM ab_user_assignments 
                            WHERE user_id = %s
                        """, (user_id,))
                    
                    return {row[0]: row[1] for row in cursor.fetchall()}
                    
        except Exception as e:
            self.logger.error(f"Error getting user assignments for {user_id}: {e}")
            return {}
    
    def track_experiment_event(self, experiment_id: int, variant_id: int, user_id: str, 
                             event_type: str, event_data: Dict = None, 
                             quality_metrics_id: int = None, request_id: str = None):
        """Track an event for A/B testing analysis."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        INSERT INTO ab_experiment_results 
                        (experiment_id, variant_id, user_id, event_type, event_data, 
                         quality_metrics_id, request_id, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        experiment_id, variant_id, user_id, event_type,
                        json.dumps(event_data) if event_data else None,
                        quality_metrics_id, request_id
                    ))
                    conn.commit()
                    
                    # Update Prometheus metrics
                    metrics.ab_test_events_total.labels(
                        experiment_id=experiment_id,
                        variant_id=variant_id,
                        event_type=event_type
                    ).inc()
                    
        except Exception as e:
            self.logger.error(f"Error tracking experiment event: {e}")
    
    def get_experiment(self, experiment_id: int) -> Optional[Dict]:
        """Get experiment configuration by ID."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT id, name, description, status, traffic_percentage,
                               start_date, end_date, targeting_rules, exclusion_rules,
                               minimum_sample_size, confidence_level
                        FROM ab_experiments 
                        WHERE id = %s
                    """, (experiment_id,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    return {
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'status': row[3],
                        'traffic_percentage': float(row[4]),
                        'start_date': row[5],
                        'end_date': row[6],
                        'targeting_rules': row[7],
                        'exclusion_rules': row[8],
                        'minimum_sample_size': row[9],
                        'confidence_level': float(row[10])
                    }
                    
        except Exception as e:
            self.logger.error(f"Error getting experiment {experiment_id}: {e}")
            return None
    
    def get_experiment_variants(self, experiment_id: int) -> List[Dict]:
        """Get all variants for an experiment."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT id, name, description, traffic_allocation, 
                               algorithm_config, is_control
                        FROM ab_variants 
                        WHERE experiment_id = %s
                        ORDER BY is_control DESC, created_at
                    """, (experiment_id,))
                    
                    variants = []
                    for row in cursor.fetchall():
                        variants.append({
                            'id': row[0],
                            'name': row[1],
                            'description': row[2],
                            'traffic_allocation': float(row[3]),
                            'algorithm_config': row[4],
                            'is_control': row[5]
                        })
                    
                    return variants
                    
        except Exception as e:
            self.logger.error(f"Error getting variants for experiment {experiment_id}: {e}")
            return []
    
    def get_user_assignment(self, user_id: str, experiment_id: int) -> Optional[Dict]:
        """Get existing user assignment for an experiment."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT variant_id, assignment_time
                        FROM ab_user_assignments 
                        WHERE user_id = %s AND experiment_id = %s
                    """, (user_id, experiment_id))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'variant_id': row[0],
                            'assignment_time': row[1]
                        }
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting user assignment for {user_id}, experiment {experiment_id}: {e}")
            return None
    
    def _is_user_eligible(self, user_id: str, experiment: Dict) -> bool:
        """Check if user is eligible for the experiment based on targeting rules."""
        try:
            # For now, implement basic eligibility (can be extended)
            # In production, this would check against user profiles, segments, etc.
            
            targeting_rules = experiment.get('targeting_rules', {})
            exclusion_rules = experiment.get('exclusion_rules', {})
            
            # Simple implementation - if no rules specified, user is eligible
            if not targeting_rules and not exclusion_rules:
                return True
            
            # TODO: Implement sophisticated targeting logic based on user attributes
            # This would integrate with user profile/segmentation system
            
            return True  # Default to eligible for now
            
        except Exception as e:
            self.logger.error(f"Error checking user eligibility: {e}")
            return False
    
    def _store_user_assignment(self, user_id: str, experiment_id: int, variant_id: int):
        """Store user assignment in database."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        INSERT INTO ab_user_assignments 
                        (user_id, experiment_id, variant_id, assignment_time)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (user_id, experiment_id) 
                        DO NOTHING
                    """, (user_id, experiment_id, variant_id))
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Error storing user assignment: {e}")

    def _check_performance_gates(self, experiment_id: int, variant_id: int = None) -> bool:
        """
        Check if performance gates allow new user assignments to variants.
        
        Args:
            experiment_id: ID of the experiment
            variant_id: Optional specific variant to check (if None, checks all variants)
            
        Returns:
            True if assignments are allowed, False if blocked by performance gates
        """
        try:
            # Get recent performance gate evaluations
            evaluations = evaluate_experiment_performance_gates(experiment_id, [variant_id] if variant_id else None)
            
            # Check if any gates are in failed status for this variant
            failed_gates = [
                e for e in evaluations 
                if e.status == GateStatus.FAILED and (variant_id is None or e.variant_id == variant_id)
            ]
            
            if failed_gates:
                self.logger.warning(
                    f"Performance gates blocking assignment to experiment {experiment_id}, "
                    f"variant {variant_id}: {[g.metric_name for g in failed_gates]}"
                )
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking performance gates: {e}")
            # On error, allow assignment (fail open to avoid blocking users)
            return True


class ABTestingMiddleware:
    """Middleware to integrate A/B testing with recommendation requests."""
    
    def __init__(self):
        self.ab_engine = ABTestingEngine()
        self.logger = logging.getLogger(__name__)
    
    def process_recommendation_request(self, user_id: str, request_params: Dict) -> Dict:
        """
        Process recommendation request through A/B testing framework.
        
        Args:
            user_id: User making the request
            request_params: Original request parameters
            
        Returns:
            Modified request parameters with A/B test configurations applied
        """
        try:
            # Get active experiments for this user
            active_experiments = self.ab_engine.get_active_experiments_for_user(user_id)
            
            # Process each experiment
            for experiment in active_experiments:
                experiment_id = experiment['id']
                
                # Get or assign user to variant
                variant_id = self.ab_engine.assign_user_to_variant(user_id, experiment_id)
                
                if variant_id:
                    # Get variant configuration
                    variants = self.ab_engine.get_experiment_variants(experiment_id)
                    variant = next((v for v in variants if v['id'] == variant_id), None)
                    
                    if variant and variant['algorithm_config']:
                        # Apply algorithm configuration from variant
                        self._apply_variant_config(request_params, variant['algorithm_config'])
                        
                        # Track recommendation request event
                        self.ab_engine.track_experiment_event(
                            experiment_id=experiment_id,
                            variant_id=variant_id,
                            user_id=user_id,
                            event_type='recommendation_request',
                            event_data={
                                'original_params': request_params.copy(),
                                'variant_name': variant['name']
                            }
                        )
                        
                        # Store experiment context for performance tracking
                        request_params['_ab_experiment_context'] = {
                            'experiment_id': experiment_id,
                            'variant_id': variant_id,
                            'user_id': user_id,
                            'variant_name': variant['name']
                        }
            
            return request_params
            
        except Exception as e:
            self.logger.error(f"Error processing A/B testing for user {user_id}: {e}")
            return request_params  # Return original params on error
    
    def _apply_variant_config(self, request_params: Dict, variant_config: Dict):
        """Apply variant-specific algorithm configuration to request parameters."""
        try:
            # Apply ranking weight modifications
            if 'ranking_weights' in variant_config:
                request_params['ranking_weights'] = variant_config['ranking_weights']
            
            # Apply cold start threshold modifications
            if 'cold_start_threshold' in variant_config:
                request_params['cold_start_threshold'] = variant_config['cold_start_threshold']
            
            # Apply other algorithm parameters
            for key, value in variant_config.items():
                if key not in ['ranking_weights', 'cold_start_threshold']:
                    request_params[key] = value
                    
        except Exception as e:
            self.logger.error(f"Error applying variant config: {e}")
    
    def track_recommendation_performance(self, user_id: str, request_params: Dict, 
                                       performance_metrics: Dict):
        """
        Track performance metrics for A/B test variants.
        
        Args:
            user_id: User who made the request
            request_params: Request parameters (may contain A/B test context)
            performance_metrics: Performance data to record
        """
        try:
            ab_context = request_params.get('_ab_experiment_context')
            if not ab_context:
                return  # No A/B test context, skip performance tracking
                
            # Record performance event
            performance_tracker._record_performance_event_direct(
                experiment_id=ab_context['experiment_id'],
                variant_id=ab_context['variant_id'],
                user_id=user_id,
                performance_metrics=performance_metrics
            )
                
        except Exception as e:
            self.logger.error(f"Error tracking recommendation performance: {e}")


# Global instances for use throughout the application
ab_testing_engine = ABTestingEngine()
ab_testing_middleware = ABTestingMiddleware() 