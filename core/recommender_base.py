"""
Base Classes and Interfaces for Recommendation Models

This module defines the core interfaces and base classes that all recommendation
models must implement to work with the Corgi model registry system.

Key Features:
- Standardized interface for all recommender models
- Abstract base classes with required methods
- Common utility functions and performance tracking
- Integration with the model registry system
- Support for different model types and architectures
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from utils.privacy import generate_user_alias
from utils.metrics import track_recommendation_score

logger = logging.getLogger(__name__)

class RecommenderCapability(Enum):
    """Capabilities that a recommender model can support."""
    PERSONALIZATION = "personalization"
    COLD_START = "cold_start"  
    REAL_TIME = "real_time"
    BATCH_INFERENCE = "batch_inference"
    INCREMENTAL_LEARNING = "incremental_learning"
    MULTI_OBJECTIVE = "multi_objective"
    EXPLANATIONS = "explanations"
    DIVERSITY = "diversity"
    FAIRNESS = "fairness"
    SCALABILITY = "scalability"

@dataclass
class RecommendationRequest:
    """Standardized recommendation request."""
    user_id: str
    limit: int = 10
    offset: int = 0
    filters: Dict[str, Any] = None
    user_context: Dict[str, Any] = None
    request_metadata: Dict[str, Any] = None
    
@dataclass 
class RecommendationItem:
    """Individual recommendation item."""
    post_id: str
    ranking_score: float
    recommendation_reason: str
    confidence_score: Optional[float] = None
    explanation_data: Optional[Dict[str, Any]] = None
    diversity_score: Optional[float] = None
    
@dataclass
class RecommendationResponse:
    """Standardized recommendation response."""
    user_id: str
    recommendations: List[RecommendationItem]
    total_candidates: Optional[int] = None
    processing_time_ms: Optional[float] = None
    model_info: Optional[Dict[str, Any]] = None
    debug_info: Optional[Dict[str, Any]] = None

class BaseRecommender(ABC):
    """
    Abstract base class for all recommendation models.
    
    All recommendation models must inherit from this class and implement
    the required abstract methods. This ensures consistency across all
    models in the registry.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the recommender.
        
        Args:
            config: Model-specific configuration dictionary
        """
        self.config = config or {}
        self.capabilities: List[RecommenderCapability] = []
        self.model_info = {
            "name": self.__class__.__name__,
            "version": self.config.get("version", "1.0"),
            "capabilities": [cap.value for cap in self.capabilities]
        }
        self._performance_metrics = {}
        logger.info(f"Initialized {self.__class__.__name__} recommender")
    
    @abstractmethod
    def generate_rankings_for_user(self, user_id: str) -> List[Dict]:
        """
        Generate personalized rankings for a user.
        
        This is the core method that all models must implement.
        For backward compatibility with existing code.
        
        Args:
            user_id: User ID to generate rankings for
            
        Returns:
            List of dictionaries with ranking data
        """
        pass
    
    def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        """
        Generate recommendations using the new standardized interface.
        
        Args:
            request: Standardized recommendation request
            
        Returns:
            Standardized recommendation response
        """
        start_time = time.time()
        
        try:
            # Call the legacy method for backward compatibility
            rankings = self.generate_rankings_for_user(request.user_id)
            
            # Convert to new format
            recommendations = []
            for rank_data in rankings[:request.limit]:
                item = RecommendationItem(
                    post_id=rank_data.get("post_id", ""),
                    ranking_score=rank_data.get("ranking_score", 0.0),
                    recommendation_reason=rank_data.get("recommendation_reason", "Recommended for you"),
                    confidence_score=rank_data.get("confidence_score"),
                    explanation_data=rank_data.get("explanation_data"),
                    diversity_score=rank_data.get("diversity_score")
                )
                recommendations.append(item)
            
            processing_time = (time.time() - start_time) * 1000
            
            response = RecommendationResponse(
                user_id=request.user_id,
                recommendations=recommendations,
                total_candidates=len(rankings),
                processing_time_ms=processing_time,
                model_info=self.model_info
            )
            
            # Track performance metrics
            self._track_performance(request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            # Return empty response on error
            return RecommendationResponse(
                user_id=request.user_id,
                recommendations=[],
                processing_time_ms=(time.time() - start_time) * 1000,
                model_info=self.model_info
            )
    
    def _track_performance(self, request: RecommendationRequest, response: RecommendationResponse):
        """Track performance metrics."""
        try:
            # Track recommendation scores
            for rec in response.recommendations:
                track_recommendation_score("model_registry", rec.ranking_score)
            
            # Update internal metrics
            self._performance_metrics.update({
                "last_request_time": datetime.utcnow(),
                "last_processing_time_ms": response.processing_time_ms,
                "last_recommendation_count": len(response.recommendations)
            })
            
        except Exception as e:
            logger.warning(f"Failed to track performance: {e}")
    
    def get_capabilities(self) -> List[RecommenderCapability]:
        """Get model capabilities."""
        return self.capabilities
    
    def has_capability(self, capability: RecommenderCapability) -> bool:
        """Check if model has a specific capability."""
        return capability in self.capabilities
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self._performance_metrics.copy()
    
    def warm_up(self) -> bool:
        """
        Warm up the model (load data, initialize caches, etc.).
        
        Returns:
            bool: True if warm-up successful
        """
        try:
            logger.info(f"Warming up {self.__class__.__name__}")
            return True
        except Exception as e:
            logger.error(f"Failed to warm up model: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the model.
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            status = {
                "status": "healthy",
                "model_name": self.model_info["name"],
                "version": self.model_info["version"],
                "capabilities": self.model_info["capabilities"],
                "last_request": self._performance_metrics.get("last_request_time"),
                "avg_processing_time_ms": self._performance_metrics.get("last_processing_time_ms")
            }
            
            # Run a quick test recommendation if possible
            try:
                test_request = RecommendationRequest(user_id="health_check_user", limit=1)
                test_response = self.recommend(test_request)
                status["test_recommendation_success"] = len(test_response.recommendations) >= 0
            except Exception as e:
                status["test_recommendation_success"] = False
                status["test_error"] = str(e)
            
            return status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model_name": self.model_info.get("name", "unknown")
            }

class SimpleLegacyWrapper(BaseRecommender):
    """
    Wrapper for legacy recommendation functions.
    
    This allows existing recommendation functions to work with the new
    model registry system without modification.
    """
    
    def __init__(self, recommendation_function: callable, config: Dict[str, Any] = None):
        """
        Initialize wrapper with a legacy recommendation function.
        
        Args:
            recommendation_function: Function that takes user_id and returns rankings
            config: Optional configuration
        """
        super().__init__(config)
        self.recommendation_function = recommendation_function
        self.capabilities = [
            RecommenderCapability.PERSONALIZATION,
            RecommenderCapability.BATCH_INFERENCE
        ]
        self.model_info["name"] = f"LegacyWrapper_{recommendation_function.__name__}"
    
    def generate_rankings_for_user(self, user_id: str) -> List[Dict]:
        """Call the wrapped legacy function."""
        return self.recommendation_function(user_id)

class CollaborativeFilteringRecommender(BaseRecommender):
    """
    Base class for collaborative filtering models.
    
    Provides common functionality for CF-based models including
    user-item interaction handling and similarity computation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.capabilities = [
            RecommenderCapability.PERSONALIZATION,
            RecommenderCapability.BATCH_INFERENCE,
            RecommenderCapability.EXPLANATIONS
        ]
        self.user_item_matrix = None
        self.item_features = None
        self.user_features = None
    
    @abstractmethod
    def fit(self, interactions: List[Dict], item_features: Dict = None, user_features: Dict = None):
        """
        Train the collaborative filtering model.
        
        Args:
            interactions: List of user-item interactions
            item_features: Optional item feature data
            user_features: Optional user feature data
        """
        pass
    
    @abstractmethod
    def compute_user_similarity(self, user_id1: str, user_id2: str) -> float:
        """Compute similarity between two users."""
        pass
    
    @abstractmethod
    def compute_item_similarity(self, item_id1: str, item_id2: str) -> float:
        """Compute similarity between two items."""
        pass

