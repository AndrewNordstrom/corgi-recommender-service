"""
Timeline route with enhanced injection capabilities using timeline_injector.

This module implements the /api/v1/timelines/home endpoint with the ability
to blend real Mastodon posts with injected synthetic/recommended posts
using configurable injection strategies.
"""

import json
import logging
import time
import os
from datetime import datetime
from urllib.parse import urljoin
from flask import Blueprint, request, jsonify, Response
import requests
from typing import Optional, List, Dict, Union

from utils.logging_decorator import log_route
from utils.timeline_injector import inject_into_timeline
from utils.recommendation_engine import (
    get_ranked_recommendations,
    load_cold_start_posts,
)
from utils.metrics import (
    track_injection,
    track_timeline_post_counts,
    track_injection_processing_time,
    track_recommendation_generation,
    track_recommendation_processing_time,
    track_fallback,
)
from routes.proxy import (
    get_authenticated_user,
    get_user_instance,
    ALLOW_COLD_START_FOR_ANONYMOUS,
    should_exit_cold_start,
    should_reenter_cold_start,
    generate_user_alias,
)
from db.connection import get_db_connection, get_cursor, USE_IN_MEMORY_DB

# Setup logger
logger = logging.getLogger(__name__)
timeline_logger = logging.getLogger("timeline_injection")

# Create Blueprint
timeline_bp = Blueprint("timeline", __name__)

# Path to cold start posts JSON file
COLD_START_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "cold_start_formatted.json"
)


def load_json_file(filepath):
    """
    Load a JSON file and return its contents.

    Args:
        filepath: Path to the JSON file

    Returns:
        dict or list: Parsed JSON content

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file isn't valid JSON
    """
    try:
        # Debug the file path being loaded
        logger.debug(f"[DEBUG] Loading JSON file from: {filepath}")
        logger.debug(f"[DEBUG] File exists: {os.path.exists(filepath)}")
        logger.debug(f"[DEBUG] Working directory: {os.getcwd()}")

        with open(filepath, "r") as f:
            data = json.load(f)

        # Debug the loaded data
        if isinstance(data, list):
            logger.debug(f"[DEBUG] Loaded {len(data)} items from {filepath}")
        else:
            logger.debug(f"[DEBUG] Loaded data of type {type(data)} from {filepath}")

        return data
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        raise


def get_real_mastodon_posts_from_db(limit=20, languages: Optional[List[str]] = None):
    """
    Get real Mastodon posts from the database.
    
    This function loads the actual Mastodon posts that were seeded into the database
    from static/real_mastodon_posts.json, ensuring all users get real content
    instead of cold start posts.
    
    Returns:
        List of real Mastodon posts with enhanced interaction counts and user states
    """
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Get real Mastodon posts from the database
                language_clause = ""
                params = []
                if languages:
                    language_clause = "AND language IN ({})".format(
                        ",".join(["%s"] * len(languages))
                    )
                    params.extend(languages)
                
                params.append(limit)

                cur.execute(f"""
                    SELECT id, content, created_at, author_id, author_name, language,
                           favourites_count, reblogs_count, replies_count, url, source_instance
                    FROM posts 
                    WHERE is_real_mastodon_post = 1
                    {language_clause}
                    ORDER BY created_at DESC
                    LIMIT %s
                """, tuple(params))
                
                rows = cur.fetchall()
                
                posts = []
                for row in rows:
                    post = {
                        "id": str(row[0]),
                        "content": row[1],
                        "created_at": row[2],
                        "account": {
                            "id": row[3],
                            "username": row[4],
                            "display_name": row[4],
                            "url": f"https://{row[10] or 'mastodon.social'}/@{row[4]}",
                        },
                        "language": row[5] or "en",
                        "favourites_count": row[6] or 0,
                        "reblogs_count": row[7] or 0,
                        "replies_count": row[8] or 0,
                        "url": row[9],
                        "source_instance": row[10],
                        "is_real_mastodon_post": True,
                        "is_synthetic": False,
                        "injected": True,
                        "media_attachments": [],
                        "mentions": [],
                        "tags": [],
                        "emojis": [],
                    }
                    posts.append(post)
                
                logger.info(f"Loaded {len(posts)} real Mastodon posts from database")
                return posts
                
    except Exception as e:
        logger.error(f"Error loading real Mastodon posts from database: {e}")
        return []


