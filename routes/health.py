"""
Health check routes for the Corgi Recommender Service.

This module provides endpoints for monitoring the health and status
of the service.
"""

import logging
from flask import Blueprint, jsonify
import psycopg2
import os
import socket
import platform
from datetime import datetime

from config import API_PREFIX, DB_CONFIG, HEALTH_CHECK_TIMEOUT
from db.connection import get_db_connection, USE_IN_MEMORY_DB
from utils.logging_decorator import log_route

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint - no prefix to allow health checks at root level
health_bp = Blueprint("health", __name__)


@health_bp.route("/")
@health_bp.route("/health")
@health_bp.route(f"{API_PREFIX}/health")
@log_route
def health_check():
    """
    Health check endpoint that verifies connectivity to all required services.

    Returns:
        200 OK if all systems are operational
        500 Error if any dependencies are unavailable
    """
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": os.getenv("APP_VERSION", "dev"),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "database": "unknown",
    }

    # Check database connectivity
    try:
        with get_db_connection() as conn:
            if USE_IN_MEMORY_DB:
                # SQLite doesn't use context manager for cursor
                cur = conn.cursor()
                cur.execute("SELECT 1")
                result = cur.fetchone()
                cur.close()
                status["database"] = "connected (SQLite in-memory)"
                status["database_config"] = {"type": "SQLite", "mode": "in-memory"}
            else:
                # PostgreSQL uses context manager for cursor
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    status["database"] = "connected"
                    status["database_config"] = {
                        "host": DB_CONFIG["host"],
                        "dbname": DB_CONFIG["dbname"],
                        "user": DB_CONFIG["user"],
                    }
    except Exception as e:
        logger.error(f"Health check failed: Database connection error: {e}")
        status["status"] = "unhealthy"
        status["database"] = "disconnected"
        status["database_error"] = str(e)
        return jsonify(status), 500

    return jsonify(status)


@health_bp.route(f"{API_PREFIX}/metrics/flush", methods=["POST"])
@log_route
def flush_metrics():
    """
    Force a flush of all metrics to their respective outputs.

    This is primarily for debugging and testing purposes.

    Returns:
        200 OK if metrics were successfully flushed
        500 Error if there was a problem flushing metrics
    """
    try:
        # Import and call the force_metrics_flush function
        from utils.metrics import force_metrics_flush

        success = force_metrics_flush()

        if success:
            return jsonify(
                {
                    "status": "success",
                    "message": "Metrics successfully flushed",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Error flushing metrics",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )
    except Exception as e:
        logger.error(f"Error in metrics flush endpoint: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Exception flushing metrics: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )
