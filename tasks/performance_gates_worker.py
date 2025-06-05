"""
Performance Gates Worker

This worker automatically evaluates performance gates for active A/B testing experiments.
It runs continuously in the background and takes automated actions when thresholds are breached.

TODO #27g: Integrate performance gates into A/B testing workflow
"""

import logging
import time
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import threading

from db.connection import get_db_connection, get_cursor
from utils.performance_gates import performance_gates
from utils.ab_testing import ABTestingEngine
import utils.metrics as prometheus_metrics

logger = logging.getLogger(__name__)

class PerformanceGatesWorker:
    """
    Background worker that continuously monitors and evaluates performance gates
    for active A/B testing experiments.
    """
    
    def __init__(self, evaluation_interval_seconds: int = 300):  # 5 minutes default
        self.evaluation_interval = evaluation_interval_seconds
        self.running = False
        self.worker_thread = None
        self.ab_testing_engine = ABTestingEngine()
        
        # Configure signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()
        
    def start(self):
        """Start the performance gates worker."""
        if self.running:
            logger.warning("Performance gates worker is already running")
            return
            
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info(f"Performance gates worker started with {self.evaluation_interval}s interval")
        
    def stop(self):
        """Stop the performance gates worker."""
        if not self.running:
            return
            
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
            
        logger.info("Performance gates worker stopped")
        
    def _worker_loop(self):
        """Main worker loop that evaluates performance gates."""
        logger.info("Performance gates worker loop started")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Get active experiments
                active_experiments = self._get_active_experiments()
                
                if active_experiments:
                    logger.debug(f"Evaluating performance gates for {len(active_experiments)} active experiments")
                    
                    # Evaluate performance gates for each active experiment
                    for experiment in active_experiments:
                        if not self.running:  # Check for shutdown
                            break
                            
                        self._evaluate_experiment_gates(experiment)
                else:
                    logger.debug("No active experiments found for gate evaluation")
                
                # Update worker health metrics
                self._update_worker_metrics(start_time)
                
                # Sleep until next evaluation (or stop if shutting down)
                elapsed = time.time() - start_time
                sleep_time = max(0, self.evaluation_interval - elapsed)
                
                if sleep_time > 0 and self.running:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Error in performance gates worker loop: {e}")
                if self.running:
                    time.sleep(60)  # Wait before retrying on error
                    
        logger.info("Performance gates worker loop ended")
        
    def _get_active_experiments(self) -> List[Dict]:
        """Get list of active A/B testing experiments."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT id, name, status, traffic_percentage, start_date
                        FROM ab_experiments 
                        WHERE status = 'running'
                        AND start_date <= NOW()
                        AND (end_date IS NULL OR end_date > NOW())
                        ORDER BY start_date DESC
                    """)
                    
                    experiments = []
                    for row in cursor.fetchall():
                        experiments.append({
                            'id': row[0],
                            'name': row[1],
                            'status': row[2],
                            'traffic_percentage': float(row[3]),
                            'start_date': row[4]
                        })
                    
                    return experiments
                    
        except Exception as e:
            logger.error(f"Error getting active experiments: {e}")
            return []
    
    def _evaluate_experiment_gates(self, experiment: Dict):
        """Evaluate performance gates for a single experiment."""
        experiment_id = experiment['id']
        
        try:
            start_time = time.time()
            
            # Evaluate performance gates
            evaluations = performance_gates.evaluate_experiment_gates(experiment_id)
            
            # Track evaluation metrics
            evaluation_duration = time.time() - start_time
            prometheus_metrics.performance_gate_evaluation_duration.labels(
                experiment_id=experiment_id
            ).observe(evaluation_duration)
            
            # Log evaluation results
            if evaluations:
                failed_gates = [e for e in evaluations if e.status.value == 'failed']
                warning_gates = [e for e in evaluations if e.status.value == 'warning']
                
                if failed_gates:
                    logger.warning(
                        f"Experiment {experiment_id} has {len(failed_gates)} failed performance gates: "
                        f"{[f'{e.metric_name}({e.variant_id})' for e in failed_gates]}"
                    )
                    
                if warning_gates:
                    logger.info(
                        f"Experiment {experiment_id} has {len(warning_gates)} warning performance gates: "
                        f"{[f'{e.metric_name}({e.variant_id})' for e in warning_gates]}"
                    )
                    
                logger.debug(
                    f"Evaluated {len(evaluations)} performance gates for experiment {experiment_id} "
                    f"in {evaluation_duration:.3f}s"
                )
            else:
                logger.debug(f"No performance gates configured for experiment {experiment_id}")
                
        except Exception as e:
            logger.error(f"Error evaluating gates for experiment {experiment_id}: {e}")
    
    def _update_worker_metrics(self, start_time: float):
        """Update Prometheus metrics for worker health."""
        try:
            # Worker execution time
            execution_time = time.time() - start_time
            
            # Update last execution timestamp
            prometheus_metrics.performance_gate_evaluation_duration.labels(
                experiment_id='worker'
            ).observe(execution_time)
            
        except Exception as e:
            logger.error(f"Error updating worker metrics: {e}")
    
    def evaluate_experiment_immediately(self, experiment_id: int) -> List:
        """Trigger immediate evaluation of performance gates for an experiment."""
        try:
            logger.info(f"Immediate evaluation requested for experiment {experiment_id}")
            return performance_gates.evaluate_experiment_gates(experiment_id)
            
        except Exception as e:
            logger.error(f"Error in immediate evaluation for experiment {experiment_id}: {e}")
            return []


# Global worker instance
performance_gates_worker = None


def start_performance_gates_worker(evaluation_interval_seconds: int = 300):
    """
    Start the performance gates worker with specified evaluation interval.
    
    Args:
        evaluation_interval_seconds: Seconds between evaluations (default: 300 = 5 minutes)
    """
    global performance_gates_worker
    
    performance_gates_worker = PerformanceGatesWorker(evaluation_interval_seconds)
    performance_gates_worker.start()
    
    return performance_gates_worker


def stop_performance_gates_worker():
    """Stop the performance gates worker."""
    global performance_gates_worker
    
    if performance_gates_worker:
        performance_gates_worker.stop()


def get_worker_status() -> Dict:
    """Get current status of the performance gates worker."""
    global performance_gates_worker
    
    if performance_gates_worker is None:
        return {'status': 'not_initialized'}
    
    return {
        'status': 'running' if performance_gates_worker.running else 'stopped',
        'evaluation_interval_seconds': performance_gates_worker.evaluation_interval,
        'thread_alive': performance_gates_worker.worker_thread.is_alive() if performance_gates_worker.worker_thread else False
    }


if __name__ == "__main__":
    """Run the performance gates worker as a standalone process."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Performance Gates Worker')
    parser.add_argument(
        '--interval', 
        type=int, 
        default=300,
        help='Evaluation interval in seconds (default: 300)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Log level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start worker
    worker = start_performance_gates_worker(args.interval)
    
    logger.info(f"Performance gates worker started with {args.interval}s interval")
    logger.info("Press Ctrl+C to stop the worker")
    
    try:
        # Keep main thread alive
        while worker.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    finally:
        stop_performance_gates_worker()
        logger.info("Performance gates worker shutdown complete") 