def get_trending_cold_start_posts(limit: int = 20, languages: Optional[List[str]] = None) -> List[Dict]:
    """
    Get trending posts from crawled_posts table for cold start users.
    
    This creates a dynamic "trending page" experience by selecting posts based on:
    - Recent engagement (favorites, reblogs, replies)
    - Recency (posts from last 7 days preferred)
    - Diversity (mix of different instances and authors)
    
    Args:
        limit: Maximum number of posts to return
        languages: Optional list of language codes to filter by
        
    Returns:
        List of trending posts formatted for Mastodon compatibility
    """
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Calculate trending score based on engagement and recency
                # Score = (favorites * 1 + reblogs * 2 + replies * 1.5) * recency_factor
                # Recency factor: 1.0 for last 24h, 0.8 for 2-7 days, 0.5 for older
                
                language_clause = ""
                params = []
                if languages:
                    language_clause = "AND language IN ({})".format(
                        ",".join(["%s"] * len(languages))
                    )
                    params.extend(languages)
                
                params.append(limit * 3)  # Get more posts to ensure diversity
                
                if USE_IN_MEMORY_DB:
                    # SQLite version with different date syntax
                    cur.execute(f"""
                        SELECT 
                            post_id, content, author_username, author_acct, author_display_name,
                            author_avatar, created_at, favourites_count, reblogs_count, replies_count,
                            url, source_instance, language, author_id, tags, media_attachments,
                            mentions, emojis, visibility, card,
                            -- Calculate trending score
                            (
                                COALESCE(favourites_count, 0) * 1.0 + 
                                COALESCE(reblogs_count, 0) * 2.0 + 
                                COALESCE(replies_count, 0) * 1.5
                            ) * 
                            CASE 
                                WHEN created_at > datetime('now', '-1 day') THEN 1.0
                                WHEN created_at > datetime('now', '-7 days') THEN 0.8
                                ELSE 0.5
                            END as trending_score
                        FROM crawled_posts
                        WHERE created_at > datetime('now', '-30 days')  -- Only recent posts
                        AND content IS NOT NULL 
                        AND LENGTH(content) > 10  -- Ensure substantial content
                        {language_clause.replace('%s', '?')}
                        ORDER BY trending_score DESC, created_at DESC
                        LIMIT ?
                    """, tuple(params))
                else:
                    # PostgreSQL version
                    cur.execute(f"""
                        SELECT 
                            post_id, content, author_username, author_acct, author_display_name,
                            author_avatar, created_at, favourites_count, reblogs_count, replies_count,
                            url, source_instance, language, author_id, tags, media_attachments,
                            mentions, emojis, visibility, card,
                            -- Calculate trending score
                            (
                                COALESCE(favourites_count, 0) * 1.0 + 
                                COALESCE(reblogs_count, 0) * 2.0 + 
                                COALESCE(replies_count, 0) * 1.5
                            ) * 
                            CASE 
                                WHEN created_at > NOW() - INTERVAL '1 day' THEN 1.0
                                WHEN created_at > NOW() - INTERVAL '7 days' THEN 0.8
                                ELSE 0.5
                            END as trending_score
                        FROM crawled_posts
                        WHERE created_at > NOW() - INTERVAL '30 days'  -- Only recent posts
                        AND content IS NOT NULL 
                        AND LENGTH(content) > 10  -- Ensure substantial content
                        {language_clause}
                        ORDER BY trending_score DESC, created_at DESC
                        LIMIT %s
                    """, tuple(params))
                
                rows = cur.fetchall()
                
                if not rows:
                    logger.warning("No trending posts found in crawled_posts, falling back to static cold start")
                    return load_cold_start_posts(languages=languages)[:limit]
                
                # Process and diversify the results
                trending_posts = []
                seen_authors = set()
                seen_instances = set()
                
                for row in rows:
                    if len(trending_posts) >= limit:
                        break
                        
                    (post_id, content, author_username, author_acct, author_display_name,
                     author_avatar, created_at, favourites_count, reblogs_count, replies_count,
                     url, source_instance, language, author_id, tags_json, media_json,
                     mentions_json, emojis_json, visibility, card_json, trending_score) = row
                    
                    # Promote diversity - limit posts per author/instance
                    if author_username in seen_authors and len(seen_authors) < limit // 2:
                        continue
                    if source_instance in seen_instances and len(seen_instances) < limit // 3:
                        continue
                        
                    seen_authors.add(author_username)
                    seen_instances.add(source_instance)
                    
                    # Parse JSON fields safely
                    try:
                        if isinstance(tags_json, str):
                            tags = json.loads(tags_json) if tags_json else []
                        else:
                            tags = tags_json if tags_json else []
                    except:
                        tags = []
                        
                    try:
                        if isinstance(media_json, str):
                            media_attachments = json.loads(media_json) if media_json else []
                        else:
                            media_attachments = media_json if media_json else []
                    except:
                        media_attachments = []
                        
                    try:
                        if isinstance(mentions_json, str):
                            mentions = json.loads(mentions_json) if mentions_json else []
                        else:
                            mentions = mentions_json if mentions_json else []
                    except:
                        mentions = []
                        
                    try:
                        if isinstance(emojis_json, str):
                            emojis = json.loads(emojis_json) if emojis_json else []
                        else:
                            emojis = emojis_json if emojis_json else []
                    except:
                        emojis = []
                        
                    try:
                        if isinstance(card_json, str):
                            card = json.loads(card_json) if card_json else None
                        else:
                            card = card_json if card_json else None
                    except:
                        card = None
                    
                    # Format as Mastodon-compatible post
                    post = {
                        "id": str(post_id),
                        "created_at": created_at.isoformat() if created_at else datetime.now().isoformat(),
                        "content": content,
                        "account": {
                            "id": author_id or f"user_{author_username}",
                            "username": author_username,
                            "acct": author_acct or f"{author_username}@{source_instance}",
                            "display_name": author_display_name or author_username,
                            "avatar": author_avatar or "https://via.placeholder.com/48x48",
                            "url": f"https://{source_instance}/@{author_username}",
                        },
                        "favourites_count": favourites_count or 0,
                        "reblogs_count": reblogs_count or 0,
                        "replies_count": replies_count or 0,
                        "language": language or "en",
                        "url": url or f"https://{source_instance}/@{author_username}/{post_id}",
                        "tags": tags,
                        "media_attachments": media_attachments,
                        "mentions": mentions,
                        "emojis": emojis,
                        "card": card,
                        "visibility": visibility or "public",
                        "favourited": False,
                        "reblogged": False,
                        "bookmarked": False,
                        # Metadata for tracking
                        "is_real_mastodon_post": True,
                        "is_synthetic": False,
                        "is_cold_start": True,
                        "is_trending": True,
                        "injected": True,
                        "source_instance": source_instance,
                        "trending_score": float(trending_score) if trending_score else 0.0,
                        "injection_metadata": {
                            "source": "trending_cold_start",
                            "strategy": "engagement_based",
                            "explanation": f"Trending post from {source_instance} with {favourites_count + reblogs_count + replies_count} interactions"
                        }
                    }
                    
                    trending_posts.append(post)
                
                logger.info(f"Generated {len(trending_posts)} trending cold start posts from {len(seen_instances)} instances")
                return trending_posts
                
    except Exception as e:
        logger.error(f"Error getting trending cold start posts: {e}")
        # Fall back to static cold start posts
        return load_cold_start_posts(languages=languages)[:limit]


