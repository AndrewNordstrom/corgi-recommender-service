"""
User follows utility module for the Corgi Recommender Service.

This module provides functions for checking if a user follows other accounts
and retrieving follow relationships.
"""

import logging
import json
import requests
from flask import g

from utils.privacy import generate_user_alias
from routes.proxy import get_user_instance, get_user_by_token

logger = logging.getLogger(__name__)


def user_follows_anyone(user_token: str) -> bool:
    """Check if a user follows any accounts on their Mastodon instance.

    This function is a critical part of the cold start strategy. It determines
    whether a user should receive curated cold start content or their regular
    timeline by checking if they follow at least one account.

    The function makes an API call to the user's Mastodon instance to retrieve
    their following list with a limit of 1 (for efficiency).

    Args:
        user_token (str): The user's OAuth access token for authentication

    Returns:
        bool: True if the user follows at least one account, False if they follow no one.
              Defaults to True on any errors to avoid incorrectly triggering cold start.

    Note:
        This function defaults to True (assuming user follows someone) in case of
        any errors or exceptions to ensure users don't incorrectly get cold start
        content when they should see their regular timeline.
    """
    try:
        # Get user info to determine instance
        user_info = get_user_by_token(user_token)
        if not user_info:
            logger.warning("Cannot determine if user follows anyone: no user info")
            return True  # Default to true (assume they follow someone) to avoid cold start in case of errors

        instance_url = user_info["instance_url"]

        # Request the following accounts from Mastodon API (limit=1 for efficiency)
        headers = {"Authorization": f"Bearer {user_token}"}
        url = f"{instance_url}/api/v1/accounts/{user_info.get('mastodon_id', 'me')}/following?limit=1"

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            following = response.json()
            return len(following) > 0
        else:
            logger.warning(f"Failed to check following status: {response.status_code}")
            # On error, default to assuming user follows someone
            return True

    except Exception as e:
        logger.error(f"Error checking if user follows anyone: {e}")
        # On error, default to assuming user follows someone
        return True


def log_cold_start_interaction(user_token, post_id, action_type, is_test_mode=False):
    """Log and track user interactions with cold start content.

    This function records when users interact with cold start posts (liking,
    reblogging, etc.), which helps measure the effectiveness of different
    content types and categories in engaging new users.

    The interactions are logged to a dedicated cold_start_interactions.log file
    to enable separate analysis of cold start engagement patterns.

    Args:
        user_token (str): The user's OAuth access token
        post_id (str): ID of the cold start post being interacted with
                      (usually starts with 'cold_start_post_')
        action_type (str): Type of interaction (e.g., 'favorite', 'reblog', 'bookmark')
        is_test_mode (bool, optional): Whether this interaction is from test mode.
                                     Defaults to False.

    Returns:
        None

    Note:
        The function uses the user's pseudonymized ID rather than their actual ID
        in the logs to maintain privacy while still enabling engagement analysis.
    """
    request_id = getattr(g, "request_id", "unknown")
    user_info = get_user_by_token(user_token)

    if not user_info:
        logger.warning(
            f"REQ-{request_id} | Cannot log cold start interaction: no user info"
        )
        return

    user_id = user_info["user_id"]
    user_alias = generate_user_alias(user_id)

    # Create the log entry
    cold_start_logger = logging.getLogger("cold_start_interactions")
    cold_start_logger.info(
        f"{user_alias} | {post_id} | {action_type} | "
        + f"test_mode={is_test_mode} | request_id={request_id}"
    )

    logger.info(
        f"REQ-{request_id} | Logged cold start interaction: User={user_alias}, Post={post_id}, Action={action_type}"
    )
