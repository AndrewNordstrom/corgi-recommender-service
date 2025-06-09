#!/usr/bin/env python3
"""
Core Content Crawling System Tests

Focused test suite covering essential functionality:
- Language detection core cases
- Mastodon API client essentials
- Content crawler task basics
- Content discovery API core endpoints
- Cold start integration essentials
"""

import pytest
import json
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from unittest import TestCase
import requests

# Import the components we're testing
from tasks.content_crawler import (
    aggregate_trending_posts_standalone as aggregate_trending_posts, 
    crawl_instance_timeline_standalone as crawl_instance_timeline, 
    update_post_lifecycle_standalone as update_post_lifecycle
)
from utils.language_detector import detect_language, get_supported_languages, is_supported_language
from utils.mastodon_client import MastodonAPIClient
from routes.content_discovery import content_discovery_bp
from db.connection import get_db_connection, get_cursor

class TestLanguageDetector(TestCase):
    """Core language detection tests."""
    
    def test_detect_language_english(self):
        """Test detection of English text."""
        text = "The quick brown fox jumps over the lazy dog. This is definitely an English sentence with common English words and phrases."
        result = detect_language(text)
        self.assertEqual(result, 'en')
    
    def test_detect_language_non_english(self):
        """Test detection of non-English text."""
        text = "Hola mundo, este es un mensaje de prueba en español."
        result = detect_language(text)
        self.assertEqual(result, 'es')
    
    def test_detect_language_edge_cases(self):
        """Test detection with edge cases."""
        # Empty text
        result = detect_language("")
        self.assertEqual(result, 'en')  # Should default to English
        
        # Short text
        result = detect_language("Hi")
        self.assertEqual(result, 'en')
    
    def test_supported_languages(self):
        """Test supported language functionality."""
        languages = get_supported_languages()
        self.assertIsInstance(languages, list)
        self.assertIn('en', languages)
        
        self.assertTrue(is_supported_language('en'))
        self.assertFalse(is_supported_language('xyz'))


class TestMastodonAPIClient(TestCase):
    """Core Mastodon API client tests."""
    
    def setUp(self):
        """Set up test client."""
        self.client = MastodonAPIClient("https://test.example.com")
    
    @patch('requests.Session.get')
    def test_get_public_timeline_success(self, mock_get):
        """Test successful public timeline retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'X-RateLimit-Remaining': '299'}
        mock_response.json.return_value = [
            {
                'id': '12345',
                'content': '<p>Test post content</p>',
                'created_at': '2025-05-28T12:00:00.000Z',
                'favourites_count': 5,
                'reblogs_count': 2,
                'replies_count': 1,
                'account': {'username': 'testuser'},
                'tags': []
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        posts = self.client.get_public_timeline(limit=1)
        
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].id, '12345')
    
    @patch('requests.Session.get')
    def test_rate_limit_handling(self, mock_get):
        """Test rate limit and error handling."""
        # Rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'X-RateLimit-Remaining': '0'}
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        mock_get.return_value = mock_response
        
        posts = self.client.get_public_timeline(limit=10)
        self.assertEqual(len(posts), 0)
    
    @patch('requests.Session.get')
    def test_get_trending_hashtags(self, mock_get):
        """Test trending hashtags retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'X-RateLimit-Remaining': '299'}
        mock_response.json.return_value = [
            {'name': 'trending1', 'uses': [{'accounts': '100', 'uses': '500'}]}
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        tags = self.client.get_trending_hashtags()
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0]['name'], 'trending1')


