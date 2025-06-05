"""
A/B Testing Automated Analysis and Recommendations Module

This module provides intelligent analysis capabilities for A/B testing experiments,
including statistical significance testing, effect size calculations, and automated
recommendations for experiment management decisions.

TODO #28j: Add automated experiment analysis and recommendations
"""

import logging
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import scipy.stats as stats
import json

from db.connection import get_db_connection, get_cursor

logger = logging.getLogger(__name__)

class RecommendationType(Enum):
    """Types of recommendations that can be generated."""
    CONTINUE_EXPERIMENT = "continue_experiment"
    STOP_WINNER_FOUND = "stop_winner_found"
    STOP_NO_EFFECT = "stop_no_effect"
    INCREASE_SAMPLE_SIZE = "increase_sample_size"
    EXTEND_DURATION = "extend_duration"
    INVESTIGATE_ANOMALY = "investigate_anomaly"
    OPTIMIZE_TRAFFIC = "optimize_traffic"
    SEGMENT_ANALYSIS = "segment_analysis"

class SignificanceLevel(Enum):
    """Statistical significance levels."""
    NOT_SIGNIFICANT = "not_significant"
    MARGINALLY_SIGNIFICANT = "marginally_significant"
    SIGNIFICANT = "significant"
    HIGHLY_SIGNIFICANT = "highly_significant"

@dataclass
class VariantAnalysis:
    """Analysis results for a single variant."""
    variant_id: int
    variant_name: str
    sample_size: int
    conversion_rate: float
    confidence_interval: Tuple[float, float]
    quality_scores: Dict[str, float]
    performance_metrics: Dict[str, float]
    statistical_power: float
    
@dataclass
class ComparisonResult:
    """Results of comparing two variants."""
    variant_a_id: int
    variant_b_id: int
    effect_size: float
    p_value: float
    confidence_level: float
    significance_level: SignificanceLevel
    practical_significance: bool
    winner: Optional[int]  # variant_id of winner, None if no clear winner
    
@dataclass
class ExperimentAnalysis:
    """Complete analysis of an experiment."""
    experiment_id: int
    experiment_name: str
    analysis_timestamp: datetime
    runtime_days: float
    total_sample_size: int
    variant_analyses: List[VariantAnalysis]
    pairwise_comparisons: List[ComparisonResult]
    overall_winner: Optional[int]
    statistical_significance: SignificanceLevel
    practical_significance: bool
    recommendations: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    next_steps: List[str]

