"""
Logging decorator module for the Corgi Recommender Service.

This module provides a decorator for route functions to add consistent
logging and error handling.
"""

import logging
import time
import traceback
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)


def log_route(f):
    """
    Decorator to add logging and error handling to route functions.

    Usage:
        @app.route('/my-route')
        @log_route
        def my_route():
            # Your route code here

    Features:
        - Logs incoming request details
        - Logs function execution time
        - Catches and logs exceptions
        - Returns standardized error responses for exceptions
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()

        # Log request details
        logger.info(f"Request received: {request.method} {request.path}")
        logger.debug(f"Request headers: {dict(request.headers)}")

        if request.data:
            try:
                logger.debug(f"Request data: {request.get_json()}")
            except:
                logger.debug(f"Request data (raw): {request.data}")

        try:
            # Execute the route function
            result = f(*args, **kwargs)

            # Log execution time
            execution_time = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {request.path} in {execution_time:.3f}s"
            )

            return result
        except Exception as e:
            # Log the exception
            logger.error(f"Error in {f.__name__}: {str(e)}")
            logger.error(traceback.format_exc())

            # Return error response
            execution_time = time.time() - start_time
            logger.info(
                f"Request failed: {request.method} {request.path} in {execution_time:.3f}s"
            )

            return (
                jsonify(
                    {"error": "An internal server error occurred", "status": "error"}
                ),
                500,
            )

    return decorated_function


# Alias for API routes - same functionality as log_route
log_api_call = log_route
