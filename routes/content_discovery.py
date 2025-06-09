"""
Content Discovery API Routes

This module provides endpoints for content discovery and crawler management,
including status monitoring and statistics for the content crawling system.
"""

import json
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from db.connection import get_db_connection
from utils.auth import require_authentication
from utils.logging_decorator import log_api_call

# Create the content discovery blueprint
content_discovery_bp = Blueprint('content_discovery', __name__, url_prefix='/api/content')

@content_discovery_bp.route('/crawler/status', methods=['GET'])
@log_api_call
def get_crawler_status():
    """
    Get the current status of the content crawler.
    
    Returns:
        JSON response with crawler status information including:
        - total_posts: Total number of crawled posts
        - active_instances: Number of active instances being crawled
        - last_crawl_time: Timestamp of the last successful crawl
        - success: Boolean indicating if the request was successful
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get total posts count
                cursor.execute("SELECT COUNT(*) FROM posts")
                total_posts_result = cursor.fetchone()
                total_posts = total_posts_result[0] if total_posts_result else 0
                
                # Get active instances count (simplified - could be more sophisticated)
                cursor.execute("SELECT COUNT(DISTINCT author_id) FROM posts WHERE created_at > datetime('now', '-24 hours')")
                active_instances_result = cursor.fetchone()
                active_instances = active_instances_result[0] if active_instances_result else 0
                
                # Get last crawl time
                cursor.execute("SELECT MAX(created_at) FROM posts")
                last_crawl_result = cursor.fetchone()
                last_crawl_time = last_crawl_result[0] if last_crawl_result and last_crawl_result[0] else None
                
                return jsonify({
                    'success': True,
                    'data': {
                        'total_posts': total_posts,
                        'active_instances': active_instances,
                        'last_crawl_time': last_crawl_time.isoformat() if last_crawl_time else None,
                        'status': 'active' if last_crawl_time else 'inactive'
                    }
                })
                
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get crawler status: {str(e)}'
        }), 500

@content_discovery_bp.route('/discovery/stats', methods=['GET'])
@log_api_call
def get_discovery_stats():
    """
    Get content discovery statistics.
    
    Returns:
        JSON response with discovery statistics including:
        - language_distribution: Distribution of posts by language
        - engagement_metrics: Average engagement metrics
        - temporal_distribution: Posts distribution over time
        - success: Boolean indicating if the request was successful
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get language distribution
                cursor.execute("""
                    SELECT language, COUNT(*) as count 
                    FROM posts 
                    WHERE language IS NOT NULL 
                    GROUP BY language 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                language_distribution = [
                    {'language': row[0], 'count': row[1]} 
                    for row in cursor.fetchall()
                ]
                
                # Get engagement metrics
                cursor.execute("""
                    SELECT 
                        AVG(favorites) as avg_favorites,
                        AVG(boosts) as avg_boosts,
                        AVG(replies) as avg_replies
                    FROM posts
                    WHERE created_at > datetime('now', '-7 days')
                """)
                engagement_result = cursor.fetchone()
                engagement_metrics = {
                    'avg_favorites': float(engagement_result[0]) if engagement_result[0] else 0.0,
                    'avg_boosts': float(engagement_result[1]) if engagement_result[1] else 0.0,
                    'avg_replies': float(engagement_result[2]) if engagement_result[2] else 0.0
                } if engagement_result else {}
                
                # Get temporal distribution (posts per day for last 7 days)
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as post_date,
                        COUNT(*) as count
                    FROM posts
                    WHERE created_at > datetime('now', '-7 days')
                    GROUP BY DATE(created_at)
                    ORDER BY post_date DESC
                """)
                temporal_distribution = [
                    {'date': row[0].isoformat() if row[0] else None, 'count': row[1]}
                    for row in cursor.fetchall()
                ]
                
                return jsonify({
                    'success': True,
                    'data': {
                        'language_distribution': language_distribution,
                        'engagement_metrics': engagement_metrics,
                        'temporal_distribution': temporal_distribution,
                        'generated_at': datetime.now(timezone.utc).isoformat()
                    }
                })
                
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get discovery stats: {str(e)}'
        }), 500

