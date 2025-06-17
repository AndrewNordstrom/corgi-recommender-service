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

from config import ALGORITHM_CONFIG, MIN_RANKING_SCORE
from db.connection import get_db_connection, get_cursor, USE_IN_MEMORY_DB
from utils.privacy import generate_user_alias

# Set up logging
logger = logging.getLogger(__name__)


def load_model_configuration(model_id: int) -> Optional[Dict]:
    """
    Load model configuration from the ab_variants table.
    
    Args:
        model_id: ID of the variant/model to load
        
    Returns:
        Dictionary with 'name' and 'config' keys, or None if not found
    """
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                if USE_IN_MEMORY_DB:
                    # For SQLite, we'll create a simple fallback
                    logger.warning("Model configuration loading not fully supported in SQLite mode")
                    return None
                else:
                    # PostgreSQL version
                    cur.execute("""
                        SELECT name, algorithm_config 
                        FROM ab_variants 
                        WHERE id = %s
                    """, (model_id,))
                    
                    row = cur.fetchone()
                    if row:
                        name, config_json = row
                        # Parse the JSON configuration
                        if config_json:
                            try:
                                config = json.loads(config_json) if isinstance(config_json, str) else config_json
                                return {
                                    'name': name,
                                    'config': config
                                }
                            except json.JSONDecodeError as e:
                                logger.error(f"Invalid JSON in algorithm_config for model {model_id}: {e}")
                                return None
                        else:
                            logger.warning(f"Model {model_id} has no algorithm_config")
                            return None
                    else:
                        logger.warning(f"Model {model_id} not found in ab_variants table")
                        return None
                        
    except Exception as e:
        logger.error(f"Error loading model configuration for model {model_id}: {e}")
        return None


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
    languages: Optional[List[str]] = None,
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
        languages: List of languages to filter posts by

    Returns:
        List of post records with post_id, author_id, content, etc.
    """
    # First check how many real posts we have available in total (for diagnostics)
    with get_cursor(conn) as cur:
        if USE_IN_MEMORY_DB:
            # SQLite version - check both posts and crawled_posts tables
            cur.execute("SELECT COUNT(*) FROM posts")
            posts_count = cur.fetchone()[0]
            
            try:
                cur.execute("SELECT COUNT(*) FROM crawled_posts")
                crawled_count = cur.fetchone()[0]
            except:
                crawled_count = 0
                
            total_real_posts = posts_count + crawled_count
            total_synthetic_posts = 0  # SQLite doesn't distinguish synthetic posts
        else:
            # PostgreSQL version
            cur.execute("SELECT COUNT(*) FROM post_metadata WHERE mastodon_post IS NOT NULL")
            total_real_posts = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM post_metadata WHERE mastodon_post IS NULL")
            total_synthetic_posts = cur.fetchone()[0]

        logger.info(f"Database contains {total_real_posts} real posts and {total_synthetic_posts} synthetic posts")

    exclude_clause = ""
    language_clause = ""
    params = []
    
    if USE_IN_MEMORY_DB:
        # SQLite version - get from both posts and crawled_posts tables
        if exclude_post_ids and len(exclude_post_ids) > 0:
            placeholders = ", ".join(["?"] * len(exclude_post_ids))
            exclude_clause = f"AND post_id NOT IN ({placeholders})"
            params.extend(exclude_post_ids)
        
        if languages:
            lang_placeholders = ", ".join(["?"] * len(languages))
            language_clause = f"AND language IN ({lang_placeholders})"
            params.extend(languages)
            
        # Finalize params for SQLite (need to duplicate for UNION)
        params_posts = params.copy()
        params_crawled = params.copy()
        params_posts.append(limit // 2)  # Split limit between tables
        params_crawled.append(limit // 2)

        query = f"""
            SELECT post_id, author_id, content, created_at, metadata, language, 'posts' as source_table
            FROM posts
            WHERE 1=1
            {exclude_clause}
            {language_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
        
        # Also query crawled_posts table
        crawled_query = f"""
            SELECT post_id, author_id, content, created_at, 
                   json_object('interaction_counts', json_object(
                       'favorites', favourites_count,
                       'reblogs', reblogs_count, 
                       'replies', replies_count
                   )) as metadata,
                   language, 'crawled_posts' as source_table
            FROM crawled_posts
            WHERE 1=1
            {exclude_clause}
            {language_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
    else:
        # PostgreSQL version
        mastodon_clause = "AND mastodon_post IS NOT NULL" if not include_synthetic else ""
        params = [days_limit]
        
        if exclude_post_ids and len(exclude_post_ids) > 0:
            placeholders = ", ".join(["%s"] * len(exclude_post_ids))
            exclude_clause = f"AND pm.post_id NOT IN ({placeholders})"
            params.extend(exclude_post_ids)
            
        if languages:
            lang_placeholders = ", ".join(["%s"] * len(languages))
            language_clause = f"AND pm.language IN ({lang_placeholders})"
            params.extend(languages)
        
        # Finalize params for PostgreSQL
        params.append(limit)
            
        query = f"""
            SELECT pm.post_id, pm.author_id, pm.author_name, pm.content, 
                   pm.created_at, pm.interaction_counts, pm.language
            FROM post_metadata pm
            WHERE pm.created_at > NOW() - INTERVAL '%s days'
            {exclude_clause}
            {language_clause}
            {mastodon_clause}
            ORDER BY pm.created_at DESC
            LIMIT %s
        """

    with get_cursor(conn) as cur:
        if USE_IN_MEMORY_DB:
            # Execute both queries and combine results
            logger.debug(f"Executing posts query: {query}")
            cur.execute(query, params_posts)
            posts_results = cur.fetchall()
            posts_columns = [desc[0] for desc in cur.description]
            
            logger.debug(f"Executing crawled_posts query: {crawled_query}")
            cur.execute(crawled_query, params_crawled)
            crawled_results = cur.fetchall()
            crawled_columns = [desc[0] for desc in cur.description]
            
            # Combine results and deduplicate by post_id
            all_results = []
            seen_post_ids = set()
            
            # Add posts from posts table first
            for row in posts_results:
                post_dict = dict(zip(posts_columns, row))
                post_id = post_dict.get('post_id')
                if post_id and post_id not in seen_post_ids:
                    all_results.append(post_dict)
                    seen_post_ids.add(post_id)
            
            # Add posts from crawled_posts table, avoiding duplicates
            for row in crawled_results:
                post_dict = dict(zip(crawled_columns, row))
                post_id = post_dict.get('post_id')
                if post_id and post_id not in seen_post_ids:
                    all_results.append(post_dict)
                    seen_post_ids.add(post_id)
            
            # Sort by created_at and limit
            all_results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            results = all_results[:limit]
            
            logger.info(f"Found {len(posts_results)} posts from posts table, {len(crawled_results)} from crawled_posts table, {len(results)} total")
        else:
            logger.debug(f"Executing query: {query}")
            cur.execute(query, params)
            results = cur.fetchall()
            
            logger.info(f"Found {len(results)} candidate posts")

            # Convert to list of dictionaries
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, row)) for row in results]

        return results


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

    # If we still have no interactions linked to this author, return baseline.
    # This means the user has interactions with other authors, but not with this specific author.
    if author_interactions["total"] == 0:
        return 0.1

    # --------------------------------------------------------------
    # Standard path – we have at least one interaction for the target
    # author, so compute the preference score normally.
    # --------------------------------------------------------------
    positive_ratio = author_interactions["positive"] / author_interactions["total"]
    preference_score = 1 / (1 + math.exp(-5 * (positive_ratio - 0.5)))

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
    post: Dict, user_interactions: List[Dict], algorithm_config: Optional[Dict] = None
) -> Tuple[float, str]:
    """
    Calculate the overall ranking score for a post using specified algorithm configuration.

    Args:
        post: Post record to rank
        user_interactions: User's past interactions
        algorithm_config: Algorithm configuration to use. If None, uses default ALGORITHM_CONFIG.

    Returns:
        Tuple of (score, reason_detail) where score is between 0 and 1 and reason_detail is specific
    """
    # Use provided config or fall back to default
    if algorithm_config is None:
        algorithm_config = ALGORITHM_CONFIG
    
    # Calculate individual feature scores
    author_score = get_author_preference_score(user_interactions, post["author_id"])
    engagement_score = get_content_engagement_score(post)
    recency_score = get_recency_score(post)

    # Combine scores using weights from algorithm config
    weights = algorithm_config["weights"]
    overall_score = (
        weights["author_preference"] * author_score
        + weights["content_engagement"] * engagement_score
        + weights["recency"] * recency_score
    )

    # Generate specific recommendation reason based on discovery data and scoring
    reason_detail = generate_specific_recommendation_reason_from_ranking(
        post, user_interactions, author_score, engagement_score, recency_score, weights
    )

    return overall_score, reason_detail


def generate_specific_recommendation_reason_from_ranking(post: Dict, user_interactions: List[Dict], 
                                                      author_score: float, engagement_score: float, 
                                                      recency_score: float, weights: Dict) -> str:
    """
    Generate specific recommendation reason based on ranking factors and discovery metadata.
    
    Args:
        post: Post record with metadata
        user_interactions: User's interaction history
        author_score: Calculated author preference score
        engagement_score: Content engagement score
        recency_score: Recency score
        weights: Algorithm weights
        
    Returns:
        Specific reason string for the recommendation
    """
    # Check if we have specific discovery reason data
    reason_type = post.get('recommendation_reason_type')
    reason_detail = post.get('recommendation_reason_detail')
    
    # Priority 1: Use discovery-specific reasons if available
    if reason_type == 'hashtag_trending' and reason_detail:
        return f"Trending in {reason_detail}"
    
    elif reason_type == 'author_network' and reason_detail:
        return f"Popular among followers of {reason_detail}"
    
    elif reason_type == 'federated_trending' and reason_detail:
        return f"Trending on {reason_detail}"
    
    elif reason_type == 'local_trending' and reason_detail:
        return f"Popular on {reason_detail}"
    
    # Priority 2: Use user interaction patterns for personalized reasons
    if author_score > 0.6:
        # Find specific author interaction (safely check for post_author_id field)
        author_interactions = [i for i in user_interactions if i.get('post_author_id') == post['author_id']]
        if author_interactions:
            return f"Because you liked a post by this author"
        
    # Priority 3: Use weighted scoring to determine dominant factor
    weighted_scores = [
        (author_score * weights["author_preference"], "author_preference"),
        (engagement_score * weights["content_engagement"], "engagement"), 
        (recency_score * weights["recency"], "trending")
    ]
    
    max_weighted_score, dominant_factor = max(weighted_scores, key=lambda x: x[0])
    
    # Generate contextual reasons based on dominant factor
    if dominant_factor == "engagement" and engagement_score > 0.7:
        return "Popular in your network"
    elif dominant_factor == "trending" and recency_score > 0.8:
        return "Trending in topics you follow"
    elif dominant_factor == "author_preference":
        return "Based on posts you've liked"
    
    # Fallback to generic reason with some specificity
    if post.get('tags') and len(post['tags']) > 0:
        # Use the first tag for some specificity
        first_tag = post['tags'][0] if isinstance(post['tags'], list) else post['tags']
        return f"Trending in topics you follow"
    
    return "Recommended for you"


def generate_rankings_for_user(user_id: str, model_id: Optional[int] = None, languages: Optional[List[str]] = None) -> List[Dict]:
    """
    Generate post rankings for a specific user using a specific model configuration.

    This function orchestrates the entire ranking process:
    1. Load model configuration (if model_id provided)
    2. Fetch user's past interactions
    3. Get candidate posts
    4. Calculate scores for each post using model parameters
    5. Store rankings in the database
    6. Return ranked posts

    Args:
        user_id: User ID to generate rankings for
        model_id: Optional variant ID to use for algorithm configuration.
                 If provided, loads parameters from ab_variants table.
                 If None, uses default ALGORITHM_CONFIG.
        languages: List of languages to filter posts by

    Returns:
        List of ranked posts with scores and reasons
    """
    try:
        # Get pseudonymized user ID for privacy
        user_alias = generate_user_alias(user_id)

        # Step 0: Load model configuration if model_id is provided
        algorithm_config = ALGORITHM_CONFIG.copy()  # Start with defaults
        model_name = "default"
        
        if model_id is not None:
            model_config = load_model_configuration(model_id)
            if model_config:
                algorithm_config = model_config['config']
                model_name = model_config['name']
                logger.info(f"Using model '{model_name}' (ID: {model_id}) for user {user_alias}")
            else:
                logger.warning(f"Model ID {model_id} not found, falling back to default configuration")
        else:
            logger.info(f"Using default algorithm configuration for user {user_alias}")

        with get_db_connection() as conn:
            # Step 1: Get user's interaction history
            user_interactions = get_user_interactions(conn, user_alias, days_limit=30)
            logger.info(
                f"Retrieved {len(user_interactions)} interactions for user {user_alias}"
            )

            # ------------------------------------------------------------------
            # DATA AUGMENTATION ‑ ensure each interaction knows the author of the
            # corresponding post.  The downstream reasoning helper
            # (generate_specific_recommendation_reason_from_ranking) expects a
            # 'post_author_id' field.  In production this information is easy to
            # look up; in our earlier implementation it was missing which led to
            # a KeyError.  We perform a single batched lookup **once** for all
            # interactions to avoid per-row queries.
            # ------------------------------------------------------------------
            try:
                interaction_post_ids = [i["post_id"] for i in user_interactions]

                if interaction_post_ids:
                    # Deduplicate and respect reasonable upper bound to keep
                    # query efficient.
                    unique_ids = list(dict.fromkeys(interaction_post_ids))[:500]

                    if USE_IN_MEMORY_DB:
                        placeholders = ", ".join(["?"] * len(unique_ids))
                        lookup_query = (
                            f"SELECT post_id, author_id FROM posts WHERE post_id IN ({placeholders})"
                        )
                    else:
                        placeholders = ", ".join(["%s"] * len(unique_ids))
                        lookup_query = (
                            f"SELECT post_id, author_id FROM post_metadata WHERE post_id IN ({placeholders})"
                        )

                    with get_cursor(conn) as cur_lookup:
                        cur_lookup.execute(lookup_query, tuple(unique_ids))
                        mapping_rows = cur_lookup.fetchall()

                    post_to_author = {pid: aid for pid, aid in mapping_rows}

                    # Attach author id to each interaction dict (if available)
                    for interaction in user_interactions:
                        pid = interaction.get("post_id")
                        interaction["post_author_id"] = post_to_author.get(pid)

                    logger.debug(
                        f"Augmented {len(user_interactions)} interactions with author IDs"
                    )
            except Exception as aug_err:
                # Non-fatal – log and continue without augmentation (fallback
                # logic in the reason generator will simply skip author-specific
                # rules).
                logger.warning(
                    f"Unable to augment interactions with author IDs: {aug_err}"
                )

            # Extract post IDs the user has already interacted with
            seen_post_ids = [
                interaction["post_id"] for interaction in user_interactions
            ]

            # Step 2: Get candidate posts, excluding any the user has interacted with
            # and respecting language preferences
            candidate_posts = get_candidate_posts(
                conn, exclude_post_ids=seen_post_ids, languages=languages
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
                score, reason = calculate_ranking_score(post, user_interactions, algorithm_config)

                # Include only posts with reasonable scores (configurable threshold)
                if score > MIN_RANKING_SCORE:
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
