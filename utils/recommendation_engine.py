"""
Recommendation Engine Module for the Corgi Recommender Service.

This module provides functions for generating and retrieving personalized
recommendations for users based on their interactions and preferences.
"""

import logging
import json
import os
import time
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta

from db.connection import get_db_connection
from utils.privacy import generate_user_alias
from core.ranking_algorithm import generate_rankings_for_user
from utils.metrics import track_recommendation_score

# Setup logger
logger = logging.getLogger(__name__)

# Path to cold start posts JSON file (as fallback)
COLD_START_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "cold_start_formatted.json"
)


def load_cold_start_posts(languages: Optional[List[str]] = None) -> List[Dict]:
    """
    Load cold start posts from the JSON file.

    Args:
        languages: Optional list of language codes to filter by (e.g., ['en', 'es'])

    Returns:
        List of pre-formatted cold start posts, optionally filtered by language
    """
    try:
        with open(COLD_START_DATA_PATH, "r") as f:
            cold_start_posts = json.load(f)
            
        # Filter by language if specified
        if languages:
            filtered_posts = []
            for post in cold_start_posts:
                post_lang = post.get('language', 'en')  # Default to 'en' if no language specified
                if post_lang in languages:
                    filtered_posts.append(post)
            cold_start_posts = filtered_posts
            
        logger.info(f"Loaded {len(cold_start_posts)} cold start posts" + 
                   (f" (filtered for languages: {', '.join(languages)})" if languages else ""))

        # No need to track metrics here as it will be tracked by the calling functions
        # This function just loads data; the decision to use it is what we track

        return cold_start_posts
    except Exception as e:
        logger.error(f"Error loading cold start posts: {e}")
        # Track the failure to load cold start posts
        from utils.metrics import FALLBACK_USAGE_TOTAL

        FALLBACK_USAGE_TOTAL.labels(reason="cold_start_load_error").inc()
        return []


def is_new_user(user_id: str) -> bool:
    """
    Determine if a user is new or has low activity based on interaction history.

    Args:
        user_id: The user ID to check

    Returns:
        True if the user is new or has low activity, False otherwise
    """
    if not user_id or user_id == "anonymous":
        return True

    # For synthetic users, always consider them new
    if user_id.startswith("corgi_validator_") or user_id.startswith("test_"):
        return True

    try:
        # Get pseudonymized user ID for privacy
        user_alias = generate_user_alias(user_id)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if the user has any interactions in the past 30 days
                cur.execute(
                    """
                    SELECT COUNT(*) 
                    FROM interactions 
                    WHERE user_alias = %s 
                    AND created_at > NOW() - INTERVAL '30 days'
                """,
                    (user_alias,),
                )

                count = cur.fetchone()[0]

                # If the user has fewer than 5 interactions, consider them new
                return count < 5

    except Exception as e:
        logger.error(f"Error checking if user {user_id} is new: {e}")
        return True  # Default to treating as new user on error


