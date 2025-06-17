#!/usr/bin/env python3
"""
Real API Tracking Test

Makes actual Anthropic API calls to test token and cost tracking accuracy.
Compares our tracking system against real API usage data.
"""

import asyncio
import json
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
    # Manual .env loading if python-dotenv not available
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

from agents.token_tracker import TokenTracker
from agents.claude_interface import ClaudeInterface
from agents.cost_tracker import CostTracker, APICall, AgentBudget

class RealAPITrackingTest:
    """Test real API calls against our tracking systems"""
    
    def __init__(self):
        self.setup_logging()
        
        # Check for API key
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            self.logger.error("❌ ANTHROPIC_API_KEY not found in environment")
            self.logger.info("Please add your API key to .env file:")
            self.logger.info("ANTHROPIC_API_KEY=sk-ant-api03-...")
            sys.exit(1)
        
        self.logger.info(f"✅ Found API key: {self.api_key[:20]}...")
        
        # Initialize tracking systems
        self.token_tracker = TokenTracker(max_tokens=10000)
        self.cost_tracker = CostTracker()
        self.claude_interface = ClaudeInterface(token_tracker=self.token_tracker)
        
        # Set up test budget
        self.setup_test_budget()
        
        self.test_results = []
        
    def setup_logging(self):
        """Setup logging for the test"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_test_budget(self):
        """Set up a test budget for the cost tracker"""
        budget = AgentBudget(
            agent_id="api_test_agent",
            hourly_limit_usd=5.0,
            daily_limit_usd=20.0,
            monthly_limit_usd=100.0,
            hourly_token_limit=50000,
            daily_token_limit=200000,
            monthly_token_limit=1000000,
            priority=2
        )
        self.cost_tracker.set_agent_budget(budget)
        self.logger.info("✅ Test budget configured: $5/hour, $20/day")
        
    def log_test_result(self, test_name: str, success: bool, details: dict):
        """Log a test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.logger.info(f"{status}: {test_name}")
        for key, value in details.items():
            self.logger.info(f"   {key}: {value}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
    async def test_haiku_call(self):
        """Test a call to Claude 3 Haiku (cheapest model)"""
        test_name = "Claude 3 Haiku API Call"
        
        try:
            # Get initial tracking state
            initial_summary = self.token_tracker.get_usage_summary()
            initial_cost = initial_summary['total_cost']
            initial_tokens = initial_summary['total_tokens']
            
            # Make API call
            self.logger.info("🔄 Making API call to Claude 3 Haiku...")
            response = self.claude_interface.send_message(
                message="Hello! Please count from 1 to 5 and explain what you're doing.",
                model="claude-3-haiku-20240307",
                max_tokens=100
            )
            
            # Check for errors
            if 'error' in response:
                self.log_test_result(test_name, False, {
                    'error': response['error'],
                    'status_code': response.get('status_code', 'unknown')
                })
                return
            
            # Get final tracking state
            final_summary = self.token_tracker.get_usage_summary()
            final_cost = final_summary['total_cost']
            final_tokens = final_summary['total_tokens']
            
            # Extract actual API usage from response
            api_usage = response.get('usage', {})
            api_input_tokens = api_usage.get('input_tokens', 0)
            api_output_tokens = api_usage.get('output_tokens', 0)
            api_total_tokens = api_input_tokens + api_output_tokens
            
            # Calculate expected cost using our pricing
            expected_cost = self.cost_tracker.calculate_cost(
                "claude-3-haiku", api_input_tokens, api_output_tokens
            )
            
            # Track the call in our cost tracker too
            api_call = APICall(
                agent_id="api_test_agent",
                timestamp=datetime.now(),
                model="claude-3-haiku",
                input_tokens=api_input_tokens,
                output_tokens=api_output_tokens,
                total_tokens=api_total_tokens,
                cost_usd=expected_cost,
                duration_ms=1000,  # Approximate
                success=True
            )
            self.cost_tracker.record_api_call(api_call)
            
            # Compare tracking accuracy
            token_delta = final_tokens - initial_tokens
            cost_delta = final_cost - initial_cost
            
            details = {
                'api_input_tokens': api_input_tokens,
                'api_output_tokens': api_output_tokens,
                'api_total_tokens': api_total_tokens,
                'tracked_token_delta': token_delta,
                'tracked_cost_delta': f"${cost_delta:.6f}",
                'expected_cost': f"${expected_cost:.6f}",
                'token_accuracy': f"{(token_delta / api_total_tokens * 100):.1f}%" if api_total_tokens > 0 else "N/A",
                'cost_accuracy': f"{(cost_delta / expected_cost * 100):.1f}%" if expected_cost > 0 else "N/A",
                'response_preview': response.get('content', [{}])[0].get('text', 'No text')[:100] + "..."
            }
            
            # Test passes if tracking is reasonably accurate
            token_accurate = abs(token_delta - api_total_tokens) <= 1
            cost_accurate = abs(cost_delta - expected_cost) < 0.001
            
            success = token_accurate and cost_accurate
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, {
                'exception': str(e),
                'type': type(e).__name__
            })
            
    async def test_sonnet_call(self):
        """Test a call to Claude 3 Sonnet (medium model)"""
        test_name = "Claude 3 Sonnet API Call"
        
        try:
            # Get initial state
            initial_summary = self.token_tracker.get_usage_summary()
            initial_cost = initial_summary['total_cost']
            initial_tokens = initial_summary['total_tokens']
            
            # Make API call with a longer prompt
            self.logger.info("🔄 Making API call to Claude 3 Sonnet...")
            response = self.claude_interface.send_message(
                message="""Please write a short poem about artificial intelligence and the future of technology. 
                Make it thoughtful and include themes about both the opportunities and challenges ahead.
                Keep it to about 4-6 lines.""",
                model="claude-3-sonnet-20240229",
                max_tokens=200
            )
            
            if 'error' in response:
                self.log_test_result(test_name, False, {
                    'error': response['error'],
                    'status_code': response.get('status_code', 'unknown')
                })
                return
            
            # Get final state
            final_summary = self.token_tracker.get_usage_summary()
            final_cost = final_summary['total_cost']
            final_tokens = final_summary['total_tokens']
            
            # Extract API usage
            api_usage = response.get('usage', {})
            api_input_tokens = api_usage.get('input_tokens', 0)
            api_output_tokens = api_usage.get('output_tokens', 0)
            api_total_tokens = api_input_tokens + api_output_tokens
            
            # Calculate expected cost
            expected_cost = self.cost_tracker.calculate_cost(
                "claude-3-sonnet", api_input_tokens, api_output_tokens
            )
            
            # Track in cost tracker
            api_call = APICall(
                agent_id="api_test_agent",
                timestamp=datetime.now(),
                model="claude-3-sonnet",
                input_tokens=api_input_tokens,
                output_tokens=api_output_tokens,
                total_tokens=api_total_tokens,
                cost_usd=expected_cost,
                duration_ms=1200,
                success=True
            )
            self.cost_tracker.record_api_call(api_call)
            
            # Compare accuracy
            token_delta = final_tokens - initial_tokens
            cost_delta = final_cost - initial_cost
            
            details = {
                'api_input_tokens': api_input_tokens,
                'api_output_tokens': api_output_tokens,
                'api_total_tokens': api_total_tokens,
                'tracked_token_delta': token_delta,
                'tracked_cost_delta': f"${cost_delta:.6f}",
                'expected_cost': f"${expected_cost:.6f}",
                'token_accuracy': f"{(token_delta / api_total_tokens * 100):.1f}%" if api_total_tokens > 0 else "N/A",
                'cost_accuracy': f"{(cost_delta / expected_cost * 100):.1f}%" if expected_cost > 0 else "N/A",
                'response_preview': response.get('content', [{}])[0].get('text', 'No text')[:150] + "..."
            }
            
            # Test accuracy
            token_accurate = abs(token_delta - api_total_tokens) <= 1
            cost_accurate = abs(cost_delta - expected_cost) < 0.001
            
            success = token_accurate and cost_accurate
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, {
                'exception': str(e),
                'type': type(e).__name__
            })
            
    async def test_budget_enforcement(self):
        """Test that budget limits are enforced"""
        test_name = "Budget Limit Enforcement"
        
        try:
            # Check current usage
            usage_stats = self.cost_tracker.get_usage_stats("api_test_agent", "hour")
            
            # Check budget limits
            budget_check = self.cost_tracker.check_budget_limits("api_test_agent", 0.50)
            
            details = {
                'current_hourly_cost': f"${usage_stats.total_cost_usd:.6f}",
                'current_hourly_tokens': usage_stats.total_tokens,
                'total_calls': usage_stats.total_calls,
                'successful_calls': usage_stats.successful_calls,
                'budget_allowed': budget_check['allowed'],
                'budget_reason': budget_check.get('reason', 'within_limits')
            }
            
            # Test passes if we can track usage and budget status
            success = usage_stats.total_calls > 0 and 'allowed' in budget_check
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, {
                'exception': str(e),
                'type': type(e).__name__
            })
            
    async def test_cost_summary(self):
        """Test cost summary generation"""
        test_name = "Cost Summary Generation"
        
        try:
            # Get comprehensive cost summary
            cost_summary = self.cost_tracker.get_cost_summary("hour")
            token_summary = self.token_tracker.get_usage_summary()
            
            details = {
                'cost_tracker_total_cost': f"${cost_summary['total_cost_usd']:.6f}",
                'cost_tracker_total_tokens': cost_summary['total_tokens'],
                'cost_tracker_total_calls': cost_summary['total_calls'],
                'cost_tracker_agent_count': cost_summary['agent_count'],
                'token_tracker_total_cost': f"${token_summary['total_cost']:.6f}",
                'token_tracker_total_tokens': token_summary['total_tokens'],
                'token_tracker_request_count': token_summary['request_count'],
                'models_tracked': list(token_summary['usage_by_model'].keys())
            }
            
            # Test passes if both systems show activity
            success = (cost_summary['total_calls'] > 0 and 
                      token_summary['request_count'] > 0 and
                      cost_summary['total_cost_usd'] > 0 and
                      token_summary['total_cost'] > 0)
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, {
                'exception': str(e),
                'type': type(e).__name__
            })
            
    async def run_all_tests(self):
        """Run all API tracking tests"""
        self.logger.info("🚀 Starting Real API Tracking Tests...")
        self.logger.info("=" * 60)
        
        # Run tests in sequence
        await self.test_haiku_call()
        await asyncio.sleep(1)  # Brief pause between calls
        
        await self.test_sonnet_call()
        await asyncio.sleep(1)
        
        await self.test_budget_enforcement()
        await self.test_cost_summary()
        
        # Print final summary
        self.print_test_summary()
        
        # Save detailed results
        self.save_results()
        
    def print_test_summary(self):
        """Print test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        self.logger.info("=" * 60)
        self.logger.info("REAL API TRACKING TEST SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Passed: {passed_tests}")
        self.logger.info(f"Failed: {failed_tests}")
        self.logger.info(f"Success Rate: {success_rate:.1f}%")
        self.logger.info("=" * 60)
        
        if failed_tests > 0:
            self.logger.info("FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    self.logger.info(f"  ❌ {result['test']}")
        
        # Show final usage summary
        final_token_summary = self.token_tracker.get_usage_summary()
        final_cost_summary = self.cost_tracker.get_cost_summary("hour")
        
        self.logger.info("")
        self.logger.info("FINAL USAGE SUMMARY:")
        self.logger.info(f"  Total API Calls: {final_token_summary['request_count']}")
        self.logger.info(f"  Total Tokens: {final_token_summary['total_tokens']}")
        self.logger.info(f"  Total Cost: ${final_token_summary['total_cost']:.6f}")
        self.logger.info(f"  Models Used: {list(final_token_summary['usage_by_model'].keys())}")
        
    def save_results(self):
        """Save test results to file"""
        results_file = Path("logs/real_api_test_results.json")
        results_file.parent.mkdir(exist_ok=True)
        
        # Combine all data
        full_results = {
            'test_results': self.test_results,
            'final_token_summary': self.token_tracker.get_usage_summary(),
            'final_cost_summary': self.cost_tracker.get_cost_summary("hour"),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(results_file, 'w') as f:
            json.dump(full_results, f, indent=2, default=str)
        
        self.logger.info(f"📊 Detailed results saved to: {results_file}")

async def main():
    """Main test runner"""
    try:
        tester = RealAPITrackingTest()
        await tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 