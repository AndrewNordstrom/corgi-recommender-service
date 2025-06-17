"""
Privacy routes for the Corgi Recommender Service.

This module provides endpoints for users to manage their privacy settings.
"""

import logging
from flask import Blueprint, request, jsonify

from db.connection import get_db_connection
from utils.privacy import (
    generate_user_alias,
    get_user_privacy_level,
    update_user_privacy_level,
)
from utils.logging_decorator import log_route
from utils.rbac import require_authentication, get_current_user

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
privacy_bp = Blueprint("privacy", __name__)


@privacy_bp.route("", methods=["GET"])
@log_route
@require_authentication
def get_privacy():
    """
    Get privacy settings for the authenticated user.

    Headers:
        Authorization: Bearer token for user authentication

    Returns:
        200 OK with privacy settings
        401 Unauthorized if token is invalid
        500 Server Error on failure
    """
    # Get user from the authentication decorator
    current_user = get_current_user()
    user_id = current_user.get("id")

    if not user_id:
        # This case should ideally not be reached if require_authentication works
        return jsonify({"error": "Could not identify authenticated user"}), 401

    with get_db_connection() as conn:
        tracking_level = get_user_privacy_level(conn, user_id)

    return jsonify({"user_id": user_id, "tracking_level": tracking_level})


@privacy_bp.route("", methods=["POST"])
@log_route
@require_authentication
def update_privacy():
    """
    Update privacy settings for the authenticated user.

    Request body:
    {
        "tracking_level": "full" | "limited" | "none"
    }

    Returns:
        200 OK if settings updated successfully
        400 Bad Request if required fields are missing or invalid
        500 Server Error on failure
    """
    data = request.json
    
    # Get user from the authentication decorator
    current_user = get_current_user()
    user_id = current_user.get("id")

    # Validate required fields
    tracking_level = data.get("tracking_level")

    if not user_id:
        # This case should not be reached due to the decorator
        return jsonify({"error": "Could not identify authenticated user"}), 401

    if not tracking_level:
        return jsonify({"error": "Missing required field: tracking_level"}), 400

    if tracking_level not in ["full", "limited", "none"]:
        return (
            jsonify(
                {
                    "error": "Invalid tracking_level value",
                    "valid_values": ["full", "limited", "none"],
                }
            ),
            400,
        )

    with get_db_connection() as conn:
        success = update_user_privacy_level(conn, user_id, tracking_level)

        if not success:
            return jsonify({"error": "Failed to update privacy settings"}), 500

    return jsonify(
        {"user_id": user_id, "tracking_level": tracking_level, "status": "ok"}
    )


@privacy_bp.route("/settings", methods=["GET"])
@log_route
def get_privacy_settings():
    """
    Legacy endpoint for getting privacy settings for a user.

    Query parameters:
        user_id: ID of the user to get settings for

    Returns:
        200 OK with privacy settings
        400 Bad Request if user_id is missing
        500 Server Error on failure
    """
    return get_privacy()


@privacy_bp.route("/settings", methods=["POST"])
@log_route
def update_privacy_settings():
    """
    Legacy endpoint for updating privacy settings for a user.

    Request body:
    {
        "user_id": "123",
        "tracking_level": "full" | "limited" | "none"
    }

    Returns:
        200 OK if settings updated successfully
        400 Bad Request if required fields are missing or invalid
        500 Server Error on failure
    """
    return update_privacy()
