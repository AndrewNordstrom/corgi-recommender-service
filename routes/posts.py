"""
Post routes for the Corgi Recommender Service.

This module provides endpoints for retrieving and storing post metadata.
"""

import logging
import json
from flask import Blueprint, request, jsonify

from db.connection import get_db_connection, get_cursor, USE_IN_MEMORY_DB
from utils.logging_decorator import log_route

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
posts_bp = Blueprint('posts', __name__)

@posts_bp.route('', methods=['GET'])
@log_route
def get_posts():
    """
    Get a list of posts with optional filtering.
    
    Query parameters:
        limit: Maximum number of posts to return (default: 100)
    
    Returns:
        200 OK with post data
        500 Server Error on failure
    """
    limit = request.args.get('limit', default=100, type=int)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT post_id, author_id, author_name, content, content_type, created_at, 
                       interaction_counts, mastodon_post
                FROM post_metadata
                ORDER BY created_at DESC
                LIMIT %s
            ''', (limit,))
            
            posts = cur.fetchall()
            
            # Process posts in Mastodon format when available
            formatted_posts = []
            for row in posts:
                mastodon_post = row[7]
                
                if mastodon_post:
                    # Use Mastodon format if available
                    try:
                        if isinstance(mastodon_post, str):
                            post_data = json.loads(mastodon_post)
                        else:
                            post_data = mastodon_post
                        formatted_posts.append(post_data)
                        continue
                    except Exception as e:
                        logger.error(f"Error parsing mastodon_post JSON: {e}")
                        # Fall back to legacy format on error
                
                # Fall back to legacy format with adjusted field names for Mastodon compatibility
                post_data = {
                    "id": row[0],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "content": row[3],
                    "favourites_count": row[6].get("favorites", 0) if row[6] else 0,
                    "reblogs_count": row[6].get("reblogs", 0) if row[6] else 0,
                    "replies_count": row[6].get("replies", 0) if row[6] else 0
                }
                formatted_posts.append(post_data)
    
    return jsonify(formatted_posts)

@posts_bp.route('', methods=['POST'])
@log_route
def create_post():
    """
    Create or update a post.
    
    Request body:
    {
        "post_id": "post_123",
        "author_id": "author_456",
        "author_name": "Username",
        "content": "Post content",
        "content_type": "text",
        "created_at": "2023-01-01T12:00:00Z",
        "interaction_counts": {
            "favorites": 0,
            "reblogs": 0,
            "replies": 0
        },
        "mastodon_post": {} // Optional: full Mastodon API post object
    }
    
    Returns:
        201 Created on success
        400 Bad Request if required fields are missing
        500 Server Error on failure
    """
    data = request.json
    
    # Extract required fields
    post_id = data.get('post_id')
    
    if not post_id:
        return jsonify({"error": "Missing required post_id field"}), 400
    
    # Check if this is an update to an existing post
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            # Adjust for SQLite vs PostgreSQL
            placeholder = "?" if USE_IN_MEMORY_DB else "%s"
            
            query = f"SELECT 1 FROM posts WHERE post_id = {placeholder}"
            cur.execute(query, (post_id,))
            is_update = cur.fetchone() is not None
            
            # Full post info is required for new posts
            if not is_update and not data.get('author_id'):
                return jsonify({"error": "Missing required author_id field for new post"}), 400
            
            # Extract remaining fields
            author_id = data.get('author_id')
            author_name = data.get('author_name')
            content = data.get('content')
            content_type = data.get('content_type', 'text')
            created_at = data.get('created_at')
            interaction_counts = data.get('interaction_counts', {})
            mastodon_post = data.get('mastodon_post')
            
            # Adapt for SQLite vs PostgreSQL
            if USE_IN_MEMORY_DB:
                # SQLite simpler version
                if is_update:
                    cur.execute('''
                        UPDATE posts
                        SET content = ?, metadata = ?
                        WHERE post_id = ?
                    ''', (
                        content,
                        json.dumps({
                            "interaction_counts": interaction_counts,
                            "content_type": content_type
                        }),
                        post_id
                    ))
                else:
                    cur.execute('''
                        INSERT INTO posts 
                        (post_id, author_id, content, created_at, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        post_id, 
                        author_id, 
                        content, 
                        created_at, 
                        json.dumps({
                            "author_name": author_name,
                            "content_type": content_type,
                            "interaction_counts": interaction_counts,
                            "mastodon_post": mastodon_post
                        })
                    ))
                
                conn.commit()
                return jsonify({
                    "message": "Post saved successfully",
                    "post_id": post_id
                }), 201
            else:
                # PostgreSQL original version with upsert
                if is_update and interaction_counts and not (author_id or author_name or content):
                    # Only updating interaction counts
                    cur.execute('''
                        UPDATE post_metadata
                        SET interaction_counts = %s
                        WHERE post_id = %s
                        RETURNING post_id
                    ''', (json.dumps(interaction_counts), post_id))
                else:
                    # Full insert or update
                    cur.execute('''
                        INSERT INTO post_metadata 
                        (post_id, author_id, author_name, content, content_type, created_at, 
                         interaction_counts, mastodon_post)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (post_id) 
                        DO UPDATE SET 
                            content = COALESCE(EXCLUDED.content, post_metadata.content),
                            author_name = COALESCE(EXCLUDED.author_name, post_metadata.author_name),
                            content_type = COALESCE(EXCLUDED.content_type, post_metadata.content_type),
                            interaction_counts = EXCLUDED.interaction_counts,
                            mastodon_post = COALESCE(EXCLUDED.mastodon_post, post_metadata.mastodon_post)
                        RETURNING post_id
                    ''', (
                        post_id, 
                        author_id, 
                        author_name, 
                        content, 
                        content_type, 
                        created_at, 
                        json.dumps(interaction_counts),
                        json.dumps(mastodon_post) if mastodon_post else None
                    ))
                
                result = cur.fetchone()
                conn.commit()
                
                return jsonify({
                    "message": "Post saved successfully",
                    "post_id": result[0]
                }), 201

