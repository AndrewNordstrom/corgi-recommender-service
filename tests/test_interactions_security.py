"""
Security-focused tests for the Interactions API.

This module contains red team style tests designed to identify security vulnerabilities
in the interactions endpoint, including injection attacks, DoS attempts, enumeration
attacks, and other security concerns.
"""

import json
import pytest
import time
from unittest.mock import patch, MagicMock
from config import API_PREFIX


class TestInteractionsSecurityVulnerabilities:
    """Security vulnerability tests for interactions API."""

    def test_sql_injection_in_post_ids_batch(self, client):
        """Test for SQL injection vulnerabilities in batch post retrieval."""
        # Test various SQL injection payloads
        injection_payloads = [
            "'; DROP TABLE interactions; --",
            "' OR '1'='1",
            "'; INSERT INTO interactions VALUES('malicious', 'data'); --",
            "post123' UNION SELECT 'malicious', 'data', 1 --",
            "post123'; EXEC xp_cmdshell('whoami'); --",
            "post123' OR post_id IN (SELECT password FROM users) --"
        ]
        
        for payload in injection_payloads:
            test_data = {"post_ids": [payload]}
            
            response = client.post(
                f'{API_PREFIX}/interactions/counts/batch',
                json=test_data,
                content_type='application/json'
            )
            
            # Should either reject the payload (400) or handle safely (200)
            # Should NOT return 500 which might indicate SQL error
            assert response.status_code in [200, 400], f"SQL injection test failed for payload: {payload[:50]}"
            
            if response.status_code == 200:
                data = json.loads(response.data)
                # Verify no unexpected data was returned
                assert "interaction_counts" in data
                # Should not contain any injected data
                assert not any("malicious" in str(v) for v in data.values())

    def test_json_bomb_deep_nesting_attack(self, client):
        """Test for JSON bomb attacks using deeply nested structures."""
        # Create deeply nested JSON that should trigger nesting depth protection
        def create_deeply_nested(depth, current=0):
            if current >= depth:
                return "end"
            return {"level": current, "nested": create_deeply_nested(depth, current + 1)}
        
        # Test with depth exceeding the limit (MAX_NESTING_DEPTH = 10)
        deep_context = create_deeply_nested(15)
        
        test_data = {
            "user_id": "test_user",
            "post_id": "test_post",
            "action_type": "favorite",
            "context": deep_context
        }
        
        response = client.post(
            f'{API_PREFIX}/interactions',
            json=test_data,
            content_type='application/json'
        )
        
        # Should reject due to nesting depth
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "nesting depth" in data["error"].lower()

    def test_json_bomb_wide_nesting_attack(self, client):
        """Test for JSON bomb attacks using very wide nesting."""
        # Create very wide context that could consume excessive memory
        wide_context = {f"key_{i}": {"nested": f"value_{i}"} for i in range(1000)}
        
        test_data = {
            "user_id": "test_user",
            "post_id": "test_post", 
            "action_type": "favorite",
            "context": wide_context
        }
        
        response = client.post(
            f'{API_PREFIX}/interactions',
            json=test_data,
            content_type='application/json'
        )
        
        # Should either reject due to size limits or handle gracefully
        assert response.status_code in [200, 400], "Wide nesting attack not handled properly"

    def test_oversized_json_payload_attack(self, client):
        """Test protection against oversized JSON payloads."""
        # Create a payload larger than MAX_JSON_SIZE (1MB)
        large_string = "A" * (1024 * 1024 + 1)  # Just over 1MB
        
        test_data = {
            "user_id": "test_user",
            "post_id": "test_post",
            "action_type": "favorite",
            "context": {"large_field": large_string}
        }
        
        response = client.post(
            f'{API_PREFIX}/interactions',
            json=test_data,
            content_type='application/json'
        )
        
        # Should reject oversized payload
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "oversized" in data["error"].lower() or "invalid" in data["error"].lower()

    def test_null_byte_injection(self, client):
        """Test for null byte injection vulnerabilities."""
        null_byte_payloads = [
            "test\x00user",
            "post\x00id",
            "favorite\x00action",
            "test\x00\x00\x00injection"
        ]
        
        for payload in null_byte_payloads:
            test_data = {
                "user_id": payload,
                "post_id": "test_post",
                "action_type": "favorite"
            }
            
            response = client.post(
                f'{API_PREFIX}/interactions',
                json=test_data,
                content_type='application/json'
            )
            
            # Should reject null byte characters
            assert response.status_code == 400, f"Null byte injection not handled for: {repr(payload)}"

    def test_control_character_injection(self, client):
        """Test for control character injection vulnerabilities."""
        control_chars = [
            "test\ruser",  # Carriage return
            "test\nuser",  # Line feed  
            "test\x08user",  # Backspace
            "test\x1buser",  # Escape
        ]
        
        for payload in control_chars:
            test_data = {
                "user_id": payload,
                "post_id": "test_post", 
                "action_type": "favorite"
            }
            
            response = client.post(
                f'{API_PREFIX}/interactions',
                json=test_data,
                content_type='application/json'
            )
            
            # Should reject dangerous control characters
            assert response.status_code == 400, f"Control character injection not handled for: {repr(payload)}"

    def test_unicode_normalization_attack(self, client):
        """Test for Unicode normalization attacks."""
        # Unicode payloads that could bypass filtering after normalization
        unicode_payloads = [
            "test\u0000user",  # Null in Unicode
            "test\uff1cscript\uff1e",  # Fullwidth < and >
            "test\u202e_resu",  # Right-to-left override
            "\u0009\u000A\u000D\u0020test",  # Various whitespace chars
        ]
        
        for payload in unicode_payloads:
            test_data = {
                "user_id": payload,
                "post_id": "test_post",
                "action_type": "favorite"
            }
            
            response = client.post(
                f'{API_PREFIX}/interactions',
                json=test_data,
                content_type='application/json'
            )
            
            # Should handle Unicode normalization safely
            # Either reject (400) or accept but sanitize properly (201)
            assert response.status_code in [200, 201, 400], f"Unicode attack not handled for: {repr(payload)}"

    def test_excessive_string_length_attack(self, client):
        """Test protection against excessively long strings."""
        # Create strings longer than MAX_STRING_LENGTH (255)
        long_string = "A" * 1000
        
        test_cases = [
            {"user_id": long_string, "post_id": "test", "action_type": "favorite"},
            {"user_id": "test", "post_id": long_string, "action_type": "favorite"},
            {"user_id": "test", "post_id": "test", "action_type": long_string},
        ]
        
        for test_data in test_cases:
            response = client.post(
                f'{API_PREFIX}/interactions',
                json=test_data,
                content_type='application/json'
            )
            
            # Should reject strings that are too long
            assert response.status_code == 400, f"Long string not rejected: {list(test_data.keys())}"

    def test_dangerous_context_keys_injection(self, client):
        """Test that dangerous keys in context are rejected."""
        dangerous_contexts = [
            {"admin": "true", "role": "administrator"},
            {"system": "override", "auth": "bypass"},
            {"token": "malicious_token", "password": "secret"},
            {"__proto__": {"admin": True}},  # Prototype pollution attempt
        ]
        
        for dangerous_context in dangerous_contexts:
            test_data = {
                "user_id": "test_user",
                "post_id": "test_post",
                "action_type": "favorite",
                "context": dangerous_context
            }
            
            response = client.post(
                f'{API_PREFIX}/interactions',
                json=test_data,
                content_type='application/json'
            )
            
            # Should reject dangerous context keys
            assert response.status_code == 400, f"Dangerous context not rejected: {dangerous_context}"

    def test_user_enumeration_timing_attack(self, client):
        """Test for user enumeration via timing differences."""
        # Test with potentially valid vs invalid user IDs
        valid_users = ["user123", "testuser", "validuser"]
        invalid_users = ["nonexistent999", "fakeuserid", "invaliduser"]
        
        valid_times = []
        invalid_times = []
        
        # Measure timing for existing vs non-existing users
        for user_id in valid_users:
            start_time = time.time()
            response = client.get(f'{API_PREFIX}/interactions/user/{user_id}')
            end_time = time.time()
            valid_times.append(end_time - start_time)
            
        for user_id in invalid_users:
            start_time = time.time()
            response = client.get(f'{API_PREFIX}/interactions/user/{user_id}')
            end_time = time.time()
            invalid_times.append(end_time - start_time)
        
        # Calculate average timing
        avg_valid_time = sum(valid_times) / len(valid_times)
        avg_invalid_time = sum(invalid_times) / len(invalid_times)
        
        # Timing difference should not be significant (less than 50ms difference)
        timing_diff = abs(avg_valid_time - avg_invalid_time)
        assert timing_diff < 0.05, f"Potential timing attack vulnerability: {timing_diff}s difference"

    def test_cache_invalidation_dos_attack(self, client):
        """Test for cache invalidation DoS vulnerability."""
        # Rapidly send many interaction requests to trigger cache invalidation
        user_id = "dos_test_user"
        
        for i in range(20):  # Simulate rapid requests
            test_data = {
                "user_id": user_id,
                "post_id": f"post_{i}",
                "action_type": "favorite"
            }
            
            response = client.post(
                f'{API_PREFIX}/interactions',
                json=test_data,
                content_type='application/json'
            )
            
            # All requests should be handled without degrading performance
            assert response.status_code in [200, 201, 429], f"Cache DoS failed at request {i}"

    @pytest.mark.parametrize("malicious_action", [
        "favorite'; DROP TABLE interactions; --",
        "favorite' OR '1'='1",
        "favorite\x00admin",
        "EXEC('malicious')",
        "../../../etc/passwd",
        "javascript:alert('xss')",
        "<script>alert('xss')</script>",
    ])
    def test_action_type_injection_attacks(self, client, malicious_action):
        """Test various injection attacks via action_type field."""
        test_data = {
            "user_id": "test_user",
            "post_id": "test_post",
            "action_type": malicious_action
        }
        
        response = client.post(
            f'{API_PREFIX}/interactions',
            json=test_data,
            content_type='application/json'
        )
        
        # Should reject malicious action types
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Invalid action_type" in data.get("error", "") or "Invalid input format" in data.get("error", "")

    def test_batch_post_ids_limit_bypass(self, client):
        """Test attempts to bypass the 100 post_ids limit."""
        # Try to send more than 100 post_ids
        large_post_list = [f"post_{i}" for i in range(150)]
        
        test_data = {"post_ids": large_post_list}
        
        response = client.post(
            f'{API_PREFIX}/interactions/counts/batch',
            json=test_data,
            content_type='application/json'
        )
        
        # Should reject requests exceeding the limit
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Too many post_ids" in data["error"]

    def test_post_id_path_traversal_attack(self, client):
        """Test for path traversal attacks in post_id URL parameter."""
        malicious_post_ids = [
            "../../../admin",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "....//....//....//etc//passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]
        
        for malicious_id in malicious_post_ids:
            response = client.get(f'{API_PREFIX}/interactions/{malicious_id}')
            
            # Should either sanitize the input or reject it
            # 403 is acceptable - proxy/security layer blocking the attack
            # Should not return internal system files
            assert response.status_code in [200, 400, 403, 404]
            
            if response.status_code == 200:
                data = json.loads(response.data)
                # Should not contain any injected data
                assert "interaction_counts" in data
                # Verify no system paths leaked in response
                response_str = str(data)
                assert "/etc/passwd" not in response_str
                assert "/admin" not in response_str or malicious_id in response_str

    def test_user_id_path_traversal_attack(self, client):
        """Test for path traversal attacks in user_id URL parameter."""
        malicious_user_ids = [
            "../../../admin",
            "..%2F..%2F..%2Fadmin", 
            "....//....//admin",
        ]
        
        for malicious_id in malicious_user_ids:
            response = client.get(f'{API_PREFIX}/interactions/user/{malicious_id}')
            
            # Should handle path traversal attempts safely
            assert response.status_code in [400, 404]

    @patch('routes.interactions.get_db_connection')
    def test_race_condition_simulation(self, mock_get_db, client):
        """Test for race conditions in concurrent interaction logging."""
        import threading
        import queue
        
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        mock_cursor.fetchone.return_value = None
        
        results = queue.Queue()
        
        def make_concurrent_request():
            test_data = {
                "user_id": "race_user",
                "post_id": "race_post", 
                "action_type": "favorite"
            }
            
            response = client.post(
                f'{API_PREFIX}/interactions',
                json=test_data,
                content_type='application/json'
            )
            results.put(response.status_code)
        
        # Launch multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_concurrent_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all requests to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())
        
        # All requests should be handled properly (no crashes or data corruption)
        assert all(code in [200, 201, 500] for code in status_codes)
        assert len(status_codes) == 10 