class ContentBasedRecommender(BaseRecommender):
    """
    Base class for content-based recommendation models.
    
    Provides common functionality for content-based models including
    feature extraction and content similarity computation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.capabilities = [
            RecommenderCapability.PERSONALIZATION,
            RecommenderCapability.COLD_START,
            RecommenderCapability.EXPLANATIONS,
            RecommenderCapability.BATCH_INFERENCE
        ]
        self.content_features = None
        self.feature_extractor = None
    
    @abstractmethod
    def extract_features(self, content: str) -> Dict[str, Any]:
        """
        Extract features from content.
        
        Args:
            content: Text content to extract features from
            
        Returns:
            Dictionary of extracted features
        """
        pass
    
    @abstractmethod
    def compute_content_similarity(self, content1: str, content2: str) -> float:
        """
        Compute similarity between two pieces of content.
        
        Args:
            content1: First content item
            content2: Second content item
            
        Returns:
            Similarity score between 0 and 1
        """
        pass

class HybridRecommender(BaseRecommender):
    """
    Base class for hybrid recommendation models.
    
    Combines multiple recommendation approaches (e.g., collaborative + content-based).
    """
    
    def __init__(self, models: List[BaseRecommender], weights: List[float] = None, config: Dict[str, Any] = None):
        super().__init__(config)
        self.models = models
        self.weights = weights or [1.0 / len(models)] * len(models)
        
        if len(self.weights) != len(self.models):
            raise ValueError("Number of weights must match number of models")
        
        # Combine capabilities from all models
        all_capabilities = set()
        for model in self.models:
            all_capabilities.update(model.get_capabilities())
        self.capabilities = list(all_capabilities)
        
        self.model_info["name"] = f"Hybrid_{len(models)}_models"
        self.model_info["component_models"] = [model.model_info["name"] for model in models]
    
    def generate_rankings_for_user(self, user_id: str) -> List[Dict]:
        """
        Generate hybrid recommendations by combining multiple models.
        
        Args:
            user_id: User ID to generate rankings for
            
        Returns:
            Combined and re-ranked recommendations
        """
        try:
            all_recommendations = {}
            
            # Get recommendations from each model
            for i, model in enumerate(self.models):
                try:
                    model_recs = model.generate_rankings_for_user(user_id)
                    weight = self.weights[i]
                    
                    for rec in model_recs:
                        post_id = rec.get("post_id")
                        score = rec.get("ranking_score", 0.0) * weight
                        
                        if post_id in all_recommendations:
                            # Combine scores from multiple models
                            all_recommendations[post_id]["ranking_score"] += score
                            all_recommendations[post_id]["model_sources"].append(model.model_info["name"])
                        else:
                            rec_copy = rec.copy()
                            rec_copy["ranking_score"] = score
                            rec_copy["model_sources"] = [model.model_info["name"]]
                            all_recommendations[post_id] = rec_copy
                            
                except Exception as e:
                    logger.warning(f"Error getting recommendations from model {i}: {e}")
                    continue
            
            # Sort by combined score and return
            sorted_recs = sorted(
                all_recommendations.values(),
                key=lambda x: x["ranking_score"],
                reverse=True
            )
            
            # Update recommendation reasons for hybrid
            for rec in sorted_recs:
                sources = rec.get("model_sources", [])
                if len(sources) > 1:
                    rec["recommendation_reason"] = f"Recommended by {len(sources)} algorithms"
                elif sources:
                    rec["recommendation_reason"] = f"Recommended by {sources[0]}"
            
            return sorted_recs
            
        except Exception as e:
            logger.error(f"Error in hybrid recommendation: {e}")
            return []

class OnlineLearningRecommender(BaseRecommender):
    """
    Base class for online learning recommendation models.
    
    Supports incremental updates and real-time learning from user feedback.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.capabilities = [
            RecommenderCapability.PERSONALIZATION,
            RecommenderCapability.REAL_TIME,
            RecommenderCapability.INCREMENTAL_LEARNING,
            RecommenderCapability.BATCH_INFERENCE
        ]
    
    @abstractmethod
    def update_with_feedback(self, user_id: str, item_id: str, feedback: float, timestamp: datetime = None):
        """
        Update model with user feedback.
        
        Args:
            user_id: User providing feedback
            item_id: Item being rated
            feedback: Feedback value (e.g., rating, click, etc.)
            timestamp: When feedback was provided
        """
        pass
    
    @abstractmethod
    def partial_fit(self, interactions: List[Dict]):
        """
        Incrementally update model with new interactions.
        
        Args:
            interactions: New user-item interactions to learn from
        """
        pass

