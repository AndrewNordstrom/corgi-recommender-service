#!/usr/bin/env python3
"""
Comprehensive Tests for Agent Configuration Management
Tests configuration loading, validation, and management
"""

import pytest
import tempfile
import yaml
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_config import (
    AgentConfig, WebsiteHealthConfig, SecurityConfig,
    PerformanceConfig, UserExperienceConfig, ContentConfig,
    MLModelConfig, DeploymentConfig, ConfigManager
)

class TestAgentConfig:
    """Test base agent configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = AgentConfig()
        assert config.enabled is True
        assert config.interval == 300  # 5 minutes
        assert config.priority == "medium"
        assert config.max_retries == 3
        assert config.timeout == 30
        assert config.log_level == "INFO"
    
    def test_config_with_custom_values(self):
        """Test configuration with custom values"""
        config = AgentConfig(
            enabled=False,
            interval=600,
            priority="high",
            max_retries=5,
            timeout=60,
            log_level="DEBUG"
        )
        assert config.enabled is False
        assert config.interval == 600
        assert config.priority == "high"
        assert config.max_retries == 5
        assert config.timeout == 60
        assert config.log_level == "DEBUG"
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Test invalid priority
        with pytest.raises(ValueError):
            AgentConfig(priority="invalid")
        
        # Test invalid log level
        with pytest.raises(ValueError):
            AgentConfig(log_level="INVALID")
        
        # Test negative interval
        with pytest.raises(ValueError):
            AgentConfig(interval=-1)
        
        # Test negative timeout
        with pytest.raises(ValueError):
            AgentConfig(timeout=-1)

class TestWebsiteHealthConfig:
    """Test Website Health configuration"""
    
    def test_default_config(self):
        """Test default website health configuration"""
        config = WebsiteHealthConfig()
        assert len(config.endpoints) > 0
        assert config.response_time_threshold == 2.0
        assert config.uptime_threshold == 99.0
        assert config.check_ssl is True
        assert config.check_redirects is True
    
    def test_custom_config(self):
        """Test custom website health configuration"""
        endpoints = ["/custom", "/api/custom"]
        config = WebsiteHealthConfig(
            endpoints=endpoints,
            response_time_threshold=1.5,
            uptime_threshold=95.0,
            check_ssl=False,
            check_redirects=False
        )
        assert config.endpoints == endpoints
        assert config.response_time_threshold == 1.5
        assert config.uptime_threshold == 95.0
        assert config.check_ssl is False
        assert config.check_redirects is False
    
    def test_config_validation(self):
        """Test website health configuration validation"""
        # Test invalid response time threshold
        with pytest.raises(ValueError):
            WebsiteHealthConfig(response_time_threshold=-1.0)
        
        # Test invalid uptime threshold
        with pytest.raises(ValueError):
            WebsiteHealthConfig(uptime_threshold=101.0)

class TestSecurityConfig:
    """Test Security configuration"""
    
    def test_default_config(self):
        """Test default security configuration"""
        config = SecurityConfig()
        assert len(config.vulnerability_scanners) > 0
        assert config.dependency_check is True
        assert config.ssl_check is True
        assert config.security_headers_check is True
        assert config.api_security_check is True
        assert config.vulnerability_threshold == "medium"
    
    def test_custom_config(self):
        """Test custom security configuration"""
        scanners = ["custom_scanner"]
        config = SecurityConfig(
            vulnerability_scanners=scanners,
            dependency_check=False,
            ssl_check=False,
            security_headers_check=False,
            api_security_check=False,
            vulnerability_threshold="high"
        )
        assert config.vulnerability_scanners == scanners
        assert config.dependency_check is False
        assert config.ssl_check is False
        assert config.security_headers_check is False
        assert config.api_security_check is False
        assert config.vulnerability_threshold == "high"
    
    def test_config_validation(self):
        """Test security configuration validation"""
        # Test invalid vulnerability threshold
        with pytest.raises(ValueError):
            SecurityConfig(vulnerability_threshold="invalid")

class TestPerformanceConfig:
    """Test Performance configuration"""
    
    def test_default_config(self):
        """Test default performance configuration"""
        config = PerformanceConfig()
        assert config.cpu_threshold == 80.0
        assert config.memory_threshold == 85.0
        assert config.disk_threshold == 90.0
        assert config.response_time_threshold == 2.0
        assert config.enable_caching is True
        assert config.enable_compression is True
    
    def test_custom_config(self):
        """Test custom performance configuration"""
        config = PerformanceConfig(
            cpu_threshold=70.0,
            memory_threshold=75.0,
            disk_threshold=80.0,
            response_time_threshold=1.0,
            enable_caching=False,
            enable_compression=False
        )
        assert config.cpu_threshold == 70.0
        assert config.memory_threshold == 75.0
        assert config.disk_threshold == 80.0
        assert config.response_time_threshold == 1.0
        assert config.enable_caching is False
        assert config.enable_compression is False
    
    def test_config_validation(self):
        """Test performance configuration validation"""
        # Test invalid CPU threshold
        with pytest.raises(ValueError):
            PerformanceConfig(cpu_threshold=101.0)
        
        # Test invalid memory threshold
        with pytest.raises(ValueError):
            PerformanceConfig(memory_threshold=-1.0)

class TestUserExperienceConfig:
    """Test User Experience configuration"""
    
    def test_default_config(self):
        """Test default UX configuration"""
        config = UserExperienceConfig()
        assert len(config.metrics) > 0
        assert config.core_web_vitals_check is True
        assert config.accessibility_check is True
        assert config.mobile_optimization_check is True
        assert config.performance_budget_check is True
        assert config.lcp_threshold == 2.5
        assert config.fid_threshold == 100
        assert config.cls_threshold == 0.1
    
    def test_custom_config(self):
        """Test custom UX configuration"""
        metrics = ["custom_metric"]
        config = UserExperienceConfig(
            metrics=metrics,
            core_web_vitals_check=False,
            accessibility_check=False,
            mobile_optimization_check=False,
            performance_budget_check=False,
            lcp_threshold=3.0,
            fid_threshold=150,
            cls_threshold=0.2
        )
        assert config.metrics == metrics
        assert config.core_web_vitals_check is False
        assert config.accessibility_check is False
        assert config.mobile_optimization_check is False
        assert config.performance_budget_check is False
        assert config.lcp_threshold == 3.0
        assert config.fid_threshold == 150
        assert config.cls_threshold == 0.2
    
    def test_config_validation(self):
        """Test UX configuration validation"""
        # Test invalid LCP threshold
        with pytest.raises(ValueError):
            UserExperienceConfig(lcp_threshold=-1.0)
        
        # Test invalid FID threshold
        with pytest.raises(ValueError):
            UserExperienceConfig(fid_threshold=-1)

class TestMLModelConfig:
    """Test ML Model configuration"""
    
    def test_default_config(self):
        """Test default ML model configuration"""
        config = MLModelConfig()
        assert config.model_monitoring is True
        assert config.drift_detection is True
        assert config.performance_monitoring is True
        assert config.a_b_testing is True
        assert config.drift_threshold == 0.1
        assert config.performance_threshold == 0.8
        assert config.retraining_threshold == 0.05
    
    def test_custom_config(self):
        """Test custom ML model configuration"""
        config = MLModelConfig(
            model_monitoring=False,
            drift_detection=False,
            performance_monitoring=False,
            a_b_testing=False,
            drift_threshold=0.2,
            performance_threshold=0.9,
            retraining_threshold=0.1
        )
        assert config.model_monitoring is False
        assert config.drift_detection is False
        assert config.performance_monitoring is False
        assert config.a_b_testing is False
        assert config.drift_threshold == 0.2
        assert config.performance_threshold == 0.9
        assert config.retraining_threshold == 0.1
    
    def test_config_validation(self):
        """Test ML model configuration validation"""
        # Test invalid drift threshold
        with pytest.raises(ValueError):
            MLModelConfig(drift_threshold=-1.0)
        
        # Test invalid performance threshold
        with pytest.raises(ValueError):
            MLModelConfig(performance_threshold=1.1)

class TestConfigManager:
    """Test Configuration Manager"""
    
    def setup_method(self):
        """Setup for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        self.config_manager = ConfigManager()
    
    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_create_default_config(self):
        """Test creating default configuration"""
        config = self.config_manager.create_default_config()
        
        assert hasattr(config, 'website_health')
        assert hasattr(config, 'security')
        assert hasattr(config, 'performance')
        assert hasattr(config, 'user_experience')
        assert hasattr(config, 'content_management')
        assert hasattr(config, 'ml_model')
        assert hasattr(config, 'deployment')
        
        # Check individual configs
        assert isinstance(config.website_health, WebsiteHealthConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.performance, PerformanceConfig)
    
    def test_save_config_yaml(self):
        """Test saving configuration to YAML"""
        config = self.config_manager.create_default_config()
        self.config_manager.save_config(config, self.config_path)
        
        assert self.config_path.exists()
        
        # Verify YAML structure
        with open(self.config_path, 'r') as f:
            yaml_data = yaml.safe_load(f)
        
        assert 'website_health' in yaml_data
        assert 'security' in yaml_data
        assert 'performance' in yaml_data
    
    def test_save_config_json(self):
        """Test saving configuration to JSON"""
        config = self.config_manager.create_default_config()
        json_path = Path(self.temp_dir) / "test_config.json"
        self.config_manager.save_config(config, json_path)
        
        assert json_path.exists()
        
        # Verify JSON structure
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        
        assert 'website_health' in json_data
        assert 'security' in json_data
        assert 'performance' in json_data
    
    def test_load_config_yaml(self):
        """Test loading configuration from YAML"""
        # Create test YAML
        test_config = {
            'website_health': {
                'enabled': True,
                'interval': 300,
                'endpoints': ['/health', '/api/health'],
                'response_time_threshold': 2.0
            },
            'security': {
                'enabled': True,
                'interval': 600,
                'vulnerability_scanners': ['safety', 'bandit']
            }
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        config = self.config_manager.load_config(self.config_path)
        
        assert config.website_health.enabled is True
        assert config.website_health.interval == 300
        assert config.website_health.endpoints == ['/health', '/api/health']
        assert config.security.enabled is True
        assert config.security.interval == 600
    
    def test_load_config_json(self):
        """Test loading configuration from JSON"""
        json_path = Path(self.temp_dir) / "test_config.json"
        test_config = {
            'website_health': {
                'enabled': False,
                'interval': 400,
                'response_time_threshold': 1.5
            },
            'performance': {
                'enabled': True,
                'cpu_threshold': 75.0,
                'memory_threshold': 80.0
            }
        }
        
        with open(json_path, 'w') as f:
            json.dump(test_config, f)
        
        config = self.config_manager.load_config(json_path)
        
        assert config.website_health.enabled is False
        assert config.website_health.interval == 400
        assert config.website_health.response_time_threshold == 1.5
        assert config.performance.cpu_threshold == 75.0
    
    def test_load_config_nonexistent_file(self):
        """Test loading configuration from non-existent file"""
        nonexistent_path = Path(self.temp_dir) / "nonexistent.yaml"
        
        with pytest.raises(FileNotFoundError):
            self.config_manager.load_config(nonexistent_path)
    
    def test_load_config_invalid_yaml(self):
        """Test loading configuration from invalid YAML"""
        invalid_yaml = "invalid: yaml: content: ["
        
        with open(self.config_path, 'w') as f:
            f.write(invalid_yaml)
        
        with pytest.raises(yaml.YAMLError):
            self.config_manager.load_config(self.config_path)
    
    def test_load_config_invalid_json(self):
        """Test loading configuration from invalid JSON"""
        json_path = Path(self.temp_dir) / "invalid.json"
        invalid_json = '{"invalid": json, "content":'
        
        with open(json_path, 'w') as f:
            f.write(invalid_json)
        
        with pytest.raises(json.JSONDecodeError):
            self.config_manager.load_config(json_path)
    
    def test_validate_config(self):
        """Test configuration validation"""
        valid_config = self.config_manager.create_default_config()
        
        # Should not raise any exception
        self.config_manager.validate_config(valid_config)
        
        # Test with invalid configuration
        valid_config.website_health.response_time_threshold = -1.0
        
        with pytest.raises(ValueError):
            self.config_manager.validate_config(valid_config)
    
    def test_merge_configs(self):
        """Test merging configurations"""
        base_config = self.config_manager.create_default_config()
        
        # Create override config
        override_data = {
            'website_health': {
                'enabled': False,
                'interval': 600
            },
            'security': {
                'vulnerability_threshold': 'high'
            }
        }
        
        merged_config = self.config_manager.merge_configs(base_config, override_data)
        
        # Check that overrides were applied
        assert merged_config.website_health.enabled is False
        assert merged_config.website_health.interval == 600
        assert merged_config.security.vulnerability_threshold == 'high'
        
        # Check that non-overridden values remain
        assert merged_config.website_health.response_time_threshold == 2.0  # default
        assert merged_config.security.dependency_check is True  # default
    
    def test_environment_variable_override(self):
        """Test environment variable configuration override"""
        with patch.dict(os.environ, {
            'AGENT_WEBSITE_HEALTH_ENABLED': 'false',
            'AGENT_WEBSITE_HEALTH_INTERVAL': '900',
            'AGENT_SECURITY_VULNERABILITY_THRESHOLD': 'low'
        }):
            config = self.config_manager.load_config_with_env_override()
            
            assert config.website_health.enabled is False
            assert config.website_health.interval == 900
            assert config.security.vulnerability_threshold == 'low'
    
    def test_config_schema_validation(self):
        """Test configuration schema validation"""
        # Test with missing required fields
        incomplete_config = {
            'website_health': {
                'enabled': True
                # Missing interval and other required fields
            }
        }
        
        # Should use defaults for missing fields
        config = self.config_manager.create_config_from_dict(incomplete_config)
        assert config.website_health.interval == 300  # default
    
    def test_config_type_conversion(self):
        """Test configuration type conversion"""
        string_config = {
            'website_health': {
                'enabled': 'true',  # string instead of bool
                'interval': '600',  # string instead of int
                'response_time_threshold': '1.5'  # string instead of float
            }
        }
        
        config = self.config_manager.create_config_from_dict(string_config)
        
        assert config.website_health.enabled is True
        assert config.website_health.interval == 600
        assert config.website_health.response_time_threshold == 1.5

class TestConfigIntegration:
    """Test configuration integration with agent system"""
    
    def setup_method(self):
        """Setup for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "integration_config.yaml"
        self.config_manager = ConfigManager()
    
    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_config_affects_agent_behavior(self):
        """Test that configuration affects agent behavior"""
        # Create custom config
        custom_config = self.config_manager.create_default_config()
        custom_config.website_health.enabled = False
        custom_config.security.enabled = True
        custom_config.security.interval = 120
        
        # Save and load config
        self.config_manager.save_config(custom_config, self.config_path)
        loaded_config = self.config_manager.load_config(self.config_path)
        
        assert loaded_config.website_health.enabled is False
        assert loaded_config.security.enabled is True
        assert loaded_config.security.interval == 120
    
    def test_config_update_without_restart(self):
        """Test configuration update without system restart"""
        # Initial config
        config = self.config_manager.create_default_config()
        config.website_health.interval = 300
        
        # Update config
        config.website_health.interval = 600
        self.config_manager.save_config(config, self.config_path)
        
        # Reload config
        updated_config = self.config_manager.load_config(self.config_path)
        assert updated_config.website_health.interval == 600
    
    def test_config_backup_and_restore(self):
        """Test configuration backup and restore functionality"""
        # Create original config
        original_config = self.config_manager.create_default_config()
        original_config.website_health.interval = 300
        
        # Save original
        self.config_manager.save_config(original_config, self.config_path)
        
        # Create backup
        backup_path = Path(self.temp_dir) / "backup_config.yaml"
        self.config_manager.backup_config(self.config_path, backup_path)
        
        # Modify original
        original_config.website_health.interval = 600
        self.config_manager.save_config(original_config, self.config_path)
        
        # Restore from backup
        restored_config = self.config_manager.load_config(backup_path)
        assert restored_config.website_health.interval == 300

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 