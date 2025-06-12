"""
SQLAlchemy models for the Corgi Recommender Service.

This module defines the ORM models for all database tables,
with support for both SQLite and PostgreSQL.
"""

import enum
import json
import datetime
from typing import List, Optional, Dict, Any, Union
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, ForeignKey, 
    Enum, JSON, Text, Table, create_engine, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

# Create base model class
Base = declarative_base()

# Enum for privacy levels
class PrivacyLevel(enum.Enum):
    NONE = "none"
    LIMITED = "limited"
    FULL = "full"
    PUBLIC = "public"

# Enum for interaction types
class InteractionType(enum.Enum):
    FAVORITE = "favorite"
    BOOST = "boost"
    REPLY = "reply"
    VIEW = "view"
    BOOKMARK = "bookmark"

class UserAlias(Base):
    """
    Model for user aliases - privacy-preserving identifiers for users.
    """
    __tablename__ = "user_aliases"
    
    alias_id = Column(String(64), primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    privacy_level = Column(Enum(PrivacyLevel), default=PrivacyLevel.FULL)
    
    # Relationships
    interactions = relationship("Interaction", back_populates="user_alias", cascade="all, delete-orphan")
    timelines = relationship("UserTimeline", back_populates="user_alias", cascade="all, delete-orphan")
    old_interactions = relationship("UserInteraction", back_populates="user_alias", cascade="all, delete-orphan")
    author_preferences = relationship("AuthorPreference", back_populates="user_alias", cascade="all, delete-orphan")
    recommendation_logs = relationship("RecommendationLog", back_populates="user_alias", cascade="all, delete-orphan")

class PostMetadata(Base):
    """
    Model for post metadata - stores information about posts.
    """
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

class UserInteraction(Base):
    """
    Model for user interactions with posts.
    """
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
    user_alias = relationship("UserAlias", back_populates="old_interactions")
    post = relationship("PostMetadata", back_populates="interactions")
    
    __table_args__ = (
        # Unique constraint to prevent duplicate interactions of the same type
        {'sqlite_autoincrement': True}
    )

class AuthorPreference(Base):
    """
    Model for user preferences for authors, aggregated from interactions.
    """
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

class RecommendationLog(Base):
    """
    Model for logging recommendations made to users.
    """
    __tablename__ = "recommendation_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_id = Column(String(64), ForeignKey("user_aliases.alias_id"), nullable=False, index=True)
    post_id = Column(String(64), ForeignKey("post_metadata.post_id"), nullable=False, index=True)
    recommended_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    reason = Column(String(255))
    reason_type = Column(String(50))  # New field for specific reason type
    reason_detail = Column(Text)  # New field for specific reason detail
    model_version = Column(String(50))
    
    # Relationships
    user_alias = relationship("UserAlias", back_populates="recommendation_logs")
    post = relationship("PostMetadata", back_populates="recommendation_logs")
    
    __table_args__ = (
        {'sqlite_autoincrement': True}
    )

class Post(Base):
    """
    Model for social media posts stored in the database.
    """
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(64), unique=True, nullable=False, index=True)
    author_name = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    privacy_level = Column(Enum(PrivacyLevel), default=PrivacyLevel.PUBLIC, index=True)
    language = Column(String(10), default='en', index=True)
    is_synthetic = Column(Boolean, default=False, index=True)
    post_metadata = Column(JSON, default={})
    
    # Relationships
    interactions = relationship("Interaction", back_populates="post", cascade="all, delete-orphan")
    crawled_posts = relationship("CrawledPost", back_populates="post", cascade="all, delete-orphan")