def load_injected_posts_for_user(user_id, languages: Optional[List[str]] = None):
    """
    Load posts to be injected for a user based on their status.
    """
    from utils.user_signals import is_new_user  # DEFERRED IMPORT to break circular dependency

    start_time = time.time()

    # For anonymous users, always use trending posts
    if not user_id or user_id == "anonymous":
        try:
            posts = get_trending_cold_start_posts(limit=20, languages=languages)
            logger.info(f"Loaded {len(posts)} trending posts for anonymous user")

            # Track metrics
            track_recommendation_generation("trending_cold_start", "anonymous", len(posts))

            return posts, "trending_cold_start"
        except Exception as e:
            logger.error(f"Error loading trending cold start posts: {e}")
            track_fallback("error_loading_trending_cold_start")
            return [], "cold_start"

    # For synthetic or validator users, use trending posts
    if user_id.startswith("corgi_validator_") or user_id.startswith("test_"):
        try:
            posts = get_trending_cold_start_posts(limit=20, languages=languages)
            logger.info(
                f"Loaded {len(posts)} trending posts for synthetic user {user_id}"
            )

            # Track metrics
            track_recommendation_generation("trending_cold_start", "synthetic", len(posts))

            return posts, "trending_cold_start"
        except Exception as e:
            logger.error(f"Error loading trending cold start posts for synthetic user: {e}")
            track_fallback("error_loading_trending_cold_start")
            return [], "cold_start"

    # Check if user is new or has low activity - use trending posts
    # if is_new_user(user_id):
    #     try:
    #         posts = get_trending_cold_start_posts(limit=20, languages=languages)
    #         logger.info(f"User {user_id} is new, using trending posts")
    #
    #         # Track metrics
    #         track_recommendation_generation("trending_cold_start", "new_user", len(posts))
    #         track_fallback("new_user")
    #
    #         return posts, "trending_cold_start"
    #     except Exception as e:
    #         logger.error(f"Error loading trending cold start posts for new user: {e}")
    #         track_fallback("error_loading_trending_cold_start")
    #         return [], "cold_start"

    # For returning users with sufficient activity, get personalized recommendations
    try:
        # Get recommended posts from the recommendation engine
        recommendation_start_time = time.time()
        posts = get_ranked_recommendations(user_id, limit=20, languages=languages)
        recommendation_time = time.time() - recommendation_start_time

        # Track recommendation processing time
        track_recommendation_processing_time(
            "recommendation_engine", recommendation_time
        )

        if not posts:
            # Fall back to trending posts if no recommendations
            logger.warning(
                f"No recommended posts for user {user_id}, falling back to trending posts"
            )
            posts = get_trending_cold_start_posts(limit=20, languages=languages)

            # Track metrics
            track_fallback("no_recommendations")
            track_recommendation_generation(
                "trending_cold_start", "returning_user_fallback", len(posts)
            )

            return posts, "trending_cold_start_fallback"

        # Track successful personalized recommendations
        track_recommendation_generation(
            "recommendation_engine", "returning_user", len(posts)
        )

        logger.info(
            f"Loaded {len(posts)} personalized recommendations for user {user_id}"
        )
        return posts, "personalized"
    except Exception as e:
        logger.error(f"Error loading personalized posts: {e}")
        # Fall back to trending posts on error
        try:
            posts = get_trending_cold_start_posts(limit=20, languages=languages)

            # Track metrics
            track_fallback("recommendation_error")
            track_recommendation_generation(
                "trending_cold_start", "returning_user_error_fallback", len(posts)
            )

            return posts, "trending_cold_start_fallback"
        except:
            track_fallback("total_failure")
            return [], "error"


def get_injection_strategy(user_id, is_anonymous, strategy_name=None):
    """
    Determine the appropriate injection strategy based on user state.

    Args:
        user_id: User identifier
        is_anonymous: Whether this is an anonymous session
        strategy_name: Override strategy name if provided

    Returns:
        dict: Strategy configuration for inject_into_timeline
    """
    # Debug the parameters to help diagnose issues
    logger.debug(
        f"[DEBUG] Getting injection strategy for user_id={user_id}, is_anonymous={is_anonymous}, strategy_name={strategy_name}"
    )
    # Use requested strategy if provided
    if strategy_name:
        if strategy_name == "uniform":
            return {"type": "uniform", "max_injections": 5, "shuffle_injected": True}
        elif strategy_name == "after_n":
            return {
                "type": "after_n",
                "n": 3,
                "max_injections": 5,
                "shuffle_injected": True,
            }
        elif strategy_name == "first_only":
            return {"type": "first_only", "max_injections": 3, "shuffle_injected": True}
        elif strategy_name == "tag_match":
            return {"type": "tag_match", "max_injections": 5, "shuffle_injected": True}

    # For anonymous users, use uniform strategy
    if is_anonymous:
        return {
            "type": "uniform",
            "max_injections": 5,
            "shuffle_injected": True,
            # Removed inject_only_if_gap_minutes to ensure injection happens
        }

    # For new users (could be determined by account age or activity)
    # use first_only strategy to front-load recommendations
    if user_id.startswith("new_") or user_id.startswith("corgi_validator_"):
        return {"type": "first_only", "max_injections": 3, "shuffle_injected": True}

    # For regular users, use tag matching for more relevant injections
    return {
        "type": "tag_match",
        "max_injections": 5,
        "shuffle_injected": True,
        "inject_only_if_gap_minutes": 10,
    }


