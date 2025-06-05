#!/usr/bin/env python3
"""
Performance Benchmark Reporting and Visualization API - TODO #27f

This module provides comprehensive API endpoints for the benchmark reporting
and visualization dashboard, including:

1. Benchmark data retrieval and filtering
2. Performance trend analysis
3. Regression report access
4. Real-time monitoring integration
5. Comparative analysis tools
6. Export and reporting functionality
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify
from db.connection import get_db_connection, get_cursor
from utils.performance_benchmarking import PerformanceBenchmark
from utils.performance_regression_detection import (
    PerformanceRegressionDetector, 
    get_regression_detector,
    detect_regressions_for_benchmark
)
from utils.performance_monitoring import get_global_monitor

logger = logging.getLogger(__name__)

# Create blueprint
performance_bp = Blueprint('performance', __name__, url_prefix='/api/performance')

@performance_bp.route('/benchmarks', methods=['GET'])
def get_benchmarks():
    """
    Get performance benchmarks with filtering and pagination.
    
    Query parameters:
    - benchmark_type: Filter by type (baseline, variant, regression, test)
    - start_date: ISO datetime string for start of date range
    - end_date: ISO datetime string for end of date range
    - limit: Number of results (default: 50, max: 200)
    - offset: Pagination offset (default: 0)
    - order_by: Sort field (test_timestamp, p95_latency, requests_per_second)
    - order_dir: Sort direction (asc, desc, default: desc)
    """
    try:
        # Parse query parameters
        benchmark_type = request.args.get('benchmark_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = int(request.args.get('offset', 0))
        order_by = request.args.get('order_by', 'test_timestamp')
        order_dir = request.args.get('order_dir', 'desc').upper()
        
        # Validate sort parameters
        valid_order_fields = [
            'test_timestamp', 'p95_latency', 'requests_per_second', 
            'error_rate', 'peak_cpu_usage', 'peak_memory_mb'
        ]
        if order_by not in valid_order_fields:
            order_by = 'test_timestamp'
        
        if order_dir not in ['ASC', 'DESC']:
            order_dir = 'DESC'
        
        # Build query
        where_conditions = []
        params = []
        
        if benchmark_type:
            where_conditions.append("benchmark_type = %s")
            params.append(benchmark_type)
        
        if start_date:
            where_conditions.append("test_timestamp >= %s")
            params.append(datetime.fromisoformat(start_date.replace('Z', '+00:00')))
        
        if end_date:
            where_conditions.append("test_timestamp <= %s")
            params.append(datetime.fromisoformat(end_date.replace('Z', '+00:00')))
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                # Get total count
                count_query = f"SELECT COUNT(*) FROM performance_benchmarks {where_clause}"
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]
                
                # Get benchmarks
                query = f"""
                    SELECT id, name, description, benchmark_type, test_timestamp,
                           concurrent_users, test_duration_seconds, total_requests,
                           p50_latency, p95_latency, p99_latency, max_latency,
                           requests_per_second, error_rate,
                           avg_cpu_usage, peak_cpu_usage, avg_memory_mb, peak_memory_mb,
                           avg_db_query_time, db_connections_used, quality_score_degradation,
                           algorithm_config, environment_info
                    FROM performance_benchmarks 
                    {where_clause}
                    ORDER BY {order_by} {order_dir}
                    LIMIT %s OFFSET %s
                """
                
                cursor.execute(query, params + [limit, offset])
                columns = [desc[0] for desc in cursor.description]
                benchmarks = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                # Convert datetime objects to ISO strings
                for benchmark in benchmarks:
                    if 'test_timestamp' in benchmark and benchmark['test_timestamp']:
                        benchmark['test_timestamp'] = benchmark['test_timestamp'].isoformat()
        
        return jsonify({
            'success': True,
            'data': {
                'benchmarks': benchmarks,
                'pagination': {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': (offset + limit) < total_count
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting benchmarks: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/benchmarks/<int:benchmark_id>', methods=['GET'])
def get_benchmark_details(benchmark_id: int):
    """Get detailed information for a specific benchmark."""
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                cursor.execute("""
                    SELECT * FROM performance_benchmarks WHERE id = %s
                """, (benchmark_id,))
                
                row = cursor.fetchone()
                if not row:
                    return jsonify({
                        'success': False,
                        'error': 'Benchmark not found'
                    }), 404
                
                columns = [desc[0] for desc in cursor.description]
                benchmark = dict(zip(columns, row))
                
                # Convert datetime to ISO string
                if benchmark['test_timestamp']:
                    benchmark['test_timestamp'] = benchmark['test_timestamp'].isoformat()
        
        return jsonify({
            'success': True,
            'data': benchmark
        })
        
    except Exception as e:
        logger.error(f"Error getting benchmark {benchmark_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/benchmarks/<int:benchmark_id>/compare/<int:baseline_id>', methods=['GET'])
def compare_benchmarks(benchmark_id: int, baseline_id: int):
    """Compare two benchmarks and return detailed comparison."""
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                # Get both benchmarks
                cursor.execute("""
                    SELECT * FROM performance_benchmarks WHERE id IN (%s, %s)
                """, (benchmark_id, baseline_id))
                
                rows = cursor.fetchall()
                if len(rows) != 2:
                    return jsonify({
                        'success': False,
                        'error': 'One or both benchmarks not found'
                    }), 404
                
                columns = [desc[0] for desc in cursor.description]
                benchmarks = {row[0]: dict(zip(columns, row)) for row in rows}
                
                current = benchmarks[benchmark_id]
                baseline = benchmarks[baseline_id]
        
        # Calculate percentage changes for key metrics
        metrics_comparison = {}
        key_metrics = [
            'p50_latency', 'p95_latency', 'p99_latency', 'requests_per_second',
            'error_rate', 'peak_cpu_usage', 'peak_memory_mb'
        ]
        
        for metric in key_metrics:
            current_val = current.get(metric, 0) or 0
            baseline_val = baseline.get(metric, 0) or 0
            
            if baseline_val > 0:
                change_percent = ((current_val - baseline_val) / baseline_val) * 100
                change_absolute = current_val - baseline_val
            else:
                change_percent = 0
                change_absolute = current_val
            
            metrics_comparison[metric] = {
                'current_value': current_val,
                'baseline_value': baseline_val,
                'change_percent': round(change_percent, 2),
                'change_absolute': round(change_absolute, 2),
                'is_better': _is_metric_improvement(metric, change_percent)
            }
        
        # Convert timestamps
        for benchmark in [current, baseline]:
            if benchmark['test_timestamp']:
                benchmark['test_timestamp'] = benchmark['test_timestamp'].isoformat()
        
        return jsonify({
            'success': True,
            'data': {
                'current_benchmark': current,
                'baseline_benchmark': baseline,
                'metrics_comparison': metrics_comparison,
                'overall_assessment': _assess_overall_performance(metrics_comparison)
            }
        })
        
    except Exception as e:
        logger.error(f"Error comparing benchmarks {benchmark_id} vs {baseline_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/trends', methods=['GET'])
def get_performance_trends():
    """
    Get performance trends over time.
    
    Query parameters:
    - days: Number of days to analyze (default: 30)
    - metric: Specific metric to trend (default: all key metrics)
    - benchmark_type: Filter by benchmark type
    - granularity: Time granularity (daily, weekly, default: daily)
    """
    try:
        days = int(request.args.get('days', 30))
        metric = request.args.get('metric')
        benchmark_type = request.args.get('benchmark_type')
        granularity = request.args.get('granularity', 'daily')
        
        # Determine time grouping
        if granularity == 'weekly':
            time_group = "DATE_TRUNC('week', test_timestamp)"
        else:
            time_group = "DATE_TRUNC('day', test_timestamp)"
        
        # Build query conditions
        where_conditions = [f"test_timestamp >= NOW() - INTERVAL '{days} days'"]
        params = []
        
        if benchmark_type:
            where_conditions.append("benchmark_type = %s")
            params.append(benchmark_type)
        
        where_clause = " AND ".join(where_conditions)
        
        # Define metrics to trend
        if metric and metric in ['p50_latency', 'p95_latency', 'p99_latency', 'requests_per_second', 
                                'error_rate', 'peak_cpu_usage', 'peak_memory_mb']:
            metrics_to_trend = [metric]
        else:
            metrics_to_trend = ['p95_latency', 'requests_per_second', 'error_rate', 'peak_cpu_usage']
        
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                trends = {}
                
                for metric_name in metrics_to_trend:
                    query = f"""
                        SELECT {time_group} as time_period,
                               COUNT(*) as benchmark_count,
                               AVG({metric_name}) as avg_value,
                               MIN({metric_name}) as min_value,
                               MAX({metric_name}) as max_value,
                               STDDEV({metric_name}) as std_dev
                        FROM performance_benchmarks
                        WHERE {where_clause}
                        GROUP BY {time_group}
                        ORDER BY time_period
                    """
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    trend_data = []
                    for row in rows:
                        trend_data.append({
                            'timestamp': row[0].isoformat() if row[0] else None,
                            'benchmark_count': row[1],
                            'avg_value': float(row[2]) if row[2] else 0,
                            'min_value': float(row[3]) if row[3] else 0,
                            'max_value': float(row[4]) if row[4] else 0,
                            'std_dev': float(row[5]) if row[5] else 0
                        })
                    
                    trends[metric_name] = trend_data
        
        return jsonify({
            'success': True,
            'data': {
                'trends': trends,
                'period': {
                    'days': days,
                    'granularity': granularity,
                    'start_date': (datetime.utcnow() - timedelta(days=days)).isoformat(),
                    'end_date': datetime.utcnow().isoformat()
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/regressions', methods=['GET'])
def get_regression_reports():
    """
    Get performance regression reports.
    
    Query parameters:
    - days: Number of days to look back (default: 30)
    - severity: Filter by severity (none, low, medium, high, critical)
    - limit: Number of results (default: 20)
    """
    try:
        days = int(request.args.get('days', 30))
        severity = request.args.get('severity')
        limit = min(int(request.args.get('limit', 20)), 100)
        
        where_conditions = [f"detection_timestamp >= NOW() - INTERVAL '{days} days'"]
        params = []
        
        if severity:
            where_conditions.append("overall_severity = %s")
            params.append(severity)
        
        where_clause = " AND ".join(where_conditions)
        
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
                    return jsonify({
                        'success': True,
                        'data': {
                            'regression_reports': [],
                            'message': 'No regression reports table found. No regressions analyzed yet.'
                        }
                    })
                
                query = f"""
                    SELECT report_id, test_name, detection_timestamp, overall_severity,
                           baseline_benchmark_id, current_benchmark_id, 
                           detected_regressions, performance_score, 
                           recommendations, alert_sent
                    FROM performance_regression_reports
                    WHERE {where_clause}
                    ORDER BY detection_timestamp DESC
                    LIMIT %s
                """
                
                cursor.execute(query, params + [limit])
                columns = [desc[0] for desc in cursor.description]
                reports = []
                
                for row in cursor.fetchall():
                    report = dict(zip(columns, row))
                    # Convert datetime to ISO string
                    if report['detection_timestamp']:
                        report['detection_timestamp'] = report['detection_timestamp'].isoformat()
                    reports.append(report)
        
        return jsonify({
            'success': True,
            'data': {
                'regression_reports': reports,
                'total_found': len(reports)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting regression reports: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/regressions/<report_id>', methods=['GET'])
def get_regression_report_details(report_id: str):
    """Get detailed regression report."""
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                cursor.execute("""
                    SELECT * FROM performance_regression_reports 
                    WHERE report_id = %s
                """, (report_id,))
                
                row = cursor.fetchone()
                if not row:
                    return jsonify({
                        'success': False,
                        'error': 'Regression report not found'
                    }), 404
                
                columns = [desc[0] for desc in cursor.description]
                report = dict(zip(columns, row))
                
                # Convert datetime to ISO string
                if report['detection_timestamp']:
                    report['detection_timestamp'] = report['detection_timestamp'].isoformat()
        
        return jsonify({
            'success': True,
            'data': report
        })
        
    except Exception as e:
        logger.error(f"Error getting regression report {report_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/analyze/<int:benchmark_id>', methods=['POST'])
def analyze_benchmark_regression(benchmark_id: int):
    """Trigger regression analysis for a specific benchmark."""
    try:
        # Get optional baseline ID from request - handle missing Content-Type gracefully
        try:
            data = request.get_json(force=True) or {}
        except Exception:
            # If JSON parsing fails or no content, use empty dict
            data = {}
        baseline_id = data.get('baseline_id')
        
        # Run regression detection
        report = detect_regressions_for_benchmark(benchmark_id, baseline_id)
        
        # Convert datetime objects to ISO strings for JSON response
        report_dict = {
            'report_id': report.report_id,
            'test_name': report.test_name,
            'detection_timestamp': report.detection_timestamp.isoformat(),
            'overall_severity': report.overall_severity.value,
            'baseline_benchmark_id': report.baseline_benchmark_id,
            'current_benchmark_id': report.current_benchmark_id,
            'performance_score': report.performance_score,
            'recommendations': report.recommendations,
            'alert_sent': report.alert_sent,
            'detected_regressions': [
                {
                    'metric_name': r.metric_name,
                    'regression_type': r.regression_type.value,
                    'severity': r.severity.value,
                    'baseline_value': r.baseline_value,
                    'current_value': r.current_value,
                    'change_percent': r.change_percent,
                    'recommendation': r.recommendation,
                    'trend_direction': r.trend_direction
                }
                for r in report.detected_regressions
            ],
            'statistical_summary': report.statistical_summary,
            'trend_analysis': report.trend_analysis
        }
        
        return jsonify({
            'success': True,
            'data': report_dict
        })
        
    except Exception as e:
        logger.error(f"Error analyzing benchmark {benchmark_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/monitoring/current', methods=['GET'])
def get_current_monitoring_status():
    """Get current real-time monitoring status and metrics."""
    try:
        monitor = get_global_monitor()
        
        # Get performance summary
        summary = monitor.get_performance_summary()
        
        # Get active alerts
        active_alerts = monitor.threshold_monitor.get_active_alerts()
        
        # Convert alerts to serializable format
        alerts_data = []
        for alert in active_alerts:
            alerts_data.append({
                'alert_id': alert.alert_id,
                'timestamp': alert.timestamp.isoformat(),
                'metric_name': alert.metric_name,
                'current_value': alert.current_value,
                'severity': alert.severity,
                'message': alert.message
            })
        
        return jsonify({
            'success': True,
            'data': {
                'monitoring_active': monitor.monitoring_active,
                'performance_summary': summary,
                'active_alerts': alerts_data,
                'alert_count': len(alerts_data)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/monitoring/snapshot', methods=['POST'])
def create_monitoring_snapshot():
    """Create a performance snapshot from current monitoring data."""
    try:
        monitor = get_global_monitor()
        snapshot_id = monitor.save_performance_snapshot()
        
        return jsonify({
            'success': True,
            'data': {
                'snapshot_id': snapshot_id,
                'message': 'Performance snapshot created successfully'
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating monitoring snapshot: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/stats/summary', methods=['GET'])
def get_performance_stats_summary():
    """Get high-level performance statistics summary."""
    try:
        days = int(request.args.get('days', 7))
        
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                # Get benchmark statistics
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_benchmarks,
                        COUNT(DISTINCT benchmark_type) as benchmark_types,
                        AVG(p95_latency) as avg_p95_latency,
                        AVG(requests_per_second) as avg_rps,
                        AVG(error_rate) as avg_error_rate,
                        MIN(test_timestamp) as earliest_test,
                        MAX(test_timestamp) as latest_test
                    FROM performance_benchmarks
                    WHERE test_timestamp >= NOW() - INTERVAL '{days} days'
                """)
                
                stats_row = cursor.fetchone()
                
                # Get recent benchmark counts by type
                cursor.execute(f"""
                    SELECT benchmark_type, COUNT(*) as count
                    FROM performance_benchmarks
                    WHERE test_timestamp >= NOW() - INTERVAL '{days} days'
                    GROUP BY benchmark_type
                """)
                
                type_counts = dict(cursor.fetchall())
                
                # Get regression summary (if table exists)
                regression_summary = {}
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'performance_regression_reports'
                    )
                """)
                
                if cursor.fetchone()[0]:
                    cursor.execute(f"""
                        SELECT 
                            overall_severity,
                            COUNT(*) as count
                        FROM performance_regression_reports
                        WHERE detection_timestamp >= NOW() - INTERVAL '{days} days'
                        GROUP BY overall_severity
                    """)
                    
                    regression_summary = dict(cursor.fetchall())
        
        stats_data = {
            'total_benchmarks': stats_row[0] or 0,
            'benchmark_types': stats_row[1] or 0,
            'avg_p95_latency': float(stats_row[2]) if stats_row[2] else 0,
            'avg_requests_per_second': float(stats_row[3]) if stats_row[3] else 0,
            'avg_error_rate': float(stats_row[4]) if stats_row[4] else 0,
            'earliest_test': stats_row[5].isoformat() if stats_row[5] else None,
            'latest_test': stats_row[6].isoformat() if stats_row[6] else None,
            'benchmark_type_counts': type_counts,
            'regression_severity_counts': regression_summary,
            'analysis_period_days': days
        }
        
        return jsonify({
            'success': True,
            'data': stats_data
        })
        
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_bp.route('/export/benchmarks', methods=['GET'])
def export_benchmarks_csv():
    """Export benchmark data as CSV."""
    try:
        # Parse filters similar to get_benchmarks
        benchmark_type = request.args.get('benchmark_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = min(int(request.args.get('limit', 1000)), 5000)
        
        # Build query
        where_conditions = []
        params = []
        
        if benchmark_type:
            where_conditions.append("benchmark_type = %s")
            params.append(benchmark_type)
        
        if start_date:
            where_conditions.append("test_timestamp >= %s")
            params.append(datetime.fromisoformat(start_date.replace('Z', '+00:00')))
        
        if end_date:
            where_conditions.append("test_timestamp <= %s")
            params.append(datetime.fromisoformat(end_date.replace('Z', '+00:00')))
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        with get_db_connection() as conn:
            with get_cursor(conn) as cursor:
                query = f"""
                    SELECT id, name, benchmark_type, test_timestamp,
                           concurrent_users, test_duration_seconds, total_requests,
                           p50_latency, p95_latency, p99_latency, max_latency,
                           requests_per_second, error_rate,
                           avg_cpu_usage, peak_cpu_usage, avg_memory_mb, peak_memory_mb,
                           avg_db_query_time, quality_score_degradation
                    FROM performance_benchmarks 
                    {where_clause}
                    ORDER BY test_timestamp DESC
                    LIMIT %s
                """
                
                cursor.execute(query, params + [limit])
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
        
        # Create CSV content
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(columns)
        
        # Write data rows
        for row in rows:
            # Convert datetime to string for CSV
            csv_row = []
            for i, value in enumerate(row):
                if isinstance(value, datetime):
                    csv_row.append(value.isoformat())
                else:
                    csv_row.append(value)
            writer.writerow(csv_row)
        
        csv_content = output.getvalue()
        output.close()
        
        # Return CSV as downloadable file
        from flask import Response
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=performance_benchmarks_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting benchmarks: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _is_metric_improvement(metric_name: str, change_percent: float) -> bool:
    """Determine if a metric change is an improvement."""
    # For latency, error rate, CPU, memory - lower is better
    if metric_name in ['p50_latency', 'p95_latency', 'p99_latency', 'error_rate', 
                       'peak_cpu_usage', 'peak_memory_mb']:
        return change_percent < 0
    
    # For throughput - higher is better
    if metric_name in ['requests_per_second']:
        return change_percent > 0
    
    return False


def _assess_overall_performance(metrics_comparison: Dict) -> Dict:
    """Assess overall performance comparison."""
    improvements = 0
    degradations = 0
    total_metrics = len(metrics_comparison)
    
    for metric_name, comparison in metrics_comparison.items():
        if comparison['is_better']:
            improvements += 1
        elif abs(comparison['change_percent']) > 5:  # Significant change threshold
            degradations += 1
    
    if improvements > degradations:
        assessment = "improved"
    elif degradations > improvements:
        assessment = "degraded"
    else:
        assessment = "similar"
    
    return {
        'assessment': assessment,
        'improvements': improvements,
        'degradations': degradations,
        'total_metrics': total_metrics,
        'improvement_ratio': improvements / total_metrics if total_metrics > 0 else 0
    }


# Register error handlers
@performance_bp.errorhandler(404)
def handle_404(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@performance_bp.errorhandler(500)
def handle_500(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500 