@content_discovery_bp.route('/instances', methods=['GET'])
@log_api_call
def get_monitored_instances():
    """
    Get list of monitored instances and their status.
    
    Returns:
        JSON response with list of monitored instances and their crawling status
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get instances with recent activity
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN author_id LIKE 'https://%' THEN 
                                CASE 
                                    WHEN INSTR(SUBSTR(author_id, 9), '/') > 0 THEN
                                        SUBSTR(author_id, 9, INSTR(SUBSTR(author_id, 9), '/') - 1)
                                    ELSE 
                                        SUBSTR(author_id, 9)
                                END
                            WHEN author_id LIKE 'http://%' THEN 
                                CASE 
                                    WHEN INSTR(SUBSTR(author_id, 8), '/') > 0 THEN
                                        SUBSTR(author_id, 8, INSTR(SUBSTR(author_id, 8), '/') - 1)
                                    ELSE 
                                        SUBSTR(author_id, 8)
                                END
                            ELSE 'unknown'
                        END as instance,
                        COUNT(*) as post_count,
                        MAX(created_at) as last_post_time
                    FROM posts
                    WHERE created_at > datetime('now', '-30 days')
                    GROUP BY instance
                    ORDER BY post_count DESC
                    LIMIT 20
                """)
                
                instances = [
                    {
                        'instance': row[0] if row[0] else 'unknown',
                        'post_count': row[1],
                        'last_post_time': row[2].isoformat() if row[2] else None
                    }
                    for row in cursor.fetchall()
                ]
                
                return jsonify({
                    'success': True,
                    'data': {
                        'instances': instances,
                        'total_instances': len(instances)
                    }
                })
                
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get monitored instances: {str(e)}'
        }), 500

@content_discovery_bp.route('/trending', methods=['GET'])
@log_api_call
def get_trending_content():
    """
    Get trending content based on engagement metrics.
    
    Query Parameters:
        - language: Filter by language (optional)
        - limit: Number of results to return (default: 20, max: 100)
        - timeframe: Time window for trending calculation (1h, 6h, 24h, 7d)
    
    Returns:
        JSON response with trending posts
    """
    try:
        language = request.args.get('language')
        limit = min(int(request.args.get('limit', 20)), 100)
        timeframe = request.args.get('timeframe', '24h')
        
        # Convert timeframe to SQLite interval format
        timeframe_intervals = {
            '1h': '-1 hours',
            '6h': '-6 hours', 
            '24h': '-24 hours',
            '7d': '-7 days'
        }
        interval = timeframe_intervals.get(timeframe, '-24 hours')
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Build query with optional language filter
                base_query = """
                    SELECT 
                        id, content, author_name, created_at, language,
                        favorites, boosts, replies,
                        (favorites * 1.0 + boosts * 2.0 + replies * 1.5) as engagement_score
                    FROM posts
                    WHERE created_at > datetime('now', ?)
                """
                
                params = [interval]
                if language:
                    base_query += " AND language = ?"
                    params.append(language)
                
                base_query += " ORDER BY engagement_score DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(base_query, params)
                
                trending_posts = [
                    {
                        'id': row[0],
                        'content': row[1][:200] + '...' if len(row[1]) > 200 else row[1],  # Truncate content
                        'author_name': row[2],
                        'created_at': row[3].isoformat() if row[3] else None,
                        'language': row[4],
                        'favorites': row[5],
                        'boosts': row[6],
                        'replies': row[7],
                        'engagement_score': float(row[8]) if row[8] else 0.0
                    }
                    for row in cursor.fetchall()
                ]
                
                return jsonify({
                    'success': True,
                    'data': {
                        'trending_posts': trending_posts,
                        'filters': {
                            'language': language,
                            'timeframe': timeframe,
                            'limit': limit
                        },
                        'total_results': len(trending_posts)
                    }
                })
                
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get trending content: {str(e)}'
        }), 500

# Error handlers for the blueprint
@content_discovery_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors for content discovery endpoints."""
    return jsonify({
        'success': False,
        'error': 'Content discovery endpoint not found'
    }), 404

@content_discovery_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors for content discovery endpoints."""
    return jsonify({
        'success': False,
        'error': 'Internal server error in content discovery'
    }), 500 