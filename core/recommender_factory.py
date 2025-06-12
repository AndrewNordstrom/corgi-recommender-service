"""
Recommender Factory for Model Registry Integration

This module provides a factory interface for creating and managing recommendation
models, integrating the model registry with the existing Corgi recommendation system.

Features:
- Clean factory interface for model creation
- Integration with existing routes and APIs
- Automatic model selection based on configuration
- A/B testing support through the model registry
- Performance monitoring and health checks
- Backward compatibility with existing code
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime

from core.model_registry import get_registry, ModelRegistry, ModelType, ModelStatus
from core.recommender_base import (
    BaseRecommender, SimpleLegacyWrapper, HybridRecommender,
    create_simple_recommender, validate_recommender_interface
)
from config import ALGORITHM_CONFIG

logger = logging.getLogger(__name__)

class RecommenderFactory:
    """
    Factory for creating and managing recommendation models.
    
    This factory integrates with the model registry to provide a clean
    interface for model selection, A/B testing, and performance monitoring.
    """
    
    def __init__(self, registry: ModelRegistry = None):
        """
        Initialize the recommender factory.
        
        Args:
            registry: Model registry instance (defaults to global registry)
        """
        self.registry = registry or get_registry()
        self._default_model_name = ALGORITHM_CONFIG.get("default_model", "simple")
        self._fallback_model = None
        
        # Register the default simple model if not already registered
        self._ensure_default_models()
        
        logger.info("Recommender factory initialized")
    
    def _ensure_default_models(self):
        """Ensure default models are registered."""
        try:
            # Check if simple model is already registered
            if not self.registry.get_model_metadata("simple"):
                # Register the legacy simple model
                simple_model = create_simple_recommender()
                self.registry.register_model(
                    name="simple",
                    version="1.0",
                    model_instance=simple_model,
                    model_type=ModelType.SIMPLE,
                    author="corgi_system",
                    description="Default simple ranking algorithm",
                    config=ALGORITHM_CONFIG.copy(),
                    status=ModelStatus.PRODUCTION,
                    code_reference="core.ranking_algorithm.generate_rankings_for_user"
                )
                logger.info("Registered default simple model")
                
        except Exception as e:
            logger.warning(f"Could not register default models: {e}")
    
    def get_recommender_for_user(
        self, 
        user_id: str, 
        user_segment: str = None,
        model_name: str = None,
        version: str = None
    ) -> BaseRecommender:
        """
        Get the appropriate recommender for a user.
        
        This method handles model selection based on:
        1. Explicit model specification
        2. A/B testing configuration
        3. User segmentation
        4. Default fallback
        
        Args:
            user_id: User ID
            user_segment: Optional user segment for targeted experiments
            model_name: Optional explicit model name
            version: Optional explicit model version
            
        Returns:
            BaseRecommender instance
        """
        try:
            # If explicit model is specified, use it
            if model_name:
                model_instance = self.registry.get_model(model_name, version)
                if not isinstance(model_instance, BaseRecommender):
                    # Wrap legacy models
                    model_instance = SimpleLegacyWrapper(
                        model_instance.generate_rankings_for_user,
                        {"name": model_name, "version": version or "unknown"}
                    )
                return model_instance
            
            # Otherwise, use registry's model selection (handles A/B testing)
            model_instance, model_spec = self.registry.get_model_for_user(
                user_id, user_segment, fallback_to_default=True
            )
            
            if not isinstance(model_instance, BaseRecommender):
                # Wrap legacy models
                model_instance = SimpleLegacyWrapper(
                    model_instance.generate_rankings_for_user,
                    {"name": model_spec}
                )
            
            return model_instance
            
        except Exception as e:
            logger.error(f"Failed to get recommender for user {user_id}: {e}")
            return self._get_fallback_recommender()
    
    def _get_fallback_recommender(self) -> BaseRecommender:
        """Get emergency fallback recommender."""
        if self._fallback_model is None:
            self._fallback_model = create_simple_recommender()
        return self._fallback_model
    
    def get_recommender_by_name(self, name: str, version: str = None) -> BaseRecommender:
        """
        Get a specific recommender by name and version.
        
        Args:
            name: Model name
            version: Model version (optional, defaults to latest production)
            
        Returns:
            BaseRecommender instance
        """
        try:
            model_instance = self.registry.get_model(name, version)
            
            if not isinstance(model_instance, BaseRecommender):
                # Wrap legacy models
                model_instance = SimpleLegacyWrapper(
                    model_instance.generate_rankings_for_user,
                    {"name": name, "version": version or "latest"}
                )
            
            return model_instance
            
        except Exception as e:
            logger.error(f"Failed to get recommender {name}:{version}: {e}")
            return self._get_fallback_recommender()
    
    def register_model(
        self,
        name: str,
        model_instance: Any,
        version: str = "1.0",
        model_type: ModelType = ModelType.CUSTOM,
        author: str = "unknown",
        description: str = "",
        config: Dict[str, Any] = None,
        performance_metrics: Dict[str, float] = None,
        status: ModelStatus = ModelStatus.EXPERIMENTAL,
        **kwargs
    ) -> bool:
        """
        Register a new model in the registry.
        
        Args:
            name: Model name
            model_instance: The model instance or class
            version: Model version
            model_type: Type of model
            author: Model author
            description: Model description
            config: Model configuration
            performance_metrics: Initial performance metrics
            status: Initial model status
            **kwargs: Additional metadata
            
        Returns:
            bool: True if registration successful
        """
        try:
            # Validate model interface
            if not validate_recommender_interface(model_instance):
                logger.error(f"Model {name} does not implement required interface")
                return False
            
            # Wrap in BaseRecommender if needed
            if not isinstance(model_instance, BaseRecommender):
                model_instance = SimpleLegacyWrapper(
                    model_instance.generate_rankings_for_user,
                    config or {}
                )
            
            # Register with the registry
            metadata = self.registry.register_model(
                name=name,
                version=version,
                model_instance=model_instance,
                model_type=model_type,
                author=author,
                description=description,
                config=config or {},
                performance_metrics=performance_metrics or {},
                status=status,
                **kwargs
            )
            
            logger.info(f"Successfully registered model {name}:{version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register model {name}: {e}")
            return False
    
    def create_hybrid_model(
        self,
        name: str,
        component_models: List[Tuple[str, str]],  # List of (model_name, version) tuples
        weights: List[float] = None,
        version: str = "1.0",
        **kwargs
    ) -> bool:
        """
        Create and register a hybrid model from existing models.
        
        Args:
            name: Name for the hybrid model
            component_models: List of (model_name, version) tuples
            weights: Weights for combining models (defaults to equal)
            version: Version for the hybrid model
            **kwargs: Additional registration parameters
            
        Returns:
            bool: True if creation successful
        """
        try:
            # Get component model instances
            models = []
            for model_name, model_version in component_models:
                model = self.get_recommender_by_name(model_name, model_version)
                models.append(model)
            
            # Create hybrid model
            hybrid_model = HybridRecommender(
                models=models,
                weights=weights,
                config={
                    "component_models": component_models,
                    "weights": weights or [1.0 / len(models)] * len(models)
                }
            )
            
            # Register the hybrid model
            return self.register_model(
                name=name,
                model_instance=hybrid_model,
                version=version,
                model_type=ModelType.ENSEMBLE,
                description=f"Hybrid model combining {len(models)} models",
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Failed to create hybrid model {name}: {e}")
            return False
    
    def set_a_b_test(
        self,
        experiment_id: str,
        models: Dict[str, float],  # model_name:version -> percentage
        user_segments: List[str] = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> bool:
        """
        Set up an A/B test between models.
        
        Args:
            experiment_id: Unique experiment identifier
            models: Dictionary mapping model specs to traffic percentages
            user_segments: Optional user segments to target
            start_time: When to start the experiment
            end_time: When to end the experiment
            
        Returns:
            bool: True if A/B test setup successful
        """
        try:
            return self.registry.set_traffic_split(
                experiment_id=experiment_id,
                model_configs=models,
                user_segments=user_segments,
                start_time=start_time,
                end_time=end_time
            )
        except Exception as e:
            logger.error(f"Failed to set A/B test {experiment_id}: {e}")
            return False
    
    def promote_model_to_production(self, name: str, version: str) -> bool:
        """
        Promote a model from experimental/staging to production.
        
        Args:
            name: Model name
            version: Model version
            
        Returns:
            bool: True if promotion successful
        """
        try:
            # First, demote current production models of the same name
            current_production = self.registry.list_models(status=ModelStatus.PRODUCTION)
            for model in current_production:
                if model.name == name:
                    self.registry.update_model_status(
                        model.name, model.version, ModelStatus.RETIRED
                    )
            
            # Promote the specified model
            return self.registry.update_model_status(name, version, ModelStatus.PRODUCTION)
            
        except Exception as e:
            logger.error(f"Failed to promote model {name}:{version}: {e}")
            return False
    
    def get_model_performance_comparison(
        self,
        models: List[Tuple[str, str]],
        start_time: datetime = None,
        end_time: datetime = None,
        user_segment: str = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Get performance comparison between models.
        
        Args:
            models: List of (model_name, version) tuples
            start_time: Start time for comparison period
            end_time: End time for comparison period
            user_segment: Optional user segment filter
            
        Returns:
            Dictionary with performance metrics for each model
        """
        return self.registry.get_performance_comparison(
            models, start_time, end_time, user_segment
        )
    
    def log_model_performance(
        self,
        name: str,
        version: str,
        metrics: Dict[str, float],
        user_segment: str = None,
        a_b_test_id: str = None,
        sample_size: int = None
    ):
        """
        Log performance metrics for a model.
        
        Args:
            name: Model name
            version: Model version
            metrics: Performance metrics dictionary
            user_segment: Optional user segment
            a_b_test_id: Optional A/B test identifier
            sample_size: Optional sample size
        """
        self.registry.log_performance(
            name, version, metrics, user_segment, a_b_test_id, sample_size
        )
    
    def list_available_models(self, status: ModelStatus = None) -> List[Dict[str, Any]]:
        """
        List all available models with their metadata.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of model metadata dictionaries
        """
        models = self.registry.list_models(status)
        return [
            {
                "name": model.name,
                "version": model.version,
                "type": model.model_type.value,
                "status": model.status.value,
                "author": model.author,
                "description": model.description,
                "capabilities": model.config.get("capabilities", []),
                "performance_metrics": model.performance_metrics,
                "created_at": model.created_at.isoformat(),
                "updated_at": model.updated_at.isoformat()
            }
            for model in models
        ]
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the factory and registry.
        
        Returns:
            Dictionary with health status
        """
        try:
            registry_health = self.registry.health_check()
            
            # Test default model
            default_model_health = {}
            try:
                default_model = self.get_recommender_by_name(self._default_model_name)
                default_model_health = default_model.health_check()
            except Exception as e:
                default_model_health = {"status": "unhealthy", "error": str(e)}
            
            return {
                "factory_status": "healthy",
                "registry_health": registry_health,
                "default_model_health": default_model_health,
                "default_model_name": self._default_model_name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "factory_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Global factory instance
_factory = None

def get_factory() -> RecommenderFactory:
    """Get the global recommender factory instance."""
    global _factory
    if _factory is None:
        _factory = RecommenderFactory()
    return _factory

def get_recommender_for_user(user_id: str, **kwargs) -> BaseRecommender:
    """
    Convenience function to get a recommender for a user.
    
    This is the main entry point for getting recommendations
    and handles all the complexity of model selection.
    """
    factory = get_factory()
    return factory.get_recommender_for_user(user_id, **kwargs)

def generate_rankings_for_user_via_registry(user_id: str, **kwargs) -> List[Dict]:
    """
    Generate rankings using the model registry system.
    
    This function provides a drop-in replacement for the original
    generate_rankings_for_user function but uses the model registry.
    """
    try:
        recommender = get_recommender_for_user(user_id, **kwargs)
        return recommender.generate_rankings_for_user(user_id)
    except Exception as e:
        logger.error(f"Failed to generate rankings via registry: {e}")
        # Fallback to original function
        from core.ranking_algorithm import generate_rankings_for_user
        return generate_rankings_for_user(user_id) 