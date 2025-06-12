"""
Analytics aggregation tasks for the Corgi Recommender Service.

This module provides Celery tasks for aggregating interaction data
into performance metrics for model comparison.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from celery import Celery
from db.connection import get_db_connection, get_cursor, USE_IN_MEMORY_DB

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Celery
try:
    from utils.celery_app import celery
    CELERY_AVAILABLE = True
except ImportError:
    logger.warning("Celery not available, analytics aggregation will be disabled")
    CELERY_AVAILABLE = False
    celery = None


@celery.task(bind=True, name="analytics.aggregate_model_performance")
def aggregate_model_performance(self, hours_back: int = 24):
    """
    Aggregate model performance metrics from interaction logs.
    
    This task runs periodically to calculate performance metrics for each
    model variant based on user interactions with recommendations.
    
    Args:
        hours_back: Number of hours back to aggregate (default: 24)
    """
    try:
        logger.info(f"Starting model performance aggregation for last {hours_back} hours")
        
        if USE_IN_MEMORY_DB:
            logger.info("Skipping aggregation for in-memory database")
            return {"status": "skipped", "reason": "in_memory_db"}
        
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Calculate the time range for aggregation
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours_back)
                
                # Get all hours that need aggregation
                hours_to_process = []
                current_hour = start_time.replace(minute=0, second=0, microsecond=0)
                
                while current_hour <= end_time:
                    hours_to_process.append(current_hour)
                    current_hour += timedelta(hours=1)
                
                logger.info(f"Processing {len(hours_to_process)} hours of data")
                
                # Aggregate metrics for each hour and variant
                total_aggregated = 0
                
                for hour_start in hours_to_process:
                    hour_end = hour_start + timedelta(hours=1)
                    
                    # Get all model variants that had activity in this hour
                    cur.execute("""
                        SELECT DISTINCT model_variant_id
                        FROM interactions 
                        WHERE model_variant_id IS NOT NULL
                        AND created_at >= %s 
                        AND created_at < %s
                    """, (hour_start, hour_end))
                    
                    active_variants = [row[0] for row in cur.fetchall()]
                    
                    for variant_id in active_variants:
                        metrics = calculate_variant_metrics(cur, variant_id, hour_start, hour_end)
                        
                        if metrics:
                            # Insert or update the aggregated metrics
                            cur.execute("""
                                INSERT INTO model_performance_summary 
                                (variant_id, date_hour, impressions, likes, clicks, bookmarks, reblogs, 
                                 total_users, unique_posts, avg_response_time)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (variant_id, date_hour)
                                DO UPDATE SET
                                    impressions = EXCLUDED.impressions,
                                    likes = EXCLUDED.likes,
                                    clicks = EXCLUDED.clicks,
                                    bookmarks = EXCLUDED.bookmarks,
                                    reblogs = EXCLUDED.reblogs,
                                    total_users = EXCLUDED.total_users,
                                    unique_posts = EXCLUDED.unique_posts,
                                    avg_response_time = EXCLUDED.avg_response_time,
                                    updated_at = CURRENT_TIMESTAMP
                            """, (
                                variant_id,
                                hour_start,
                                metrics['impressions'],
                                metrics['likes'],
                                metrics['clicks'],
                                metrics['bookmarks'],
                                metrics['reblogs'],
                                metrics['total_users'],
                                metrics['unique_posts'],
                                metrics['avg_response_time']
                            ))
                            
                            total_aggregated += 1
                
                conn.commit()
                
                logger.info(f"Successfully aggregated {total_aggregated} variant-hour metrics")
                
                return {
                    "status": "success",
                    "hours_processed": len(hours_to_process),
                    "metrics_aggregated": total_aggregated,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat()
                }
                
    except Exception as e:
        logger.error(f"Error during model performance aggregation: {e}")
        # Re-raise so Celery can handle retry logic
        raise


def calculate_variant_metrics(cur, variant_id: int, hour_start: datetime, hour_end: datetime) -> Optional[Dict]:
    """
    Calculate performance metrics for a specific variant within a time window.
    
    Args:
        cur: Database cursor
        variant_id: ID of the model variant
        hour_start: Start of the time window
        hour_end: End of the time window
        
    Returns:
        Dictionary with calculated metrics or None if no data
    """
    try:
        # Count different types of interactions
        cur.execute("""
            SELECT 
                action_type,
                COUNT(*) as count,
                COUNT(DISTINCT user_alias) as unique_users,
                COUNT(DISTINCT post_id) as unique_posts
            FROM interactions 
            WHERE model_variant_id = %s
            AND created_at >= %s 
            AND created_at < %s
            GROUP BY action_type
        """, (variant_id, hour_start, hour_end))
        
        interaction_data = cur.fetchall()
        
        if not interaction_data:
            return None
        
        # Initialize metrics
        metrics = {
            'impressions': 0,  # Views or recommendations shown
            'likes': 0,        # Favorite/like actions
            'clicks': 0,       # Click/view actions
            'bookmarks': 0,    # Bookmark actions
            'reblogs': 0,      # Reblog/share actions
            'total_users': 0,  # Unique users who interacted
            'unique_posts': 0, # Unique posts interacted with
            'avg_response_time': 0.0  # Will be calculated separately
        }
        
        # Aggregate by action type
        all_users = set()
        all_posts = set()
        
        for action_type, count, unique_users, unique_posts in interaction_data:
            all_users.add(unique_users)
            all_posts.add(unique_posts)
            
            # Map action types to metric categories
            if action_type in ['view', 'impression']:
                metrics['impressions'] += count
            elif action_type in ['favorite', 'like']:
                metrics['likes'] += count
            elif action_type in ['click', 'view']:
                metrics['clicks'] += count
            elif action_type in ['bookmark']:
                metrics['bookmarks'] += count
            elif action_type in ['reblog', 'share']:
                metrics['reblogs'] += count
        
        # Calculate totals
        metrics['total_users'] = len(all_users)
        metrics['unique_posts'] = len(all_posts)
        
        # If no explicit impressions were tracked, estimate from total interactions
        if metrics['impressions'] == 0:
            total_interactions = sum([metrics['likes'], metrics['clicks'], metrics['bookmarks'], metrics['reblogs']])
            # Estimate impressions as 10x interactions (rough industry average)
            metrics['impressions'] = max(total_interactions * 10, total_interactions)
        
        # Calculate average response time if we have timing data in context
        cur.execute("""
            SELECT context
            FROM interactions 
            WHERE model_variant_id = %s
            AND created_at >= %s 
            AND created_at < %s
            AND context IS NOT NULL
        """, (variant_id, hour_start, hour_end))
        
        context_data = cur.fetchall()
        response_times = []
        
        for (context_json,) in context_data:
            try:
                context = json.loads(context_json) if isinstance(context_json, str) else context_json
                if 'response_time' in context:
                    response_times.append(float(context['response_time']))
            except:
                continue
        
        if response_times:
            metrics['avg_response_time'] = sum(response_times) / len(response_times)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating metrics for variant {variant_id}: {e}")
        return None


@celery.task(bind=True, name="analytics.cleanup_old_performance_data")
def cleanup_old_performance_data(self, days_to_keep: int = 30):
    """
    Clean up old performance data to prevent unlimited growth.
    
    Args:
        days_to_keep: Number of days of data to retain (default: 30)
    """
    try:
        logger.info(f"Cleaning up performance data older than {days_to_keep} days")
        
        if USE_IN_MEMORY_DB:
            logger.info("Skipping cleanup for in-memory database")
            return {"status": "skipped", "reason": "in_memory_db"}
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Delete old performance summaries
                cur.execute("""
                    DELETE FROM model_performance_summary 
                    WHERE date_hour < %s
                """, (cutoff_date,))
                
                deleted_count = cur.rowcount
                conn.commit()
                
                logger.info(f"Deleted {deleted_count} old performance summary records")
                
                return {
                    "status": "success",
                    "deleted_records": deleted_count,
                    "cutoff_date": cutoff_date.isoformat()
                }
                
    except Exception as e:
        logger.error(f"Error during performance data cleanup: {e}")
        raise


@celery.task(bind=True, name="analytics.generate_comparison_report")
def generate_comparison_report(self, variant_ids: List[int], days_back: int = 7):
    """
    Generate a detailed comparison report for multiple model variants.
    
    Args:
        variant_ids: List of variant IDs to compare
        days_back: Number of days to include in analysis (default: 7)
    """
    try:
        logger.info(f"Generating comparison report for variants {variant_ids} over {days_back} days")
        
        if USE_IN_MEMORY_DB:
            logger.info("Skipping report generation for in-memory database")
            return {"status": "skipped", "reason": "in_memory_db"}
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Get aggregated metrics for each variant
                variant_data = {}
                
                for variant_id in variant_ids:
                    cur.execute("""
                        SELECT 
                            SUM(impressions) as total_impressions,
                            SUM(likes) as total_likes,
                            SUM(clicks) as total_clicks,
                            SUM(bookmarks) as total_bookmarks,
                            SUM(reblogs) as total_reblogs,
                            AVG(engagement_rate) as avg_engagement_rate,
                            AVG(avg_response_time) as avg_response_time,
                            COUNT(DISTINCT total_users) as total_unique_users
                        FROM model_performance_summary
                        WHERE variant_id = %s
                        AND date_hour >= %s
                    """, (variant_id, start_date))
                    
                    result = cur.fetchone()
                    if result and result[0]:  # Has data
                        variant_data[variant_id] = {
                            'total_impressions': int(result[0] or 0),
                            'total_likes': int(result[1] or 0),
                            'total_clicks': int(result[2] or 0),
                            'total_bookmarks': int(result[3] or 0),
                            'total_reblogs': int(result[4] or 0),
                            'avg_engagement_rate': float(result[5] or 0),
                            'avg_response_time': float(result[6] or 0),
                            'total_unique_users': int(result[7] or 0)
                        }
                
                # Calculate comparisons and statistical significance
                comparison_results = {}
                if len(variant_data) >= 2:
                    variant_ids_sorted = sorted(variant_data.keys())
                    for i, variant_a in enumerate(variant_ids_sorted):
                        for variant_b in variant_ids_sorted[i+1:]:
                            comparison_key = f"{variant_a}_vs_{variant_b}"
                            comparison_results[comparison_key] = calculate_statistical_comparison(
                                variant_data[variant_a], 
                                variant_data[variant_b]
                            )
                
                return {
                    "status": "success",
                    "variant_data": variant_data,
                    "comparisons": comparison_results,
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": datetime.now().isoformat(),
                        "days": days_back
                    }
                }
                
    except Exception as e:
        logger.error(f"Error generating comparison report: {e}")
        raise


def calculate_statistical_comparison(data_a: Dict, data_b: Dict) -> Dict:
    """
    Calculate statistical comparison between two variants.
    
    Args:
        data_a: Performance data for variant A
        data_b: Performance data for variant B
        
    Returns:
        Dictionary with comparison metrics and significance tests
    """
    try:
        comparison = {}
        
        # Calculate percentage lifts for key metrics
        metrics_to_compare = ['avg_engagement_rate', 'total_likes', 'total_clicks', 'avg_response_time']
        
        for metric in metrics_to_compare:
            value_a = data_a.get(metric, 0)
            value_b = data_b.get(metric, 0)
            
            if value_a > 0:
                lift = ((value_b - value_a) / value_a) * 100
                comparison[f"{metric}_lift"] = round(lift, 2)
                
                # Simple significance test (in real world, would use more sophisticated tests)
                # For now, consider significant if lift is > 5% and sample sizes are reasonable
                sample_size_a = data_a.get('total_impressions', 0)
                sample_size_b = data_b.get('total_impressions', 0)
                
                is_significant = (
                    abs(lift) > 5.0 and 
                    sample_size_a > 100 and 
                    sample_size_b > 100
                )
                
                comparison[f"{metric}_significant"] = is_significant
                comparison[f"{metric}_winner"] = "B" if lift > 0 else "A" if lift < 0 else "tie"
            else:
                comparison[f"{metric}_lift"] = 0
                comparison[f"{metric}_significant"] = False
                comparison[f"{metric}_winner"] = "insufficient_data"
        
        return comparison
        
    except Exception as e:
        logger.error(f"Error calculating statistical comparison: {e}")
        return {}


# Schedule the aggregation task to run every hour
if CELERY_AVAILABLE and celery:
    # Add periodic task configuration
    from celery.schedules import crontab
    
    celery.conf.beat_schedule = celery.conf.beat_schedule or {}
    celery.conf.beat_schedule.update({
        'aggregate-model-performance': {
            'task': 'analytics.aggregate_model_performance',
            'schedule': crontab(minute=0),  # Run every hour
            'args': (2,),  # Aggregate last 2 hours to handle any delays
        },
        'cleanup-old-performance-data': {
            'task': 'analytics.cleanup_old_performance_data',
            'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
            'args': (30,),  # Keep 30 days of data
        },
    }) 