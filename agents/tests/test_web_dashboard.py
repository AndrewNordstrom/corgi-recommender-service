#!/usr/bin/env python3
"""
Comprehensive Tests for Web Agent Dashboard
Tests Flask API endpoints and dashboard functionality
"""

import pytest
import json
import tempfile
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_agent_dashboard import AgentDashboard
from core_agent_system import (
    AgentOrchestrator, WebsiteHealthAgent, SecurityAgent,
    AgentAction, AgentMetrics, AgentStatus
)

class TestAgentDashboard:
    """Test Agent Dashboard Web Interface"""
    
    def setup_method(self):
        """Setup for each test"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Initialize orchestrator with temp database
        self.orchestrator = AgentOrchestrator()
        self.orchestrator.db_path = self.temp_db.name
        self.orchestrator.setup_database()
        
        # Initialize dashboard
        self.dashboard = AgentDashboard(self.orchestrator)
        self.app = self.dashboard.app.test_client()
        self.app.testing = True
        
        # Add test agents
        self.health_agent = WebsiteHealthAgent()
        self.security_agent = SecurityAgent()
        self.orchestrator.register_agent(self.health_agent)
        self.orchestrator.register_agent(self.security_agent)
        
        # Add test data
        self._add_test_data()
    
    def teardown_method(self):
        """Cleanup after each test"""
        Path(self.temp_db.name).unlink(missing_ok=True)
    
    def _add_test_data(self):
        """Add test data to database"""
        # Add test actions
        test_actions = [
            AgentAction(
                agent_id="health_monitor",
                action_type="endpoint_check",
                description="Checked API health",
                timestamp=datetime.now() - timedelta(minutes=5),
                result="success",
                metadata={"endpoint": "/health", "response_time": 0.5}
            ),
            AgentAction(
                agent_id="security_monitor",
                action_type="vulnerability_scan",
                description="Scanned for vulnerabilities",
                timestamp=datetime.now() - timedelta(minutes=3),
                result="warning",
                metadata={"issues_found": 2}
            ),
            AgentAction(
                agent_id="health_monitor",
                action_type="performance_check",
                description="Monitored performance",
                timestamp=datetime.now() - timedelta(minutes=1),
                result="success",
                metadata={"cpu_usage": 45.2, "memory_usage": 62.1}
            )
        ]
        
        for action in test_actions:
            self.orchestrator.store_action(action)
        
        # Update agent metrics
        self.health_agent.metrics.tasks_completed = 10
        self.health_agent.metrics.errors_encountered = 1
        self.health_agent.metrics.last_activity = datetime.now()
        self.health_agent.status = AgentStatus.ACTIVE
        
        self.security_agent.metrics.tasks_completed = 5
        self.security_agent.metrics.errors_encountered = 0
        self.security_agent.metrics.last_activity = datetime.now()
        self.security_agent.status = AgentStatus.IDLE
        
        self.orchestrator.store_agent_metrics(self.health_agent)
        self.orchestrator.store_agent_metrics(self.security_agent)
    
    def test_homepage_render(self):
        """Test homepage renders correctly"""
        response = self.app.get('/')
        assert response.status_code == 200
        assert b'Agent Management Dashboard' in response.data
        assert b'System Overview' in response.data
        assert b'Agent Status' in response.data
    
    def test_api_status_endpoint(self):
        """Test /api/status endpoint"""
        response = self.app.get('/api/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'total_agents' in data
        assert 'active_agents' in data
        assert 'error_agents' in data
        assert 'agents' in data
        assert data['total_agents'] == 2
        assert len(data['agents']) == 2
    
    def test_api_metrics_endpoint(self):
        """Test /api/metrics endpoint"""
        response = self.app.get('/api/metrics')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'system_metrics' in data
        assert 'agent_metrics' in data
        
        system_metrics = data['system_metrics']
        assert 'total_actions' in system_metrics
        assert 'success_rate' in system_metrics
        assert 'error_rate' in system_metrics
        
        agent_metrics = data['agent_metrics']
        assert len(agent_metrics) == 2
        
        # Check health agent metrics
        health_metrics = next(m for m in agent_metrics if m['agent_id'] == 'health_monitor')
        assert health_metrics['tasks_completed'] == 10
        assert health_metrics['errors_encountered'] == 1
    
    def test_api_actions_endpoint(self):
        """Test /api/actions endpoint"""
        response = self.app.get('/api/actions')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'actions' in data
        assert len(data['actions']) == 3
        
        # Check first action (most recent)
        first_action = data['actions'][0]
        assert first_action['agent_id'] == 'health_monitor'
        assert first_action['action_type'] == 'performance_check'
        assert first_action['result'] == 'success'
    
    def test_api_actions_with_limit(self):
        """Test /api/actions endpoint with limit parameter"""
        response = self.app.get('/api/actions?limit=2')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data['actions']) == 2
    
    def test_api_actions_by_agent(self):
        """Test /api/actions endpoint filtered by agent"""
        response = self.app.get('/api/actions?agent_id=health_monitor')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data['actions']) == 2
        for action in data['actions']:
            assert action['agent_id'] == 'health_monitor'
    
    def test_api_trigger_cycle(self):
        """Test /api/trigger-cycle endpoint"""
        with pytest.mock.patch.object(self.orchestrator, 'run_agent_cycle') as mock_cycle:
            mock_cycle.return_value = None
            
            response = self.app.post('/api/trigger-cycle')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['status'] == 'success'
            assert 'Agent cycle triggered' in data['message']
            
            mock_cycle.assert_called_once()
    
    def test_api_export_report(self):
        """Test /api/export-report endpoint"""
        response = self.app.get('/api/export-report')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'report' in data
        
        report = data['report']
        assert 'timestamp' in report
        assert 'system_status' in report
        assert 'agent_metrics' in report
        assert 'recent_actions' in report
        assert 'summary' in report
        
        # Check summary statistics
        summary = report['summary']
        assert 'total_actions' in summary
        assert 'successful_actions' in summary
        assert 'error_actions' in summary
        assert 'warning_actions' in summary
    
    def test_api_agent_details(self):
        """Test /api/agent/<agent_id> endpoint"""
        response = self.app.get('/api/agent/health_monitor')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['agent_id'] == 'health_monitor'
        assert data['name'] == 'Website Health Agent'
        assert data['status'] == 'active'
        assert 'metrics' in data
        assert 'recent_actions' in data
    
    def test_api_agent_not_found(self):
        """Test /api/agent/<agent_id> endpoint with non-existent agent"""
        response = self.app.get('/api/agent/nonexistent')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Agent not found' in data['error']
    
    def test_dashboard_statistics(self):
        """Test dashboard statistics calculation"""
        stats = self.dashboard.get_dashboard_statistics()
        
        assert 'total_actions' in stats
        assert 'success_rate' in stats
        assert 'error_rate' in stats
        assert 'warning_rate' in stats
        assert 'active_agents' in stats
        assert 'idle_agents' in stats
        
        assert stats['total_actions'] == 3
        assert stats['success_rate'] == 66.67  # 2 success out of 3
        assert stats['warning_rate'] == 33.33  # 1 warning out of 3
        assert stats['active_agents'] == 1
        assert stats['idle_agents'] == 1
    
    def test_system_health_score(self):
        """Test system health score calculation"""
        health_score = self.dashboard.calculate_system_health_score()
        
        assert 0 <= health_score <= 100
        # With 2 success and 1 warning, should be good but not perfect
        assert 60 <= health_score <= 85
    
    def test_performance_trends(self):
        """Test performance trends calculation"""
        trends = self.dashboard.get_performance_trends()
        
        assert 'hourly_actions' in trends
        assert 'success_rate_trend' in trends
        assert 'response_time_trend' in trends
        
        # Should have data for recent hours
        assert len(trends['hourly_actions']) > 0
    
    def test_agent_status_distribution(self):
        """Test agent status distribution"""
        distribution = self.dashboard.get_agent_status_distribution()
        
        assert 'active' in distribution
        assert 'idle' in distribution
        assert 'error' in distribution
        
        assert distribution['active'] == 1
        assert distribution['idle'] == 1
        assert distribution['error'] == 0
    
    def test_error_handling_invalid_json(self):
        """Test error handling for invalid JSON requests"""
        response = self.app.post('/api/trigger-cycle', 
                               data='invalid json',
                               content_type='application/json')
        # Should still work as this endpoint doesn't require JSON body
        assert response.status_code == 200

class TestDashboardUtilities:
    """Test dashboard utility functions"""
    
    def setup_method(self):
        """Setup for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.orchestrator = AgentOrchestrator()
        self.orchestrator.db_path = self.temp_db.name
        self.orchestrator.setup_database()
        
        self.dashboard = AgentDashboard(self.orchestrator)
    
    def teardown_method(self):
        """Cleanup after each test"""
        Path(self.temp_db.name).unlink(missing_ok=True)
    
    def test_format_timestamp(self):
        """Test timestamp formatting"""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        formatted = self.dashboard.format_timestamp(timestamp)
        assert "2023-01-01" in formatted
        assert "12:00:00" in formatted
    
    def test_calculate_success_rate(self):
        """Test success rate calculation"""
        actions = [
            {'result': 'success'},
            {'result': 'success'},
            {'result': 'error'},
            {'result': 'warning'}
        ]
        
        success_rate = self.dashboard.calculate_success_rate(actions)
        assert success_rate == 50.0  # 2 success out of 4
    
    def test_calculate_success_rate_empty(self):
        """Test success rate calculation with empty actions"""
        success_rate = self.dashboard.calculate_success_rate([])
        assert success_rate == 0.0
    
    def test_get_recent_actions_empty_db(self):
        """Test getting recent actions from empty database"""
        actions = self.dashboard.get_recent_actions(limit=10)
        assert len(actions) == 0
    
    def test_status_color_mapping(self):
        """Test status color mapping"""
        assert self.dashboard.get_status_color('success') == 'success'
        assert self.dashboard.get_status_color('error') == 'danger'
        assert self.dashboard.get_status_color('warning') == 'warning'
        assert self.dashboard.get_status_color('unknown') == 'secondary'

