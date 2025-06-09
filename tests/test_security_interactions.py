"""
Core Security Tests for Interactions API

Essential red team security tests covering:
- JSON payload security (size limits, nesting)
- Input validation and injection protection  
- Basic enumeration and amplification attacks
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from config import API_PREFIX

class TestInteractionsSecurityVulnerabilities:
    """Core security tests for interactions API."""

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
            "injection_test": "'; DROP TABLE interactions; --",
            "path_traversal": "../../../../etc/passwd",
            # Nested object
            "nested_bomb": {f"level_{i}": {"data": "x" * 100} for i in range(100)}
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

    def test_batch_request_amplification_attack(self, client):
        """Test protection against batch request amplification."""
        # Try to overwhelm with oversized batch
        oversized_batch = ["post_" + str(i) for i in range(101)]  # Over limit
        
        with patch('routes.interactions.get_db_connection') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            
            response = client.post(f'{API_PREFIX}/interactions/counts/batch',
                                 json={"post_ids": oversized_batch},
                                 content_type='application/json')
        
        # Should reject oversized batch requests
        assert response.status_code == 400, "Oversized batch should be rejected"

    def test_post_id_injection_attacks(self, client):
        """Test post_id field against injection attacks."""
        injection_payloads = [
            "'; DROP TABLE posts; --",
            "' OR '1'='1",
            "../../../etc/passwd",
            "<script>alert('xss')</script>"
        ]
        
        for payload in injection_payloads:
            with patch('routes.interactions.get_db_connection') as mock_db:
                mock_conn = MagicMock()
                mock_cursor = MagicMock() 
                mock_db.return_value.__enter__.return_value = mock_conn
                mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
                mock_cursor.fetchone.return_value = None
                
                response = client.get(f'{API_PREFIX}/interactions/{payload}')
                
                # Should handle injection attempts safely
                assert response.status_code in [200, 400, 404], f"Injection not handled: {payload}"
                
                if response.status_code == 200:
                    data = response.json
                    # Should not contain injected content
                    assert "DROP TABLE" not in str(data)
                    assert "etc/passwd" not in str(data)


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 