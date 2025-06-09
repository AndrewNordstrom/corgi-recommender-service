"""
Ranking Algorithm Module for the Corgi Recommender Service.

This module provides the core logic for ranking posts based on user preferences,
engagement metrics, and recency.

Functions:
    - get_user_interactions: Retrieve a user's interactions from the database
    - get_candidate_posts: Retrieve candidate posts for ranking
    - calculate_ranking_score: Calculate overall ranking score for a post
    - generate_rankings_for_user: Generate and store post rankings for a user
"""

import logging
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

from config import ALGORITHM_CONFIG
from db.connection import get_db_connection, get_cursor, USE_IN_MEMORY_DB
from utils.privacy import generate_user_alias

# Set up logging
logger = logging.getLogger(__name__)


def get_user_interactions(conn, user_id: str, days_limit: int = 30) -> List[Dict]:
    """
    Retrieve a user's interactions from the database.

    Args:
        conn: Database connection
        user_id: The user's pseudonymized ID
        days_limit: How far back to look for interactions

    Returns:
        List of interaction records with post_id, action_type, etc.
    """
    # Use get_cursor for proper cursor management
    with get_cursor(conn) as cur:
        if USE_IN_MEMORY_DB:
            # SQLite version with different table structure and NO context column
            cur.execute(
                """
                SELECT post_id, interaction_type as action_type, created_at
                FROM interactions
                WHERE user_id = ? 
                AND datetime(created_at) > datetime('now', '-' || ? || ' days')
                ORDER BY created_at DESC
            """,
                (user_id, days_limit),
            )
        else:
            # PostgreSQL version
            cur.execute(
                """
                SELECT post_id, action_type, context, created_at
                FROM interactions
                WHERE user_alias = %s 
                AND created_at > NOW() - INTERVAL '%s days'
                ORDER BY created_at DESC
            """,
                (user_id, days_limit),
            )

        # Convert to list of dictionaries
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        interactions = []
        for row in rows:
            interaction = dict(zip(columns, row))
            # Ensure context field exists for SQLite (which doesn't have this column)
            if 'context' not in interaction:
                interaction['context'] = {}
            interactions.append(interaction)
            
        return interactions


