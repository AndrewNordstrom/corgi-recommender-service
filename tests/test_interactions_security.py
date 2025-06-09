"""
Core Security Tests for the Interactions API

Essential security vulnerability tests covering:
- SQL injection protection
- JSON security (oversized payloads, nesting)
- Input validation and sanitization
- Basic DoS protection
"""

import json
import pytest
import time
from unittest.mock import patch, MagicMock
from config import API_PREFIX


class TestInteractionsSecurityVulnerabilities:
    """Core security vulnerability tests for interactions API."""

    def test_sql_injection_in_post_ids_batch(self, client):
        """Test for SQL injection vulnerabilities in batch post retrieval."""
        injection_payloads = [
            "'; DROP TABLE interactions; --",
            "' OR '1'='1",
            "post123' UNION SELECT 'malicious', 'data', 1 --"
        ]
        
        for payload in injection_payloads:
            test_data = {"post_ids": [payload]}
            
            response = client.post(
                f'{API_PREFIX}/interactions/counts/batch',
                json=test_data,
                content_type='application/json'
            )
            
            # Should either reject the payload (400) or handle safely (200)
            assert response.status_code in [200, 400], f"SQL injection test failed for payload: {payload[:50]}"
            
            if response.status_code == 200:
                data = json.loads(response.data)
                assert "interaction_counts" in data
                assert not any("malicious" in str(v) for v in data.values())

    def test_json_bomb_deep_nesting_attack(self, client):
        """Test for JSON bomb attacks using deeply nested structures."""
        def create_deeply_nested(depth, current=0):
            if current >= depth:
                return "end"
            return {"level": current, "nested": create_deeply_nested(depth, current + 1)}
        
        # Test with depth exceeding the limit
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
            "favorite\x00action"
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
            "test\x08user"  # Backspace
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

    @pytest.mark.parametrize("malicious_action", [
        "favorite'; DROP TABLE interactions; --",
        "favorite' OR '1'='1",
        "<script>alert('xss')</script>",
    ])
    def test_action_type_injection_attacks(self, client, malicious_action):
        """Test action_type field against various injection attacks."""
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
        assert response.status_code == 400, f"Action type injection not handled for: {malicious_action}"

    def test_cache_invalidation_dos_attack(self, client):
        """Test for cache invalidation DoS attacks."""
        # Attempt to flood cache invalidation with rapid requests
        user_ids = [f"dos_user_{i}" for i in range(10)]
        
        start_time = time.time()
        for user_id in user_ids:
            test_data = {
                "user_id": user_id,
                "post_id": "test_post",
                "action_type": "favorite"
            }
            
            response = client.post(
                f'{API_PREFIX}/interactions',
                json=test_data,
                content_type='application/json'
            )
            
            # Should handle gracefully without crashing
            assert response.status_code in [200, 201, 400, 429], f"DoS attack not handled for user: {user_id}"
        
        end_time = time.time()
        
        # Should complete within reasonable time (not hanging/blocking)
        assert end_time - start_time < 30, "Cache invalidation DoS causing performance issues"


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 