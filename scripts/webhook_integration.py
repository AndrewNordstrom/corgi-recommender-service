#!/usr/bin/env python3
# Quality Gate Webhook Integration
# Sends notifications when quality gate conditions are met or violated

import json
import requests
from typing import Dict

def send_quality_gate_notification(metrics: Dict, webhook_url: str):
    """Send quality gate notification to webhook."""
    
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
