"""
Tests for authentication token management functionality.
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from utils.auth import get_user_by_token, set_token_expiration, revoke_token, get_token_info


class TestTokenValidation:
    """Test token validation with expiration."""
    
    def test_valid_token_no_expiration(self, app, client):
        """Test token validation when no expiration is set."""
        with patch('utils.auth.get_db_connection') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock token lookup with no expiration
            mock_cursor.fetchone.return_value = (
                'user123', 'https://mastodon.social', 'valid_token', None, '2024-01-01 00:00:00'
            )
            
            result = get_user_by_token('valid_token')
            
            assert result is not None
            assert result['user_id'] == 'user123'
            assert result['instance_url'] == 'https://mastodon.social'
    
    def test_valid_token_not_expired(self, app, client):
        """Test token validation with future expiration."""
        with patch('utils.auth.get_db_connection') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock token lookup with future expiration
            future_expiry = datetime.utcnow() + timedelta(hours=24)
            mock_cursor.fetchone.return_value = (
                'user123', 'https://mastodon.social', 'valid_token', 
                future_expiry.isoformat(), '2024-01-01 00:00:00'
            )
            
            result = get_user_by_token('valid_token')
            
            assert result is not None
            assert result['user_id'] == 'user123'
    
    def test_expired_token_rejected(self, app, client):
        """Test that expired tokens are rejected."""
        with patch('utils.auth.get_db_connection') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock token lookup with past expiration
            past_expiry = datetime.utcnow() - timedelta(hours=1)
            mock_cursor.fetchone.return_value = (
                'user123', 'https://mastodon.social', 'expired_token', 
                past_expiry.isoformat(), '2024-01-01 00:00:00'
            )
            
            result = get_user_by_token('expired_token')
            
            assert result is None
    
    def test_nonexistent_token(self, app, client):
        """Test lookup of non-existent token."""
        with patch('utils.auth.get_db_connection') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock empty result for non-existent token
            mock_cursor.fetchone.return_value = None
            
            result = get_user_by_token('nonexistent_token')
            
            assert result is None


class TestTokenExpiration:
    """Test token expiration management."""
    
    def test_set_token_expiration_success(self, app, client):
        """Test successfully setting token expiration."""
        with patch('utils.auth.get_db_connection') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock successful update
            mock_cursor.rowcount = 1
            
            result = set_token_expiration('valid_token', 48)
            
            assert result is True
            mock_cursor.execute.assert_called_once()
            mock_conn.commit.assert_called_once()
    
    def test_set_token_expiration_token_not_found(self, app, client):
        """Test setting expiration for non-existent token."""
        with patch('utils.auth.get_db_connection') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock no rows affected
            mock_cursor.rowcount = 0
            
            result = set_token_expiration('nonexistent_token', 24)
            
            assert result is False
    
    def test_revoke_token_success(self, app, client):
        """Test successful token revocation."""
        with patch('routes.auth.get_user_by_token') as mock_get_user, \
             patch('routes.auth.revoke_token') as mock_revoke:
            
            # Mock valid user and successful revocation
            mock_get_user.return_value = {'user_id': 'user123'}
            mock_revoke.return_value = True
            
            response = client.post('/api/v1/auth/token/revoke',
                                 headers={'Authorization': 'Bearer valid_token'})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'message' in data
    
    def test_get_token_info_valid_token(self, app, client):
        """Test getting information about a valid token."""
        with patch('utils.auth.get_db_connection') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock token lookup with future expiration
            future_expiry = datetime.utcnow() + timedelta(hours=12)
            mock_cursor.fetchone.return_value = (
                'user123', 'https://mastodon.test', 'valid_token', future_expiry.isoformat(), '2024-01-01 00:00:00'
            )
            
            result = get_token_info('valid_token')
            
            assert result is not None
            assert result['user_id'] == 'user123'
            assert result['is_expired'] is False
            assert result['expires_in_seconds'] is not None


class TestAuthAPI:
    """Test authentication API endpoints."""
    
    def test_token_info_success(self, app, client):
        """Test successful token info retrieval."""
        with patch('routes.auth.get_token_info') as mock_get_token_info:
            # Mock token info
            mock_get_token_info.return_value = {
                'user_id': 'user123',
                'token_expires_at': '2024-12-31T23:59:59',
                'created_at': '2024-01-01T00:00:00',
                'updated_at': '2024-01-01T12:00:00',
                'is_expired': False,
                'time_until_expiry': timedelta(hours=12)
            }
            
            response = client.get('/api/v1/auth/token/info',
                                headers={'Authorization': 'Bearer valid_token'})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['user_id'] == 'user123'
            assert data['is_expired'] is False
            assert 'time_until_expiry_seconds' in data
    
    def test_token_info_missing_auth_header(self, app, client):
        """Test token info with missing authorization header."""
        response = client.get('/api/v1/auth/token/info')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_token_info_invalid_token(self, app, client):
        """Test token info with invalid token."""
        with patch('routes.auth.get_token_info') as mock_get_token_info:
            # Mock invalid token
            mock_get_token_info.return_value = None
            
            response = client.get('/api/v1/auth/token/info',
                                headers={'Authorization': 'Bearer invalid_token'})
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_revoke_token_success(self, app, client):
        """Test successful token revocation."""
        with patch('routes.auth.get_user_by_token') as mock_get_user, \
             patch('routes.auth.revoke_token') as mock_revoke:
            
            # Mock valid user and successful revocation
            mock_get_user.return_value = {'user_id': 'user123'}
            mock_revoke.return_value = True
            
            response = client.post('/api/v1/auth/token/revoke',
                                 headers={'Authorization': 'Bearer valid_token'})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'message' in data
    
    def test_extend_token_success(self, app, client):
        """Test successful token extension."""
        with patch('routes.auth.get_user_by_token') as mock_get_user, \
             patch('routes.auth.set_token_expiration') as mock_set_expiry:
            
            # Mock valid user and successful extension
            mock_get_user.return_value = {'user_id': 'user123'}
            mock_set_expiry.return_value = True
            
            response = client.post('/api/v1/auth/token/extend',
                                 headers={'Authorization': 'Bearer valid_token'},
                                 json={'hours': 48})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['hours_extended'] == 48
    
    def test_extend_token_invalid_hours(self, app, client):
        """Test token extension with invalid hours parameter."""
        with patch('routes.auth.get_user_by_token') as mock_get_user:
            # Mock valid user
            mock_get_user.return_value = {'user_id': 'user123'}
            
            response = client.post('/api/v1/auth/token/extend',
                                 headers={'Authorization': 'Bearer valid_token'},
                                 json={'hours': 200})  # Too many hours
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_extend_token_expired_token(self, app, client):
        """Test token extension with expired token."""
        with patch('routes.auth.get_user_by_token') as mock_get_user:
            # Mock expired token
            mock_get_user.return_value = None
            
            response = client.post('/api/v1/auth/token/extend',
                                 headers={'Authorization': 'Bearer expired_token'})
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert 'error' in data 