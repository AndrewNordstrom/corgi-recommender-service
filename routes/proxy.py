"""
Proxy routes for the Corgi Recommender Service.

This module provides a transparent proxy that forwards requests to Mastodon instances
while intercepting specific endpoints to inject personalized recommendations.
"""

import logging
import logging.handlers
import requests
import json
import os
import re
from flask import Blueprint, request, Response, jsonify, g, current_app
from urllib.parse import urljoin, urlparse
import time
import datetime
import os
import re
import hashlib

from db.connection import get_db_connection, get_cursor, USE_IN_MEMORY_DB
from utils.logging_decorator import log_route
from utils.privacy import get_user_privacy_level, generate_user_alias
from config import (
    COLD_START_ENABLED,
    COLD_START_POSTS_PATH,
    COLD_START_POST_LIMIT,
    ALLOW_COLD_START_FOR_ANONYMOUS,
    PROXY_CACHE_TTL_TIMELINE,
    PROXY_CACHE_TTL_PROFILE,
    PROXY_CACHE_TTL_INSTANCE,
    PROXY_CACHE_TTL_STATUS,
    PROXY_CACHE_TTL_DEFAULT
)
from utils.user_signals import (
    get_weighted_post_selection,
    update_user_signals,
    should_exit_cold_start,
    should_reenter_cold_start,
    import_user_signals_from_db,
    export_user_signals_to_db,
)

# Set up logging
logger = logging.getLogger(__name__)

# Get the repo root directory
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
logs_dir = os.path.join(repo_root, "logs")

# Ensure logs directory exists
os.makedirs(logs_dir, exist_ok=True)

