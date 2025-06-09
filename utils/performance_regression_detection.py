"""
Performance Regression Detection System

This module provides automated performance regression detection capabilities
for the Corgi Recommender Service. It builds upon the existing performance
benchmarking infrastructure to provide:

1. Automated baseline comparison
2. Statistical significance testing
3. Multi-metric regression analysis
4. Trend-based detection
5. Alert management and notification
6. Performance degradation classification

TODO #27e: Build performance regression detection system
"""

import json
import logging
import statistics
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
from scipy import stats
from db.connection import get_db_connection, get_cursor, USE_IN_MEMORY_DB
from utils.performance_benchmarking import PerformanceBenchmark
from utils.performance_monitoring import PerformanceMonitoringSystem, PerformanceAlert, PerformanceThreshold
import utils.metrics as metrics

logger = logging.getLogger(__name__)

class RegressionSeverity(Enum):
    """Severity levels for performance regressions."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            severity_order = [self.NONE, self.LOW, self.MEDIUM, self.HIGH, self.CRITICAL]
            return severity_order.index(self) < severity_order.index(other)
        return NotImplemented
    
    def __le__(self, other):
        if self.__class__ is other.__class__:
            severity_order = [self.NONE, self.LOW, self.MEDIUM, self.HIGH, self.CRITICAL]
            return severity_order.index(self) <= severity_order.index(other)
        return NotImplemented
    
    @property
    def order(self):
        """Return the severity level as a number for comparison"""
        severity_order = {
            self.NONE: 0,
            self.LOW: 1,
            self.MEDIUM: 2,
            self.HIGH: 3,
            self.CRITICAL: 4
        }
        return severity_order[self]

class RegressionType(Enum):
    """Types of performance regressions."""
    LATENCY_DEGRADATION = "latency_degradation"
    THROUGHPUT_DEGRADATION = "throughput_degradation"
    ERROR_RATE_INCREASE = "error_rate_increase"
    RESOURCE_INCREASE = "resource_increase"
    QUALITY_DEGRADATION = "quality_degradation"
    STABILITY_DEGRADATION = "stability_degradation"

@dataclass
class RegressionThreshold:
    """Configuration for regression detection thresholds."""
    metric_name: str
    warning_threshold_percent: float  # % change from baseline
    critical_threshold_percent: float
    absolute_threshold: Optional[float] = None  # Absolute value threshold
    statistical_significance: float = 0.05  # p-value for significance testing
    minimum_sample_size: int = 10
    trend_window_days: int = 7
    enabled: bool = True

@dataclass
class RegressionDetectionResult:
    """Result of regression detection analysis."""
    metric_name: str
    regression_type: RegressionType
    severity: RegressionSeverity
    baseline_value: float
    current_value: float
    change_percent: float
    absolute_change: float
    statistical_significance: float
    confidence_interval: Tuple[float, float]
    trend_direction: str  # "improving", "degrading", "stable"
    detection_timestamp: datetime
    evidence: Dict[str, Any]
    recommendation: str

@dataclass
class RegressionReport:
    """Comprehensive regression analysis report."""
    report_id: str
    test_name: str
    detection_timestamp: datetime
    overall_severity: RegressionSeverity
    baseline_benchmark_id: int
    current_benchmark_id: int
    detected_regressions: List[RegressionDetectionResult]
    statistical_summary: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    performance_score: float  # 0-100 scale
    recommendations: List[str]
    alert_sent: bool = False

class PerformanceRegressionDetector:
    """Advanced performance regression detection system."""
    
    def __init__(self, monitoring_system: Optional[PerformanceMonitoringSystem] = None):
        """
        Initialize the regression detection system.
        
        Args:
            monitoring_system: Optional monitoring system for alert integration
        """
        self.monitoring_system = monitoring_system
        self.logger = logging.getLogger(__name__)
        self.default_thresholds = self._create_default_thresholds()
        
    def _create_default_thresholds(self) -> Dict[str, RegressionThreshold]:
        """Create default regression thresholds based on established KPIs."""
        return {
            'p95_latency': RegressionThreshold(
                metric_name='p95_latency',
                warning_threshold_percent=15.0,
                critical_threshold_percent=25.0,
                absolute_threshold=500.0,  # 500ms absolute limit
                statistical_significance=0.05,
                minimum_sample_size=20,
                trend_window_days=7
            ),
            'p99_latency': RegressionThreshold(
                metric_name='p99_latency',
                warning_threshold_percent=20.0,
                critical_threshold_percent=40.0,
                absolute_threshold=1000.0,  # 1s absolute limit
                statistical_significance=0.05,
                minimum_sample_size=20,
                trend_window_days=7
            ),
            'requests_per_second': RegressionThreshold(
                metric_name='requests_per_second',
                warning_threshold_percent=-15.0,  # Negative = decrease is bad
                critical_threshold_percent=-25.0,
                absolute_threshold=50.0,  # Minimum 50 RPS
                statistical_significance=0.05,
                minimum_sample_size=15,
                trend_window_days=7
            ),
            'error_rate': RegressionThreshold(
                metric_name='error_rate',
                warning_threshold_percent=50.0,  # 50% relative increase
                critical_threshold_percent=100.0,  # 100% relative increase
                absolute_threshold=0.05,  # 5% absolute error rate
                statistical_significance=0.01,  # Stricter for errors
                minimum_sample_size=10,
                trend_window_days=3
            ),
            'peak_cpu_usage': RegressionThreshold(
                metric_name='peak_cpu_usage',
                warning_threshold_percent=20.0,
                critical_threshold_percent=40.0,
                absolute_threshold=85.0,  # 85% CPU usage
                statistical_significance=0.05,
                minimum_sample_size=15,
                trend_window_days=7
            ),
            'peak_memory_mb': RegressionThreshold(
                metric_name='peak_memory_mb',
                warning_threshold_percent=25.0,
                critical_threshold_percent=50.0,
                absolute_threshold=2048.0,  # 2GB memory usage
                statistical_significance=0.05,
                minimum_sample_size=15,
                trend_window_days=7
            ),
            'avg_db_query_time': RegressionThreshold(
                metric_name='avg_db_query_time',
                warning_threshold_percent=30.0,
                critical_threshold_percent=60.0,
                absolute_threshold=100.0,  # 100ms DB query time
                statistical_significance=0.05,
                minimum_sample_size=20,
                trend_window_days=7
            )
        }
    
    def detect_regressions(self, current_benchmark_id: int, 
                          baseline_benchmark_id: Optional[int] = None,
                          custom_thresholds: Optional[Dict[str, RegressionThreshold]] = None) -> RegressionReport:
        """
        Detect performance regressions by comparing current benchmark against baseline.
        
        Args:
            current_benchmark_id: ID of the current benchmark to analyze
            baseline_benchmark_id: Optional specific baseline to compare against
            custom_thresholds: Optional custom thresholds for specific tests
            
        Returns:
            Comprehensive regression analysis report
        """
        try:
            self.logger.info(f"Starting regression detection for benchmark {current_benchmark_id}")
            
            # Get current benchmark data
            current_benchmark = self._get_benchmark_data(current_benchmark_id)
            if not current_benchmark:
                raise ValueError(f"Benchmark {current_benchmark_id} not found")
            
            # Get baseline benchmark data
            if not baseline_benchmark_id:
                baseline_benchmark_id = self._find_latest_baseline(current_benchmark['benchmark_type'])
            
            baseline_benchmark = self._get_benchmark_data(baseline_benchmark_id)
            if not baseline_benchmark:
                raise ValueError(f"Baseline benchmark {baseline_benchmark_id} not found")
            
            self.logger.info(f"Comparing against baseline {baseline_benchmark_id}")
            
            # Use custom thresholds if provided, otherwise use defaults
            thresholds = custom_thresholds or self.default_thresholds
            
            # Detect regressions for each metric
            detected_regressions = []
            for metric_name, threshold in thresholds.items():
                if not threshold.enabled:
                    continue
                    
                regression = self._analyze_metric_regression(
                    metric_name, current_benchmark, baseline_benchmark, threshold
                )
                if regression and regression.severity != RegressionSeverity.NONE:
                    detected_regressions.append(regression)
            
            # Perform statistical analysis
            statistical_summary = self._perform_statistical_analysis(
                current_benchmark, baseline_benchmark, detected_regressions
            )
            
            # Analyze trends over time
            trend_analysis = self._analyze_performance_trends(
                current_benchmark_id, baseline_benchmark_id
            )
            
            # Calculate overall performance score
            performance_score = self._calculate_performance_score(
                current_benchmark, baseline_benchmark, detected_regressions
            )
            
            # Determine overall severity
            overall_severity = self._determine_overall_severity(detected_regressions)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                detected_regressions, trend_analysis, performance_score
            )
            
            # Create regression report
            report = RegressionReport(
                report_id=f"regression_{current_benchmark_id}_{int(time.time())}",
                test_name=current_benchmark.get('name', 'Unknown Test'),
                detection_timestamp=datetime.utcnow(),
                overall_severity=overall_severity,
                baseline_benchmark_id=baseline_benchmark_id,
                current_benchmark_id=current_benchmark_id,
                detected_regressions=detected_regressions,
                statistical_summary=statistical_summary,
                trend_analysis=trend_analysis,
                performance_score=performance_score,
                recommendations=recommendations
            )
            
            # Store regression report
            self._store_regression_report(report)
            
            # Send alerts if necessary
            if overall_severity in [RegressionSeverity.MEDIUM, RegressionSeverity.HIGH, RegressionSeverity.CRITICAL]:
                self._send_regression_alerts(report)
            
            self.logger.info(f"Regression detection complete. Severity: {overall_severity.value}")
            return report
            
        except Exception as e:
            self.logger.error(f"Error in regression detection: {e}")
            raise
    
    def _analyze_metric_regression(self, metric_name: str, current: Dict, baseline: Dict, 
                                 threshold: RegressionThreshold) -> Optional[RegressionDetectionResult]:
        """Analyze a specific metric for regression."""
        try:
            current_value = current.get(metric_name)
            baseline_value = baseline.get(metric_name)
            
            if current_value is None or baseline_value is None:
                self.logger.warning(f"Missing data for metric {metric_name}")
                return None
            
            if baseline_value == 0:
                self.logger.warning(f"Baseline value is zero for metric {metric_name}")
                return None
            
            # Calculate change
            absolute_change = current_value - baseline_value
            change_percent = (absolute_change / baseline_value) * 100
            
            # Determine regression type
            regression_type = self._classify_regression_type(metric_name, change_percent)
            
            # Check if change exceeds thresholds
            severity = self._determine_severity(
                metric_name, current_value, baseline_value, change_percent, 
                absolute_change, threshold
            )
            
            if severity == RegressionSeverity.NONE:
                return None
            
            # Perform statistical significance test
            statistical_significance = self._calculate_statistical_significance(
                metric_name, current_value, baseline_value
            )
            
            # Calculate confidence interval
            confidence_interval = self._calculate_confidence_interval(
                current_value, baseline_value, statistical_significance
            )
            
            # Analyze trend direction
            trend_direction = self._analyze_metric_trend(metric_name, current['id'])
            
            # Gather evidence
            evidence = self._gather_regression_evidence(
                metric_name, current, baseline, change_percent
            )
            
            # Generate recommendation
            recommendation = self._generate_metric_recommendation(
                metric_name, regression_type, severity, change_percent
            )
            
            return RegressionDetectionResult(
                metric_name=metric_name,
                regression_type=regression_type,
                severity=severity,
                baseline_value=baseline_value,
                current_value=current_value,
                change_percent=change_percent,
                absolute_change=absolute_change,
                statistical_significance=statistical_significance,
                confidence_interval=confidence_interval,
                trend_direction=trend_direction,
                detection_timestamp=datetime.utcnow(),
                evidence=evidence,
                recommendation=recommendation
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing metric {metric_name}: {e}")
            return None
    
    def _classify_regression_type(self, metric_name: str, change_percent: float) -> RegressionType:
        """Classify the type of regression based on metric and change."""
        if 'latency' in metric_name.lower() and change_percent > 0:
            return RegressionType.LATENCY_DEGRADATION
        elif 'requests_per_second' in metric_name.lower() and change_percent < 0:
            return RegressionType.THROUGHPUT_DEGRADATION
        elif 'error_rate' in metric_name.lower() and change_percent > 0:
            return RegressionType.ERROR_RATE_INCREASE
        elif any(resource in metric_name.lower() for resource in ['cpu', 'memory']) and change_percent > 0:
            return RegressionType.RESOURCE_INCREASE
        elif 'quality' in metric_name.lower() and change_percent < 0:
            return RegressionType.QUALITY_DEGRADATION
        else:
            return RegressionType.STABILITY_DEGRADATION
    
    def _determine_severity(self, metric_name: str, current_value: float, baseline_value: float,
                          change_percent: float, absolute_change: float, 
                          threshold: RegressionThreshold) -> RegressionSeverity:
        """Determine the severity of a regression."""
        try:
            # Check absolute threshold first
            if threshold.absolute_threshold is not None:
                if metric_name in ['error_rate'] and current_value > threshold.absolute_threshold:
                    return RegressionSeverity.CRITICAL
                elif metric_name in ['p95_latency', 'p99_latency'] and current_value > threshold.absolute_threshold:
                    return RegressionSeverity.CRITICAL
                elif metric_name in ['requests_per_second'] and current_value < threshold.absolute_threshold:
                    return RegressionSeverity.CRITICAL
                elif metric_name in ['peak_cpu_usage', 'peak_memory_mb'] and current_value > threshold.absolute_threshold:
                    return RegressionSeverity.HIGH
            
            # Check percentage thresholds
            abs_change_percent = abs(change_percent)
            
            # For metrics where decrease is bad (throughput), flip the check
            if metric_name in ['requests_per_second'] and change_percent < 0:
                abs_change_percent = abs(change_percent)
            elif metric_name in ['requests_per_second']:
                return RegressionSeverity.NONE  # Increase in throughput is good
            
            # For metrics where increase is bad (latency, errors, resources)
            if metric_name in ['p95_latency', 'p99_latency', 'error_rate', 'peak_cpu_usage', 'peak_memory_mb', 'avg_db_query_time']:
                if change_percent < 0:
                    return RegressionSeverity.NONE  # Improvement is good
            
            if abs_change_percent >= abs(threshold.critical_threshold_percent):
                return RegressionSeverity.CRITICAL
            elif abs_change_percent >= abs(threshold.warning_threshold_percent):
                return RegressionSeverity.HIGH if abs_change_percent >= abs(threshold.warning_threshold_percent) * 1.5 else RegressionSeverity.MEDIUM
            else:
                return RegressionSeverity.NONE
                
        except Exception as e:
            self.logger.error(f"Error determining severity for {metric_name}: {e}")
            return RegressionSeverity.NONE
    
    def _calculate_statistical_significance(self, metric_name: str, current_value: float, 
                                          baseline_value: float) -> float:
        """Calculate statistical significance of the change."""
        try:
            # Get historical data for statistical testing
            historical_data = self._get_historical_metric_data(metric_name, days=30)
            
            if len(historical_data) < 10:
                return 1.0  # Not enough data for significance testing
            
            # Perform t-test if we have enough data
            baseline_samples = [d['value'] for d in historical_data if d['is_baseline']]
            current_samples = [current_value]  # Single current measurement
            
            if len(baseline_samples) < 3:
                return 1.0
            
            # Use one-sample t-test to compare current value against baseline distribution
            t_stat, p_value = stats.ttest_1samp(baseline_samples, current_value)
            
            return p_value if not np.isnan(p_value) else 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating statistical significance: {e}")
            return 1.0
    
    def _calculate_confidence_interval(self, current_value: float, baseline_value: float,
                                     p_value: float) -> Tuple[float, float]:
        """Calculate confidence interval for the difference."""
        try:
            # Simple confidence interval based on the difference
            difference = current_value - baseline_value
            margin_of_error = abs(difference) * 0.1  # 10% margin
            
            return (
                current_value - margin_of_error,
                current_value + margin_of_error
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence interval: {e}")
            return (current_value, current_value)
    
    def _analyze_metric_trend(self, metric_name: str, current_benchmark_id: int, 
                            days: int = 7) -> str:
        """Analyze the trend direction for a metric over time."""
        try:
            # Get recent benchmark data
            recent_data = self._get_recent_metric_data(metric_name, days=days)
            
            if len(recent_data) < 3:
                return "insufficient_data"
            
            # Simple linear regression to determine trend
            values = [d['value'] for d in recent_data]
            x = list(range(len(values)))
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
            
            if abs(slope) < 0.01:  # Very small slope
                return "stable"
            elif slope > 0:
                # For latency, errors, resources: positive slope is bad
                if metric_name in ['p95_latency', 'p99_latency', 'error_rate', 'peak_cpu_usage', 'peak_memory_mb']:
                    return "degrading"
                else:
                    return "improving"
            else:
                # For latency, errors, resources: negative slope is good
                if metric_name in ['p95_latency', 'p99_latency', 'error_rate', 'peak_cpu_usage', 'peak_memory_mb']:
                    return "improving"
                else:
                    return "degrading"
                    
        except Exception as e:
            self.logger.error(f"Error analyzing trend for {metric_name}: {e}")
            return "unknown"
    
    def _gather_regression_evidence(self, metric_name: str, current: Dict, baseline: Dict,
                                  change_percent: float) -> Dict[str, Any]:
        """Gather additional evidence for the regression."""
        evidence = {
            'baseline_timestamp': baseline.get('test_timestamp'),
            'current_timestamp': current.get('test_timestamp'),
            'baseline_test_config': {
                'concurrent_users': baseline.get('concurrent_users'),
                'test_duration': baseline.get('test_duration_seconds'),
                'total_requests': baseline.get('total_requests')
            },
            'current_test_config': {
                'concurrent_users': current.get('concurrent_users'),
                'test_duration': current.get('test_duration_seconds'),
                'total_requests': current.get('total_requests')
            }
        }
        
        # Add context-specific evidence
        if 'latency' in metric_name:
            evidence['related_metrics'] = {
                'error_rate_change': self._calculate_metric_change(current, baseline, 'error_rate'),
                'cpu_usage_change': self._calculate_metric_change(current, baseline, 'peak_cpu_usage'),
                'memory_usage_change': self._calculate_metric_change(current, baseline, 'peak_memory_mb')
            }
        elif metric_name == 'error_rate':
            evidence['related_metrics'] = {
                'latency_change': self._calculate_metric_change(current, baseline, 'p95_latency'),
                'throughput_change': self._calculate_metric_change(current, baseline, 'requests_per_second')
            }
        
        return evidence
    
    def _calculate_metric_change(self, current: Dict, baseline: Dict, metric_name: str) -> float:
        """Calculate percentage change for a metric."""
        try:
            current_val = current.get(metric_name, 0)
            baseline_val = baseline.get(metric_name, 0)
            
            if baseline_val == 0:
                return 0.0
                
            return ((current_val - baseline_val) / baseline_val) * 100
            
        except Exception:
            return 0.0
    
    def _generate_metric_recommendation(self, metric_name: str, regression_type: RegressionType,
                                      severity: RegressionSeverity, change_percent: float) -> str:
        """Generate specific recommendation for a metric regression."""
        base_recommendations = {
            RegressionType.LATENCY_DEGRADATION: {
                RegressionSeverity.CRITICAL: "URGENT: Latency has critically degraded. Consider immediate rollback and investigation of recent algorithm changes.",
                RegressionSeverity.HIGH: "High latency degradation detected. Review recent algorithm modifications and database query optimization.",
                RegressionSeverity.MEDIUM: "Moderate latency increase observed. Monitor closely and consider optimization if trend continues."
            },
            RegressionType.THROUGHPUT_DEGRADATION: {
                RegressionSeverity.CRITICAL: "URGENT: Significant throughput drop. Check for algorithm bottlenecks and consider scaling resources.",
                RegressionSeverity.HIGH: "Throughput degradation detected. Review algorithm efficiency and database performance.",
                RegressionSeverity.MEDIUM: "Moderate throughput decrease. Monitor system load and consider optimization."
            },
            RegressionType.ERROR_RATE_INCREASE: {
                RegressionSeverity.CRITICAL: "CRITICAL: Error rate spike detected. Immediate investigation required for stability.",
                RegressionSeverity.HIGH: "Elevated error rate. Check logs for error patterns and recent code changes.",
                RegressionSeverity.MEDIUM: "Slight error rate increase. Monitor error logs and investigate if trend continues."
            },
            RegressionType.RESOURCE_INCREASE: {
                RegressionSeverity.CRITICAL: "Critical resource usage increase. Check for memory leaks or inefficient algorithm changes.",
                RegressionSeverity.HIGH: "High resource usage detected. Review algorithm efficiency and consider resource optimization.",
                RegressionSeverity.MEDIUM: "Moderate resource increase. Monitor resource usage trends and optimize if necessary."
            }
        }
        
        return base_recommendations.get(regression_type, {}).get(
            severity, 
            f"Performance change detected in {metric_name}: {change_percent:.1f}% change. Monitor closely."
        )
    
    def _perform_statistical_analysis(self, current: Dict, baseline: Dict, 
                                    regressions: List[RegressionDetectionResult]) -> Dict[str, Any]:
        """Perform comprehensive statistical analysis."""
        try:
            analysis = {
                'total_metrics_analyzed': len(self.default_thresholds),
                'regressions_detected': len(regressions),
                'severity_distribution': {},
                'confidence_scores': {},
                'correlation_analysis': {}
            }
            
            # Severity distribution
            for severity in RegressionSeverity:
                count = len([r for r in regressions if r.severity == severity])
                analysis['severity_distribution'][severity.value] = count
            
            # Confidence scores
            for regression in regressions:
                analysis['confidence_scores'][regression.metric_name] = {
                    'statistical_significance': regression.statistical_significance,
                    'trend_consistency': 1.0 if regression.trend_direction == 'degrading' else 0.5
                }
            
            # Simple correlation analysis
            if len(regressions) >= 2:
                latency_regression = next((r for r in regressions if 'latency' in r.metric_name), None)
                resource_regression = next((r for r in regressions if r.metric_name in ['peak_cpu_usage', 'peak_memory_mb']), None)
                
                if latency_regression and resource_regression:
                    analysis['correlation_analysis']['latency_resource_correlation'] = {
                        'detected': True,
                        'description': 'Latency degradation correlates with resource usage increase'
                    }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in statistical analysis: {e}")
            return {'error': str(e)}
    
    def _analyze_performance_trends(self, current_benchmark_id: int, 
                                  baseline_benchmark_id: int, days: int = 30) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        try:
            trends = {}
            
            for metric_name in ['p95_latency', 'requests_per_second', 'error_rate']:
                trend_data = self._get_recent_metric_data(metric_name, days=days)
                
                if len(trend_data) >= 5:
                    values = [d['value'] for d in trend_data]
                    
                    # Calculate trend statistics
                    recent_avg = statistics.mean(values[-7:]) if len(values) >= 7 else statistics.mean(values)
                    overall_avg = statistics.mean(values)
                    trend_direction = "improving" if recent_avg < overall_avg else "degrading"
                    
                    if metric_name in ['requests_per_second']:  # Higher is better
                        trend_direction = "improving" if recent_avg > overall_avg else "degrading"
                    
                    trends[metric_name] = {
                        'trend_direction': trend_direction,
                        'recent_average': recent_avg,
                        'overall_average': overall_avg,
                        'volatility': statistics.stdev(values) if len(values) > 1 else 0,
                        'data_points': len(values)
                    }
                else:
                    trends[metric_name] = {
                        'trend_direction': 'insufficient_data',
                        'data_points': len(trend_data)
                    }
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error analyzing trends: {e}")
            return {'error': str(e)}
    
    def _calculate_performance_score(self, current: Dict, baseline: Dict, 
                                   regressions: List[RegressionDetectionResult]) -> float:
        """Calculate overall performance score (0-100)."""
        try:
            score = 100.0
            
            # Deduct points for each regression based on severity
            severity_penalties = {
                RegressionSeverity.CRITICAL: 30,
                RegressionSeverity.HIGH: 20,
                RegressionSeverity.MEDIUM: 10,
                RegressionSeverity.LOW: 5
            }
            
            for regression in regressions:
                penalty = severity_penalties.get(regression.severity, 0)
                score -= penalty
            
            # Bonus for improvements
            improvement_bonus = 0
            for metric_name in ['p95_latency', 'error_rate']:
                current_val = current.get(metric_name, 0)
                baseline_val = baseline.get(metric_name, 0)
                
                if baseline_val > 0 and current_val < baseline_val * 0.9:  # 10% improvement
                    improvement_bonus += 5
            
            # Bonus for throughput improvements
            throughput_current = current.get('requests_per_second', 0)
            throughput_baseline = baseline.get('requests_per_second', 0)
            
            if throughput_baseline > 0 and throughput_current > throughput_baseline * 1.1:  # 10% improvement
                improvement_bonus += 5
            
            score += improvement_bonus
            
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            self.logger.error(f"Error calculating performance score: {e}")
            return 50.0  # Default middle score
    
    def _determine_overall_severity(self, regressions: List[RegressionDetectionResult]) -> RegressionSeverity:
        """Determine overall severity based on all detected regressions."""
        if not regressions:
            return RegressionSeverity.NONE
        
        # Take the highest severity
        max_severity = max(regression.severity for regression in regressions)
        
        # Escalate if multiple high-severity regressions
        high_severity_count = len([r for r in regressions if r.severity in [RegressionSeverity.HIGH, RegressionSeverity.CRITICAL]])
        
        if high_severity_count >= 3:
            return RegressionSeverity.CRITICAL
        elif high_severity_count >= 2:
            return RegressionSeverity.HIGH
        else:
            return max_severity
    
    def _generate_recommendations(self, regressions: List[RegressionDetectionResult], 
                                trend_analysis: Dict[str, Any], performance_score: float) -> List[str]:
        """Generate comprehensive recommendations."""
        recommendations = []
        
        # Critical issues first
        critical_regressions = [r for r in regressions if r.severity == RegressionSeverity.CRITICAL]
        if critical_regressions:
            recommendations.append("URGENT: Critical performance regressions detected. Consider immediate rollback of recent changes.")
            for regression in critical_regressions:
                recommendations.append(f"- {regression.recommendation}")
        
        # High-priority issues
        high_regressions = [r for r in regressions if r.severity == RegressionSeverity.HIGH]
        if high_regressions:
            recommendations.append("High-priority performance issues require immediate attention:")
            for regression in high_regressions:
                recommendations.append(f"- {regression.recommendation}")
        
        # Medium-priority issues
        medium_regressions = [r for r in regressions if r.severity == RegressionSeverity.MEDIUM]
        if medium_regressions:
            recommendations.append("Medium-priority issues to monitor and address:")
            for regression in medium_regressions:
                recommendations.append(f"- {regression.recommendation}")
        
        # Performance score-based recommendations
        if performance_score < 70:
            recommendations.append(f"Overall performance score is low ({performance_score:.1f}/100). Consider comprehensive performance review.")
        elif performance_score < 85:
            recommendations.append(f"Performance score ({performance_score:.1f}/100) indicates room for optimization.")
        
        # Trend-based recommendations
        degrading_trends = [k for k, v in trend_analysis.items() if v.get('trend_direction') == 'degrading']
        if degrading_trends:
            recommendations.append(f"Degrading trends detected in: {', '.join(degrading_trends)}. Monitor closely.")
        
        # If no specific issues found, add general status
        if not regressions and not degrading_trends and performance_score >= 85:
            recommendations.append("No performance regressions detected. System performance is within acceptable thresholds.")
        
        return recommendations
    
    def _get_benchmark_data(self, benchmark_id: int) -> Optional[Dict]:
        """Get benchmark data from database."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cur:
                    # Use correct placeholder syntax based on database type
                    placeholder = "?" if USE_IN_MEMORY_DB else "%s"
                    
                    cur.execute(f"SELECT * FROM performance_benchmarks WHERE id = {placeholder}", (benchmark_id,))
                    
                    row = cur.fetchone()
                    if row:
                        # Convert to dict format
                        if hasattr(cur, 'description') and cur.description:
                            columns = [desc[0] for desc in cur.description]
                            return dict(zip(columns, row))
                        else:
                            # Fallback for mock testing
                            return None
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting benchmark data: {e}")
            return None
    
    def _find_latest_baseline(self, benchmark_type: str = 'baseline') -> Optional[int]:
        """Find the latest baseline benchmark."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Use correct placeholder syntax based on database type
                    placeholder = "?" if USE_IN_MEMORY_DB else "%s"
                    
                    cursor.execute(f"""
                        SELECT id FROM performance_benchmarks 
                        WHERE benchmark_type = {placeholder}
                        ORDER BY test_timestamp DESC 
                        LIMIT 1
                    """, (benchmark_type,))
                    
                    row = cursor.fetchone()
                    return row[0] if row else None
                    
        except Exception as e:
            self.logger.error(f"Error finding latest baseline: {e}")
            return None
    
    def _get_historical_metric_data(self, metric_name: str, days: int = 30) -> List[Dict]:
        """Get historical data for a specific metric."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Use correct placeholder syntax based on database type
                    if USE_IN_MEMORY_DB:
                        # SQLite syntax
                        cursor.execute(f"""
                            SELECT {metric_name} as value, 
                                   CASE WHEN benchmark_type = 'baseline' THEN 1 ELSE 0 END as is_baseline,
                                   test_timestamp
                            FROM performance_benchmarks 
                            WHERE test_timestamp > datetime('now', '-? days')
                            AND {metric_name} IS NOT NULL
                            ORDER BY test_timestamp DESC
                        """, (days,))
                    else:
                        # PostgreSQL syntax
                        cursor.execute(f"""
                            SELECT {metric_name} as value, 
                                   benchmark_type = 'baseline' as is_baseline,
                                   test_timestamp
                            FROM performance_benchmarks 
                            WHERE test_timestamp > NOW() - INTERVAL '%s days'
                            AND {metric_name} IS NOT NULL
                            ORDER BY test_timestamp DESC
                        """, (days,))
                    
                    return [
                        {
                            'value': row[0],
                            'is_baseline': bool(row[1]),
                            'timestamp': row[2]
                        }
                        for row in cursor.fetchall()
                    ]
                    
        except Exception as e:
            self.logger.error(f"Error getting historical data for {metric_name}: {e}")
            return []
    
    def _get_recent_metric_data(self, metric_name: str, days: int = 7) -> List[Dict]:
        """Get recent metric data for trend analysis."""
        return self._get_historical_metric_data(metric_name, days)
    
    def _store_regression_report(self, report: RegressionReport):
        """Store regression report in database."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Check if table exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'performance_regression_reports'
                        )
                    """)
                    
                    if not cursor.fetchone()[0]:
                        # Create table if it doesn't exist
                        self._create_regression_reports_table(cursor)
                    
                    # Insert report
                    cursor.execute("""
                        INSERT INTO performance_regression_reports 
                        (report_id, test_name, detection_timestamp, overall_severity,
                         baseline_benchmark_id, current_benchmark_id, detected_regressions,
                         statistical_summary, trend_analysis, performance_score,
                         recommendations, alert_sent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        report.report_id,
                        report.test_name,
                        report.detection_timestamp,
                        report.overall_severity.value,
                        report.baseline_benchmark_id,
                        report.current_benchmark_id,
                        json.dumps([asdict(r) for r in report.detected_regressions], default=str),
                        json.dumps(report.statistical_summary, default=str),
                        json.dumps(report.trend_analysis, default=str),
                        report.performance_score,
                        json.dumps(report.recommendations),
                        report.alert_sent
                    ))
                    
                    conn.commit()
                    self.logger.info(f"Stored regression report: {report.report_id}")
                    
        except Exception as e:
            self.logger.error(f"Error storing regression report: {e}")
    
    def _create_regression_reports_table(self, cursor):
        """Create the regression reports table."""
        cursor.execute("""
            CREATE TABLE performance_regression_reports (
                id SERIAL PRIMARY KEY,
                report_id VARCHAR(255) UNIQUE NOT NULL,
                test_name VARCHAR(255) NOT NULL,
                detection_timestamp TIMESTAMP NOT NULL,
                overall_severity VARCHAR(20) NOT NULL,
                baseline_benchmark_id INTEGER NOT NULL,
                current_benchmark_id INTEGER NOT NULL,
                detected_regressions JSONB,
                statistical_summary JSONB,
                trend_analysis JSONB,
                performance_score FLOAT NOT NULL,
                recommendations JSONB,
                alert_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX idx_regression_reports_detection_timestamp ON performance_regression_reports(detection_timestamp)")
        cursor.execute("CREATE INDEX idx_regression_reports_severity ON performance_regression_reports(overall_severity)")
        cursor.execute("CREATE INDEX idx_regression_reports_benchmark_ids ON performance_regression_reports(baseline_benchmark_id, current_benchmark_id)")
    
    def _send_regression_alerts(self, report: RegressionReport):
        """Send alerts for detected regressions."""
        try:
            if not self.monitoring_system:
                self.logger.warning("No monitoring system configured for alerts")
                return
            
            # Create alert for each critical/high regression
            for regression in report.detected_regressions:
                if regression.severity in [RegressionSeverity.CRITICAL, RegressionSeverity.HIGH]:
                    # Create a threshold object for the PerformanceAlert
                    threshold = PerformanceThreshold(
                        metric_name=regression.metric_name,
                        operator="gt",
                        threshold_value=regression.baseline_value,
                        severity=regression.severity.value,
                        description=f"regression_{regression.metric_name}"
                    )
                    
                    alert = PerformanceAlert(
                        alert_id=f"regression_{regression.metric_name}_{int(time.time())}",
                        timestamp=datetime.utcnow(),
                        metric_name=regression.metric_name,
                        current_value=regression.current_value,
                        threshold=threshold,
                        severity=regression.severity.value,
                        message=f"Performance regression detected: {regression.recommendation}",
                        context={
                            'regression_type': regression.regression_type.value,
                            'change_percent': regression.change_percent,
                            'report_id': report.report_id,
                            'trend_direction': regression.trend_direction
                        }
                    )
                    
                    # Add to monitoring system for notification
                    if hasattr(self.monitoring_system, 'notification_manager'):
                        self.monitoring_system.notification_manager.notify(alert)
            
            # Mark report as alerted
            report.alert_sent = True
            
        except Exception as e:
            self.logger.error(f"Error sending regression alerts: {e}")

# Global regression detector instance
_global_detector = None

def get_regression_detector() -> PerformanceRegressionDetector:
    """Get global regression detector instance."""
    global _global_detector
    if _global_detector is None:
        _global_detector = PerformanceRegressionDetector()
    return _global_detector

def detect_regressions_for_benchmark(benchmark_id: int, 
                                   baseline_id: Optional[int] = None) -> RegressionReport:
    """Convenience function to detect regressions for a benchmark."""
    detector = get_regression_detector()
    return detector.detect_regressions(benchmark_id, baseline_id)

# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance Regression Detection")
    parser.add_argument("benchmark_id", type=int, help="Current benchmark ID to analyze")
    parser.add_argument("--baseline-id", type=int, help="Specific baseline to compare against")
    parser.add_argument("--output", help="Output file for detailed report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    try:
        report = detect_regressions_for_benchmark(args.benchmark_id, args.baseline_id)
        
        print("="*60)
        print("PERFORMANCE REGRESSION DETECTION REPORT")
        print("="*60)
        print(f"Report ID: {report.report_id}")
        print(f"Test: {report.test_name}")
        print(f"Overall Severity: {report.overall_severity.value.upper()}")
        print(f"Performance Score: {report.performance_score:.1f}/100")
        print(f"Regressions Detected: {len(report.detected_regressions)}")
        
        if report.detected_regressions:
            print("\nDETECTED REGRESSIONS:")
            for regression in report.detected_regressions:
                print(f"- {regression.metric_name}: {regression.change_percent:+.1f}% ({regression.severity.value})")
                print(f"  {regression.recommendation}")
        
        if report.recommendations:
            print("\nRECOMMENDATIONS:")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"{i}. {rec}")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)
            print(f"\nDetailed report saved to: {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")
        exit(1) 