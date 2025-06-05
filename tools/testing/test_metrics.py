#!/usr/bin/env python3
"""
Test script for Corgi Recommender Service metrics.

This script makes multiple API calls to test metrics collection and monitoring.
"""

import requests
import time
import random
import json
import argparse
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Test Corgi metrics functionality")
    parser.add_argument(
        "--host", default="http://localhost:5002", help="Corgi service host URL"
    )
    parser.add_argument(
        "--metrics-port", default=9100, type=int, help="Metrics server port"
    )
    parser.add_argument(
        "--iterations", default=10, type=int, help="Number of test iterations"
    )
    parser.add_argument("--user-id", default="test_user", help="User ID for testing")
    args = parser.parse_args()

    base_url = args.host
    metrics_url = f"http://localhost:{args.metrics_port}/metrics"

    print(f"🧪 Testing Corgi metrics with {args.iterations} iterations")
    print(f"🔗 Corgi API URL: {base_url}")
    print(f"📊 Metrics URL: {metrics_url}")

    # Test timeline API with different strategies
    strategies = ["uniform", "tag_match", "first_only", "after_n"]

    # Create a test user ID with timestamp to make it unique
    timestamp = int(time.time())
    user_id = f"{args.user_id}_{timestamp}"

    print(f"\n📱 Using test user: {user_id}")

    # Test metrics for each strategy
    for i in range(args.iterations):
        strategy = random.choice(strategies)

        # Test timeline injection
        print(f"\n🔄 Iteration {i+1}/{args.iterations} - Testing strategy: {strategy}")

        # Get timeline with injection
        timeline_url = f"{base_url}/api/v1/timelines/home?limit=20&strategy={strategy}&user_id={user_id}"
        try:
            print(f"  📥 Getting timeline with {strategy} strategy")
            response = requests.get(timeline_url)
            if response.status_code == 200:
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

                # Test interaction with a post (if any posts exist)
                if timeline and len(timeline) > 0:
                    post = random.choice(timeline)
                    post_id = post.get("id")

                    # Randomly choose interaction type
                    action_type = random.choice(
                        ["favorite", "reblog", "bookmark", "more_like_this"]
                    )

                    # Track if this is an injected post
                    is_injected = post.get("injected", False)

                    # Log interaction
                    interaction_url = f"{base_url}/api/v1/interactions"
                    interaction_data = {
                        "user_id": user_id,
                        "post_id": post_id,
                        "action_type": action_type,
                        "context": {"source": "test_script", "injected": is_injected},
                    }

                    print(
                        f"  👆 Logging {action_type} interaction with post {post_id} (injected: {is_injected})"
                    )
                    interaction_response = requests.post(
                        interaction_url, json=interaction_data
                    )

                    if interaction_response.status_code == 200:
                        print(f"  ✅ Interaction logged successfully")
                    else:
                        print(
                            f"  ❌ Failed to log interaction: {interaction_response.status_code}"
                        )
            else:
                print(f"  ❌ Failed to get timeline: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        # Short delay between iterations
        time.sleep(1)

    # Check metrics endpoint
    try:
        print("\n📊 Checking metrics endpoint")
        metrics_response = requests.get(metrics_url)

        if metrics_response.status_code == 200:
            print("  ✅ Metrics endpoint is working")

            # Show key metrics
            metrics_text = metrics_response.text

            print("\n📈 Relevant metrics:")
            for metric in [
                "corgi_injected_posts_total",
                "corgi_recommendations_total",
                "corgi_fallback_usage_total",
                "corgi_recommendation_interactions_total",
            ]:
                if metric in metrics_text:
                    # Get lines containing the metric
                    metric_lines = [
                        line
                        for line in metrics_text.split("\n")
                        if line.startswith(metric) and "{" in line
                    ]
                    for line in metric_lines:
                        print(f"  {line}")
        else:
            print(f"  ❌ Failed to get metrics: {metrics_response.status_code}")
    except Exception as e:
        print(f"  ❌ Error accessing metrics: {e}")

    print("\n🏁 Testing complete!")
    print("\nTo view the complete metrics:")
    print(f"  curl {metrics_url}")
    print("\nTo start the monitoring dashboard:")
    print("  docker compose -f docker-compose-monitoring.yml up -d")
    print("  open http://localhost:3000 (Grafana dashboard credentials: admin/corgi)")


if __name__ == "__main__":
    main()
