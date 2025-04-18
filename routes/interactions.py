"""
Interaction routes for the Corgi Recommender Service.

This module provides endpoints for logging and querying user interactions
with posts, such as favorites, bookmarks, etc.
"""

import logging
import json
from flask import Blueprint, request, jsonify

from db.connection import get_db_connection
from utils.privacy import generate_user_alias, get_user_privacy_level
from utils.logging_decorator import log_route

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
interactions_bp = Blueprint('interactions', __name__)

@interactions_bp.route('', methods=['POST'])
@log_route
def log_interaction():
    """
    Log a user interaction with a post.
    
    Request body:
    {
        "user_alias": "abc123",
        "post_id": "xyz789",
        "action_type": "favorite",
        "context": {
            "source": "timeline_home"
        }
    }
    
    Returns:
        200 OK on success
        400 Bad Request if required fields are missing
        500 Server Error on failure
    """
    data = request.json
    
    # Validate required fields
    user_alias = data.get('user_alias')
    post_id = data.get('post_id')
    action_type = data.get('action_type')
    context = data.get('context', {})
    
    if not all([user_alias, post_id, action_type]):
        return jsonify({
            "error": "Missing required fields",
            "received": {
                "user_alias": user_alias is not None,
                "post_id": post_id is not None,
                "action_type": action_type is not None
            }
        }), 400
    
    # Normalize action types for consistency
    ACTION_TYPE_MAPPING = {
        "favourited": "favorite",
        "favourite": "favorite",
        "unfavourite": "unfavorite",
        "bookmarked": "bookmark"
    }
    action_type = ACTION_TYPE_MAPPING.get(action_type, action_type)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Remove conflicting binary actions if necessary
            # (e.g., remove "less_like_this" if action is "more_like_this")
            conflicting_action = "more_like_this" if action_type == "less_like_this" else "less_like_this"
            cur.execute('''
                DELETE FROM interactions 
                WHERE user_alias = %s AND post_id = %s AND action_type = %s
            ''', (user_alias, post_id, conflicting_action))
            
            # Check if this is a new interaction or an update
            cur.execute('''
                SELECT id FROM interactions
                WHERE user_alias = %s AND post_id = %s AND action_type = %s
            ''', (user_alias, post_id, action_type))
            
            existing_interaction = cur.fetchone()
            is_new = existing_interaction is None
            
            # Insert or update the interaction
            cur.execute('''
                INSERT INTO interactions 
                (user_alias, post_id, action_type, context)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_alias, post_id, action_type) 
                DO UPDATE SET 
                    context = EXCLUDED.context,
                    created_at = CURRENT_TIMESTAMP
                RETURNING id
            ''', (user_alias, post_id, action_type, json.dumps(context)))
            
            result = cur.fetchone()
            
            # Update post interaction counts if necessary
            if is_new and action_type in ['favorite', 'reblog', 'reply', 'bookmark', 'favourited']:
                try:
                    # Increment the appropriate counter in post_metadata
                    field_name = {
                        'favorite': 'favorites',
                        'favourite': 'favorites',
                        'favourited': 'favorites',
                        'reblog': 'reblogs',
                        'reply': 'replies',
                        'bookmark': 'bookmarks'
                    }.get(action_type)
                    
                    if field_name:
                        cur.execute('''
                            UPDATE post_metadata
                            SET interaction_counts = jsonb_set(
                                COALESCE(interaction_counts, '{}'::jsonb),
                                %s,
                                (COALESCE((interaction_counts->%s)::int, 0) + 1)::text::jsonb
                            )
                            WHERE post_id = %s
                        ''', ([field_name], field_name, post_id))
                except Exception as e:
                    logger.error(f"Error updating post interaction counts: {e}")
            
            conn.commit()
            
            return jsonify({
                "status": "ok"
            }), 200

