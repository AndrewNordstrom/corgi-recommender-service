#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Core Agent System
Tests all agent functionality and orchestration
"""

import pytest
import asyncio
import tempfile
import sqlite3
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from pathlib import Path

# Import the agent system components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core_agent_system import (
    AgentOrchestrator, WebsiteHealthAgent, SecurityAgent,
    PerformanceOptimizationAgent, UserExperienceAgent,
    ContentManagementAgent, MLModelAgent, DeploymentAgent,
    AgentAction, AgentMetrics, AgentStatus, AgentPriority
)

class TestAgentMetrics:
    """Test agent metrics functionality"""
    
    def test_metrics_initialization(self):
        """Test metric initialization with default values"""
        metrics = AgentMetrics()
        assert metrics.tasks_completed == 0
        assert metrics.errors_encountered == 0
        assert metrics.average_response_time == 0.0
        assert metrics.performance_score == 100.0
        assert metrics.last_activity is None
    
    def test_metrics_with_values(self):
        """Test metrics with custom values"""
        now = datetime.now()
        metrics = AgentMetrics(
            tasks_completed=10,
            errors_encountered=2,
            average_response_time=1.5,
            performance_score=85.0,
            last_activity=now
        )
        assert metrics.tasks_completed == 10
        assert metrics.errors_encountered == 2
        assert metrics.average_response_time == 1.5
        assert metrics.performance_score == 85.0
        assert metrics.last_activity == now

class TestAgentAction:
    """Test agent action creation and properties"""
    
    def test_action_creation(self):
        """Test creating an agent action"""
        now = datetime.now()
        action = AgentAction(
            agent_id="test_agent",
            action_type="test_action",
            description="Test description",
            timestamp=now,
            result="success",
            metadata={"key": "value"}
        )
        
        assert action.agent_id == "test_agent"
        assert action.action_type == "test_action"
        assert action.description == "Test description"
        assert action.timestamp == now
        assert action.result == "success"
        assert action.metadata == {"key": "value"}

class TestWebsiteHealthAgent:
    """Test Website Health Agent functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.agent = WebsiteHealthAgent()
    
    def test_agent_initialization(self):
        """Test agent initialization"""
        assert self.agent.agent_id == "health_monitor"
        assert self.agent.name == "Website Health Agent"
        assert self.agent.priority == AgentPriority.CRITICAL
        assert self.agent.status == AgentStatus.IDLE
        assert len(self.agent.endpoints) > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test agent health check"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await self.agent.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test agent health check failure"""
        with patch('aiohttp.ClientSession.get', side_effect=Exception("Connection failed")):
            result = await self.agent.health_check()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful execution"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="OK")
            mock_get.return_value.__aenter__.return_value = mock_response
            
            actions = await self.agent.execute()
            assert len(actions) > 0
            assert all(action.agent_id == "health_monitor" for action in actions)
    
    @pytest.mark.asyncio
    async def test_execute_slow_response(self):
        """Test execution with slow response detection"""
        with patch('aiohttp.ClientSession.get') as mock_get, \
             patch('time.time', side_effect=[0, 3.0]):  # Simulate 3 second response
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="OK")
            mock_get.return_value.__aenter__.return_value = mock_response
            
            actions = await self.agent.execute()
            # Should include alert for slow response
            alert_actions = [a for a in actions if a.action_type == "performance_alert"]
            assert len(alert_actions) > 0

class TestSecurityAgent:
    """Test Security Agent functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.agent = SecurityAgent()
    
    def test_agent_initialization(self):
        """Test agent initialization"""
        assert self.agent.agent_id == "security_monitor"
        assert self.agent.name == "Security Agent"
        assert self.agent.priority == AgentPriority.CRITICAL
        assert len(self.agent.security_checks) > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test agent health check"""
        result = await self.agent.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_dependency_vulnerability_check(self):
        """Test dependency vulnerability checking"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "metadata": {
                    "vulnerabilities": {
                        "critical": 0,
                        "high": 0
                    }
                }
            })
            
            result = await self.agent.check_dependency_vulnerabilities()
            assert result["status"] == "pass"
    
    @pytest.mark.asyncio
    async def test_dependency_vulnerability_found(self):
        """Test dependency vulnerability detection"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "metadata": {
                    "vulnerabilities": {
                        "critical": 2,
                        "high": 3
                    }
                }
            })
            
            result = await self.agent.check_dependency_vulnerabilities()
            assert result["status"] == "fail"
            assert "2 critical and 3 high" in result["message"]
    
    @pytest.mark.asyncio
    async def test_api_security_check(self):
        """Test API security header checking"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000"
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await self.agent.check_api_security()
            assert result["status"] == "pass"
    
    @pytest.mark.asyncio
    async def test_api_security_missing_headers(self):
        """Test API security with missing headers"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.headers = {}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await self.agent.check_api_security()
            assert result["status"] == "warning"
            assert "missing_headers" in result

