#!/usr/bin/env python3
"""
Test suite for Language-Aware Trending Post Aggregator (TODO #113a)

This test suite validates the enhanced Active Content Crawling System
with sophisticated language detection and trending aggregation capabilities.
"""

import pytest
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from tasks.content_crawler import (
    calculate_trending_score,
    get_language_specific_trending_posts,
)
from utils.language_detector import (
    detect_language_with_confidence,
    batch_detect_languages,
    get_language_statistics
)
from utils.recommendation_engine import get_dynamic_cold_start_posts


class TestLanguageAwareTrendingAggregator:
    """Test the language-aware trending post aggregator system."""
    
    def test_enhanced_trending_score_calculation(self):
        """Test the enhanced trending score calculation with multiple factors."""
        # Create mock post objects
        fresh_viral_post = Mock()
        fresh_viral_post.favourites_count = 512
        fresh_viral_post.reblogs_count = 198
        fresh_viral_post.replies_count = 76
        fresh_viral_post.content = "This is a substantial viral post with rich content about technology trends and amazing developments in the field!"
        fresh_viral_post.created_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        fresh_viral_post.media_attachments = [Mock()]  # Has media
        fresh_viral_post.tags = [Mock(), Mock(), Mock()]  # Multiple hashtags
        
        engagement_velocity = 50.0  # Very high velocity (50 engagements per hour)
        trending_score = calculate_trending_score(fresh_viral_post, engagement_velocity)
        
        # Verify high trending score for viral content
        assert trending_score > 100.0, "Viral content should have high trending score"
        assert isinstance(trending_score, float)
        
        # Test older post with lower engagement
        older_post = Mock()
        older_post.favourites_count = 25
        older_post.reblogs_count = 8
        older_post.replies_count = 3
        older_post.content = "Short post"
        older_post.created_at = datetime.now(timezone.utc) - timedelta(hours=36)
        older_post.media_attachments = []
        older_post.tags = []
        
        older_score = calculate_trending_score(older_post, 2.0)
        
        # Verify time decay affects scoring
        assert older_score < trending_score, "Older posts should have lower scores"
        assert older_score > 0, "All posts should have positive scores"
    
    def test_language_detection_with_confidence(self):
        """Test enhanced language detection with confidence scoring."""
        test_cases = [
            ("This is a wonderful English text about technology!", 'en', 0.05),
            ("Das ist ein wunderschöner deutscher Text über Technologie!", 'de', 0.15),
            ("Esta es una hermosa oración en español sobre tecnología!", 'es', 0.15),
            ("C'est un beau texte français sur la technologie!", 'fr', 0.15),
            ("", 'en', 0.0),  # Empty text defaults to English
            ("Short", 'en', 0.1)  # Very short text has low confidence
        ]
        
        for text, expected_lang, min_confidence in test_cases:
            language, confidence = detect_language_with_confidence(text)
            
            assert language == expected_lang, f"Language detection failed for: {text}"
            assert confidence >= min_confidence, f"Confidence too low for: {text}"
            assert confidence <= 1.0, f"Confidence too high for: {text}"
    
    def test_batch_language_detection(self):
        """Test efficient batch language detection."""
        texts = [
            "English text here",
            "Deutscher Text hier",
            "Texto en español aquí",
            "Texte français ici",
            "これは日本語のテキストです"
        ]
        
        results = batch_detect_languages(texts)
        
        assert len(results) == len(texts)
        
        for i, (language, confidence) in enumerate(results):
            assert isinstance(language, str)
            assert isinstance(confidence, float)
            assert confidence >= 0.0
            assert confidence <= 1.0
    
    def test_language_statistics_calculation(self):
        """Test language distribution statistics calculation."""
        detected_languages = ['en', 'en', 'de', 'es', 'en', 'fr', 'de', 'en']
        
        stats = get_language_statistics(detected_languages)
        
        assert stats['total'] == 8
        assert stats['dominant_language'] == 'en'
        assert stats['unique_languages'] == 4
        assert stats['diversity_score'] > 0.0
        assert 'en' in stats['distribution']
        assert stats['distribution']['en']['count'] == 4
        assert stats['distribution']['en']['percentage'] == 50.0
    
    @patch('tasks.content_crawler.get_db_connection')
    def test_get_language_specific_trending_posts(self, mock_db):
        """Test retrieval of trending posts for specific languages."""
        # Mock database results
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results for English posts
        mock_cursor.fetchall.return_value = [
            (
                'trending_en_001', 'Amazing English content!', 
                datetime.now(timezone.utc), 'author1', 'user1',
                'mastodon.social', 125, 45, 23, 89.5, 15.2,
                '["tech", "trending"]', datetime.now(timezone.utc), 'fresh'
            ),
            (
                'trending_en_002', 'Another great English post!',
                datetime.now(timezone.utc), 'author2', 'user2', 
                'mastodon.world', 98, 34, 18, 72.1, 12.8,
                '["news", "viral"]', datetime.now(timezone.utc), 'relevant'
            )
        ]
        
        # Test retrieval
        trending_posts = get_language_specific_trending_posts('en', limit=50)
        
        assert len(trending_posts) == 2
        
        # Verify post structure
        first_post = trending_posts[0]
        assert first_post['post_id'] == 'trending_en_001'
        assert first_post['language'] == 'en'
        assert first_post['trending_score'] > 0
        assert isinstance(first_post['tags'], list)
        assert first_post['tags'] == ['tech', 'trending']
        
        # Verify database query was called correctly
        mock_cursor.execute.assert_called_once()
        query_args = mock_cursor.execute.call_args[0]
        assert 'language = %s' in query_args[0]
        assert query_args[1] == ('en', 50)
    
    @patch('tasks.content_crawler.get_db_connection')
    def test_get_language_specific_trending_posts_empty_result(self, mock_db):
        """Test handling of empty results for language-specific queries."""
        # Mock empty database results
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        trending_posts = get_language_specific_trending_posts('ja', limit=20)
        
        assert len(trending_posts) == 0
        assert isinstance(trending_posts, list)
    
    @patch('utils.recommendation_engine.get_db_connection')
    @patch('tasks.content_crawler.get_db_connection')
    @patch('tasks.content_crawler.get_language_specific_trending_posts')
    @patch('utils.language_detector.get_supported_languages')
    def test_enhanced_cold_start_with_language_aware_trending(self, mock_languages, mock_trending, mock_crawler_db, mock_rec_db):
        """Test enhanced cold start system using language-aware trending posts."""
        # Setup proper mock for database connection context manager
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # Return empty results for fallback queries
        mock_cursor.execute.return_value = None
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        
        mock_crawler_db.return_value = mock_conn
        mock_rec_db.return_value = mock_conn
        
        # Mock supported languages
        mock_languages.return_value = ['en', 'de', 'es', 'fr']
        
        # Mock trending posts for different languages
        def mock_trending_posts(language, limit):
            if language == 'en':
                # Return enough posts to satisfy the limit (10) to avoid database fallback
                posts = []
                for i in range(min(limit, 5)):  # Return up to 5 English posts
                    posts.append({
                        'post_id': f'trending_en_{i:03d}',
                        'content': f'Amazing English trending content #{i+1}!',
                        'created_at': datetime.now(timezone.utc),
                        'author_username': f'english_author_{i+1}',
                        'source_instance': 'mastodon.social',
                        'language': 'en',
                        'favourites_count': 125 + (i * 10),
                        'reblogs_count': 45 + (i * 5),
                        'replies_count': 23 + (i * 2),
                        'trending_score': 89.5 - (i * 2),
                        'engagement_velocity': 15.2 - (i * 0.5),
                        'tags': ['tech', 'trending']
                    })
                return posts
            elif language == 'de':
                # Return enough German posts to supplement
                posts = []
                for i in range(min(limit, 3)):  # Return up to 3 German posts
                    posts.append({
                        'post_id': f'trending_de_{i:03d}',
                        'content': f'Erstaunlicher deutscher Inhalt #{i+1}!',
                        'created_at': datetime.now(timezone.utc),
                        'author_username': f'german_author_{i+1}',
                        'source_instance': 'mastodon.de',
                        'language': 'de',
                        'favourites_count': 89 + (i * 8),
                        'reblogs_count': 31 + (i * 4),
                        'replies_count': 15 + (i * 1),
                        'trending_score': 72.3 - (i * 1.5),
                        'engagement_velocity': 12.8 - (i * 0.3),
                        'tags': ['tech', 'deutschland']
                    })
                return posts
            elif language == 'es':
                # Return some Spanish posts
                posts = []
                for i in range(min(limit, 2)):  # Return up to 2 Spanish posts
                    posts.append({
                        'post_id': f'trending_es_{i:03d}',
                        'content': f'¡Contenido español increíble #{i+1}!',
                        'created_at': datetime.now(timezone.utc),
                        'author_username': f'spanish_author_{i+1}',
                        'source_instance': 'mastodon.es',
                        'language': 'es',
                        'favourites_count': 75 + (i * 6),
                        'reblogs_count': 25 + (i * 3),
                        'replies_count': 12 + (i * 1),
                        'trending_score': 65.8 - (i * 1.2),
                        'engagement_velocity': 11.5 - (i * 0.2),
                        'tags': ['tecnología', 'trending']
                    })
                return posts
            else:
                return []
        
        mock_trending.side_effect = mock_trending_posts
        
        # Test cold start with English preference
        cold_start_posts = get_dynamic_cold_start_posts(user_language='en', limit=10)
        
        assert len(cold_start_posts) > 0
        
        # Verify the first post is English
        first_post = cold_start_posts[0]
        assert first_post['language'] == 'en'
        assert first_post['is_crawled_content'] == True
        assert first_post['is_trending_content'] == True
        assert first_post['trending_score'] > 0
        
        # Verify Mastodon compatibility
        assert 'id' in first_post
        assert 'content' in first_post
        assert 'account' in first_post
        assert 'created_at' in first_post
    
    def test_integration_trending_aggregator_full_pipeline(self):
        """Test the full pipeline from content discovery to cold start delivery."""
        # This integration test validates the complete workflow:
        # 1. Language detection with confidence
        # 2. Trending score calculation  
        # 3. Language-specific aggregation
        # 4. Cold start integration
        
        # Test content samples
        test_content = [
            "This is breaking news about amazing technology developments!",
            "Das sind wunderbare Nachrichten über technologische Entwicklungen!",
            "¡Estas son noticias increíbles sobre desarrollos tecnológicos!"
        ]
        
        # Step 1: Language detection
        language_results = batch_detect_languages(test_content)
        
        assert len(language_results) == 3
        assert language_results[0][0] == 'en'  # English
        assert language_results[1][0] == 'de'  # German
        assert language_results[2][0] == 'es'  # Spanish
        
        # Step 2: Create mock posts with detected languages
        mock_posts = []
        for i, (content, (language, confidence)) in enumerate(zip(test_content, language_results)):
            mock_post = Mock()
            mock_post.content = content
            mock_post.favourites_count = 50 + (i * 20)
            mock_post.reblogs_count = 15 + (i * 5)
            mock_post.replies_count = 8 + (i * 2)
            mock_post.created_at = datetime.now(timezone.utc) - timedelta(hours=i+1)
            mock_post.media_attachments = []
            mock_post.tags = []
            
            # Calculate trending score
            engagement_velocity = (mock_post.favourites_count + mock_post.reblogs_count) / ((i+1) * 2)
            trending_score = calculate_trending_score(mock_post, engagement_velocity)
            
            assert trending_score > 0, f"Post {i} should have positive trending score"
            
            mock_posts.append({
                'content': content,
                'language': language,
                'confidence': confidence,
                'trending_score': trending_score,
                'engagement_velocity': engagement_velocity
            })
        
        # Step 3: Verify language distribution
        detected_languages = [post['language'] for post in mock_posts]
        language_stats = get_language_statistics(detected_languages)
        
        assert language_stats['total'] == 3
        assert language_stats['unique_languages'] == 3
        assert language_stats['diversity_score'] > 0.5  # High diversity
        
        # Step 4: Verify trending scores correlate with engagement
        scores = [post['trending_score'] for post in mock_posts]
        assert all(score > 0 for score in scores), "All posts should have positive trending scores"


