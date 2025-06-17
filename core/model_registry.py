"""
Bulletproof Model Registry for Corgi Recommender Service

This module provides a comprehensive model management system for handling
multiple recommendation algorithms, versioning, performance tracking,
A/B testing, and production deployment management.

Features:
- Model registration and versioning
- Performance tracking and comparison
- A/B testing framework integration
- Traffic splitting and canary deployments
- Automatic model selection based on user segments
- Model lifecycle management (staging, production, retired)
- Health monitoring and automatic fallbacks
- Configuration management per model
"""

import logging
import json
import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import pickle
import importlib
from contextlib import contextmanager

from db.connection import get_db_connection, get_cursor
from utils.cache import cache_get, cache_set
from utils.metrics import track_recommendation_score

logger = logging.getLogger(__name__)

class ModelStatus(Enum):
    """Model deployment status."""
    EXPERIMENTAL = "experimental"
    STAGING = "staging" 
    PRODUCTION = "production"
    CANARY = "canary"
    RETIRED = "retired"
    FAILED = "failed"

class ModelType(Enum):
    """Types of recommendation models."""
    SIMPLE = "simple"
    COLLABORATIVE_FILTERING = "collaborative_filtering"
    NEURAL_COLLABORATIVE = "neural_collaborative"
    DEEP_AND_WIDE = "deep_and_wide"
    TRANSFORMER = "transformer"
    GRAPH_NEURAL = "graph_neural"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    MULTI_ARMED_BANDIT = "multi_armed_bandit"
    ENSEMBLE = "ensemble"
    CUSTOM = "custom"

@dataclass
class ModelMetadata:
    """Comprehensive model metadata."""
    name: str
    version: str
    model_type: ModelType
    status: ModelStatus
    created_at: datetime
    updated_at: datetime
    author: str
    description: str
    config: Dict[str, Any]
    performance_metrics: Dict[str, float]
    training_data_hash: Optional[str] = None
    model_size_bytes: Optional[int] = None
    inference_time_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    dependencies: List[str] = None
    tags: List[str] = None
    paper_reference: Optional[str] = None
    code_reference: Optional[str] = None

@dataclass 
class ModelPerformance:
    """Model performance tracking."""
    model_name: str
    version: str
    timestamp: datetime
    metrics: Dict[str, float]
    user_segment: Optional[str] = None
    a_b_test_id: Optional[str] = None
    sample_size: Optional[int] = None

@dataclass
class TrafficSplit:
    """Traffic splitting configuration for A/B testing."""
    model_configs: Dict[str, float]  # model_name -> traffic_percentage
    user_segments: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    experiment_id: Optional[str] = None

class ModelRegistryError(Exception):
    """Custom exception for model registry operations."""
    pass

