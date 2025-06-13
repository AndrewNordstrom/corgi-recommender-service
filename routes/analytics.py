"""
Analytics routes for the Corgi Recommender Service.

This module provides endpoints for retrieving analytics data about interactions
and post engagement.
"""

import logging
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import json
from typing import Optional

from db.connection import get_db_connection, get_cursor, USE_IN_MEMORY_DB
from utils.logging_decorator import log_route
from utils.privacy import generate_user_alias
from utils.rbac import require_role, get_user_from_request, require_permission

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
analytics_bp = Blueprint("analytics", __name__)

# Import authentication function
from routes.proxy import get_authenticated_user
import scipy.stats as stats
import numpy as np


@analytics_bp.route("/models/variants/<int:variant_id>/activate", methods=["POST"])
@log_route
def activate_model_variant(variant_id):
    """
    Activate a specific model variant for the authenticated user.
    
    This endpoint sets the active_model_variant_id for the user,
    which will be used by the recommendation system.
    
    Args:
        variant_id: ID of the variant to activate
        
    Returns:
        200 OK if activation successful
        401 Unauthorized if user not authenticated
        404 Not Found if variant doesn't exist
        500 Server Error on failure
    """
    try:
        # Get authenticated user
        user_data = get_authenticated_user()
        if not user_data:
            return jsonify({"error": "Authentication required"}), 401
        
        user_id = user_data.get('id') or user_data.get('username')
        if not user_id:
            return jsonify({"error": "Invalid user data"}), 401
            
        user_alias = generate_user_alias(str(user_id))
        
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # First verify the variant exists
                cur.execute("""
                    SELECT id, name, description 
                    FROM ab_variants 
                    WHERE id = %s
                """, (variant_id,))
                
                variant = cur.fetchone()
                if not variant:
                    return jsonify({"error": f"Variant {variant_id} not found"}), 404
                
                variant_info = {
                    'id': variant[0],
                    'name': variant[1], 
                    'description': variant[2]
                }
                
                # Check if user_identities table has active_model_variant_id column
                # If not, we'll need to add it or create a separate user_model_preferences table
                try:
                    cur.execute("""
                        UPDATE user_identities 
                        SET active_model_variant_id = %s 
                        WHERE user_alias = %s
                    """, (variant_id, user_alias))
                    
                    if cur.rowcount == 0:
                        # User doesn't exist in user_identities, create entry
                        cur.execute("""
                            INSERT INTO user_identities (user_alias, active_model_variant_id)
                            VALUES (%s, %s)
                        """, (user_alias, variant_id))
                        
                except Exception as e:
                    # Column might not exist, let's try a separate approach with user_model_preferences
                    logger.info("active_model_variant_id column not found, using user_model_preferences table")
                    
                    cur.execute("""
                        INSERT INTO user_model_preferences (user_alias, active_variant_id, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (user_alias)
                        DO UPDATE SET 
                            active_variant_id = EXCLUDED.active_variant_id,
                            updated_at = NOW()
                    """, (user_alias, variant_id))
                
                conn.commit()
                
                logger.info(f"Activated variant {variant_id} ({variant_info['name']}) for user {user_alias}")
                
                return jsonify({
                    "message": "Model variant activated successfully",
                    "variant": variant_info,
                    "user_alias": user_alias
                })
                
    except Exception as e:
        logger.error(f"Error activating variant {variant_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


def get_active_model_variant(user_alias: str) -> Optional[int]:
    """
    Get the active model variant ID for a user.
    
    Args:
        user_alias: The pseudonymized user ID
        
    Returns:
        variant_id if user has an active variant, None otherwise
    """
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Try user_identities table first
                try:
                    cur.execute("""
                        SELECT active_model_variant_id 
                        FROM user_identities 
                        WHERE user_alias = %s 
                        AND active_model_variant_id IS NOT NULL
                    """, (user_alias,))
                    
                    row = cur.fetchone()
                    if row and row[0]:
                        return row[0]
                        
                except Exception:
                    # Column might not exist, try user_model_preferences
                    pass
                
                # Try user_model_preferences table
                try:
                    cur.execute("""
                        SELECT active_variant_id 
                        FROM user_model_preferences 
                        WHERE user_alias = %s
                    """, (user_alias,))
                    
                    row = cur.fetchone()
                    if row and row[0]:
                        return row[0]
                        
                except Exception:
                    # Table might not exist yet
                    pass
                    
                return None
                
    except Exception as e:
        logger.error(f"Error getting active variant for user {user_alias}: {e}")
        return None


@analytics_bp.route("/interactions", methods=["GET"])
@log_route
def get_interaction_analytics():
    """
    Get analytics data about interactions.

    Query parameters:
        days (int): Number of days to look back (default: 7)
        user_id (str): Filter by user ID (optional)

    Returns:
        200 OK with analytics data
        500 Server Error on failure
    """
    days = request.args.get("days", default=7, type=int)
    user_id = request.args.get("user_id")

    # Limit to reasonable range
    if days > 90:
        days = 90

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Build query filters
    filters = "WHERE created_at >= %s AND created_at <= %s"
    params = [start_date, end_date]

    if user_id:
        user_alias = generate_user_alias(user_id)
        filters += " AND user_alias = %s"
        params.append(user_alias)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get total interactions by type
            cur.execute(
                f"""
                SELECT action_type, COUNT(*) as count
                FROM interactions
                {filters}
                GROUP BY action_type
                ORDER BY count DESC
            """,
                params,
            )

            interactions_by_type = cur.fetchall()

            # Get interactions by day
            cur.execute(
                f"""
                SELECT DATE(created_at) as date, action_type, COUNT(*) as count
                FROM interactions
                {filters}
                GROUP BY DATE(created_at), action_type
                ORDER BY date, action_type
            """,
                params,
            )

            interactions_by_day = cur.fetchall()

            # Get top posts by interactions
            cur.execute(
                f"""
                SELECT post_id, COUNT(*) as total_interactions
                FROM interactions
                {filters}
                GROUP BY post_id
                ORDER BY total_interactions DESC
                LIMIT 10
            """,
                params,
            )

            top_posts = cur.fetchall()

            # Get top users by interactions (pseudonymized)
            user_specific = " AND user_alias = %s" if user_id else ""
            cur.execute(
                f"""
                SELECT user_alias, COUNT(*) as total_interactions
                FROM interactions
                {filters} {user_specific}
                GROUP BY user_alias
                ORDER BY total_interactions DESC
                LIMIT 10
            """,
                params,
            )

            top_users = cur.fetchall()

    # Format the data for response
    # Format interactions by type
    formatted_by_type = [
        {"action_type": row[0], "count": row[1]} for row in interactions_by_type
    ]

    # Format interactions by day - convert to a structure for charting
    days_dict = {}
    for row in interactions_by_day:
        date_str = row[0].isoformat()
        action_type = row[1]
        count = row[2]

        if date_str not in days_dict:
            days_dict[date_str] = {"date": date_str}

        days_dict[date_str][action_type] = count

    formatted_by_day = list(days_dict.values())

    # Format top posts
    formatted_top_posts = [
        {"post_id": row[0], "total_interactions": row[1]} for row in top_posts
    ]

    # Format top users (pseudonymized)
    formatted_top_users = [
        {"user_alias": row[0], "total_interactions": row[1]} for row in top_users
    ]

    return jsonify(
        {
            "interactions_by_type": formatted_by_type,
            "interactions_by_day": formatted_by_day,
            "top_posts": formatted_top_posts,
            "top_users": formatted_top_users,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days,
            },
        }
    )