class TestLanguageAwareTrendingQualityMetrics:
    """Test quality metrics and performance of the language-aware trending system."""
    
    def test_trending_score_consistency(self):
        """Test that trending scores are consistent and meaningful."""
        # Create posts with known engagement patterns
        high_engagement_post = Mock()
        high_engagement_post.favourites_count = 500
        high_engagement_post.reblogs_count = 200
        high_engagement_post.replies_count = 100
        high_engagement_post.content = "High engagement content with lots of interesting details and media!"
        high_engagement_post.created_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        high_engagement_post.media_attachments = [Mock(), Mock()]
        high_engagement_post.tags = [Mock(), Mock(), Mock()]
        
        low_engagement_post = Mock()
        low_engagement_post.favourites_count = 5
        low_engagement_post.reblogs_count = 1
        low_engagement_post.replies_count = 0
        low_engagement_post.content = "Low."
        low_engagement_post.created_at = datetime.now(timezone.utc) - timedelta(hours=24)
        low_engagement_post.media_attachments = []
        low_engagement_post.tags = []
        
        # Calculate trending scores
        high_score = calculate_trending_score(high_engagement_post, 100.0)
        low_score = calculate_trending_score(low_engagement_post, 0.5)
        
        # Verify score ordering
        assert high_score > low_score, "High engagement should score higher"
        assert high_score > 50.0, "High engagement should have substantial score"
        assert low_score < 20.0, "Low engagement should have modest score"
    
    def test_language_detection_accuracy_requirements(self):
        """Test that language detection meets accuracy requirements."""
        # Test clear language samples
        clear_samples = [
            ("The quick brown fox jumps over the lazy dog", 'en'),
            ("Der schnelle braune Fuchs springt über den faulen Hund", 'de'), 
            ("El zorro marrón rápido salta sobre el perro perezoso", 'es'),
            ("Le renard brun rapide saute par-dessus le chien paresseux", 'fr')
        ]
        
        correct_detections = 0
        total_detections = len(clear_samples)
        
        for text, expected_lang in clear_samples:
            detected_lang, confidence = detect_language_with_confidence(text)
            if detected_lang == expected_lang:
                correct_detections += 1
                assert confidence > 0.1, f"Confidence too low for clear {expected_lang} text"
        
        accuracy = correct_detections / total_detections
        assert accuracy > 0.75, f"Language detection accuracy {accuracy:.2f} below 75% threshold"
    
    def test_aggregation_performance_characteristics(self):
        """Test performance characteristics of the aggregation system."""
        # Test with varying batch sizes
        batch_sizes = [10, 50, 100]
        
        for batch_size in batch_sizes:
            # Generate test texts
            test_texts = [f"Test content number {i} with english text" for i in range(batch_size)]
            
            # Measure batch detection time
            start_time = time.time()
            results = batch_detect_languages(test_texts)
            detection_time = time.time() - start_time
            
            # Verify results
            assert len(results) == batch_size
            
            # Performance requirement: < 100ms per text on average
            avg_time_per_text = detection_time / batch_size
            assert avg_time_per_text < 0.1, f"Language detection too slow: {avg_time_per_text:.3f}s per text"


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 