@posts_bp.route('/<post_id>', methods=['GET'])
@log_route
def get_post(post_id):
    """
    Get a specific post by ID.
    
    URL parameters:
        post_id: ID of the post to retrieve
    
    Returns:
        200 OK with post data
        404 Not Found if post doesn't exist
        500 Server Error on failure
    """
    with get_db_connection() as conn:
        with get_cursor(conn) as cur:
            if USE_IN_MEMORY_DB:
                # SQLite version
                cur.execute('''
                    SELECT post_id, author_id, content, created_at, metadata
                    FROM posts
                    WHERE post_id = ?
                ''', (post_id,))
                
                post_data = cur.fetchone()
                
                if not post_data:
                    return jsonify({"message": "Post not found"}), 404
                
                # Parse metadata from SQLite
                metadata = json.loads(post_data[4]) if post_data[4] else {}
                author_name = metadata.get("author_name", "")
                content_type = metadata.get("content_type", "text")
                interaction_counts = metadata.get("interaction_counts", {})
                mastodon_post = metadata.get("mastodon_post")
                
                if mastodon_post:
                    # If we have a mastodon_post field, return that directly
                    return jsonify(mastodon_post)
                
                # Fall back to legacy post format
                return jsonify({
                    "id": post_data[0],  # Use "id" instead of "post_id" for Mastodon compatibility
                    "author_id": post_data[1],
                    "author_name": author_name,
                    "content": post_data[2],
                    "content_type": content_type,
                    "created_at": post_data[3],
                    "favourites_count": interaction_counts.get("favorites", 0),
                    "reblogs_count": interaction_counts.get("reblogs", 0),
                    "replies_count": interaction_counts.get("replies", 0)
                })
            else:
                # PostgreSQL version
                cur.execute('''
                    SELECT post_id, author_id, author_name, content, content_type, created_at, 
                           interaction_counts, mastodon_post
                    FROM post_metadata
                    WHERE post_id = %s
                ''', (post_id,))
                
                post_data = cur.fetchone()
                
                if not post_data:
                    return jsonify({"message": "Post not found"}), 404
                
                # Check if we have a Mastodon-compatible post version
                mastodon_post = post_data[7]
                
                if mastodon_post:
                    # If we have a mastodon_post field, return that directly
                    try:
                        if isinstance(mastodon_post, str):
                            mastodon_post = json.loads(mastodon_post)
                        return jsonify(mastodon_post)
                    except Exception as e:
                        logger.error(f"Error parsing mastodon_post JSON: {e}")
                        # Fall back to legacy format if JSON parsing fails
                
                # Fall back to legacy post format
                return jsonify({
                    "id": post_data[0],  # Use "id" instead of "post_id" for Mastodon compatibility
                    "author_id": post_data[1],
                    "author_name": post_data[2],
                    "content": post_data[3],
                    "content_type": post_data[4],
                    "created_at": post_data[5].isoformat() if post_data[5] else None,
                    "favourites_count": post_data[6].get("favorites", 0) if post_data[6] else 0,
                    "reblogs_count": post_data[6].get("reblogs", 0) if post_data[6] else 0,
                    "replies_count": post_data[6].get("replies", 0) if post_data[6] else 0
                })

