"""
Model Registry Demo

This script demonstrates how to use the Corgi model registry system for:
- Registering new recommendation models
- Setting up A/B testing experiments
- Managing model deployment lifecycle
- Monitoring model performance

Run this script to see the model registry in action!
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import random
from datetime import datetime, timedelta
from typing import List, Dict

from core.recommender_factory import get_factory
from core.model_registry import ModelType, ModelStatus
from core.recommender_base import BaseRecommender, RecommenderCapability

# Sample advanced recommender models for demonstration

class NeuralCollaborativeFilteringModel(BaseRecommender):
    """
    Example Neural Collaborative Filtering model.
    
    This is a placeholder implementation that would be replaced
    with actual neural network code in a real system.
    """
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.capabilities = [
            RecommenderCapability.PERSONALIZATION,
            RecommenderCapability.BATCH_INFERENCE,
            RecommenderCapability.EXPLANATIONS
        ]
        
        # Neural network hyperparameters
        self.embedding_dim = config.get("embedding_dim", 64)
        self.hidden_layers = config.get("hidden_layers", [128, 64, 32])
        self.dropout_rate = config.get("dropout_rate", 0.2)
        self.learning_rate = config.get("learning_rate", 0.001)
        
        self.model_info["name"] = "NeuralCollaborativeFiltering"
        self.model_info["version"] = config.get("version", "1.0")
    
    def generate_rankings_for_user(self, user_id: str) -> List[Dict]:
        """Generate neural CF-based recommendations."""
        
        # Simulate neural network inference
        time.sleep(0.01)  # Simulate computation time
        
        # In a real implementation, this would:
        # 1. Get user embedding vector
        # 2. Get item embedding vectors for candidate items
        # 3. Compute interaction scores using neural network
        # 4. Return ranked recommendations
        
        # For demo, generate synthetic recommendations with neural-inspired scoring
        recommendations = []
        num_recommendations = random.randint(5, 15)
        
        for i in range(num_recommendations):
            # Simulate neural network output with confidence scores
            neural_score = random.random() * 0.8 + 0.1  # 0.1 to 0.9
            confidence = random.random() * 0.3 + 0.7    # 0.7 to 1.0
            
            recommendation = {
                "post_id": f"neural_post_{i}_{user_id}",
                "ranking_score": neural_score,
                "recommendation_reason": "Neural collaborative filtering recommendation",
                "confidence_score": confidence,
                "explanation_data": {
                    "user_embedding_similarity": random.random(),
                    "item_popularity_score": random.random(),
                    "neural_attention_weights": [random.random() for _ in range(5)]
                }
            }
            recommendations.append(recommendation)
        
        # Sort by score
        recommendations.sort(key=lambda x: x["ranking_score"], reverse=True)
        return recommendations

class ContentBasedSemanticModel(BaseRecommender):
    """
    Example content-based model using semantic similarity.
    
    This would use NLP techniques like embeddings to understand content.
    """
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.capabilities = [
            RecommenderCapability.PERSONALIZATION,
            RecommenderCapability.COLD_START,
            RecommenderCapability.EXPLANATIONS,
            RecommenderCapability.BATCH_INFERENCE
        ]
        
        # NLP model parameters
        self.embedding_model = config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
        self.similarity_threshold = config.get("similarity_threshold", 0.7)
        self.content_weight = config.get("content_weight", 0.8)
        
        self.model_info["name"] = "ContentBasedSemantic"
        self.model_info["version"] = config.get("version", "1.0")
    
    def generate_rankings_for_user(self, user_id: str) -> List[Dict]:
        """Generate content-based semantic recommendations."""
        
        # Simulate semantic analysis
        time.sleep(0.02)  # Simulate NLP computation
        
        # In a real implementation, this would:
        # 1. Get user's historical content preferences
        # 2. Extract semantic features from candidate posts
        # 3. Compute semantic similarity scores
        # 4. Rank by semantic relevance
        
        recommendations = []
        num_recommendations = random.randint(8, 12)
        
        for i in range(num_recommendations):
            semantic_score = random.random() * 0.7 + 0.2  # 0.2 to 0.9
            
            recommendation = {
                "post_id": f"semantic_post_{i}_{user_id}",
                "ranking_score": semantic_score,
                "recommendation_reason": "Semantically similar to your interests",
                "explanation_data": {
                    "semantic_similarity": semantic_score,
                    "topic_match": random.choice(["technology", "science", "social", "entertainment"]),
                    "content_features": ["keyword_overlap", "entity_similarity", "sentiment_match"]
                }
            }
            recommendations.append(recommendation)
        
        recommendations.sort(key=lambda x: x["ranking_score"], reverse=True)
        return recommendations

class MultiArmedBanditModel(BaseRecommender):
    """
    Example multi-armed bandit model for exploration/exploitation.
    
    This balances showing popular content vs. exploring new content.
    """
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.capabilities = [
            RecommenderCapability.PERSONALIZATION,
            RecommenderCapability.REAL_TIME,
            RecommenderCapability.INCREMENTAL_LEARNING,
            RecommenderCapability.MULTI_OBJECTIVE
        ]
        
        # Bandit parameters
        self.epsilon = config.get("epsilon", 0.1)  # Exploration rate
        self.alpha = config.get("alpha", 0.1)      # Learning rate
        self.exploration_bonus = config.get("exploration_bonus", 0.2)
        
        self.model_info["name"] = "MultiArmedBandit"
        self.model_info["version"] = config.get("version", "1.0")
    
    def generate_rankings_for_user(self, user_id: str) -> List[Dict]:
        """Generate bandit-based recommendations."""
        
        # Simulate bandit algorithm
        time.sleep(0.005)  # Very fast inference
        
        recommendations = []
        num_recommendations = random.randint(6, 10)
        
        for i in range(num_recommendations):
            # Simulate exploitation vs exploration decision
            is_exploration = random.random() < self.epsilon
            
            if is_exploration:
                score = random.random() * 0.6 + 0.1  # Lower scores for exploration
                reason = "Exploring new content for you"
            else:
                score = random.random() * 0.4 + 0.6  # Higher scores for exploitation
                reason = "Based on your proven preferences"
            
            recommendation = {
                "post_id": f"bandit_post_{i}_{user_id}",
                "ranking_score": score,
                "recommendation_reason": reason,
                "explanation_data": {
                    "is_exploration": is_exploration,
                    "exploitation_score": score if not is_exploration else None,
                    "exploration_bonus": self.exploration_bonus if is_exploration else 0,
                    "confidence_interval": [score - 0.1, score + 0.1]
                }
            }
            recommendations.append(recommendation)
        
        recommendations.sort(key=lambda x: x["ranking_score"], reverse=True)
        return recommendations

def demonstrate_model_registration():
    """Demonstrate registering different types of models."""
    print("🔧 Demonstrating Model Registration")
    print("=" * 50)
    
    factory = get_factory()
    
    # Register Neural Collaborative Filtering model
    print("📊 Registering Neural Collaborative Filtering model...")
    neural_cf_config = {
        "embedding_dim": 128,
        "hidden_layers": [256, 128, 64],
        "dropout_rate": 0.3,
        "learning_rate": 0.001,
        "version": "2.0"
    }
    
    neural_cf_model = NeuralCollaborativeFilteringModel(neural_cf_config)
    
    success = factory.register_model(
        name="neural_cf",
        model_instance=neural_cf_model,
        version="2.0",
        model_type=ModelType.NEURAL_COLLABORATIVE,
        author="ml_research_team",
        description="Advanced neural collaborative filtering with deep embeddings",
        config=neural_cf_config,
        performance_metrics={
            "precision_at_10": 0.82,
            "recall_at_10": 0.75,
            "ndcg": 0.78
        },
        tags=["neural", "collaborative", "embeddings"],
        paper_reference="https://arxiv.org/abs/1708.05031"
    )
    
    if success:
        print("✅ Neural CF model registered successfully!")
    else:
        print("❌ Failed to register Neural CF model")
    
    # Register Content-Based Semantic model
    print("\n🧠 Registering Content-Based Semantic model...")
    semantic_config = {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "similarity_threshold": 0.75,
        "content_weight": 0.85,
        "version": "1.5"
    }
    
    semantic_model = ContentBasedSemanticModel(semantic_config)
    
    success = factory.register_model(
        name="semantic_content",
        model_instance=semantic_model,
        version="1.5",
        model_type=ModelType.CUSTOM,
        author="nlp_research_team",
        description="Semantic content-based recommendations using transformer embeddings",
        config=semantic_config,
        performance_metrics={
            "precision_at_10": 0.79,
            "recall_at_10": 0.71,
            "diversity_score": 0.85
        },
        tags=["content", "semantic", "nlp", "transformers"],
        dependencies=["sentence-transformers", "torch"]
    )
    
    if success:
        print("✅ Semantic content model registered successfully!")
    else:
        print("❌ Failed to register semantic content model")
    
    # Register Multi-Armed Bandit model
    print("\n🎰 Registering Multi-Armed Bandit model...")
    bandit_config = {
        "epsilon": 0.15,
        "alpha": 0.05,
        "exploration_bonus": 0.25,
        "version": "3.0"
    }
    
    bandit_model = MultiArmedBanditModel(bandit_config)
    
    success = factory.register_model(
        name="multi_armed_bandit",
        model_instance=bandit_model,
        version="3.0",
        model_type=ModelType.MULTI_ARMED_BANDIT,
        author="rl_research_team",
        description="Multi-armed bandit for exploration/exploitation balance",
        config=bandit_config,
        performance_metrics={
            "click_through_rate": 0.08,
            "exploration_rate": 0.15,
            "regret": 0.12
        },
        tags=["bandit", "exploration", "real-time"],
        status=ModelStatus.STAGING
    )
    
    if success:
        print("✅ Multi-armed bandit model registered successfully!")
    else:
        print("❌ Failed to register multi-armed bandit model")

def demonstrate_hybrid_model():
    """Demonstrate creating hybrid models."""
    print("\n🔀 Demonstrating Hybrid Model Creation")
    print("=" * 50)
    
    factory = get_factory()
    
    # Create a hybrid model combining neural CF and semantic content
    print("🚀 Creating hybrid model (Neural CF + Semantic Content)...")
    
    success = factory.create_hybrid_model(
        name="neural_semantic_hybrid",
        component_models=[
            ("neural_cf", "2.0"),
            ("semantic_content", "1.5")
        ],
        weights=[0.6, 0.4],  # 60% neural CF, 40% semantic content
        version="1.0",
        author="ensemble_research_team",
        description="Hybrid model combining neural collaborative filtering with semantic content analysis"
    )
    
    if success:
        print("✅ Hybrid model created successfully!")
        
        # Test the hybrid model
        print("🧪 Testing hybrid model...")
        hybrid_model = factory.get_recommender_by_name("neural_semantic_hybrid", "1.0")
        test_recommendations = hybrid_model.generate_rankings_for_user("test_user_123")
        print(f"   Generated {len(test_recommendations)} hybrid recommendations")
        
        # Show first recommendation
        if test_recommendations:
            first_rec = test_recommendations[0]
            print(f"   Top recommendation: {first_rec['post_id']} (score: {first_rec['ranking_score']:.3f})")
            print(f"   Reason: {first_rec['recommendation_reason']}")
    else:
        print("❌ Failed to create hybrid model")

def demonstrate_ab_testing():
    """Demonstrate A/B testing setup."""
    print("\n🧪 Demonstrating A/B Testing Setup")
    print("=" * 50)
    
    factory = get_factory()
    
    # Set up A/B test between different models
    print("⚖️ Setting up A/B test: Neural CF vs Semantic Content...")
    
    success = factory.set_a_b_test(
        experiment_id="neural_vs_semantic_q1_2024",
        models={
            "neural_cf:2.0": 50.0,          # 50% traffic
            "semantic_content:1.5": 30.0,   # 30% traffic
            "simple:1.0": 20.0              # 20% traffic (control)
        },
        user_segments=["power_users", "content_creators"],
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(days=30)
    )
    
    if success:
        print("✅ A/B test configured successfully!")
        
        # Simulate user assignment
        print("👥 Simulating user assignments...")
        test_users = [f"user_{i}" for i in range(10)]
        
        for user_id in test_users:
            model, model_spec = factory.registry.get_model_for_user(user_id, fallback_to_default=True)
            print(f"   {user_id} → {model_spec}")
    else:
        print("❌ Failed to set up A/B test")

def demonstrate_performance_tracking():
    """Demonstrate performance tracking and comparison."""
    print("\n📊 Demonstrating Performance Tracking")
    print("=" * 50)
    
    factory = get_factory()
    
    # Log some sample performance metrics
    models_to_track = [
        ("neural_cf", "2.0"),
        ("semantic_content", "1.5"),
        ("multi_armed_bandit", "3.0")
    ]
    
    print("📈 Logging performance metrics...")
    
    for model_name, version in models_to_track:
        # Simulate performance metrics with some randomness
        metrics = {
            "precision_at_10": random.uniform(0.75, 0.90),
            "recall_at_10": random.uniform(0.65, 0.80),
            "ndcg": random.uniform(0.70, 0.85),
            "click_through_rate": random.uniform(0.05, 0.12),
            "diversity_score": random.uniform(0.60, 0.90)
        }
        
        factory.log_model_performance(
            name=model_name,
            version=version,
            metrics=metrics,
            user_segment="power_users",
            a_b_test_id="neural_vs_semantic_q1_2024",
            sample_size=random.randint(500, 2000)
        )
        
        print(f"   {model_name}:{version} - Precision@10: {metrics['precision_at_10']:.3f}")
    
    # Get performance comparison
    print("\n📋 Performance comparison:")
    comparison = factory.get_model_performance_comparison(
        models=models_to_track,
        start_time=datetime.utcnow() - timedelta(hours=1)
    )
    
    for model_spec, metrics in comparison.items():
        print(f"   {model_spec}:")
        for metric_name, value in metrics.items():
            if value is not None:
                print(f"     {metric_name}: {value:.3f}")

def demonstrate_model_lifecycle():
    """Demonstrate model lifecycle management."""
    print("\n🔄 Demonstrating Model Lifecycle Management")
    print("=" * 50)
    
    factory = get_factory()
    
    # List all models
    print("📋 Current models in registry:")
    models = factory.list_available_models()
    
    for model in models:
        print(f"   {model['name']}:{model['version']} ({model['status']}) by {model['author']}")
    
    # Promote a model to production
    print("\n🚀 Promoting neural_cf:2.0 to production...")
    success = factory.promote_model_to_production("neural_cf", "2.0")
    
    if success:
        print("✅ Model promoted to production!")
        
        # Check updated status
        updated_models = factory.list_available_models(ModelStatus.PRODUCTION)
        print("🏭 Production models:")
        for model in updated_models:
            print(f"   {model['name']}:{model['version']}")
    else:
        print("❌ Failed to promote model")

def demonstrate_health_checks():
    """Demonstrate health checking capabilities."""
    print("\n❤️ Demonstrating Health Checks")
    print("=" * 50)
    
    factory = get_factory()
    
    # Factory health check
    print("🏥 Factory health check:")
    health = factory.health_check()
    print(f"   Status: {health.get('factory_status', 'unknown')}")
    print(f"   Registry health: {health.get('registry_health', {}).get('status', 'unknown')}")
    print(f"   Total models: {health.get('registry_health', {}).get('total_models', 0)}")
    
    # Individual model health checks
    print("\n🔍 Individual model health checks:")
    models_to_check = ["neural_cf", "semantic_content", "multi_armed_bandit"]
    
    for model_name in models_to_check:
        try:
            model = factory.get_recommender_by_name(model_name)
            model_health = model.health_check()
            print(f"   {model_name}: {model_health.get('status', 'unknown')}")
        except Exception as e:
            print(f"   {model_name}: error ({e})")

def main():
    """Run the complete model registry demonstration."""
    print("🐕 Corgi Model Registry Demo")
    print("=" * 60)
    print("This demo shows how to use the model registry for advanced")
    print("recommendation system management and experimentation.")
    print()
    
    try:
        # Run all demonstrations
        demonstrate_model_registration()
        demonstrate_hybrid_model()
        demonstrate_ab_testing()
        demonstrate_performance_tracking()
        demonstrate_model_lifecycle()
        demonstrate_health_checks()
        
        print("\n🎉 Demo completed successfully!")
        print("\nThe model registry is now ready for your insane recommender system!")
        print("\nNext steps:")
        print("1. Replace placeholder models with your actual ML implementations")
        print("2. Set up continuous integration for model deployment")
        print("3. Configure monitoring and alerting for production models")
        print("4. Implement automated A/B testing and champion/challenger evaluation")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 