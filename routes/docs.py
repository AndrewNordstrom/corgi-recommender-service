"""
API Documentation routes for the Corgi Recommender Service.

This module provides routes for accessing the API documentation using Swagger UI and ReDoc.
It serves the OpenAPI specification and configures interactive documentation interfaces.
"""

import os
import yaml
import json
import logging
from flask import (
    Blueprint,
    jsonify,
    current_app,
    send_from_directory,
    render_template_string,
    request,
    redirect,
)
from flask_swagger_ui import get_swaggerui_blueprint
from config import API_PREFIX

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
docs_bp = Blueprint("docs", __name__)

# Define OpenAPI specification path
SWAGGER_URL = f"{API_PREFIX}/docs"
API_URL = f"{API_PREFIX}/docs/spec"
REDOC_URL = f"{API_PREFIX}/docs/redoc"
STATIC_URL = f"{API_PREFIX}/docs/static"
OPENAPI_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "openapi.yaml")
SWAGGER_UI_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static", "swagger-ui"
)
ROOT_PATH = os.path.dirname(os.path.dirname(__file__))

# Create a swagger UI blueprint
swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        "app_name": "Corgi Recommender Service API",
        "dom_id": "#swagger-ui",
        "deepLinking": True,
        "syntaxHighlight.theme": "monokai",
        "displayRequestDuration": True,
        "defaultModelsExpandDepth": 3,
        "docExpansion": "list",
    },
)


@docs_bp.route("/spec", methods=["GET"])
def get_api_spec():
    """
    Return the OpenAPI specification as JSON.

    This endpoint serves the complete OpenAPI specification that describes
    all available endpoints, parameters, and response formats. It is used by
    the Swagger UI and ReDoc interfaces to generate the documentation.
    """
    try:
        with open(OPENAPI_PATH, "r") as f:
            spec = yaml.safe_load(f)

        # Add base URL if it's not already set
        if "servers" not in spec or not spec["servers"]:
            host_url = request.host_url.rstrip("/")
            spec["servers"] = [{"url": host_url, "description": "Current server"}]

        return jsonify(spec)
    except Exception as e:
        logger.error(f"Error loading OpenAPI spec: {e}")
        return jsonify({"error": "Failed to load API specification"}), 500


@docs_bp.route("/redoc", methods=["GET"])
def redoc():
    """
    Serve ReDoc API documentation.

    ReDoc provides an alternative documentation UI that is more user-friendly
    for API consumers. It uses the same OpenAPI specification as Swagger UI.
    """
    redoc_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Corgi Recommender Service API Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        <style>
            body {
                margin: 0;
                padding: 0;
            }
            
            .api-info {
                padding: 10px 20px;
                background-color: #f8f8f8;
                border-bottom: 1px solid #e1e1e1;
            }
            
            .api-info h2 {
                margin-top: 0;
            }
        </style>
    </head>
    <body>
        <div class="api-info">
            <h2>Corgi Recommender Service API Documentation</h2>
            <p>Interactive documentation for the Corgi Recommender Service API.</p>
        </div>
        <redoc spec-url="{{ spec_url }}"></redoc>
        <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"> </script>
    </body>
    </html>
    """
    return render_template_string(redoc_html, spec_url=API_URL)


@docs_bp.route("/", methods=["GET"])
def docs_index():
    """
    Documentation index page.

    Provides links to both Swagger UI and ReDoc interfaces, allowing users
    to choose their preferred documentation format.
    """
    index_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Corgi Recommender Service API Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        <style>
            body {
                font-family: 'Roboto', sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f8f8f8;
                color: #333;
            }
            
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .header {
                text-align: center;
                margin-bottom: 40px;
                padding: 20px;
                background-color: #FF9A3C;
                color: white;
                border-radius: 8px;
            }
            
            .header h1 {
                margin-top: 0;
            }
            
            .doc-links {
                display: flex;
                justify-content: space-around;
                margin-top: 30px;
            }
            
            .doc-option {
                flex: 1;
                max-width: 350px;
                margin: 0 15px;
                padding: 20px;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                text-align: center;
            }
            
            .doc-option h2 {
                color: #FF9A3C;
            }
            
            .doc-option p {
                margin-bottom: 20px;
                color: #666;
            }
            
            .button {
                display: inline-block;
                padding: 10px 20px;
                background-color: #FF9A3C;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-weight: 500;
            }
            
            .button:hover {
                background-color: #e67e00;
            }
            
            .footer {
                margin-top: 40px;
                text-align: center;
                color: #666;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Corgi Recommender Service API</h1>
                <p>Complete API documentation for developers</p>
            </div>
            
            <div class="doc-links">
                <div class="doc-option">
                    <h2>Swagger UI</h2>
                    <p>Interactive documentation with a focus on request building and testing. Best for API exploration and direct API testing.</p>
                    <a href="{{ swagger_url }}" class="button">Open Swagger UI</a>
                </div>
                <div class="doc-option">
                    <h2>ReDoc</h2>
                    <p>Clean, responsive documentation with clear request/response examples. Ideal for reading and understanding the API.</p>
                    <a href="{{ redoc_url }}" class="button">Open ReDoc</a>
                </div>
            </div>
            
            <div class="footer">
                <p>Corgi Recommender Service &copy; 2025</p>
                <p>API Specification: <a href="{{ spec_url }}">OpenAPI JSON</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(
        index_html, swagger_url=SWAGGER_URL, redoc_url=REDOC_URL, spec_url=API_URL
    )


@docs_bp.route("/static/<path:filename>")
def serve_static(filename):
    """
    Serve static files for the documentation interfaces.

    This endpoint serves static assets needed by the documentation interfaces,
    such as CSS, JavaScript, and images.
    """
    try:
        return send_from_directory(SWAGGER_UI_PATH, filename)
    except:
        return "File not found", 404


def register_docs_routes(app):
    """
    Register the API documentation routes with the Flask app.

    This function sets up the documentation routes and configures the Swagger UI
    and ReDoc interfaces.

    Args:
        app: The Flask application instance
    """
    # Ensure the swagger-ui directory exists
    os.makedirs(SWAGGER_UI_PATH, exist_ok=True)

    # Register the Swagger UI blueprint
    app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

    # Register the API documentation blueprint
    app.register_blueprint(docs_bp, url_prefix=SWAGGER_URL)

    # Add a redirect from the API root to the docs
    @app.route(f"{API_PREFIX}")
    def api_root_redirect():
        return redirect(SWAGGER_URL)

    logger.info(f"API documentation registered at {SWAGGER_URL}")
    logger.info(f"ReDoc documentation registered at {REDOC_URL}")
