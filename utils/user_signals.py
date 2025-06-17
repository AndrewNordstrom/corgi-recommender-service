"""
User signals module for the Corgi Recommender Service.

This module provides utilities for tracking and updating user engagement signals
during the cold start phase, enabling adaptive content personalization.
"""

import logging
import json
import os
import time
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Set, Tuple
import threading

from utils.privacy import generate_user_alias
from db.connection import get_db_connection

# Set up logging
logger = logging.getLogger(__name__)

# In-memory storage with thread safety
_signal_lock = threading.Lock()
_user_signals = {}  # User signal storage
_user_last_active = {}  # Track when users were last active
_promotion_status = {}  # Track if users have been promoted out of cold start
_signal_history = defaultdict(list)  # Track signal history for analysis

# Constants
SIGNAL_TYPES = ["tags", "vibe", "tone", "account_type", "post_type", "category"]
SIGNAL_WEIGHTS = {
    "favorite": 1.0,  # Standard weight for favorites
    "reblog": 1.5,  # Higher weight for reblogs (stronger signal)
    "bookmark": 1.2,  # Medium weight for bookmarks
    "reply": 1.8,  # Highest weight for replies (very strong signal)
}
PROMOTION_THRESHOLD_INTERACTIONS = 5  # Default number of interactions before promotion
PROMOTION_THRESHOLD_UNIQUE_TAGS = (
    3  # Default number of unique tags with >=2 interactions
)
COLD_START_DECAY_DAYS = 14  # Days of inactivity before cold start can re-trigger

# Path to config file
_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "cold_start_weights.json"
)

# Default weights (70% diverse, 30% personalized)
_DEFAULT_WEIGHTS = {
    "random_ratio": 0.7,  # Percentage of random content
    "weighted_ratio": 0.3,  # Percentage of personalized content
    "evolution_rate": 0.1,  # How quickly to shift to personalized content
    "min_weighted_ratio": 0.3,  # Minimum personalized ratio
    "max_weighted_ratio": 1.0,  # Maximum personalized ratio
}

# Load config if available
try:
    if os.path.exists(_CONFIG_PATH):
        with open(_CONFIG_PATH, "r") as f:
            _CONFIG = json.load(f)
    else:
        _CONFIG = _DEFAULT_WEIGHTS
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
        # Write default config
        with open(_CONFIG_PATH, "w") as f:
            json.dump(_DEFAULT_WEIGHTS, f, indent=2)
except Exception as e:
    logger.error(f"Error loading cold start weights config: {e}")
    _CONFIG = _DEFAULT_WEIGHTS


def get_user_signals(user_id: str) -> Dict[str, Counter]:
    """
    Get a user's signal profile with their content preferences.

    Retrieves the accumulated signals for a user, which represent their
    content preferences across different dimensions (tags, vibes, tones, etc.).

    Args:
        user_id: The user's ID

    Returns:
        Dict containing signal counters for each dimension (tags, vibe, tone, etc.)
    """
    # Generate pseudonymized user alias for privacy
    user_alias = generate_user_alias(user_id)

    with _signal_lock:
        # If user doesn't exist in the cache, initialize empty counters
        if user_alias not in _user_signals:
            _user_signals[user_alias] = {
                signal_type: Counter() for signal_type in SIGNAL_TYPES
            }

        # Return a copy to prevent external modification
        return {k: Counter(v) for k, v in _user_signals[user_alias].items()}


def is_new_user(user_id: str) -> bool:
    """
    Placeholder check to see if a user is new.
    
    This is a temporary fix to prevent import errors. A real implementation
    would check interaction history from the database.
    """
    user_alias = generate_user_alias(user_id)
    with _signal_lock:
        # A user is "new" for the purpose of this check if they have no signal history.
        return user_alias not in _signal_history or not _signal_history[user_alias]