@timeline_bp.route("/api/v1/timelines/home", methods=["GET"])
@log_route
def get_timeline():
    """
    Get a user's home timeline with injectable posts blended in.

    This enhanced timeline endpoint supports both real Mastodon posts
    and injected recommendations based on configurable strategies.

    Query parameters:
        limit (int, optional): Maximum posts to return (default: 20)
        strategy (str, optional): Injection strategy to use
            (uniform, after_n, first_only, tag_match)
        inject (bool, optional): Whether to inject posts (default: true)

    Returns:
        Flask.Response: JSON response containing:
            - timeline: List of posts in chronological order
            - metadata: Information about the injection if performed
    """
    request_id = hash(f"{time.time()}_{request.remote_addr}") % 10000000

    # Get request parameters
    limit = request.args.get("limit", default=20, type=int)
    strategy_name = request.args.get("strategy", default=None)
    inject_posts = request.args.get("inject", "true").lower() == "true"
    languages_str = request.args.get("languages")
    languages = languages_str.split(",") if languages_str else []

    # Get user ID either from query param or auth header
    user_id = get_authenticated_user(request)
    is_anonymous = not user_id

    # Log the request
    logger.info(
        f"REQ-{request_id} | GET /api/v1/timelines/home | "
        f"User: {user_id or 'anonymous'} | "
        f"Client: {request.remote_addr} | "
        f"Inject: {inject_posts} | "
        f"Strategy: {strategy_name or 'default'}"
    )

    # Handle anonymous users
    if is_anonymous:
        # Check if anonymous access is allowed
        if not ALLOW_COLD_START_FOR_ANONYMOUS and not user_id:
            logger.info(
                f"AUTH-{request_id} | Anonymous access not allowed, returning empty timeline"
            )
            return jsonify(
                {"timeline": [], "metadata": {"error": "Authentication required"}}
            )

        # Use "anonymous" as user_id for tracking
        user_id = "anonymous"

    # Get the real timeline posts
    real_posts = []

    # For real users, attempt to proxy to their instance
    if (
        not is_anonymous
        and not user_id.startswith("corgi_validator_")
        and not user_id.startswith("test_")
    ):
        instance_url = get_user_instance(request)

        try:
            # Build the target URL for the Mastodon instance
            target_url = urljoin(instance_url, f"/api/v1/timelines/home")

            # Extract request components
            headers = {
                key: value
                for key, value in request.headers.items()
                if key.lower() not in ["host", "content-length"]
            }
            params = request.args.to_dict()

            # Remove our custom parameters
            if "strategy" in params:
                del params["strategy"]
            if "inject" in params:
                del params["inject"]

            # Make the request to the Mastodon instance
            upstream_start_time = time.time()
            proxied_response = requests.request(
                method="GET", url=target_url, headers=headers, params=params, timeout=10
            )
            upstream_time = time.time() - upstream_start_time

            # Log upstream response metrics
            logger.info(
                f"UP-{request_id} | Upstream timeline response | "
                f"Status: {proxied_response.status_code} | "
                f"Time: {upstream_time:.3f}s"
            )

            if proxied_response.status_code == 200:
                # Extract the response content
                real_posts = proxied_response.json()
                logger.info(
                    f"TIMELINE-{request_id} | Retrieved {len(real_posts)} real posts"
                )
            else:
                # For errors, log but continue with empty real posts
                logger.warning(
                    f"ERR-{request_id} | Error {proxied_response.status_code} from upstream, "
                    f"continuing with empty real timeline"
                )
        except Exception as e:
            logger.error(f"ERROR-{request_id} | Timeline proxy failed: {e}")

    # For synthetic/validator users, create dummy timeline
    elif user_id.startswith("corgi_validator_") or user_id.startswith("test_"):
        logger.info(f"SYNTH-{request_id} | Synthetic user detected: {user_id}")

        # Create some synthetic posts
        synthetic_count = min(5, limit)
        for i in range(synthetic_count):
            post_id = f"corgi_synthetic_post_{user_id}_{i}"
            real_posts.append(
                {
                    "id": post_id,
                    "content": f"Synthetic post {i+1} for user {user_id}",
                    "created_at": datetime.now().isoformat(),
                    "account": {
                        "id": f"synth_author_{i}",
                        "username": f"synthetic_user_{i}",
                        "display_name": f"Synthetic User {i}",
                        "url": f"https://example.com/@synthetic_user_{i}",
                    },
                    "language": "en",
                    "favourites_count": 0,
                    "reblogs_count": 0,
                    "replies_count": 0,
                    "is_real_mastodon_post": False,
                    "is_synthetic": True,
                }
            )

        logger.info(
            f"TIMELINE-{request_id} | Created {len(real_posts)} synthetic timeline posts"
        )

    # If we should inject posts
    if inject_posts:
        # Get posts to inject
        injectable_posts, source_type = load_injected_posts_for_user(user_id, languages=languages)

        if injectable_posts:
            # Get appropriate injection strategy
            strategy = get_injection_strategy(user_id, is_anonymous, strategy_name)

            # Log injection attempt
            logger.info(
                f"INJECT-{request_id} | Injecting posts | "
                f"User: {user_id} | "
                f"Strategy: {strategy['type']} | "
                f"Source: {source_type} | "
                f"Available posts: {len(injectable_posts)}"
            )

            # Add debug logs before injection
            logger.debug(
                f"[DEBUG] Before injection: real_posts={len(real_posts)}, injectable_posts={len(injectable_posts)}"
            )
            logger.debug(f"[DEBUG] Strategy: {strategy}")

            # If real_posts is empty, we can still inject posts (important for cold start)
            if not real_posts and injectable_posts:
                logger.debug(
                    "[DEBUG] No real posts but have injectable posts - will create standalone timeline"
                )
                # Create a stub real post just to trigger injection
                # This post will be removed later if not needed
                real_posts = [
                    {
                        "id": "stub_post",
                        "content": "Stub post for injection",
                        "created_at": datetime.now().isoformat(),
                        "account": {
                            "id": "stub_account",
                            "username": "stub",
                            "display_name": "Stub Account",
                            "url": "https://example.com/@stub",
                        },
                        "stub_for_injection": True,
                    }
                ]

            # Inject posts using timeline injector
            logger.debug(
                f"[DEBUG] Calling inject_into_timeline with {len(real_posts)} real posts, {len(injectable_posts)} injectable posts, and strategy type {strategy.get('type', 'unknown')}"
            )

            try:
                start_time = time.time()
                logger.info(
                    f"[INFO] Starting inject_into_timeline with {len(real_posts)} real posts and {len(injectable_posts)} injectable posts"
                )
                merged_timeline = inject_into_timeline(
                    real_posts, injectable_posts, strategy
                )
                inject_time = time.time() - start_time

                # Track injection processing time
                track_injection_processing_time(strategy["type"], inject_time)

                logger.debug(
                    f"[DEBUG] inject_into_timeline returned {len(merged_timeline)} total posts"
                )
            except Exception as e:
                import traceback

                error_trace = traceback.format_exc()
                logger.error(f"[ERROR] Timeline injection failed: {e}")
                logger.error(f"[ERROR] Traceback: {error_trace}")
                # If injection fails, use a fallback approach
                merged_timeline = []
                inject_time = time.time() - start_time
                track_fallback("injection_error")

            # Remove stub post if it was added
            merged_timeline = [
                post
                for post in merged_timeline
                if not post.get("stub_for_injection", False)
            ]

            # If merged_timeline is empty but we had injectable posts, something went wrong
            # Let's manually create a timeline with a subset of injectable posts
            if not merged_timeline and injectable_posts:
                logger.warning(
                    f"[DEBUG] Timeline injection produced empty result despite having {len(injectable_posts)} injectable posts. Falling back to direct inclusion."
                )
                # Create a new list for the timeline
                merged_timeline = []
                # Directly add injectable posts (up to max_injections)
                max_posts = min(
                    strategy.get("max_injections", 5), len(injectable_posts)
                )
                for i in range(max_posts):
                    if i < len(injectable_posts):  # Make sure we don't go out of bounds
                        from copy import deepcopy

                        post = deepcopy(injectable_posts[i])
                        post["injected"] = True
                        merged_timeline.append(post)
                logger.debug(
                    f"[DEBUG] Manually added {len(merged_timeline)} posts to timeline as fallback"
                )

            # Ensure merged_timeline is a list before continuing
            if not isinstance(merged_timeline, list):
                logger.error(
                    f"Expected merged_timeline to be a list but got {type(merged_timeline)}. Creating empty list instead."
                )
                merged_timeline = []

            # Count injected posts - notice we're checking for injected=True, not defaulting to True
            try:
                injected_count = sum(
                    1 for post in merged_timeline if post.get("injected") is True
                )
                real_count = len(merged_timeline) - injected_count

                # Debug the result
                logger.debug(
                    f"[DEBUG] After injection: merged_timeline={len(merged_timeline)}, injected_count={injected_count}"
                )

                # Log injection results
                timeline_logger.info(
                    f"INJECTION-{request_id} | "
                    f"User: {generate_user_alias(user_id)} | "
                    f"Strategy: {strategy['type']} | "
                    f"Injected: {injected_count}/{len(injectable_posts)} | "
                    f"Total posts: {len(merged_timeline)} | "
                    f"Processing time: {inject_time:.3f}s"
                )

                # Track metrics - wrap each call in try/except to ensure one failure doesn't prevent others
                try:
                    track_injection(strategy["type"], source_type, injected_count)
                except Exception as e:
                    logger.error(f"Error tracking injection metrics: {e}")

                try:
                    track_timeline_post_counts(real_count, injected_count)
                except Exception as e:
                    logger.error(f"Error tracking timeline post counts: {e}")

                # Add extra metrics tracking
                # This extra explicit tracking ensures metrics are incremented regardless of any side effects
                try:
                    from utils.metrics import (
                        INJECTED_POSTS_TOTAL,
                        TIMELINE_POST_COUNT,
                        INJECTION_RATIO,
                    )

                    # Explicitly increment the metrics
                    INJECTED_POSTS_TOTAL.labels(
                        strategy=strategy["type"], source=source_type
                    ).inc(injected_count)
                    TIMELINE_POST_COUNT.labels(post_type="real").set(real_count)
                    TIMELINE_POST_COUNT.labels(post_type="injected").set(injected_count)

                    if real_count + injected_count > 0:
                        ratio = injected_count / (real_count + injected_count)
                        INJECTION_RATIO.observe(ratio)
                except Exception as e:
                    logger.error(f"Error setting explicit metrics: {e}")
            except Exception as e:
                logger.error(f"Error processing timeline metrics: {e}")

            # Apply ELK compatibility to all posts in merged timeline
            for post in merged_timeline:
                try:
                    ensure_elk_compatibility(post, user_id)
                except Exception as e:
                    logger.warning(f"Error applying ELK compatibility to post {post.get('id', 'unknown')}: {e}")

            # Return direct array for ELK compatibility (not wrapped)
            return jsonify(merged_timeline)
        else:
            # Log that we couldn't inject posts
            logger.warning(
                f"NOINJECT-{request_id} | No injectable posts available | "
                f"User: {user_id} | "
                f"Source type: {source_type}"
            )

    # If we're here, we're not injecting or had no posts to inject
    # Apply ELK compatibility to all real posts
    for post in real_posts:
        try:
            ensure_elk_compatibility(post, user_id)
        except Exception as e:
            logger.warning(f"Error applying ELK compatibility to post {post.get('id', 'unknown')}: {e}")

    # Return direct array for ELK compatibility (not wrapped)
    return jsonify(real_posts)


