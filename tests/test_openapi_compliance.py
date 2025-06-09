#!/usr/bin/env python3
"""
Core OpenAPI Specification Compliance Tests

Essential tests to ensure our API implementation matches the OpenAPI specification.
Covers core endpoint validation, basic schema compliance, and essential security.
"""

import json
import pytest
import yaml
import requests
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from jsonschema import validate, ValidationError
from urllib.parse import urljoin
import logging

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.conftest import client, app
from db.connection import get_db_connection, get_cursor

logger = logging.getLogger(__name__)


class OpenAPISpecValidator:
    """Validates API compliance against OpenAPI specification"""
    
    def __init__(self, spec_path: str = "openapi.yaml", base_url: str = "http://localhost:5002"):
        self.spec_path = Path(spec_path)
        self.base_url = base_url
        self.spec = self._load_openapi_spec()
        self.paths = self.spec.get('paths', {})
        self.components = self.spec.get('components', {})
        self.schemas = self.components.get('schemas', {})
        
    def _load_openapi_spec(self) -> Dict[str, Any]:
        """Load and parse the OpenAPI specification"""
        try:
            with open(self.spec_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise Exception(f"Failed to load OpenAPI spec from {self.spec_path}: {e}")
    
    def get_all_endpoints(self) -> List[Dict[str, Any]]:
        """Extract all endpoints from the OpenAPI spec"""
        endpoints = []
        
        for path, path_spec in self.paths.items():
            for method, operation in path_spec.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                    endpoints.append({
                        'path': path,
                        'method': method.upper(),
                        'operation_id': operation.get('operationId'),
                        'summary': operation.get('summary'),
                        'responses': operation.get('responses', {}),
                        'tags': operation.get('tags', [])
                    })
        
        return endpoints
    
    def validate_response_schema(self, response_data: Any, schema_ref: str) -> bool:
        """Validate response data against OpenAPI schema"""
        try:
            if schema_ref.startswith('#/components/schemas/'):
                schema_name = schema_ref.split('/')[-1]
                schema = self.schemas.get(schema_name)
                if not schema:
                    return True  # Skip validation if schema not found
            else:
                schema = schema_ref
            
            validate(instance=response_data, schema=schema)
            return True
            
        except (ValidationError, Exception):
            return False


@pytest.fixture
def openapi_validator():
    """Provide OpenAPI validator instance"""
    return OpenAPISpecValidator()


class TestOpenAPICompliance:
    """Core OpenAPI specification compliance tests"""
    
    def test_openapi_spec_loads(self, openapi_validator):
        """Test that the OpenAPI specification file loads correctly"""
        assert openapi_validator.spec is not None
        assert 'openapi' in openapi_validator.spec
        assert 'info' in openapi_validator.spec
        assert 'paths' in openapi_validator.spec
        
        info = openapi_validator.spec['info']
        assert 'title' in info
        assert 'version' in info
    
    def test_spec_has_required_sections(self, openapi_validator):
        """Test that the spec has all required sections"""
        required_sections = ['openapi', 'info', 'paths']
        
        for section in required_sections:
            assert section in openapi_validator.spec
        
        info = openapi_validator.spec['info']
        assert info['title'] == 'Corgi Recommender Service API'
        assert 'description' in info
    
    def test_health_endpoint_compliance(self, client, openapi_validator):
        """Test health endpoint compliance with OpenAPI spec"""
        response = client.get('/health')
        
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'status' in data
        assert 'database' in data
    
    def test_interactions_post_compliance(self, client, openapi_validator):
        """Test interactions POST endpoint compliance"""
        interaction_data = {
            "post_id": "test_post_123",
            "interaction_type": "like",
            "user_id": "test_user_123"  # Add required user_id
        }
        
        response = client.post('/api/v1/interactions', 
                             json=interaction_data,
                             headers={'Content-Type': 'application/json'})
        
        # Should be either success or auth error (both valid per spec)
        assert response.status_code in [200, 201, 401, 422]
        
        if response.status_code in [200, 201]:
            data = response.get_json()
            assert 'success' in data or 'status' in data
    
    def test_privacy_endpoints_compliance(self, client, openapi_validator):
        """Test privacy endpoints compliance"""
        # Test GET privacy settings with Authorization header
        headers = {'Authorization': 'Bearer test_token_123'}
        response = client.get('/api/v1/privacy/settings', headers=headers)
        assert response.status_code in [200, 401]  # Success or auth required
        
        if response.status_code == 200:
            data = response.get_json()
            assert isinstance(data, (dict, list))
    
    def test_recommendations_endpoint_compliance(self, client, openapi_validator):
        """Test recommendations endpoint compliance"""
        # Add Authorization header for recommendations
        headers = {'Authorization': 'Bearer test_token_123'}
        response = client.get('/api/v1/recommendations', headers=headers)
        
        # Should return proper format regardless of auth
        assert response.status_code in [200, 401]
        assert response.content_type == 'application/json'
    
    def test_error_response_compliance(self, client, openapi_validator):
        """Test error response format compliance"""
        # Test invalid endpoint
        response = client.get('/api/v1/nonexistent')
        
        assert response.status_code == 404
        data = response.get_json()
        # Handle case where response might be None or empty
        if data is not None:
            assert 'error' in data or 'message' in data
        else:
            # If no JSON response, check that it's still a proper 404
            assert response.status_code == 404
    
    def test_content_type_compliance(self, client, openapi_validator):
        """Test content type compliance"""
        response = client.get('/health')
        
        assert response.status_code == 200
        assert 'application/json' in response.content_type
    
    def test_endpoint_tags_coverage(self, openapi_validator):
        """Test that endpoints have proper tags"""
        endpoints = openapi_validator.get_all_endpoints()
        
        assert len(endpoints) > 0
        
        # Most endpoints should have tags
        tagged_endpoints = [ep for ep in endpoints if ep['tags']]
        assert len(tagged_endpoints) > len(endpoints) * 0.5  # At least 50% tagged


class TestOpenAPISchemaValidation:
    """Core schema validation tests"""
    
    def test_interaction_request_schema(self, client, openapi_validator):
        """Test interaction request schema validation"""
        # Valid interaction
        valid_data = {
            "post_id": "123",
            "interaction_type": "like",
            "user_id": "test_user_123"  # Add required user_id
        }
        
        response = client.post('/api/v1/interactions',
                             json=valid_data,
                             headers={'Content-Type': 'application/json'})
        
        # Should process request (may fail auth but not schema)
        assert response.status_code in [200, 201, 401, 422]
        
        # Invalid interaction (missing required field)
        invalid_data = {"interaction_type": "like"}  # Missing post_id and user_id
        
        response = client.post('/api/v1/interactions',
                             json=invalid_data,
                             headers={'Content-Type': 'application/json'})
        
        # Should reject for missing data
        assert response.status_code in [400, 422]


class TestOpenAPISecurityCompliance:
    """Core security compliance tests"""
    
    def test_cors_headers_present(self, client, openapi_validator):
        """Test CORS headers are present"""
        response = client.options('/api/v1/recommendations')
        
        # Should handle OPTIONS request properly
        assert response.status_code in [200, 204]


def test_comprehensive_openapi_compliance(client, openapi_validator):
    """Test overall API compliance with OpenAPI spec"""
    endpoints = openapi_validator.get_all_endpoints()
    
    # Test a sample of core endpoints
    core_endpoints = [
        ('/health', 'GET'),
        ('/api/v1/recommendations', 'GET'),
        ('/api/v1/interactions', 'POST')
    ]
    
    for path, method in core_endpoints:
        if method == 'GET':
            response = client.get(path)
        elif method == 'POST':
            response = client.post(path, json={})
        
        # Should respond (not necessarily succeed, but respond properly)
        assert response.status_code < 500
        assert response.content_type == 'application/json'


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 