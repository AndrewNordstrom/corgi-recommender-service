#!/usr/bin/env python3
"""
Debug script for Corgi Recommender Service metrics.
Enhanced version with detailed error handling and diagnostic logging.
"""

import requests
import time
import random
import json
import argparse
import sys
import traceback
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Debug Corgi metrics functionality")
    parser.add_argument(
        "--host", default="http://localhost:5002", help="Corgi service host URL"
    )
    parser.add_argument(
        "--metrics-port", default=9100, type=int, help="Metrics server port"
    )
    parser.add_argument(
        "--iterations", default=2, type=int, help="Number of test iterations"
    )
    parser.add_argument("--user-id", default="test_user", help="User ID for testing")
    parser.add_argument(
        "--verify-ssl", action="store_true", help="Verify SSL certificates"
    )

    # Suppress insecure request warnings
    import warnings
    from urllib3.exceptions import InsecureRequestWarning

    warnings.simplefilter("ignore", InsecureRequestWarning)
    args = parser.parse_args()

    base_url = args.host
    metrics_url = f"http://localhost:{args.metrics_port}/metrics"

    print(f"🧪 Testing Corgi metrics with {args.iterations} iterations")
    print(f"🔗 Corgi API URL: {base_url}")
    print(f"📊 Metrics URL: {metrics_url}")

    # First, test the basic health endpoint to verify API is responsive
    try:
        print("\n🔍 Testing basic API health...")
        health_url = f"{base_url}/api/v1/health"
        response = requests.get(health_url, timeout=5, verify=args.verify_ssl)
        print(f"  Health endpoint response: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✅ API health check passed: {response.json()}")
        else:
            print(f"  ❌ API health check failed: {response.text}")
            print("  ⚠️ API may not be running properly - investigate server logs")
    except Exception as e:
        print(f"  ❌ API health check error: {e}")
        print("  ⚠️ Cannot reach API server - verify it's running on the correct port")
        print("  ℹ️ If using HTTPS, make sure SSL certificates are properly configured")
        return

    # Test database connection if available
    try:
        print("\n🔍 Testing database connection...")
        db_check_url = f"{base_url}/api/v1/health/database"
        response = requests.get(db_check_url, timeout=5, verify=args.verify_ssl)
        print(f"  Database health response: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✅ Database connection check passed: {response.json()}")
        else:
            print(f"  ⚠️ Database connection check warning: {response.text}")
            print(
                "  ℹ️ This might cause issues with recommendations that need DB access"
            )
    except Exception as e:
        print(f"  ⚠️ Database connection check error: {e}")
        print("  ℹ️ Could not verify database connection - some features may not work")

    # Test metrics endpoint is available
    try:
        print("\n🔍 Checking if metrics endpoint is accessible...")
        metrics_response = requests.get(metrics_url, timeout=5)
        if metrics_response.status_code == 200:
            print(
                f"  ✅ Metrics endpoint is responding ({len(metrics_response.text)} bytes)"
            )
        else:
            print(f"  ❌ Metrics endpoint failed: {metrics_response.status_code}")
    except Exception as e:
        print(f"  ❌ Metrics endpoint error: {e}")
        print(
            "  ⚠️ Cannot reach metrics server - verify prometheus_client is configured correctly"
        )

    # Create a test user ID with timestamp to make it unique
    timestamp = int(time.time())
    user_id = f"{args.user_id}_{timestamp}"

    print(f"\n📱 Using test user: {user_id}")

    # Test each endpoint separately to isolate issues
    # 1. Test getting timeline without injection
    try:
        print("\n🔍 Testing timeline endpoint WITHOUT injection...")
        timeline_url = (
            f"{base_url}/api/v1/timelines/home?inject=false&user_id={user_id}"
        )

        response = requests.get(timeline_url, timeout=10, verify=args.verify_ssl)
        print(f"  Timeline non-injection response: {response.status_code}")

        if response.status_code == 200:
            timeline = response.json()
            print(f"  ✅ Got {len(timeline)} posts without injection")
        else:
            print(f"  ❌ Timeline without injection failed: {response.status_code}")
            if response.text:
                print(f"  Response: {response.text[:200]}...")
    except Exception as e:
        print(f"  ❌ Error getting timeline without injection: {e}")
        print(f"  {traceback.format_exc()}")

    # 2. Test each strategy individually
    strategies = ["uniform", "tag_match", "first_only", "after_n"]

    for strategy in strategies:
        try:
            print(f"\n🔍 Testing timeline with {strategy} strategy...")

            # Include verbose debug flag to get more info
            timeline_url = f"{base_url}/api/v1/timelines/home?limit=5&strategy={strategy}&user_id={user_id}&debug=true"

            # Use a session to maintain connection details
            with requests.Session() as session:
                # Disable SSL verification for self-signed certs
                session.verify = args.verify_ssl
                response = session.get(timeline_url, timeout=15)

                print(f"  Timeline response ({strategy}): {response.status_code}")

                if response.status_code == 200:
                    try:
                        timeline = response.json()

                        # Count injected posts
                        injected_count = sum(
                            1
                            for post in timeline
                            if isinstance(post, dict) and post.get("injected")
                        )
                        real_count = len(timeline) - injected_count

                        print(
                            f"  ✅ Got {len(timeline)} posts ({injected_count} injected, {real_count} real)"
                        )

                        # Check if posts have the correct structure
                        if timeline and len(timeline) > 0:
                            sample_post = timeline[0]
                            print(f"  Post ID: {sample_post.get('id')}")
                            print(
                                f"  Has 'injected' field: {'injected' in sample_post}"
                            )
                            print(
                                f"  Has 'injection_metadata': {'injection_metadata' in sample_post}"
                            )

                            # Test a simple interaction to see if that works
                            if "id" in sample_post:
                                post_id = sample_post["id"]
                                action_type = "favorite"
                                is_injected = sample_post.get("injected", False)

                                print(
                                    f"\n  🔍 Testing interaction with post {post_id}..."
                                )

                                interaction_url = f"{base_url}/api/v1/interactions"
                                interaction_data = {
                                    "user_id": user_id,
                                    "post_id": post_id,
                                    "action_type": action_type,
                                    "context": {
                                        "source": "debug_script",
                                        "injected": is_injected,
                                    },
                                }

                                int_response = session.post(
                                    interaction_url,
                                    json=interaction_data,
                                    timeout=10,
                                    verify=args.verify_ssl,
                                )

                                print(
                                    f"  Interaction response: {int_response.status_code}"
                                )
                                if int_response.status_code == 200:
                                    print(f"  ✅ Interaction logged successfully")
                                else:
                                    print(
                                        f"  ❌ Failed to log interaction: {int_response.status_code}"
                                    )
                                    print(f"  Response: {int_response.text[:200]}...")
                    except json.JSONDecodeError:
                        print(f"  ❌ Invalid JSON response: {response.text[:200]}...")
                else:
                    print(f"  ❌ Timeline request failed: {response.status_code}")
                    if response.text:
                        print(f"  Response: {response.text[:200]}...")
        except Exception as e:
            print(f"  ❌ Error testing {strategy} strategy: {e}")
            print(f"  {traceback.format_exc()}")

    # Force a Prometheus metrics flush to ensure all metrics are sent
    try:
        print("\n🔄 Attempting to force flush metrics...")

        # 1. First try calling our custom endpoint
        try:
            flush_url = f"{base_url}/api/v1/metrics/flush"
            response = requests.post(flush_url, timeout=3, verify=args.verify_ssl)
            if response.status_code == 200:
                print("  ✅ Successfully called metrics flush endpoint")
            else:
                print(f"  ⚠️ Metrics flush endpoint returned: {response.status_code}")
        except Exception:
            # If endpoint doesn't exist, try the alternative method
            flush_url = f"{base_url}/api/v1/health"
            response = requests.get(flush_url, timeout=3, verify=args.verify_ssl)
            if response.status_code == 200:
                print(
                    "  ✅ Made request to trigger metrics collection via health endpoint"
                )
            else:
                print(
                    f"  ⚠️ Failed to trigger metrics collection: {response.status_code}"
                )

        # Brief pause to allow metrics processing
        time.sleep(1)

        # 2. Try to directly access metrics file as a backup
        try:
            import os

            metrics_file = "/tmp/corgi_metrics.prom"
            if os.path.exists(metrics_file):
                file_size = os.path.getsize(metrics_file)
                print(f"  ✅ Found metrics file: {metrics_file} ({file_size} bytes)")

                # If file is small, check content
                if file_size < 5000:
                    with open(metrics_file, "r") as f:
                        content = f.read()
                        if "corgi_" in content:
                            print(f"  ✅ Metrics file contains corgi metrics")
                        else:
                            print(f"  ⚠️ Metrics file doesn't contain corgi metrics")
        except Exception as e:
            print(f"  ℹ️ Couldn't access metrics file: {e}")

    except Exception as e:
        print(f"  ⚠️ Error triggering metrics flush: {e}")

    # 3. Final check of metrics after all tests
    try:
        print("\n📊 Checking metrics after tests...")
        metrics_response = requests.get(metrics_url)

        if metrics_response.status_code == 200:
            metrics_text = metrics_response.text
            print("  ✅ Metrics endpoint still responding")
            print(f"  Metrics size: {len(metrics_text)} bytes")

            # Check for specific metrics
            key_metrics = [
                "corgi_injected_posts_total",
                "corgi_recommendations_total",
                "corgi_fallback_usage_total",
                "corgi_recommendation_interactions_total",
                "corgi_timeline_post_count",
            ]

            print("\n📈 Key metrics status:")
            metrics_found = False

            for metric in key_metrics:
                if metric in metrics_text:
                    metric_lines = [
                        line
                        for line in metrics_text.split("\n")
                        if line.startswith(metric) and "{" in line
                    ]
                    count = len(metric_lines)
                    if count > 0:
                        metrics_found = True
                        print(f"  ✅ {metric}: {count} entries found")
                        # Show first entry as example
                        if metric_lines:
                            print(f"    Example: {metric_lines[0]}")
                    else:
                        print(
                            f"  ⚠️ {metric}: Found in metrics definition but no data points"
                        )
                        # Check if there's a definition line without data
                        definition_lines = [
                            line
                            for line in metrics_text.split("\n")
                            if line.startswith(f"# HELP {metric}")
                        ]
                        if definition_lines:
                            print(f"    Definition: {definition_lines[0]}")
                else:
                    print(f"  ❌ {metric}: Not found in metrics output")

            # Show other metrics that are present
            if not metrics_found:
                print("\n  ℹ️ Other metrics that are present:")
                sample_metrics = []
                for line in metrics_text.split("\n"):
                    if line.startswith("corgi_") and "{" in line:
                        metric_name = line.split("{")[0]
                        if metric_name not in sample_metrics:
                            sample_metrics.append(metric_name)
                            if len(sample_metrics) <= 5:  # Show max 5 examples
                                print(f"    {line}")

            # Print all metrics for debugging
            print("\n  🔎 Dumping all metrics with 'corgi_' prefix:")
            for line in metrics_text.split("\n"):
                if line.startswith("corgi_"):
                    print(f"    {line}")

            # Check if no metrics were found at all
            if not any(line.startswith("corgi_") for line in metrics_text.split("\n")):
                print(
                    "\n  ⚠️ No metrics with 'corgi_' prefix found. This suggests a problem with metrics collection or export."
                )
                print("  💡 Recommendations:")
                print(
                    "     - Check that the Prometheus client is correctly initialized in app.py"
                )
                print(
                    "     - Verify metrics are being collected in the correct registry"
                )
                print(
                    "     - Make sure the metrics server is running on the expected port"
                )
        else:
            print(f"  ❌ Failed to get metrics: {metrics_response.status_code}")
    except Exception as e:
        print(f"  ❌ Error accessing metrics: {e}")
        print(f"  {traceback.format_exc()}")

    print("\n🏁 Diagnostics complete!")


if __name__ == "__main__":
    main()