# Utility functions for model creation and management

def create_simple_recommender() -> BaseRecommender:
    """Create the default simple recommender."""
    from core.ranking_algorithm import generate_rankings_for_user
    return SimpleLegacyWrapper(generate_rankings_for_user, {"type": "simple", "version": "1.0"})

def validate_recommender_interface(model: Any) -> bool:
    """
    Validate that a model implements the required interface.
    
    Args:
        model: Model instance to validate
        
    Returns:
        bool: True if model implements required methods
    """
    required_methods = ["generate_rankings_for_user"]
    
    for method_name in required_methods:
        if not hasattr(model, method_name):
            logger.error(f"Model missing required method: {method_name}")
            return False
        
        if not callable(getattr(model, method_name)):
            logger.error(f"Model attribute {method_name} is not callable")
            return False
    
    return True

def get_model_signature(model: BaseRecommender) -> Dict[str, Any]:
    """
    Get a signature/fingerprint of a model for comparison.
    
    Args:
        model: Model instance
        
    Returns:
        Dictionary with model signature information
    """
    return {
        "name": model.model_info["name"],
        "version": model.model_info["version"],
        "capabilities": model.model_info["capabilities"],
        "config_hash": hash(str(sorted(model.config.items()))) if model.config else None,
        "class_name": model.__class__.__name__
    } 