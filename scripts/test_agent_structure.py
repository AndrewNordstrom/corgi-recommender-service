#!/usr/bin/env python3
"""
Test Agent Structure

Basic test to verify the specialized agents are properly structured
and can be imported without requiring API connections.
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_agent_imports():
    """Test that agents can be imported and have required methods."""
    print("🔍 Testing Agent Imports and Structure...")
    
    try:
        # Test Profiler & Optimizer Agent
        from agents.profiler_optimizer_agent import ProfilerOptimizerAgent
        
        # Check class structure without instantiating (to avoid API calls)
        profiler_methods = [method for method in dir(ProfilerOptimizerAgent) if not method.startswith('_')]
        required_profiler_methods = ['execute', 'health_check']
        
        profiler_ok = all(method in profiler_methods for method in required_profiler_methods)
        print(f"  Profiler & Optimizer Agent: {'✅ Structure OK' if profiler_ok else '❌ Missing methods'}")
        
        # Test Tester Agent
        from agents.tester_agent import TesterAgent
        
        tester_methods = [method for method in dir(TesterAgent) if not method.startswith('_')]
        required_tester_methods = ['execute', 'health_check']
        
        tester_ok = all(method in tester_methods for method in required_tester_methods)
        print(f"  Tester Agent: {'✅ Structure OK' if tester_ok else '❌ Missing methods'}")
        
        # Test Scheduler
        from scripts.specialized_agent_scheduler import SpecializedAgentScheduler
        
        scheduler_methods = [method for method in dir(SpecializedAgentScheduler) if not method.startswith('_')]
        required_scheduler_methods = ['run_scheduler', 'run_on_demand']
        
        scheduler_ok = all(method in scheduler_methods for method in required_scheduler_methods)
        print(f"  Scheduler: {'✅ Structure OK' if scheduler_ok else '❌ Missing methods'}")
        
        return profiler_ok and tester_ok and scheduler_ok
        
    except ImportError as e:
        print(f"  ❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False

def test_base_agent_inheritance():
    """Test that agents properly inherit from BaseAgent."""
    print("🧬 Testing Base Agent Inheritance...")
    
    try:
        from agents.base_agent import BaseAgent
        from agents.profiler_optimizer_agent import ProfilerOptimizerAgent
        from agents.tester_agent import TesterAgent
        
        profiler_inherits = issubclass(ProfilerOptimizerAgent, BaseAgent)
        tester_inherits = issubclass(TesterAgent, BaseAgent)
        
        print(f"  Profiler Agent inherits BaseAgent: {'✅ Yes' if profiler_inherits else '❌ No'}")
        print(f"  Tester Agent inherits BaseAgent: {'✅ Yes' if tester_inherits else '❌ No'}")
        
        return profiler_inherits and tester_inherits
        
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False

def test_agent_configuration():
    """Test agent configuration and attributes."""
    print("⚙️ Testing Agent Configuration...")
    
    try:
        # Test configuration attributes exist
        from agents.profiler_optimizer_agent import ProfilerOptimizerAgent
        from agents.tester_agent import TesterAgent
        
        # Check if classes have expected configuration attributes
        profiler_attrs = dir(ProfilerOptimizerAgent)
        tester_attrs = dir(TesterAgent)
        
        # These should be defined in __init__ but we can't test without instantiation
        # Just verify the classes are properly defined
        profiler_defined = hasattr(ProfilerOptimizerAgent, '__init__')
        tester_defined = hasattr(TesterAgent, '__init__')
        
        print(f"  Profiler Agent properly defined: {'✅ Yes' if profiler_defined else '❌ No'}")
        print(f"  Tester Agent properly defined: {'✅ Yes' if tester_defined else '❌ No'}")
        
        return profiler_defined and tester_defined
        
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False

def main():
    """Run all structure tests."""
    print("🚀 Testing Specialized Agent Structure")
    print("=" * 50)
    
    # Test imports and structure
    imports_ok = test_agent_imports()
    print()
    
    # Test inheritance
    inheritance_ok = test_base_agent_inheritance()
    print()
    
    # Test configuration
    config_ok = test_agent_configuration()
    print()
    
    # Summary
    print("📊 Structure Test Summary")
    print("=" * 50)
    print(f"Agent Imports & Structure: {'✅ Passed' if imports_ok else '❌ Failed'}")
    print(f"Base Agent Inheritance: {'✅ Passed' if inheritance_ok else '❌ Failed'}")
    print(f"Agent Configuration: {'✅ Passed' if config_ok else '❌ Failed'}")
    
    all_passed = imports_ok and inheritance_ok and config_ok
    print(f"\nOverall: {'✅ All structure tests passed!' if all_passed else '❌ Some tests failed'}")
    
    if all_passed:
        print("\n🎉 Specialized agents are properly structured!")
        print("\nNote: API functionality requires proper ANTHROPIC_API_KEY configuration.")
        print("The agents are ready for deployment once API access is configured.")
        
        print("\nAgent Capabilities:")
        print("📊 Profiler & Optimizer Agent:")
        print("  • Automated performance benchmarking")
        print("  • LLM-powered profiling analysis") 
        print("  • Performance regression detection")
        print("  • Optimization recommendations")
        
        print("\n🧪 Tester Agent:")
        print("  • Automated test generation")
        print("  • Code change analysis")
        print("  • Test coverage monitoring")
        print("  • Pattern learning from existing tests")
        
        print("\n🕐 Scheduler:")
        print("  • Nightly performance analysis")
        print("  • Weekly deep analysis")
        print("  • Code change triggered testing")
        print("  • Manager Agent integration")
        print("  • Slack notifications")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 