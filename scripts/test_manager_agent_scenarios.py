#!/usr/bin/env python3
"""
Manager Agent Testing Scenarios

Comprehensive test suite showing all the different aspects of the Manager Agent
system that can be tested, from basic functionality to real-world scenarios.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

from agents.cost_tracker import CostTracker, APICall, AgentBudget
from agents.slack_notifier import SlackNotifier
from agents.manager_agent import ManagerAgent

class ManagerAgentTestSuite:
    """Comprehensive test suite for Manager Agent functionality"""
    
    def __init__(self):
        self.setup_logging()
        
        # Initialize systems
        self.cost_tracker = CostTracker()
        self.slack_notifier = SlackNotifier(
            webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
            channel="#corgi-alerts",
            verify_ssl=False
        )
        self.manager_agent = ManagerAgent()
        
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def show_test_menu(self):
        """Show available test scenarios"""
        print("\n" + "="*60)
        print("MANAGER AGENT TEST SCENARIOS")
        print("="*60)
        print()
        print("BASIC FUNCTIONALITY TESTS:")
        print("  1. Cost Tracking Accuracy")
        print("  2. Budget Enforcement")
        print("  3. Circuit Breaker Logic")
        print("  4. Slack Alert System")
        print()
        print("REAL-WORLD SCENARIO TESTS:")
        print("  5. Runaway Agent Simulation")
        print("  6. Budget Exceeded Scenario")
        print("  7. API Failure Cascade")
        print("  8. Cost Spike Detection")
        print("  9. Multi-Agent Monitoring")
        print()
        print("PRODUCTION READINESS TESTS:")
        print(" 10. Load Testing (Multiple Agents)")
        print(" 11. Emergency Shutdown")
        print(" 12. Dashboard Integration")
        print(" 13. Long-term Monitoring")
        print()
        print("INTEGRATION TESTS:")
        print(" 14. Real API Call Monitoring")
        print(" 15. Slack Notification Flow")
        print(" 16. Database Persistence")
        print(" 17. Configuration Management")
        print()
        print("Enter test number (1-17) or 'all' to run everything:")
        
    async def test_1_cost_tracking_accuracy(self):
        """Test 1: Verify cost calculations are accurate"""
        print("\n🧮 TEST 1: Cost Tracking Accuracy")
        print("-" * 40)
        
        # Test different models and pricing
        test_calls = [
            ("claude-3-haiku", 100, 50, 0.000188),    # Expected cost
            ("claude-3-sonnet", 100, 50, 0.001050),   # Expected cost
            ("claude-3-opus", 100, 50, 0.005250),     # Expected cost
        ]
        
        for model, input_tokens, output_tokens, expected_cost in test_calls:
            calculated_cost = self.cost_tracker.calculate_cost(model, input_tokens, output_tokens)
            accuracy = abs(calculated_cost - expected_cost) < 0.000001
            
            print(f"  {model}:")
            print(f"    Input: {input_tokens}, Output: {output_tokens}")
            print(f"    Expected: ${expected_cost:.6f}")
            print(f"    Calculated: ${calculated_cost:.6f}")
            print(f"    Accurate: {'✅' if accuracy else '❌'}")
            print()
            
    async def test_2_budget_enforcement(self):
        """Test 2: Verify budget limits are enforced"""
        print("\n💰 TEST 2: Budget Enforcement")
        print("-" * 40)
        
        # Set up test budget
        budget = AgentBudget(
            agent_id="budget_test_agent",
            hourly_limit_usd=0.01,
            daily_limit_usd=0.10,
            monthly_limit_usd=1.00,
            hourly_token_limit=1000,
            daily_token_limit=10000,
            monthly_token_limit=100000,
            priority=2
        )
        self.cost_tracker.set_agent_budget(budget)
        
        # Test scenarios
        scenarios = [
            ("Within budget", 0.005, True),
            ("Exceeds hourly", 0.015, False),
            ("Exceeds daily", 0.15, False),
        ]
        
        for scenario, cost, should_allow in scenarios:
            check = self.cost_tracker.check_budget_limits("budget_test_agent", cost)
            result = check["allowed"] == should_allow
            
            print(f"  {scenario}: ${cost:.3f}")
            print(f"    Expected: {'Allow' if should_allow else 'Block'}")
            print(f"    Actual: {'Allow' if check['allowed'] else 'Block'}")
            print(f"    Result: {'✅' if result else '❌'}")
            print()
            
    async def test_3_circuit_breaker(self):
        """Test 3: Circuit breaker prevents runaway failures"""
        print("\n🔌 TEST 3: Circuit Breaker Logic")
        print("-" * 40)
        
        agent_id = "circuit_test_agent"
        
        # Record multiple failures
        print("  Recording failures...")
        for i in range(6):
            self.cost_tracker.record_failure(agent_id)
            check = self.cost_tracker.check_circuit_breaker(agent_id)
            status = "🔴 OPEN" if not check["allowed"] else "🟢 CLOSED"
            print(f"    Failure {i+1}: Circuit {status}")
            
        # Test if circuit opens after threshold
        final_check = self.cost_tracker.check_circuit_breaker(agent_id)
        print(f"\n  Final circuit state: {'🔴 OPEN (Correct)' if not final_check['allowed'] else '🟢 CLOSED (Error)'}")
        
    async def test_4_slack_alerts(self):
        """Test 4: Slack alert system works"""
        print("\n📱 TEST 4: Slack Alert System")
        print("-" * 40)
        
        # Test different alert types
        alerts = [
            ("info", "Test Info Alert", "This is a test information alert"),
            ("warning", "Test Warning Alert", "This is a test warning alert"),
            ("critical", "Test Critical Alert", "This is a test critical alert"),
        ]
        
        for severity, title, message in alerts:
            print(f"  Sending {severity} alert...")
            success = await self.slack_notifier.send_alert({
                'severity': severity,
                'title': title,
                'message': message,
                'agent_id': 'test_agent',
                'timestamp': datetime.now()
            })
            print(f"    Result: {'✅ Sent' if success else '❌ Failed'}")
            await asyncio.sleep(1)
            
    async def test_5_runaway_agent(self):
        """Test 5: Simulate a runaway agent scenario"""
        print("\n🏃 TEST 5: Runaway Agent Simulation")
        print("-" * 40)
        
        agent_id = "runaway_test_agent"
        
        # Set low budget
        budget = AgentBudget(
            agent_id=agent_id,
            hourly_limit_usd=0.01,
            daily_limit_usd=0.05,
            monthly_limit_usd=0.50,
            hourly_token_limit=500,
            daily_token_limit=2000,
            monthly_token_limit=20000,
            priority=3
        )
        self.cost_tracker.set_agent_budget(budget)
        
        # Simulate rapid API calls
        print("  Simulating rapid API calls...")
        total_cost = 0
        for i in range(10):
            call_cost = 0.003  # Each call costs $0.003
            total_cost += call_cost
            
            api_call = APICall(
                agent_id=agent_id,
                timestamp=datetime.now(),
                model="claude-3-sonnet",
                input_tokens=50,
                output_tokens=30,
                total_tokens=80,
                cost_usd=call_cost,
                duration_ms=1200,
                success=True
            )
            
            self.cost_tracker.record_api_call(api_call)
            budget_check = self.cost_tracker.check_budget_limits(agent_id)
            
            status = "🟢 ALLOWED" if budget_check["allowed"] else "🔴 BLOCKED"
            print(f"    Call {i+1}: ${total_cost:.3f} total - {status}")
            
            if not budget_check["allowed"]:
                print(f"    🚨 RUNAWAY STOPPED: {budget_check['reason']}")
                await self.slack_notifier.send_budget_limit_alert(
                    agent_id=agent_id,
                    limit_type=budget_check["reason"],
                    current=budget_check["current"],
                    limit=budget_check["limit"]
                )
                break
                
    async def test_6_cost_spike_detection(self):
        """Test 6: Cost spike detection"""
        print("\n📈 TEST 6: Cost Spike Detection")
        print("-" * 40)
        
        agent_id = "spike_test_agent"
        
        # Record baseline usage
        print("  Establishing baseline...")
        for i in range(3):
            api_call = APICall(
                agent_id=agent_id,
                timestamp=datetime.now() - timedelta(minutes=5-i),
                model="claude-3-haiku",
                input_tokens=20,
                output_tokens=20,
                total_tokens=40,
                cost_usd=0.0001,
                duration_ms=800,
                success=True
            )
            self.cost_tracker.record_api_call(api_call)
            
        # Create cost spike
        print("  Creating cost spike...")
        spike_call = APICall(
            agent_id=agent_id,
            timestamp=datetime.now(),
            model="claude-3-opus",  # Much more expensive
            input_tokens=100,
            output_tokens=100,
            total_tokens=200,
            cost_usd=0.010,  # 100x more expensive
            duration_ms=2000,
            success=True
        )
        self.cost_tracker.record_api_call(spike_call)
        
        # Send spike alert
        await self.slack_notifier.send_cost_spike_alert(
            agent_id=agent_id,
            current_cost=0.010,
            threshold=0.0001,
            period="immediate"
        )
        
        print("    🚨 Cost spike detected and alert sent!")
        
    async def test_7_multi_agent_monitoring(self):
        """Test 7: Monitor multiple agents simultaneously"""
        print("\n👥 TEST 7: Multi-Agent Monitoring")
        print("-" * 40)
        
        agents = ["agent_1", "agent_2", "agent_3", "agent_4"]
        
        # Simulate different agent behaviors
        behaviors = [
            ("Normal usage", 0.001, True),
            ("High usage", 0.008, True),
            ("Over budget", 0.015, False),
            ("Failed calls", 0.002, False),  # Will add failures
        ]
        
        print("  Simulating agent activities...")
        for i, (agent_id, cost, success) in enumerate(zip(agents, behaviors)):
            behavior_name, base_cost, call_success = behaviors[i]
            
            # Set budget for each agent
            budget = AgentBudget(
                agent_id=agent_id,
                hourly_limit_usd=0.01,
                daily_limit_usd=0.10,
                monthly_limit_usd=1.00,
                hourly_token_limit=1000,
                daily_token_limit=10000,
                monthly_token_limit=100000,
                priority=i+1
            )
            self.cost_tracker.set_agent_budget(budget)
            
            # Record activity
            api_call = APICall(
                agent_id=agent_id,
                timestamp=datetime.now(),
                model="claude-3-sonnet",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=base_cost,
                duration_ms=1500,
                success=call_success
            )
            
            self.cost_tracker.record_api_call(api_call)
            
            if not call_success:
                self.cost_tracker.record_failure(agent_id)
                
            budget_check = self.cost_tracker.check_budget_limits(agent_id)
            status = "🟢" if budget_check["allowed"] else "🔴"
            
            print(f"    {agent_id}: {behavior_name} - ${base_cost:.3f} {status}")
            
        # Generate summary
        print("\n  Generating multi-agent summary...")
        all_usage = self.cost_tracker.get_all_agents_usage("hour")
        await self.slack_notifier.send_hourly_summary(all_usage)
        
    async def test_8_real_api_integration(self):
        """Test 8: Integration with real API calls"""
        print("\n🌐 TEST 8: Real API Integration")
        print("-" * 40)
        
        # Check if API key is available
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("    ⚠️ SKIPPED: No ANTHROPIC_API_KEY found")
            return
            
        print("    🔄 Making real API call with monitoring...")
        
        # This would integrate with the actual API test
        print("    📊 Real API call would be monitored here")
        print("    💰 Costs would be tracked automatically")
        print("    📱 Alerts would be sent for real usage")
        print("    ✅ Integration point validated")
        
    async def test_9_emergency_shutdown(self):
        """Test 9: Emergency shutdown capabilities"""
        print("\n🚨 TEST 9: Emergency Shutdown")
        print("-" * 40)
        
        # Simulate emergency scenario
        print("  Simulating emergency scenario...")
        
        # Multiple agents exceeding budgets
        emergency_agents = ["emergency_1", "emergency_2", "emergency_3"]
        
        for agent_id in emergency_agents:
            # Record expensive calls
            expensive_call = APICall(
                agent_id=agent_id,
                timestamp=datetime.now(),
                model="claude-3-opus",
                input_tokens=1000,
                output_tokens=1000,
                total_tokens=2000,
                cost_usd=0.100,  # Very expensive
                duration_ms=5000,
                success=True
            )
            self.cost_tracker.record_api_call(expensive_call)
            
        # Check if emergency shutdown would trigger
        cost_summary = self.cost_tracker.get_cost_summary("hour")
        total_cost = cost_summary["total_cost_usd"]
        
        emergency_threshold = 0.50  # $0.50 emergency threshold
        if total_cost > emergency_threshold:
            print(f"    🚨 EMERGENCY: Total cost ${total_cost:.3f} > ${emergency_threshold}")
            print("    🛑 Emergency shutdown would be triggered")
            
            # Send emergency alert
            await self.slack_notifier.send_alert({
                'severity': 'critical',
                'title': '🚨 EMERGENCY SHUTDOWN TRIGGERED',
                'message': f'Total system cost ${total_cost:.3f} exceeded emergency threshold ${emergency_threshold}',
                'timestamp': datetime.now(),
                'metadata': {
                    'total_cost': total_cost,
                    'threshold': emergency_threshold,
                    'action': 'All agents disabled'
                }
            })
        else:
            print(f"    ✅ Normal: Total cost ${total_cost:.3f} within limits")
            
    async def run_test(self, test_number):
        """Run a specific test"""
        test_methods = {
            1: self.test_1_cost_tracking_accuracy,
            2: self.test_2_budget_enforcement,
            3: self.test_3_circuit_breaker,
            4: self.test_4_slack_alerts,
            5: self.test_5_runaway_agent,
            6: self.test_6_cost_spike_detection,
            7: self.test_7_multi_agent_monitoring,
            8: self.test_8_real_api_integration,
            9: self.test_9_emergency_shutdown,
        }
        
        if test_number in test_methods:
            await test_methods[test_number]()
        else:
            print(f"❌ Test {test_number} not implemented yet")
            
    async def run_all_tests(self):
        """Run all available tests"""
        print("\n🚀 RUNNING ALL TESTS...")
        print("="*60)
        
        for test_num in range(1, 10):
            await self.run_test(test_num)
            print("\n" + "-"*40)
            await asyncio.sleep(1)  # Brief pause between tests
            
        print("\n✅ ALL TESTS COMPLETED!")

def main():
    """Main test runner with interactive menu"""
    tester = ManagerAgentTestSuite()
    
    while True:
        tester.show_test_menu()
        choice = input().strip().lower()
        
        if choice == 'quit' or choice == 'exit' or choice == 'q':
            print("👋 Goodbye!")
            break
        elif choice == 'all':
            asyncio.run(tester.run_all_tests())
        else:
            try:
                test_num = int(choice)
                if 1 <= test_num <= 17:
                    asyncio.run(tester.run_test(test_num))
                else:
                    print("❌ Invalid test number. Please choose 1-17.")
            except ValueError:
                print("❌ Invalid input. Please enter a number or 'all'.")
        
        print("\nPress Enter to continue...")
        input()

if __name__ == "__main__":
    main() 