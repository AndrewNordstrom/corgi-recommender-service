"""
Feedback Routes for the Corgi Recommender Service.

This module handles user feedback on recommendations, allowing users to
indicate whether they want more or less content similar to specific posts.
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from utils.logging_decorator import log_route
from routes.proxy import get_authenticated_user
from utils.privacy import generate_user_alias
from db.connection import get_db_connection, get_cursor

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/v1/feedback')


@feedback_bp.route('', methods=['POST'])
@log_route
def submit_feedback():
    """
    Submit user feedback on a recommendation.
    
    This endpoint allows users to provide feedback on recommended posts,
    which will be used to improve future recommendations through machine learning.
    
    Request Body:
        {
            "post_id": "12345",
            "feedback": "more"  # "more" or "less"
        }
        
    Returns:
        202 Accepted: Feedback successfully received
        400 Bad Request: Invalid request format or missing fields
        401 Unauthorized: User not authenticated
        500 Server Error: Internal error processing feedback
    """
    request_id = hash(f"{datetime.now().timestamp()}_{request.remote_addr}") % 10000000
    
    # Get authenticated user
    user_id = get_authenticated_user(request)
    if not user_id:
        # For development/testing, allow fallback to query parameter
        user_id = request.args.get("user_id")
        if not user_id:
            logger.warning(f"REQ-{request_id} | Unauthorized feedback submission attempt")
            return jsonify({"error": "Authentication required"}), 401
        else:
            logger.warning(f"REQ-{request_id} | Using fallback user_id for feedback: {user_id} (DEVELOPMENT ONLY)")
    
    # Validate request body
    if not request.is_json:
        logger.warning(f"REQ-{request_id} | Invalid content type for feedback submission")
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    data = request.get_json()
    
    # Validate required fields
    post_id = data.get('post_id')
    feedback = data.get('feedback')
    
    if not post_id:
        logger.warning(f"REQ-{request_id} | Missing post_id in feedback request")
        return jsonify({"error": "post_id is required"}), 400
    
    if not feedback:
        logger.warning(f"REQ-{request_id} | Missing feedback in request")
        return jsonify({"error": "feedback is required"}), 400
    
    # Validate feedback value
    if feedback not in ['more', 'less']:
        logger.warning(f"REQ-{request_id} | Invalid feedback value: {feedback}")
        return jsonify({"error": "feedback must be 'more' or 'less'"}), 400
    
    # Get pseudonymized user ID for privacy
    user_alias = generate_user_alias(user_id)
    
    logger.info(
        f"REQ-{request_id} | POST /api/v1/feedback | "
        f"User: {user_id} | Post: {post_id} | Feedback: {feedback}"
    )
    
    try:
        # Store feedback in database
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Insert feedback record
                import json
                cur.execute(
                    """
                    INSERT INTO interactions (
                        user_alias, post_id, action_type, context, created_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        user_alias,
                        post_id,
                        f"{feedback}_like_this",  # "more_like_this" or "less_like_this"
                        json.dumps({"source": "recommendation_feedback", "request_id": request_id}),
                        datetime.now()
                    )
                )
                
                conn.commit()
                
                logger.info(
                    f"FEEDBACK-{request_id} | Successfully recorded {feedback} feedback "
                    f"for post {post_id} from user {user_alias}"
                )
                
                # Optional: Log for ML training purposes
                logger.info(
                    f"ML_TRAINING_DATA | user_alias={user_alias} | post_id={post_id} | "
                    f"feedback={feedback} | timestamp={datetime.now().isoformat()}"
                )
                
                return jsonify({
                    "message": "Feedback received successfully",
                    "post_id": post_id,
                    "feedback": feedback
                }), 202
                
    except Exception as e:
        # Handle foreign key constraint errors gracefully
        if "fk_post_id" in str(e) or "foreign key constraint" in str(e):
            logger.warning(
                f"FEEDBACK-{request_id} | Post {post_id} not found in post_metadata table, "
                f"but logging feedback anyway for ML training"
            )
            
            # Log for ML training even if we can't store in interactions table
            logger.info(
                f"ML_TRAINING_DATA | user_alias={user_alias} | post_id={post_id} | "
                f"feedback={feedback} | timestamp={datetime.now().isoformat()} | "
                f"source=crawled_posts"
            )
            
            return jsonify({
                "message": "Feedback received successfully",
                "post_id": post_id,
                "feedback": feedback,
                "note": "Feedback logged for training purposes"
            }), 202
        else:
            logger.error(f"ERROR-{request_id} | Failed to store feedback: {e}")
            return jsonify({"error": "Failed to process feedback"}), 500


@feedback_bp.route('/stats/<user_id>', methods=['GET'])
@log_route  
def get_feedback_stats(user_id):
    """
    Get feedback statistics for a user (for debugging/analytics).
    
    Args:
        user_id: User ID to get stats for
        
    Returns:
        200 OK: Statistics object
        401 Unauthorized: User not authenticated or not authorized
        500 Server Error: Internal error
    """
    request_id = hash(f"{datetime.now().timestamp()}_{request.remote_addr}") % 10000000
    
    # Get authenticated user  
    auth_user_id = get_authenticated_user(request)
    if not auth_user_id:
        # For development/testing, allow fallback
        auth_user_id = request.args.get("auth_user_id")
        if not auth_user_id:
            logger.warning(f"REQ-{request_id} | Unauthorized access to feedback stats")
            return jsonify({"error": "Authentication required"}), 401
    
    # For now, only allow users to see their own stats or admin access
    if auth_user_id != user_id and not request.args.get("admin"):
        logger.warning(f"REQ-{request_id} | User {auth_user_id} attempted to access stats for {user_id}")
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get pseudonymized user ID
    user_alias = generate_user_alias(user_id)
    
    logger.info(f"REQ-{request_id} | GET /api/v1/feedback/stats/{user_id}")
    
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Get feedback counts
                cur.execute(
                    """
                    SELECT action_type, COUNT(*) as count
                    FROM interactions
                    WHERE user_alias = %s 
                    AND action_type IN ('more_like_this', 'less_like_this')
                    AND created_at > NOW() - INTERVAL '30 days'
                    GROUP BY action_type
                    """,
                    (user_alias,)
                )
                
                results = cur.fetchall()
                
                stats = {
                    "user_id": user_id,
                    "more_like_this": 0,
                    "less_like_this": 0,
                    "total_feedback": 0,
                    "period": "last_30_days"
                }
                
                for action_type, count in results:
                    if action_type == "more_like_this":
                        stats["more_like_this"] = count
                    elif action_type == "less_like_this":
                        stats["less_like_this"] = count
                
                stats["total_feedback"] = stats["more_like_this"] + stats["less_like_this"]
                
                logger.info(
                    f"STATS-{request_id} | User {user_alias} feedback stats: "
                    f"more={stats['more_like_this']}, less={stats['less_like_this']}"
                )
                
                return jsonify(stats), 200
                
    except Exception as e:
        logger.error(f"ERROR-{request_id} | Failed to get feedback stats: {e}")
        return jsonify({"error": "Failed to retrieve feedback statistics"}), 500 