def get_ranked_recommendations(user_id: str, limit: int = 10, languages: Optional[List[str]] = None) -> List[Dict]:
    """
    Get personalized ranked recommendations for a user.

    This function fetches and ranks recommended posts for the specified user
    based on their interaction history and preferences. If the user is new or
    has insufficient data, it falls back to cold start recommendations.

    Args:
        user_id: The user ID to get recommendations for
        limit: Maximum number of recommendations to return
        languages: List of languages to consider for recommendations

    Returns:
        List of recommended posts in ranked order, formatted as Mastodon-compatible posts
    """
    # For anonymous users or when user_id is None, use cold start data
    if not user_id or user_id == "anonymous":
        logger.info(f"Using cold start recommendations for anonymous user")
        return load_cold_start_posts(languages=languages)

    # For synthetic or validator users, use cold start data
    if user_id.startswith("corgi_validator_") or user_id.startswith("test_"):
        logger.info(f"Using cold start recommendations for synthetic user {user_id}")
        return load_cold_start_posts(languages=languages)

    # Check if user is new or has low activity
    if is_new_user(user_id):
        logger.info(
            f"User {user_id} is new or has low activity, using cold start recommendations"
        )
        return load_cold_start_posts(languages=languages)

    # Get pseudonymized user ID for privacy
    try:
        user_alias = generate_user_alias(user_id)
        logger.debug(f"Generated user alias for {user_id}")
    except Exception as e:
        logger.error(f"Error generating user alias: {e}")
        return load_cold_start_posts(languages=languages)

    try:
        # Generate rankings for this user
        logger.info(f"Generating rankings for user {user_id} with languages: {languages}")
        start_time = time.time()
        ranked_posts = generate_rankings_for_user(user_id, languages=languages)
        elapsed = time.time() - start_time
        logger.info(f"Rankings generation took {elapsed:.3f} seconds")

        if not ranked_posts:
            logger.warning(
                f"No ranked posts generated for user {user_id}, falling back to cold start"
            )
            return load_cold_start_posts(languages=languages)

        # Sort by ranking score (descending) and limit to requested number
        ranked_posts.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)
        ranked_posts = ranked_posts[:limit]

        # Transform ranked posts into Mastodon-compatible format
        mastodon_posts = []

        for post in ranked_posts:
            # Start with any existing Mastodon post data if available
            mastodon_post = None

            # Attempt to load any stored Mastodon post data
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        # First try post_metadata table
                        cur.execute(
                            """
                            SELECT mastodon_post
                            FROM post_metadata
                            WHERE post_id = %s
                        """,
                            (post["post_id"],),
                        )

                        result = cur.fetchone()
                        if result and result[0]:
                            mastodon_post = result[0]
                        else:
                            # If not found, try crawled_posts table and construct mastodon_post
                            cur.execute(
                                """
                                SELECT post_id, content, author_username, author_acct, author_display_name,
                                       author_avatar, created_at, favourites_count, reblogs_count, replies_count,
                                       url, source_instance, language, author_id
                                FROM crawled_posts
                                WHERE post_id = %s
                            """,
                                (post["post_id"],),
                            )
                            
                            crawled_result = cur.fetchone()
                            if crawled_result:
                                (cp_id, cp_content, cp_username, cp_acct, cp_display_name, cp_avatar, 
                                 cp_created_at, cp_favs, cp_reblogs, cp_replies, cp_url, cp_instance, 
                                 cp_language, cp_author_id) = crawled_result
                                
                                # Construct mastodon_post from crawled_posts data
                                mastodon_post = {
                                    "id": cp_id,
                                    "content": cp_content or "",
                                    "created_at": cp_created_at.isoformat() if cp_created_at else datetime.now().isoformat(),
                                    "account": {
                                        "id": cp_author_id or "unknown",
                                        "username": cp_username or "unknown",
                                        "acct": cp_acct or f"{cp_username}@{cp_instance}",
                                        "display_name": cp_display_name or cp_username or "Unknown User",
                                        "avatar": cp_avatar or "",
                                        "url": f"https://{cp_instance}/@{cp_username}" if cp_instance and cp_username else "",
                                    },
                                    "favourites_count": cp_favs or 0,
                                    "reblogs_count": cp_reblogs or 0,
                                    "replies_count": cp_replies or 0,
                                    "url": cp_url or "",
                                    "language": cp_language or "en",
                                    "media_attachments": [],
                                    "mentions": [],
                                    "tags": [],
                                    "emojis": [],
                                    "visibility": "public",
                                    "_corgi_source_instance": cp_instance,
                                    "_corgi_external": True,
                                    "_corgi_cached": True,
                                }
                                logger.debug(f"Constructed mastodon_post from crawled_posts for {cp_id}")
            except Exception as e:
                logger.error(
                    f"Error fetching Mastodon post data for {post['post_id']}: {e}"
                )

            # If we have a stored Mastodon post, use it as the base
            if mastodon_post:
                formatted_post = (
                    mastodon_post.copy() if isinstance(mastodon_post, dict) else {}
                )
            else:
                # Otherwise, create a new Mastodon-compatible post
                formatted_post = {
                    "id": post["post_id"],
                    "post_id": post["post_id"],
                    "content": post.get("content", "No content available"),
                    "created_at": post.get("created_at", datetime.now().isoformat()),
                    "account": {
                        "id": post.get("author_id", "unknown"),
                        "username": post.get("author_name", "unknown"),
                        "display_name": post.get("author_name", "Unknown User"),
                        "url": f"https://example.com/@{post.get('author_name', 'unknown')}",
                    },
                    "media_attachments": [],
                    "mentions": [],
                    "tags": [],
                    "emojis": [],
                    "favourites_count": 0,
                    "reblogs_count": 0,
                    "replies_count": 0,
                }

                # Parse interaction_counts if available
                if post.get("interaction_counts"):
                    counts = post["interaction_counts"]
                    if isinstance(counts, str):
                        try:
                            counts = json.loads(counts)
                        except:
                            counts = {}

                    # Update engagement metrics
                    formatted_post["favourites_count"] = counts.get("favorites", 0)
                    formatted_post["reblogs_count"] = counts.get("reblogs", 0)
                    formatted_post["replies_count"] = counts.get("replies", 0)

            # Add recommendation metadata
            score = post.get("ranking_score", 0)
            strategy = "personalized"

            # Track recommendation score for metrics
            track_recommendation_score(strategy, score)

            formatted_post.update(
                {
                    "is_real_mastodon_post": mastodon_post is not None,
                    "is_synthetic": False,
                    "injected": True,
                    "injection_metadata": {
                        "source": "recommendation_engine",
                        "strategy": strategy,
                        "score": score,
                        "explanation": post.get(
                            "recommendation_reason",
                            "Recommended based on your interests",
                        ),
                    },
                }
            )

            mastodon_posts.append(formatted_post)

        # Track metrics directly
        from utils.metrics import RECOMMENDATIONS_TOTAL

        RECOMMENDATIONS_TOTAL.labels(
            source="recommendation_engine", user_type="returning_user"
        ).inc(len(mastodon_posts))

        logger.info(
            f"Generated {len(mastodon_posts)} personalized recommendations for user {user_id}"
        )
        return mastodon_posts

    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.error(f"Error generating recommendations for user {user_id}: {e}")
        logger.error(f"Recommendation error traceback: {error_trace}")
        logger.info(f"Falling back to cold start recommendations due to error")

        # Track fallback directly
        from utils.metrics import FALLBACK_USAGE_TOTAL, RECOMMENDATIONS_TOTAL

        FALLBACK_USAGE_TOTAL.labels(reason="recommendation_error").inc()

        # Load and track cold start recommendations
        cold_start_posts = load_cold_start_posts(languages=languages)
        RECOMMENDATIONS_TOTAL.labels(
            source="cold_start", user_type="returning_user_error_fallback"
        ).inc(len(cold_start_posts))

        return cold_start_posts


