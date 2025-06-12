#!/usr/bin/env python3
"""
Configuration Management for Corgi Agent System
Centralized configuration and settings management
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import timedelta

@dataclass
class AgentConfig:
    """Base configuration for agents"""
    enabled: bool = True
    priority: str = "medium"
    execution_interval: int = 300  # seconds
    timeout: int = 60  # seconds
    retry_attempts: int = 3
    retry_delay: int = 5  # seconds
    
@dataclass
class WebsiteHealthConfig(AgentConfig):
    """Configuration for Website Health Agent"""
    endpoints: list = None
    response_time_threshold: float = 2.0
    error_rate_threshold: float = 0.05
    availability_threshold: float = 0.99
    check_ssl: bool = True
    check_redirects: bool = True
    
    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = [
                "http://localhost:3000",
                "http://localhost:3000/dashboard", 
                "http://localhost:9999/health",
                "http://localhost:9999/api/v1/health"
            ]

@dataclass
class SecurityConfig(AgentConfig):
    """Configuration for Security Agent"""
    vulnerability_scan_interval: int = 1800  # 30 minutes
    security_headers: list = None
    dependency_check: bool = True
    ssl_check: bool = True
    ports_to_scan: list = None
    
    def __post_init__(self):
        if self.security_headers is None:
            self.security_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options",
                "X-XSS-Protection", 
                "Strict-Transport-Security",
                "Content-Security-Policy"
            ]
        if self.ports_to_scan is None:
            self.ports_to_scan = [3000, 5000, 9999, 5001]

@dataclass  
class PerformanceConfig(AgentConfig):
    """Configuration for Performance Optimization Agent"""
    cpu_threshold: float = 70.0
    memory_threshold: float = 80.0
    disk_threshold: float = 90.0
    response_time_target: float = 1.0
    cache_hit_rate_target: float = 90.0
    optimization_aggressive: bool = False
    
@dataclass
class UserExperienceConfig(AgentConfig):
    """Configuration for User Experience Agent"""
    core_web_vitals: dict = None
    accessibility_checks: bool = True
    mobile_optimization: bool = True
    
    def __post_init__(self):
        if self.core_web_vitals is None:
            self.core_web_vitals = {
                "largest_contentful_paint": 2.5,
                "first_input_delay": 100,
                "cumulative_layout_shift": 0.1
            }

@dataclass
class ContentConfig(AgentConfig):
    """Configuration for Content Management Agent"""
    freshness_threshold_days: int = 30
    seo_optimization: bool = True
    content_quality_checks: bool = True
    link_validation: bool = True
    image_optimization: bool = True

@dataclass
class MLModelConfig(AgentConfig):
    """Configuration for ML Model Agent"""
    performance_threshold: float = 0.8
    drift_threshold: float = 0.2
    model_variants: list = None
    auto_retrain: bool = False
    
    def __post_init__(self):
        if self.model_variants is None:
            self.model_variants = [
                "collaborative_filtering",
                "content_based", 
                "hybrid_ensemble",
                "neural_collaborative",
                "multi_armed_bandit",
                "graph_neural_network"
            ]

@dataclass
class DeploymentConfig(AgentConfig):
    """Configuration for Deployment Agent"""
    auto_scaling: bool = True
    backup_enabled: bool = True
    backup_retention_days: int = 30
    health_check_urls: list = None
    
    def __post_init__(self):
        if self.health_check_urls is None:
            self.health_check_urls = [
                "http://localhost:3000/health",
                "http://localhost:9999/health"
            ]

@dataclass
class SystemConfig:
    """Overall system configuration"""
    database_path: str = "agents/agent_data.db"
    log_level: str = "INFO"
    log_file: str = "agents/agent_system.log"
    dashboard_port: int = 5001
    api_rate_limit: int = 100  # requests per minute
    data_retention_days: int = 90
    notification_webhook: Optional[str] = None
    email_notifications: bool = False
    
    # Agent configurations
    website_health: WebsiteHealthConfig = None
    security: SecurityConfig = None
    performance: PerformanceConfig = None
    user_experience: UserExperienceConfig = None
    content: ContentConfig = None
    ml_model: MLModelConfig = None
    deployment: DeploymentConfig = None
    
    def __post_init__(self):
        if self.website_health is None:
            self.website_health = WebsiteHealthConfig()
        if self.security is None:
            self.security = SecurityConfig()
        if self.performance is None:
            self.performance = PerformanceConfig()
        if self.user_experience is None:
            self.user_experience = UserExperienceConfig()
        if self.content is None:
            self.content = ContentConfig()
        if self.ml_model is None:
            self.ml_model = MLModelConfig()
        if self.deployment is None:
            self.deployment = DeploymentConfig()

class ConfigManager:
    """Manages configuration loading and saving"""
    
    def __init__(self, config_file: str = "agents/config.yaml"):
        self.config_file = Path(config_file)
        self.config: SystemConfig = SystemConfig()
        self.load_config()
        
    def load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    if self.config_file.suffix.lower() == '.yaml':
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)
                
                # Convert dict to SystemConfig
                self.config = self._dict_to_config(data)
            else:
                # Create default config file
                self.save_config()
                
        except Exception as e:
            print(f"Warning: Could not load config file {self.config_file}: {e}")
            print("Using default configuration")
            
    def save_config(self):
        """Save configuration to file"""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert config to dict
            config_dict = self._config_to_dict(self.config)
            
            with open(self.config_file, 'w') as f:
                if self.config_file.suffix.lower() == '.yaml':
                    yaml.safe_dump(config_dict, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_dict, f, indent=2, default=str)
                    
        except Exception as e:
            print(f"Error saving config file: {e}")
    
    def _dict_to_config(self, data: Dict[str, Any]) -> SystemConfig:
        """Convert dictionary to SystemConfig"""
        config = SystemConfig()
        
        # Set main system config
        for key, value in data.items():
            if hasattr(config, key) and not key.endswith('_config'):
                setattr(config, key, value)
        
        # Set agent configs
        agent_configs = {
            'website_health': WebsiteHealthConfig,
            'security': SecurityConfig,
            'performance': PerformanceConfig,
            'user_experience': UserExperienceConfig,
            'content': ContentConfig,
            'ml_model': MLModelConfig,
            'deployment': DeploymentConfig
        }
        
        for agent_name, config_class in agent_configs.items():
            if agent_name in data:
                agent_config = config_class(**data[agent_name])
                setattr(config, agent_name, agent_config)
        
        return config
    
    def _config_to_dict(self, config: SystemConfig) -> Dict[str, Any]:
        """Convert SystemConfig to dictionary"""
        result = {}
        
        # Convert main config
        for key, value in asdict(config).items():
            if isinstance(value, dict):
                result[key] = value
            else:
                result[key] = value
        
        return result
    
    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """Get configuration for a specific agent"""
        return getattr(self.config, agent_name, AgentConfig())
    
    def update_agent_config(self, agent_name: str, updates: Dict[str, Any]):
        """Update configuration for a specific agent"""
        agent_config = getattr(self.config, agent_name, None)
        if agent_config:
            for key, value in updates.items():
                if hasattr(agent_config, key):
                    setattr(agent_config, key, value)
            self.save_config()
    
    def get_environment_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables"""
        overrides = {}
        
        # Environment variable mapping
        env_mapping = {
            'AGENT_LOG_LEVEL': 'log_level',
            'AGENT_DASHBOARD_PORT': 'dashboard_port',
            'AGENT_DB_PATH': 'database_path',
            'AGENT_NOTIFICATION_WEBHOOK': 'notification_webhook',
            'AGENT_EMAIL_NOTIFICATIONS': 'email_notifications',
            'AGENT_DATA_RETENTION_DAYS': 'data_retention_days'
        }
        
        for env_var, config_key in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert to appropriate type
                if config_key in ['dashboard_port', 'data_retention_days']:
                    value = int(value)
                elif config_key in ['email_notifications']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                
                overrides[config_key] = value
        
        return overrides
    
    def apply_environment_overrides(self):
        """Apply environment variable overrides"""
        overrides = self.get_environment_overrides()
        for key, value in overrides.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