@timeline_bp.route("/api/v1/timelines/local", methods=["GET"])
@log_route
def get_local_timeline():
    """
    Get the local timeline (posts from the local instance).
    
    This is a simplified implementation that returns empty for now,
    as this service doesn't have local instance posts.
    
    Query parameters:
        limit (int, optional): Maximum posts to return (default: 20)
        max_id (str, optional): Return posts older than this ID
        since_id (str, optional): Return posts newer than this ID
        
    Returns:
        List[dict]: Empty array for now (could be enhanced to show local content)
    """
    request_id = hash(f"{time.time()}_{request.remote_addr}") % 10000000
    limit = request.args.get("limit", default=20, type=int)
    
    logger.info(
        f"REQ-{request_id} | GET /api/v1/timelines/local | "
        f"Client: {request.remote_addr} | "
        f"Limit: {limit}"
    )
    
    # Return empty timeline in direct array format for ELK compatibility
    return jsonify([])


@timeline_bp.route("/api/v1/timelines/public", methods=["GET"])
@log_route
def get_public_timeline():
    """
    Get the public timeline (posts from the known fediverse).
    
    This is a simplified implementation that returns empty for now,
    as this service doesn't federate with other instances.
    
    Query parameters:
        limit (int, optional): Maximum posts to return (default: 20)
        max_id (str, optional): Return posts older than this ID
        since_id (str, optional): Return posts newer than this ID
        local (bool, optional): Show only local posts (default: false)
        remote (bool, optional): Show only remote posts (default: false)
        
    Returns:
        List[dict]: Empty array for now (could be enhanced to show federated content)
    """
    request_id = hash(f"{time.time()}_{request.remote_addr}") % 10000000
    limit = request.args.get("limit", default=20, type=int)
    local_only = request.args.get("local", "false").lower() == "true"
    remote_only = request.args.get("remote", "false").lower() == "true"
    
    logger.info(
        f"REQ-{request_id} | GET /api/v1/timelines/public | "
        f"Client: {request.remote_addr} | "
        f"Limit: {limit} | "
        f"Local: {local_only} | "
        f"Remote: {remote_only}"
    )
    
    # Return empty timeline in direct array format for ELK compatibility
    return jsonify([])