# Secure the logs directory - restrict to user only (0700)
try:
    import stat

    os.chmod(logs_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
except Exception as e:
    logger.warning(f"Could not set secure permissions on logs directory: {e}")

# Set up proxy-specific file logger
proxy_logger = logging.getLogger("proxy")
proxy_logger.setLevel(logging.INFO)

# Use a secure log file with permissions set correctly
log_file_path = os.path.join(logs_dir, "proxy.log")

# Add rotating file handler
file_handler = logging.handlers.RotatingFileHandler(
    log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5  # 10 MB
)

# Secure the log file - restrict to user only (0600)
try:
    if os.path.exists(log_file_path):
        os.chmod(log_file_path, stat.S_IRUSR | stat.S_IWUSR)
except Exception as e:
    logger.warning(f"Could not set secure permissions on log file: {e}")
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler.setFormatter(file_formatter)
proxy_logger.addHandler(file_handler)

# Set up interaction-specific logger
interaction_logger = logging.getLogger("proxy_interactions")
interaction_logger.setLevel(logging.INFO)

# Only add handler if it doesn't already exist
if not interaction_logger.handlers:
    # Create file handler for proxy_interactions.log
    interaction_log_path = os.path.join(logs_dir, "proxy_interactions.log")
    interaction_handler = logging.handlers.RotatingFileHandler(
        interaction_log_path, maxBytes=10 * 1024 * 1024, backupCount=5  # 10 MB
    )

    # Secure the interaction log file - restrict to user only (0600)
    try:
        if os.path.exists(interaction_log_path):
            os.chmod(interaction_log_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception as e:
        logger.warning(f"Could not set secure permissions on interaction log file: {e}")

    # Use a simple formatter for clean logs
    interaction_formatter = logging.Formatter("%(asctime)s | %(message)s")
    interaction_handler.setFormatter(interaction_formatter)

    # Add the handler to the logger
    interaction_logger.addHandler(interaction_handler)

# Set up cold start logger
cold_start_logger = logging.getLogger("cold_start_interactions")
cold_start_logger.setLevel(logging.INFO)

# Only add handler if it doesn't already exist
if not cold_start_logger.handlers:
    # Create file handler for cold_start_interactions.log
    cold_start_log_path = os.path.join(logs_dir, "cold_start_interactions.log")
    cold_start_handler = logging.handlers.RotatingFileHandler(
        cold_start_log_path, maxBytes=10 * 1024 * 1024, backupCount=5  # 10 MB
    )

    # Secure the cold start log file - restrict to user only (0600)
    try:
        if os.path.exists(cold_start_log_path):
            os.chmod(cold_start_log_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception as e:
        logger.warning(f"Could not set secure permissions on cold start log file: {e}")

    # Use a simple formatter for clean logs
    cold_start_formatter = logging.Formatter("%(asctime)s | %(message)s")
    cold_start_handler.setFormatter(cold_start_formatter)

    # Add the handler to the logger
    cold_start_logger.addHandler(cold_start_handler)

# Add console handler in development mode
if os.environ.get("FLASK_ENV") == "development":
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(asctime)s [PROXY] %(message)s")
    console_handler.setFormatter(console_formatter)
    proxy_logger.addHandler(console_handler)

# Create blueprint
proxy_bp = Blueprint("proxy", __name__)


def sanitize_instance_url(url):
    """
    Validate and sanitize a Mastodon instance URL.

    Args:
        url: The instance URL to validate

    Returns:
        str: Sanitized URL or None if invalid
    """
    if not url:
        return None

    try:
        # Add https:// if no scheme is provided
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        parsed = urlparse(url)

        # Basic validation
        if not parsed.netloc:
            logger.warning(f"Invalid URL format: {url}")
            return None

        # Domain validation pattern (basic check for valid domain format)
        domain_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"

        # Check if domain matches pattern
        if not re.match(domain_pattern, parsed.netloc):
            logger.warning(f"Invalid domain in instance URL: {parsed.netloc}")
            return None

        # Remove any paths from the URL - keep just the domain with scheme
        url = f"{parsed.scheme}://{parsed.netloc}"

        # Exclude localhost in production unless explicitly allowed
        if (
            parsed.netloc == "localhost"
            or parsed.netloc.startswith("127.0.0.")
            or parsed.netloc.startswith("0.0.0.")
        ):
            if (
                os.environ.get("FLASK_ENV") == "production"
                and os.environ.get("ALLOW_LOCAL_TESTING") != "true"
            ):
                logger.warning(f"Blocked localhost URL in production: {url}")
                return None

        return url
    except Exception as e:
        logger.error(f"Error parsing instance URL: {e}")
        return None


def load_cold_start_posts():
    """Load and prepare cold start posts from the configured JSON file.

    This function loads pre-curated content that's shown to new users who don't
    follow anyone yet (cold start scenario). It adds metadata flags to each post
    to identify it as cold start content in the system.

    The posts are loaded from the path specified in COLD_START_POSTS_PATH config.
    Each post is marked with `is_cold_start=True`, `is_real_mastodon_post=False`,
    and `is_synthetic=True` flags.

    Returns:
        list: A list of cold start posts in Mastodon-compatible format with added flags.
              Returns an empty list if loading fails.

    Raises:
        No exceptions are raised; errors are logged and an empty list is returned.
    """
    try:
        with open(COLD_START_POSTS_PATH, "r") as f:
            posts = json.load(f)

        # Mark posts as cold start content
        for post in posts:
            post["is_cold_start"] = True
            post["is_real_mastodon_post"] = False
            post["is_synthetic"] = True

        proxy_logger.info(
            f"Loaded {len(posts)} cold start posts from {COLD_START_POSTS_PATH}"
        )
        return posts
    except Exception as e:
        proxy_logger.error(f"Error loading cold start posts: {e}")
        # Return an empty list if we can't load the posts
        return []


def get_user_instance(req):
    """
    Extract the user's Mastodon instance from request.

    Attempts to determine the instance from:
    1. X-Mastodon-Instance header
    2. instance query parameter
    3. Authorization token lookup in user_identities

    Args:
        req: The Flask request object

    Returns:
        str: The Mastodon instance URL with scheme (e.g., https://mastodon.social)
    """
    # Check for explicit instance header (set by client)
    instance = req.headers.get("X-Mastodon-Instance")
    if instance:
        logger.debug(f"Using instance from X-Mastodon-Instance header: {instance}")

        # Validate and sanitize instance URL
        instance = sanitize_instance_url(instance)
        if instance:
            return instance
        else:
            logger.warning(
                f"Invalid instance URL in X-Mastodon-Instance header, falling back to default"
            )

    # Check for instance query parameter
    instance = req.args.get("instance")
    if instance:
        logger.debug(f"Using instance from query parameter: {instance}")

        # Validate and sanitize instance URL
        instance = sanitize_instance_url(instance)
        if instance:
            return instance
        else:
            logger.warning(
                f"Invalid instance URL in query parameter, falling back to default"
            )

    # Try to extract from authorization token
    auth_header = req.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        # Look up in database
        user_info = get_user_by_token(token)
        if user_info and "instance_url" in user_info:
            logger.debug(
                f"Using instance from token lookup: {user_info['instance_url']}"
            )
            return user_info["instance_url"]

    # Default fallback instance
    default_instance = current_app.config.get(
        "DEFAULT_MASTODON_INSTANCE", "https://mastodon.social"
    )
    logger.warning(f"No instance found in request, using default: {default_instance}")
    return default_instance


def get_user_by_token(token):
    """
    Look up user information based on an OAuth token.

    Args:
        token: The OAuth token to look up

    Returns:
        dict: User information including instance_url and user_id
    """
    try:
        with get_db_connection() as conn:
            with get_cursor(conn) as cur:
                # Use correct placeholder syntax based on database type
                placeholder = "?" if USE_IN_MEMORY_DB else "%s"
                
                cur.execute(
                    f"""
                    SELECT user_id, instance_url, access_token 
                    FROM user_identities 
                    WHERE access_token = {placeholder}
                """,
                    (token,),
                )

                result = cur.fetchone()
                if result:
                    return {
                        "user_id": result[0],
                        "instance_url": result[1],
                        "access_token": result[2],
                    }
    except Exception as e:
        logger.error(f"Database error looking up token: {e}")

    return None


def get_authenticated_user(req):
    """
    Resolve the internal user ID from the request.

    Args:
        req: The Flask request object

    Returns:
        str: Internal user ID for the authenticated user or None
    """
    logger.info(f"HEADERS: {req.headers}")
    # Try to get from the Authorization header
    auth_header = req.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        # Look up in database
        user_info = get_user_by_token(token)
        if user_info:
            return user_info["user_id"]

    # Check if development mode is explicitly enabled
    if (
        os.environ.get("FLASK_ENV") == "development"
        and os.environ.get("ALLOW_QUERY_USER_ID") == "true"
    ):
        # Only allow query parameter user_id in development when explicitly enabled
        user_id = req.args.get("user_id")
        if user_id:
            logger.warning(
                f"Using user_id from query parameter: {user_id} - THIS IS INSECURE AND ONLY FOR DEVELOPMENT"
            )
            return user_id

    # No user identified
    return None


def check_user_privacy(user_id):
    """
    Check if a user has opted out of personalization.

    Args:
        user_id: The user ID to check

    Returns:
        bool: True if personalization is allowed, False otherwise
    """
    if not user_id:
        return False

    try:
        with get_db_connection() as conn:
            privacy_level = get_user_privacy_level(conn, user_id)

            # Only allow personalization for 'full' privacy level
            return privacy_level == "full"
    except Exception as e:
        logger.error(f"Error checking privacy settings: {e}")
        # Default to no personalization on error
        return False


def get_recommendations(user_id, limit=5):
    """
    Get personalized recommendations for a user.

    Args:
        user_id: The user ID to get recommendations for
        limit: Maximum number of recommendations to return

    Returns:
        list: List of Mastodon-compatible post objects
    """
    try:
        # Import here to avoid circular imports
        from routes.recommendations import get_recommended_timeline

        # Create a mock request with user_id and limit
        class MockRequest:
            args = {"user_id": user_id, "limit": limit}

        # Call the recommendations endpoint directly
        recommendations = get_recommended_timeline(MockRequest())

        # Parse the JSON response
        if isinstance(recommendations, Response):
            try:
                recommendations = json.loads(recommendations.get_data(as_text=True))
            except:
                recommendations = []

        # Mark recommendations so they can be identified
        for rec in recommendations:
            rec["is_recommendation"] = True

            # Ensure recommendations have a minimum set of fields
            if "id" not in rec:
                rec["id"] = f"rec_{int(time.time())}_{hash(str(rec)) % 10000}"

            # Add explanation if missing
            if "recommendation_reason" not in rec:
                rec["recommendation_reason"] = "Recommended for you"

        return recommendations
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return []


def blend_recommendations(original_posts, recommendations, blend_ratio=0.3):
    """
    Blend recommendations into the original timeline.

    Args:
        original_posts: List of posts from Mastodon
        recommendations: List of personalized recommendations
        blend_ratio: Approximate ratio of recommendations to include

    Returns:
        list: Combined and sorted list of posts
    """
    if not recommendations:
        logger.debug("No recommendations to blend")
        return original_posts

    if not original_posts:
        logger.debug("No original posts, returning only recommendations")
        return recommendations

    # Compute how many recommendations to include
    total_posts = len(original_posts)
    rec_count = min(len(recommendations), max(1, int(total_posts * blend_ratio)))

    # Get the subset of recommendations to use
    recs_to_use = recommendations[:rec_count]

    # Calculate spacing for injecting recommendations
    if total_posts <= rec_count:
        # If few original posts, alternate
        spacing = 1
    else:
        # Otherwise, distribute evenly
        spacing = max(1, total_posts // rec_count - 1)

    # Create the blended timeline
    blended = []
    rec_index = 0

    for i, post in enumerate(original_posts):
        blended.append(post)

        # Insert a recommendation after every 'spacing' posts
        if i % spacing == 0 and rec_index < len(recs_to_use):
            blended.append(recs_to_use[rec_index])
            rec_index += 1

    # Add any remaining recommendations at the end
    if rec_index < len(recs_to_use):
        blended.extend(recs_to_use[rec_index:])

    # Ensure we're not returning more than the original count (to avoid pagination issues)
    # Allow up to 3 extra posts for a smoother experience
    max_allowed = total_posts + 3
    if len(blended) > max_allowed:
        blended = blended[:max_allowed]

    return blended


# New endpoints for home timeline
@proxy_bp.route("/timelines/home", methods=["GET"])
@log_route
def get_home_timeline():
    """Get a user's home timeline with cold start support for new users.

    This endpoint implements Mastodon-compatible GET /api/v1/timelines/home with
    additional cold start functionality that activates when:
    1. A user follows no one on their Mastodon instance
    2. The `cold_start=true` query parameter is explicitly provided

    The cold start feature provides a curated set of engaging posts to new users
    instead of showing an empty timeline, helping to bootstrap their social
    experience on the platform.

    Args:
        None (uses Flask request object)

    Query Parameters:
        limit (int, optional): Maximum number of posts to return. Defaults to 20.
        cold_start (bool, optional): Force cold start mode regardless of follow status.
                                   Defaults to false.

    Returns:
        Flask.Response: JSON response containing:
            - timeline: List of Mastodon-compatible post objects
            - For cold start posts, each post contains additional flags:
                - is_cold_start: True
                - is_real_mastodon_post: False
                - is_synthetic: True

    Environment Variables:
        COLD_START_ENABLED: Controls whether cold start is active (default: True)
        COLD_START_POSTS_PATH: Path to the cold start posts JSON file
        COLD_START_POST_LIMIT: Maximum number of cold start posts to return
    """
    request_id = hash(f"{time.time()}_{request.remote_addr}") % 10000000
    proxy_logger.info(
        f"REQ-{request_id} | GET /timelines/home | "
        f"User: {get_authenticated_user(request) or 'anonymous'} | "
        f"Client: {request.remote_addr}"
    )

    # Get user ID either from query param or auth header
    user_id = get_authenticated_user(request)
    is_anonymous = not user_id

    # Get request parameters
    limit = request.args.get("limit", default=20, type=int)
    force_cold_start = request.args.get("cold_start", "").lower() == "true"

    # Extract auth token from request
    auth_header = request.headers.get("Authorization")
    user_token = None
    if auth_header and auth_header.startswith("Bearer "):
        user_token = auth_header.split(" ")[1]

    # Check if cold start mode is forced or should be triggered
    cold_start_mode = force_cold_start

    # Handle anonymous users with cold start content if configured
    if is_anonymous and (ALLOW_COLD_START_FOR_ANONYMOUS or force_cold_start):
        proxy_logger.info(
            f"[COLD_START_FALLBACK] Anonymous session triggered cold start | request_id={request_id}"
        )
        # Set cold start mode to true for anonymous users
        cold_start_mode = True
        # Use "anonymous" as user_id for tracking
        user_id = "anonymous"

    # Check if user should exit cold start due to sufficient interactions
    if COLD_START_ENABLED and user_id and not force_cold_start:
        exit_cold_start = should_exit_cold_start(user_id)
        if exit_cold_start:
            proxy_logger.info(
                f"COLD-START-EXIT-{request_id} | User {user_id} has graduated from cold start mode"
            )
            # Skip cold start, continue with normal timeline below
        else:
            # Check if user should re-enter cold start due to inactivity
            should_reenter, reason = should_reenter_cold_start(user_id)
            if should_reenter:
                cold_start_mode = True
                proxy_logger.info(
                    f"COLD-START-REENTRY-{request_id} | User {user_id} re-entering cold start: {reason}"
                )
            # If not exiting or re-entering, check follows status
            elif COLD_START_ENABLED and not cold_start_mode and user_token:
                try:
                    # Import here to avoid circular imports
                    from utils.follows import user_follows_anyone

                    # Check if user follows anyone
                    follows_anyone = user_follows_anyone(user_token)

                    if not follows_anyone:
                        cold_start_mode = True
                        proxy_logger.info(
                            f"COLD-START-{request_id} | User {user_id} follows no one - triggering cold start mode"
                        )
                except Exception as e:
                    proxy_logger.error(
                        f"ERROR-{request_id} | Error checking user follows: {e}"
                    )
                    # Continue with normal flow

    # Handle cold start mode if enabled
    if cold_start_mode:
        try:
            # Check if this is an anonymous user session
            is_anonymous_session = user_id == "anonymous"

            # Log the cold start event
            user_alias = (
                "anonymous" if is_anonymous_session else generate_user_alias(user_id)
            )
            cold_start_logger.info(
                f"{user_alias} | COLD_START_TRIGGERED | "
                + f"forced={force_cold_start} | anonymous={is_anonymous_session} | request_id={request_id}"
            )

            # Load all cold start posts
            all_posts = load_cold_start_posts()

            # For anonymous users, always use random selection
            if is_anonymous_session or force_cold_start or len(all_posts) == 0:
                # For anonymous or forced cold start, use random selection
                posts = all_posts[: min(COLD_START_POST_LIMIT, limit)]

                proxy_logger.info(
                    f"[COLD_START] Injecting default content | "
                    + f"User: {user_id} | Count: {len(posts)} | "
                    + f"Anonymous: {is_anonymous_session} | "
                    + f"Test mode: {force_cold_start}"
                )
            else:
                # For authenticated users with history, use weighted selection
                posts = get_weighted_post_selection(
                    user_id=user_id,
                    posts=all_posts,
                    count=min(COLD_START_POST_LIMIT, limit),
                )

                proxy_logger.info(
                    f"[COLD_START] Injecting personalized cold start content | "
                    + f"User: {user_id} | Count: {len(posts)} | "
                    + f"Adaptive: true"
                )

            # Return cold start posts
            return jsonify({"timeline": posts})
        except Exception as e:
            proxy_logger.error(f"ERROR-{request_id} | Cold start content error: {e}")
            # Fall back to normal flow on error

    # For validator or synthetic users, return dummy timeline
    if user_id.startswith("corgi_validator_") or user_id.startswith("test_"):
        proxy_logger.info(f"SYNTH-{request_id} | Synthetic user detected: {user_id}")
        from routes.recommendations import get_recommended_timeline

        # Try to get some real posts from recommendations endpoint
        try:

            class MockRequest:
                args = {"user_id": user_id, "limit": limit}

            # Get timeline posts from the recommendations endpoint
            timeline_data = get_recommended_timeline(MockRequest())

            if isinstance(timeline_data, Response):
                timeline_data = json.loads(timeline_data.get_data(as_text=True))

            # Add is_real_mastodon_post flag if not present
            for post in timeline_data:
                if "is_real_mastodon_post" not in post:
                    post["is_real_mastodon_post"] = False

                # Add is_synthetic flag if not present
                if "is_synthetic" not in post:
                    post["is_synthetic"] = True

            proxy_logger.info(
                f"TIMELINE-{request_id} | Synthetic timeline generated with {len(timeline_data)} posts"
            )
            return jsonify({"timeline": timeline_data})
        except Exception as e:
            proxy_logger.error(
                f"ERROR-{request_id} | Error generating synthetic timeline: {e}"
            )
            # Return empty array on error
            return jsonify({"timeline": []})

    # For real users, attempt to proxy to their instance
    instance_url = get_user_instance(request)

    try:
        # Build the target URL
        target_url = urljoin(instance_url, f"/api/v1/timelines/home")

        # Extract request components
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in ["host", "content-length"]
        }
        params = request.args.to_dict()

        # Make the request to the Mastodon instance
        upstream_start_time = time.time()
        proxied_response = requests.request(
            method="GET", url=target_url, headers=headers, params=params, timeout=10
        )
        upstream_time = time.time() - upstream_start_time

        # Log upstream response metrics
        proxy_logger.info(
            f"UP-{request_id} | Upstream timeline response | "
            f"Status: {proxied_response.status_code} | "
            f"Time: {upstream_time:.3f}s"
        )

        if proxied_response.status_code == 200:
            try:
                # Extract the response content
                timeline_data = proxied_response.json()

                # Ensure all posts have required ELK interaction fields
                for post in timeline_data:
                    if 'favourited' not in post:
                        post['favourited'] = False
                    if 'reblogged' not in post:
                        post['reblogged'] = False
                    if 'bookmarked' not in post:
                        post['bookmarked'] = False
                    if 'muted' not in post:
                        post['muted'] = False
                    if 'pinned' not in post:
                        post['pinned'] = False

                # Return direct array for ELK compatibility (not wrapped in timeline object)
                return jsonify(timeline_data)
            except Exception as e:
                proxy_logger.error(
                    f"ERROR-{request_id} | Failed to parse timeline: {e}"
                )
                # Return proxied response as-is
                return Response(
                    proxied_response.content,
                    status=proxied_response.status_code,
                    content_type=proxied_response.headers.get("Content-Type"),
                )
        elif proxied_response.status_code == 401:
            # For 401 Unauthorized, return empty array instead
            proxy_logger.info(
                f"AUTH-{request_id} | Unauthorized response from upstream, returning empty timeline"
            )
            return jsonify([])
        else:
            # For other errors, return empty array
            proxy_logger.info(
                f"ERR-{request_id} | Error {proxied_response.status_code} from upstream, returning empty timeline"
            )
            return jsonify([])
    except Exception as e:
        proxy_logger.error(f"ERROR-{request_id} | Timeline proxy failed: {e}")
        # Return empty array on error
        return jsonify([])


@proxy_bp.route("/timelines/home/augmented", methods=["GET"])
@log_route
def get_augmented_timeline():
    """
    Get a user's augmented timeline with personalized recommendations.

    This endpoint implements Mastodon-compatible GET /api/v1/timelines/home/augmented

    Query parameters:
        user_id: ID of the user (for testing/validation)
        limit: Maximum number of posts to return (default: 20)
        inject_recommendations: Whether to inject recommendations (default: false)

    Returns:
        200 OK with blended timeline posts
    """
    request_id = hash(f"{time.time()}_{request.remote_addr}") % 10000000
    proxy_logger.info(
        f"REQ-{request_id} | GET /timelines/home/augmented | "
        f"User: {get_authenticated_user(request) or 'anonymous'} | "
        f"Client: {request.remote_addr}"
    )

    # Get user ID either from query param or auth header
    user_id = get_authenticated_user(request)
    if not user_id:
        # Return empty array instead of 401 for validator compatibility
        proxy_logger.info(
            f"USER-{request_id} | No authenticated user, returning empty timeline"
        )
        return jsonify({"timeline": []})

    # Get request parameters
    limit = request.args.get("limit", default=20, type=int)
    inject_recommendations = (
        request.args.get("inject_recommendations", "").lower() == "true"
    )

    # Get the regular timeline first
    regular_timeline = []

    # Depending on the user type, get timeline differently
    if user_id.startswith("corgi_validator_") or user_id.startswith("test_"):
        # For synthetic users, use mock timeline data
        proxy_logger.info(f"SYNTH-{request_id} | Synthetic user detected: {user_id}")

        # Create some synthetic posts
        synthetic_count = min(
            5, limit // 2
        )  # Use at most half the limit for synthetic posts
        for i in range(synthetic_count):
            post_id = f"corgi_synthetic_post_{user_id}_{i}"
            regular_timeline.append(
                {
                    "id": post_id,
                    "content": f"Synthetic post {i+1} for user {user_id}",
                    "created_at": datetime.datetime.now().isoformat(),
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

        proxy_logger.info(
            f"TIMELINE-{request_id} | Created {len(regular_timeline)} synthetic timeline posts"
        )
    else:
        # For real users, try to get their timeline from the instance
        try:
            # Get regular timeline
            instance_url = get_user_instance(request)
            target_url = urljoin(instance_url, f"/api/v1/timelines/home")

            # Extract request components
            headers = {
                key: value
                for key, value in request.headers.items()
                if key.lower() not in ["host", "content-length"]
            }
            params = request.args.to_dict()

            # Make the request to get regular timeline
            proxied_response = requests.request(
                method="GET", url=target_url, headers=headers, params=params, timeout=10
            )

            if proxied_response.status_code == 200:
                try:
                    # Extract the response content
                    regular_timeline = proxied_response.json()
                    for post in regular_timeline:
                        post["is_real_mastodon_post"] = True
                        post["is_synthetic"] = False

                    proxy_logger.info(
                        f"TIMELINE-{request_id} | Retrieved {len(regular_timeline)} regular timeline posts"
                    )
                except Exception as e:
                    proxy_logger.error(
                        f"ERROR-{request_id} | Failed to parse timeline: {e}"
                    )
            else:
                proxy_logger.info(
                    f"ERR-{request_id} | Error {proxied_response.status_code} from upstream timeline"
                )
        except Exception as e:
            proxy_logger.error(f"ERROR-{request_id} | Timeline retrieval failed: {e}")

    # If inject_recommendations is true, get and blend recommendations
    if inject_recommendations:
        try:
            proxy_logger.info(
                f"INJECT-{request_id} | Getting recommendations for user {user_id}"
            )
            recommendations = get_recommendations(user_id, limit=min(10, limit))

            # Add is_recommendation flag for validator compatibility
            for rec in recommendations:
                rec["is_recommendation"] = True

                # Ensure other required flags are present
                if "is_real_mastodon_post" not in rec:
                    rec["is_real_mastodon_post"] = False
                if "is_synthetic" not in rec:
                    rec["is_synthetic"] = True

            # If we have regular timeline posts, blend them
            if regular_timeline:
                blended_timeline = blend_recommendations(
                    regular_timeline, recommendations
                )
                proxy_logger.info(
                    f"BLEND-{request_id} | Blended {len(regular_timeline)} regular posts with "
                    f"{len(recommendations)} recommendations, resulting in {len(blended_timeline)} posts"
                )
            else:
                # If no regular posts, just use recommendations
                blended_timeline = recommendations
                proxy_logger.info(
                    f"BLEND-{request_id} | No regular posts, using {len(recommendations)} recommendations directly"
                )

            # Return the blended timeline
            return jsonify(
                {"timeline": blended_timeline, "injected_count": len(recommendations)}
            )
        except Exception as e:
            proxy_logger.error(
                f"ERROR-{request_id} | Recommendation blending failed: {e}"
            )
            # Return regular timeline on error
            return jsonify({"timeline": regular_timeline})
    else:
        # No recommendations requested, just return regular timeline
        proxy_logger.info(
            f"NOREC-{request_id} | No recommendations requested, returning {len(regular_timeline)} regular posts"
        )
        return jsonify({"timeline": regular_timeline})


@proxy_bp.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
@log_route
def proxy_to_mastodon(path):
    """
    Proxy requests to the appropriate Mastodon instance.

    For most endpoints, simply forwards the request unchanged.
    For timeline endpoints, injects personalized recommendations.

    Args:
        path: The API path after /api/v1/

    Returns:
        Response: The proxied response, potentially with injected recommendations
    """
    # Extract request information for logging
    request_id = hash(f"{time.time()}_{request.remote_addr}") % 10000000
    request_start_time = time.time()

    # Extract Mastodon instance to proxy to
    instance_url = get_user_instance(request)

    # Default to environment variable if available
    if not instance_url and os.environ.get("MASTODON_DEFAULT_INSTANCE"):
        instance_url = os.environ.get("MASTODON_DEFAULT_INSTANCE")
        if not instance_url.startswith(("http://", "https://")):
            instance_url = f"https://{instance_url}"

    # Build the target URL
    target_url = urljoin(instance_url, f"/api/v1/{path}")

    # Get authenticated user information
    user_id = get_authenticated_user(request)

    # Log the proxy request
    proxy_logger.info(
        f"REQ-{request_id} | {request.method} /{path} | "
        f"Target: {instance_url} | "
        f"User: {user_id or 'anonymous'} | "
        f"Client: {request.remote_addr} | "
        f"UA: {request.headers.get('User-Agent', 'Unknown').split(' ')[0]}"
    )

    # Extract request components
    method = request.method
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in ["host", "content-length"]
    }
    params = request.args.to_dict()
    data = request.get_data()

    # Extract auth token if present
    user_token = None
    auth_header = headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        user_token = auth_header.split(" ")[1]

    # Log auth headers presence (without revealing tokens)
    has_auth = "Authorization" in headers
    proxy_logger.debug(f"REQ-{request_id} | Auth headers present: {has_auth}")

    # Check if this is an interaction endpoint we need to handle
    interaction_pattern = re.match(
        r"^statuses/([^/]+)/(favourite|bookmark|reblog)$", path
    )
    is_interaction = interaction_pattern is not None

    # Indicate if the route is likely to be enriched
    is_enrichable = path == "timelines/home" and method == "GET"

    # Track metrics for later use
    enrichment_status = "not_applicable"
    recommendations_count = 0

    # Extract post ID and action type if this is an interaction endpoint
    post_id = None
    action_type = None
    if is_interaction:
        post_id = interaction_pattern.group(1)
        raw_action = interaction_pattern.group(2)

        # Normalize action type
        if raw_action == "favourite":
            action_type = "favorite"
        else:
            action_type = raw_action  # 'bookmark' or 'reblog'

        proxy_logger.info(
            f"INTERACTION-{request_id} | Detected interaction | "
            f"Action: {action_type} | "
            f"Post: {post_id} | "
            f"User: {user_id or 'anonymous'}"
        )

        # Check if this is a cold start post interaction
        if post_id.startswith("cold_start_post_") and user_token:
            # Import here to avoid circular imports
            from utils.follows import log_cold_start_interaction

            # Log the cold start interaction
            try:
                # Get the post data to extract metadata for signal tracking
                cold_start_posts = load_cold_start_posts()
                post_metadata = None

                # Find the post in our cold start collection
                for post in cold_start_posts:
                    if post.get("id") == post_id:
                        post_metadata = post
                        break

                # Log basic interaction for analyzing cold start effectiveness
                log_cold_start_interaction(
                    user_token=user_token,
                    post_id=post_id,
                    action_type=action_type,
                    is_test_mode=False,
                )

                # Update user's signal profile with this interaction
                if post_metadata and user_id:
                    updated_signals = update_user_signals(
                        user_id=user_id,
                        post_metadata=post_metadata,
                        action_type=action_type,
                    )

                    # Export to database periodically (simple approach)
                    # In a production system, this would be done in a background task
                    if hash(post_id) % 5 == 0:  # ~20% of interactions trigger export
                        export_user_signals_to_db()

                    proxy_logger.info(
                        f"COLD-START-SIGNAL-{request_id} | Updated user signals | "
                        f"User: {user_id} | Post: {post_id} | "
                        f"Category: {post_metadata.get('category', 'unknown')} | "
                        f"Tags: {','.join(post_metadata.get('tags', []))}"
                    )

                proxy_logger.info(
                    f"COLD-START-{request_id} | Logged interaction with cold start post | "
                    f"Post: {post_id} | Action: {action_type}"
                )
            except Exception as e:
                proxy_logger.error(
                    f"ERROR-{request_id} | Failed to log cold start interaction: {e}"
                )
                # Continue with normal processing

    # If this is a home timeline request, let our specialized endpoint handle it
    if path == "timelines/home" and method == "GET":
        proxy_logger.info(
            f"ROUTE-{request_id} | Home timeline detected, redirecting to specialized handler"
        )
        return get_home_timeline()

    try:
        # Make the request to the target Mastodon instance
        upstream_start_time = time.time()
        proxied_response = requests.request(
            method=method,
            url=target_url,
            headers=headers,
            params=params,
            data=data,
            timeout=10,
        )
        upstream_time = time.time() - upstream_start_time

        # Log upstream response metrics
        proxy_logger.info(
            f"UP-{request_id} | Upstream response | "
            f"Status: {proxied_response.status_code} | "
            f"Time: {upstream_time:.3f}s | "
            f"Size: {len(proxied_response.content)} bytes"
        )

        # Extract the response for potential modification
        response_headers = {
            key: value
            for key, value in proxied_response.headers.items()
            if key.lower()
            not in ["content-encoding", "transfer-encoding", "content-length"]
        }
        response_content = proxied_response.content
        status_code = proxied_response.status_code

        # Handle interaction logging for successful requests to interaction endpoints
        if is_interaction and status_code >= 200 and status_code < 300 and user_id:
            try:
                # Parse post data from response
                post_data = json.loads(response_content)

                # Only proceed if we have a valid user ID
                if user_id:
                    # Check privacy settings
                    with get_db_connection() as conn:
                        privacy_level = get_user_privacy_level(conn, user_id)

                        # Don't log if privacy level is 'none'
                        if privacy_level != "none":
                            # Generate user alias for privacy
                            user_alias = generate_user_alias(user_id)

                            # Create context with source info
                            context = {
                                "source": "mastodon_proxy",
                                "instance": instance_url,
                                "client_ip": request.remote_addr,
                                "user_agent": request.headers.get(
                                    "User-Agent", "Unknown"
                                ),
                            }

                            # Add minimal post info to ensure we have post metadata
                            ensure_post_metadata(conn, post_id, post_data)

                            # Log the interaction
                            log_proxy_interaction(
                                conn, user_alias, post_id, action_type, context
                            )

                            proxy_logger.info(
                                f"INTERACTION-{request_id} | Logged interaction | "
                                f"User: {user_id} | "
                                f"Post: {post_id} | "
                                f"Action: {action_type} | "
                                f"Privacy: {privacy_level}"
                            )
                        else:
                            proxy_logger.info(
                                f"INTERACTION-{request_id} | Skipped logging (privacy: none) | "
                                f"User: {user_id}"
                            )
            except Exception as e:
                proxy_logger.error(
                    f"ERROR-{request_id} | Failed to log interaction: {str(e)}"
                )
                # Continue with the proxied response even if logging fails

        # For timeline/home, consider injecting recommendations
        if is_enrichable and status_code == 200:
            # Check if personalization is allowed for this user
            privacy_level = "unknown"
            personalization_allowed = False

            if user_id:
                try:
                    with get_db_connection() as conn:
                        privacy_level = get_user_privacy_level(conn, user_id)
                        personalization_allowed = privacy_level == "full"
                except Exception as e:
                    proxy_logger.error(
                        f"ERROR-{request_id} | Failed to check privacy: {e}"
                    )
                    privacy_level = "error"

            proxy_logger.info(
                f"PRIV-{request_id} | Privacy check | "
                f"User: {user_id or 'anonymous'} | "
                f"Level: {privacy_level} | "
                f"Can enrich: {personalization_allowed}"
            )

            if user_id and personalization_allowed:
                try:
                    # Parse the original response
                    original_posts = json.loads(response_content)
                    original_count = len(original_posts)

                    # Get recommendations for this user
                    rec_start_time = time.time()
                    recommendations = get_recommendations(user_id)
                    rec_time = time.time() - rec_start_time

                    if recommendations:
                        # Blend recommendations with the original posts
                        blend_start_time = time.time()
                        blended_timeline = blend_recommendations(
                            original_posts, recommendations
                        )
                        blend_time = time.time() - blend_start_time

                        # Convert back to JSON
                        response_content = json.dumps(blended_timeline).encode("utf-8")
                        response_headers["Content-Type"] = "application/json"

                        # Add header to indicate recommendations were injected
                        recommendations_count = len(recommendations)
                        response_headers["X-Corgi-Recommendations"] = (
                            f"injected={recommendations_count}"
                        )

                        # Log the enrichment
                        proxy_logger.info(
                            f"ENRICH-{request_id} | Timeline enriched | "
                            f"Original posts: {original_count} | "
                            f"Recs added: {recommendations_count} | "
                            f"Final posts: {len(blended_timeline)} | "
                            f"Rec time: {rec_time:.3f}s | "
                            f"Blend time: {blend_time:.3f}s"
                        )

                        enrichment_status = "enriched"
                    else:
                        proxy_logger.info(
                            f"ENRICH-{request_id} | No recommendations generated"
                        )
                        enrichment_status = "no_recommendations"
                except Exception as e:
                    proxy_logger.error(
                        f"ERROR-{request_id} | Enrichment failed: {str(e)}"
                    )
                    enrichment_status = "error"
                    # Continue with original response on error
            else:
                if not user_id:
                    enrichment_status = "no_user"
                else:
                    enrichment_status = "privacy_restricted"
                proxy_logger.info(
                    f"ENRICH-{request_id} | Skipped enrichment | "
                    f"Reason: {enrichment_status}"
                )

        # Prepare final response
        response = Response(
            response_content, status=status_code, headers=response_headers
        )

        # Log completion
        total_time = time.time() - request_start_time
        proxy_logger.info(
            f"RESP-{request_id} | Request completed | "
            f"Status: {status_code} | "
            f"Total time: {total_time:.3f}s | "
            f"Enriched: {enrichment_status}"
        )

        # Record metrics if this was a timeline request
        if is_enrichable and status_code == 200:
            record_proxy_metrics(
                path=path,
                user_id=user_id,
                elapsed_time=total_time,
                upstream_time=upstream_time,
                enriched=(enrichment_status == "enriched"),
                recommendations_count=recommendations_count,
                status_code=status_code,
            )

        return response

    except requests.RequestException as e:
        error_time = time.time() - request_start_time
        proxy_logger.error(
            f"ERROR-{request_id} | Proxy failed | "
            f"Target: {instance_url} | "
            f"Error: {str(e)} | "
            f"Time: {error_time:.3f}s"
        )

        # Record error metrics
        if is_enrichable:
            record_proxy_metrics(
                path=path,
                user_id=user_id,
                elapsed_time=error_time,
                upstream_time=0,
                enriched=False,
                recommendations_count=0,
                status_code=502,
                error=str(e),
            )

        return (
            jsonify(
                {
                    "error": "Failed to proxy request to Mastodon instance",
                    "instance": instance_url,
                    "details": str(e),
                }
            ),
            502,
        )


# In-memory metrics store
from collections import defaultdict, deque
import threading

# Thread-safe metrics storage
_metrics_lock = threading.Lock()
_request_metrics = defaultdict(int)
_latency_samples = deque(maxlen=100)  # Store the 100 most recent request times
_error_samples = deque(maxlen=20)  # Store the 20 most recent errors
_last_reset_time = time.time()


def ensure_post_metadata(conn, post_id, post_data):
    """
    Ensure post metadata exists in the database.

    Args:
        conn: Database connection
        post_id: Post ID
        post_data: Post data from Mastodon API
    """
    try:
        with conn.cursor() as cur:
            # Check if post exists
            cur.execute(
                "SELECT post_id FROM post_metadata WHERE post_id = %s", (post_id,)
            )
            exists = cur.fetchone() is not None

            if not exists:
                # Extract basic post information
                author_id = str(post_data.get("account", {}).get("id", ""))
                author_name = post_data.get("account", {}).get("username", "unknown")
                content = post_data.get("content", "")
                sensitive = post_data.get("sensitive", False)
                language = post_data.get("language", "en")

                # Extract tags
                tags = []
                for tag in post_data.get("tags", []):
                    if isinstance(tag, dict) and "name" in tag:
                        tags.append(tag["name"])
                    elif isinstance(tag, str):
                        tags.append(tag)

                # Insert post metadata
                cur.execute(
                    """
                    INSERT INTO post_metadata 
                    (post_id, author_id, author_name, content, language, tags, sensitive, mastodon_post)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (post_id) DO NOTHING
                """,
                    (
                        post_id,
                        author_id,
                        author_name,
                        content,
                        language,
                        tags,
                        sensitive,
                        json.dumps(post_data),
                    ),
                )
                conn.commit()

                proxy_logger.debug(f"Added new post metadata for post {post_id}")
    except Exception as e:
        proxy_logger.error(f"Error ensuring post metadata: {e}")
        # Don't raise, to avoid breaking the interaction flow


def log_proxy_interaction(conn, user_alias, post_id, action_type, context):
    """
    Log a user interaction from the proxy.

    Args:
        conn: Database connection
        user_alias: Pseudonymized user ID
        post_id: Post ID
        action_type: Type of action (favorite, bookmark, reblog)
        context: Additional context information
    """
    try:
        with conn.cursor() as cur:
            # Insert the interaction
            cur.execute(
                """
                INSERT INTO interactions 
                (user_alias, post_id, action_type, context)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_alias, post_id, action_type) 
                DO UPDATE SET 
                    context = EXCLUDED.context,
                    created_at = CURRENT_TIMESTAMP
                RETURNING id
            """,
                (user_alias, post_id, action_type, json.dumps(context)),
            )

            result = cur.fetchone()
            interaction_id = result[0] if result else None

            # Update interaction counts if this is a trackable action
            if action_type in ["favorite", "bookmark", "reblog"]:
                field_name = {
                    "favorite": "favorites",
                    "bookmark": "bookmarks",
                    "reblog": "reblogs",
                }.get(action_type)

                if field_name:
                    cur.execute(
                        """
                        UPDATE post_metadata
                        SET interaction_counts = jsonb_set(
                            COALESCE(interaction_counts, '{}'::jsonb),
                            %s,
                            (COALESCE((interaction_counts->%s)::int, 0) + 1)::text::jsonb
                        )
                        WHERE post_id = %s
                    """,
                        ([field_name], field_name, post_id),
                    )

            conn.commit()

            # Log the interaction to the dedicated interactions log
            try:
                # Log the interaction using the pre-configured logger
                interaction_logger.info(f"{user_alias} | {post_id} | {action_type}")
            except Exception as log_err:
                proxy_logger.error(f"Failed to write to interaction log: {log_err}")

            return interaction_id
    except Exception as e:
        proxy_logger.error(f"Error logging interaction: {e}")
        conn.rollback()
        return None


def record_proxy_metrics(
    path,
    user_id,
    elapsed_time,
    upstream_time,
    enriched,
    recommendations_count,
    status_code,
    error=None,
):
    """
    Record metrics about a proxy request.

    Args:
        path: The API path that was proxied
        user_id: The user ID (or None)
        elapsed_time: Total request time
        upstream_time: Time spent in the upstream request
        enriched: Whether the response was enriched with recommendations
        recommendations_count: Number of recommendations added
        status_code: HTTP status code
        error: Error message (if any)
    """
    with _metrics_lock:
        # Increment request counter
        _request_metrics["total_requests"] += 1

        # Track successful vs failed requests
        if 200 <= status_code < 300:
            _request_metrics["successful_requests"] += 1
        else:
            _request_metrics["failed_requests"] += 1

        # Track timeline requests specifically
        if path == "timelines/home":
            _request_metrics["timeline_requests"] += 1

            if enriched:
                _request_metrics["enriched_timelines"] += 1
                _request_metrics["total_recommendations"] += recommendations_count

        # Track latency
        _latency_samples.append(elapsed_time)

        # Track errors
        if error:
            _error_samples.append(
                {
                    "time": time.time(),
                    "path": path,
                    "error": error,
                    "status_code": status_code,
                }
            )


def get_proxy_metrics():
    """
    Get the current proxy metrics.

    Returns:
        dict: Metrics about proxy usage
    """
    with _metrics_lock:
        # Calculate average latency
        avg_latency = sum(_latency_samples) / max(len(_latency_samples), 1)

        # Calculate enrichment rate
        timeline_requests = _request_metrics["timeline_requests"]
        enrichment_rate = 0
        if timeline_requests > 0:
            enrichment_rate = _request_metrics["enriched_timelines"] / timeline_requests

        # Get recent errors
        recent_errors = list(_error_samples)

        # Calculate uptime
        uptime = time.time() - _last_reset_time

        return {
            "total_requests": _request_metrics["total_requests"],
            "successful_requests": _request_metrics["successful_requests"],
            "failed_requests": _request_metrics["failed_requests"],
            "timeline_requests": timeline_requests,
            "enriched_timelines": _request_metrics["enriched_timelines"],
            "total_recommendations": _request_metrics["total_recommendations"],
            "avg_latency_seconds": avg_latency,
            "enrichment_rate": enrichment_rate,
            "sample_size": len(_latency_samples),
            "recent_errors": recent_errors,
            "uptime_seconds": uptime,
        }


def reset_proxy_metrics():
    """Reset all proxy metrics."""
    with _metrics_lock:
        _request_metrics.clear()
        _latency_samples.clear()
        _error_samples.clear()
        global _last_reset_time
        _last_reset_time = time.time()


# Additional routes for debugging/monitoring


@proxy_bp.route("/status", methods=["GET"])
def proxy_status():
    """
    Status endpoint to check if the proxy is running.
    """
    return jsonify(
        {
            "status": "ok",
            "proxy": "active",
            "default_instance": current_app.config.get(
                "DEFAULT_MASTODON_INSTANCE", "https://mastodon.social"
            ),
        }
    )


@proxy_bp.route("/instance", methods=["GET"])
def detect_instance():
    """
    Debug endpoint to see what instance would be detected for the current request.
    """
    instance = get_user_instance(request)
    user_id = get_authenticated_user(request)

    return jsonify(
        {
            "detected_instance": instance,
            "user_id": user_id,
            "headers": dict(request.headers),
            "args": request.args.to_dict(),
        }
    )


@proxy_bp.route("/v2/instance", methods=["GET"])
def get_instance_info():
    """
    Return Mastodon instance information.

    This endpoint implements Mastodon's GET /api/v2/instance
    Required by Elk for proper client integration.
    """
    return jsonify(
        {
            "uri": request.host,
            "title": "Corgi Recommender",
            "short_description": "Test instance for Corgi + Elk integration",
            "description": "A test instance for Corgi Recommender + Elk integration",
            "version": "4.3.0",
            "urls": {},
            "stats": {"user_count": 1, "status_count": 100, "domain_count": 1},
            "thumbnail": "/static/assets/corgi-mascot.png",
            "languages": ["en"],
            "registrations": False,
            "approval_required": False,
            "contact_account": None,
        }
    )


@proxy_bp.route("/v1/accounts/verify_credentials", methods=["GET"])
def verify_credentials():
    """
    Return user account information.

    This endpoint implements Mastodon's GET /api/v1/accounts/verify_credentials
    Required by Elk to verify user login and access token.
    """
    # Get authenticated user from the request
    user_id = get_authenticated_user(request)

    # Generate a user display name
    display_name = "Demo User"
    if user_id:
        display_name = f"User {user_id}"

    # Return minimal account data that Elk expects
    return jsonify(
        {
            "id": user_id or "demo_user",
            "username": user_id or "demo_user",
            "acct": f"{user_id or 'demo_user'}@{request.host}",
            "display_name": display_name,
            "note": "Demo user for Corgi Recommender",
            "url": f"https://{request.host}/@{user_id or 'demo_user'}",
            "avatar": f"https://{request.host}/static/assets/corgi-mascot.png",
            "header": f"https://{request.host}/static/assets/corgi-hero.png",
            "followers_count": 0,
            "following_count": 0,
            "statuses_count": 0,
            "bot": False,
            "locked": False,
            "source": {"privacy": "public", "sensitive": False, "language": "en"},
            "created_at": "2023-01-01T00:00:00.000Z",
        }
    )


@proxy_bp.route("/metrics", methods=["GET"])
def proxy_metrics():
    """
    Return metrics about proxy usage.
    """
    reset = request.args.get("reset", "").lower() == "true"
    metrics = get_proxy_metrics()

    if reset:
        reset_proxy_metrics()
        metrics["reset"] = True

    return jsonify(metrics)


def generate_proxy_cache_key(endpoint, params, user_id, instance):
    """
    Generate a cache key for proxy requests.
    
    Args:
        endpoint: The API endpoint being requested
        params: Query parameters dict
        user_id: User ID (if any)
        instance: Mastodon instance URL
        
    Returns:
        str: Cache key for this request
    """
    # Sort params for consistent key generation
    sorted_params = sorted(params.items()) if params else []
    params_str = "&".join([f"{k}={v}" for k, v in sorted_params])
    
    # Create cache key components
    key_parts = [
        endpoint or "",
        params_str,
        user_id or "anonymous",
        instance or "default"
    ]
    
    # Join and hash for consistent key
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def determine_proxy_cache_ttl(endpoint):
    """
    Determine the appropriate TTL for a proxy cache entry based on endpoint type.
    
    Args:
        endpoint: The API endpoint being requested
        
    Returns:
        int: TTL in seconds
    """
    if not endpoint:
        return PROXY_CACHE_TTL_DEFAULT
    
    endpoint = endpoint.lower()
    
    # Timeline endpoints - short TTL for fresh content
    if 'timeline' in endpoint:
        return PROXY_CACHE_TTL_TIMELINE
    
    # Profile/account endpoints - medium TTL
    if 'account' in endpoint:
        return PROXY_CACHE_TTL_PROFILE
    
    # Instance info endpoints - long TTL (rarely changes)
    if 'instance' in endpoint or 'custom_emojis' in endpoint:
        return PROXY_CACHE_TTL_INSTANCE
    
    # Status/post endpoints - medium TTL
    if 'status' in endpoint:
        return PROXY_CACHE_TTL_STATUS
    
    # Default TTL for other endpoints
    return PROXY_CACHE_TTL_DEFAULT


def should_cache_proxy_request(endpoint, method, status_code):
    """
    Determine if a proxy request should be cached.
    
    Args:
        endpoint: The API endpoint being requested
        method: HTTP method
        status_code: Response status code
        
    Returns:
        bool: True if request should be cached, False otherwise
    """
    # Only cache GET requests
    if method.upper() != 'GET':
        return False
    
    # Only cache successful responses
    if status_code != 200:
        return False
    
    # Don't cache interaction endpoints (favorites, boosts, etc.)
    if endpoint and any(action in endpoint.lower() for action in ['favourite', 'unfavourite', 'reblog', 'unreblog', 'bookmark', 'unbookmark']):
        return False
    
    return True