# Global config manager instance
config_manager = ConfigManager()

def get_config() -> SystemConfig:
    """Get the global configuration"""
    return config_manager.config

def get_agent_config(agent_name: str) -> AgentConfig:
    """Get configuration for a specific agent"""
    return config_manager.get_agent_config(agent_name)

def update_agent_config(agent_name: str, updates: Dict[str, Any]):
    """Update configuration for a specific agent"""
    config_manager.update_agent_config(agent_name, updates)

def reload_config():
    """Reload configuration from file"""
    config_manager.load_config()
    config_manager.apply_environment_overrides()

# Example configuration file creation
def create_example_config():
    """Create an example configuration file"""
    example_config = {
        "log_level": "INFO",
        "dashboard_port": 5001,
        "data_retention_days": 90,
        "website_health": {
            "enabled": True,
            "execution_interval": 300,
            "response_time_threshold": 2.0,
            "endpoints": [
                "http://localhost:3000", 
                "http://localhost:9999/health"
            ]
        },
        "security": {
            "enabled": True,
            "vulnerability_scan_interval": 1800,
            "dependency_check": True,
            "ssl_check": True
        },
        "performance": {
            "enabled": True,
            "cpu_threshold": 70.0,
            "memory_threshold": 80.0,
            "optimization_aggressive": False
        },
        "user_experience": {
            "enabled": True,
            "accessibility_checks": True,
            "mobile_optimization": True
        },
        "content": {
            "enabled": True,
            "freshness_threshold_days": 30,
            "seo_optimization": True
        },
        "ml_model": {
            "enabled": True,
            "performance_threshold": 0.8,
            "auto_retrain": False
        },
        "deployment": {
            "enabled": True,
            "auto_scaling": True,
            "backup_enabled": True
        }
    }
    
    Path("agents").mkdir(exist_ok=True)
    with open("agents/config.example.yaml", 'w') as f:
        yaml.safe_dump(example_config, f, default_flow_style=False, indent=2)

if __name__ == "__main__":
    # Create example configuration
    create_example_config()
    print("Created example configuration file: agents/config.example.yaml") 