def fetch_real_interaction_counts(post_url):
    """
    Fetch real-time interaction counts from Mastodon API.
    
    TEMPORARILY DISABLED: External API calls were causing hangs.
    Returns randomized static counts for demo purposes.
    
    Args:
        post_url: Full URL to the Mastodon post (e.g., https://mastodon.social/@user/123)
    
    Returns:
        dict: Static interaction counts for now
    """
    # TEMPORARILY DISABLED - return static counts to prevent API hangs
    import random
    random.seed(hash(post_url) % 1000)  # Consistent random values per post
    
    return {
        'favourites_count': random.randint(1, 15),
        'reblogs_count': random.randint(0, 8),
        'replies_count': random.randint(0, 5),
        'favouritesCount': random.randint(1, 15),  # camelCase for ELK
        'reblogsCount': random.randint(0, 8),
        'repliesCount': random.randint(0, 5),
    }


def ensure_elk_compatibility(post_data, user_id=None):
    """Ensure post has all fields required by ELK for interaction support"""
    
    # Get user's interaction state for this post if user_id is provided
    user_interactions = {}
    if user_id:
        try:
            # Generate user alias for privacy
            user_alias = generate_user_alias(user_id)
            
            with get_db_connection() as conn:
                with get_cursor(conn) as cur:
                    # Get user interactions for this specific post with timestamps
                    if USE_IN_MEMORY_DB:
                        # For SQLite in-memory DB, use action_type consistently
                        cur.execute("""
                            SELECT action_type, created_at
                            FROM interactions 
                            WHERE user_id = ? AND post_id = ?
                            ORDER BY created_at DESC
                        """, (user_alias, post_data.get('id')))
                        interaction_rows = cur.fetchall()
                        logger.debug(f"User interaction lookup for user={user_alias}, post={post_data.get('id')}: found {len(interaction_rows)} interactions")
                    else:
                        # PostgreSQL version uses user_alias and action_type
                        cur.execute("""
                            SELECT action_type, created_at
                            FROM interactions 
                            WHERE user_alias = %s AND post_id = %s
                            ORDER BY created_at DESC
                        """, (user_alias, post_data.get('id')))
                        interaction_rows = cur.fetchall()
                    
                    # Find the most recent action for each interaction type
                    latest_favorite = None
                    latest_reblog = None
                    latest_bookmark = None
                    
                    for action_type, created_at in interaction_rows:
                        if action_type in ['favorite', 'unfavorite'] and latest_favorite is None:
                            latest_favorite = action_type
                        elif action_type in ['reblog', 'unreblog'] and latest_reblog is None:
                            latest_reblog = action_type
                        elif action_type in ['bookmark', 'unbookmark'] and latest_bookmark is None:
                            latest_bookmark = action_type
                    
                    # Set interaction state based on most recent actions
                    user_interactions = {
                        'favourited': latest_favorite == 'favorite',
                        'reblogged': latest_reblog == 'reblog',
                        'bookmarked': latest_bookmark == 'bookmark',
                    }
                    logger.debug(f"User interaction state for post {post_data.get('id')}: {user_interactions}")
                    
        except Exception as e:
            logger.warning(f"Could not fetch user interactions for post {post_data.get('id')}: {e}")
            user_interactions = {}
    
    # Fetch real-time interaction counts if this is a real Mastodon post
    post_url = post_data.get("url")
    real_counts = None
    if post_url and post_data.get("is_real_mastodon_post"):
        real_counts = fetch_real_interaction_counts(post_url)
        if real_counts:
            logger.debug(f"Updated interaction counts for {post_data.get('id')}: {real_counts}")
    
    # Update interaction counts with real-time data if available
    if real_counts:
        post_data.update(real_counts)
    
    # Interaction states - use user's actual interactions or defaults
    post_data['favourited'] = user_interactions.get('favourited', post_data.get('favourited', False))
    post_data['reblogged'] = user_interactions.get('reblogged', post_data.get('reblogged', False))  
    post_data['bookmarked'] = user_interactions.get('bookmarked', post_data.get('bookmarked', False))
    post_data['muted'] = post_data.get('muted', False)
    post_data['pinned'] = post_data.get('pinned', False)
    
    # Interaction counts (ensure they exist)
    if 'favourites_count' not in post_data:
        post_data['favourites_count'] = 0
    if 'reblogs_count' not in post_data:
        post_data['reblogs_count'] = 0
    if 'replies_count' not in post_data:
        post_data['replies_count'] = 0
    
    # Also add camelCase versions for ELK compatibility
    if 'favouritesCount' not in post_data:
        post_data['favouritesCount'] = post_data.get('favourites_count', 0)
    if 'reblogsCount' not in post_data:
        post_data['reblogsCount'] = post_data.get('reblogs_count', 0)
    if 'repliesCount' not in post_data:
        post_data['repliesCount'] = post_data.get('replies_count', 0)
    
    # -----------------------------------------
    # Bridge Corgi-specific metadata → frontend
    # -----------------------------------------
    if 'recommendation_reason' not in post_data:
        if post_data.get('_corgi_recommendation_reason'):
            post_data['recommendation_reason'] = post_data['_corgi_recommendation_reason']
        elif post_data.get('injection_metadata', {}).get('explanation'):
            post_data['recommendation_reason'] = post_data['injection_metadata']['explanation']

    # Surface score
    if 'recommendation_score' not in post_data:
        if post_data.get('_corgi_score') is not None:
            post_data['recommendation_score'] = post_data['_corgi_score']
        elif post_data.get('injection_metadata', {}).get('score') is not None:
            post_data['recommendation_score'] = post_data['injection_metadata']['score']
    
    if post_data.get('recommendation_score') is not None and 'recommendation_percent' not in post_data:
        try:
            post_data['recommendation_percent'] = round(float(post_data['recommendation_score']) * 100)
        except (ValueError, TypeError):
            pass
    
    # Explicit recommendation flag so UI/injection can detect
    if 'is_recommendation' not in post_data:
        # Consider any post with recommendation_reason or _corgi_recommendation flag as recommendation
        if post_data.get('_corgi_recommendation') or post_data.get('recommendation_reason'):
            post_data['is_recommendation'] = True

    # Duplicate reason into _corgi_reason for native ELK setting
    if 'recommendation_reason' in post_data and '_corgi_reason' not in post_data:
        post_data['_corgi_reason'] = post_data['recommendation_reason']
    
    return post_data
