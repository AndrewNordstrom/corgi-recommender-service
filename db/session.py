"""
Database session management for the Corgi Recommender Service.

This module provides connection and session management for SQLAlchemy,
with support for both SQLite and PostgreSQL databases.
"""

import os
import logging
import datetime
import os
from typing import Optional, Generator, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.pool import StaticPool

from config import DB_CONFIG

# Set up logging
logger = logging.getLogger(__name__)

# Determine if we should use the in-memory database
USE_IN_MEMORY_DB = os.getenv("USE_IN_MEMORY_DB", "false").lower() == "true"

# Default database URL (can be overridden by environment variables)
DEFAULT_DB_URL = "sqlite:///data/corgi_recommender.db"

# Get database URL from environment variable with fallbacks
DB_URL = os.getenv("CORGI_DB_URL", os.getenv("DATABASE_URL", DEFAULT_DB_URL))

# In-memory SQLite connection string
IN_MEMORY_DB_URL = "sqlite:///:memory:"

# SQLite database path for file-based SQLite
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", DB_URL)

# Engine instances
sqlite_engine = None
postgres_engine = None
Session = None

def get_database_url() -> str:
    """
    Get the database URL based on configuration.
    
    Returns:
        str: The database URL for SQLAlchemy
    """
    if USE_IN_MEMORY_DB:
        logger.info("Using in-memory SQLite database")
        return IN_MEMORY_DB_URL
    
    # Check if we're using an explicit DB URL from environment
    if DB_URL:
        if DB_URL.startswith("sqlite:"):
            logger.info(f"Using SQLite database from environment: {DB_URL}")
            return DB_URL
        elif DB_URL.startswith("postgresql:"):
            logger.info(f"Using PostgreSQL database from environment: {DB_URL}")
            return DB_URL
    
    # If using file-based SQLite explicitly
    if os.getenv("USE_SQLITE", "false").lower() == "true":
        logger.info(f"Using SQLite database (explicit): {SQLITE_DB_PATH}")
        return SQLITE_DB_PATH
    
    # Otherwise, fall back to PostgreSQL with DB_CONFIG
    pg_config = DB_CONFIG.copy()
    pg_url = f"postgresql://{pg_config['user']}:{pg_config['password']}@{pg_config['host']}:{pg_config['port']}/{pg_config['dbname']}"
    logger.info(f"Using PostgreSQL database from DB_CONFIG: {pg_url.replace(pg_config['password'], '******')}")
    return pg_url

def setup_sqlite_for_json(engine):
    """Configure SQLite to handle JSON data type properly."""
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Add JSON serialization/deserialization for SQLite
    import json
    import sqlalchemy.types as types
    
    class JSONEncodedDict(types.TypeDecorator):
        impl = types.TEXT
        
        def process_bind_param(self, value, dialect):
            if value is not None:
                value = json.dumps(value)
            return value
            
        def process_result_value(self, value, dialect):
            if value is not None:
                value = json.loads(value)
            return value
    
    # Replace JSON type with our SQLite-compatible version
    from sqlalchemy import JSON
    JSON = JSONEncodedDict

def init_db_engine():
    """
    Initialize the database engine based on configuration.
    
    Returns:
        SQLAlchemy engine instance
    """
    global sqlite_engine, postgres_engine, Session
    
    db_url = get_database_url()
    
    if db_url.startswith('sqlite'):
        # SQLite-specific configuration
        connect_args = {}
        if db_url == IN_MEMORY_DB_URL:
            # For in-memory SQLite, use StaticPool to keep the connection alive
            connect_args = {"check_same_thread": False}
            engine = create_engine(
                db_url, 
                connect_args=connect_args,
                poolclass=StaticPool,
                echo=os.getenv("SQL_ECHO", "false").lower() == "true"
            )
        else:
            # For file-based SQLite
            engine = create_engine(
                db_url,
                connect_args=connect_args,
                echo=os.getenv("SQL_ECHO", "false").lower() == "true"
            )
        
        setup_sqlite_for_json(engine)
        sqlite_engine = engine
        logger.info(f"Initialized SQLite engine: {db_url}")
    else:
        # PostgreSQL configuration
        engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true"
        )
        postgres_engine = engine
        logger.info(f"Initialized PostgreSQL engine: {db_url.replace(DB_CONFIG['password'], '*****')}")
    
    # Create session factory
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Session = scoped_session(session_factory)
    
    # Create all tables if they don't exist
    create_all_tables(engine)
    
    return engine

def get_engine():
    """
    Get the current database engine.
    
    Returns:
        SQLAlchemy engine instance
    """
    global sqlite_engine, postgres_engine
    
    if USE_IN_MEMORY_DB or os.getenv("USE_SQLITE", "false").lower() == "true":
        if sqlite_engine is None:
            init_db_engine()
        return sqlite_engine
    else:
        if postgres_engine is None:
            init_db_engine()
        return postgres_engine

def get_session() -> Session:
    """
    Get a new database session.
    
    Returns:
        SQLAlchemy Session object
    """
    global Session
    
    if Session is None:
        init_db_engine()
    
    return Session()