def update_user_signals(
    user_id: str, post_metadata: Dict[str, Any], action_type: str
) -> Dict[str, Counter]:
    """
    Update a user's signal profile based on their interaction with a post.

    Extracts metadata from the post (tags, vibe, tone, etc.) and updates
    the user's signal counters, increasing counts for the metadata values
    according to the interaction type weight.

    Args:
        user_id: The user's ID
        post_metadata: Metadata from the post being interacted with
        action_type: Type of interaction (favorite, reblog, bookmark, reply)

    Returns:
        Updated signal profile as a dict of Counters
    """
    # Generate pseudonymized user alias for privacy
    user_alias = generate_user_alias(user_id)

    # Get the weight for this action type
    weight = SIGNAL_WEIGHTS.get(action_type, 1.0)

    # Initialize signal updates for logging
    signal_updates = {}

    with _signal_lock:
        # Initialize user signals if not present
        if user_alias not in _user_signals:
            _user_signals[user_alias] = {
                signal_type: Counter() for signal_type in SIGNAL_TYPES
            }

        # Update last active timestamp
        _user_last_active[user_alias] = time.time()

        # Extract and update each signal type
        for signal_type in SIGNAL_TYPES:
            # Skip if this signal type isn't in the post metadata
            if signal_type not in post_metadata and signal_type != "category":
                continue

            # Special handling for tags (list) vs other fields (scalar)
            if signal_type == "tags" and "tags" in post_metadata:
                tags = post_metadata["tags"]
                if isinstance(tags, list):
                    for tag in tags:
                        _user_signals[user_alias][signal_type][tag] += weight
                        # Log changes for this update
                        if signal_type not in signal_updates:
                            signal_updates[signal_type] = {}
                        signal_updates[signal_type][tag] = _user_signals[user_alias][
                            signal_type
                        ][tag]

            # Handle category separately (common field)
            elif signal_type == "category" and "category" in post_metadata:
                category = post_metadata["category"]
                _user_signals[user_alias][signal_type][category] += weight
                # Log changes
                if signal_type not in signal_updates:
                    signal_updates[signal_type] = {}
                signal_updates[signal_type][category] = _user_signals[user_alias][
                    signal_type
                ][category]

            # Handle scalar fields (vibe, tone, etc.)
            elif signal_type in post_metadata:
                value = post_metadata[signal_type]
                _user_signals[user_alias][signal_type][value] += weight
                # Log changes
                if signal_type not in signal_updates:
                    signal_updates[signal_type] = {}
                signal_updates[signal_type][value] = _user_signals[user_alias][
                    signal_type
                ][value]

        # Log the interaction for history tracking
        _signal_history[user_alias].append(
            {
                "timestamp": time.time(),
                "action_type": action_type,
                "post_id": post_metadata.get("id", "unknown"),
                "updates": signal_updates,
            }
        )

        # Check if user should be promoted out of cold start
        check_promotion_status(user_alias)

        # Return a copy of the updated signals
        return {k: Counter(v) for k, v in _user_signals[user_alias].items()}


def check_promotion_status(user_alias: str) -> bool:
    """
    Check if a user should be promoted out of cold start mode.

    A user is promoted when they meet the configured thresholds:
    - Total number of interactions exceeds PROMOTION_THRESHOLD_INTERACTIONS
    - At least PROMOTION_THRESHOLD_UNIQUE_TAGS tags have 2+ interactions

    Args:
        user_alias: The pseudonymized user ID

    Returns:
        bool: True if the user should be promoted, False otherwise
    """
    with _signal_lock:
        # Skip if user has already been promoted
        if user_alias in _promotion_status and _promotion_status[user_alias]:
            return True

        # Skip if user doesn't have signal history
        if user_alias not in _signal_history:
            return False

        # Check total interactions
        total_interactions = len(_signal_history[user_alias])

        # Get tag counts for tag diversity check
        tag_counts = _user_signals.get(user_alias, {}).get("tags", Counter())

        # Count tags with 2+ interactions
        tags_with_multiple = sum(1 for tag, count in tag_counts.items() if count >= 2)

        # Check promotion criteria
        should_promote = (
            total_interactions >= PROMOTION_THRESHOLD_INTERACTIONS
            and tags_with_multiple >= PROMOTION_THRESHOLD_UNIQUE_TAGS
        )

        # Log promotion status check
        logger.info(
            f"Cold start promotion check for {user_alias}: "
            + f"interactions={total_interactions}/{PROMOTION_THRESHOLD_INTERACTIONS}, "
            + f"diverse_tags={tags_with_multiple}/{PROMOTION_THRESHOLD_UNIQUE_TAGS}, "
            + f"result={'promoted' if should_promote else 'not promoted'}"
        )

        # Update promotion status if promoted
        if should_promote:
            _promotion_status[user_alias] = True
            # Log promotion event
            cold_start_logger = logging.getLogger("cold_start_interactions")
            cold_start_logger.info(
                f"{user_alias} | COLD_START_PROMOTED | "
                + f"interactions={total_interactions} | "
                + f"unique_tags_with_multiple={tags_with_multiple}"
            )

        return should_promote


