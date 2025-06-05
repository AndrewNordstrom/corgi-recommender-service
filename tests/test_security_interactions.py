"""
Security-focused tests for the interactions API.

This module contains red team tests designed to identify and verify fixes 
for security vulnerabilities in the interactions routes.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from config import API_PREFIX

class TestInteractionsSecurityVulnerabilities:
    """Red team security tests for interactions API."""

    def test_json_payload_size_limit(self, client):
        """Test protection against oversized JSON payloads."""
        # Create a 10MB JSON payload
        huge_string = "A" * (10 * 1024 * 1024)  # 10MB string
        huge_payload = {
            "user_id": "test_user",
            "post_id": "test_post", 
            "action_type": "favorite",
            "context": {"malicious_data": huge_string}
        }
        
        response = client.post(f'{API_PREFIX}/interactions',
                             json=huge_payload,
                             content_type='application/json')
        
        # Should reject oversized payloads
        assert response.status_code in [400, 413, 414], "Large payloads should be rejected"

    def test_deeply_nested_json_attack(self, client):
        """Test protection against deeply nested JSON structures."""
        # Create deeply nested JSON to cause stack overflow
        nested_bomb = {"user_id": "test", "post_id": "test", "action_type": "favorite"}
        for i in range(1000):  # 1000 levels of nesting
            nested_bomb = {"nested": nested_bomb}
        
        response = client.post(f'{API_PREFIX}/interactions',
                             json=nested_bomb,
                             content_type='application/json')
        
        # Should handle deeply nested JSON gracefully
        assert response.status_code in [400, 413], "Deeply nested JSON should be rejected"

    def test_unicode_bomb_in_strings(self, client):
        """Test protection against Unicode expansion attacks."""
        # Unicode string that expands significantly when normalized
        unicode_bomb = "\u1e9b" * 100000  # Character that normalizes to multiple chars
        
        test_data = {
            "user_id": unicode_bomb,
            "post_id": "test_post",
            "action_type": "favorite"
        }
        
        response = client.post(f'{API_PREFIX}/interactions',
                             json=test_data,
                             content_type='application/json')
        
        # Should reject strings that exceed length after normalization
        assert response.status_code == 400, "Unicode bomb should be rejected"

    def test_null_byte_injection_in_strings(self, client):
        """Test protection against null byte injection."""
        test_cases = [
            "user\x00id",  # Null byte in user_id
            "post\x00id",  # Null byte in post_id  
            "favorite\x00",  # Null byte in action_type
        ]
        
        for i, malicious_string in enumerate(test_cases):
            test_data = {
                "user_id": malicious_string if i == 0 else "valid_user",
                "post_id": malicious_string if i == 1 else "valid_post",
                "action_type": malicious_string if i == 2 else "favorite"
            }
            
            response = client.post(f'{API_PREFIX}/interactions',
                                 json=test_data,
                                 content_type='application/json')
            
            # Should reject strings with null bytes
            assert response.status_code == 400, f"Null byte in field {i} should be rejected"

    def test_context_field_schema_pollution(self, client):
        """Test protection against context field schema pollution."""
        malicious_context = {
            "admin": True,
            "role": "administrator",
            "system_override": True,
            "injection_test": "'; DROP TABLE interactions; --",
            "path_traversal": "../../../../etc/passwd",
            # Massive nested object
            "nested_bomb": {f"level_{i}": {"data": "x" * 1000} for i in range(1000)}
        }
        
        test_data = {
            "user_id": "test_user",
            "post_id": "test_post", 
            "action_type": "favorite",
            "context": malicious_context
        }
        
        with patch('routes.interactions.get_db_connection') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            
            response = client.post(f'{API_PREFIX}/interactions',
                                 json=test_data,
                                 content_type='application/json')
        
        # Should validate or sanitize context content
        assert response.status_code in [400, 413], "Malicious context should be rejected"

    @patch('routes.interactions.get_db_connection')
    def test_concurrent_conflicting_actions_race_condition(self, mock_db, client):
        """Test for race conditions in conflicting action handling."""
        import threading
        import time
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        results = []
        
        def send_conflicting_request(action_type):
            test_data = {
                "user_id": "race_test_user",
                "post_id": "race_test_post",
                "action_type": action_type
            }
            response = client.post(f'{API_PREFIX}/interactions',
                                 json=test_data,
                                 content_type='application/json')
            results.append((action_type, response.status_code))
        
        # Send conflicting actions simultaneously
        threads = []
        for _ in range(10):
            t1 = threading.Thread(target=send_conflicting_request, args=("more_like_this",))
            t2 = threading.Thread(target=send_conflicting_request, args=("less_like_this",))
            threads.extend([t1, t2])
        
        # Start all threads simultaneously
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # All requests should complete successfully without crashes
        assert all(status in [200, 201] for _, status in results), "Race condition caused failures"

    def test_user_enumeration_via_privacy_responses(self, client):
        """Test for user enumeration through privacy level disclosure."""
        test_users = ["user_exists", "user_not_exists", "admin_user", "test_user"]
        responses = {}
        
        for user_id in test_users:
            with patch('routes.interactions.get_user_privacy_level') as mock_privacy:
                # Simulate different privacy responses 
                if user_id == "user_not_exists":
                    mock_privacy.side_effect = Exception("User not found")
                else:
                    mock_privacy.return_value = "none"
                
                response = client.get(f'{API_PREFIX}/interactions/user/{user_id}')
                responses[user_id] = {
                    'status_code': response.status_code,
                    'response_body': response.json if response.content_type == 'application/json' else None
                }
        
        # Responses should not reveal user existence patterns
        status_codes = [r['status_code'] for r in responses.values()]
        assert len(set(status_codes)) <= 2, "Status codes should not reveal user enumeration patterns"

    def test_batch_request_amplification_attack(self, client):
        """Test protection against batch request amplification."""
        # Try to overwhelm with maximum allowed batch size
        max_post_ids = ["post_" + str(i) for i in range(100)]  # Maximum allowed
        oversized_batch = ["post_" + str(i) for i in range(101)]  # Over limit
        
        # Test maximum allowed size
        with patch('routes.interactions.get_db_connection') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            
            response = client.post(f'{API_PREFIX}/interactions/counts/batch',
                                 json={"post_ids": max_post_ids},
                                 content_type='application/json')
            
            assert response.status_code == 200, "Maximum batch size should be allowed"
        
        # Test oversized batch
        response = client.post(f'{API_PREFIX}/interactions/counts/batch',
                             json={"post_ids": oversized_batch},
                             content_type='application/json')
        
        assert response.status_code == 400, "Oversized batch should be rejected"

    def test_information_disclosure_in_errors(self, client):
        """Test for information disclosure in error messages."""
        test_cases = [
            {},  # Empty payload
            {"invalid": "data"},  # Invalid structure
            {"user_id": None},  # Null values
            {"user_id": "", "post_id": "", "action_type": ""},  # Empty strings
        ]
        
        for test_data in test_cases:
            response = client.post(f'{API_PREFIX}/interactions',
                                 json=test_data,
                                 content_type='application/json')
            
            if response.content_type == 'application/json':
                error_data = response.json
                
                # Error messages should not expose internal details
                error_text = json.dumps(error_data).lower()
                sensitive_patterns = [
                    'traceback', 'stack trace', 'file "/', 
                    'line ', '.py', 'exception', 'internal',
                    'database', 'sql', 'postgres', 'connection'
                ]
                
                for pattern in sensitive_patterns:
                    assert pattern not in error_text, f"Error message exposes sensitive info: {pattern}"

    def test_post_id_injection_attacks(self, client):
        """Test for injection attacks via post_id parameter."""
        malicious_post_ids = [
            "'; DROP TABLE interactions; --",  # SQL injection
            "../../../etc/passwd",  # Path traversal
            "javascript:alert('xss')",  # XSS attempt
            "\x00\x01\x02",  # Binary data
            "post_id\nHTTP/1.1 200 OK\r\n\r\n",  # HTTP header injection
        ]
        
        for malicious_id in malicious_post_ids:
            test_data = {
                "user_id": "test_user",
                "post_id": malicious_id,
                "action_type": "favorite"
            }
            
            response = client.post(f'{API_PREFIX}/interactions',
                                 json=test_data,
                                 content_type='application/json')
            
            # Should validate and reject malicious post IDs
            assert response.status_code == 400, f"Malicious post_id should be rejected: {malicious_id}"

    def test_action_type_bypass_attempts(self, client):
        """Test attempts to bypass action_type validation."""
        bypass_attempts = [
            "favorite\x00admin",  # Null byte injection
            "favorite; DROP TABLE interactions;",  # SQL injection
            "favorite\r\nSet-Cookie: admin=true",  # Header injection
            "fаvorite",  # Unicode homograph (Cyrillic 'а' instead of 'a')
            "FAVORITE",  # Case variation
            " favorite ",  # Whitespace padding
        ]
        
        for malicious_action in bypass_attempts:
            test_data = {
                "user_id": "test_user", 
                "post_id": "test_post",
                "action_type": malicious_action
            }
            
            response = client.post(f'{API_PREFIX}/interactions',
                                 json=test_data,
                                 content_type='application/json')
            
            # Should reject non-standard action types
            assert response.status_code == 400, f"Malicious action_type should be rejected: {malicious_action}"

    @patch('routes.interactions.get_db_connection')
    def test_database_connection_exhaustion(self, mock_db, client):
        """Test protection against database connection exhaustion."""
        # Simulate database connection failure
        mock_db.side_effect = Exception("Connection pool exhausted")
        
        test_data = {
            "user_id": "test_user",
            "post_id": "test_post", 
            "action_type": "favorite"
        }
        
        response = client.post(f'{API_PREFIX}/interactions',
                             json=test_data,
                             content_type='application/json')
        
        # Should handle database failures gracefully
        assert response.status_code == 500, "Database failures should return 500"
        
        # Response should not expose sensitive connection details
        if response.content_type == 'application/json':
            error_data = response.json
            error_text = json.dumps(error_data).lower()
            assert 'connection' not in error_text, "Should not expose connection details"
            assert 'database' not in error_text, "Should not expose database details" 