class ABTestAnalyzer:
    """Automated A/B testing analysis engine."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configuration for analysis thresholds
        self.min_sample_size = 100
        self.significance_threshold = 0.05
        self.practical_significance_threshold = 0.02  # 2% minimum effect size
        self.minimum_runtime_days = 7
        self.target_statistical_power = 0.8
        
    def analyze_experiment(self, experiment_id: int) -> ExperimentAnalysis:
        """
        Perform comprehensive analysis of an A/B testing experiment.
        
        Args:
            experiment_id: ID of the experiment to analyze
            
        Returns:
            Complete analysis with recommendations
        """
        try:
            # Get experiment basic info
            experiment_info = self._get_experiment_info(experiment_id)
            if not experiment_info:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            # Get variant data
            variants_data = self._get_variants_data(experiment_id)
            if len(variants_data) < 2:
                raise ValueError(f"Experiment {experiment_id} needs at least 2 variants for analysis")
            
            # Perform variant-level analysis
            variant_analyses = []
            for variant_data in variants_data:
                analysis = self._analyze_variant(variant_data)
                variant_analyses.append(analysis)
            
            # Perform pairwise comparisons
            pairwise_comparisons = self._perform_pairwise_comparisons(variants_data)
            
            # Determine overall winner and significance
            overall_winner, significance = self._determine_overall_results(pairwise_comparisons)
            
            # Calculate experiment runtime
            start_date = experiment_info.get('start_date')
            runtime_days = 0
            if start_date:
                runtime_days = (datetime.now() - start_date).total_seconds() / (24 * 3600)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                experiment_info, variant_analyses, pairwise_comparisons, runtime_days
            )
            
            # Assess risks
            risk_assessment = self._assess_risks(experiment_info, variant_analyses, pairwise_comparisons)
            
            # Generate next steps
            next_steps = self._generate_next_steps(recommendations, risk_assessment)
            
            # Calculate total sample size
            total_sample_size = sum(va.sample_size for va in variant_analyses)
            
            # Determine practical significance
            practical_significance = self._has_practical_significance(pairwise_comparisons)
            
            analysis = ExperimentAnalysis(
                experiment_id=experiment_id,
                experiment_name=experiment_info['name'],
                analysis_timestamp=datetime.now(),
                runtime_days=runtime_days,
                total_sample_size=total_sample_size,
                variant_analyses=variant_analyses,
                pairwise_comparisons=pairwise_comparisons,
                overall_winner=overall_winner,
                statistical_significance=significance,
                practical_significance=practical_significance,
                recommendations=recommendations,
                risk_assessment=risk_assessment,
                next_steps=next_steps
            )
            
            # Store analysis results
            self._store_analysis_results(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing experiment {experiment_id}: {e}")
            raise
    
    def _get_experiment_info(self, experiment_id: int) -> Optional[Dict]:
        """Get basic experiment information."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    cursor.execute("""
                        SELECT id, name, description, status, start_date, end_date,
                               minimum_sample_size, confidence_level, created_at
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
                        'start_date': row[4],
                        'end_date': row[5],
                        'minimum_sample_size': row[6],
                        'confidence_level': float(row[7]),
                        'created_at': row[8]
                    }
                    
        except Exception as e:
            self.logger.error(f"Error getting experiment info: {e}")
            return None
    
    def _get_variants_data(self, experiment_id: int) -> List[Dict]:
        """Get variant data with metrics for analysis."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Get variant basic info
                    cursor.execute("""
                        SELECT id, name, description, traffic_allocation, is_control
                        FROM ab_variants 
                        WHERE experiment_id = %s
                        ORDER BY is_control DESC, created_at
                    """, (experiment_id,))
                    
                    variants = []
                    for row in cursor.fetchall():
                        variant_id = row[0]
                        
                        # Get event counts for this variant
                        cursor.execute("""
                            SELECT 
                                COUNT(*) as total_events,
                                COUNT(CASE WHEN event_type = 'recommendation_generation' THEN 1 END) as recommendations,
                                COUNT(CASE WHEN event_type = 'user_interaction' THEN 1 END) as interactions
                            FROM ab_experiment_results
                            WHERE experiment_id = %s AND variant_id = %s
                        """, (experiment_id, variant_id))
                        
                        event_stats = cursor.fetchone()
                        
                        # Get quality metrics
                        cursor.execute("""
                            SELECT 
                                COALESCE(AVG(q.diversity_score), 0) as avg_diversity,
                                COALESCE(AVG(q.freshness_score), 0) as avg_freshness,
                                COALESCE(AVG(q.engagement_rate), 0) as avg_engagement,
                                COUNT(q.id) as quality_count
                            FROM ab_experiment_results r
                            LEFT JOIN recommendation_quality_metrics q ON r.quality_metrics_id = q.id
                            WHERE r.experiment_id = %s AND r.variant_id = %s
                        """, (experiment_id, variant_id))
                        
                        quality_stats = cursor.fetchone()
                        
                        # Get performance metrics
                        cursor.execute("""
                            SELECT 
                                AVG(latency_ms) as avg_latency,
                                AVG(memory_usage_mb) as avg_memory,
                                SUM(items_processed) as total_items,
                                AVG(cache_hit_rate) as avg_cache_hit_rate,
                                COUNT(CASE WHEN error_occurred THEN 1 END) as error_count
                            FROM ab_performance_events
                            WHERE experiment_id = %s AND variant_id = %s
                        """, (experiment_id, variant_id))
                        
                        perf_stats = cursor.fetchone()
                        
                        variant_data = {
                            'id': variant_id,
                            'name': row[1],
                            'description': row[2],
                            'traffic_allocation': float(row[3]),
                            'is_control': row[4],
                            'total_events': event_stats[0] if event_stats else 0,
                            'recommendations': event_stats[1] if event_stats else 0,
                            'interactions': event_stats[2] if event_stats else 0,
                            'quality_scores': {
                                'diversity': float(quality_stats[0]) if quality_stats and quality_stats[0] else 0,
                                'freshness': float(quality_stats[1]) if quality_stats and quality_stats[1] else 0,
                                'engagement': float(quality_stats[2]) if quality_stats and quality_stats[2] else 0,
                                'coverage': 0.0  # Default since coverage_score may not be available
                            },
                            'performance_metrics': {
                                'avg_latency_ms': float(perf_stats[0]) if perf_stats and perf_stats[0] else 0,
                                'avg_memory_mb': float(perf_stats[1]) if perf_stats and perf_stats[1] else 0,
                                'total_items': perf_stats[2] if perf_stats else 0,
                                'avg_cache_hit_rate': float(perf_stats[3]) if perf_stats and perf_stats[3] else 0,
                                'error_count': perf_stats[4] if perf_stats else 0
                            }
                        }
                        
                        variants.append(variant_data)
                    
                    return variants
                    
        except Exception as e:
            self.logger.error(f"Error getting variants data: {e}")
            return []
    
    def _analyze_variant(self, variant_data: Dict) -> VariantAnalysis:
        """Analyze a single variant."""
        # Calculate conversion rate (interactions / recommendations)
        recommendations = variant_data['recommendations']
        interactions = variant_data['interactions']
        conversion_rate = interactions / max(recommendations, 1)
        
        # Calculate confidence interval for conversion rate
        confidence_interval = self._calculate_confidence_interval(
            interactions, recommendations, confidence_level=0.95
        )
        
        # Calculate statistical power (simplified estimation)
        statistical_power = min(0.9, max(0.1, recommendations / self.min_sample_size))
        
        return VariantAnalysis(
            variant_id=variant_data['id'],
            variant_name=variant_data['name'],
            sample_size=recommendations,
            conversion_rate=conversion_rate,
            confidence_interval=confidence_interval,
            quality_scores=variant_data['quality_scores'],
            performance_metrics=variant_data['performance_metrics'],
            statistical_power=statistical_power
        )
    
    def _calculate_confidence_interval(self, successes: int, trials: int, 
                                     confidence_level: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for a proportion."""
        if trials == 0:
            return (0.0, 0.0)
            
        # Wilson score interval (more accurate for small samples)
        z = stats.norm.ppf(1 - (1 - confidence_level) / 2)
        p = successes / trials
        n = trials
        
        denominator = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denominator
        margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
        
        return (max(0, center - margin), min(1, center + margin))
    
    def _perform_pairwise_comparisons(self, variants_data: List[Dict]) -> List[ComparisonResult]:
        """Perform statistical comparisons between all variant pairs."""
        comparisons = []
        
        for i, variant_a in enumerate(variants_data):
            for j, variant_b in enumerate(variants_data):
                if i >= j:  # Avoid duplicate comparisons
                    continue
                
                comparison = self._compare_variants(variant_a, variant_b)
                comparisons.append(comparison)
        
        return comparisons
    
    def _compare_variants(self, variant_a: Dict, variant_b: Dict) -> ComparisonResult:
        """Compare two variants statistically."""
        # Get conversion data
        a_successes = variant_a['interactions']
        a_trials = variant_a['recommendations']
        b_successes = variant_b['interactions']
        b_trials = variant_b['recommendations']
        
        # Calculate conversion rates
        a_rate = a_successes / max(a_trials, 1)
        b_rate = b_successes / max(b_trials, 1)
        
        # Perform two-proportion z-test
        if a_trials == 0 or b_trials == 0:
            p_value = 1.0
            effect_size = 0.0
        else:
            # Pool proportion
            pooled_p = (a_successes + b_successes) / (a_trials + b_trials)
            se = math.sqrt(pooled_p * (1 - pooled_p) * (1/a_trials + 1/b_trials))
            
            if se == 0:
                p_value = 1.0
                z_score = 0.0
            else:
                z_score = (a_rate - b_rate) / se
                p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
            
            # Effect size (difference in conversion rates)
            effect_size = abs(a_rate - b_rate)
        
        # Determine significance level
        if p_value < 0.001:
            significance = SignificanceLevel.HIGHLY_SIGNIFICANT
        elif p_value < 0.01:
            significance = SignificanceLevel.SIGNIFICANT
        elif p_value < 0.05:
            significance = SignificanceLevel.MARGINALLY_SIGNIFICANT
        else:
            significance = SignificanceLevel.NOT_SIGNIFICANT
        
        # Check practical significance
        practical_significance = effect_size >= self.practical_significance_threshold
        
        # Determine winner
        winner = None
        if significance in [SignificanceLevel.SIGNIFICANT, SignificanceLevel.HIGHLY_SIGNIFICANT]:
            if practical_significance:
                winner = variant_a['id'] if a_rate > b_rate else variant_b['id']
        
        return ComparisonResult(
            variant_a_id=variant_a['id'],
            variant_b_id=variant_b['id'],
            effect_size=effect_size,
            p_value=p_value,
            confidence_level=0.95,
            significance_level=significance,
            practical_significance=practical_significance,
            winner=winner
        )
    
    def _determine_overall_results(self, comparisons: List[ComparisonResult]) -> Tuple[Optional[int], SignificanceLevel]:
        """Determine overall experiment winner and significance."""
        # Find the most significant comparison
        most_significant = SignificanceLevel.NOT_SIGNIFICANT
        overall_winner = None
        
        for comparison in comparisons:
            if comparison.significance_level.value in ['significant', 'highly_significant']:
                if comparison.practical_significance and comparison.winner:
                    if most_significant == SignificanceLevel.NOT_SIGNIFICANT:
                        most_significant = comparison.significance_level
                        overall_winner = comparison.winner
                    elif comparison.significance_level == SignificanceLevel.HIGHLY_SIGNIFICANT:
                        most_significant = comparison.significance_level
                        overall_winner = comparison.winner
        
        return overall_winner, most_significant
    
    def _has_practical_significance(self, comparisons: List[ComparisonResult]) -> bool:
        """Check if any comparison has practical significance."""
        return any(comp.practical_significance for comp in comparisons)
    
    def _generate_recommendations(self, experiment_info: Dict, variant_analyses: List[VariantAnalysis],
                                 comparisons: List[ComparisonResult], runtime_days: float) -> List[Dict[str, Any]]:
        """Generate intelligent recommendations based on analysis."""
        recommendations = []
        
        # Check sample size adequacy
        total_sample_size = sum(va.sample_size for va in variant_analyses)
        min_required = experiment_info.get('minimum_sample_size', self.min_sample_size)
        
        if total_sample_size < min_required:
            recommendations.append({
                'type': RecommendationType.INCREASE_SAMPLE_SIZE.value,
                'priority': 'high',
                'message': f'Sample size ({total_sample_size}) is below minimum required ({min_required})',
                'action': 'Continue experiment to reach minimum sample size',
                'estimated_time': f'{((min_required - total_sample_size) / max(total_sample_size / max(runtime_days, 1), 1)):.1f} days'
            })
        
        # Check runtime adequacy
        if runtime_days < self.minimum_runtime_days:
            recommendations.append({
                'type': RecommendationType.EXTEND_DURATION.value,
                'priority': 'medium',
                'message': f'Experiment has only run for {runtime_days:.1f} days (minimum: {self.minimum_runtime_days})',
                'action': 'Continue experiment for more reliable results',
                'estimated_time': f'{self.minimum_runtime_days - runtime_days:.1f} more days recommended'
            })
        
        # Check for clear winner
        significant_comparisons = [c for c in comparisons if c.significance_level.value in ['significant', 'highly_significant']]
        practical_comparisons = [c for c in significant_comparisons if c.practical_significance]
        
        if practical_comparisons and runtime_days >= self.minimum_runtime_days:
            recommendations.append({
                'type': RecommendationType.STOP_WINNER_FOUND.value,
                'priority': 'high',
                'message': 'Clear winner identified with statistical and practical significance',
                'action': 'Stop experiment and implement winning variant',
                'winner_variant_id': practical_comparisons[0].winner,
                'confidence': 'high' if practical_comparisons[0].significance_level == SignificanceLevel.HIGHLY_SIGNIFICANT else 'medium'
            })
        
        # Check for no effect scenario
        if not significant_comparisons and runtime_days >= self.minimum_runtime_days * 2:
            recommendations.append({
                'type': RecommendationType.STOP_NO_EFFECT.value,
                'priority': 'medium',
                'message': 'No statistically significant differences detected after extended runtime',
                'action': 'Consider stopping experiment or redesigning with larger effect size',
                'confidence': 'medium'
            })
        
        # Check for performance issues
        for variant in variant_analyses:
            if variant.performance_metrics.get('error_count', 0) > 0:
                error_rate = variant.performance_metrics['error_count'] / max(variant.sample_size, 1)
                if error_rate > 0.01:  # 1% error rate threshold
                    recommendations.append({
                        'type': RecommendationType.INVESTIGATE_ANOMALY.value,
                        'priority': 'high',
                        'message': f'Variant {variant.variant_name} has high error rate ({error_rate:.2%})',
                        'action': 'Investigate and fix errors before continuing',
                        'variant_id': variant.variant_id
                    })
        
        # Traffic optimization recommendations
        if len(variant_analyses) > 2:
            # Check if we should focus traffic on promising variants
            best_performers = sorted(variant_analyses, key=lambda v: v.conversion_rate, reverse=True)[:2]
            if len(best_performers) >= 2:
                recommendations.append({
                    'type': RecommendationType.OPTIMIZE_TRAFFIC.value,
                    'priority': 'low',
                    'message': 'Consider focusing traffic on top 2 performing variants',
                    'action': 'Reallocate traffic to improve statistical power',
                    'suggested_variants': [v.variant_id for v in best_performers]
                })
        
        return recommendations
    
    def _assess_risks(self, experiment_info: Dict, variant_analyses: List[VariantAnalysis],
                     comparisons: List[ComparisonResult]) -> Dict[str, Any]:
        """Assess risks associated with the experiment."""
        risks = {
            'level': 'low',
            'factors': [],
            'mitigation_strategies': []
        }
        
        # Statistical power risk
        low_power_variants = [v for v in variant_analyses if v.statistical_power < self.target_statistical_power]
        if low_power_variants:
            risks['factors'].append('Low statistical power detected')
            risks['mitigation_strategies'].append('Increase sample size or extend duration')
            risks['level'] = 'medium'
        
        # Multiple testing risk
        if len(comparisons) > 3:
            risks['factors'].append('Multiple comparisons increase false positive risk')
            risks['mitigation_strategies'].append('Apply Bonferroni correction or use sequential testing')
            risks['level'] = 'medium'
        
        # Performance degradation risk
        performance_issues = []
        for variant in variant_analyses:
            if variant.performance_metrics.get('avg_latency_ms', 0) > 1000:  # 1 second threshold
                performance_issues.append(f"Variant {variant.variant_name} has high latency")
        
        if performance_issues:
            risks['factors'].extend(performance_issues)
            risks['mitigation_strategies'].append('Optimize slow variants or exclude from experiment')
            risks['level'] = 'high'
        
        return risks
    
    def _generate_next_steps(self, recommendations: List[Dict], risk_assessment: Dict) -> List[str]:
        """Generate concrete next steps based on recommendations and risks."""
        next_steps = []
        
        # Process high priority recommendations first
        high_priority_recs = [r for r in recommendations if r['priority'] == 'high']
        
        for rec in high_priority_recs:
            if rec['type'] == RecommendationType.STOP_WINNER_FOUND.value:
                next_steps.append(f"1. Stop experiment and implement variant {rec.get('winner_variant_id', 'TBD')}")
                next_steps.append("2. Monitor implementation for unexpected issues")
                next_steps.append("3. Document learnings for future experiments")
                return next_steps  # Early return for definitive action
            
            elif rec['type'] == RecommendationType.INCREASE_SAMPLE_SIZE.value:
                next_steps.append(f"1. Continue experiment for {rec.get('estimated_time', 'TBD')}")
                
            elif rec['type'] == RecommendationType.INVESTIGATE_ANOMALY.value:
                next_steps.append(f"1. Investigate errors in variant {rec.get('variant_id', 'TBD')}")
        
        # Add medium priority recommendations
        medium_priority_recs = [r for r in recommendations if r['priority'] == 'medium']
        for rec in medium_priority_recs:
            if rec['type'] == RecommendationType.EXTEND_DURATION.value:
                next_steps.append(f"2. Extend experiment duration by {rec.get('estimated_time', 'TBD')}")
        
        # Add risk mitigation steps
        if risk_assessment['level'] in ['medium', 'high']:
            next_steps.append("3. Address identified risks:")
            for strategy in risk_assessment['mitigation_strategies']:
                next_steps.append(f"   - {strategy}")
        
        # Default next step if no specific recommendations
        if not next_steps:
            next_steps.append("1. Continue monitoring experiment progress")
            next_steps.append("2. Review results again in 2-3 days")
        
        return next_steps
    
    def _store_analysis_results(self, analysis: ExperimentAnalysis):
        """Store analysis results in database for future reference."""
        try:
            # Prepare analysis data for storage
            analysis_data = {
                'experiment_id': analysis.experiment_id,
                'analysis_timestamp': analysis.analysis_timestamp.isoformat(),
                'runtime_days': analysis.runtime_days,
                'total_sample_size': analysis.total_sample_size,
                'overall_winner': analysis.overall_winner,
                'statistical_significance': analysis.statistical_significance.value,
                'practical_significance': analysis.practical_significance,
                'recommendations_count': len(analysis.recommendations),
                'risk_level': analysis.risk_assessment['level'],
                'next_steps_count': len(analysis.next_steps)
            }
            
            with get_db_connection() as connection:
                with get_cursor(connection) as cursor:
                    # Find control variant to use as placeholder for system analysis
                    control_variant_id = None
                    cursor.execute("""
                        SELECT id FROM ab_variants 
                        WHERE experiment_id = %s AND is_control = true 
                        LIMIT 1
                    """, (analysis.experiment_id,))
                    result = cursor.fetchone()
                    if result:
                        control_variant_id = result[0]
                    
                    if control_variant_id:
                        # Store in experiment results table with control variant as placeholder
                        cursor.execute("""
                            INSERT INTO ab_experiment_results 
                            (experiment_id, variant_id, user_id, event_type, event_data, timestamp)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            analysis.experiment_id,
                            control_variant_id,  # Use control variant as placeholder
                            'system',
                            'automated_analysis',
                            json.dumps(analysis_data),  # Convert to JSON string
                            analysis.analysis_timestamp
                        ))
                        
                        connection.commit()
                        logger.info(f"Analysis results stored for experiment {analysis.experiment_id}")
                    else:
                        logger.warning(f"No control variant found for experiment {analysis.experiment_id}, skipping storage")
                        
        except Exception as e:
            logger.error(f"Error storing analysis results: {e}")
            # Don't fail the analysis if storage fails
            pass

# Global analyzer instance
ab_analyzer = ABTestAnalyzer() 