class Interaction(Base):
    """
    Model for user interactions with posts.
    """
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_id = Column(String(64), ForeignKey("user_aliases.alias_id"), nullable=False, index=True)
    post_id = Column(String(64), ForeignKey("posts.post_id"), nullable=False, index=True)
    interaction_type = Column(Enum(InteractionType), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    context = Column(JSON, default={})
    
    # Relationships
    user_alias = relationship("UserAlias", back_populates="interactions")
    post = relationship("Post", back_populates="interactions")


class CrawledPost(Base):
    """
    Model for posts that have been crawled from external sources.
    """
    __tablename__ = "crawled_posts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(64), ForeignKey("posts.post_id"), nullable=False, index=True)
    source_url = Column(String(500), nullable=False)
    crawled_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    crawler_version = Column(String(50))
    status = Column(String(50), default='active', index=True)
    crawl_metadata = Column(JSON, default={})
    
    # Relationships
    post = relationship("Post", back_populates="crawled_posts")


class UserTimeline(Base):
    """
    Model for user timeline data and preferences.
    """
    __tablename__ = "user_timelines"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_id = Column(String(64), ForeignKey("user_aliases.alias_id"), nullable=False, index=True)
    timeline_type = Column(String(50), default='home', index=True)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    preferences = Column(JSON, default={})
    cached_data = Column(JSON, default={})
    
    # Relationships
    user_alias = relationship("UserAlias", back_populates="timelines")
    cached_recommendations = relationship("CachedRecommendation", back_populates="timeline", cascade="all, delete-orphan")


class CachedRecommendation(Base):
    """
    Model for cached recommendation results.
    """
    __tablename__ = "cached_recommendations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timeline_id = Column(Integer, ForeignKey("user_timelines.id"), nullable=False, index=True)
    post_id = Column(String(64), ForeignKey("posts.post_id"), nullable=False, index=True)
    score = Column(Float, nullable=False, index=True)
    rank_position = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    expires_at = Column(DateTime, index=True)
    algorithm_version = Column(String(50))
    cache_metadata = Column(JSON, default={})
    
    # Relationships
    timeline = relationship("UserTimeline", back_populates="cached_recommendations")
    post = relationship("Post")

# This function will be used to handle JSON serialization/deserialization
def json_serializer(obj):
    """Helper function to serialize objects to JSON."""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, enum.Enum):
        return obj.value
    raise TypeError(f"Type {type(obj)} not serializable")


# Authentication models for dashboard users and OAuth applications
from flask_login import UserMixin
from cryptography.fernet import Fernet


