"""
CRUD (Create, Read, Update, Delete) operations for the database layer.

This module provides common database operations for the Corgi Recommender Service.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session

from db.models import (
    Post, Interaction, InteractionType, PrivacyLevel,
    CrawledPost, UserTimeline, CachedRecommendation
)
from db.session import db_session

logger = logging.getLogger(__name__)

def record_interaction_with_context(
    alias_id: str,
    post_id: str,
    interaction_type: InteractionType,
    context: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None
) -> Optional[Interaction]:
    """
    Record a user interaction with context information.
    
    Args:
        alias_id: User alias ID
        post_id: Post ID
        interaction_type: Type of interaction
        context: Additional context information
        timestamp: Interaction timestamp (defaults to now)
        
    Returns:
        Optional[Interaction]: Created interaction or None if failed
    """
    try:
        with db_session() as session:
            interaction = Interaction(
                alias_id=alias_id,
                post_id=post_id,
                interaction_type=interaction_type,
                context=context or {},
                timestamp=timestamp or datetime.utcnow()
            )
            
            session.add(interaction)
            session.commit()
            session.refresh(interaction)
            
            logger.info(f"Recorded interaction: {interaction_type.value} for user {alias_id} on post {post_id}")
            return interaction
            
    except Exception as e:
        logger.error(f"Failed to record interaction: {e}")
        return None

def get_user_interactions(
    session: Session,
    alias_id: str,
    limit: int = 100,
    interaction_types: Optional[List[InteractionType]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Interaction]:
    """
    Get interactions for a user.
    
    Args:
        session: Database session
        alias_id: User alias ID
        limit: Maximum number of interactions to return
        interaction_types: Filter by interaction types
        start_date: Filter interactions after this date
        end_date: Filter interactions before this date
        
    Returns:
        List[Interaction]: List of user interactions
    """
    try:
        query = session.query(Interaction).filter(Interaction.alias_id == alias_id)
        
        if interaction_types:
            query = query.filter(Interaction.interaction_type.in_(interaction_types))
            
        if start_date:
            query = query.filter(Interaction.timestamp >= start_date)
            
        if end_date:
            query = query.filter(Interaction.timestamp <= end_date)
        
        interactions = query.order_by(desc(Interaction.timestamp)).limit(limit).all()
        
        logger.debug(f"Retrieved {len(interactions)} interactions for user {alias_id}")
        return interactions
        
    except Exception as e:
        logger.error(f"Failed to get user interactions: {e}")
        return []

def get_recent_posts(
    session: Session,
    limit: int = 50,
    privacy_level: Optional[PrivacyLevel] = None,
    language_filter: Optional[List[str]] = None,
    exclude_synthetic: bool = False
) -> List[Post]:
    """
    Get recent posts from the database.
    
    Args:
        session: Database session
        limit: Maximum number of posts to return
        privacy_level: Filter by privacy level
        language_filter: Filter by language codes
        exclude_synthetic: Whether to exclude synthetic posts
        
    Returns:
        List[Post]: List of recent posts
    """
    try:
        query = session.query(Post)
        
        if privacy_level:
            query = query.filter(Post.privacy_level == privacy_level)
            
        if language_filter:
            query = query.filter(Post.language.in_(language_filter))
            
        if exclude_synthetic:
            query = query.filter(Post.is_synthetic == False)
        
        posts = query.order_by(desc(Post.created_at)).limit(limit).all()
        
        logger.debug(f"Retrieved {len(posts)} recent posts")
        return posts
        
    except Exception as e:
        logger.error(f"Failed to get recent posts: {e}")
        return []

def create_post(
    session: Session,
    post_id: str,
    author_name: str,
    content: str,
    created_at: Optional[datetime] = None,
    privacy_level: PrivacyLevel = PrivacyLevel.PUBLIC,
    language: str = 'en',
    is_synthetic: bool = False,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[Post]:
    """
    Create a new post in the database.
    
    Args:
        session: Database session
        post_id: Unique post ID
        author_name: Author's name
        content: Post content
        created_at: Post creation timestamp
        privacy_level: Privacy level of the post
        language: Language code
        is_synthetic: Whether this is a synthetic post
        metadata: Additional metadata
        
    Returns:
        Optional[Post]: Created post or None if failed
    """
    try:
        post = Post(
            post_id=post_id,
            author_name=author_name,
            content=content,
            created_at=created_at or datetime.utcnow(),
            privacy_level=privacy_level,
            language=language,
            is_synthetic=is_synthetic,
            metadata=metadata or {}
        )
        
        session.add(post)
        session.commit()
        session.refresh(post)
        
        logger.info(f"Created post {post_id} by {author_name}")
        return post
        
    except Exception as e:
        logger.error(f"Failed to create post: {e}")
        return None

def get_post_by_id(session: Session, post_id: str) -> Optional[Post]:
    """
    Get a post by its ID.
    
    Args:
        session: Database session
        post_id: Post ID to find
        
    Returns:
        Optional[Post]: Post if found, None otherwise
    """
    try:
        post = session.query(Post).filter(Post.post_id == post_id).first()
        return post
    except Exception as e:
        logger.error(f"Failed to get post by ID {post_id}: {e}")
        return None

def get_posts_by_author(
    session: Session,
    author_name: str,
    limit: int = 50
) -> List[Post]:
    """
    Get posts by a specific author.
    
    Args:
        session: Database session
        author_name: Author's name
        limit: Maximum number of posts to return
        
    Returns:
        List[Post]: List of posts by the author
    """
    try:
        posts = session.query(Post).filter(
            Post.author_name == author_name
        ).order_by(desc(Post.created_at)).limit(limit).all()
        
        logger.debug(f"Retrieved {len(posts)} posts by {author_name}")
        return posts
        
    except Exception as e:
        logger.error(f"Failed to get posts by author {author_name}: {e}")
        return []

def get_interaction_counts(
    session: Session,
    post_ids: List[str],
    interaction_type: Optional[InteractionType] = None
) -> Dict[str, int]:
    """
    Get interaction counts for posts.
    
    Args:
        session: Database session
        post_ids: List of post IDs
        interaction_type: Filter by interaction type
        
    Returns:
        Dict[str, int]: Post ID to interaction count mapping
    """
    try:
        query = session.query(
            Interaction.post_id,
            func.count(Interaction.id).label('count')
        ).filter(Interaction.post_id.in_(post_ids))
        
        if interaction_type:
            query = query.filter(Interaction.interaction_type == interaction_type)
        
        results = query.group_by(Interaction.post_id).all()
        
        counts = {post_id: 0 for post_id in post_ids}
        for result in results:
            counts[result.post_id] = result.count
            
        return counts
        
    except Exception as e:
        logger.error(f"Failed to get interaction counts: {e}")
        return {post_id: 0 for post_id in post_ids}

def delete_old_interactions(
    session: Session,
    older_than_days: int = 90,
    batch_size: int = 1000
) -> int:
    """
    Delete old interactions from the database.
    
    Args:
        session: Database session
        older_than_days: Delete interactions older than this many days
        batch_size: Number of records to delete per batch
        
    Returns:
        int: Number of interactions deleted
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        total_deleted = 0
        while True:
            # Delete in batches to avoid locking the database
            deleted = session.query(Interaction).filter(
                Interaction.timestamp < cutoff_date
            ).limit(batch_size).delete(synchronize_session=False)
            
            session.commit()
            total_deleted += deleted
            
            if deleted < batch_size:
                break
        
        logger.info(f"Deleted {total_deleted} interactions older than {older_than_days} days")
        return total_deleted
        
    except Exception as e:
        logger.error(f"Failed to delete old interactions: {e}")
        return 0

