"""
OAuth routes for the Corgi Recommender Service.

This module provides basic OAuth flows for Mastodon integration.
These are placeholder scaffold implementations for Phase 3.
"""

import os
import logging
import secrets
import json
import time
from flask import Blueprint, request, redirect, url_for, jsonify, session, current_app
from utils.logging_decorator import log_route

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
oauth_bp = Blueprint("oauth", __name__)

# In-memory store for auth states and tokens (would be in a database in production)
# These are only for development/testing; production should use a proper database
auth_states = {}


# Add proper token expiration handling
class TokenStore:
    def __init__(self):
        self.tokens = {}
        self.expiry_time = 3600  # 1 hour default token expiry

    def store_token(self, token, data):
        """Store a token with expiration time"""
        expiry = int(time.time()) + self.expiry_time
        self.tokens[token] = {**data, "expires_at": expiry}
        return expiry

    def get_token(self, token):
        """Get token data if it exists and is not expired"""
        if token not in self.tokens:
            return None

        token_data = self.tokens[token]
        current_time = int(time.time())

        # Check if token is expired
        if current_time > token_data.get("expires_at", 0):
            # Token is expired, remove it
            self.remove_token(token)
            return None

        return token_data

    def remove_token(self, token):
        """Remove a token"""
        if token in self.tokens:
            del self.tokens[token]
            return True
        return False

    def cleanup_expired(self):
        """Clean up all expired tokens"""
        current_time = int(time.time())
        expired_tokens = [
            token
            for token, data in self.tokens.items()
            if current_time > data.get("expires_at", 0)
        ]

        for token in expired_tokens:
            self.remove_token(token)

        return len(expired_tokens)


# Initialize token store
auth_tokens = TokenStore()


@oauth_bp.route("/connect", methods=["GET"])
@log_route
def oauth_connect():
    """
    Start the OAuth flow to connect to a Mastodon instance.

    This is a placeholder implementation for the MVP demo.
    """
    # Get the Mastodon instance from the request
    instance = request.args.get("instance", "mastodon.social")
    redirect_uri = request.args.get(
        "redirect_uri", url_for("oauth.callback", _external=True)
    )

    # Generate a state parameter to prevent CSRF
    state = secrets.token_urlsafe(16)

    # Store the state and instance
    auth_states[state] = {
        "instance": instance,
        "redirect_uri": redirect_uri,
        "created_at": str(
            int(os.path.getmtime(__file__))
        ),  # Use file modification time as timestamp
    }

    # Get client ID from environment variable with fallback for development
    client_id = os.getenv("OAUTH_CLIENT_ID", "")
    if not client_id:
        # Log a warning but allow development to proceed with a randomly generated ID
        logger.warning(
            "OAUTH_CLIENT_ID environment variable not set - using temporary ID for development only"
        )
        client_id = f"temp_{secrets.token_hex(8)}"

    # Construct the authorization URL
    auth_url = f"https://{instance}/oauth/authorize"
    auth_url += f"?client_id={client_id}"
    auth_url += f"&redirect_uri={redirect_uri}"
    auth_url += f"&response_type=code"
    auth_url += f"&state={state}"
    auth_url += f"&scope=read+write+follow"

    logger.info(f"Redirecting to Mastodon OAuth: {auth_url}")

    # In a real implementation, we would redirect to the auth URL
    # For the demo, return a JSON response with the URL
    return jsonify(
        {
            "status": "scaffold_implementation",
            "note": "This is a placeholder for Phase 3 OAuth implementation",
            "auth_url": auth_url,
            "state": state,
        }
    )


@oauth_bp.route("/callback", methods=["GET"])
@log_route
def callback():
    """
    Handle the OAuth callback from Mastodon.

    This is a placeholder implementation for the MVP demo.
    """
    # Get the authorization code and state from the query string
    code = request.args.get("code")
    state = request.args.get("state")

    # Validate the state parameter
    if not state or state not in auth_states:
        logger.error(f"Invalid OAuth state: {state}")
        return jsonify({"error": "Invalid OAuth state"}), 400

    # Get the stored state data
    state_data = auth_states.pop(state)
    instance = state_data["instance"]

    # In a real implementation, exchange the code for an access token
    # For the demo, generate a fake token
    access_token = f"demo_token_{secrets.token_hex(8)}"

    # Store the token with expiration
    user_id = f"demo_user_{secrets.token_hex(4)}"
    token_data = {
        "instance": instance,
        "user_id": user_id,
        "created_at": int(time.time()),
    }
    expiry = auth_tokens.store_token(access_token, token_data)

    logger.info(f"OAuth flow completed for instance: {instance}")

    # Return the token with expiry information
    return jsonify(
        {
            "status": "scaffold_implementation",
            "note": "This is a placeholder for Phase 3 OAuth implementation",
            "access_token": access_token,
            "token_type": "Bearer",
            "scope": "read write follow",
            "created_at": token_data["created_at"],
            "expires_at": expiry,
            "expires_in": auth_tokens.expiry_time,
        }
    )


# Only expose token listing endpoint in development environments for security
if os.getenv("FLASK_ENV") == "development":
    @oauth_bp.route("/tokens", methods=["GET"])
    @log_route
    def list_tokens():
        """
        List all stored tokens (for demo purposes only).

        This would not be present in a production implementation.
        """
        # Clean up expired tokens first
        expired_count = auth_tokens.cleanup_expired()
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired tokens")

        # For security, only return limited token information (no actual tokens)
        token_info = {
            token: {
                "user_id": data.get("user_id", "unknown"),
                "instance": data.get("instance", "unknown"),
                "created_at": data.get("created_at", 0),
                "expires_at": data.get("expires_at", 0),
                "is_valid": int(time.time()) < data.get("expires_at", 0),
            }
            for token, data in auth_tokens.tokens.items()
        }

        return jsonify(
            {
                "status": "scaffold_implementation",
                "note": "This is a placeholder for Phase 3 OAuth implementation",
                "tokens": token_info,
                "active_token_count": len(token_info),
            }
        )


@oauth_bp.route("/revoke", methods=["POST"])
@log_route
def revoke_token():
    """
    Revoke an OAuth token.

    This is a placeholder implementation for the MVP demo.
    """
    token = request.json.get("token")

    if not token:
        return jsonify({"error": "Missing token parameter"}), 400

    # Try to remove the token - returns True if token existed and was removed
    if auth_tokens.remove_token(token):
        logger.info(f"Token successfully revoked")
        return jsonify(
            {
                "status": "success",
                "note": "This is a placeholder for Phase 3 OAuth implementation",
                "message": "Token revoked successfully",
            }
        )
    else:
        # Token was not found or was already revoked
        logger.warning(f"Attempt to revoke non-existent token")
        return (
            jsonify(
                {"status": "warning", "message": "Token not found or already revoked"}
            ),
            404,
        )
