"""
Analytics routes for the Corgi Recommender Service.

This module provides endpoints for retrieving analytics data about interactions
and post engagement.
"""

import logging
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import json

from db.connection import get_db_connection
from utils.logging_decorator import log_route
from utils.privacy import generate_user_alias

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
analytics_bp = Blueprint("analytics", __name__)


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