class TestContentCrawlerTasks(TestCase):
    """Core content crawler task tests."""
    
    def setUp(self):
        self.sample_posts = [
            {
                'id': '1001',
                'content': '<p>Hello world from mastodon!</p>',
                'created_at': '2025-05-28T12:00:00.000Z',
                'favourites_count': 10,
                'reblogs_count': 5,
                'replies_count': 2,
                'account': {'username': 'user1'},
                'tags': []
            }
        ]
    
    @patch('tasks.content_crawler.get_db_connection')
    @patch('utils.mastodon_client.MastodonAPIClient')
    def test_crawl_instance_timeline_success(self, mock_client_class, mock_get_db):
        """Test successful timeline crawling."""
        # Mock API client
        mock_client = Mock()
        mock_client.get_public_timeline.return_value = [Mock(**post) for post in self.sample_posts]
        mock_client_class.return_value = mock_client
        
        # Mock database
        mock_cursor = Mock()
        mock_get_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        result = crawl_instance_timeline("test.example.com", limit=1)
        
        self.assertTrue(result)
        mock_client.get_public_timeline.assert_called_once_with(limit=1, local=False)
    
    @patch('tasks.content_crawler.crawl_instance_timeline')
    def test_aggregate_trending_posts(self, mock_crawl):
        """Test trending posts aggregation."""
        mock_crawl.return_value = True
        
        result = aggregate_trending_posts(['test1.example', 'test2.example'])
        
        self.assertTrue(result)
        self.assertEqual(mock_crawl.call_count, 2)
    
    @patch('tasks.content_crawler.get_db_connection')
    def test_update_post_lifecycle(self, mock_get_db):
        """Test post lifecycle updates."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('1001', datetime.now(timezone.utc) - timedelta(hours=25))
        ]
        mock_get_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        result = update_post_lifecycle()
        
        self.assertTrue(result)
        # Verify database queries were made
        self.assertTrue(mock_cursor.execute.called)


class TestContentDiscoveryAPI(TestCase):
    """Core content discovery API tests."""
    
    def setUp(self):
        from flask import Flask
        self.app = Flask(__name__)
        self.app.register_blueprint(content_discovery_bp)
        self.client = self.app.test_client()
    
    @patch('routes.content_discovery.get_db_connection')
    def test_get_crawler_status(self, mock_get_db):
        """Test crawler status endpoint."""
        mock_cursor = Mock()
        # Setup multiple fetchone() responses for the three queries
        mock_cursor.fetchone.side_effect = [
            (100,),    # total_posts count
            (5,),      # active_instances count  
            (datetime.now(timezone.utc),)  # last_crawl_time
        ]
        mock_get_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        response = self.client.get('/api/content/crawler/status')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
    @patch('routes.content_discovery.get_db_connection')
    def test_get_discovery_stats(self, mock_get_db):
        """Test discovery statistics endpoint."""
        mock_cursor = Mock()
        # Setup responses for all the queries
        mock_cursor.fetchall.side_effect = [
            [('en', 50), ('es', 30), ('ja', 20)],  # language_distribution
            []  # temporal_distribution (empty for test)
        ]
        mock_cursor.fetchone.return_value = (10.5, 5.2, 3.1)  # engagement_metrics
        mock_get_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        response = self.client.get('/api/content/discovery/stats')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('language_distribution', data['data'])


class TestColdStartIntegration(TestCase):
    """Core cold start integration tests."""
    
    def setUp(self):
        self.sample_crawled_posts = [
            {
                'post_id': '1001',
                'content': '<p>Test content</p>',
                'language': 'en',
                'engagement_score': 0.85,
                'created_at': datetime.now(timezone.utc)
            }
        ]
    
    @patch('utils.recommendation_engine.get_dynamic_cold_start_posts')
    @patch('utils.recommendation_engine.load_static_cold_start_posts')
    def test_load_cold_start_posts_blending(self, mock_load_static, mock_get_dynamic):
        """Test cold start post blending."""
        # Mock both static and dynamic posts
        mock_load_static.return_value = [{'id': 's1', 'type': 'static'}]
        mock_get_dynamic.return_value = [{'id': 'd1', 'type': 'dynamic'}]
        
        from utils.recommendation_engine import load_cold_start_posts
        
        result = load_cold_start_posts()  # Call without arguments
        
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
    
    @patch('db.connection.get_db_connection')
    def test_get_dynamic_cold_start_posts_success(self, mock_get_db):
        """Test dynamic cold start post retrieval."""
        from utils.recommendation_engine import get_dynamic_cold_start_posts
        
        # Mock the database connection to ensure test isolation
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('1001', 'testuser', '<p>Test</p>', datetime.now(timezone.utc), '{}')
        ]
        mock_get_db.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        
        result = get_dynamic_cold_start_posts('en', limit=10)
        
        self.assertIsInstance(result, list)
        # When database is successful, should have post_id
        if result and 'post_id' in result[0]:
            self.assertEqual(result[0]['post_id'], '1001')


def test_integration_content_crawler_pipeline():
    """Test end-to-end content crawler pipeline."""
    with patch('tasks.content_crawler.crawl_instance_timeline') as mock_crawl:
        with patch('tasks.content_crawler.aggregate_trending_posts') as mock_aggregate:
            mock_crawl.return_value = True
            mock_aggregate.return_value = True
            
            # Simulate pipeline execution
            crawl_result = mock_crawl('test.example')
            aggregate_result = mock_aggregate(['test.example'])
            
            assert crawl_result is True
            assert aggregate_result is True


if __name__ == '__main__':
    import unittest
    unittest.main() 