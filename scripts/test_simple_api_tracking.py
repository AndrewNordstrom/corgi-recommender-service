#!/usr/bin/env python3
"""
Simple API Tracking Test

Makes direct Anthropic API calls to test token and cost tracking accuracy
without the validation step that's causing issues.
"""

import json
import logging
import os
import sys
import time
import requests
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
    # Manual .env loading
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

from agents.token_tracker import TokenTracker
from agents.cost_tracker import CostTracker, APICall, AgentBudget

class SimpleAPITest:
    """Simple direct API test without validation"""
    
    def __init__(self):
        self.setup_logging()
        
        # Check for API key
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            self.logger.error("❌ ANTHROPIC_API_KEY not found in environment")
            sys.exit(1)
        
        self.logger.info(f"✅ Found API key: {self.api_key[:20]}...")
        
        # Initialize tracking systems
        self.token_tracker = TokenTracker(max_tokens=10000)
        self.cost_tracker = CostTracker()
        
        # API configuration
        self.base_url = "https://api.anthropic.com/v1"
        self.api_version = "2023-06-01"
        
        # Set up test budget
        self.setup_test_budget()
        
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_test_budget(self):
        """Set up test budget"""
        budget = AgentBudget(
            agent_id="simple_test_agent",
            hourly_limit_usd=5.0,
            daily_limit_usd=20.0,
            monthly_limit_usd=100.0,
            hourly_token_limit=50000,
            daily_token_limit=200000,
            monthly_token_limit=1000000,
            priority=2
        )
        self.cost_tracker.set_agent_budget(budget)
        self.logger.info("✅ Test budget configured")
        
    def make_api_call(self, message: str, model: str = "claude-3-haiku-20240307", max_tokens: int = 100):
        """Make direct API call to Anthropic"""
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": self.api_version,
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": max_tokens
        }
        
        self.logger.info(f"🔄 Making API call to {model}...")
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.base_url}/messages", 
                headers=headers, 
                json=payload
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code != 200:
                self.logger.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
            response_data = response.json()
            
            # Extract usage information
            usage = response_data.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            total_tokens = input_tokens + output_tokens
            
            # Get response text
            content = response_data.get('content', [])
            response_text = content[0].get('text', '') if content else ''
            
            self.logger.info(f"✅ API call successful:")
            self.logger.info(f"   Input tokens: {input_tokens}")
            self.logger.info(f"   Output tokens: {output_tokens}")
            self.logger.info(f"   Total tokens: {total_tokens}")
            self.logger.info(f"   Duration: {duration_ms}ms")
            self.logger.info(f"   Response preview: {response_text[:100]}...")
            
            # Track in token tracker
            self.token_tracker.record_usage(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                request_duration=(duration_ms / 1000)
            )
            
            # Calculate cost and track in cost tracker
            cost = self.cost_tracker.calculate_cost(
                model.replace('claude-3-', 'claude-3-').replace('-20240307', '').replace('-20240229', ''),
                input_tokens, 
                output_tokens
            )
            
            api_call = APICall(
                agent_id="simple_test_agent",
                timestamp=datetime.now(),
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                duration_ms=duration_ms,
                success=True
            )
            self.cost_tracker.record_api_call(api_call)
            
            self.logger.info(f"   Calculated cost: ${cost:.6f}")
            
            return {
                'response_data': response_data,
                'usage': usage,
                'cost': cost,
                'duration_ms': duration_ms,
                'response_text': response_text
            }
            
        except Exception as e:
            self.logger.error(f"API call failed: {e}")
            return None
    
    def test_haiku_model(self):
        """Test Claude 3 Haiku"""
        self.logger.info("=" * 50)
        self.logger.info("Testing Claude 3 Haiku")
        self.logger.info("=" * 50)
        
        result = self.make_api_call(
            message="Hello! Please count from 1 to 5 and briefly explain what you're doing.",
            model="claude-3-haiku-20240307",
            max_tokens=100
        )
        
        return result is not None
    
    def test_sonnet_model(self):
        """Test Claude 3 Sonnet"""
        self.logger.info("=" * 50)
        self.logger.info("Testing Claude 3 Sonnet")
        self.logger.info("=" * 50)
        
        result = self.make_api_call(
            message="Write a short haiku about artificial intelligence.",
            model="claude-3-sonnet-20240229",
            max_tokens=150
        )
        
        return result is not None
    
    def show_tracking_summary(self):
        """Show final tracking summary"""
        self.logger.info("=" * 50)
        self.logger.info("TRACKING SUMMARY")
        self.logger.info("=" * 50)
        
        # Token tracker summary
        token_summary = self.token_tracker.get_usage_summary()
        self.logger.info("Token Tracker Results:")
        self.logger.info(f"   Total requests: {token_summary['request_count']}")
        self.logger.info(f"   Total tokens: {token_summary['total_tokens']}")
        self.logger.info(f"   Total cost: ${token_summary['total_cost']:.6f}")
        self.logger.info(f"   Models used: {list(token_summary['usage_by_model'].keys())}")
        
        for model, stats in token_summary['usage_by_model'].items():
            self.logger.info(f"   {model}: {stats['requests']} calls, ${stats['cost']:.6f}")
        
        # Cost tracker summary
        cost_summary = self.cost_tracker.get_cost_summary("hour")
        usage_stats = self.cost_tracker.get_usage_stats("simple_test_agent", "hour")
        
        self.logger.info("\nCost Tracker Results:")
        self.logger.info(f"   Total calls: {usage_stats.total_calls}")
        self.logger.info(f"   Successful calls: {usage_stats.successful_calls}")
        self.logger.info(f"   Total tokens: {usage_stats.total_tokens}")
        self.logger.info(f"   Total cost: ${usage_stats.total_cost_usd:.6f}")
        
        # Budget check
        budget_check = self.cost_tracker.check_budget_limits("simple_test_agent")
        self.logger.info(f"   Budget status: {'✅ Within limits' if budget_check['allowed'] else '❌ ' + budget_check['reason']}")
        
        # Save detailed results
        self.save_results(token_summary, cost_summary, usage_stats)
        
    def save_results(self, token_summary, cost_summary, usage_stats):
        """Save results to file"""
        results_file = Path("logs/simple_api_test_results.json")
        results_file.parent.mkdir(exist_ok=True)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'token_tracker_summary': token_summary,
            'cost_tracker_summary': cost_summary,
            'agent_usage_stats': {
                'agent_id': usage_stats.agent_id,
                'period': usage_stats.period,
                'total_calls': usage_stats.total_calls,
                'successful_calls': usage_stats.successful_calls,
                'failed_calls': usage_stats.failed_calls,
                'total_tokens': usage_stats.total_tokens,
                'total_cost_usd': usage_stats.total_cost_usd,
                'avg_response_time_ms': usage_stats.avg_response_time_ms
            }
        }
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"📊 Results saved to: {results_file}")
    
    def run_tests(self):
        """Run all tests"""
        self.logger.info("🚀 Starting Simple API Tracking Tests...")
        
        tests_passed = 0
        total_tests = 2
        
        # Test Haiku
        if self.test_haiku_model():
            tests_passed += 1
            
        time.sleep(1)  # Brief pause
        
        # Test Sonnet
        if self.test_sonnet_model():
            tests_passed += 1
        
        # Show summary
        self.show_tracking_summary()
        
        # Final results
        self.logger.info("=" * 50)
        self.logger.info(f"TESTS COMPLETED: {tests_passed}/{total_tests} passed")
        self.logger.info("=" * 50)
        
        return tests_passed == total_tests

def main():
    """Main test runner"""
    try:
        tester = SimpleAPITest()
        success = tester.run_tests()
        
        if success:
            print("\n🎉 All tests passed! Token and cost tracking is working correctly.")
        else:
            print("\n⚠️ Some tests failed. Check the logs above for details.")
            
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 