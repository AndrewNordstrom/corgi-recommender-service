#!/usr/bin/env python3
"""
Integration Tests for Complete Agent System
End-to-end testing of agent orchestration, dashboard, and configuration
"""

import pytest
import asyncio
import tempfile
import sqlite3
import requests
import time
import threading
from pathlib import Path
from unittest.mock import patch, AsyncMock
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core_agent_system import AgentOrchestrator, WebsiteHealthAgent, SecurityAgent
from web_agent_dashboard import AgentDashboard
from agent_config import ConfigManager
from agent_launcher import AgentLauncher

class TestFullSystemIntegration:
    """Test complete system integration"""
    
    def setup_method(self):
        """Setup for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_agents.db"
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        
        # Initialize components
        self.orchestrator = AgentOrchestrator()
        self.orchestrator.db_path = str(self.db_path)
        self.orchestrator.setup_database()
        
        self.config_manager = ConfigManager()
        self.dashboard = AgentDashboard(self.orchestrator)
        
        # Create test configuration
        self.config = self.config_manager.create_default_config()
        self.config_manager.save_config(self.config, self.config_path)
    
    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_orchestrator_with_multiple_agents(self):
        """Test orchestrator managing multiple agents"""
        # Register multiple agents
        health_agent = WebsiteHealthAgent()
        security_agent = SecurityAgent()
        
        self.orchestrator.register_agent(health_agent)
        self.orchestrator.register_agent(security_agent)
        
        # Mock agent executions
        with patch.object(health_agent, 'execute') as mock_health, \
             patch.object(security_agent, 'execute') as mock_security, \
             patch.object(health_agent, 'health_check', return_value=True), \
             patch.object(security_agent, 'health_check', return_value=True):
            
            # Configure mock returns
            from core_agent_system import AgentAction
            from datetime import datetime
            
            mock_health.return_value = [
                AgentAction("health_monitor", "endpoint_check", 
                          "Checked endpoints", datetime.now(), "success", {})
            ]
            mock_security.return_value = [
                AgentAction("security_monitor", "vulnerability_scan",
                          "Scanned vulnerabilities", datetime.now(), "success", {})
            ]
            
            # Run agent cycle
            await self.orchestrator.run_agent_cycle()
            
            # Verify both agents were executed
            mock_health.assert_called_once()
            mock_security.assert_called_once()
            
            # Check actions were stored
            assert len(self.orchestrator.action_history) >= 2
    
    def test_dashboard_integration_with_live_data(self):
        """Test dashboard integration with live orchestrator data"""
        # Add agents to orchestrator
        health_agent = WebsiteHealthAgent()
        self.orchestrator.register_agent(health_agent)
        
        # Add some test data
        from core_agent_system import AgentAction
        from datetime import datetime
        
        test_action = AgentAction(
            agent_id="health_monitor",
            action_type="test_integration",
            description="Integration test action",
            timestamp=datetime.now(),
            result="success",
            metadata={"test": True}
        )
        
        self.orchestrator.store_action(test_action)
        
        # Test dashboard endpoints
        app = self.dashboard.app.test_client()
        
        # Test status endpoint
        response = app.get('/api/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total_agents'] == 1
        
        # Test actions endpoint
        response = app.get('/api/actions')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['actions']) >= 1
        assert data['actions'][0]['description'] == "Integration test action"
    
    def test_configuration_affects_orchestrator(self):
        """Test that configuration changes affect orchestrator behavior"""
        # Load configuration
        config = self.config_manager.load_config(self.config_path)
        
        # Modify configuration
        config.website_health.enabled = False
        config.security.enabled = True
        config.security.interval = 120
        
        # Save updated configuration
        self.config_manager.save_config(config, self.config_path)
        
        # Reload configuration
        reloaded_config = self.config_manager.load_config(self.config_path)
        
        assert reloaded_config.website_health.enabled is False
        assert reloaded_config.security.enabled is True
        assert reloaded_config.security.interval == 120
    
    @pytest.mark.asyncio
    async def test_agent_failure_handling(self):
        """Test system behavior when agents fail"""
        # Create agent that will fail
        failing_agent = WebsiteHealthAgent()
        self.orchestrator.register_agent(failing_agent)
        
        # Mock agent to fail
        with patch.object(failing_agent, 'execute', side_effect=Exception("Agent failed")), \
             patch.object(failing_agent, 'health_check', return_value=True):
            
            # Run agent cycle - should handle failure gracefully
            await self.orchestrator.run_agent_cycle()
            
            # Check that failure was recorded
            status = self.orchestrator.get_system_status()
            # System should still be operational despite agent failure
            assert status['total_agents'] == 1
    
    def test_database_persistence(self):
        """Test that data persists across orchestrator instances"""
        # Create first orchestrator instance
        orchestrator1 = AgentOrchestrator()
        orchestrator1.db_path = str(self.db_path)
        orchestrator1.setup_database()
        
        # Add test data
        from core_agent_system import AgentAction
        from datetime import datetime
        
        test_action = AgentAction(
            agent_id="test_agent",
            action_type="persistence_test",
            description="Testing persistence",
            timestamp=datetime.now(),
            result="success",
            metadata={}
        )
        
        orchestrator1.store_action(test_action)
        
        # Create second orchestrator instance
        orchestrator2 = AgentOrchestrator()
        orchestrator2.db_path = str(self.db_path)
        orchestrator2.setup_database()
        
        # Check that data persists
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM agent_actions WHERE description = ?", 
                      ("Testing persistence",))
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1
    
    def test_concurrent_agent_execution(self):
        """Test concurrent agent execution"""
        # Register multiple agents
        agents = [
            WebsiteHealthAgent(),
            SecurityAgent()
        ]
        
        for agent in agents:
            self.orchestrator.register_agent(agent)
        
        # Mock agent executions with delays to test concurrency
        async def mock_health_execute():
            await asyncio.sleep(0.1)  # Simulate work
            from core_agent_system import AgentAction
            from datetime import datetime
            return [AgentAction("health_monitor", "concurrent_test", 
                              "Concurrent execution", datetime.now(), "success", {})]
        
        async def mock_security_execute():
            await asyncio.sleep(0.1)  # Simulate work
            from core_agent_system import AgentAction
            from datetime import datetime
            return [AgentAction("security_monitor", "concurrent_test", 
                              "Concurrent execution", datetime.now(), "success", {})]
        
        with patch.object(agents[0], 'execute', side_effect=mock_health_execute), \
             patch.object(agents[1], 'execute', side_effect=mock_security_execute), \
             patch.object(agents[0], 'health_check', return_value=True), \
             patch.object(agents[1], 'health_check', return_value=True):
            
            # Measure execution time
            start_time = time.time()
            
            # Run the async test
            asyncio.run(self.orchestrator.run_agent_cycle())
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Should complete in less than 0.2 seconds (concurrent) rather than 0.2+ (sequential)
            assert execution_time < 0.2, f"Execution took {execution_time}s, expected concurrent execution"

class TestAgentLauncherIntegration:
    """Test Agent Launcher integration"""
    
    def setup_method(self):
        """Setup for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "launcher_test.db"
        self.config_path = Path(self.temp_dir) / "launcher_config.yaml"
        
        # Create test configuration
        config_manager = ConfigManager()
        config = config_manager.create_default_config()
        config_manager.save_config(config, self.config_path)
    
    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_launcher_initialization(self):
        """Test launcher initialization with configuration"""
        launcher = AgentLauncher(
            config_path=str(self.config_path),
            db_path=str(self.db_path),
            dashboard_port=5555,  # Use different port for testing
            agent_interval=60
        )
        
        assert launcher.config_path == str(self.config_path)
        assert launcher.db_path == str(self.db_path)
        assert launcher.dashboard_port == 5555
        assert launcher.agent_interval == 60
    
    def test_launcher_component_creation(self):
        """Test launcher creates all necessary components"""
        launcher = AgentLauncher(
            config_path=str(self.config_path),
            db_path=str(self.db_path)
        )
        
        orchestrator, dashboard, config = launcher.create_components()
        
        assert orchestrator is not None
        assert dashboard is not None
        assert config is not None
        
        # Check that orchestrator has database setup
        assert Path(launcher.db_path).exists()
        
        # Check that agents are registered
        assert len(orchestrator.agents) > 0