def get_candidate_posts(
    conn,
    limit: int = 100,
    days_limit: int = 7,
    exclude_post_ids: List[str] = None,
    include_synthetic: bool = False,
) -> List[Dict]:
    """
    Retrieve candidate posts for ranking.

    Args:
        conn: Database connection to the posts database
        limit: Maximum number of posts to retrieve
        days_limit: How recent the posts should be
        exclude_post_ids: List of post IDs to exclude (e.g., already seen)
        include_synthetic: Whether to include synthetic posts (default: False)
                          If False, only returns posts with mastodon_post NOT NULL
                          If True, includes all posts

    Returns:
        List of post records with post_id, author_id, content, etc.
    """
    # First check how many real posts we have available in total (for diagnostics)
    with get_cursor(conn) as cur:
        if USE_IN_MEMORY_DB:
            # SQLite version
            cur.execute("SELECT COUNT(*) FROM posts")
            total_real_posts = cur.fetchone()[0]
            total_synthetic_posts = 0  # SQLite doesn't distinguish synthetic posts
        else:
            # PostgreSQL version
            cur.execute("SELECT COUNT(*) FROM post_metadata WHERE mastodon_post IS NOT NULL")
            total_real_posts = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM post_metadata WHERE mastodon_post IS NULL")
            total_synthetic_posts = cur.fetchone()[0]

        logger.info(f"Database contains {total_real_posts} real posts and {total_synthetic_posts} synthetic posts")

    exclude_clause = ""
    params = []
    
    if USE_IN_MEMORY_DB:
        # SQLite version - get from posts table
        if exclude_post_ids and len(exclude_post_ids) > 0:
            placeholders = ", ".join(["?"] * len(exclude_post_ids))
            exclude_clause = f"AND post_id NOT IN ({placeholders})"
            params = exclude_post_ids + [limit]
        else:
            params = [limit]
            
        query = f"""
            SELECT post_id, author_id, content, created_at, metadata
            FROM posts
            WHERE 1=1
            {exclude_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
    else:
        # PostgreSQL version
        mastodon_clause = "AND mastodon_post IS NOT NULL" if not include_synthetic else ""
        params = [days_limit]
        
        if exclude_post_ids and len(exclude_post_ids) > 0:
            placeholders = ", ".join(["%s"] * len(exclude_post_ids))
            exclude_clause = f"AND post_id NOT IN ({placeholders})"
            params = [days_limit] + exclude_post_ids + [limit]
        else:
            params = [days_limit, limit]
            
        query = f"""
            SELECT post_id, author_id, author_name, content, created_at, interaction_counts
            FROM post_metadata
            WHERE created_at > NOW() - INTERVAL '%s days'
            {exclude_clause}
            {mastodon_clause}
            ORDER BY created_at DESC
            LIMIT %s
        """

    with get_cursor(conn) as cur:
        logger.debug(f"Executing query: {query}")
        cur.execute(query, params)
        results = cur.fetchall()
        
        logger.info(f"Found {len(results)} candidate posts")

        # Convert to list of dictionaries
        columns = [desc[0] for desc in cur.description]
        result_dicts = [dict(zip(columns, row)) for row in results]

        return result_dicts


def get_author_preference_score(user_interactions: List[Dict], author_id: str) -> float:
    """
    Calculate how much a user prefers content from a specific author.

    Args:
        user_interactions: List of user's past interactions
        author_id: ID of the author to calculate preference for

    Returns:
        A score between 0 and 1 indicating preference level
    """
    if not user_interactions or not author_id:
        return 0.1  # Return baseline if no interactions or no author

    # Define positive and negative interaction types
    positive_actions = ["favorite", "bookmark", "reblog", "more_like_this"]
    negative_actions = ["less_like_this"]

    # Track the posts the user has interacted with to retrieve author data
    post_ids = [interaction["post_id"] for interaction in user_interactions]

    if not post_ids:
        return 0.1  # Return baseline if no post interactions

    # Get a mapping of post_id -> author_id for all post IDs the user has interacted with
    post_author_map = {}
    try:
        from db.connection import get_db_connection

        with get_db_connection() as conn:
            # Limit the query to 100 posts maximum to avoid performance issues
            post_ids_subset = post_ids[:100]

            if len(post_ids_subset) == 1:
                if USE_IN_MEMORY_DB:
                    query = "SELECT post_id, author_id FROM posts WHERE post_id = ?"
                    params = (post_ids_subset[0],)
                else:
                    query = "SELECT post_id, author_id FROM post_metadata WHERE post_id = %s"
                    params = (post_ids_subset[0],)
            else:
                if USE_IN_MEMORY_DB:
                    placeholders = ", ".join(["?"] * len(post_ids_subset))
                    query = f"SELECT post_id, author_id FROM posts WHERE post_id IN ({placeholders})"
                    params = tuple(post_ids_subset)
                else:
                    placeholders = ", ".join(["%s"] * len(post_ids_subset))
                    query = f"SELECT post_id, author_id FROM post_metadata WHERE post_id IN ({placeholders})"
                    params = tuple(post_ids_subset)

            with get_cursor(conn) as cur:
                cur.execute(query, params)
                for post_id, post_author_id in cur.fetchall():
                    post_author_map[post_id] = post_author_id
    except Exception as e:
        logger.error(f"Error getting post author mapping: {e}")
        return 0.1  # Return baseline on error

    # Count interactions with this specific author
    author_interactions = {"positive": 0, "negative": 0, "total": 0}

    # Process all interactions for the target author
    for interaction in user_interactions:
        post_id = interaction["post_id"]
        if post_id in post_author_map and post_author_map[post_id] == author_id:
            action_type = interaction["action_type"]
            author_interactions["total"] += 1

            if action_type in positive_actions:
                author_interactions["positive"] += 1
            elif action_type in negative_actions:
                author_interactions["negative"] += 1

    # Calculate preference score based on interaction data
    if author_interactions["total"] == 0:
        return 0.1  # Baseline score for authors without interactions

    # Calculate positive ratio (with a small epsilon to avoid division by zero)
    positive_ratio = author_interactions["positive"] / (
        author_interactions["total"] + 0.001
    )

    # Apply a sigmoid function to map the ratio to a 0-1 range with a smooth curve
    import math

    preference_score = 1 / (1 + math.exp(-5 * (positive_ratio - 0.5)))

    # Ensure minimum score is still the baseline
    return max(preference_score, 0.1)


def get_content_engagement_score(post: Dict) -> float:
    """
    Calculate an engagement score based on favorites, reblogs, and replies.

    Args:
        post: Post record with interaction_counts

    Returns:
        A score between 0 and 1 indicating engagement level
    """
    # Get engagement metrics from interaction_counts
    if not post.get("interaction_counts"):
        return 0.0

    # Parse the JSONB data if needed
    counts = post["interaction_counts"]
    if isinstance(counts, str):
        try:
            counts = json.loads(counts)
        except:
            return 0.0

    # Extract counts with fallbacks to 0
    favorites = int(counts.get("favorites", 0))
    reblogs = int(counts.get("reblogs", 0))
    replies = int(counts.get("replies", 0))

    # Simple engagement score - can be replaced with more sophisticated metrics
    total = favorites + reblogs + replies

    # Logarithmic scaling to prevent very popular posts from completely dominating
    # Add 1 to avoid log(0)
    return math.log(total + 1) / 10.0  # Normalize to roughly 0-1 range


def get_recency_score(post: Dict) -> float:
    """
    Calculate how recent a post is, with exponential decay.

    Args:
        post: Post record with created_at timestamp

    Returns:
        A score between 0 and 1, with 1 being most recent
    """
    if not post.get("created_at"):
        # If no timestamp, use a default middle value
        return 0.5

    # Parse timestamp if it's a string
    created_at = post["created_at"]
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except:
            # If parsing fails, use a default value
            return 0.5

    # Calculate age in days
    now = datetime.now()
    if hasattr(created_at, "tzinfo") and created_at.tzinfo:
        # Remove timezone information for comparison
        now = datetime.now().replace(tzinfo=None)
        created_at = created_at.replace(tzinfo=None)

    age_days = (now - created_at).total_seconds() / (24 * 3600)

    # Exponential decay based on age
    decay_factor = ALGORITHM_CONFIG["time_decay_days"]
    recency_score = math.exp(-age_days / decay_factor)

    # Ensure the score doesn't get too low, even for older posts
    return max(recency_score, 0.2)


def calculate_ranking_score(
    post: Dict, user_interactions: List[Dict]
) -> Tuple[float, str]:
    """
    Calculate the overall ranking score for a post.

    Args:
        post: Post record to rank
        user_interactions: User's past interactions

    Returns:
        Tuple of (score, reason) where score is between 0 and 1
    """
    # Calculate individual feature scores
    author_score = get_author_preference_score(user_interactions, post["author_id"])
    engagement_score = get_content_engagement_score(post)
    recency_score = get_recency_score(post)

    # Combine scores using weights
    weights = ALGORITHM_CONFIG["weights"]
    overall_score = (
        weights["author_preference"] * author_score
        + weights["content_engagement"] * engagement_score
        + weights["recency"] * recency_score
    )

    # Generate user-friendly recommendation reason based on dominant factor
    weighted_scores = [
        (author_score * weights["author_preference"], "Based on posts you've liked"),
        (engagement_score * weights["content_engagement"], "Popular in your network"), 
        (recency_score * weights["recency"], "Trending in topics you follow")
    ]
    
    # Find the highest contributing factor
    max_weighted_score, primary_reason = max(weighted_scores)
    
    # Add contextual modifiers based on multiple factors
    reason = primary_reason
    
    # If engagement is particularly high, emphasize popularity
    if engagement_score > 0.7:
        if "Popular" not in reason:
            reason = "Popular in your network"
    
    # If it's very recent and has good engagement, emphasize trending
    if recency_score > 0.8 and engagement_score > 0.5:
        reason = "Trending in topics you follow"
    
    # If user has strong author preference, emphasize that
    if author_score > 0.6:
        reason = "Based on posts you've liked"

    return overall_score, reason


def generate_rankings_for_user(user_id: str) -> List[Dict]:
    """
    Generate post rankings for a specific user.

    This function orchestrates the entire ranking process:
    1. Fetch user's past interactions
    2. Get candidate posts
    3. Calculate scores for each post
    4. Store rankings in the database
    5. Return ranked posts

    Args:
        user_id: User ID to generate rankings for

    Returns:
        List of ranked posts with scores and reasons
    """
    try:
        # Get pseudonymized user ID for privacy
        user_alias = generate_user_alias(user_id)

        with get_db_connection() as conn:
            # Step 1: Get user's interaction history
            user_interactions = get_user_interactions(conn, user_alias, days_limit=30)
            logger.info(
                f"Retrieved {len(user_interactions)} interactions for user {user_alias}"
            )

            # Extract post IDs the user has already interacted with
            seen_post_ids = [
                interaction["post_id"] for interaction in user_interactions
            ]

            # Step 2: Get candidate posts (excluding ones user has seen)
            candidate_posts = get_candidate_posts(
                conn,
                limit=ALGORITHM_CONFIG["max_candidates"],
                days_limit=14,
                exclude_post_ids=seen_post_ids,
                include_synthetic=ALGORITHM_CONFIG["include_synthetic"],
            )
            logger.debug(f"Found {len(candidate_posts)} candidate posts")

            # Return early if no candidate posts are found
            if not candidate_posts:
                logger.error(
                    "No candidate posts found — recommendation pipeline will be empty."
                )
                return []

            # Step 3: Calculate ranking scores for each post
            ranked_posts = []
            for post in candidate_posts:
                score, reason = calculate_ranking_score(post, user_interactions)

                # Include only posts with reasonable scores
                if score > 0.1:
                    post["ranking_score"] = score
                    post["recommendation_reason"] = reason
                    ranked_posts.append(post)

            # Sort by ranking score (descending)
            ranked_posts.sort(key=lambda x: x["ranking_score"], reverse=True)
            logger.info(f"Generated {len(ranked_posts)} ranked posts")

            # Step 4: Store rankings in the database
            for post in ranked_posts:
                try:
                    with get_cursor(conn) as cur:
                        if USE_IN_MEMORY_DB:
                            # SQLite version - store in recommendations table
                            cur.execute(
                                """
                                INSERT OR REPLACE INTO recommendations 
                                (user_id, post_id, score, reason)
                                VALUES (?, ?, ?, ?)
                            """,
                                (
                                    user_alias,
                                    post["post_id"],
                                    post["ranking_score"],
                                    post["recommendation_reason"],
                                ),
                            )
                        else:
                            # PostgreSQL version - store in post_rankings table
                            cur.execute(
                                """
                                INSERT INTO post_rankings 
                                (user_id, post_id, ranking_score, recommendation_reason)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (user_id, post_id) 
                                DO UPDATE SET 
                                    ranking_score = EXCLUDED.ranking_score,
                                    recommendation_reason = EXCLUDED.recommendation_reason,
                                    created_at = CURRENT_TIMESTAMP
                            """,
                                (
                                    user_alias,
                                    post["post_id"],
                                    post["ranking_score"],
                                    post["recommendation_reason"],
                                ),
                            )
                except Exception as e:
                    logger.error(
                        f"Error storing ranking for post {post['post_id']}: {e}"
                    )

            conn.commit()

            # Log success and details of ranked posts
            logger.info(
                f"Successfully generated and stored {len(ranked_posts)} rankings for user {user_alias}"
            )

            # Return the ranked posts for further use
            return ranked_posts

    except Exception as e:
        logger.error(f"Error generating rankings: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return []
