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

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
privacy_bp = Blueprint("privacy", __name__)


@privacy_bp.route("", methods=["GET"])
@log_route
def get_privacy():
    """
    Get privacy settings for a user.

    Query parameters:
        user_id: ID of the user to get settings for

    Returns:
        200 OK with privacy settings
        400 Bad Request if user_id is missing
        500 Server Error on failure
    """
    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"error": "Missing required parameter: user_id"}), 400

    with get_db_connection() as conn:
        tracking_level = get_user_privacy_level(conn, user_id)

    return jsonify({"user_id": user_id, "tracking_level": tracking_level})


@privacy_bp.route("", methods=["POST"])
@log_route
def update_privacy():
    """
    Update privacy settings for a user.

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
    data = request.json

    # Validate required fields
    user_id = data.get("user_id")
    tracking_level = data.get("tracking_level")

    if not user_id:
        return jsonify({"error": "Missing required field: user_id"}), 400

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
