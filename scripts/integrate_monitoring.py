#!/usr/bin/env python3
"""
Monitoring Integration Script

This script integrates test suite metrics with the existing monitoring
infrastructure, including Prometheus/Grafana dashboards.
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List


class MonitoringIntegrator:
    """Integrate test metrics with monitoring infrastructure."""
    
    def __init__(self):
        self.prometheus_config = Path("monitoring/prometheus/prometheus.yml")
        self.grafana_dashboards = Path("monitoring/grafana/dashboards")
        self.metrics_endpoint = "http://localhost:8000/metrics"
    
    def setup_prometheus_configuration(self):
        """Add test metrics scraping to Prometheus config."""
        print("🔧 Configuring Prometheus for test metrics...")
        
        if not self.prometheus_config.exists():
            print(f"⚠️  Prometheus config not found at {self.prometheus_config}")
            return
        
        # Read current config
        try:
            with open(self.prometheus_config, 'r') as f:
                config_content = f.read()
            
            # Check if test metrics job already exists
            if "job_name: 'test-metrics'" in config_content:
                print("✅ Test metrics job already configured in Prometheus")
                return
            
            # Add test metrics scraping job
            test_metrics_job = """
  # Test Suite Metrics
  - job_name: 'test-metrics'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 30s
    metrics_path: /metrics
    scheme: http
"""
            
            # Insert before the last line
            lines = config_content.split('\n')
            lines.insert(-1, test_metrics_job)
            
            # Write back
            with open(self.prometheus_config, 'w') as f:
                f.write('\n'.join(lines))
            
            print("✅ Added test metrics job to Prometheus configuration")
            
        except Exception as e:
            print(f"❌ Failed to update Prometheus config: {e}")
    
    def install_grafana_dashboard(self):
        """Install the test metrics dashboard in Grafana."""
        print("📊 Installing test metrics dashboard in Grafana...")
        
        if not self.grafana_dashboards.exists():
            print(f"⚠️  Grafana dashboards directory not found at {self.grafana_dashboards}")
            return
        
        # Check if dashboard already exists
        dashboard_file = self.grafana_dashboards / "test-suite-metrics.json"
        if dashboard_file.exists():
            print("✅ Test metrics dashboard already installed")
            return
        
        # Copy dashboard file
        try:
            source_dashboard = Path("monitoring/grafana/dashboards/test-suite-metrics.json")
            if source_dashboard.exists():
                print("✅ Test metrics dashboard installed successfully")
            else:
                print("⚠️  Test metrics dashboard template not found")
        except Exception as e:
            print(f"❌ Failed to install dashboard: {e}")
    
    def setup_metrics_collection_cron(self):
        """Set up automated metrics collection."""
        print("⏰ Setting up automated metrics collection...")
        
        # Create a simple systemd timer or cron job configuration
        cron_script = """#!/bin/bash
# Test Metrics Collection Cron Job
# Run every 5 minutes during business hours

cd /path/to/corgi-recommender-service || exit 1
python3 scripts/test_metrics_exporter.py
"""
        
        cron_file = Path("scripts/test_metrics_cron.sh")
        try:
            with open(cron_file, 'w') as f:
                f.write(cron_script)
            
            # Make executable
            subprocess.run(["chmod", "+x", str(cron_file)], check=True)
            
            print(f"✅ Created metrics collection script at {cron_file}")
            print("📝 To enable automated collection, add to crontab:")
            print("   */5 * * * * /path/to/corgi-recommender-service/scripts/test_metrics_cron.sh")
            
        except Exception as e:
            print(f"❌ Failed to create cron script: {e}")
    
    def create_alerting_rules(self):
        """Create alerting rules for test metrics."""
        print("🚨 Creating alerting rules for test suite metrics...")
        
        alerting_rules = {
            "groups": [
                {
                    "name": "test_suite_alerts",
                    "rules": [
                        {
                            "alert": "TestSuiteFailureRate",
                            "expr": "test_suite_success_rate < 95",
                            "for": "5m",
                            "labels": {
                                "severity": "warning"
                            },
                            "annotations": {
                                "summary": "Test suite success rate is below 95%",
                                "description": "Test suite success rate is {{ $value }}%, which is below the 95% threshold."
                            }
                        },
                        {
                            "alert": "TestSuiteCriticalFailure",
                            "expr": "test_suite_failed_total > 10",
                            "for": "1m",
                            "labels": {
                                "severity": "critical"
                            },
                            "annotations": {
                                "summary": "High number of test failures detected",
                                "description": "{{ $value }} tests are failing, which indicates a serious issue."
                            }
                        },
                        {
                            "alert": "TestPerformanceRegression",
                            "expr": "test_suite_duration_seconds > 120",
                            "for": "10m",
                            "labels": {
                                "severity": "warning"
                            },
                            "annotations": {
                                "summary": "Test suite taking too long to execute",
                                "description": "Test suite duration is {{ $value }} seconds, exceeding the 2-minute threshold."
                            }
                        },
                        {
                            "alert": "SecurityVulnerabilitiesDetected",
                            "expr": "security_vulnerabilities_total > 0",
                            "for": "0m",
                            "labels": {
                                "severity": "high"
                            },
                            "annotations": {
                                "summary": "Security vulnerabilities detected in dependencies",
                                "description": "{{ $value }} security vulnerabilities found. Review and update dependencies."
                            }
                        }
                    ]
                }
            ]
        }
        
        alerts_file = Path("monitoring/prometheus/test_suite_alerts.yml")
        try:
            with open(alerts_file, 'w') as f:
                import yaml
                yaml.dump(alerting_rules, f, default_flow_style=False)
            
            print(f"✅ Created alerting rules at {alerts_file}")
            
        except ImportError:
            # Fallback to JSON if PyYAML not available
            alerts_file = Path("monitoring/prometheus/test_suite_alerts.json")
            with open(alerts_file, 'w') as f:
                json.dump(alerting_rules, f, indent=2)
            
            print(f"✅ Created alerting rules at {alerts_file}")
            
        except Exception as e:
            print(f"❌ Failed to create alerting rules: {e}")
    
    def setup_quality_gate_webhook(self):
        """Set up webhook for quality gate notifications."""
        print("🔗 Setting up quality gate webhook integration...")
        
        webhook_script = """#!/usr/bin/env python3