@interactions_bp.route('/<post_id>', methods=['GET'])
@log_route
def get_interactions_by_post(post_id):
    """
    Get all interactions for a specific post.
    
    URL parameters:
        post_id: ID of the post to get interactions for
    
    Returns:
        200 OK with interaction data
        404 Not Found if no interactions exist
        500 Server Error on failure
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT action_type, COUNT(*) as count
                FROM interactions
                WHERE post_id = %s
                GROUP BY action_type
            ''', (post_id,))
            
            interactions = cur.fetchall()
    
    # Standardizing action types
    ACTION_TYPE_MAPPING = {
        "favourited": "favorite",
        "favourite": "favorite",
        "unfavourite": "unfavorite",
        "bookmarked": "bookmark",
    }
    
    # Convert to a dict for easier access
    interaction_counts = {}
    for row in interactions:
        action_type = ACTION_TYPE_MAPPING.get(row[0], row[0])
        interaction_counts[action_type] = row[1]
        
    # Format the response data
    formatted_counts = {
        "favorites": interaction_counts.get("favorite", 0),
        "reblogs": interaction_counts.get("reblog", 0),
        "replies": interaction_counts.get("reply", 0),
        "bookmarks": interaction_counts.get("bookmark", 0)
    }
    
    # Add additional interaction types that might be present
    for action_type, count in interaction_counts.items():
        if action_type not in ["favorite", "reblog", "reply", "bookmark"]:
            formatted_counts[action_type] = count
    
    return jsonify({
        "post_id": post_id,
        "interaction_counts": formatted_counts,
        "interactions": [
            {
                "action_type": ACTION_TYPE_MAPPING.get(row[0], row[0]),
                "count": row[1]
            }
            for row in interactions
        ]
    })

@interactions_bp.route('/counts/batch', methods=['POST'])
@log_route
def get_interactions_counts_batch():
    """
    Get interaction counts for multiple posts in a single request.
    
    Request body:
    {
        "post_ids": ["post_123", "post_456", ...]
    }
    
    Returns:
        200 OK with interaction counts for all posts
        400 Bad Request if no post_ids provided or too many requested
        500 Server Error on failure
    """
    data = request.json
    post_ids = data.get('post_ids', [])
    
    if not post_ids:
        return jsonify({"error": "No post_ids provided"}), 400
        
    if len(post_ids) > 100:
        return jsonify({"error": "Too many post_ids. Maximum 100 allowed."}), 400
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if len(post_ids) == 1:
                # Special case for a single post
                cur.execute('''
                    SELECT post_id, action_type, COUNT(*) as count
                    FROM interactions
                    WHERE post_id = %s
                    GROUP BY post_id, action_type
                ''', (post_ids[0],))
            else:
                # Multiple posts case
                post_ids_tuple = tuple(post_ids)
                cur.execute('''
                    SELECT post_id, action_type, COUNT(*) as count
                    FROM interactions
                    WHERE post_id IN %s
                    GROUP BY post_id, action_type
                ''', (post_ids_tuple,))
            
            interactions = cur.fetchall()
    
    # Standardizing action types
    ACTION_TYPE_MAPPING = {
        "favourited": "favorite",
        "favourite": "favorite",
        "unfavourite": "unfavorite",
        "bookmarked": "bookmark",
    }
    
    # Group by post_id
    results = {}
    for post_id in post_ids:
        results[post_id] = {
            "favorites": 0,
            "reblogs": 0,
            "replies": 0,
            "bookmarks": 0
        }
        
    # Fill in the actual counts
    for row in interactions:
        post_id, action_type, count = row
        std_action = ACTION_TYPE_MAPPING.get(action_type, action_type)
        
        # Map to Mastodon-compatible property names
        if std_action == "favorite":
            results[post_id]["favorites"] = count
        elif std_action == "reblog":
            results[post_id]["reblogs"] = count
        elif std_action == "reply":
            results[post_id]["replies"] = count
        elif std_action == "bookmark":
            results[post_id]["bookmarks"] = count
        else:
            # Custom interaction types
            results[post_id][std_action] = count
    
    return jsonify({
        "interaction_counts": results
    })

@interactions_bp.route('/user/<user_id>', methods=['GET'])
@log_route
def get_user_interactions_data(user_id):
    """
    Get all interactions for a specific user.
    
    URL parameters:
        user_id: ID of the user to get interactions for
    
    Returns:
        200 OK with interaction data
        404 Not Found if no interactions exist
        500 Server Error on failure
    """
    # Validate user_id
    if not user_id:
        return jsonify({"error": "Missing user_id parameter"}), 400
        
    # Check privacy settings for this user
    from db.connection import get_db_connection
    
    # Pseudonymize user ID for privacy
    user_alias = generate_user_alias(user_id)
    
    with get_db_connection() as conn:
        # Get user's privacy settings
        privacy_level = get_user_privacy_level(conn, user_id)
        
        # If privacy level is 'none', return minimal data
        if privacy_level == 'none':
            logger.info(f"User {user_id} has privacy level 'none', returning minimal interaction data")
            return jsonify({
                "user_id": user_id,
                "privacy_level": "none",
                "interactions": [],
                "message": "This user has opted out of interaction tracking"
            })
        
        # For limited privacy, we'll only return interaction types, not content
        limited_privacy = (privacy_level == 'limited')
        
        with conn.cursor() as cur:
            if limited_privacy:
                # Limited privacy - only return action types and counts
                cur.execute('''
                    SELECT action_type, COUNT(*) as count
                    FROM interactions
                    WHERE user_alias = %s
                    GROUP BY action_type
                ''', (user_alias,))
                
                interaction_counts = cur.fetchall()
                
                if not interaction_counts:
                    return jsonify({"message": "No interactions found for this user"}), 404
                    
                return jsonify({
                    "user_id": user_id,
                    "privacy_level": "limited",
                    "interaction_counts": {
                        action_type: count for action_type, count in interaction_counts
                    }
                })
            else:
                # Full privacy - return all interaction data
                cur.execute('''
                    SELECT post_id, action_type, context, created_at
                    FROM interactions
                    WHERE user_alias = %s
                    ORDER BY created_at DESC
                ''', (user_alias,))
                
                interactions = cur.fetchall()
    
    if not interactions:
        return jsonify({"message": "No interactions found for this user"}), 404
    
    return jsonify({
        "user_id": user_id,
        "interactions": [
            {
                "post_id": row[0],
                "action_type": row[1],
                "context": row[2],
                "created_at": row[3].isoformat() if row[3] else None
            }
            for row in interactions
        ]
    })

@interactions_bp.route('/favourites', methods=['GET'])
@log_route
def get_user_favourites():
    """
    Get all posts favorited by a specific user.
    
    Query parameters:
        user_id: ID of the user to get favorites for
    
    Returns:
        200 OK with favorited posts
        400 Bad Request if user_id is missing
        404 Not Found if no favorites exist
        500 Server Error on failure
    """
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({"error": "Missing user_id parameter"}), 400
    
    # Pseudonymize user ID for privacy
    user_alias = generate_user_alias(user_id)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT post_id, created_at
                FROM interactions
                WHERE user_alias = %s AND action_type = 'favorite'
                ORDER BY created_at DESC
            ''', (user_alias,))
            
            favourites = cur.fetchall()
    
    if not favourites:
        return jsonify({"message": "No favourites found for this user"}), 404
    
    return jsonify({
        "user_id": user_id,
        "favourites": [
            {
                "post_id": row[0],
                "created_at": row[1].isoformat() if row[1] else None
            }
            for row in favourites
        ]
    })