def get_weighted_post_selection(
    user_id: str, posts: List[Dict[str, Any]], count: int
) -> List[Dict[str, Any]]:
    """
    Select posts for a user's cold start feed with adaptive weighting.

    Blends random diversity with personalization based on the user's
    interaction history. The weighting evolves as users interact more,
    gradually moving toward more personalized content selection.

    Args:
        user_id: The user's ID
        posts: List of all candidate cold start posts
        count: Number of posts to select

    Returns:
        List of selected posts, blending random and personalized content
    """
    import random

    # Generate pseudonymized user alias for privacy
    user_alias = generate_user_alias(user_id)

    # Get user signals
    user_signals = get_user_signals(user_id)

    # Get current weights configuration
    random_ratio = _CONFIG["random_ratio"]
    weighted_ratio = _CONFIG["weighted_ratio"]

    # For users with interaction history, adjust the weighting toward personalization
    if user_alias in _signal_history and len(_signal_history[user_alias]) > 0:
        # Calculate adjusted weight based on interaction count
        interaction_count = len(_signal_history[user_alias])

        # Increase personalization by evolution_rate per interaction
        # (bounded by min and max ratios)
        adjusted_weighted_ratio = min(
            _CONFIG["max_weighted_ratio"],
            weighted_ratio + (interaction_count * _CONFIG["evolution_rate"]),
        )

        # Ensure random_ratio and weighted_ratio sum to 1.0
        random_ratio = max(0, 1.0 - adjusted_weighted_ratio)
        weighted_ratio = adjusted_weighted_ratio

        logger.debug(
            f"Adjusted feed ratios for {user_alias}: "
            + f"random={random_ratio:.2f}, weighted={weighted_ratio:.2f}, "
            + f"interactions={interaction_count}"
        )
    else:
        logger.debug(
            f"Using default feed ratios for {user_alias}: "
            + f"random={random_ratio:.2f}, weighted={weighted_ratio:.2f}"
        )

    # Calculate how many posts to select randomly vs with weighting
    random_count = max(1, int(count * random_ratio))
    weighted_count = count - random_count

    # Always ensure at least one post of each type
    if random_count == 0 and count > 1:
        random_count = 1
        weighted_count = count - 1
    elif weighted_count == 0 and count > 1:
        weighted_count = 1
        random_count = count - 1

    # Choose random posts
    selected_posts = []
    if random_count > 0:
        selected_posts.extend(random.sample(posts, min(random_count, len(posts))))

    # Choose weighted posts
    if (
        weighted_count > 0
        and user_alias in _signal_history
        and len(_signal_history[user_alias]) > 0
    ):
        # Filter out already selected posts
        remaining_posts = [p for p in posts if p not in selected_posts]

        if remaining_posts:
            # Score posts based on user signals
            scored_posts = []
            for post in remaining_posts:
                score = calculate_post_score(post, user_signals)
                scored_posts.append((post, score))

            # Sort by score (highest first)
            scored_posts.sort(key=lambda x: x[1], reverse=True)

            # Take top N weighted posts
            top_posts = [p[0] for p in scored_posts[:weighted_count]]
            selected_posts.extend(top_posts)
    elif weighted_count > 0:
        # If no interaction history, just add random posts
        remaining_posts = [p for p in posts if p not in selected_posts]
        additional_random = random.sample(
            remaining_posts, min(weighted_count, len(remaining_posts))
        )
        selected_posts.extend(additional_random)

    # Shuffle the final selection to avoid obvious grouping
    random.shuffle(selected_posts)

    # Log the post selection with key info
    log_post_selection(user_alias, selected_posts, random_ratio, weighted_ratio)

    return selected_posts


