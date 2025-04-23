# SQLAlchemy Models

This page documents the SQLAlchemy models used by the Corgi Recommender Service. These models define the database schema and provide the object-relational mapping between Python objects and database tables.

## Base Model

All models inherit from the SQLAlchemy `declarative_base()` class:

```python
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
```

## Enum Types

### PrivacyLevel

```python
class PrivacyLevel(enum.Enum):
    NONE = "none"
    LIMITED = "limited"
    FULL = "full"
```

This enum represents the different privacy levels a user can choose:

- **NONE**: Minimal data collection, only essential information is stored
- **LIMITED**: Standard data collection with anonymization after a retention period
- **FULL**: Complete data collection for optimal recommendations

### InteractionType

```python
class InteractionType(enum.Enum):
    FAVORITE = "favorite"
    BOOST = "boost"
    REPLY = "reply"
    VIEW = "view"
    BOOKMARK = "bookmark"
```

This enum represents the different types of interactions a user can have with posts.

## Models

### UserAlias

```python
class UserAlias(Base):
    """Model for user aliases - privacy-preserving identifiers for users."""
    __tablename__ = "user_aliases"
    
    alias_id = Column(String(64), primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    privacy_level = Column(Enum(PrivacyLevel), default=PrivacyLevel.FULL)
    
    # Relationships
    interactions = relationship("UserInteraction", back_populates="user_alias", cascade="all, delete-orphan")
    author_preferences = relationship("AuthorPreference", back_populates="user_alias", cascade="all, delete-orphan")
    recommendation_logs = relationship("RecommendationLog", back_populates="user_alias", cascade="all, delete-orphan")
```

The `UserAlias` model stores pseudonymized user identifiers and privacy preferences. The `alias_id` is generated using a HMAC-SHA256 hash of the original user ID.

### PostMetadata

```python
class PostMetadata(Base):
    """Model for post metadata - stores information about posts."""
    __tablename__ = "post_metadata"
    
    post_id = Column(String(64), primary_key=True)
    author_id = Column(String(64), nullable=False, index=True)
    author_name = Column(String(255))
    created_at = Column(DateTime, nullable=False, index=True)
    content = Column(Text)
    language = Column(String(10), default="en", index=True)
    favorites = Column(Integer, default=0)
    boosts = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    sensitive = Column(Boolean, default=False)
    
    # JSON fields - handled differently in SQLite vs PostgreSQL
    tags = Column(JSON)  # Will be automatically mapped to appropriate type
    
    # Relationships
    interactions = relationship("UserInteraction", back_populates="post", cascade="all, delete-orphan")
    recommendation_logs = relationship("RecommendationLog", back_populates="post", cascade="all, delete-orphan")
    
    def get_tags(self) -> List[str]:
        """Get tags as a list, handling different database backends."""
        if self.tags is None:
            return []
        if isinstance(self.tags, list):
            return self.tags
        if isinstance(self.tags, str):
            try:
                return json.loads(self.tags)
            except json.JSONDecodeError:
                return []
        return []
```

The `PostMetadata` model stores information about posts from Mastodon/fediverse. It includes a helper method `get_tags()` that handles differences between SQLite and PostgreSQL JSON storage.

### UserInteraction

```python
class UserInteraction(Base):
    """Model for user interactions with posts."""
    __tablename__ = "user_interactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_id = Column(String(64), ForeignKey("user_aliases.alias_id"), nullable=False, index=True)
    post_id = Column(String(64), ForeignKey("post_metadata.post_id"), nullable=False, index=True)
    interaction_type = Column(Enum(InteractionType), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    score_weight = Column(Float, default=1.0)
    
    # Context for the interaction - stored as JSON
    context = Column(JSON, nullable=True)
    
    # Relationships
    user_alias = relationship("UserAlias", back_populates="interactions")
    post = relationship("PostMetadata", back_populates="interactions")
    
    __table_args__ = (
        # Unique constraint to prevent duplicate interactions of the same type
        {'sqlite_autoincrement': True}
    )
```

The `UserInteraction` model tracks user interactions with posts. It supports storing additional context as JSON data.

### AuthorPreference

```python
class AuthorPreference(Base):
    """Model for user preferences for authors, aggregated from interactions."""
    __tablename__ = "author_preferences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_id = Column(String(64), ForeignKey("user_aliases.alias_id"), nullable=False, index=True)
    author_id = Column(String(64), nullable=False, index=True)
    interaction_count = Column(Integer, default=0)
    last_interaction_at = Column(DateTime, default=datetime.datetime.utcnow)
    preference_score = Column(Float, default=0.0)
    
    # Relationships
    user_alias = relationship("UserAlias", back_populates="author_preferences")
    
    __table_args__ = (
        # Unique constraint for alias_id + author_id
        {'sqlite_autoincrement': True}
    )
```

The `AuthorPreference` model aggregates user preferences for authors based on their interactions. It maintains a calculated preference score that is used for recommendations.

### RecommendationLog

```python
class RecommendationLog(Base):
    """Model for logging recommendations made to users."""
    __tablename__ = "recommendation_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_id = Column(String(64), ForeignKey("user_aliases.alias_id"), nullable=False, index=True)
    post_id = Column(String(64), ForeignKey("post_metadata.post_id"), nullable=False, index=True)
    recommended_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    reason = Column(String(255))
    model_version = Column(String(50))
    
    # Relationships
    user_alias = relationship("UserAlias", back_populates="recommendation_logs")
    post = relationship("PostMetadata", back_populates="recommendation_logs")
    
    __table_args__ = (
        {'sqlite_autoincrement': True}
    )
```

The `RecommendationLog` model logs recommendations made to users, including the reason for the recommendation and the model version used.

## Database Compatibility

These models are designed to work with both SQLite and PostgreSQL databases through SQLAlchemy's abstraction layer. Special considerations include:

1. **JSON Handling**: 
   - PostgreSQL uses native JSON/JSONB types
   - SQLite stores JSON as TEXT with serialization/deserialization

2. **Auto-increment**:
   - Uses `sqlite_autoincrement=True` to ensure compatible behavior across databases

3. **Indexes**:
   - Basic indexes work the same on both databases
   - Advanced indexes (like GIN) are only applied on PostgreSQL

## Using Models in Code

To use these models in your code:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import UserAlias, PostMetadata, UserInteraction

# Create engine and session
engine = create_engine("sqlite:///data/corgi_recommender.db")
Session = sessionmaker(bind=engine)
session = Session()

# Query example
user_alias = session.query(UserAlias).filter_by(alias_id="some_hash").first()
user_interactions = user_alias.interactions if user_alias else []

# Cleanup
session.close()
```

For most use cases, however, you should use the `db.interface` module instead of working with the models directly. This provides a cleaner API and handles proper session management.