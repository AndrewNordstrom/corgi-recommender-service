"""
Interaction routes for the Corgi Recommender Service.

This module provides endpoints for logging and querying user interactions
with posts, such as favorites, bookmarks, etc.
"""

import logging
import json
from flask import Blueprint, request, jsonify

from db.connection import get_db_connection, get_cursor, USE_IN_MEMORY_DB
from utils.privacy import generate_user_alias, get_user_privacy_level
from utils.logging_decorator import log_route
from utils.metrics import track_recommendation_interaction

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
    
    Also supports using user_id instead of user_alias:
    {
        "user_id": "user123",
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
    
    # Support both user_alias and user_id
    user_alias = data.get('user_alias')
    user_id = data.get('user_id')
    
    # If user_id is provided but not user_alias, generate an alias
    if not user_alias and user_id:
        user_alias = generate_user_alias(user_id)
        
    post_id = data.get('post_id')
    action_type = data.get('action_type')
    context = data.get('context', {})
    
    # Validate required fields
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
        with get_cursor(conn) as cur:
            # Use correct placeholder based on database type
            placeholder = "?" if USE_IN_MEMORY_DB else "%s"
            
            if USE_IN_MEMORY_DB:
                # SQLite version - simplified for in-memory database
                
                # Check if this is a new interaction or an update
                cur.execute(f'''
                    SELECT id FROM interactions
                    WHERE user_id = ? AND post_id = ? AND interaction_type = ?
                ''', (user_alias, post_id, action_type))
                
                existing_interaction = cur.fetchone()
                is_new = existing_interaction is None
                
                # Remove conflicting binary actions
                conflicting_action = "more_like_this" if action_type == "less_like_this" else "less_like_this"
                cur.execute(f'''
                    DELETE FROM interactions 
                    WHERE user_id = ? AND post_id = ? AND interaction_type = ?
                ''', (user_alias, post_id, conflicting_action))
                
                if is_new:
                    # Insert new interaction
                    cur.execute(f'''
                        INSERT INTO interactions 
                        (user_id, post_id, interaction_type)
                        VALUES (?, ?, ?)
                    ''', (user_alias, post_id, action_type))
                else:
                    # Update existing interaction timestamp
                    cur.execute(f'''
                        UPDATE interactions
                        SET created_at = datetime('now')
                        WHERE user_id = ? AND post_id = ? AND interaction_type = ?
                    ''', (user_alias, post_id, action_type))
                
                conn.commit()
                
                # Track metrics for interactions with recommendations
                is_injected = context.get('injected', False)
                track_recommendation_interaction(action_type, is_injected)
                
                return jsonify({
                    "status": "ok",
                    "message": "Interaction logged successfully"
                }), 200
            else:
                # PostgreSQL version with full features
                # First, check if the post exists in post_metadata, and if not, add it
                cur.execute(f'''
                    SELECT post_id FROM post_metadata
                    WHERE post_id = {placeholder}
                ''', (post_id,))
                
                post_exists = cur.fetchone() is not None
                
                if not post_exists:
                    # Post doesn't exist in metadata, so we need to add a stub entry
                    # to satisfy the foreign key constraint
                    logger.info(f"Post {post_id} not found in post_metadata, adding stub entry")
                    try:
                        # Parse any available metadata from context
                        author_id = context.get('author_id', 'unknown')
                        author_name = context.get('author_name', 'Unknown Author')
                        created_at = context.get('created_at', None)
                        
                        # Insert a minimal entry to satisfy the foreign key constraint
                        cur.execute(f'''
                            INSERT INTO post_metadata 
                            (post_id, author_id, author_name, created_at, mastodon_post)
                            VALUES ({placeholder}, {placeholder}, {placeholder}, 
                                    COALESCE({placeholder}, CURRENT_TIMESTAMP), {placeholder})
                            ON CONFLICT (post_id) DO NOTHING
                        ''', (post_id, author_id, author_name, created_at, json.dumps({
                            "id": post_id,
                            "content": context.get('content', 'Stub post content'),
                            "is_stub": True
                        })))
                        
                        post_exists = True
                        logger.info(f"Successfully added stub entry for post {post_id}")
                    except Exception as e:
                        logger.error(f"Error adding stub entry for post {post_id}: {e}")
                        return jsonify({
                            "error": f"Failed to create stub entry for post: {e}"
                        }), 500
                
                if post_exists:
                    # Remove conflicting binary actions if necessary
                    conflicting_action = "more_like_this" if action_type == "less_like_this" else "less_like_this"
                    cur.execute(f'''
                        DELETE FROM interactions 
                        WHERE user_alias = {placeholder} AND post_id = {placeholder} AND action_type = {placeholder}
                    ''', (user_alias, post_id, conflicting_action))
                    
                    # Check if this is a new interaction or an update
                    cur.execute(f'''
                        SELECT id FROM interactions
                        WHERE user_alias = {placeholder} AND post_id = {placeholder} AND action_type = {placeholder}
                    ''', (user_alias, post_id, action_type))
                    
                    existing_interaction = cur.fetchone()
                    is_new = existing_interaction is None
                    
                    # Insert or update the interaction
                    cur.execute(f'''
                        INSERT INTO interactions 
                        (user_alias, post_id, action_type, context)
                        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                        ON CONFLICT (user_alias, post_id, action_type) 
                        DO UPDATE SET 
                            context = EXCLUDED.context,
                            created_at = CURRENT_TIMESTAMP
                        RETURNING id
                    ''', (user_alias, post_id, action_type, json.dumps(context)))
                    
                    result = cur.fetchone()
                else:
                    # If we couldn't create the post entry for some reason, return an error
                    return jsonify({
                        "error": f"Cannot log interaction: post {post_id} does not exist and could not be created"
                    }), 400
                
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
                            cur.execute(f'''
                                UPDATE post_metadata
                                SET interaction_counts = jsonb_set(
                                    COALESCE(interaction_counts, '{{}}'::jsonb),
                                    {placeholder},
                                    (COALESCE((interaction_counts->{placeholder})::int, 0) + 1)::text::jsonb
                                )
                                WHERE post_id = {placeholder}
                            ''', ([field_name], field_name, post_id))
                    except Exception as e:
                        logger.error(f"Error updating post interaction counts: {e}")
                
                conn.commit()
                
                # Track metrics for interactions with recommendations
                is_injected = context.get('injected', False)
                track_recommendation_interaction(action_type, is_injected)
                
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
        with get_cursor(conn) as cur:
            # Use appropriate placeholder and column names based on database type
            placeholder = "?" if USE_IN_MEMORY_DB else "%s"
            action_column = "interaction_type" if USE_IN_MEMORY_DB else "action_type"
            
            query = f'''
                SELECT {action_column}, COUNT(*) as count
                FROM interactions
                WHERE post_id = {placeholder}
                GROUP BY {action_column}
            '''
            cur.execute(query, (post_id,))
            
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
        with get_cursor(conn) as cur:
            # Use appropriate placeholder and column names based on database type
            placeholder = "?" if USE_IN_MEMORY_DB else "%s"
            action_column = "interaction_type" if USE_IN_MEMORY_DB else "action_type"
            
            if USE_IN_MEMORY_DB:
                # SQLite doesn't have a direct equivalent for tuple IN operator,
                # so we'll query each post individually and combine results
                interactions = []
                
                for post_id in post_ids:
                    query = f'''
                        SELECT post_id, {action_column}, COUNT(*) as count
                        FROM interactions
                        WHERE post_id = {placeholder}
                        GROUP BY post_id, {action_column}
                    '''
                    cur.execute(query, (post_id,))
                    interactions.extend(cur.fetchall())
            else:
                # PostgreSQL version
                if len(post_ids) == 1:
                    # Special case for a single post
                    cur.execute(f'''
                        SELECT post_id, action_type, COUNT(*) as count
                        FROM interactions
                        WHERE post_id = {placeholder}
                        GROUP BY post_id, action_type
                    ''', (post_ids[0],))
                else:
                    # Multiple posts case
                    post_ids_tuple = tuple(post_ids)
                    cur.execute(f'''
                        SELECT post_id, action_type, COUNT(*) as count
                        FROM interactions
                        WHERE post_id IN {placeholder}
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
        
        with get_cursor(conn) as cur:
            # Use appropriate placeholder and column names based on database type
            placeholder = "?" if USE_IN_MEMORY_DB else "%s"
            action_column = "interaction_type" if USE_IN_MEMORY_DB else "action_type"
            user_column = "user_id" if USE_IN_MEMORY_DB else "user_alias"
            
            if limited_privacy:
                # Limited privacy - only return action types and counts
                query = f'''
                    SELECT {action_column}, COUNT(*) as count
                    FROM interactions
                    WHERE {user_column} = {placeholder}
                    GROUP BY {action_column}
                '''
                cur.execute(query, (user_alias,))
                
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
                if USE_IN_MEMORY_DB:
                    # SQLite version
                    query = f'''
                        SELECT post_id, {action_column}, created_at
                        FROM interactions
                        WHERE {user_column} = {placeholder}
                        ORDER BY created_at DESC
                    '''
                    cur.execute(query, (user_alias,))
                    
                    # SQLite doesn't store context in separate field
                    # Also, the created_at is already a string in SQLite, not a datetime object
                    rows = cur.fetchall()
                    interactions = []
                    for row in rows:
                        post_id = row[0]
                        action_type = row[1]
                        created_at = row[2]  # Already a string, so don't call isoformat()
                        context = {}  # Empty context for SQLite
                        interactions.append((post_id, action_type, context, created_at))
                else:
                    # PostgreSQL version
                    query = f'''
                        SELECT post_id, action_type, context, created_at
                        FROM interactions
                        WHERE user_alias = {placeholder}
                        ORDER BY created_at DESC
                    '''
                    cur.execute(query, (user_alias,))
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
                "created_at": row[3].isoformat() if hasattr(row[3], 'isoformat') else row[3]
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
        with get_cursor(conn) as cur:
            # Use appropriate placeholder and column names based on database type
            placeholder = "?" if USE_IN_MEMORY_DB else "%s"
            action_column = "interaction_type" if USE_IN_MEMORY_DB else "action_type"
            user_column = "user_id" if USE_IN_MEMORY_DB else "user_alias"
            
            query = f'''
                SELECT post_id, created_at
                FROM interactions
                WHERE {user_column} = {placeholder} AND {action_column} = {placeholder}
                ORDER BY created_at DESC
            '''
            cur.execute(query, (user_alias, 'favorite'))
            
            favourites = cur.fetchall()
    
    if not favourites:
        return jsonify({"message": "No favourites found for this user"}), 404
    
    return jsonify({
        "user_id": user_id,
        "favourites": [
            {
                "post_id": row[0],
                "created_at": row[1].isoformat() if hasattr(row[1], 'isoformat') else row[1]
            }
            for row in favourites
        ]
    })