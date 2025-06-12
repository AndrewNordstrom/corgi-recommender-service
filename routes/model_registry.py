"""
Model Registry API Routes

This module provides REST API endpoints for managing the model registry,
including model registration, deployment, A/B testing, and performance monitoring.

Endpoints:
- GET /api/v1/models - List available models
- POST /api/v1/models - Register a new model
- GET /api/v1/models/{name} - Get model details
- PUT /api/v1/models/{name}/{version}/status - Update model status
- POST /api/v1/models/hybrid - Create hybrid model
- GET /api/v1/experiments - List A/B tests
- POST /api/v1/experiments - Create A/B test
- GET /api/v1/performance - Get performance metrics
- POST /api/v1/performance - Log performance metrics
- GET /api/v1/health - Registry health check
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest, NotFound, Conflict

from core.recommender_factory import get_factory
from core.model_registry import ModelType, ModelStatus
from utils.auth import require_authentication as require_auth
from utils.logging_decorator import log_route

logger = logging.getLogger(__name__)

# Create blueprint
model_registry_bp = Blueprint('model_registry', __name__, url_prefix='/api/v1/models')

@model_registry_bp.route('', methods=['GET'])
@log_route
def list_models():
    """
    List all available models.
    
    Query Parameters:
    - status: Filter by model status (experimental, staging, production, etc.)
    - type: Filter by model type
    - author: Filter by author
    """
    try:
        factory = get_factory()
        
        # Get query parameters
        status_filter = request.args.get('status')
        type_filter = request.args.get('type')
        author_filter = request.args.get('author')
        
        # Parse status filter
        status = None
        if status_filter:
            try:
                status = ModelStatus(status_filter.lower())
            except ValueError:
                return jsonify({"error": f"Invalid status: {status_filter}"}), 400
        
        # Get models
        models = factory.list_available_models(status)
        
        # Apply additional filters
        if type_filter:
            models = [m for m in models if m['type'].lower() == type_filter.lower()]
        
        if author_filter:
            models = [m for m in models if author_filter.lower() in m['author'].lower()]
        
        return jsonify({
            "models": models,
            "total": len(models),
            "filters": {
                "status": status_filter,
                "type": type_filter,
                "author": author_filter
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({"error": "Failed to list models"}), 500

@model_registry_bp.route('', methods=['POST'])
@require_auth
@log_route
def register_model():
    """
    Register a new model.
    
    Request Body:
    {
        "name": "model_name",
        "version": "1.0",
        "type": "neural_collaborative",
        "author": "researcher@university.edu",
        "description": "Neural collaborative filtering model",
        "config": {...},
        "performance_metrics": {...},
        "status": "experimental",
        "code_reference": "path.to.model.class",
        "paper_reference": "https://...",
        "tags": ["neural", "collaborative"]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        # Validate required fields
        required_fields = ["name", "version", "author", "code_reference"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        factory = get_factory()
        
        # Parse model type
        model_type = ModelType.CUSTOM
        if 'type' in data:
            try:
                model_type = ModelType(data['type'].lower())
            except ValueError:
                return jsonify({"error": f"Invalid model type: {data['type']}"}), 400
        
        # Parse status
        status = ModelStatus.EXPERIMENTAL
        if 'status' in data:
            try:
                status = ModelStatus(data['status'].lower())
            except ValueError:
                return jsonify({"error": f"Invalid status: {data['status']}"}), 400
        
        # For now, we can only register models by code reference
        # In a real system, you might also support file uploads
        if 'code_reference' not in data:
            return jsonify({"error": "code_reference is required for model registration"}), 400
        
        # Create a placeholder model instance (would be replaced by actual instantiation)
        class PlaceholderModel:
            def __init__(self, config):
                self.config = config
            
            def generate_rankings_for_user(self, user_id: str):
                # This would be replaced by the actual model implementation
                return []
        
        model_instance = PlaceholderModel(data.get('config', {}))
        
        # Register the model
        success = factory.register_model(
            name=data['name'],
            model_instance=model_instance,
            version=data['version'],
            model_type=model_type,
            author=data['author'],
            description=data.get('description', ''),
            config=data.get('config', {}),
            performance_metrics=data.get('performance_metrics', {}),
            status=status,
            paper_reference=data.get('paper_reference'),
            code_reference=data['code_reference'],
            tags=data.get('tags', [])
        )
        
        if success:
            return jsonify({
                "message": f"Model {data['name']}:{data['version']} registered successfully",
                "model": {
                    "name": data['name'],
                    "version": data['version'],
                    "status": status.value
                }
            }), 201
        else:
            return jsonify({"error": "Failed to register model"}), 500
            
    except Exception as e:
        logger.error(f"Error registering model: {e}")
        return jsonify({"error": "Failed to register model"}), 500

@model_registry_bp.route('/<name>', methods=['GET'])
@log_route
def get_model_details(name: str):
    """
    Get detailed information about a specific model.
    
    Query Parameters:
    - version: Specific version (defaults to latest)
    """
    try:
        factory = get_factory()
        version = request.args.get('version')
        
        # Get model metadata
        registry = factory.registry
        metadata = registry.get_model_metadata(name, version)
        
        if not metadata:
            return jsonify({"error": f"Model {name} not found"}), 404
        
        # Get performance history
        performance_comparison = registry.get_performance_comparison(
            [(name, metadata.version)],
            start_time=datetime.utcnow() - timedelta(days=30)
        )
        
        model_details = {
            "name": metadata.name,
            "version": metadata.version,
            "type": metadata.model_type.value,
            "status": metadata.status.value,
            "author": metadata.author,
            "description": metadata.description,
            "config": metadata.config,
            "performance_metrics": metadata.performance_metrics,
            "created_at": metadata.created_at.isoformat(),
            "updated_at": metadata.updated_at.isoformat(),
            "model_size_bytes": metadata.model_size_bytes,
            "inference_time_ms": metadata.inference_time_ms,
            "memory_usage_mb": metadata.memory_usage_mb,
            "dependencies": metadata.dependencies,
            "tags": metadata.tags,
            "paper_reference": metadata.paper_reference,
            "code_reference": metadata.code_reference,
            "recent_performance": performance_comparison.get(f"{name}:{metadata.version}", {})
        }
        
        return jsonify(model_details)
        
    except Exception as e:
        logger.error(f"Error getting model details: {e}")
        return jsonify({"error": "Failed to get model details"}), 500

@model_registry_bp.route('/<name>/<version>/status', methods=['PUT'])
@require_auth
@log_route
def update_model_status(name: str, version: str):
    """
    Update model status (e.g., promote to production).
    
    Request Body:
    {
        "status": "production"
    }
    """
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({"error": "Status is required"}), 400
        
        # Parse status
        try:
            new_status = ModelStatus(data['status'].lower())
        except ValueError:
            return jsonify({"error": f"Invalid status: {data['status']}"}), 400
        
        factory = get_factory()
        
        if new_status == ModelStatus.PRODUCTION:
            # Use the promotion method which handles retiring old production models
            success = factory.promote_model_to_production(name, version)
        else:
            # Regular status update
            success = factory.registry.update_model_status(name, version, new_status)
        
        if success:
            return jsonify({
                "message": f"Model {name}:{version} status updated to {new_status.value}",
                "model": {
                    "name": name,
                    "version": version,
                    "status": new_status.value
                }
            })
        else:
            return jsonify({"error": "Failed to update model status"}), 500
            
    except Exception as e:
        logger.error(f"Error updating model status: {e}")
        return jsonify({"error": "Failed to update model status"}), 500

@model_registry_bp.route('/hybrid', methods=['POST'])
@require_auth
@log_route
def create_hybrid_model():
    """
    Create a hybrid model from existing models.
    
    Request Body:
    {
        "name": "hybrid_model_v1",
        "version": "1.0",
        "component_models": [
            ["neural_cf", "1.0"],
            ["simple", "1.0"]
        ],
        "weights": [0.7, 0.3],
        "author": "researcher@university.edu",
        "description": "Hybrid of neural CF and simple model"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        # Validate required fields
        required_fields = ["name", "component_models", "author"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        factory = get_factory()
        
        # Create hybrid model
        success = factory.create_hybrid_model(
            name=data['name'],
            component_models=data['component_models'],
            weights=data.get('weights'),
            version=data.get('version', '1.0'),
            author=data['author'],
            description=data.get('description', '')
        )
        
        if success:
            return jsonify({
                "message": f"Hybrid model {data['name']} created successfully",
                "model": {
                    "name": data['name'],
                    "version": data.get('version', '1.0'),
                    "component_models": data['component_models'],
                    "weights": data.get('weights')
                }
            }), 201
        else:
            return jsonify({"error": "Failed to create hybrid model"}), 500
            
    except Exception as e:
        logger.error(f"Error creating hybrid model: {e}")
        return jsonify({"error": "Failed to create hybrid model"}), 500

# A/B Testing endpoints
experiments_bp = Blueprint('experiments', __name__, url_prefix='/api/v1/experiments')

@experiments_bp.route('', methods=['GET'])
@log_route
def list_experiments():
    """List all A/B testing experiments."""
    try:
        # This would be implemented to fetch from database
        # For now, return empty list
        return jsonify({
            "experiments": [],
            "total": 0
        })
        
    except Exception as e:
        logger.error(f"Error listing experiments: {e}")
        return jsonify({"error": "Failed to list experiments"}), 500

@experiments_bp.route('', methods=['POST'])
@require_auth
@log_route
def create_experiment():
    """
    Create a new A/B testing experiment.
    
    Request Body:
    {
        "experiment_id": "neural_cf_vs_simple",
        "models": {
            "neural_cf:1.0": 50.0,
            "simple:1.0": 50.0
        },
        "user_segments": ["power_users"],
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-31T23:59:59Z"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        # Validate required fields
        required_fields = ["experiment_id", "models"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        factory = get_factory()
        
        # Parse timestamps
        start_time = None
        end_time = None
        
        if 'start_time' in data:
            try:
                start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid start_time format"}), 400
        
        if 'end_time' in data:
            try:
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid end_time format"}), 400
        
        # Create A/B test
        success = factory.set_a_b_test(
            experiment_id=data['experiment_id'],
            models=data['models'],
            user_segments=data.get('user_segments'),
            start_time=start_time,
            end_time=end_time
        )
        
        if success:
            return jsonify({
                "message": f"Experiment {data['experiment_id']} created successfully",
                "experiment": {
                    "experiment_id": data['experiment_id'],
                    "models": data['models'],
                    "user_segments": data.get('user_segments'),
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None
                }
            }), 201
        else:
            return jsonify({"error": "Failed to create experiment"}), 500
            
    except Exception as e:
        logger.error(f"Error creating experiment: {e}")
        return jsonify({"error": "Failed to create experiment"}), 500

# Performance monitoring endpoints
performance_bp = Blueprint('performance', __name__, url_prefix='/api/v1/performance')

@performance_bp.route('', methods=['GET'])
@log_route
def get_performance_metrics():
    """
    Get performance metrics for models.
    
    Query Parameters:
    - models: Comma-separated list of model:version specs
    - start_time: Start time for metrics (ISO format)
    - end_time: End time for metrics (ISO format)
    - user_segment: User segment filter
    """
    try:
        factory = get_factory()
        
        # Parse query parameters
        models_param = request.args.get('models', '')
        start_time_param = request.args.get('start_time')
        end_time_param = request.args.get('end_time')
        user_segment = request.args.get('user_segment')
        
        # Parse models
        models = []
        if models_param:
            for model_spec in models_param.split(','):
                if ':' in model_spec:
                    name, version = model_spec.strip().split(':', 1)
                    models.append((name, version))
                else:
                    models.append((model_spec.strip(), None))
        
        # Parse timestamps
        start_time = None
        end_time = None
        
        if start_time_param:
            try:
                start_time = datetime.fromisoformat(start_time_param.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid start_time format"}), 400
        
        if end_time_param:
            try:
                end_time = datetime.fromisoformat(end_time_param.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid end_time format"}), 400
        
        # Get performance comparison
        comparison = factory.get_model_performance_comparison(
            models, start_time, end_time, user_segment
        )
        
        return jsonify({
            "performance_metrics": comparison,
            "query": {
                "models": models_param,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "user_segment": user_segment
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({"error": "Failed to get performance metrics"}), 500

@performance_bp.route('', methods=['POST'])
@require_auth
@log_route
def log_performance():
    """
    Log performance metrics for a model.
    
    Request Body:
    {
        "model_name": "neural_cf",
        "version": "1.0",
        "metrics": {
            "precision_at_10": 0.85,
            "recall_at_10": 0.72,
            "ndcg": 0.78
        },
        "user_segment": "power_users",
        "a_b_test_id": "neural_cf_vs_simple",
        "sample_size": 1000
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        # Validate required fields
        required_fields = ["model_name", "version", "metrics"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        factory = get_factory()
        
        # Log performance
        factory.log_model_performance(
            name=data['model_name'],
            version=data['version'],
            metrics=data['metrics'],
            user_segment=data.get('user_segment'),
            a_b_test_id=data.get('a_b_test_id'),
            sample_size=data.get('sample_size')
        )
        
        return jsonify({
            "message": "Performance metrics logged successfully",
            "logged": {
                "model": f"{data['model_name']}:{data['version']}",
                "metrics": list(data['metrics'].keys()),
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error logging performance: {e}")
        return jsonify({"error": "Failed to log performance metrics"}), 500

# Health check endpoint
health_bp = Blueprint('registry_health', __name__, url_prefix='/api/v1/registry')

@health_bp.route('/health', methods=['GET'])
@log_route
def registry_health_check():
    """Get health status of the model registry."""
    try:
        factory = get_factory()
        health_status = factory.health_check()
        
        status_code = 200 if health_status.get("factory_status") == "healthy" else 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Error in registry health check: {e}")
        return jsonify({
            "factory_status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503

def register_model_registry_routes(app):
    """Register all model registry routes with the Flask app."""
    app.register_blueprint(model_registry_bp)
    app.register_blueprint(experiments_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(health_bp) 