def load_static_cold_start_posts(limit: int = 10) -> List[Dict]:
    """
    Load static cold start posts from pre-defined content.
    
    This provides baseline recommendations when dynamic content is not available.
    
    Args:
        limit: Maximum number of posts to return
        
    Returns:
        List of static cold start posts
    """
    try:
        # Return a subset of the static cold start posts
        all_static_posts = load_cold_start_posts()
        return all_static_posts[:limit]
        
    except Exception as e:
        logger.error(f"Error loading static cold start posts: {e}")
        return []


def get_dynamic_cold_start_posts(language: str = 'en', limit: int = 10) -> List[Dict]:
    """
    Get dynamic cold start posts based on current trends and language preferences.
    
    Args:
        language: Language preference for posts
        limit: Maximum number of posts to return
        
    Returns:
        List of trending posts formatted for display
    """
    try:
        from db.connection import get_db_connection
        
        # Try to get trending posts from the last 24 hours
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    post_id,
                    author_id,
                    content,
                    created_at,
                    metadata
                FROM posts 
                WHERE 
                    created_at > datetime('now', '-24 hours')
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            posts = cur.fetchall()
            
            if not posts:
                # Fall back to recent posts
                cur.execute("""
                    SELECT 
                        post_id,
                        author_id,
                        content,
                        created_at,
                        metadata
                    FROM posts 
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                
                posts = cur.fetchall()
        
        # Format posts as Mastodon-compatible objects
        formatted_posts = []
        for post in posts:
            post_id, author_id, content, created_at, metadata = post
            
            # Parse metadata JSON if it exists
            try:
                metadata_dict = json.loads(metadata) if metadata else {}
            except:
                metadata_dict = {}
            
            # Extract author name from author_id or use default
            author_name = author_id.split('@')[0] if '@' in author_id else (author_id or 'unknown')
            
            formatted_post = {
                "id": post_id,
                "post_id": post_id,
                "content": content or "No content available",
                "created_at": created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at),
                "account": {
                    "id": f"dynamic_{author_name}",
                    "username": author_name,
                    "display_name": author_name or "Unknown User",
                    "url": f"https://example.com/@{author_name}",
                },
                "media_attachments": [],
                "mentions": [],
                "tags": [],
                "emojis": [],
                "favourites_count": metadata_dict.get('favorites', 0),
                "reblogs_count": metadata_dict.get('boosts', 0),
                "replies_count": metadata_dict.get('replies', 0),
                "language": language,
                "is_real_mastodon_post": False,
                "is_synthetic": False,
                "injected": True,
                "injection_metadata": {
                    "source": "dynamic_cold_start",
                    "strategy": "recent",
                    "language": language,
                    "explanation": "Recent post from database",
                },
            }
            
            formatted_posts.append(formatted_post)
        
        logger.info(f"Generated {len(formatted_posts)} dynamic cold start posts for language '{language}'")
        return formatted_posts
        
    except Exception as e:
        logger.error(f"Error generating dynamic cold start posts: {e}")
        # Fall back to static cold start posts
        return load_cold_start_posts()[:limit]