def get_user_activity_summary(
    session: Session,
    alias_id: str,
    days: int = 30
) -> Dict[str, Any]:
    """
    Get a summary of user activity over the specified period.
    
    Args:
        session: Database session
        alias_id: User alias ID
        days: Number of days to look back
        
    Returns:
        Dict[str, Any]: Activity summary
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get interaction counts by type
        interaction_counts = session.query(
            Interaction.interaction_type,
            func.count(Interaction.id).label('count')
        ).filter(
            and_(
                Interaction.alias_id == alias_id,
                Interaction.timestamp >= start_date
            )
        ).group_by(Interaction.interaction_type).all()
        
        # Get total interactions
        total_interactions = session.query(func.count(Interaction.id)).filter(
            and_(
                Interaction.alias_id == alias_id,
                Interaction.timestamp >= start_date
            )
        ).scalar() or 0
        
        # Get unique posts interacted with
        unique_posts = session.query(func.count(func.distinct(Interaction.post_id))).filter(
            and_(
                Interaction.alias_id == alias_id,
                Interaction.timestamp >= start_date
            )
        ).scalar() or 0
        
        summary = {
            'alias_id': alias_id,
            'period_days': days,
            'total_interactions': total_interactions,
            'unique_posts': unique_posts,
            'interaction_breakdown': {
                result.interaction_type.value: result.count
                for result in interaction_counts
            }
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get user activity summary: {e}")
        return {
            'alias_id': alias_id,
            'period_days': days,
            'total_interactions': 0,
            'unique_posts': 0,
            'interaction_breakdown': {}
        } 