def calculate_post_score(
    post: Dict[str, Any], user_signals: Dict[str, Counter]
) -> float:
    """
    Calculate a personalization score for a post based on user signals.

    The higher the score, the better the post matches the user's preferences
    across different metadata dimensions (tags, vibe, tone, etc.)

    Args:
        post: Post data including metadata
        user_signals: User's signal profile with preference counters

    Returns:
        float: Score indicating how well the post matches user preferences
    """
    score = 0.0

    # Weight each signal type differently based on its predictive value
    type_weights = {
        "tags": 1.0,  # Tags are strong indicators
        "category": 0.8,  # Categories are also strong
        "vibe": 0.6,  # Vibes are medium strength
        "tone": 0.5,  # Tone is medium strength
        "post_type": 0.4,  # Post type is less predictive
        "account_type": 0.3,  # Account type is least predictive
    }

    # For each signal type
    for signal_type, weight in type_weights.items():
        # Skip if this signal type isn't in the user's signals or post metadata
        if (
            signal_type not in user_signals
            or not user_signals[signal_type]
            or signal_type not in post
            and signal_type != "category"
        ):
            continue

        # Special handling for tags (list) vs other fields (scalar)
        if signal_type == "tags" and "tags" in post:
            post_tags = post["tags"]
            if isinstance(post_tags, list):
                for tag in post_tags:
                    # Add the signal value to the score, weighted by importance
                    tag_value = user_signals[signal_type].get(tag, 0)
                    score += tag_value * weight

        # Handle category separately (common field)
        elif signal_type == "category" and "category" in post:
            category = post["category"]
            category_value = user_signals[signal_type].get(category, 0)
            score += category_value * weight

        # Handle scalar fields (vibe, tone, etc.)
        elif signal_type in post:
            value = post[signal_type]
            signal_value = user_signals[signal_type].get(value, 0)
            score += signal_value * weight

    return score


def log_post_selection(
    user_alias: str,
    selected_posts: List[Dict[str, Any]],
    random_ratio: float,
    weighted_ratio: float,
) -> None:
    """
    Log information about the adaptive post selection for analytics.

    Args:
        user_alias: Pseudonymized user ID
        selected_posts: List of posts selected for display
        random_ratio: Ratio of random posts in the selection
        weighted_ratio: Ratio of personalized posts in the selection
    """
    # Extract post IDs and categories for logging
    post_ids = [post.get("id", "unknown") for post in selected_posts]
    post_categories = {}
    for post in selected_posts:
        category = post.get("category", "unknown")
        post_categories[post.get("id", "unknown")] = category

    # Get structured post tags for logging
    post_tags = {}
    for post in selected_posts:
        if "tags" in post and isinstance(post["tags"], list):
            post_tags[post.get("id", "unknown")] = post["tags"]

    # Create log message with key info for analysis
    cold_start_logger = logging.getLogger("cold_start_interactions")
    cold_start_logger.info(
        f"{user_alias} | COLD_START_FEED_SELECTION | "
        + f"random_ratio={random_ratio:.2f} | weighted_ratio={weighted_ratio:.2f} | "
        + f"post_count={len(selected_posts)} | "
        + f"post_ids={','.join(post_ids)} | "
        + f"categories={json.dumps(post_categories)} | "
        + f"interaction_count={len(_signal_history.get(user_alias, []))}"
    )


def should_exit_cold_start(user_id: str) -> bool:
    """
    Check if a user should exit cold start mode based on their signals.

    Args:
        user_id: The user's ID

    Returns:
        bool: True if the user should exit cold start, False otherwise
    """
    # Generate pseudonymized user alias for privacy
    user_alias = generate_user_alias(user_id)

    with _signal_lock:
        # Check if user has been promoted
        return user_alias in _promotion_status and _promotion_status[user_alias]