class TestSystemPerformance:
    """Test system performance and resource usage"""
    
    def setup_method(self):
        """Setup for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "performance_test.db"
        
        self.orchestrator = AgentOrchestrator()
        self.orchestrator.db_path = str(self.db_path)
        self.orchestrator.setup_database()
    
    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_high_volume_action_storage(self):
        """Test system performance with high volume of actions"""
        from core_agent_system import AgentAction
        from datetime import datetime
        
        # Generate large number of actions
        start_time = time.time()
        
        for i in range(1000):
            action = AgentAction(
                agent_id=f"test_agent_{i % 10}",
                action_type="performance_test",
                description=f"Performance test action {i}",
                timestamp=datetime.now(),
                result="success",
                metadata={"index": i}
            )
            self.orchestrator.store_action(action)
        
        end_time = time.time()
        storage_time = end_time - start_time
        
        # Should be able to store 1000 actions in reasonable time
        assert storage_time < 10.0, f"Storing 1000 actions took {storage_time}s"
        
        # Verify all actions were stored
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM agent_actions")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1000
    
    def test_memory_usage_with_large_history(self):
        """Test memory usage with large action history"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Add large amount of data to action history
        from core_agent_system import AgentAction
        from datetime import datetime
        
        for i in range(5000):
            action = AgentAction(
                agent_id=f"memory_test_{i % 20}",
                action_type="memory_test",
                description=f"Memory test action {i}",
                timestamp=datetime.now(),
                result="success",
                metadata={"large_data": "x" * 1000}  # 1KB per action
            )
            self.orchestrator.action_history.append(action)
        
        # Get final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for 5000 actions)
        assert memory_increase < 100 * 1024 * 1024, f"Memory increased by {memory_increase / 1024 / 1024:.2f} MB"
    
    @pytest.mark.asyncio
    async def test_concurrent_database_access(self):
        """Test concurrent database access"""
        from core_agent_system import AgentAction
        from datetime import datetime
        
        async def store_actions(agent_id, count):
            for i in range(count):
                action = AgentAction(
                    agent_id=agent_id,
                    action_type="concurrent_test",
                    description=f"Concurrent test {i}",
                    timestamp=datetime.now(),
                    result="success",
                    metadata={}
                )
                self.orchestrator.store_action(action)
        
        # Run multiple concurrent storage operations
        tasks = []
        for i in range(5):
            task = asyncio.create_task(store_actions(f"concurrent_agent_{i}", 100))
            tasks.append(task)
        
        start_time = time.time()
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete concurrent operations efficiently
        assert execution_time < 30.0, f"Concurrent operations took {execution_time}s"
        
        # Verify all actions were stored
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM agent_actions")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 500  # 5 agents * 100 actions each

