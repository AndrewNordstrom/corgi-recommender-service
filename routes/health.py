"""
Health check endpoint for the Corgi Recommender Service.

This module provides health status information for monitoring and deployment.
"""

import logging
import socket
from datetime import datetime
from flask import Blueprint, jsonify

from db.connection import get_db_connection

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
@health_bp.route("/", methods=["GET"])
@health_bp.route("/api/v1/health", methods=["GET"])
def health():
    """
    Health check endpoint.
    
    Returns:
        200 OK with health status (sanitized for security)
        503 Service Unavailable if database connection fails
    """
    try:
        # Test database connection
        with get_db_connection() as conn:
            if conn:
                database_status = "connected"
            else:
                database_status = "disconnected"
                
        # Return sanitized health information (removed sensitive details)
        return jsonify({
            "status": "healthy",
            "database": database_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",  # ISO format with UTC
            "service": "corgi-recommender",
            "hostname": socket.gethostname()
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "database": "error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "corgi-recommender"
        }), 503


# Metrics endpoint removed for security hardening
# Only essential health information is exposed
