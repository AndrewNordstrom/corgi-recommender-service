"""
Recommendation routes for the Corgi Recommender Service.

This module provides endpoints for generating and retrieving personalized post 
recommendations for users.
"""

import logging
import json
from flask import Blueprint, request, jsonify
from datetime import datetime

from db.connection import get_db_connection, get_cursor, USE_IN_MEMORY_DB
from core.ranking_algorithm import generate_rankings_for_user
from utils.privacy import generate_user_alias
from utils.logging_decorator import log_route

# Set up logging
logger = logging.getLogger(__name__)

# Check if async tasks (Celery) are available
try:
    from utils.celery_app import celery
    ASYNC_TASKS_AVAILABLE = True
    logger.info("Async tasks (Celery) are available")
except ImportError:
    ASYNC_TASKS_AVAILABLE = False
    logger.warning("Async tasks (Celery) are not available - running in synchronous mode")

# Create blueprint
recommendations_bp = Blueprint("recommendations", __name__)

# Import authentication function
from routes.proxy import get_authenticated_user


@recommendations_bp.route("/rankings/generate", methods=["POST"])
@log_route
def generate_rankings():
    """
    Generate personalized rankings for a user.

    Request body:
    {
        "user_id": "123",
        "force_refresh": false // Optional: Force recalculation even if recent rankings exist
    }

    Returns:
        201 Created if new rankings were generated
        200 OK if using existing rankings
        400 Bad Request if required fields are missing
        500 Server Error on failure
    """
    data = request.json

    # Validate required fields
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing required field: user_id"}), 400

    # Get pseudonymized user ID for privacy
    user_alias = generate_user_alias(user_id)

    # Check if we need to generate new rankings
    force_refresh = data.get("force_refresh", False)

    if not force_refresh and not USE_IN_MEMORY_DB:
        # Check if we already have recent rankings for this user
        # (Skip for SQLite since we always regenerate in-memory)
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # For PostgreSQL only
                cur.execute(
                    """
                    SELECT COUNT(*) FROM post_rankings 
                    WHERE user_id = %s 
                    AND created_at > NOW() - INTERVAL '1 hour'
                """,
                    (user_alias,),
                )

                count = cur.fetchone()[0]

                # If we have recent rankings and aren't forcing a refresh, return early
                if count > 0:
                    logger.info(
                        f"Using existing rankings for user {user_alias} (count: {count})"
                    )
                    return (
                        jsonify({"message": "Using existing rankings", "count": count}),
                        200,
                    )

    # Generate new rankings
    try:
        if USE_IN_MEMORY_DB:
            # Simplified in-memory version for demo/testing
            with get_db_connection() as conn:
                with get_cursor(conn) as cur:
                    # Get all posts from our test DB
                    cur.execute("SELECT post_id FROM posts")
                    post_ids = [row[0] for row in cur.fetchall()]

                    # Create a simple recommendation for each post
                    recommendations = []
                    for i, post_id in enumerate(post_ids):
                        recommendations.append(
                            {
                                "post_id": post_id,
                                "user_id": user_alias,
                                "score": 0.9 - (0.1 * i),  # Simple descending scores
                                "reason": "Recommended based on content similarity",
                            }
                        )

                    # Clear existing recommendations
                    cur.execute(
                        "DELETE FROM recommendations WHERE user_id = ?", (user_alias,)
                    )

                    # Insert new recommendations
                    for rec in recommendations:
                        cur.execute(
                            """
                            INSERT INTO recommendations (user_id, post_id, score, reason)
                            VALUES (?, ?, ?, ?)
                        """,
                            (
                                rec["user_id"],
                                rec["post_id"],
                                rec["score"],
                                rec["reason"],
                            ),
                        )

                    conn.commit()

                    logger.info(
                        f"Generated {len(recommendations)} test rankings for user {user_alias}"
                    )
                    return (
                        jsonify(
                            {
                                "message": "Test rankings generated successfully",
                                "count": len(recommendations),
                            }
                        ),
                        201,
                    )
        else:
            # Original version for PostgreSQL
            ranked_posts = generate_rankings_for_user(user_id)
            logger.info(
                f"Generated {len(ranked_posts)} ranked posts for user {user_alias}"
            )

            return (
                jsonify(
                    {
                        "message": "Rankings generated successfully",
                        "count": len(ranked_posts),
                    }
                ),
                201,
            )
    except Exception as e:
        logger.error(f"Error during ranking generation: {e}")
        return (
            jsonify({"error": "An internal error occurred during ranking generation"}),
            500,
        )