class TestDashboardIntegration:
    """Test dashboard integration with agent system"""
    
    def setup_method(self):
        """Setup for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.orchestrator = AgentOrchestrator()
        self.orchestrator.db_path = self.temp_db.name
        self.orchestrator.setup_database()
        
        self.dashboard = AgentDashboard(self.orchestrator)
        self.app = self.dashboard.app.test_client()
        self.app.testing = True
    
    def teardown_method(self):
        """Cleanup after each test"""
        Path(self.temp_db.name).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_dashboard_with_live_agents(self):
        """Test dashboard with live agent data"""
        # Register agents
        health_agent = WebsiteHealthAgent()
        security_agent = SecurityAgent()
        
        self.orchestrator.register_agent(health_agent)
        self.orchestrator.register_agent(security_agent)
        
        # Mock successful execution
        with pytest.mock.patch.object(health_agent, 'execute') as mock_execute:
            mock_execute.return_value = [
                AgentAction("health_monitor", "test", "Test action", 
                          datetime.now(), "success", {})
            ]
            
            # Run agent cycle
            await self.orchestrator.run_agent_cycle()
            
            # Check dashboard reflects the changes
            response = self.app.get('/api/status')
            data = json.loads(response.data)
            
            assert data['total_agents'] == 2
            
            # Check actions were recorded
            response = self.app.get('/api/actions')
            actions_data = json.loads(response.data)
            assert len(actions_data['actions']) > 0
    
    def test_dashboard_responsive_design(self):
        """Test dashboard responsive design elements"""
        response = self.app.get('/')
        assert response.status_code == 200
        
        html_content = response.data.decode()
        # Check for responsive CSS classes
        assert 'col-md-' in html_content
        assert 'col-lg-' in html_content
        assert 'responsive' in html_content or 'viewport' in html_content
    
    def test_dashboard_auto_refresh(self):
        """Test dashboard auto-refresh functionality"""
        response = self.app.get('/')
        assert response.status_code == 200
        
        html_content = response.data.decode()
        # Check for auto-refresh mechanism
        assert 'setInterval' in html_content or 'setTimeout' in html_content
    
    def test_dashboard_error_recovery(self):
        """Test dashboard error recovery"""
        # Simulate database connection error
        original_db_path = self.orchestrator.db_path
        self.orchestrator.db_path = "/nonexistent/path.db"
        
        # Should handle gracefully
        response = self.app.get('/api/status')
        
        # Restore original path
        self.orchestrator.db_path = original_db_path
        
        # Should recover after fixing the issue
        response = self.app.get('/api/status')
        assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 