class TestErrorHandlingAndRecovery:
    """Test error handling and system recovery"""
    
    def setup_method(self):
        """Setup for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "error_test.db"
        
        self.orchestrator = AgentOrchestrator()
        self.orchestrator.db_path = str(self.db_path)
        self.orchestrator.setup_database()
    
    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_database_corruption_recovery(self):
        """Test recovery from database corruption"""
        # Create and populate database
        from core_agent_system import AgentAction
        from datetime import datetime
        
        action = AgentAction(
            agent_id="test_agent",
            action_type="corruption_test",
            description="Before corruption",
            timestamp=datetime.now(),
            result="success",
            metadata={}
        )
        
        self.orchestrator.store_action(action)
        
        # Simulate database corruption by writing invalid data
        with open(str(self.db_path), 'wb') as f:
            f.write(b'corrupted data')
        
        # Create new orchestrator - should handle corruption gracefully
        new_orchestrator = AgentOrchestrator()
        new_orchestrator.db_path = str(self.db_path)
        
        # Should recreate database without crashing
        new_orchestrator.setup_database()
        
        # Should be able to store new actions
        new_action = AgentAction(
            agent_id="recovery_agent",
            action_type="recovery_test",
            description="After recovery",
            timestamp=datetime.now(),
            result="success",
            metadata={}
        )
        
        new_orchestrator.store_action(new_action)
        
        # Verify recovery worked
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT description FROM agent_actions")
        descriptions = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert "After recovery" in descriptions
    
    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self):
        """Test handling of agent timeouts"""
        # Create agent that will timeout
        slow_agent = WebsiteHealthAgent()
        self.orchestrator.register_agent(slow_agent)
        
        # Mock agent to simulate long execution
        async def slow_execute():
            await asyncio.sleep(10)  # Simulate very slow execution
            return []
        
        with patch.object(slow_agent, 'execute', side_effect=slow_execute), \
             patch.object(slow_agent, 'health_check', return_value=True):
            
            # Set short timeout for testing
            original_timeout = self.orchestrator.agent_timeout
            self.orchestrator.agent_timeout = 1.0  # 1 second timeout
            
            try:
                start_time = time.time()
                await self.orchestrator.run_agent_cycle()
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                # Should timeout quickly, not wait for full 10 seconds
                assert execution_time < 5.0, f"Execution took {execution_time}s, timeout not working"
                
            finally:
                self.orchestrator.agent_timeout = original_timeout
    
    def test_dashboard_error_recovery(self):
        """Test dashboard error recovery"""
        dashboard = AgentDashboard(self.orchestrator)
        app = dashboard.app.test_client()
        
        # Test with corrupted database
        original_db_path = self.orchestrator.db_path
        self.orchestrator.db_path = "/nonexistent/path.db"
        
        # Should handle database errors gracefully
        response = app.get('/api/status')
        # Should return some response, not crash
        assert response.status_code in [200, 500]  # Either works or returns server error
        
        # Restore database path
        self.orchestrator.db_path = original_db_path
        
        # Should recover
        response = app.get('/api/status')
        assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"]) 