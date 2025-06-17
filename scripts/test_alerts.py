#!/usr/bin/env python3
"""
Test Alerts Script

Comprehensive testing of the Manager Agent alerting system.
Tests all notification types, Slack integration, and cost tracking.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, try to load manually
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.cost_tracker import CostTracker, AgentBudget, APICall
from agents.slack_notifier import SlackNotifier, SlackAlert
from agents.manager_agent import ManagerAgent

class AlertTester:
    """Comprehensive testing suite for the alerting system"""
    
    def __init__(self):
        self.setup_logging()
        self.cost_tracker = CostTracker()
        
        # Check for Slack webhook
        webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        if not webhook_url:
            self.logger.warning("SLACK_WEBHOOK_URL not set - using mock notifications")
            self.slack_notifier = None
        else:
            # Disable SSL verification for testing to avoid certificate issues
            self.slack_notifier = SlackNotifier(webhook_url, "#corgi-alerts-test", verify_ssl=False)
        
        self.test_results = []
    
    def setup_logging(self):
        """Setup logging for the test suite"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log a test result"""
        status = "✓ PASS" if success else "✗ FAIL"
        self.logger.info(f"{status}: {test_name} - {details}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    async def test_cost_tracker_basic(self):
        """Test basic cost tracker functionality"""
        test_name = "Cost Tracker Basic Operations"
        
        try:
            # Create test budget
            budget = AgentBudget(
                agent_id="test_agent_basic",
                hourly_limit_usd=1.0,
                daily_limit_usd=10.0,
                monthly_limit_usd=100.0,
                hourly_token_limit=10000,
                daily_token_limit=100000,
                monthly_token_limit=1000000,
                priority=3
            )
            
            self.cost_tracker.set_agent_budget(budget)
            
            # Record test API call
            call = APICall(
                agent_id="test_agent_basic",
                timestamp=datetime.now(),
                model="claude-3-sonnet",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=0.45,
                duration_ms=1500,
                success=True
            )
            
            self.cost_tracker.record_api_call(call)
            
            # Get usage stats
            stats = self.cost_tracker.get_usage_stats("test_agent_basic", "hour")
            
            # Verify
            assert stats.total_calls == 1
            assert stats.successful_calls == 1
            assert stats.total_cost_usd == 0.45
            
            self.log_test_result(test_name, True, f"Recorded call: ${stats.total_cost_usd}")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def test_budget_limits(self):
        """Test budget limit checking"""
        test_name = "Budget Limit Checking"
        
        try:
            # Create restrictive budget
            budget = AgentBudget(
                agent_id="test_agent_budget",
                hourly_limit_usd=0.1,  # Very low limit
                daily_limit_usd=1.0,
                monthly_limit_usd=10.0,
                hourly_token_limit=100,
                daily_token_limit=1000,
                monthly_token_limit=10000,
                priority=4
            )
            
            self.cost_tracker.set_agent_budget(budget)
            
            # Check budget before any calls
            check1 = self.cost_tracker.check_budget_limits("test_agent_budget")
            assert check1["allowed"] == True
            
            # Record expensive call
            expensive_call = APICall(
                agent_id="test_agent_budget",
                timestamp=datetime.now(),
                model="claude-3-sonnet",
                input_tokens=1000,
                output_tokens=500,
                total_tokens=1500,
                cost_usd=4.5,  # Exceeds budget
                duration_ms=2000,
                success=True
            )
            
            self.cost_tracker.record_api_call(expensive_call)
            
            # Check budget after expensive call
            check2 = self.cost_tracker.check_budget_limits("test_agent_budget")
            assert check2["allowed"] == False
            
            self.log_test_result(test_name, True, f"Budget limit triggered: {check2['reason']}")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        test_name = "Circuit Breaker Pattern"
        
        try:
            agent_id = "test_agent_circuit"
            
            # Record multiple failures
            for i in range(6):  # Exceed the failure threshold
                self.cost_tracker.record_failure(agent_id)
            
            # Check circuit breaker status
            check = self.cost_tracker.check_circuit_breaker(agent_id)
            assert check["allowed"] == False
            assert check["reason"] == "circuit_breaker_open"
            
            self.log_test_result(test_name, True, f"Circuit breaker opened after 6 failures")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def test_slack_connection(self):
        """Test Slack webhook connection"""
        test_name = "Slack Connection Test"
        
        if not self.slack_notifier:
            self.log_test_result(test_name, False, "No Slack webhook configured")
            return
        
        try:
            success = await self.slack_notifier.test_connection()
            self.log_test_result(test_name, success, "Slack webhook responded" if success else "Slack webhook failed")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def test_cost_spike_alert(self):
        """Test cost spike alert"""
        test_name = "Cost Spike Alert"
        
        if not self.slack_notifier:
            self.log_test_result(test_name, False, "No Slack webhook configured")
            return
        
        try:
            success = await self.slack_notifier.send_cost_spike_alert(
                agent_id="test_agent_spike",
                current_cost=5.50,
                threshold=4.00,
                period="hourly"
            )
            
            self.log_test_result(test_name, success, "Cost spike alert sent")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def test_circuit_breaker_alert(self):
        """Test circuit breaker alert"""
        test_name = "Circuit Breaker Alert"
        
        if not self.slack_notifier:
            self.log_test_result(test_name, False, "No Slack webhook configured")
            return
        
        try:
            success = await self.slack_notifier.send_circuit_breaker_alert(
                agent_id="test_agent_cb",
                failure_count=5,
                last_error="API rate limit exceeded"
            )
            
            self.log_test_result(test_name, success, "Circuit breaker alert sent")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def test_budget_limit_alert(self):
        """Test budget limit alert"""
        test_name = "Budget Limit Alert"
        
        if not self.slack_notifier:
            self.log_test_result(test_name, False, "No Slack webhook configured")
            return
        
        try:
            success = await self.slack_notifier.send_budget_limit_alert(
                agent_id="test_agent_budget_alert",
                limit_type="hourly_cost_limit",
                current=1.25,
                limit=1.00
            )
            
            self.log_test_result(test_name, success, "Budget limit alert sent")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def test_infinite_loop_alert(self):
        """Test infinite loop detection alert"""
        test_name = "Infinite Loop Alert"
        
        if not self.slack_notifier:
            self.log_test_result(test_name, False, "No Slack webhook configured")
            return
        
        try:
            success = await self.slack_notifier.send_infinite_loop_alert(
                agent_id="test_agent_loop",
                call_count=25,
                time_window=60
            )
            
            self.log_test_result(test_name, success, "Infinite loop alert sent")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def test_hourly_summary(self):
        """Test hourly summary report"""
        test_name = "Hourly Summary Report"
        
        if not self.slack_notifier:
            self.log_test_result(test_name, False, "No Slack webhook configured")
            return
        
        try:
            # Get actual usage stats
            usage_stats = self.cost_tracker.get_all_agents_usage('hour')
            
            success = await self.slack_notifier.send_hourly_summary(usage_stats)
            
            self.log_test_result(test_name, success, f"Summary sent for {len(usage_stats)} agents")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def test_daily_cost_report(self):
        """Test daily cost report"""
        test_name = "Daily Cost Report"
        
        if not self.slack_notifier:
            self.log_test_result(test_name, False, "No Slack webhook configured")
            return
        
        try:
            cost_summary = self.cost_tracker.get_cost_summary('day')
            optimization_suggestions = [
                "Consider using Claude Haiku for simple tasks",
                "Review high-cost agents for optimization opportunities"
            ]
            
            success = await self.slack_notifier.send_daily_cost_report(
                cost_summary, optimization_suggestions
            )
            
            self.log_test_result(test_name, success, f"Daily report sent: ${cost_summary['total_cost_usd']:.4f}")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def test_aggregated_issues(self):
        """Test aggregated issues report"""
        test_name = "Aggregated Issues Report"
        
        if not self.slack_notifier:
            self.log_test_result(test_name, False, "No Slack webhook configured")
            return
        
        try:
            # Create mock issues
            issues = [
                {
                    'type': 'cost_spike',
                    'agent_id': 'agent_1',
                    'severity': 'warning',
                    'message': 'Cost spike detected',
                    'error_type': 'budget_exceeded'
                },
                {
                    'type': 'cost_spike',
                    'agent_id': 'agent_2',
                    'severity': 'warning',
                    'message': 'Cost spike detected',
                    'error_type': 'budget_exceeded'
                },
                {
                    'type': 'circuit_breaker',
                    'agent_id': 'agent_3',
                    'severity': 'critical',
                    'message': 'Circuit breaker opened',
                    'error_type': 'api_failure'
                }
            ]
            
            success = await self.slack_notifier.send_aggregated_issues(issues)
            
            self.log_test_result(test_name, success, f"Aggregated report sent for {len(issues)} issues")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def test_manager_agent_integration(self):
        """Test Manager Agent integration"""
        test_name = "Manager Agent Integration"
        
        try:
            # Create manager instance
            manager = ManagerAgent()
            
            # Test dashboard data
            dashboard_data = await manager.get_dashboard_data()
            
            assert 'timestamp' in dashboard_data
            assert 'agent_count' in dashboard_data
            assert 'total_daily_cost' in dashboard_data
            
            self.log_test_result(test_name, True, f"Dashboard data: {len(dashboard_data)} fields")
            
        except Exception as e:
            self.log_test_result(test_name, False, str(e))
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        self.logger.info("Starting comprehensive alert system tests...")
        
        tests = [
            self.test_cost_tracker_basic,
            self.test_budget_limits,
            self.test_circuit_breaker,
            self.test_slack_connection,
            self.test_cost_spike_alert,
            self.test_circuit_breaker_alert,
            self.test_budget_limit_alert,
            self.test_infinite_loop_alert,
            self.test_hourly_summary,
            self.test_daily_cost_report,
            self.test_aggregated_issues,
            self.test_manager_agent_integration
        ]
        
        for test in tests:
            try:
                await test()
                # Small delay between tests to avoid rate limiting
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Test {test.__name__} failed with exception: {e}")
        
        # Print summary
        self.print_test_summary()
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("ALERT SYSTEM TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print("="*60)
        
        if failed_tests > 0:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ✗ {result['test']}: {result['details']}")
        
        print("\nDETAILED RESULTS:")
        for result in self.test_results:
            status = "✓" if result['success'] else "✗"
            print(f"  {status} {result['test']}: {result['details']}")
        
        # Save results to file
        results_file = Path("logs/alert_test_results.json")
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100
                },
                'results': self.test_results
            }, f, indent=2)
        
        print(f"\nDetailed results saved to: {results_file}")

async def main():
    """Main test runner"""
    print("Manager Agent Alert System Test Suite")
    print("=====================================")
    
    # Check environment
    if not os.getenv('SLACK_WEBHOOK_URL'):
        print("⚠️  SLACK_WEBHOOK_URL not set - Slack tests will be skipped")
        print("   Set SLACK_WEBHOOK_URL to test Slack integration")
    
    tester = AlertTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 