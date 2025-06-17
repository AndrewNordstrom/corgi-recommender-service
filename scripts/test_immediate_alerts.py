#!/usr/bin/env python3
"""
Immediate Alert Test

Tests the ultra-sensitive alert configuration that notifies on ANY API usage.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
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

class ImmediateAlertTest:
    """Test immediate alerts on any API usage"""
    
    def __init__(self):
        self.setup_logging()
        
        # Initialize systems
        self.cost_tracker = CostTracker()
        self.slack_notifier = SlackNotifier(
            webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
            channel="#corgi-alerts",
            verify_ssl=False  # Bypass SSL issues
        )
        self.manager_agent = ManagerAgent()
        
        # Set up ultra-sensitive budget
        self.setup_sensitive_budget()
        
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_sensitive_budget(self):
        """Set up ultra-sensitive budget that alerts on any usage"""
        budget = AgentBudget(
            agent_id="alert_test_agent",
            hourly_limit_usd=0.001,  # $0.001 - will trigger on any real usage
            daily_limit_usd=0.01,
            monthly_limit_usd=0.1,
            hourly_token_limit=100,  # 100 tokens - will trigger quickly
            daily_token_limit=1000,
            monthly_token_limit=10000,
            priority=1  # High priority for immediate alerts
        )
        self.cost_tracker.set_agent_budget(budget)
        self.logger.info("✅ Ultra-sensitive budget configured: $0.001/hour, 100 tokens/hour")
        
    async def simulate_api_usage(self):
        """Simulate API usage that will trigger alerts"""
        self.logger.info("🚨 Simulating API usage that should trigger alerts...")
        
        # Simulate a small API call that exceeds our tiny budget
        api_call = APICall(
            agent_id="alert_test_agent",
            timestamp=datetime.now(),
            model="claude-3-haiku",
            input_tokens=50,
            output_tokens=75,
            total_tokens=125,  # Exceeds our 100 token limit
            cost_usd=0.002,    # Exceeds our $0.001 limit
            duration_ms=1200,
            success=True
        )
        
        # Record the call
        self.cost_tracker.record_api_call(api_call)
        self.logger.info(f"📊 Recorded API call: {api_call.total_tokens} tokens, ${api_call.cost_usd:.6f}")
        
        # Check if budget limits are exceeded
        budget_check = self.cost_tracker.check_budget_limits("alert_test_agent")
        self.logger.info(f"💰 Budget check: {budget_check}")
        
        if not budget_check["allowed"]:
            self.logger.info("🚨 BUDGET EXCEEDED - Sending alert!")
            
            # Send budget limit alert
            await self.slack_notifier.send_budget_limit_alert(
                agent_id="alert_test_agent",
                limit_type=budget_check["reason"],
                current=budget_check["current"],
                limit=budget_check["limit"]
            )
            
        # Send a general usage notification
        await self.slack_notifier.send_alert({
            'severity': 'info',
            'title': 'API Usage Detected',
            'message': f'Agent `alert_test_agent` made an API call: {api_call.total_tokens} tokens, ${api_call.cost_usd:.6f}',
            'agent_id': 'alert_test_agent',
            'cost_impact': api_call.cost_usd,
            'timestamp': datetime.now(),
            'metadata': {
                'model': api_call.model,
                'input_tokens': api_call.input_tokens,
                'output_tokens': api_call.output_tokens,
                'duration_ms': api_call.duration_ms
            }
        })
        
        return True
        
    async def test_cost_spike_alert(self):
        """Test cost spike detection with 0% threshold"""
        self.logger.info("📈 Testing cost spike alert...")
        
        # Record a baseline call
        baseline_call = APICall(
            agent_id="spike_test_agent",
            timestamp=datetime.now(),
            model="claude-3-haiku",
            input_tokens=10,
            output_tokens=10,
            total_tokens=20,
            cost_usd=0.0001,
            duration_ms=800,
            success=True
        )
        self.cost_tracker.record_api_call(baseline_call)
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Record a "spike" (any increase should trigger with 0% threshold)
        spike_call = APICall(
            agent_id="spike_test_agent",
            timestamp=datetime.now(),
            model="claude-3-haiku",
            input_tokens=15,  # Slightly more
            output_tokens=15,
            total_tokens=30,
            cost_usd=0.00015,  # Slightly more expensive
            duration_ms=900,
            success=True
        )
        self.cost_tracker.record_api_call(spike_call)
        
        # Send cost spike alert
        await self.slack_notifier.send_cost_spike_alert(
            agent_id="spike_test_agent",
            current_cost=0.00015,
            threshold=0.0001,
            period="immediate"
        )
        
        self.logger.info("📈 Cost spike alert sent!")
        
    async def run_test(self):
        """Run the immediate alert test"""
        self.logger.info("🚀 Starting Immediate Alert Test...")
        self.logger.info("=" * 60)
        
        # Test 1: Budget exceeded alert
        await self.simulate_api_usage()
        await asyncio.sleep(2)
        
        # Test 2: Cost spike alert
        await self.test_cost_spike_alert()
        await asyncio.sleep(2)
        
        # Test 3: Usage summary
        usage_stats = self.cost_tracker.get_usage_stats("alert_test_agent", "hour")
        await self.slack_notifier.send_hourly_summary([usage_stats])
        
        self.logger.info("=" * 60)
        self.logger.info("🎉 Immediate alert test completed!")
        self.logger.info("Check your #corgi-alerts Slack channel for notifications!")
        
        # Show final summary
        self.logger.info("\n📊 Final Usage Summary:")
        self.logger.info(f"   Agent: alert_test_agent")
        self.logger.info(f"   Total calls: {usage_stats.total_calls}")
        self.logger.info(f"   Total tokens: {usage_stats.total_tokens}")
        self.logger.info(f"   Total cost: ${usage_stats.total_cost_usd:.6f}")
        self.logger.info(f"   Budget status: {'❌ EXCEEDED' if usage_stats.total_cost_usd > 0.001 else '✅ Within limits'}")

async def main():
    """Main test runner"""
    try:
        tester = ImmediateAlertTest()
        await tester.run_test()
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 