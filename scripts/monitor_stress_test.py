#!/usr/bin/env python3
"""
Stress Test Monitoring Script

Monitors running stress tests and provides periodic status updates.
"""

import time
import json
import subprocess
import os
import glob
from datetime import datetime, timedelta
from pathlib import Path

def get_running_stress_tests():
    """Get list of running stress test processes"""
    try:
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True
        )
        
        processes = []
        for line in result.stdout.split('\n'):
            if 'comprehensive_stress_test.py' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) >= 11:
                    pid = parts[1]
                    cpu = parts[2]
                    mem = parts[3]
                    time_running = parts[9]
                    command = ' '.join(parts[10:])
                    processes.append({
                        'pid': pid,
                        'cpu': cpu,
                        'memory': mem,
                        'time': time_running,
                        'command': command
                    })
        return processes
    except Exception as e:
        print(f"Error getting processes: {e}")
        return []

def get_latest_results():
    """Get the most recent stress test results"""
    pattern = "logs/stress_test_results_*.json"
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # Get the most recent file
    latest_file = max(files, key=os.path.getctime)
    
    try:
        with open(latest_file, 'r') as f:
            data = json.load(f)
        return data, latest_file
    except Exception as e:
        print(f"Error reading {latest_file}: {e}")
        return None

def format_duration(seconds):
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def print_status_update():
    """Print current status of stress tests"""
    print("\n" + "="*80)
    print(f"🔍 STRESS TEST MONITORING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Check running processes
    processes = get_running_stress_tests()
    
    if processes:
        print(f"🚀 Running Stress Tests: {len(processes)} active")
        for i, proc in enumerate(processes, 1):
            # Extract test info from command
            if '--duration' in proc['command']:
                duration_idx = proc['command'].find('--duration') + len('--duration ')
                duration_part = proc['command'][duration_idx:].split()[0]
                duration_minutes = duration_part
            else:
                duration_minutes = "unknown"
            
            if '--mode' in proc['command']:
                mode_idx = proc['command'].find('--mode') + len('--mode ')
                mode = proc['command'][mode_idx:].split()[0]
            else:
                mode = "unknown"
            
            print(f"   Test {i}: PID {proc['pid']} | {duration_minutes}min {mode} mode | CPU: {proc['cpu']}% | Mem: {proc['memory']}% | Runtime: {proc['time']}")
    else:
        print("💤 No stress tests currently running")
    
    # Check latest results
    results_data = get_latest_results()
    if results_data:
        data, filename = results_data
        config = data.get('test_configuration', {})
        overall = data.get('overall_metrics', {})
        assessment = data.get('performance_assessment', {})
        
        print(f"\n📊 Latest Results: {os.path.basename(filename)}")
        print(f"   Mode: {config.get('mode', 'unknown')} | Duration: {config.get('duration_minutes', 'unknown')}min")
        print(f"   Total Requests: {overall.get('total_requests', 0):,}")
        print(f"   Success Rate: {(1 - overall.get('overall_error_rate', 0)):.1%}")
        print(f"   Throughput: {overall.get('overall_throughput_rps', 0):.1f} req/s")
        print(f"   Response Time: {overall.get('overall_avg_response_time', 0)*1000:.1f}ms avg, {overall.get('overall_p95_response_time', 0)*1000:.1f}ms P95")
        print(f"   Performance Grade: {assessment.get('grade', 'unknown')}")
        
        if assessment.get('issues_found'):
            print(f"   ⚠️  Issues: {', '.join(assessment['issues_found'])}")
    else:
        print("\n📊 No stress test results found yet")
    
    print("="*80)

def monitor_continuous(interval_minutes=5):
    """Monitor stress tests continuously"""
    print(f"🎯 Starting continuous monitoring (updates every {interval_minutes} minutes)")
    print("Press Ctrl+C to stop monitoring\n")
    
    try:
        while True:
            print_status_update()
            
            # Check if any tests are still running
            processes = get_running_stress_tests()
            if not processes:
                print("\n✅ All stress tests completed. Monitoring stopped.")
                break
            
            print(f"\n⏱️  Next update in {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor running stress tests")
    parser.add_argument("--continuous", "-c", action="store_true", help="Monitor continuously")
    parser.add_argument("--interval", "-i", type=int, default=5, help="Update interval in minutes (default: 5)")
    
    args = parser.parse_args()
    
    if args.continuous:
        monitor_continuous(args.interval)
    else:
        print_status_update() 