class TestPerformanceOptimizationAgent:
    """Test Performance Optimization Agent"""
    
    def setup_method(self):
        """Setup for each test"""
        self.agent = PerformanceOptimizationAgent()
    
    def test_agent_initialization(self):
        """Test agent initialization"""
        assert self.agent.agent_id == "performance_optimizer"
        assert self.agent.name == "Performance Optimization Agent"
        assert self.agent.priority == AgentPriority.HIGH
        assert "response_time" in self.agent.optimization_targets
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test agent health check"""
        result = await self.agent.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_optimize_system_resources(self):
        """Test system resource optimization"""
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory:
            
            mock_memory.return_value.percent = 60.0
            
            action = await self.agent.optimize_system_resources()
            assert action.agent_id == "performance_optimizer"
            assert action.action_type == "system_optimization"
            assert action.result == "success"
    
    @pytest.mark.asyncio
    async def test_optimize_system_resources_high_usage(self):
        """Test system resource optimization with high usage"""
        with patch('psutil.cpu_percent', return_value=85.0), \
             patch('psutil.virtual_memory') as mock_memory:
            
            mock_memory.return_value.percent = 90.0
            
            action = await self.agent.optimize_system_resources()
            assert action.result == "success"
            optimizations = action.metadata.get("optimizations", [])
            assert len(optimizations) > 0

class TestUserExperienceAgent:
    """Test User Experience Agent"""
    
    def setup_method(self):
        """Setup for each test"""
        self.agent = UserExperienceAgent()
    
    def test_agent_initialization(self):
        """Test agent initialization"""
        assert self.agent.agent_id == "ux_optimizer"
        assert self.agent.name == "User Experience Agent"
        assert self.agent.priority == AgentPriority.HIGH
        assert len(self.agent.ux_metrics) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_core_web_vitals(self):
        """Test Core Web Vitals analysis"""
        action = await self.agent.analyze_core_web_vitals()
        assert action.action_type == "core_web_vitals_analysis"
        assert "vitals" in action.metadata
        vitals = action.metadata["vitals"]
        assert "largest_contentful_paint" in vitals
        assert "first_input_delay" in vitals
        assert "cumulative_layout_shift" in vitals
    
    @pytest.mark.asyncio
    async def test_check_accessibility(self):
        """Test accessibility checking"""
        action = await self.agent.check_accessibility()
        assert action.action_type == "accessibility_check"
        assert action.result == "success"
        assert "checks_performed" in action.metadata
    
    @pytest.mark.asyncio
    async def test_analyze_user_behavior(self):
        """Test user behavior analysis"""
        action = await self.agent.analyze_user_behavior()
        assert action.action_type == "user_behavior_analysis"
        assert "average_session_duration" in action.metadata
        assert "bounce_rate" in action.metadata

class TestMLModelAgent:
    """Test ML Model Agent"""
    
    def setup_method(self):
        """Setup for each test"""
        self.agent = MLModelAgent()
    
    def test_agent_initialization(self):
        """Test agent initialization"""
        assert self.agent.agent_id == "ml_model_manager"
        assert self.agent.name == "ML Model Agent"
        assert self.agent.priority == AgentPriority.HIGH
    
    @pytest.mark.asyncio
    async def test_monitor_model_performance(self):
        """Test model performance monitoring"""
        action = await self.agent.monitor_model_performance()
        assert action.action_type == "model_performance_monitoring"
        assert "metrics" in action.metadata
        metrics = action.metadata["metrics"]
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
    
    @pytest.mark.asyncio
    async def test_check_model_drift(self):
        """Test model drift detection"""
        action = await self.agent.check_model_drift()
        assert action.action_type == "model_drift_check"
        assert "drift_metrics" in action.metadata
        drift_metrics = action.metadata["drift_metrics"]
        assert "data_drift_score" in drift_metrics
        assert "concept_drift_score" in drift_metrics
    
    @pytest.mark.asyncio
    async def test_optimize_model_selection(self):
        """Test model selection optimization"""
        action = await self.agent.optimize_model_selection()
        assert action.action_type == "model_selection_optimization"
        assert "recommendations" in action.metadata

class TestAgentOrchestrator:
    """Test Agent Orchestrator functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        # Use temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.orchestrator = AgentOrchestrator()
        self.orchestrator.db_path = self.temp_db.name
        self.orchestrator.setup_database()
    
    def teardown_method(self):
        """Cleanup after each test"""
        Path(self.temp_db.name).unlink(missing_ok=True)
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        assert isinstance(self.orchestrator.agents, dict)
        assert isinstance(self.orchestrator.action_history, list)
        assert len(self.orchestrator.agents) == 0
    
    def test_register_agent(self):
        """Test agent registration"""
        agent = WebsiteHealthAgent()
        self.orchestrator.register_agent(agent)
        
        assert agent.agent_id in self.orchestrator.agents
        assert self.orchestrator.agents[agent.agent_id] == agent
    
    def test_store_action(self):
        """Test action storage"""
        action = AgentAction(
            agent_id="test_agent",
            action_type="test_action",
            description="Test description",
            timestamp=datetime.now(),
            result="success",
            metadata={"key": "value"}
        )
        
        self.orchestrator.store_action(action)
        
        # Verify action was stored
        conn = sqlite3.connect(self.orchestrator.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM agent_actions")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1
    
    def test_store_agent_metrics(self):
        """Test agent metrics storage"""
        agent = WebsiteHealthAgent()
        agent.metrics.tasks_completed = 5
        agent.metrics.errors_encountered = 1
        agent.metrics.last_activity = datetime.now()
        
        self.orchestrator.store_agent_metrics(agent)
        
        # Verify metrics were stored
        conn = sqlite3.connect(self.orchestrator.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM agent_metrics")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_run_agent_cycle(self):
        """Test running a complete agent cycle"""
        # Register test agents
        health_agent = WebsiteHealthAgent()
        security_agent = SecurityAgent()
        
        self.orchestrator.register_agent(health_agent)
        self.orchestrator.register_agent(security_agent)
        
        # Mock the health checks and executions
        with patch.object(health_agent, 'health_check', return_value=True), \
             patch.object(health_agent, 'execute', return_value=[
                 AgentAction("health_monitor", "test", "Test action", datetime.now(), "success")
             ]), \
             patch.object(security_agent, 'health_check', return_value=True), \
             patch.object(security_agent, 'execute', return_value=[
                 AgentAction("security_monitor", "test", "Test action", datetime.now(), "success")
             ]):
            
            await self.orchestrator.run_agent_cycle()
            
            # Verify actions were stored
            assert len(self.orchestrator.action_history) > 0
    
    def test_get_system_status(self):
        """Test system status retrieval"""
        # Register test agents
        agent1 = WebsiteHealthAgent()
        agent2 = SecurityAgent()
        
        self.orchestrator.register_agent(agent1)
        self.orchestrator.register_agent(agent2)
        
        status = self.orchestrator.get_system_status()
        
        assert status["total_agents"] == 2
        assert status["active_agents"] == 0  # Initially idle
        assert status["error_agents"] == 0
        assert len(status["agents"]) == 2

class TestAgentUpdateMetrics:
    """Test agent metrics update functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.agent = WebsiteHealthAgent()
    
    @pytest.mark.asyncio
    async def test_update_metrics_success(self):
        """Test updating metrics after successful execution"""
        execution_time = 1.5
        success = True
        
        await self.agent.update_metrics(execution_time, success)
        
        assert self.agent.metrics.tasks_completed == 1
        assert self.agent.metrics.errors_encountered == 0
        assert self.agent.metrics.average_response_time == execution_time
        assert self.agent.metrics.performance_score == 100.0
        assert self.agent.metrics.last_activity is not None
    
    @pytest.mark.asyncio
    async def test_update_metrics_failure(self):
        """Test updating metrics after failed execution"""
        execution_time = 2.0
        success = False
        
        await self.agent.update_metrics(execution_time, success)
        
        assert self.agent.metrics.tasks_completed == 1
        assert self.agent.metrics.errors_encountered == 1
        assert self.agent.metrics.average_response_time == execution_time
        assert self.agent.metrics.performance_score == 0.0  # 100% error rate
    
    @pytest.mark.asyncio
    async def test_update_metrics_multiple_executions(self):
        """Test metrics after multiple executions"""
        # First execution - success
        await self.agent.update_metrics(1.0, True)
        
        # Second execution - failure
        await self.agent.update_metrics(2.0, False)
        
        # Third execution - success
        await self.agent.update_metrics(1.5, True)
        
        assert self.agent.metrics.tasks_completed == 3
        assert self.agent.metrics.errors_encountered == 1
        # Average should be weighted: 1.0 * 0.7 + 2.0 * 0.3 = 1.3, then 1.3 * 0.7 + 1.5 * 0.3 = 1.36
        assert abs(self.agent.metrics.average_response_time - 1.36) < 0.1
        # Error rate: 1/3 = 33.33%, so performance score: 100 - 33.33 = 66.67
        assert abs(self.agent.metrics.performance_score - 66.67) < 0.1

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 