@analytics_bp.route("/posts", methods=["GET"])
@log_route
def get_post_analytics():
    """
    Get analytics data about posts.

    Query parameters:
        days (int): Number of days to look back (default: 7)

    Returns:
        200 OK with analytics data
        500 Server Error on failure
    """
    days = request.args.get("days", default=7, type=int)

    # Limit to reasonable range
    if days > 90:
        days = 90

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get posts by day
            cur.execute(
                """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM post_metadata
                WHERE created_at >= %s AND created_at <= %s
                GROUP BY DATE(created_at)
                ORDER BY date
            """,
                [start_date, end_date],
            )

            posts_by_day = cur.fetchall()

            # Get posts by content type
            cur.execute(
                """
                SELECT content_type, COUNT(*) as count
                FROM post_metadata
                WHERE created_at >= %s AND created_at <= %s
                GROUP BY content_type
                ORDER BY count DESC
            """,
                [start_date, end_date],
            )

            posts_by_type = cur.fetchall()

            # Get top authors by post count
            cur.execute(
                """
                SELECT author_id, COUNT(*) as post_count
                FROM post_metadata
                WHERE created_at >= %s AND created_at <= %s
                GROUP BY author_id
                ORDER BY post_count DESC
                LIMIT 10
            """,
                [start_date, end_date],
            )

            top_authors = cur.fetchall()

            # Get top posts by interaction count
            cur.execute(
                """
                SELECT 
                    pm.post_id,
                    pm.content_type,
                    pm.author_id,
                    COALESCE(
                        (pm.interaction_counts->>'favorites')::int, 0
                    ) +
                    COALESCE(
                        (pm.interaction_counts->>'reblogs')::int, 0
                    ) +
                    COALESCE(
                        (pm.interaction_counts->>'replies')::int, 0
                    ) as total_interactions
                FROM post_metadata pm
                WHERE pm.created_at >= %s AND pm.created_at <= %s
                ORDER BY total_interactions DESC
                LIMIT 10
            """,
                [start_date, end_date],
            )

            top_posts = cur.fetchall()

    # Format the response data
    formatted_by_day = [
        {"date": row[0].isoformat(), "count": row[1]} for row in posts_by_day
    ]

    formatted_by_type = [
        {"content_type": row[0], "count": row[1]} for row in posts_by_type
    ]

    formatted_top_authors = [
        {"author_id": row[0], "post_count": row[1]} for row in top_authors
    ]

    formatted_top_posts = [
        {
            "post_id": row[0],
            "content_type": row[1],
            "author_id": row[2],
            "total_interactions": row[3],
        }
        for row in top_posts
    ]

    return jsonify(
        {
            "posts_by_day": formatted_by_day,
            "posts_by_type": formatted_by_type,
            "top_authors": formatted_top_authors,
            "top_posts": formatted_top_posts,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days,
            },
        }
    )