@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Yields:
        SQLAlchemy Session object
    
    Usage:
        with db_session() as session:
            results = session.query(Model).all()
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        session.close()

def create_all_tables(engine):
    """
    Create all SQLAlchemy tables if they don't exist.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    try:
        from db.models import Base
        Base.metadata.create_all(engine)
        logger.info("Created all SQLAlchemy tables")
        
        # Seed initial RBAC data if needed
        seed_rbac_data(engine)
        
    except Exception as e:
        logger.error(f"Error creating SQLAlchemy tables: {e}")
        raise

def seed_rbac_data(engine):
    """
    Seed initial RBAC data (roles and permissions) if tables are empty.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    try:
        from db.models import Role, Permission, RolePermission
        
        # Create a temporary session to check and seed data
        temp_session_factory = sessionmaker(bind=engine)
        temp_session = temp_session_factory()
        
        try:
            # Check if roles exist
            role_count = temp_session.query(Role).count()
            if role_count == 0:
                logger.info("Seeding initial RBAC roles...")
                
                # Create default roles
                roles = [
                    Role(name="admin", display_name="Administrator", description="Full system access", is_system_role=True),
                    Role(name="owner", display_name="Owner", description="System owner with all permissions", is_system_role=True),
                    Role(name="user", display_name="User", description="Basic user access", is_system_role=True),
                    Role(name="guest", display_name="Guest", description="Limited read-only access", is_system_role=True),
                ]
                
                for role in roles:
                    temp_session.add(role)
                
                temp_session.commit()
                logger.info(f"Created {len(roles)} default roles")
            
            # Check if permissions exist
            permission_count = temp_session.query(Permission).count()
            if permission_count == 0:
                logger.info("Seeding initial RBAC permissions...")
                
                # Create default permissions
                permissions = [
                    # User management
                    Permission(name="users:read", display_name="Read Users", resource="users", action="read"),
                    Permission(name="users:write", display_name="Write Users", resource="users", action="write"),
                    Permission(name="users:delete", display_name="Delete Users", resource="users", action="delete"),
                    
                    # Analytics
                    Permission(name="analytics:read", display_name="Read Analytics", resource="analytics", action="read"),
                    Permission(name="analytics:write", display_name="Write Analytics", resource="analytics", action="write"),
                    
                    # Experiments
                    Permission(name="experiments:read", display_name="Read Experiments", resource="experiments", action="read"),
                    Permission(name="experiments:write", display_name="Write Experiments", resource="experiments", action="write"),
                    Permission(name="experiments:delete", display_name="Delete Experiments", resource="experiments", action="delete"),
                    
                    # System administration
                    Permission(name="system:admin", display_name="System Admin", resource="system", action="admin"),
                    Permission(name="system:config", display_name="System Config", resource="system", action="config"),
                    
                    # Content management
                    Permission(name="content:read", display_name="Read Content", resource="content", action="read"),
                    Permission(name="content:write", display_name="Write Content", resource="content", action="write"),
                    Permission(name="content:moderate", display_name="Moderate Content", resource="content", action="moderate"),
                ]
                
                for permission in permissions:
                    temp_session.add(permission)
                
                temp_session.commit()
                logger.info(f"Created {len(permissions)} default permissions")
                
                # Assign permissions to roles
                admin_role = temp_session.query(Role).filter_by(name="admin").first()
                owner_role = temp_session.query(Role).filter_by(name="owner").first()
                user_role = temp_session.query(Role).filter_by(name="user").first()
                guest_role = temp_session.query(Role).filter_by(name="guest").first()
                
                if admin_role and owner_role:
                    # Admin gets most permissions
                    admin_permissions = [
                        "users:read", "users:write", "analytics:read", "analytics:write",
                        "experiments:read", "experiments:write", "content:read", "content:write", "content:moderate"
                    ]
                    
                    # Owner gets all permissions
                    owner_permissions = [p.name for p in permissions]
                    
                    # User gets basic permissions
                    user_permissions = ["content:read", "analytics:read"]
                    
                    # Guest gets minimal permissions
                    guest_permissions = ["content:read"]
                    
                    # Create role-permission mappings
                    role_permission_mappings = [
                        (admin_role, admin_permissions),
                        (owner_role, owner_permissions),
                        (user_role, user_permissions),
                        (guest_role, guest_permissions),
                    ]
                    
                    for role, permission_names in role_permission_mappings:
                        for perm_name in permission_names:
                            permission = temp_session.query(Permission).filter_by(name=perm_name).first()
                            if permission:
                                role_perm = RolePermission(role_id=role.id, permission_id=permission.id)
                                temp_session.add(role_perm)
                    
                    temp_session.commit()
                    logger.info("Assigned permissions to roles")
        
        except Exception as e:
            temp_session.rollback()
            logger.error(f"Error seeding RBAC data: {e}")
        finally:
            temp_session.close()
            
    except Exception as e:
        logger.error(f"Error in RBAC seeding: {e}")