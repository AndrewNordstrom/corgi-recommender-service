#!/usr/bin/env python3
"""
Quick validation script to test stress test fixes.
Runs a 2-minute baseline test to validate error rate fixes.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.comprehensive_stress_test import ComprehensiveStressTester

async def validate_fixes():
    """Run a quick validation test to ensure fixes work."""
    print("🔧 VALIDATION: Testing Stress Test Fixes")
    print("=" * 50)
    
    # Create tester in mock mode
    tester = ComprehensiveStressTester(
        base_url="http://localhost:5002",
        mock_mode=True
    )
    
    # Run 2-minute baseline test
    results = await tester.run_comprehensive_stress_test(
        duration_minutes=2,
        mode="baseline"
    )
    
    # Validate results
    overall_error_rate = results['overall_metrics']['overall_error_rate']
    assessment = results['performance_assessment']
    
    print(f"\n🎯 VALIDATION RESULTS:")
    print(f"   Error Rate: {overall_error_rate:.3%}")
    print(f"   Target: <0.5%")
    print(f"   Grade: {assessment['grade']}")
    print(f"   Meets SLA: {assessment['meets_sla']}")
    
    # Check success criteria
    success = True
    if overall_error_rate > 0.005:  # >0.5%
        print(f"   ❌ FAIL: Error rate {overall_error_rate:.3%} exceeds 0.5% target")
        success = False
    else:
        print(f"   ✅ PASS: Error rate {overall_error_rate:.3%} meets <0.5% target")
    
    if not assessment['meets_sla']:
        print(f"   ❌ FAIL: Does not meet SLA requirements")
        success = False
    else:
        print(f"   ✅ PASS: Meets SLA requirements")
    
    if assessment['grade'] not in ['EXCELLENT', 'GOOD']:
        print(f"   ❌ FAIL: Grade '{assessment['grade']}' below expectations")
        success = False
    else:
        print(f"   ✅ PASS: Grade '{assessment['grade']}' meets expectations")
    
    print(f"\n🏆 OVERALL: {'SUCCESS' if success else 'FAILED'}")
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(validate_fixes())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        sys.exit(1) 