@analytics_bp.route("/comparison", methods=["GET"])
@log_route
def get_model_comparison():
    """
    Compare performance metrics for multiple model variants.
    
    Query parameters:
        ids (list): List of variant IDs to compare (e.g., ?ids=1&ids=2&ids=5)
        days (int): Number of days to look back (default: 7)
        
    Returns:
        200 OK with comparison data including time series and statistical analysis
        400 Bad Request if insufficient parameters
        401 Unauthorized if user not authenticated
        500 Server Error on failure
    """
    try:
        # Get authenticated user
        user_data = get_authenticated_user()
        if not user_data:
            return jsonify({"error": "Authentication required"}), 401
        
        # Parse variant IDs from query parameters
        variant_ids = request.args.getlist('ids', type=int)
        days = request.args.get('days', default=7, type=int)
        
        if len(variant_ids) < 2:
            return jsonify({
                "error": "At least 2 variant IDs required for comparison",
                "provided": len(variant_ids)
            }), 400
        
        if days > 90:
            days = 90
            
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Comparing variants {variant_ids} over {days} days")
        
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Verify all variants exist
                cur.execute("""
                    SELECT id, name, description 
                    FROM ab_variants 
                    WHERE id = ANY(%s)
                """, (variant_ids,))
                
                found_variants = cur.fetchall()
                found_ids = [v[0] for v in found_variants]
                
                missing_ids = set(variant_ids) - set(found_ids)
                if missing_ids:
                    return jsonify({
                        "error": f"Variant IDs not found: {list(missing_ids)}"
                    }), 400
                
                # Build variant info lookup
                variant_info = {
                    v[0]: {"id": v[0], "name": v[1], "description": v[2]}
                    for v in found_variants
                }
                
                # Get time series data for each variant
                time_series_data = {}
                summary_data = {}
                
                for variant_id in variant_ids:
                    # Get hourly performance data
                    cur.execute("""
                        SELECT 
                            date_hour,
                            impressions,
                            likes,
                            clicks,
                            bookmarks,
                            reblogs,
                            engagement_rate,
                            avg_response_time,
                            total_users,
                            unique_posts
                        FROM model_performance_summary
                        WHERE variant_id = %s
                        AND date_hour >= %s
                        AND date_hour <= %s
                        ORDER BY date_hour
                    """, (variant_id, start_date, end_date))
                    
                    hourly_data = cur.fetchall()
                    
                    # Format time series data
                    time_series_data[variant_id] = [
                        {
                            "timestamp": row[0].isoformat(),
                            "impressions": row[1] or 0,
                            "likes": row[2] or 0,
                            "clicks": row[3] or 0,
                            "bookmarks": row[4] or 0,
                            "reblogs": row[5] or 0,
                            "engagement_rate": float(row[6] or 0),
                            "avg_response_time": float(row[7] or 0),
                            "total_users": row[8] or 0,
                            "unique_posts": row[9] or 0
                        }
                        for row in hourly_data
                    ]
                    
                    # Calculate summary statistics
                    if hourly_data:
                        total_impressions = sum(row[1] or 0 for row in hourly_data)
                        total_likes = sum(row[2] or 0 for row in hourly_data)
                        total_clicks = sum(row[3] or 0 for row in hourly_data)
                        total_bookmarks = sum(row[4] or 0 for row in hourly_data)
                        total_reblogs = sum(row[5] or 0 for row in hourly_data)
                        
                        # Calculate weighted average engagement rate
                        weighted_engagement = sum(
                            (row[6] or 0) * (row[1] or 1) 
                            for row in hourly_data
                        )
                        total_weights = sum(row[1] or 1 for row in hourly_data)
                        avg_engagement_rate = weighted_engagement / total_weights if total_weights > 0 else 0
                        
                        # Calculate average response time
                        response_times = [float(row[7] or 0) for row in hourly_data if row[7]]
                        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                        
                        # Calculate total unique metrics
                        total_unique_users = len(set(row[8] for row in hourly_data if row[8]))
                        total_unique_posts = len(set(row[9] for row in hourly_data if row[9]))
                        
                        summary_data[variant_id] = {
                            "total_impressions": total_impressions,
                            "total_likes": total_likes,
                            "total_clicks": total_clicks,
                            "total_bookmarks": total_bookmarks,
                            "total_reblogs": total_reblogs,
                            "avg_engagement_rate": round(avg_engagement_rate, 4),
                            "avg_response_time": round(avg_response_time, 2),
                            "total_unique_users": total_unique_users,
                            "total_unique_posts": total_unique_posts,
                            "total_interactions": total_likes + total_clicks + total_bookmarks + total_reblogs
                        }
                    else:
                        # No data for this variant
                        summary_data[variant_id] = {
                            "total_impressions": 0,
                            "total_likes": 0,
                            "total_clicks": 0,
                            "total_bookmarks": 0,
                            "total_reblogs": 0,
                            "avg_engagement_rate": 0,
                            "avg_response_time": 0,
                            "total_unique_users": 0,
                            "total_unique_posts": 0,
                            "total_interactions": 0
                        }
                
                # Calculate statistical comparisons
                comparisons = calculate_variant_comparisons(summary_data, time_series_data, variant_info)
                
                # Determine the best performing variant
                best_variant = determine_best_variant(summary_data, variant_info)
                
                return jsonify({
                    "status": "success",
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "days": days
                    },
                    "variants": variant_info,
                    "time_series": time_series_data,
                    "summary": summary_data,
                    "comparisons": comparisons,
                    "best_variant": best_variant,
                    "metadata": {
                        "comparison_generated_at": datetime.now().isoformat(),
                        "variants_compared": len(variant_ids),
                        "data_points_per_variant": len(time_series_data[variant_ids[0]]) if variant_ids else 0
                    }
                })
                
    except Exception as e:
        logger.error(f"Error generating model comparison: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


def calculate_variant_comparisons(summary_data, time_series_data, variant_info):
    """
    Calculate statistical comparisons between variants.
    
    Args:
        summary_data: Dictionary of summary statistics for each variant
        time_series_data: Dictionary of time series data for each variant
        variant_info: Dictionary of variant metadata
        
    Returns:
        Dictionary with pairwise comparisons and statistical significance tests
    """
    comparisons = {}
    variant_ids = list(summary_data.keys())
    
    # Metrics to compare
    key_metrics = [
        'avg_engagement_rate',
        'avg_response_time', 
        'total_interactions',
        'total_impressions'
    ]
    
    # Pairwise comparisons
    for i, variant_a in enumerate(variant_ids):
        for variant_b in variant_ids[i+1:]:
            comparison_key = f"{variant_a}_vs_{variant_b}"
            variant_a_name = variant_info[variant_a]['name']
            variant_b_name = variant_info[variant_b]['name']
            
            comparison = {
                "variant_a": {
                    "id": variant_a,
                    "name": variant_a_name
                },
                "variant_b": {
                    "id": variant_b,
                    "name": variant_b_name
                },
                "metrics": {}
            }
            
            for metric in key_metrics:
                value_a = summary_data[variant_a].get(metric, 0)
                value_b = summary_data[variant_b].get(metric, 0)
                
                # Calculate percentage lift
                if value_a > 0:
                    lift_percent = ((value_b - value_a) / value_a) * 100
                else:
                    lift_percent = 0 if value_b == 0 else float('inf')
                
                # Determine winner
                if lift_percent > 5:
                    winner = variant_b_name
                    winner_id = variant_b
                elif lift_percent < -5:
                    winner = variant_a_name
                    winner_id = variant_a
                else:
                    winner = "tie"
                    winner_id = None
                
                # Statistical significance test using time series data
                significance = calculate_statistical_significance(
                    time_series_data[variant_a],
                    time_series_data[variant_b],
                    metric
                )
                
                comparison["metrics"][metric] = {
                    "value_a": round(value_a, 4),
                    "value_b": round(value_b, 4),
                    "lift_percent": round(lift_percent, 2),
                    "winner": winner,
                    "winner_id": winner_id,
                    "statistical_significance": significance
                }
            
            comparisons[comparison_key] = comparison
    
    return comparisons


def calculate_statistical_significance(data_a, data_b, metric):
    """
    Calculate statistical significance using Mann-Whitney U test.
    
    Args:
        data_a: Time series data for variant A
        data_b: Time series data for variant B
        metric: Metric name to compare
        
    Returns:
        Dictionary with statistical test results
    """
    try:
        # Extract metric values from time series data
        values_a = [point.get(metric, 0) for point in data_a if point.get(metric) is not None]
        values_b = [point.get(metric, 0) for point in data_b if point.get(metric) is not None]
        
        if len(values_a) < 5 or len(values_b) < 5:
            return {
                "test": "insufficient_data",
                "p_value": None,
                "is_significant": False,
                "confidence_level": None,
                "sample_size_a": len(values_a),
                "sample_size_b": len(values_b)
            }
        
        # Perform Mann-Whitney U test (non-parametric)
        try:
            statistic, p_value = stats.mannwhitneyu(
                values_a, values_b, 
                alternative='two-sided'
            )
            
            is_significant = p_value < 0.05
            confidence_level = (1 - p_value) * 100 if p_value > 0 else 99.9
            
            return {
                "test": "mann_whitney_u",
                "statistic": float(statistic),
                "p_value": round(float(p_value), 6),
                "is_significant": is_significant,
                "confidence_level": round(confidence_level, 2),
                "sample_size_a": len(values_a),
                "sample_size_b": len(values_b)
            }
            
        except Exception as e:
            logger.warning(f"Statistical test failed for {metric}: {e}")
            return {
                "test": "failed",
                "error": str(e),
                "is_significant": False,
                "sample_size_a": len(values_a),
                "sample_size_b": len(values_b)
            }
            
    except Exception as e:
        logger.error(f"Error calculating significance for {metric}: {e}")
        return {
            "test": "error",
            "error": str(e),
            "is_significant": False
        }


def determine_best_variant(summary_data, variant_info):
    """
    Determine the best performing variant based on multiple criteria.
    
    Args:
        summary_data: Dictionary of summary statistics for each variant
        variant_info: Dictionary of variant metadata
        
    Returns:
        Dictionary with best variant information
    """
    try:
        if not summary_data:
            return None
        
        # Scoring criteria with weights
        scoring_criteria = {
            'avg_engagement_rate': {'weight': 0.4, 'higher_is_better': True},
            'total_interactions': {'weight': 0.3, 'higher_is_better': True},
            'avg_response_time': {'weight': 0.2, 'higher_is_better': False},  # Lower is better
            'total_unique_users': {'weight': 0.1, 'higher_is_better': True}
        }
        
        variant_scores = {}
        
        # Calculate normalized scores for each variant
        for variant_id, data in summary_data.items():
            total_score = 0
            
            for metric, config in scoring_criteria.items():
                value = data.get(metric, 0)
                weight = config['weight']
                
                # Get all values for this metric for normalization
                all_values = [d.get(metric, 0) for d in summary_data.values()]
                max_value = max(all_values) if all_values else 1
                min_value = min(all_values) if all_values else 0
                
                # Normalize to 0-1 scale
                if max_value == min_value:
                    normalized_value = 0.5
                else:
                    if config['higher_is_better']:
                        normalized_value = (value - min_value) / (max_value - min_value)
                    else:
                        # For metrics where lower is better (like response time)
                        normalized_value = (max_value - value) / (max_value - min_value)
                
                total_score += normalized_value * weight
            
            variant_scores[variant_id] = {
                'score': round(total_score, 4),
                'name': variant_info[variant_id]['name'],
                'data': data
            }
        
        # Find the highest scoring variant
        best_variant_id = max(variant_scores.keys(), key=lambda k: variant_scores[k]['score'])
        best_variant = variant_scores[best_variant_id]
        
        return {
            "variant_id": best_variant_id,
            "name": best_variant['name'],
            "score": best_variant['score'],
            "metrics": best_variant['data'],
            "reasoning": "Based on weighted scoring of engagement rate (40%), total interactions (30%), response time (20%), and unique users (10%)"
        }
        
    except Exception as e:
        logger.error(f"Error determining best variant: {e}")
        return None


# ---------------------------------------------------------------------------
# A/B Experiment Creation Endpoint (admin-only)
# ---------------------------------------------------------------------------


@analytics_bp.route("/experiments", methods=["POST"])
@require_role("admin")  # Only admins/owners can create experiments
@log_route
def create_ab_experiment():
    """Create a new A/B test experiment (status = DRAFT).

    Expected JSON body:
    {
        "name": "Recency vs. Engagement Model Test",
        "description": "string",
        "variants": [
            {"model_variant_id": 1, "traffic_allocation": 0.5},
            {"model_variant_id": 2, "traffic_allocation": 0.5}
        ]
    }
    """
    try:
        data = request.get_json(silent=True) or {}

        name = data.get("name")
        description = data.get("description", "")
        variants = data.get("variants", [])

        # --- Basic validation ------------------------------------------------
        if not name or not isinstance(name, str):
            return jsonify({"error": "'name' is required and must be a string"}), 400

        if not variants or not isinstance(variants, list):
            return jsonify({"error": "'variants' must be a non-empty list"}), 400

        total_alloc = 0.0
        for idx, v in enumerate(variants):
            if not isinstance(v, dict):
                return jsonify({"error": f"Variant at index {idx} must be an object"}), 400

            if "model_variant_id" not in v or "traffic_allocation" not in v:
                return jsonify({"error": "Each variant requires 'model_variant_id' and 'traffic_allocation'"}), 400

            try:
                v["model_variant_id"] = int(v["model_variant_id"])
                v["traffic_allocation"] = float(v["traffic_allocation"])
            except (ValueError, TypeError):
                return jsonify({"error": f"Invalid types for variant at index {idx}"}), 400

            if v["traffic_allocation"] <= 0:
                return jsonify({"error": "traffic_allocation must be > 0"}), 400

            total_alloc += v["traffic_allocation"]

        if abs(total_alloc - 1.0) > 1e-6:
            return jsonify({"error": "Sum of traffic_allocation values must equal 1.0"}), 400

        # --- DB insert wrapped in transaction --------------------------------
        placeholder = "%s" if not USE_IN_MEMORY_DB else "?"

        insert_exp_sql = (
            f"INSERT INTO ab_experiments (name, description, status) VALUES ({placeholder}, {placeholder}, {placeholder})"
            + (" RETURNING id" if not USE_IN_MEMORY_DB else "")
        )

        insert_var_sql = (
            f"INSERT INTO ab_experiment_variants (experiment_id, model_variant_id, traffic_allocation) VALUES ({placeholder}, {placeholder}, {placeholder})"
        )

        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Ensure experiment table exists (esp. for SQLite tests)
                try:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS ab_experiments (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            description TEXT,
                            status TEXT DEFAULT 'DRAFT',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS ab_experiment_variants (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            experiment_id INTEGER NOT NULL,
                            model_variant_id INTEGER NOT NULL,
                            traffic_allocation REAL NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                except Exception:
                    # Ignore errors if tables already exist (PostgreSQL path)
                    pass

                # Insert experiment
                cur.execute(insert_exp_sql, (name, description, "DRAFT"))

                experiment_id = (
                    cur.fetchone()[0] if not USE_IN_MEMORY_DB else cur.lastrowid
                )

                # Insert variants
                for v in variants:
                    cur.execute(insert_var_sql, (experiment_id, v["model_variant_id"], v["traffic_allocation"]))

                conn.commit()

        return (
            jsonify(
                {
                    "id": experiment_id,
                    "name": name,
                    "description": description,
                    "status": "DRAFT",
                    "variants": variants,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error creating A/B experiment: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Experiment Management Endpoints
# ---------------------------------------------------------------------------


# Helper to convert experiment row to dict (works for PG and SQLite)
def _experiment_row_to_dict(row, cursor):
    """Convert DB row to dict. If cursor provided, use its description; else assume standard column order."""
    if cursor is not None:
        columns = [col[0] for col in cursor.description]
    else:
        columns = ["id", "name", "description", "status", "created_at"]
    return {columns[i]: row[i] for i in range(len(columns))}


@analytics_bp.route("/experiments", methods=["GET"])
@require_permission("view_analytics")
@log_route
def list_ab_experiments():
    """Return all A/B experiments ordered by creation date desc."""
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(
                    "SELECT id, name, description, status, created_at FROM ab_experiments ORDER BY created_at DESC"
                )
                rows = cur.fetchall()
                experiments = [_experiment_row_to_dict(r, cur) for r in rows]

        return jsonify({"experiments": experiments}), 200
    except Exception as e:
        logger.error(f"Error listing experiments: {e}")
        return jsonify({"error": "Internal server error"}), 500


def _update_experiment_status(experiment_id: int, target_status: str, allowed_current: tuple):
    """Internal helper to change experiment status with validation."""
    placeholder = "%s" if not USE_IN_MEMORY_DB else "?"

    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            # Ensure tables exist (SQLite dev)
            cur.execute(
                """CREATE TABLE IF NOT EXISTS ab_experiments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        description TEXT,
                        status TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
            )

            # If starting, ensure no other running exp
            if target_status == "RUNNING":
                cur.execute(
                    "SELECT id FROM ab_experiments WHERE status = 'RUNNING' AND id <> " + placeholder,
                    (experiment_id,),
                )
                if cur.fetchone():
                    return None, 409, "Another experiment is already running."

            # Check current status
            cur.execute(
                "SELECT status FROM ab_experiments WHERE id = " + placeholder,
                (experiment_id,),
            )
            row = cur.fetchone()
            if not row:
                return None, 404, "Experiment not found."

            current_status = row[0]
            if current_status not in allowed_current:
                return None, 400, f"Cannot change status from {current_status} to {target_status}."

            # Update
            cur.execute(
                "UPDATE ab_experiments SET status = " + placeholder + " WHERE id = " + placeholder,
                (target_status, experiment_id),
            )
            conn.commit()

            # Return updated row
            cur.execute(
                "SELECT id, name, description, status, created_at FROM ab_experiments WHERE id = "
                + placeholder,
                (experiment_id,),
            )
            updated = cur.fetchone()
            return updated, 200, None


@analytics_bp.route("/experiments/<int:experiment_id>/start", methods=["POST"])
@require_role("admin")
@log_route
def start_ab_experiment(experiment_id):
    row, code, err = _update_experiment_status(
        experiment_id, "RUNNING", allowed_current=("DRAFT",)
    )
    if err:
        return jsonify({"error": err}), code
    return jsonify(_experiment_row_to_dict(row, None)), 200


@analytics_bp.route("/experiments/<int:experiment_id>/stop", methods=["POST"])
@require_role("admin")
@log_route
def stop_ab_experiment(experiment_id):
    row, code, err = _update_experiment_status(
        experiment_id, "COMPLETED", allowed_current=("RUNNING",)
    )
    if err:
        return jsonify({"error": err}), code
    return jsonify(_experiment_row_to_dict(row, None)), 200