@posts_bp.route('/author/<author_id>', methods=['GET'])
@log_route
def get_posts_by_author(author_id):
    """
    Get all posts by a specific author.
    
    URL parameters:
        author_id: ID of the author to get posts for
    
    Returns:
        200 OK with post data
        404 Not Found if no posts exist for the author
        500 Server Error on failure
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT post_id, author_id, author_name, content, content_type, created_at, 
                       interaction_counts, mastodon_post
                FROM post_metadata
                WHERE author_id = %s
                ORDER BY created_at DESC
            ''', (author_id,))
            
            posts = cur.fetchall()
    
    if not posts:
        return jsonify({"message": "No posts found for this author"}), 404
    
    # Process posts in Mastodon format when available
    formatted_posts = []
    for row in posts:
        mastodon_post = row[7]
        
        if mastodon_post:
            # Use Mastodon format if available
            try:
                if isinstance(mastodon_post, str):
                    post_data = json.loads(mastodon_post)
                else:
                    post_data = mastodon_post
                formatted_posts.append(post_data)
                continue
            except Exception as e:
                logger.error(f"Error parsing mastodon_post JSON: {e}")
                # Fall back to legacy format on error
        
        # Fall back to legacy format with adjusted field names for Mastodon compatibility
        post_data = {
            "id": row[0],
            "created_at": row[5].isoformat() if row[5] else None,
            "content": row[3],
            "favourites_count": row[6].get("favorites", 0) if row[6] else 0,
            "reblogs_count": row[6].get("reblogs", 0) if row[6] else 0,
            "replies_count": row[6].get("replies", 0) if row[6] else 0
        }
        formatted_posts.append(post_data)
    
    return jsonify(formatted_posts)

@posts_bp.route('/trending', methods=['GET'])
@log_route
def get_trending_posts():
    """
    Get posts with highest interaction counts.
    
    Query parameters:
        limit: Maximum number of posts to return (default: 10)
    
    Returns:
        200 OK with trending posts
        500 Server Error on failure
    """
    limit = request.args.get('limit', default=10, type=int)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get posts with highest total interactions using jsonb functionality
            cur.execute('''
                SELECT 
                    post_id, 
                    author_id, 
                    author_name,
                    content, 
                    content_type,
                    created_at, 
                    interaction_counts,
                    (
                        COALESCE((interaction_counts->>'favorites')::int, 0) + 
                        COALESCE((interaction_counts->>'reblogs')::int, 0) + 
                        COALESCE((interaction_counts->>'replies')::int, 0)
                    ) as total_interactions,
                    mastodon_post
                FROM post_metadata
                ORDER BY total_interactions DESC, created_at DESC
                LIMIT %s
            ''', (limit,))
            
            trending_posts = cur.fetchall()
    
    # Process posts in Mastodon format when available
    formatted_posts = []
    for row in trending_posts:
        mastodon_post = row[8]
        
        if mastodon_post:
            # Use Mastodon format if available
            try:
                if isinstance(mastodon_post, str):
                    post_data = json.loads(mastodon_post)
                else:
                    post_data = mastodon_post
                # Add the total interactions for sorting/ranking purposes
                post_data["total_interactions"] = row[7]
                formatted_posts.append(post_data)
                continue
            except Exception as e:
                logger.error(f"Error parsing mastodon_post JSON: {e}")
                # Fall back to legacy format on error
        
        # Fall back to legacy format with adjusted field names for Mastodon compatibility
        post_data = {
            "id": row[0],
            "created_at": row[5].isoformat() if row[5] else None,
            "content": row[3],
            "favourites_count": row[6].get("favorites", 0) if row[6] else 0,
            "reblogs_count": row[6].get("reblogs", 0) if row[6] else 0,
            "replies_count": row[6].get("replies", 0) if row[6] else 0,
            "total_interactions": row[7]
        }
        formatted_posts.append(post_data)
    
    return jsonify(formatted_posts)