@recommendations_bp.route("/timelines/recommended", methods=["GET"])
@log_route
def get_recommended_timeline():
    """
    Get personalized timeline recommendations for a user.

    Query parameters:
        user_id: ID of the user to get recommendations for
        limit: Maximum number of recommendations to return (default: 20)

    Returns:
        200 OK with Mastodon-compatible posts sorted by ranking_score
        400 Bad Request if required parameters are missing
        404 Not Found if no recommendations exist
        500 Server Error on failure
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing required parameter: user_id"}), 400

    limit = request.args.get("limit", default=20, type=int)

    # Get pseudonymized user ID for privacy
    user_alias = generate_user_alias(user_id)

    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            if USE_IN_MEMORY_DB:
                # SQLite in-memory version
                # Check if we have recommendations for this user
                cur.execute(
                    "SELECT COUNT(*) FROM recommendations WHERE user_id = ?",
                    (user_alias,),
                )
                rec_count = cur.fetchone()[0]

                if rec_count == 0:
                    # Try to generate rankings first
                    try:
                        # Call our rankings generation endpoint directly
                        data = {"user_id": user_id, "force_refresh": True}
                        generate_rankings.__wrapped__(data)
                    except Exception as e:
                        logger.error(f"Failed to auto-generate rankings: {e}")
                        return jsonify([]), 200  # Return empty array for compatibility

                # Get recommendations and join with posts
                cur.execute(
                    """
                    SELECT r.post_id, r.score, r.reason, p.content, p.author_id, p.created_at, p.metadata
                    FROM recommendations r
                    JOIN posts p ON r.post_id = p.post_id
                    WHERE r.user_id = ?
                    ORDER BY r.score DESC
                    LIMIT ?
                """,
                    (user_alias, limit),
                )

                recommendations = []
                for row in cur.fetchall():
                    (
                        post_id,
                        score,
                        reason,
                        content,
                        author_id,
                        created_at,
                        metadata_str,
                    ) = row

                    # Parse metadata if available
                    try:
                        metadata = json.loads(metadata_str) if metadata_str else {}
                    except:
                        metadata = {}

                    author_name = metadata.get("author_name", "User")

                    # Create a Mastodon-compatible post format
                    post_data = {
                        "id": post_id,
                        "content": content,
                        "created_at": created_at,
                        "account": {
                            "id": author_id,
                            "username": author_name,
                            "display_name": author_name,
                            "url": f"https://example.com/@{author_name}",
                        },
                        "language": "en",
                        "favourites_count": 0,
                        "reblogs_count": 0,
                        "replies_count": 0,
                        "ranking_score": score,
                        "recommendation_reason": reason,
                        "is_real_mastodon_post": False,
                        "is_synthetic": True,
                    }

                    # Add to recommendations
                    recommendations.append(post_data)

                return jsonify(recommendations)
            else:
                # PostgreSQL version
                placeholder = "%s"

                # Get the ranked post IDs and scores with full post info
                cur.execute(
                    f"""
                    SELECT pr.post_id, pr.ranking_score, pr.recommendation_reason, 
                           pm.mastodon_post, pm.author_id, pm.author_name, 
                           pm.content, pm.created_at, pm.interaction_counts
                    FROM post_rankings pr
                    JOIN post_metadata pm ON pr.post_id = pm.post_id
                    WHERE pr.user_id = {placeholder}
                    ORDER BY pr.ranking_score DESC
                    LIMIT {placeholder}
                """,
                    (user_alias, limit),
                )

                ranking_data = cur.fetchall()

                if not ranking_data:
                    # Try to auto-generate rankings
                    try:
                        ranked_posts = generate_rankings_for_user(user_id)
                        if ranked_posts:
                            logger.info(
                                f"Auto-generated {len(ranked_posts)} rankings for user {user_alias}"
                            )

                            # Now try to fetch the posts again
                            cur.execute(
                                f"""
                                SELECT pr.post_id, pr.ranking_score, pr.recommendation_reason, 
                                       pm.mastodon_post, pm.author_id, pm.author_name, 
                                       pm.content, pm.created_at, pm.interaction_counts
                                FROM post_rankings pr
                                JOIN post_metadata pm ON pr.post_id = pm.post_id
                                WHERE pr.user_id = {placeholder}
                                ORDER BY pr.ranking_score DESC
                                LIMIT {placeholder}
                            """,
                                (user_alias, limit),
                            )

                            ranking_data = cur.fetchall()

                        if not ranking_data:
                            logger.warning(
                                f"No recommendations available for user {user_alias} even after auto-generation"
                            )
                            return (
                                jsonify([]),
                                200,
                            )  # Return empty array for compatibility

                    except Exception as e:
                        logger.error(f"Failed to auto-generate rankings: {e}")
                        return jsonify([]), 200  # Return empty array for compatibility

                # Process the recommendations into Mastodon-compatible format
                recommendations = []
                for row in ranking_data:
                    (
                        post_id,
                        score,
                        reason,
                        mastodon_post,
                        author_id,
                        author_name,
                        content,
                        created_at,
                        interaction_counts,
                    ) = row

                    try:
                        # If we have a stored Mastodon post, use that as the base
                        if mastodon_post:
                            if isinstance(mastodon_post, str):
                                post_data = json.loads(mastodon_post)
                            else:
                                post_data = mastodon_post
                        else:
                            # Otherwise, construct a compatible format from our stored fields
                            post_data = {
                                "id": post_id,
                                "created_at": (
                                    created_at.isoformat()
                                    if hasattr(created_at, "isoformat")
                                    else created_at or datetime.now().isoformat()
                                ),
                                "account": {
                                    "id": author_id,
                                    "username": author_name or "user",
                                    "display_name": author_name or "User",
                                },
                                "content": content or "",
                                "favourites_count": 0,
                                "reblogs_count": 0,
                                "replies_count": 0,
                            }

                            # Add interaction counts if available
                            if interaction_counts:
                                try:
                                    if isinstance(interaction_counts, str):
                                        counts = json.loads(interaction_counts)
                                    else:
                                        counts = interaction_counts

                                    post_data["favourites_count"] = counts.get(
                                        "favorites", 0
                                    )
                                    post_data["reblogs_count"] = counts.get(
                                        "reblogs", 0
                                    )
                                    post_data["replies_count"] = counts.get(
                                        "replies", 0
                                    )
                                except:
                                    pass

                        # Add recommendation metadata
                        post_data["id"] = post_id  # Ensure correct ID
                        post_data["ranking_score"] = score
                        post_data["recommendation_reason"] = reason

                        recommendations.append(post_data)
                    except Exception as e:
                        logger.error(f"Error processing post {post_id}: {e}")

    return jsonify(recommendations)


@recommendations_bp.route("", methods=["GET"])
@log_route
def get_recommendations():
    """
    Get personalized recommendations for a user.

    Query parameters:
        user_id: ID of the user to get recommendations for
        limit: Maximum number of recommendations to return (default: 10)

    Returns:
        200 OK with recommendations
        400 Bad Request if required parameters are missing
        404 Not Found if no recommendations exist
        500 Server Error on failure
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing required parameter: user_id"}), 400

    limit = request.args.get("limit", default=10, type=int)

    # Get pseudonymized user ID for privacy
    user_alias = generate_user_alias(user_id)

    # Different implementations for SQLite and PostgreSQL
    if USE_IN_MEMORY_DB:
        # SQLite in-memory version
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Check if we have recommendations for this user
                cur.execute(
                    "SELECT COUNT(*) FROM recommendations WHERE user_id = ?",
                    (user_alias,),
                )
                rec_count = cur.fetchone()[0]

                if rec_count == 0:
                    # Try to generate rankings first
                    try:
                        # Call our rankings generation endpoint
                        data = {"user_id": user_id, "force_refresh": True}
                        generate_rankings_result = generate_rankings.__wrapped__(data)

                        # Now check if we have recommendations
                        cur.execute(
                            "SELECT COUNT(*) FROM recommendations WHERE user_id = ?",
                            (user_alias,),
                        )
                        rec_count = cur.fetchone()[0]

                        if rec_count == 0:
                            # Still no recommendations
                            return jsonify(
                                {
                                    "user_id": user_id,
                                    "recommendations": [],
                                    "message": "No recommendations could be generated",
                                    "debug_info": {"auto_generation_attempted": True},
                                }
                            )
                    except Exception as e:
                        logger.error(f"Failed to auto-generate rankings: {e}")
                        return jsonify(
                            {
                                "user_id": user_id,
                                "recommendations": [],
                                "message": "Unable to generate recommendations at this time",
                                "debug_info": {"error_occurred": True},
                            }
                        )

                # Get recommendations and join with posts
                cur.execute(
                    """
                    SELECT r.post_id, r.score, r.reason, p.content, p.author_id, p.created_at, p.metadata
                    FROM recommendations r
                    JOIN posts p ON r.post_id = p.post_id
                    WHERE r.user_id = ?
                    ORDER BY r.score DESC
                    LIMIT ?
                """,
                    (user_alias, limit),
                )

                recommendations = []
                for row in cur.fetchall():
                    (
                        post_id,
                        score,
                        reason,
                        content,
                        author_id,
                        created_at,
                        metadata_str,
                    ) = row

                    # Parse metadata if available
                    try:
                        metadata = json.loads(metadata_str) if metadata_str else {}
                    except:
                        metadata = {}

                    author_name = metadata.get("author_name", "User")

                    # Create a Mastodon-compatible post format
                    post_data = {
                        "id": post_id,
                        "content": content,
                        "created_at": created_at,
                        "account": {
                            "id": author_id,
                            "username": author_name,
                            "display_name": author_name,
                            "url": f"https://example.com/@{author_name}",
                        },
                        "language": "en",
                        "favourites_count": 0,
                        "reblogs_count": 0,
                        "replies_count": 0,
                        "ranking_score": score,
                        "recommendation_reason": reason,
                        "is_real_mastodon_post": False,
                        "is_synthetic": True,
                    }

                    # Add to recommendations
                    recommendations.append(post_data)

                # Return the recommendations
                return jsonify(
                    {
                        "user_id": user_id,
                        "recommendations": recommendations,
                        "debug_info": {
                            "database_type": "SQLite in-memory",
                            "recommendations_count": len(recommendations),
                        },
                    }
                )
    else:
        # PostgreSQL version
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                placeholder = "%s"  # PostgreSQL uses %s for placeholders

                cur.execute(
                    f"SELECT COUNT(*) FROM post_metadata WHERE mastodon_post IS NOT NULL"
                )
                real_post_count = cur.fetchone()[0]

                # Next get the ranked post IDs and scores
                cur.execute(
                    f"""
                    SELECT pr.post_id, pr.ranking_score, pr.recommendation_reason, pm.mastodon_post
                    FROM post_rankings pr
                    JOIN post_metadata pm ON pr.post_id = pm.post_id
                    WHERE pr.user_id = {placeholder}
                    ORDER BY pr.ranking_score DESC
                    LIMIT {placeholder}
                """,
                    (user_alias, limit),
                )

                ranking_data = cur.fetchall()

                if not ranking_data:
                    logger.warning(f"No rankings found for user {user_alias}")
                    return jsonify(
                        {
                            "user_id": user_id,
                            "recommendations": [],
                            "message": "No recommendations found. Try generating rankings first.",
                            "debug_info": {
                                "real_posts_in_db": real_post_count,
                                "rankings_found": 0,
                            },
                        }
                    )

                # Process the recommendations
                recommendations = []
                posts_processed = 0
                for post_id, score, reason, mastodon_post in ranking_data:
                    posts_processed += 1

                    if mastodon_post:
                        try:
                            # Parse the JSON if needed
                            if isinstance(mastodon_post, str):
                                post_data = json.loads(mastodon_post)
                            else:
                                post_data = mastodon_post

                            # Add recommendation metadata to the Mastodon post
                            post_data["id"] = post_id
                            post_data["ranking_score"] = score
                            post_data["recommendation_reason"] = reason

                            recommendations.append(post_data)
                        except Exception as e:
                            logger.error(
                                f"Error processing mastodon_post for {post_id}: {e}"
                            )

                # If we couldn't process any posts, return a helpful message
                if not recommendations:
                    logger.warning(
                        f"No recommendations could be processed for user {user_id} despite having {len(ranking_data)} rankings"
                    )

                    # Generate rankings if we have no recommendations but have real posts
                    if real_post_count > 0 and len(ranking_data) == 0:
                        logger.info(
                            f"Attempting to generate rankings for user {user_id} since we have {real_post_count} real posts"
                        )
                        try:
                            # Try to generate rankings
                            ranked_posts = generate_rankings_for_user(user_id)
                            if ranked_posts:
                                logger.info(
                                    f"Successfully generated {len(ranked_posts)} rankings on-demand"
                                )
                                # Recursive call to get the recommendations using the newly generated rankings
                                # We use a different response to avoid infinite recursion
                                return jsonify(
                                    {
                                        "user_id": user_id,
                                        "recommendations": [],
                                        "message": "Generated new rankings. Please retry your request.",
                                        "debug_info": {
                                            "real_posts_in_db": real_post_count,
                                            "newly_generated_rankings": len(
                                                ranked_posts
                                            ),
                                            "retry_recommended": True,
                                        },
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Failed to generate rankings on-demand: {e}")

                    return jsonify(
                        {
                            "user_id": user_id,
                            "recommendations": [],
                            "message": "Could not process any recommendations. Please generate rankings first and try again.",
                            "debug_info": {
                                "real_posts_in_db": real_post_count,
                                "rankings_found": len(ranking_data),
                                "posts_processed": posts_processed,
                            },
                        }
                    )

        return jsonify(
            {
                "user_id": user_id,
                "recommendations": recommendations,
                "debug_info": {
                    "real_posts_in_db": real_post_count,
                    "rankings_found": len(ranking_data),
                    "recommendations_returned": len(recommendations),
                },
            }
        )


@recommendations_bp.route("/status/<task_id>", methods=["GET"])
@log_route
def get_task_status(task_id):
    """
    Get the status of an async recommendation task.
    
    Args:
        task_id: The ID of the async task to check
        
    Returns:
        200 OK with task status if task exists
        404 Not Found if task doesn't exist
        500 Server Error on failure
    """
    logger.info(f"Checking status for task: {task_id}")
    
    # For load testing purposes, simulate task status responses
    # In a real implementation, this would check Celery task status
    
    try:
        # Simulate different task states based on task_id
        task_id_num = int(task_id.split('_')[-1]) if '_' in task_id else hash(task_id)
        
        # Most tasks should be "completed" to simulate normal operation
        if task_id_num % 10 < 8:  # 80% success rate
            return jsonify({
                "task_id": task_id,
                "status": "completed",
                "result": {
                    "recommendations_count": 15,
                    "processing_time": "0.5s"
                },
                "created_at": datetime.now().isoformat()
            }), 200
        elif task_id_num % 10 == 8:  # 10% pending
            return jsonify({
                "task_id": task_id,
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }), 200
        else:  # 10% not found
            return jsonify({
                "error": "Task not found",
                "task_id": task_id
            }), 404
            
    except Exception as e:
        logger.error(f"Error checking task status for {task_id}: {e}")
        return jsonify({
            "error": "Internal error checking task status",
            "task_id": task_id
        }), 500


@recommendations_bp.route("/metrics/<user_id>", methods=["GET"])
@log_route
def get_recommendation_metrics(user_id):
    """
    Get recommendation quality metrics for a specific user.
    
    Args:
        user_id: The ID of the user to get metrics for
        
    Returns:
        200 OK with metrics data
        404 Not Found if user has no metrics
        500 Server Error on failure
    """
    try:
        # Get pseudonymized user ID for privacy
        user_alias = generate_user_alias(user_id)
        logger.info(f"Getting recommendation metrics for user: {user_alias}")
        
        # Simulate realistic metrics for load testing
        # In a real implementation, this would query actual metrics from database
        import random
        
        # Simulate some variation in metrics based on user_id
        user_seed = hash(user_id) % 1000
        random.seed(user_seed)
        
        metrics = {
            "user_id": user_alias,
            "total_recommendations_served": random.randint(50, 500),
            "total_interactions": random.randint(10, 100),
            "click_through_rate": round(random.uniform(0.05, 0.25), 3),
            "engagement_rate": round(random.uniform(0.02, 0.15), 3),
            "diversity_score": round(random.uniform(0.6, 0.9), 3),
            "relevance_score": round(random.uniform(0.7, 0.95), 3),
            "cold_start_exits": random.randint(0, 5),
            "personalization_enabled": True,
            "last_recommendation": "2025-06-08T18:00:00Z",
            "metrics_period": "last_30_days"
        }
        
        return jsonify(metrics), 200
        
    except Exception as e:
        logger.error(f"Error getting recommendation metrics for user {user_id}: {e}")
        return jsonify({"error": "Failed to retrieve recommendation metrics"}), 500


@recommendations_bp.route("/real-posts", methods=["GET"])
@log_route
def get_real_posts():
    """
    Get only real Mastodon posts.

    Query parameters:
        limit: Maximum number of posts to return (default: 20)

    Returns:
        200 OK with real posts
        500 Server Error on failure
    """
    limit = request.args.get("limit", default=20, type=int)

    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            if USE_IN_MEMORY_DB:
                # In-memory SQLite version - return test posts
                placeholder = "?"

                # Get all posts from our test DB
                cur.execute(
                    f"""
                    SELECT post_id, content, author_id, created_at, metadata
                    FROM posts
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )

                rows = cur.fetchall()

                real_posts = []
                for row in rows:
                    post_id, content, author_id, created_at, metadata_str = row

                    # Parse metadata if available
                    try:
                        metadata = json.loads(metadata_str) if metadata_str else {}
                    except:
                        metadata = {}

                    author_name = metadata.get("author_name", "User")

                    # Create a Mastodon-compatible post
                    post_data = {
                        "id": post_id,
                        "content": content,
                        "created_at": created_at,
                        "account": {
                            "id": author_id,
                            "username": author_name,
                            "display_name": author_name,
                            "url": f"https://example.com/@{author_name}",
                        },
                        "language": "en",
                        "favourites_count": 0,
                        "reblogs_count": 0,
                        "replies_count": 0,
                        "is_real_mastodon_post": False,
                        "is_synthetic": True,
                    }

                    real_posts.append(post_data)
            else:
                # PostgreSQL version - get actual Mastodon posts
                placeholder = "%s"

                # Get only real Mastodon posts
                cur.execute(
                    f"""
                    SELECT post_id, mastodon_post
                    FROM post_metadata
                    WHERE mastodon_post IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT {placeholder}
                """,
                    (limit,),
                )

                real_posts = []
                for post_id, mastodon_json in cur.fetchall():
                    try:
                        if isinstance(mastodon_json, str):
                            mastodon_post = json.loads(mastodon_json)
                        else:
                            mastodon_post = mastodon_json

                        # Add explicit real flags for frontend
                        mastodon_post["is_real_mastodon_post"] = True
                        mastodon_post["is_synthetic"] = False

                        # Ensure required fields
                        if "id" not in mastodon_post:
                            mastodon_post["id"] = post_id

                        real_posts.append(mastodon_post)
                    except Exception as e:
                        logger.error(f"Error processing post {post_id}: {e}")

    if not real_posts:
        return jsonify({"message": "No real Mastodon posts found", "posts": []})

    return jsonify(
        {
            "posts": real_posts,
            "count": len(real_posts),
            "message": f"{'Simulated' if USE_IN_MEMORY_DB else 'Real'} posts returned successfully",
        }
    )


@recommendations_bp.route("/timeline", methods=["GET"])
@log_route
def get_recommendations_timeline():
    """
    Get a clean timeline of personalized recommendations for the authenticated user.
    
    This endpoint returns only recommendations without blending with other timelines,
    designed for a dedicated "Corgi Recommendations" tab in the ELK frontend.
    
    Query parameters:
        max_id (str, optional): Return results older than this ID (for pagination)
        since_id (str, optional): Return results newer than this ID (for pagination) 
        limit (int, optional): Maximum number of recommendations to return (default: 20, max: 40)
        
    Returns:
        200 OK with array of Mastodon Status objects
        401 Unauthorized if user is not authenticated
        404 Not Found if no recommendations exist
        500 Server Error on failure
    """
    request_id = hash(f"{datetime.now().timestamp()}_{request.remote_addr}") % 10000000
    
    # Get authenticated user
    user_id = get_authenticated_user(request)
    if not user_id:
        # For development/testing, allow fallback to query parameter
        user_id = request.args.get("user_id")
        if not user_id:
            logger.warning(f"REQ-{request_id} | Unauthorized access to recommendations timeline")
            return jsonify({"error": "Authentication required"}), 401
        else:
            logger.warning(f"REQ-{request_id} | Using fallback user_id from query parameter: {user_id} (DEVELOPMENT ONLY)")
    
    # Get query parameters
    max_id = request.args.get('max_id')
    since_id = request.args.get('since_id')
    limit = min(request.args.get('limit', default=20, type=int), 40)  # Cap at 40
    
    logger.info(
        f"REQ-{request_id} | GET /api/v1/recommendations/timeline | "
        f"User: {user_id} | Limit: {limit} | max_id: {max_id} | since_id: {since_id}"
    )
    
    # Get pseudonymized user ID for privacy
    user_alias = generate_user_alias(user_id)
    
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                if USE_IN_MEMORY_DB:
                    # SQLite in-memory version
                    placeholder = "?"
                    
                    # Build query with pagination
                    query = """
                        SELECT r.post_id, r.score, r.reason, p.content, p.author_id, 
                               p.created_at, p.metadata
                        FROM recommendations r
                        JOIN posts p ON r.post_id = p.post_id
                        WHERE r.user_id = ?
                    """
                    
                    params = [user_alias]
                    
                    # Add pagination filters
                    if max_id:
                        query += " AND p.post_id < ?"
                        params.append(max_id)
                    
                    if since_id:
                        query += " AND p.post_id > ?"
                        params.append(since_id)
                    
                    query += " ORDER BY r.score DESC, p.created_at DESC LIMIT ?"
                    params.append(limit)
                    
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    
                    recommendations = []
                    for row in rows:
                        post_id, score, reason, content, author_id, created_at, metadata_str = row
                        
                        # Parse metadata if available
                        try:
                            metadata = json.loads(metadata_str) if metadata_str else {}
                        except:
                            metadata = {}
                        
                        author_name = metadata.get("author_name", f"User_{author_id}")
                        
                        # Create Mastodon-compatible Status object
                        status = {
                            "id": post_id,
                            "created_at": created_at,
                            "content": content,
                            "account": {
                                "id": author_id,
                                "username": author_name,
                                "acct": author_name,
                                "display_name": author_name,
                                "url": f"https://example.com/@{author_name}",
                                "avatar": f"https://example.com/avatars/{author_id}.png",
                                "avatar_static": f"https://example.com/avatars/{author_id}.png",
                                "followers_count": metadata.get("followers_count", 100),
                                "following_count": metadata.get("following_count", 50),
                                "statuses_count": metadata.get("statuses_count", 200),
                                "bot": False,
                                "locked": False,
                            },
                            "language": "en",
                            "favourites_count": metadata.get("favourites_count", 0),
                            "reblogs_count": metadata.get("reblogs_count", 0),
                            "replies_count": metadata.get("replies_count", 0),
                            "url": f"https://example.com/@{author_name}/{post_id}",
                            "uri": f"https://example.com/@{author_name}/{post_id}",
                            "reblogged": False,
                            "favourited": False,
                            "bookmarked": False,
                            "sensitive": False,
                            "spoiler_text": "",
                            "visibility": "public",
                            "media_attachments": [],
                            "mentions": [],
                            "tags": [],
                            "emojis": [],
                            "card": None,
                            "poll": None,
                            # Corgi-specific fields
                            "is_recommendation": True,
                            "recommendation_score": float(score),
                            "recommendation_reason": reason,
                            "is_real_mastodon_post": False,
                            "is_synthetic": True,
                        }
                        
                        recommendations.append(status)
                        
                else:
                    # PostgreSQL version - get actual recommendations
                    placeholder = "%s"
                    
                    query = """
                        SELECT r.post_id, r.score, r.reason, pm.mastodon_post
                        FROM recommendations r
                        LEFT JOIN post_metadata pm ON r.post_id = pm.post_id
                        WHERE r.user_id = %s
                    """
                    
                    params = [user_alias]
                    
                    # Add pagination filters
                    if max_id:
                        query += " AND r.post_id < %s"
                        params.append(max_id)
                    
                    if since_id:
                        query += " AND r.post_id > %s"
                        params.append(since_id)
                    
                    query += " ORDER BY r.score DESC, r.created_at DESC LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    
                    recommendations = []
                    for post_id, score, reason, mastodon_json in rows:
                        try:
                            if mastodon_json:
                                # Use existing Mastodon post data
                                if isinstance(mastodon_json, str):
                                    status = json.loads(mastodon_json)
                                else:
                                    status = mastodon_json
                            else:
                                # Create basic status if no Mastodon data
                                status = {
                                    "id": post_id,
                                    "created_at": datetime.now().isoformat(),
                                    "content": f"Recommended post {post_id}",
                                    "account": {
                                        "id": "unknown",
                                        "username": "unknown_user",
                                        "display_name": "Unknown User",
                                        "url": "https://example.com/@unknown_user",
                                    },
                                    "language": "en",
                                    "favourites_count": 0,
                                    "reblogs_count": 0,
                                    "replies_count": 0,
                                }
                            
                            # Ensure required fields exist
                            if "id" not in status:
                                status["id"] = post_id
                            
                            # Add Corgi-specific fields
                            status["is_recommendation"] = True
                            status["recommendation_score"] = float(score)
                            status["recommendation_reason"] = reason
                            status["is_real_mastodon_post"] = bool(mastodon_json)
                            status["is_synthetic"] = not bool(mastodon_json)
                            
                            recommendations.append(status)
                            
                        except Exception as e:
                            logger.error(f"Error processing recommendation {post_id}: {e}")
                            continue
                
                logger.info(
                    f"TIMELINE-{request_id} | Retrieved {len(recommendations)} recommendations for user {user_alias}"
                )
                
                if not recommendations:
                    logger.info(f"TIMELINE-{request_id} | No recommendations found for user {user_alias}")
                    return jsonify([]), 200
                
                return jsonify(recommendations), 200
                
    except Exception as e:
        logger.error(f"ERROR-{request_id} | Failed to get recommendations timeline: {e}")
        return jsonify({"error": "Failed to retrieve recommendations"}), 500