def should_reenter_cold_start(user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a user should re-enter cold start mode due to inactivity.

    Args:
        user_id: The user's ID

    Returns:
        Tuple[bool, Optional[str]]: (should_reenter, reason)
    """
    # Generate pseudonymized user alias for privacy
    user_alias = generate_user_alias(user_id)

    with _signal_lock:
        # Skip check if user has never been in cold start
        if user_alias not in _user_last_active:
            return False, None

        # Check if user has been inactive (seconds to days)
        days_inactive = (time.time() - _user_last_active[user_alias]) / (60 * 60 * 24)

        if days_inactive >= COLD_START_DECAY_DAYS:
            # Reset promotion status
            if user_alias in _promotion_status:
                _promotion_status[user_alias] = False

            return True, f"inactive_for_{days_inactive:.1f}_days"

        return False, None


def export_user_signals_to_db() -> bool:
    """
    Persist user signals from memory to database for long-term storage.

    This allows user preferences to survive service restarts and
    enables analysis of cold start patterns across the user base.

    Returns:
        bool: True if successful, False on error
    """
    try:
        with _signal_lock:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Prepare data to insert
                    now = time.time()

                    # First create a table if it doesn't exist
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS user_cold_start_signals (
                            user_alias TEXT NOT NULL,
                            signal_data JSONB NOT NULL,
                            promotion_status BOOLEAN,
                            last_active TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (user_alias)
                        )
                    """
                    )

                    # For each user, insert or update their signals
                    for user_alias, signals in _user_signals.items():
                        # Skip users with no signals
                        if not any(signals.values()):
                            continue

                        # Convert to JSON-compatible format
                        json_data = {k: dict(v) for k, v in signals.items() if v}

                        # Get last active timestamp
                        last_active = _user_last_active.get(user_alias)

                        # Get promotion status
                        promotion_status = _promotion_status.get(user_alias, False)

                        # Insert or update
                        cur.execute(
                            """
                            INSERT INTO user_cold_start_signals
                                (user_alias, signal_data, promotion_status, last_active, updated_at)
                            VALUES (%s, %s, %s, to_timestamp(%s), CURRENT_TIMESTAMP)
                            ON CONFLICT (user_alias) 
                            DO UPDATE SET 
                                signal_data = %s,
                                promotion_status = %s,
                                last_active = to_timestamp(%s),
                                updated_at = CURRENT_TIMESTAMP
                        """,
                            (
                                user_alias,
                                json.dumps(json_data),
                                promotion_status,
                                last_active or now,
                                json.dumps(json_data),
                                promotion_status,
                                last_active or now,
                            ),
                        )

                    conn.commit()

                    logger.info(
                        f"Exported {len(_user_signals)} user signal profiles to database"
                    )
                    return True

    except Exception as e:
        logger.error(f"Error exporting user signals to database: {e}")
        return False


def import_user_signals_from_db() -> bool:
    """
    Import user signals from database to memory cache on service startup.

    This restores user preference data after a service restart, allowing
    for continuous personalization across service deployments.

    Returns:
        bool: True if successful, False on error
    """
    try:
        with _signal_lock:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Check if table exists
                    cur.execute(
                        """
                        SELECT to_regclass('user_cold_start_signals')
                    """
                    )

                    table_exists = cur.fetchone()[0] is not None

                    if not table_exists:
                        logger.info("No user_cold_start_signals table exists yet")
                        return True

                    # Fetch all user signals
                    cur.execute(
                        """
                        SELECT user_alias, signal_data, promotion_status, 
                               extract(epoch from last_active)
                        FROM user_cold_start_signals
                    """
                    )

                    rows = cur.fetchall()

                    # Import each user's data
                    for user_alias, signal_data, promotion_status, last_active in rows:
                        # Parse JSON data
                        signal_dict = json.loads(signal_data)

                        # Convert to Counter objects
                        _user_signals[user_alias] = {
                            k: Counter(v) for k, v in signal_dict.items()
                        }

                        # Set promotion status
                        _promotion_status[user_alias] = promotion_status

                        # Set last active timestamp
                        _user_last_active[user_alias] = last_active

                    logger.info(
                        f"Imported {len(rows)} user signal profiles from database"
                    )
                    return True

    except Exception as e:
        logger.error(f"Error importing user signals from database: {e}")
        return False