class ModelRegistry:
    """
    Bulletproof model registry for recommendation systems.
    
    This registry provides comprehensive model management including:
    - Model registration and versioning
    - Performance tracking and A/B testing
    - Traffic splitting and canary deployments
    - Automatic fallbacks and health monitoring
    - Configuration management
    """
    
    def __init__(self, base_path: str = "models", cache_ttl: int = 300):
        """
        Initialize the model registry.
        
        Args:
            base_path: Base directory for storing model files
            cache_ttl: Cache TTL for model metadata in seconds
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self.cache_ttl = cache_ttl
        self._models: Dict[str, Dict[str, ModelMetadata]] = {}
        self._traffic_splits: Dict[str, TrafficSplit] = {}
        self._performance_history: List[ModelPerformance] = []
        self._model_instances: Dict[str, Any] = {}  # Cached model instances
        
        # Initialize database tables
        self._init_database_tables()
        
        # Load existing models from database
        self._load_models_from_db()
        
        logger.info(f"Model registry initialized with base path: {self.base_path}")

    def _init_database_tables(self):
        """Initialize database tables for model registry."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cur:
                    # Detect database type
                    is_sqlite = 'sqlite' in str(type(conn)).lower()
                    
                    # Model metadata table
                    if is_sqlite:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS model_registry (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name VARCHAR(100) NOT NULL,
                                version VARCHAR(50) NOT NULL,
                                model_type VARCHAR(50) NOT NULL,
                                status VARCHAR(20) NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                author VARCHAR(100),
                                description TEXT,
                                config TEXT,
                                performance_metrics TEXT,
                                training_data_hash VARCHAR(64),
                                model_size_bytes BIGINT,
                                inference_time_ms REAL,
                                memory_usage_mb REAL,
                                dependencies TEXT,
                                tags TEXT,
                                paper_reference TEXT,
                                code_reference TEXT,
                                UNIQUE(name, version)
                            )
                        """)
                    else:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS model_registry (
                                id SERIAL PRIMARY KEY,
                                name VARCHAR(100) NOT NULL,
                                version VARCHAR(50) NOT NULL,
                                model_type VARCHAR(50) NOT NULL,
                                status VARCHAR(20) NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                author VARCHAR(100),
                                description TEXT,
                                config JSONB,
                                performance_metrics JSONB,
                                training_data_hash VARCHAR(64),
                                model_size_bytes BIGINT,
                                inference_time_ms FLOAT,
                                memory_usage_mb FLOAT,
                                dependencies JSONB,
                                tags JSONB,
                                paper_reference TEXT,
                                code_reference TEXT,
                                UNIQUE(name, version)
                            )
                        """)
                    
                    # Model performance tracking table
                    if is_sqlite:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS model_performance (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                model_name VARCHAR(100) NOT NULL,
                                version VARCHAR(50) NOT NULL,
                                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                metrics TEXT NOT NULL,
                                user_segment VARCHAR(50),
                                a_b_test_id VARCHAR(100),
                                sample_size INTEGER
                            )
                        """)
                    else:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS model_performance (
                                id SERIAL PRIMARY KEY,
                                model_name VARCHAR(100) NOT NULL,
                                version VARCHAR(50) NOT NULL,
                                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                metrics JSONB NOT NULL,
                                user_segment VARCHAR(50),
                                a_b_test_id VARCHAR(100),
                                sample_size INTEGER
                            )
                        """)
                    
                    # Create index separately for both databases
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS model_performance_idx 
                        ON model_performance(model_name, version, timestamp)
                    """)
                    
                    # Traffic splitting configuration table
                    if is_sqlite:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS traffic_splits (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                experiment_id VARCHAR(100) UNIQUE NOT NULL,
                                model_configs TEXT NOT NULL,
                                user_segments TEXT,
                                start_time TIMESTAMP,
                                end_time TIMESTAMP,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                is_active BOOLEAN DEFAULT 1
                            )
                        """)
                    else:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS traffic_splits (
                                id SERIAL PRIMARY KEY,
                                experiment_id VARCHAR(100) UNIQUE NOT NULL,
                                model_configs JSONB NOT NULL,
                                user_segments JSONB,
                                start_time TIMESTAMP,
                                end_time TIMESTAMP,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                is_active BOOLEAN DEFAULT TRUE
                            )
                        """)
                    
                conn.commit()
                logger.info("Model registry database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize model registry database tables: {e}")
            raise ModelRegistryError(f"Database initialization failed: {e}")

    def _load_models_from_db(self):
        """Load existing models from database into memory."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cur:
                    cur.execute("""
                        SELECT name, version, model_type, status, created_at, updated_at,
                               author, description, config, performance_metrics,
                               training_data_hash, model_size_bytes, inference_time_ms,
                               memory_usage_mb, dependencies, tags, paper_reference, code_reference
                        FROM model_registry
                        WHERE status != 'retired'
                        ORDER BY created_at DESC
                    """)
                    
                    for row in cur.fetchall():
                        metadata = ModelMetadata(
                            name=row[0],
                            version=row[1], 
                            model_type=ModelType(row[2]),
                            status=ModelStatus(row[3]),
                            created_at=row[4],
                            updated_at=row[5],
                            author=row[6] or "unknown",
                            description=row[7] or "",
                            config=row[8] or {},
                            performance_metrics=row[9] or {},
                            training_data_hash=row[10],
                            model_size_bytes=row[11],
                            inference_time_ms=row[12],
                            memory_usage_mb=row[13],
                            dependencies=row[14] or [],
                            tags=row[15] or [],
                            paper_reference=row[16],
                            code_reference=row[17]
                        )
                        
                        if metadata.name not in self._models:
                            self._models[metadata.name] = {}
                        self._models[metadata.name][metadata.version] = metadata
                        
            logger.info(f"Loaded {sum(len(versions) for versions in self._models.values())} models from database")
            
        except Exception as e:
            logger.error(f"Failed to load models from database: {e}")

    def register_model(
        self,
        name: str,
        version: str,
        model_instance: Any,
        model_type: ModelType,
        author: str,
        description: str = "",
        config: Dict[str, Any] = None,
        performance_metrics: Dict[str, float] = None,
        dependencies: List[str] = None,
        tags: List[str] = None,
        paper_reference: str = None,
        code_reference: str = None,
        training_data_hash: str = None,
        status: ModelStatus = ModelStatus.EXPERIMENTAL
    ) -> ModelMetadata:
        """
        Register a new model in the registry.
        
        Args:
            name: Model name
            version: Model version (e.g., "v1.0", "v2.1")
            model_instance: The actual model instance/object
            model_type: Type of model
            author: Model author/creator
            description: Human-readable description
            config: Model configuration dictionary
            performance_metrics: Initial performance metrics
            dependencies: List of required dependencies
            tags: Tags for categorization
            paper_reference: Reference to research paper
            code_reference: Reference to source code
            training_data_hash: Hash of training data for reproducibility
            status: Initial model status
            
        Returns:
            ModelMetadata: Registered model metadata
        """
        try:
            # Validate inputs
            if not name or not version:
                raise ModelRegistryError("Model name and version are required")
                
            if not hasattr(model_instance, 'generate_rankings_for_user'):
                raise ModelRegistryError("Model must implement 'generate_rankings_for_user' method")
            
            # Check if model already exists
            if name in self._models and version in self._models[name]:
                raise ModelRegistryError(f"Model {name}:{version} already exists")
            
            # Calculate model size
            model_size_bytes = None
            try:
                model_path = self.base_path / name / f"{version}.pkl"
                model_path.parent.mkdir(exist_ok=True)
                
                with open(model_path, 'wb') as f:
                    pickle.dump(model_instance, f)
                    model_size_bytes = model_path.stat().st_size
                    
            except Exception as e:
                logger.warning(f"Could not serialize model {name}:{version}: {e}")
            
            # Create metadata
            now = datetime.now(timezone.utc)
            metadata = ModelMetadata(
                name=name,
                version=version,
                model_type=model_type,
                status=status,
                created_at=now,
                updated_at=now,
                author=author,
                description=description,
                config=config or {},
                performance_metrics=performance_metrics or {},
                training_data_hash=training_data_hash,
                model_size_bytes=model_size_bytes,
                dependencies=dependencies or [],
                tags=tags or [],
                paper_reference=paper_reference,
                code_reference=code_reference
            )
            
            # Store in database
            self._save_model_to_db(metadata)
            
            # Store in memory
            if name not in self._models:
                self._models[name] = {}
            self._models[name][version] = metadata
            
            # Cache model instance
            model_key = f"{name}:{version}"
            self._model_instances[model_key] = model_instance
            
            # Invalidate cache
            cache_key = f"model_registry:models:{name}"
            cache_set(cache_key, None, ttl=0)  # Delete cache entry
            
            logger.info(f"Successfully registered model {name}:{version}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to register model {name}:{version}: {e}")
            raise ModelRegistryError(f"Model registration failed: {e}")

    def _save_model_to_db(self, metadata: ModelMetadata):
        """Save model metadata to database."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cur:
                    # Detect database type for parameter style
                    is_sqlite = 'sqlite' in str(type(conn)).lower()
                    
                    if is_sqlite:
                        # SQLite version with ? placeholders and INSERT OR REPLACE
                        cur.execute("""
                            INSERT OR REPLACE INTO model_registry (
                                name, version, model_type, status, created_at, updated_at,
                                author, description, config, performance_metrics,
                                training_data_hash, model_size_bytes, inference_time_ms,
                                memory_usage_mb, dependencies, tags, paper_reference, code_reference
                            ) VALUES (
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                            )
                        """, (
                            metadata.name, metadata.version, metadata.model_type.value,
                            metadata.status.value, metadata.created_at, metadata.updated_at,
                            metadata.author, metadata.description, 
                            json.dumps(metadata.config), json.dumps(metadata.performance_metrics),
                            metadata.training_data_hash, metadata.model_size_bytes,
                            metadata.inference_time_ms, metadata.memory_usage_mb,
                            json.dumps(metadata.dependencies), json.dumps(metadata.tags),
                            metadata.paper_reference, metadata.code_reference
                        ))
                    else:
                        # PostgreSQL version with %s placeholders and ON CONFLICT
                        cur.execute("""
                            INSERT INTO model_registry (
                                name, version, model_type, status, created_at, updated_at,
                                author, description, config, performance_metrics,
                                training_data_hash, model_size_bytes, inference_time_ms,
                                memory_usage_mb, dependencies, tags, paper_reference, code_reference
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            ON CONFLICT (name, version) DO UPDATE SET
                                status = EXCLUDED.status,
                                updated_at = EXCLUDED.updated_at,
                                config = EXCLUDED.config,
                                performance_metrics = EXCLUDED.performance_metrics,
                                inference_time_ms = EXCLUDED.inference_time_ms,
                                memory_usage_mb = EXCLUDED.memory_usage_mb
                        """, (
                            metadata.name, metadata.version, metadata.model_type.value,
                            metadata.status.value, metadata.created_at, metadata.updated_at,
                            metadata.author, metadata.description, 
                            json.dumps(metadata.config), json.dumps(metadata.performance_metrics),
                            metadata.training_data_hash, metadata.model_size_bytes,
                            metadata.inference_time_ms, metadata.memory_usage_mb,
                            json.dumps(metadata.dependencies), json.dumps(metadata.tags),
                            metadata.paper_reference, metadata.code_reference
                        ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save model to database: {e}")
            raise

    def get_model(self, name: str, version: str = None) -> Any:
        """
        Get a model instance.
        
        Args:
            name: Model name
            version: Model version (if None, gets latest production version)
            
        Returns:
            Model instance
        """
        try:
            # Determine version to use
            if version is None:
                version = self.get_latest_version(name, status=ModelStatus.PRODUCTION)
                if version is None:
                    version = self.get_latest_version(name)
                    
            if version is None:
                raise ModelRegistryError(f"No versions found for model {name}")
            
            model_key = f"{name}:{version}"
            
            # Try to get from cache
            if model_key in self._model_instances:
                return self._model_instances[model_key]
            
            # Try to load from disk
            model_path = self.base_path / name / f"{version}.pkl"
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    model_instance = pickle.load(f)
                    self._model_instances[model_key] = model_instance
                    return model_instance
            
            # If not found, try to instantiate from class path
            metadata = self.get_model_metadata(name, version)
            if metadata and metadata.code_reference:
                model_instance = self._instantiate_from_reference(metadata)
                self._model_instances[model_key] = model_instance
                return model_instance
                
            raise ModelRegistryError(f"Model {name}:{version} not found")
            
        except Exception as e:
            logger.error(f"Failed to get model {name}:{version}: {e}")
            raise ModelRegistryError(f"Failed to get model: {e}")

    def _instantiate_from_reference(self, metadata: ModelMetadata) -> Any:
        """Instantiate model from code reference."""
        try:
            module_path, class_name = metadata.code_reference.rsplit('.', 1)
            module = importlib.import_module(module_path)
            model_class = getattr(module, class_name)
            return model_class(**metadata.config)
        except Exception as e:
            logger.error(f"Failed to instantiate model from reference: {e}")
            raise

    def get_model_for_user(
        self, 
        user_id: str, 
        user_segment: str = None,
        fallback_to_default: bool = True
    ) -> Tuple[Any, str]:
        """
        Get the appropriate model for a user based on A/B testing and traffic splits.
        
        Args:
            user_id: User ID
            user_segment: User segment (optional)
            fallback_to_default: Whether to fallback to default model if selection fails
            
        Returns:
            Tuple of (model_instance, model_name:version)
        """
        try:
            # Check for active traffic splits
            selected_model = self._select_model_from_traffic_split(user_id, user_segment)
            
            if selected_model:
                model_name, version = selected_model.split(':')
                model_instance = self.get_model(model_name, version)
                return model_instance, selected_model
            
            # Default to latest production model
            if fallback_to_default:
                default_model = self._get_default_model()
                if default_model:
                    return default_model
                    
            raise ModelRegistryError("No suitable model found for user")
            
        except Exception as e:
            logger.error(f"Failed to get model for user {user_id}: {e}")
            if fallback_to_default:
                # Last resort fallback
                return self._get_emergency_fallback()
            raise

    def _select_model_from_traffic_split(self, user_id: str, user_segment: str = None) -> Optional[str]:
        """Select model based on traffic splitting configuration."""
        try:
            # Get active traffic splits
            active_splits = self._get_active_traffic_splits(user_segment)
            
            if not active_splits:
                return None
            
            # Use user ID hash for consistent assignment
            user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            
            for split in active_splits:
                # Check if user segment matches
                if split.user_segments and user_segment not in split.user_segments:
                    continue
                    
                # Determine assignment based on hash
                cumulative_percentage = 0.0
                hash_percentage = (user_hash % 10000) / 100.0  # 0-99.99
                
                for model_name, percentage in split.model_configs.items():
                    cumulative_percentage += percentage
                    if hash_percentage < cumulative_percentage:
                        return model_name
                        
            return None
            
        except Exception as e:
            logger.error(f"Failed to select model from traffic split: {e}")
            return None

    def _get_active_traffic_splits(self, user_segment: str = None) -> List[TrafficSplit]:
        """Get active traffic splits."""
        # This would be implemented to fetch from database
        # For now, return empty list
        return []

    def _get_default_model(self) -> Tuple[Any, str]:
        """Get the default production model."""
        try:
            # Find latest production model
            for name, versions in self._models.items():
                for version, metadata in versions.items():
                    if metadata.status == ModelStatus.PRODUCTION:
                        model_instance = self.get_model(name, version)
                        return model_instance, f"{name}:{version}"
            
            # If no production model, get latest experimental
            for name, versions in self._models.items():
                latest_version = max(versions.keys())
                model_instance = self.get_model(name, latest_version)
                return model_instance, f"{name}:{latest_version}"
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get default model: {e}")
            return None

    def _get_emergency_fallback(self) -> Tuple[Any, str]:
        """Emergency fallback to simple model."""
        try:
            from core.ranking_algorithm import generate_rankings_for_user
            
            class SimpleFallbackModel:
                def generate_rankings_for_user(self, user_id: str) -> List[Dict]:
                    return generate_rankings_for_user(user_id)
            
            return SimpleFallbackModel(), "simple:fallback"
            
        except Exception as e:
            logger.error(f"Emergency fallback failed: {e}")
            raise ModelRegistryError("Complete model registry failure")

    def get_model_metadata(self, name: str, version: str = None) -> Optional[ModelMetadata]:
        """Get model metadata."""
        if name not in self._models:
            return None
            
        if version is None:
            version = self.get_latest_version(name)
            
        return self._models[name].get(version)

    def get_latest_version(self, name: str, status: ModelStatus = None) -> Optional[str]:
        """Get latest version of a model, optionally filtered by status."""
        if name not in self._models:
            return None
            
        versions = self._models[name]
        if status:
            versions = {v: m for v, m in versions.items() if m.status == status}
            
        if not versions:
            return None
            
        # Sort versions (assuming semantic versioning)
        sorted_versions = sorted(versions.keys(), key=lambda x: [int(i) for i in x.replace('v', '').split('.')])
        return sorted_versions[-1]

    def list_models(self, status: ModelStatus = None) -> List[ModelMetadata]:
        """List all models, optionally filtered by status."""
        models = []
        for name, versions in self._models.items():
            for version, metadata in versions.items():
                if status is None or metadata.status == status:
                    models.append(metadata)
        return models

    def update_model_status(self, name: str, version: str, status: ModelStatus) -> bool:
        """Update model status."""
        try:
            if name not in self._models or version not in self._models[name]:
                raise ModelRegistryError(f"Model {name}:{version} not found")
            
            metadata = self._models[name][version]
            metadata.status = status
            metadata.updated_at = datetime.utcnow()
            
            # Update in database
            self._save_model_to_db(metadata)
            
            logger.info(f"Updated model {name}:{version} status to {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update model status: {e}")
            return False

    def set_traffic_split(
        self,
        experiment_id: str,
        model_configs: Dict[str, float],
        user_segments: List[str] = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> bool:
        """
        Set traffic splitting configuration for A/B testing.
        
        Args:
            experiment_id: Unique experiment identifier
            model_configs: Dictionary of model_name:version -> traffic_percentage
            user_segments: Optional list of user segments to target
            start_time: When to start the experiment
            end_time: When to end the experiment
            
        Returns:
            bool: Success status
        """
        try:
            # Validate percentages sum to 100
            total_percentage = sum(model_configs.values())
            if abs(total_percentage - 100.0) > 0.01:
                raise ModelRegistryError(f"Traffic percentages must sum to 100, got {total_percentage}")
            
            # Validate models exist
            for model_spec in model_configs.keys():
                if ':' in model_spec:
                    name, version = model_spec.split(':', 1)
                else:
                    name, version = model_spec, None
                    
                if not self.get_model_metadata(name, version):
                    raise ModelRegistryError(f"Model {model_spec} not found")
            
            traffic_split = TrafficSplit(
                model_configs=model_configs,
                user_segments=user_segments,
                start_time=start_time or datetime.utcnow(),
                end_time=end_time,
                experiment_id=experiment_id
            )
            
            self._traffic_splits[experiment_id] = traffic_split
            
            # Save to database
            self._save_traffic_split_to_db(traffic_split)
            
            logger.info(f"Set traffic split for experiment {experiment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set traffic split: {e}")
            return False

    def _save_traffic_split_to_db(self, traffic_split: TrafficSplit):
        """Save traffic split configuration to database."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cur:
                    cur.execute("""
                        INSERT INTO traffic_splits (
                            experiment_id, model_configs, user_segments, start_time, end_time
                        ) VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (experiment_id) DO UPDATE SET
                            model_configs = EXCLUDED.model_configs,
                            user_segments = EXCLUDED.user_segments,
                            start_time = EXCLUDED.start_time,
                            end_time = EXCLUDED.end_time,
                            is_active = TRUE
                    """, (
                        traffic_split.experiment_id,
                        json.dumps(traffic_split.model_configs),
                        json.dumps(traffic_split.user_segments) if traffic_split.user_segments else None,
                        traffic_split.start_time,
                        traffic_split.end_time
                    ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save traffic split to database: {e}")
            raise

    def log_performance(
        self,
        name: str,
        version: str,
        metrics: Dict[str, float],
        user_segment: str = None,
        a_b_test_id: str = None,
        sample_size: int = None
    ):
        """Log performance metrics for a model."""
        try:
            performance = ModelPerformance(
                model_name=name,
                version=version,
                timestamp=datetime.utcnow(),
                metrics=metrics,
                user_segment=user_segment,
                a_b_test_id=a_b_test_id,
                sample_size=sample_size
            )
            
            self._performance_history.append(performance)
            
            # Update model metadata with latest metrics
            if name in self._models and version in self._models[name]:
                metadata = self._models[name][version]
                metadata.performance_metrics.update(metrics)
                metadata.updated_at = datetime.utcnow()
                self._save_model_to_db(metadata)
            
            # Save to database
            self._save_performance_to_db(performance)
            
            logger.info(f"Logged performance for {name}:{version}")
            
        except Exception as e:
            logger.error(f"Failed to log performance: {e}")

    def _save_performance_to_db(self, performance: ModelPerformance):
        """Save performance data to database."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cur:
                    cur.execute("""
                        INSERT INTO model_performance (
                            model_name, version, timestamp, metrics, user_segment, a_b_test_id, sample_size
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        performance.model_name,
                        performance.version,
                        performance.timestamp,
                        json.dumps(performance.metrics),
                        performance.user_segment,
                        performance.a_b_test_id,
                        performance.sample_size
                    ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save performance to database: {e}")
            raise

    def get_performance_comparison(
        self,
        models: List[Tuple[str, str]],
        start_time: datetime = None,
        end_time: datetime = None,
        user_segment: str = None
    ) -> Dict[str, Dict[str, float]]:
        """Get performance comparison between models."""
        try:
            comparison = {}
            
            for name, version in models:
                model_key = f"{name}:{version}"
                
                # Get performance data from database
                with get_db_connection() as conn:
                    with get_cursor(conn) as cur:
                        query = """
                            SELECT AVG((metrics->>'precision_at_10')::float) as avg_precision,
                                   AVG((metrics->>'recall_at_10')::float) as avg_recall,
                                   AVG((metrics->>'ndcg')::float) as avg_ndcg,
                                   COUNT(*) as sample_count
                            FROM model_performance
                            WHERE model_name = %s AND version = %s
                        """
                        params = [name, version]
                        
                        if start_time:
                            query += " AND timestamp >= %s"
                            params.append(start_time)
                        if end_time:
                            query += " AND timestamp <= %s"
                            params.append(end_time)
                        if user_segment:
                            query += " AND user_segment = %s"
                            params.append(user_segment)
                            
                        cur.execute(query, params)
                        row = cur.fetchone()
                        
                        if row:
                            comparison[model_key] = {
                                'precision_at_10': row[0] or 0.0,
                                'recall_at_10': row[1] or 0.0,
                                'ndcg': row[2] or 0.0,
                                'sample_count': row[3] or 0
                            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to get performance comparison: {e}")
            return {}

    @contextmanager
    def model_performance_tracking(self, name: str, version: str):
        """Context manager for tracking model performance."""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            inference_time = (end_time - start_time) * 1000  # Convert to ms
            memory_usage = end_memory - start_memory
            
            # Update model metadata
            if name in self._models and version in self._models[name]:
                metadata = self._models[name][version]
                metadata.inference_time_ms = inference_time
                metadata.memory_usage_mb = memory_usage
                metadata.updated_at = datetime.utcnow()
                self._save_model_to_db(metadata)

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on model registry."""
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "total_models": sum(len(versions) for versions in self._models.values()),
                "production_models": len([
                    m for versions in self._models.values() 
                    for m in versions.values() 
                    if m.status == ModelStatus.PRODUCTION
                ]),
                "active_experiments": len(self._traffic_splits),
                "cached_instances": len(self._model_instances),
                "database_connection": "ok"
            }
            
            # Test database connection
            try:
                with get_db_connection() as conn:
                    with get_cursor(conn) as cur:
                        cur.execute("SELECT 1")
                        cur.fetchone()
            except Exception as e:
                health_status["database_connection"] = f"error: {e}"
                health_status["status"] = "unhealthy"
            
            return health_status
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Global registry instance
_registry = None

def get_registry() -> ModelRegistry:
    """Get the global model registry instance."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry