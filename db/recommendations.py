"""
Database Recommendations Module for the Corgi Recommender Service.

This module provides database operations for managing and retrieving recommendations,
including personalized recommendations and cold start scenarios.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from db.connection import get_db_connection
from db.models import PostMetadata, UserAlias, RecommendationLog, CachedRecommendation

logger = logging.getLogger(__name__)

def get_recommendations(user_alias: str, limit: int = 10, offset: int = 0, 
                       categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Get personalized recommendations for a user.
    
    Args:
        user_alias: The user's privacy-preserving alias
        limit: Maximum number of recommendations to return
        offset: Number of recommendations to skip (for pagination)
        categories: Optional list of categories to filter by
        
    Returns:
        List of recommendation dictionaries with post data and metadata
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # First try to get cached recommendations
                cached_recs = _get_cached_recommendations(cur, user_alias, limit, offset)
                if cached_recs:
                    logger.info(f"Retrieved {len(cached_recs)} cached recommendations for user {user_alias}")
                    return cached_recs
                
                # If no cached recommendations, generate fresh ones
                base_query = """
                    SELECT DISTINCT
                        pm.post_id,
                        pm.content,
                        pm.author_name,
                        pm.created_at,
                        pm.language,
                        pm.privacy_level,
                        pm.post_metadata,
                        COALESCE(interaction_score.score, 0) as relevance_score
                    FROM post_metadata pm
                    LEFT JOIN (
                        SELECT 
                            post_id,
                            COUNT(*) * 0.7 + AVG(CASE WHEN interaction_type = 'like' THEN 3 
                                                       WHEN interaction_type = 'share' THEN 5
                                                       WHEN interaction_type = 'comment' THEN 4
                                                       ELSE 1 END) as score
                        FROM interactions 
                        WHERE created_at > %s
                        GROUP BY post_id
                    ) interaction_score ON pm.post_id = interaction_score.post_id
                    WHERE pm.created_at > %s 
                """
                
                params = [
                    datetime.utcnow() - timedelta(days=7),  # Recent interactions
                    datetime.utcnow() - timedelta(days=3)   # Recent posts
                ]
                
                # Add category filter if specified
                if categories:
                    placeholders = ','.join(['%s'] * len(categories))
                    base_query += f" AND pm.category IN ({placeholders})"
                    params.extend(categories)
                
                # Add privacy and quality filters
                base_query += """
                    AND pm.privacy_level IN ('public', 'limited')
                    AND pm.content IS NOT NULL
                    AND LENGTH(pm.content) > 10
                    ORDER BY relevance_score DESC, pm.created_at DESC
                    LIMIT %s OFFSET %s
                """
                
                params.extend([limit, offset])
                
                cur.execute(base_query, params)
                rows = cur.fetchall()
                
                recommendations = []
                for row in rows:
                    rec = {
                        'post_id': row[0],
                        'content': row[1],
                        'author_name': row[2], 
                        'created_at': row[3].isoformat() if row[3] else None,
                        'language': row[4],
                        'privacy_level': row[5],
                        'metadata': row[6] or {},
                        'relevance_score': float(row[7]) if row[7] else 0.0,
                        'recommendation_type': 'personalized'
                    }
                    recommendations.append(rec)
                
                # Cache the recommendations for future use
                _cache_recommendations(conn, user_alias, recommendations)
                
                logger.info(f"Generated {len(recommendations)} fresh recommendations for user {user_alias}")
                return recommendations
                
    except Exception as e:
        logger.error(f"Error getting recommendations for user {user_alias}: {str(e)}")
        # Fallback to cold start recommendations
        return get_cold_start_recommendations(limit, offset)

def get_cold_start_recommendations(limit: int = 10, offset: int = 0,
                                 language: str = 'en') -> List[Dict[str, Any]]:
    """
    Get cold start recommendations for new users or when personalized recs fail.
    
    Args:
        limit: Maximum number of recommendations to return
        offset: Number of recommendations to skip (for pagination)
        language: Preferred language for recommendations
        
    Returns:
        List of popular/trending post recommendations
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get trending posts based on recent interactions
                query = """
                    SELECT 
                        pm.post_id,
                        pm.content,
                        pm.author_name,
                        pm.created_at,
                        pm.language,
                        pm.privacy_level,
                        pm.post_metadata,
                        COALESCE(trend_score.score, 0) as trending_score
                    FROM post_metadata pm
                    LEFT JOIN (
                        SELECT 
                            post_id,
                            COUNT(*) * 1.0 + 
                            SUM(CASE WHEN interaction_type = 'like' THEN 2 
                                     WHEN interaction_type = 'share' THEN 4
                                     WHEN interaction_type = 'comment' THEN 3
                                     ELSE 1 END) * 
                            EXP(-EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0) as score
                        FROM interactions 
                        WHERE created_at > %s
                        GROUP BY post_id
                        HAVING COUNT(*) >= 2
                    ) trend_score ON pm.post_id = trend_score.post_id
                    WHERE pm.created_at > %s 
                    AND pm.privacy_level = 'public'
                    AND pm.content IS NOT NULL
                    AND LENGTH(pm.content) > 20
                """
                
                params = [
                    datetime.utcnow() - timedelta(days=2),  # Recent interactions
                    datetime.utcnow() - timedelta(days=7)   # Recent posts
                ]
                
                # Add language preference if specified
                if language and language != 'any':
                    query += " AND pm.language = %s"
                    params.append(language)
                
                query += """
                    ORDER BY trending_score DESC, pm.created_at DESC
                    LIMIT %s OFFSET %s
                """
                
                params.extend([limit, offset])
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                recommendations = []
                for row in rows:
                    rec = {
                        'post_id': row[0],
                        'content': row[1],
                        'author_name': row[2],
                        'created_at': row[3].isoformat() if row[3] else None,
                        'language': row[4],
                        'privacy_level': row[5],
                        'metadata': row[6] or {},
                        'trending_score': float(row[7]) if row[7] else 0.0,
                        'recommendation_type': 'cold_start'
                    }
                    recommendations.append(rec)
                
                # If we don't have enough trending posts, add some high-quality recent posts
                if len(recommendations) < limit:
                    additional_needed = limit - len(recommendations)
                    fallback_recs = _get_quality_fallback_posts(
                        conn, additional_needed, language, [r['post_id'] for r in recommendations]
                    )
                    recommendations.extend(fallback_recs)
                
                logger.info(f"Retrieved {len(recommendations)} cold start recommendations")
                return recommendations
                
    except Exception as e:
        logger.error(f"Error getting cold start recommendations: {str(e)}")
        return []

def _get_cached_recommendations(cursor, user_alias: str, limit: int, offset: int) -> List[Dict[str, Any]]:
    """Get cached recommendations if they exist and are still fresh."""
    try:
        cursor.execute("""
            SELECT recommendation_data, created_at
            FROM cached_recommendations 
            WHERE user_alias = %s 
            AND created_at > %s
            ORDER BY created_at DESC
            LIMIT 1
        """, [user_alias, datetime.utcnow() - timedelta(hours=1)])
        
        row = cursor.fetchone()
        if row:
            cached_data = row[0]
            if isinstance(cached_data, str):
                import json
                cached_data = json.loads(cached_data)
            
            # Apply pagination to cached results
            start_idx = offset
            end_idx = offset + limit
            return cached_data[start_idx:end_idx] if isinstance(cached_data, list) else []
        
        return []
    except Exception as e:
        logger.warning(f"Error retrieving cached recommendations: {str(e)}")
        return []

def _cache_recommendations(connection, user_alias: str, recommendations: List[Dict[str, Any]]):
    """Cache recommendations for future use."""
    try:
        import json
        with connection.cursor() as cur:
            cur.execute("""
                INSERT INTO cached_recommendations (user_alias, recommendation_data, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_alias) DO UPDATE SET
                    recommendation_data = EXCLUDED.recommendation_data,
                    created_at = EXCLUDED.created_at
            """, [user_alias, json.dumps(recommendations), datetime.utcnow()])
        connection.commit()
    except Exception as e:
        logger.warning(f"Error caching recommendations: {str(e)}")

def _get_quality_fallback_posts(connection, limit: int, language: str, 
                               exclude_post_ids: List[str]) -> List[Dict[str, Any]]:
    """Get high-quality posts as fallback when trending posts are insufficient."""
    try:
        with connection.cursor() as cur:
            exclude_clause = ""
            params = []
            
            if exclude_post_ids:
                placeholders = ','.join(['%s'] * len(exclude_post_ids))
                exclude_clause = f" AND pm.post_id NOT IN ({placeholders})"
                params.extend(exclude_post_ids)
            
            query = f"""
                SELECT 
                    pm.post_id,
                    pm.content,
                    pm.author_name,
                    pm.created_at,
                    pm.language,
                    pm.privacy_level,
                    pm.post_metadata,
                    LENGTH(pm.content) * 0.1 + 
                    EXTRACT(EPOCH FROM (NOW() - pm.created_at)) / -86400.0 as quality_score
                FROM post_metadata pm
                WHERE pm.created_at > %s
                AND pm.privacy_level = 'public'
                AND pm.content IS NOT NULL
                AND LENGTH(pm.content) BETWEEN 50 AND 2000
                {exclude_clause}
            """
            
            params.insert(0, datetime.utcnow() - timedelta(days=14))
            
            if language and language != 'any':
                query += " AND pm.language = %s"
                params.append(language)
            
            query += " ORDER BY quality_score DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            fallback_recs = []
            for row in rows:
                rec = {
                    'post_id': row[0],
                    'content': row[1],
                    'author_name': row[2],
                    'created_at': row[3].isoformat() if row[3] else None,
                    'language': row[4],
                    'privacy_level': row[5],
                    'metadata': row[6] or {},
                    'quality_score': float(row[7]) if row[7] else 0.0,
                    'recommendation_type': 'quality_fallback'
                }
                fallback_recs.append(rec)
            
            return fallback_recs
            
    except Exception as e:
        logger.warning(f"Error getting quality fallback posts: {str(e)}")
        return []

def log_recommendation_interaction(user_alias: str, post_id: str, interaction_type: str,
                                 recommendation_source: str = 'unknown'):
    """
    Log when a user interacts with a recommended post.
    
    Args:
        user_alias: User's privacy-preserving alias
        post_id: ID of the post that was interacted with
        interaction_type: Type of interaction (view, like, share, etc.)
        recommendation_source: Source of the recommendation (personalized, cold_start, etc.)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO recommendation_logs 
                    (alias_id, post_id, recommended_at, reason, model_version)
                    VALUES (%s, %s, %s, %s, %s)
                """, [
                    user_alias, post_id, datetime.utcnow(), 
                    f"{interaction_type}_from_{recommendation_source}", "v1.0"
                ])
            conn.commit()
            logger.info(f"Logged recommendation interaction: {user_alias} -> {post_id} ({interaction_type})")
    except Exception as e:
        logger.error(f"Error logging recommendation interaction: {str(e)}")

def get_recommendation_stats(user_alias: str, days_back: int = 7) -> Dict[str, Any]:
    """
    Get recommendation statistics for a user.
    
    Args:
        user_alias: User's privacy-preserving alias
        days_back: Number of days to look back for statistics
        
    Returns:
        Dictionary with recommendation statistics
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_recommendations,
                        COUNT(DISTINCT post_id) as unique_posts,
                        reason,
                        COUNT(*) as count_by_type
                    FROM recommendation_logs 
                    WHERE alias_id = %s 
                    AND recommended_at > %s
                    GROUP BY reason
                """, [user_alias, datetime.utcnow() - timedelta(days=days_back)])
                
                rows = cur.fetchall()
                
                stats = {
                    'total_recommendations': sum(row[0] for row in rows),
                    'unique_posts_recommended': sum(row[1] for row in rows),
                    'recommendation_types': {},
                    'period_days': days_back
                }
                
                for row in rows:
                    rec_type = row[2] or 'unknown'
                    stats['recommendation_types'][rec_type] = row[3]
                
                return stats
                
    except Exception as e:
        logger.error(f"Error getting recommendation stats: {str(e)}")
        return {'error': str(e)}

def clear_stale_cached_recommendations(hours_old: int = 24):
    """
    Clear cached recommendations older than specified hours.
    
    Args:
        hours_old: Age threshold in hours for clearing cached recommendations
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM cached_recommendations 
                    WHERE created_at < %s
                """, [datetime.utcnow() - timedelta(hours=hours_old)])
                
                deleted_count = cur.rowcount
                conn.commit()
                
                logger.info(f"Cleared {deleted_count} stale cached recommendations")
                return deleted_count
                
    except Exception as e:
        logger.error(f"Error clearing stale cached recommendations: {str(e)}")
        return 0 