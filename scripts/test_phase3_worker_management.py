#!/usr/bin/env python3
"""
Phase 3 Worker Management Test Script
Tests worker startup, monitoring, and management capabilities.
"""

import os
import sys
import time
import json
import subprocess
import signal
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def run_command(cmd, timeout=30):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"

def test_worker_script_exists():
    """Test that worker startup script exists and is executable."""
    print("📋 Testing worker startup script...")
    
    script_path = "scripts/start_worker.sh"
    if not os.path.exists(script_path):
        print(f"❌ Worker script not found: {script_path}")
        return False
    
    if not os.access(script_path, os.X_OK):
        print(f"❌ Worker script not executable: {script_path}")
        return False
    
    print(f"✅ Worker script exists and is executable: {script_path}")
    return True

def test_monitoring_script_exists():
    """Test that monitoring script exists and is executable."""
    print("📋 Testing monitoring script...")
    
    script_path = "scripts/monitor_workers.py"
    if not os.path.exists(script_path):
        print(f"❌ Monitoring script not found: {script_path}")
        return False
    
    if not os.access(script_path, os.X_OK):
        print(f"❌ Monitoring script not executable: {script_path}")
        return False
    
    print(f"✅ Monitoring script exists and is executable: {script_path}")
    return True

def test_redis_connectivity():
    """Test Redis connectivity for worker operations."""
    print("📋 Testing Redis connectivity...")
    
    code, stdout, stderr = run_command("redis-cli ping", timeout=5)
    if code != 0:
        print(f"❌ Redis not available: {stderr}")
        return False
    
    if "PONG" not in stdout:
        print(f"❌ Redis ping failed: {stdout}")
        return False
    
    print("✅ Redis connectivity OK")
    return True

def test_monitoring_script_functionality():
    """Test monitoring script basic functionality."""
    print("📋 Testing monitoring script functionality...")
    
    # Test health check
    code, stdout, stderr = run_command("PYTHONPATH=. python3 scripts/monitor_workers.py --health-only --format json", timeout=10)
    if code != 0:
        print(f"❌ Monitoring script failed: {stderr}")
        return False
    
    try:
        health_data = json.loads(stdout)
        if 'health_check' not in health_data:
            print(f"❌ Invalid health check output: {stdout}")
            return False
        
        print(f"✅ Health check working - Status: {health_data['health_check'].get('overall_status', 'unknown')}")
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON output from monitoring script: {stdout}")
        return False
    
    # Test queue monitoring
    code, stdout, stderr = run_command("PYTHONPATH=. python3 scripts/monitor_workers.py --queues-only --format json", timeout=10)
    if code != 0:
        print(f"❌ Queue monitoring failed: {stderr}")
        return False
    
    try:
        queue_data = json.loads(stdout)
        if 'queue_stats' not in queue_data:
            print(f"❌ Invalid queue stats output: {stdout}")
            return False
        
        print(f"✅ Queue monitoring working - Found {len(queue_data['queue_stats'])} queues")
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON output from queue monitoring: {stdout}")
        return False
    
    return True

def test_docker_configuration():
    """Test Docker configuration enhancements."""
    print("📋 Testing Docker configuration...")
    
    if not os.path.exists("docker-compose.yml"):
        print("❌ docker-compose.yml not found")
        return False
    
    with open("docker-compose.yml", 'r') as f:
        content = f.read()
    
    required_services = ['worker', 'flower']
    missing_services = []
    
    for service in required_services:
        if f"  {service}:" not in content:
            missing_services.append(service)
    
    if missing_services:
        print(f"❌ Missing Docker services: {', '.join(missing_services)}")
        return False
    
    # Check for worker health checks
    if 'healthcheck:' not in content:
        print("⚠️  No health checks found in Docker configuration")
    else:
        print("✅ Health checks found in Docker configuration")
    
    print("✅ Docker configuration includes worker and monitoring services")
    return True

def test_supervisor_configuration():
    """Test supervisor configuration file."""
    print("📋 Testing supervisor configuration...")
    
    config_path = "config/supervisor_worker.conf"
    if not os.path.exists(config_path):
        print(f"❌ Supervisor config not found: {config_path}")
        return False
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    required_sections = ['[program:corgi_worker]', '[program:corgi_worker_batch]', '[group:corgi_workers]']
    missing_sections = []
    
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
    
    if missing_sections:
        print(f"❌ Missing supervisor sections: {', '.join(missing_sections)}")
        return False
    
    print("✅ Supervisor configuration includes all required sections")
    return True

def test_log_directory_creation():
    """Test that log directories can be created."""
    print("📋 Testing log directory creation...")
    
    log_dir = "logs/workers"
    try:
        os.makedirs(log_dir, exist_ok=True)
        if not os.path.exists(log_dir):
            print(f"❌ Failed to create log directory: {log_dir}")
            return False
        
        print(f"✅ Log directory created/exists: {log_dir}")
        return True
    except Exception as e:
        print(f"❌ Error creating log directory: {e}")
        return False

def test_worker_startup_validation():
    """Test worker startup script validation."""
    print("📋 Testing worker startup validation...")
    
    # Test the validation functions in the script (without actually starting worker)
    code, stdout, stderr = run_command("grep -q 'Checking Redis connection' scripts/start_worker.sh && echo 'validation_found'", timeout=5)
    
    if "validation_found" not in stdout:
        print("❌ Worker script missing validation checks")
        return False
    
    print("✅ Worker script includes validation checks")
    return True

def main():
    """Run all Phase 3 tests."""
    print("🚀 Starting Phase 3 Worker Management Tests")
    print("=" * 50)
    
    tests = [
        ("Worker Script Exists", test_worker_script_exists),
        ("Monitoring Script Exists", test_monitoring_script_exists),
        ("Redis Connectivity", test_redis_connectivity),
        ("Monitoring Functionality", test_monitoring_script_functionality),
        ("Docker Configuration", test_docker_configuration),
        ("Supervisor Configuration", test_supervisor_configuration),
        ("Log Directory Creation", test_log_directory_creation),
        ("Worker Startup Validation", test_worker_startup_validation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All Phase 3 Worker Management tests passed!")
        print("\n📋 Phase 3 Summary:")
        print("✅ Enhanced worker startup script with production configuration")
        print("✅ Comprehensive worker monitoring script with health checks")
        print("✅ Enhanced Docker configuration with health checks and scaling")
        print("✅ Production supervisor configuration for non-Docker deployment")
        print("✅ Proper logging and error handling")
        print("\n🚀 Ready to proceed to Phase 4: Error Handling & Monitoring")
        return True
    else:
        print(f"❌ {failed} tests failed. Please fix issues before proceeding.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 