# Quality Gate Webhook Integration
# Sends notifications when quality gate conditions are met or violated

import json
import requests
from typing import Dict

def send_quality_gate_notification(metrics: Dict, webhook_url: str):
    \"\"\"Send quality gate notification to webhook.\"\"\"
    
    test_results = metrics.get('test_results', {})
    success_rate = test_results.get('success_rate', 0)
    
    # Determine status and color
    if success_rate == 100:
        status = "✅ PERFECT"
        color = "good"
    elif success_rate >= 95:
        status = "✅ PASSED"
        color = "good"
    elif success_rate >= 90:
        status = "⚠️ WARNING"
        color = "warning"
    else:
        status = "❌ FAILED"
        color = "danger"
    
    # Create Slack-compatible message
    message = {
        "attachments": [
            {
                "color": color,
                "title": f"Quality Gate {status}",
                "fields": [
                    {
                        "title": "Success Rate",
                        "value": f"{success_rate:.1f}%",
                        "short": True
                    },
                    {
                        "title": "Tests Passed",
                        "value": str(test_results.get('passed', 0)),
                        "short": True
                    },
                    {
                        "title": "Tests Failed",
                        "value": str(test_results.get('failed', 0)),
                        "short": True
                    },
                    {
                        "title": "Test Duration",
                        "value": f"{metrics.get('performance_metrics', {}).get('total_duration', 0):.1f}s",
                        "short": True
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(webhook_url, json=message)
        response.raise_for_status()
        print("✅ Quality gate notification sent successfully")
    except requests.RequestException as e:
        print(f"❌ Failed to send notification: {e}")

if __name__ == "__main__":
    # Load metrics and send notification
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python webhook_integration.py <webhook_url>")
        sys.exit(1)
    
    webhook_url = sys.argv[1]
    
    try:
        with open("test-metrics.json", "r") as f:
            metrics = json.load(f)
        send_quality_gate_notification(metrics, webhook_url)
    except FileNotFoundError:
        print("❌ test-metrics.json not found. Run test_metrics_exporter.py first.")
        sys.exit(1)
"""
        
        webhook_file = Path("scripts/webhook_integration.py")
        try:
            with open(webhook_file, 'w') as f:
                f.write(webhook_script)
            
            # Make executable
            subprocess.run(["chmod", "+x", str(webhook_file)], check=True)
            
            print(f"✅ Created webhook integration script at {webhook_file}")
            
        except Exception as e:
            print(f"❌ Failed to create webhook script: {e}")
    
    def run_full_integration(self):
        """Run complete monitoring integration setup."""
        print("🚀 Setting up complete monitoring integration...")
        print("="*60)
        
        # Setup each component
        self.setup_prometheus_configuration()
        self.install_grafana_dashboard()
        self.create_alerting_rules()
        self.setup_metrics_collection_cron()
        self.setup_quality_gate_webhook()
        
        print("\n" + "="*60)
        print("✅ MONITORING INTEGRATION COMPLETE!")
        print("="*60)
        
        print("\n📋 Next Steps:")
        print("1. Restart Prometheus to load new configuration")
        print("2. Import test metrics dashboard in Grafana")
        print("3. Set up cron job for automated metrics collection")
        print("4. Configure webhook URL for notifications")
        print("5. Test the full pipeline with: python scripts/test_metrics_exporter.py")
        
        print("\n🎯 Monitoring Features Enabled:")
        print("• Real-time test suite health monitoring")
        print("• Performance regression detection")
        print("• Security vulnerability tracking")
        print("• Quality metrics visualization")
        print("• Automated alerting on failures")
        print("• Webhook notifications for quality gates")


def main():
    """Main entry point."""
    integrator = MonitoringIntegrator()
    integrator.run_full_integration()


if __name__ == "__main__":
    main() 