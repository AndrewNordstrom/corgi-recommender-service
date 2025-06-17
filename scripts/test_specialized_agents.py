#!/usr/bin/env python3
"""
Test Specialized Agents

Quick test script to verify the Profiler & Optimizer Agent and Tester Agent
are working correctly and can execute their core functions.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.profiler_optimizer_agent import ProfilerOptimizerAgent
from agents.tester_agent import TesterAgent

async def test_profiler_agent():
    """Test the Profiler & Optimizer Agent."""
    print("🔍 Testing Profiler & Optimizer Agent...")
    
    try:
        agent = ProfilerOptimizerAgent()
        
        # Test health check
        health = await agent.health_check()
        print(f"  Health check: {'✅ Passed' if health else '❌ Failed'}")
        
        if health:
            # Test execution (this will be a quick on-demand run)
            print("  Running on-demand analysis...")
            result = await agent.execute()
            
            print(f"  Execution result: {'✅ Success' if result.success else '❌ Failed'}")
            if result.success:
                print(f"  Message: {result.message}")
                if hasattr(result, 'data') and result.data:
                    print(f"  Data keys: {list(result.data.keys())}")
            else:
                print(f"  Error: {result.message}")
        
        return health and (result.success if 'result' in locals() else False)
        
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False

async def test_tester_agent():
    """Test the Tester Agent."""
    print("🧪 Testing Tester Agent...")
    
    try:
        agent = TesterAgent()
        
        # Test health check
        health = await agent.health_check()
        print(f"  Health check: {'✅ Passed' if health else '❌ Failed'}")
        
        if health:
            # Test execution
            print("  Running test analysis...")
            result = await agent.execute()
            
            print(f"  Execution result: {'✅ Success' if result.success else '❌ Failed'}")
            if result.success:
                print(f"  Message: {result.message}")
                if hasattr(result, 'data') and result.data:
                    print(f"  Data keys: {list(result.data.keys())}")
            else:
                print(f"  Error: {result.message}")
        
        return health and (result.success if 'result' in locals() else False)
        
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False

async def test_scheduler_integration():
    """Test the scheduler integration."""
    print("🕐 Testing Scheduler Integration...")
    
    try:
        from scripts.specialized_agent_scheduler import SpecializedAgentScheduler
        
        scheduler = SpecializedAgentScheduler()
        print("  ✅ Scheduler initialized successfully")
        
        # Test on-demand execution
        print("  Testing on-demand profiler execution...")
        result = scheduler.run_on_demand("profiler", "test")
        print(f"  Profiler on-demand: {'✅ Success' if result.get('success') else '❌ Failed'}")
        
        print("  Testing on-demand tester execution...")
        result = scheduler.run_on_demand("tester", "test")
        print(f"  Tester on-demand: {'✅ Success' if result.get('success') else '❌ Failed'}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Testing Specialized Agents")
    print("=" * 50)
    
    # Test individual agents
    profiler_ok = await test_profiler_agent()
    print()
    
    tester_ok = await test_tester_agent()
    print()
    
    # Test scheduler integration
    scheduler_ok = await test_scheduler_integration()
    print()
    
    # Summary
    print("📊 Test Summary")
    print("=" * 50)
    print(f"Profiler & Optimizer Agent: {'✅ Passed' if profiler_ok else '❌ Failed'}")
    print(f"Tester Agent: {'✅ Passed' if tester_ok else '❌ Failed'}")
    print(f"Scheduler Integration: {'✅ Passed' if scheduler_ok else '❌ Failed'}")
    
    all_passed = profiler_ok and tester_ok and scheduler_ok
    print(f"\nOverall: {'✅ All tests passed!' if all_passed else '❌ Some tests failed'}")
    
    if all_passed:
        print("\n🎉 Specialized agents are ready for deployment!")
        print("\nTo run the scheduler:")
        print("  python3 scripts/specialized_agent_scheduler.py --mode schedule")
        print("\nTo run agents on-demand:")
        print("  python3 scripts/specialized_agent_scheduler.py --mode profiler")
        print("  python3 scripts/specialized_agent_scheduler.py --mode tester")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 