class DashboardUser(Base, UserMixin):
    """Dashboard user model for OAuth authenticated users."""
    
    __tablename__ = 'dashboard_users'
    
    id = Column(Integer, primary_key=True)
    oauth_provider = Column(String(50), nullable=False)  # 'google', 'github'
    oauth_id = Column(String(100), nullable=False)       # Provider's user ID
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(50), nullable=False, default='user')  # 'user', 'admin' (legacy field - will be deprecated)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # RBAC Relationships
    user_roles = relationship(
        "UserRole", 
        back_populates="user", 
        foreign_keys="UserRole.user_id",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f'<DashboardUser {self.email}>'
    
    def get_id(self):
        """Required by Flask-Login."""
        return str(self.id)
    
    def is_authenticated(self):
        """Required by Flask-Login."""
        return True
    
    def is_anonymous(self):
        """Required by Flask-Login."""
        return False
    
    def is_admin(self):
        """Check if user has admin role (legacy method)."""
        return self.role == 'admin' or self.has_role('admin')
    
    def update_last_login(self):
        """Update the last login timestamp."""
        self.last_login = datetime.datetime.utcnow()
    
    # RBAC Methods
    def get_roles(self):
        """Get all active roles for this user."""
        return [ur.role for ur in self.user_roles if ur.is_active and not ur.is_expired() and ur.role.is_active]
    
    def get_role_names(self):
        """Get list of role names for this user."""
        return [role.name for role in self.get_roles()]
    
    def has_role(self, role_name):
        """Check if user has a specific role."""
        for user_role in self.user_roles:
            if (user_role.role.name == role_name and 
                user_role.is_active and 
                not user_role.is_expired() and 
                user_role.role.is_active):
                return True
        return False
    
    def has_any_role(self, role_names):
        """Check if user has any of the specified roles."""
        if isinstance(role_names, str):
            role_names = [role_names]
        return any(self.has_role(role) for role in role_names)
    
    def has_permission(self, permission_name):
        """Check if user has a specific permission through their roles."""
        for user_role in self.user_roles:
            if (user_role.is_active and 
                not user_role.is_expired() and 
                user_role.role.is_active and 
                user_role.role.has_permission(permission_name)):
                return True
        return False
    
    def has_any_permission(self, permission_names):
        """Check if user has any of the specified permissions."""
        if isinstance(permission_names, str):
            permission_names = [permission_names]
        return any(self.has_permission(perm) for perm in permission_names)
    
    def get_permissions(self):
        """Get all permissions for this user from all their active roles."""
        permissions = set()
        for user_role in self.user_roles:
            if (user_role.is_active and 
                not user_role.is_expired() and 
                user_role.role.is_active):
                role_permissions = user_role.role.get_permissions()
                permissions.update(role_permissions)
        return list(permissions)
    
    def get_permission_names(self):
        """Get list of permission names for this user."""
        return [perm.name for perm in self.get_permissions()]
    
    def assign_role(self, session, role_name, assigned_by_user_id=None, expires_at=None):
        """Assign a role to this user."""
        from db.models import Role  # Import here to avoid circular imports
        
        role = session.query(Role).filter_by(name=role_name, is_active=True).first()
        if not role:
            raise ValueError(f"Role '{role_name}' not found or inactive")
        
        # Check if user already has this role
        existing = session.query(UserRole).filter_by(
            user_id=self.id,
            role_id=role.id,
            is_active=True
        ).first()
        
        if existing and not existing.is_expired():
            return existing  # Already has active role
        
        # Create new role assignment
        user_role = UserRole(
            user_id=self.id,
            role_id=role.id,
            assigned_by=assigned_by_user_id,
            expires_at=expires_at
        )
        session.add(user_role)
        return user_role
    
    def remove_role(self, session, role_name):
        """Remove a role from this user."""
        for user_role in self.user_roles:
            if user_role.role.name == role_name and user_role.is_active:
                user_role.is_active = False
                session.add(user_role)
                return True
        return False
    
    def is_system_owner(self):
        """Check if this user is the system owner (first user)."""
        return self.has_role('owner')
    
    @classmethod
    def find_or_create_from_oauth(cls, session, provider, oauth_id, email, name=None, avatar_url=None):
        """Find existing user or create new one from OAuth data."""
        user = session.query(cls).filter_by(
            oauth_provider=provider,
            oauth_id=oauth_id
        ).first()
        
        if user:
            # Update user info in case it changed
            user.email = email
            user.name = name
            user.avatar_url = avatar_url
            user.update_last_login()
        else:
            # Create new user
            user = cls(
                oauth_provider=provider,
                oauth_id=oauth_id,
                email=email,
                name=name,
                avatar_url=avatar_url,
                role='user'  # Default legacy role for new users
            )
            session.add(user)
            session.flush()  # Get the user ID
            
            # Assign default RBAC role
            from db.models import Role  # Import here to avoid circular imports
            
            # Check if this is the first user (should be owner)
            user_count = session.query(cls).count()
            if user_count == 1:  # First user
                default_role = 'owner'
            else:
                default_role = 'guest'
            
            try:
                user.assign_role(session, default_role)
            except ValueError:
                # If default role doesn't exist, create guest role assignment later
                pass
        
        return user


class OAuthApplication(Base):
    """OAuth application configuration model."""
    
    __tablename__ = 'oauth_applications'
    
    id = Column(Integer, primary_key=True)
    provider = Column(String(50), nullable=False, unique=True)
    client_id = Column(String(255), nullable=False)
    client_secret_encrypted = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<OAuthApplication {self.provider}>'
    
    @property
    def client_secret(self):
        """Decrypt and return the client secret."""
        if not hasattr(self, '_encryption_key'):
            self._encryption_key = os.getenv('OAUTH_ENCRYPTION_KEY')
            if not self._encryption_key:
                raise ValueError("OAUTH_ENCRYPTION_KEY environment variable is required")
        
        fernet = Fernet(self._encryption_key.encode())
        return fernet.decrypt(self.client_secret_encrypted.encode()).decode()
    
    @client_secret.setter
    def client_secret(self, value):
        """Encrypt and store the client secret."""
        if not hasattr(self, '_encryption_key'):
            self._encryption_key = os.getenv('OAUTH_ENCRYPTION_KEY')
            if not self._encryption_key:
                raise ValueError("OAUTH_ENCRYPTION_KEY environment variable is required")
        
        fernet = Fernet(self._encryption_key.encode())
        self.client_secret_encrypted = fernet.encrypt(value.encode()).decode()
    
    @classmethod
    def get_active_config(cls, session, provider):
        """Get active OAuth configuration for a provider."""
        return session.query(cls).filter_by(
            provider=provider,
            is_active=True
        ).first()

# RBAC Models - Role-Based Access Control System

class Role(Base):
    """Role model for RBAC system."""
    
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def has_permission(self, permission_name):
        """Check if this role has a specific permission."""
        for role_perm in self.role_permissions:
            if role_perm.permission.name == permission_name and role_perm.is_active:
                return True
        return False
    
    def get_permissions(self):
        """Get all active permissions for this role."""
        return [rp.permission for rp in self.role_permissions if rp.is_active and rp.permission.is_active]


class Permission(Base):
    """Permission model for RBAC system."""
    
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    resource = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Permission {self.name}>'
    
    @property
    def resource_action(self):
        """Get the resource:action format."""
        return f"{self.resource}:{self.action}"


class UserRole(Base):
    """User-Role mapping table."""
    
    __tablename__ = 'user_roles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('dashboard_users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    assigned_by = Column(Integer, ForeignKey('dashboard_users.id'), nullable=True)
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("DashboardUser", foreign_keys=[user_id], back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
    assigned_by_user = relationship("DashboardUser", foreign_keys=[assigned_by])
    
    def __repr__(self):
        return f'<UserRole user_id={self.user_id} role_id={self.role_id}>'
    
    def is_expired(self):
        """Check if this role assignment has expired."""
        return self.expires_at and self.expires_at < datetime.datetime.utcnow()


class RolePermission(Base):
    """Role-Permission mapping table."""
    
    __tablename__ = 'role_permissions'
    
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False)
    granted_by = Column(Integer, ForeignKey('dashboard_users.id'), nullable=True)
    granted_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
    granted_by_user = relationship("DashboardUser")
    
    def __repr__(self):
        return f'<RolePermission role_id={self.role_id} permission_id={self.permission_id}>'


class UserSession(Base):
    """User session with permission caching."""
    
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('dashboard_users.id', ondelete='CASCADE'), nullable=False)
    session_token = Column(String(255), nullable=False, unique=True)
    permissions_cache = Column(Text, nullable=True)  # JSON array of cached permissions
    cache_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("DashboardUser")
    
    def __repr__(self):
        return f'<UserSession user_id={self.user_id}>'
    
    def is_cache_valid(self):
        """Check if the permissions cache is still valid."""
        return self.cache_expires_at and self.cache_expires_at > datetime.datetime.utcnow()
    
    def get_cached_permissions(self):
        """Get cached permissions as a list."""
        if not self.is_cache_valid():
            return None
        
        try:
            import json
            return json.loads(self.permissions_cache) if self.permissions_cache else []
        except json.JSONDecodeError:
            return None
    
    def set_cached_permissions(self, permissions, cache_duration_minutes=15):
        """Set cached permissions with expiration."""
        import json
        self.permissions_cache = json.dumps(permissions)
        self.cache_expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=cache_duration_minutes)