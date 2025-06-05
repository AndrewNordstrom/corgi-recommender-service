#!/usr/bin/env python3
"""
Proxy Diagnostics CLI

A diagnostic tool for checking and monitoring the Corgi Recommender proxy middleware.
Allows testing connectivity, response times, and recommendation injection.
"""

import argparse
import json
import sys
import time
import os
import requests
from urllib.parse import urlparse, urlunparse

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Corgi Proxy Diagnostics Tool")

    # Required arguments
    parser.add_argument(
        "--url",
        default="http://localhost:5000",
        help="URL of the Corgi Recommender service (default: http://localhost:5000)",
    )

    # Optional arguments
    parser.add_argument("--user-id", help="User ID to use for the request")
    parser.add_argument(
        "--instance",
        default="mastodon.social",
        help="Mastodon instance to target (default: mastodon.social)",
    )
    parser.add_argument(
        "--path",
        default="timelines/home",
        help="API path to request (default: timelines/home)",
    )
    parser.add_argument("--token", help="OAuth token to use for authentication")
    parser.add_argument(
        "--method", default="GET", help="HTTP method to use (default: GET)"
    )
    parser.add_argument(
        "--show-headers", action="store_true", help="Show request and response headers"
    )
    parser.add_argument(
        "--dump-response",
        action="store_true",
        help="Dump full response body (JSON formatted)",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    return parser.parse_args()


def make_request(args):
    """Make a request to the proxy and collect diagnostics."""

    # Build the target URL
    if args.path.startswith("/"):
        args.path = args.path[1:]

    url = f"{args.url}/api/v1/{args.path}"

    # Prepare headers
    headers = {
        "User-Agent": "Corgi-Proxy-Diagnostics/1.0",
    }

    # Add authentication if provided
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    # Add instance information
    headers["X-Mastodon-Instance"] = args.instance

    # Add user_id as a query parameter if provided and no token
    params = {}
    if args.user_id and not args.token:
        params["user_id"] = args.user_id

    # Start timer
    start_time = time.time()

    # Make the request
    try:
        response = requests.request(
            method=args.method, url=url, headers=headers, params=params, timeout=10
        )

        # Calculate elapsed time
        elapsed_time = time.time() - start_time

        return {
            "success": True,
            "url": url,
            "instance": args.instance,
            "status_code": response.status_code,
            "elapsed_time": elapsed_time,
            "headers": dict(response.headers),
            "response": (
                response.json()
                if response.headers.get("Content-Type", "").startswith(
                    "application/json"
                )
                else None
            ),
            "response_size": len(response.content),
            "error": None,
        }
    except requests.RequestException as e:
        elapsed_time = time.time() - start_time
        return {
            "success": False,
            "url": url,
            "instance": args.instance,
            "elapsed_time": elapsed_time,
            "error": str(e),
            "headers": {},
            "response": None,
            "response_size": 0,
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            "success": False,
            "url": url,
            "instance": args.instance,
            "elapsed_time": elapsed_time,
            "error": f"Unexpected error: {str(e)}",
            "headers": {},
            "response": None,
            "response_size": 0,
        }


def analyze_result(result):
    """Analyze the results for recommendation injection and other diagnostics."""

    # Check for recommendation injection
    recommendations_injected = 0
    if result["success"] and result["response"]:
        # Look for the special header
        if "X-Corgi-Recommendations" in result["headers"]:
            header_value = result["headers"]["X-Corgi-Recommendations"]
            if header_value.startswith("injected="):
                try:
                    recommendations_injected = int(header_value.split("=")[1])
                except (ValueError, IndexError):
                    pass

        # Count posts with is_recommendation flag
        if isinstance(result["response"], list):
            actual_recs = sum(
                1 for post in result["response"] if post.get("is_recommendation", False)
            )
            if actual_recs != recommendations_injected and actual_recs > 0:
                # Update if the header was missing or incorrect
                recommendations_injected = actual_recs

    # Check for auth headers
    auth_headers_present = any(
        h.lower() == "authorization" for h in result.get("headers", {}).keys()
    )

    return {
        "success": result["success"],
        "target_instance": result["instance"],
        "status_code": result.get("status_code"),
        "response_time": result["elapsed_time"],
        "response_size": result["response_size"],
        "recommendations_injected": recommendations_injected,
        "auth_headers_present": auth_headers_present,
        "error": result["error"],
    }


def format_output(analysis, result, args):
    """Format the output according to the chosen format."""

    if args.output == "json":
        output = {
            "diagnostics": analysis,
        }

        if args.show_headers:
            output["headers"] = result.get("headers", {})

        if args.dump_response:
            output["response"] = result.get("response")

        return json.dumps(output, indent=2)

    # Default text output
    lines = []
    lines.append("Corgi Proxy Diagnostics Results")
    lines.append("==============================")
    lines.append(f"Target URL: {result['url']}")
    lines.append(f"Target Instance: {analysis['target_instance']}")
    lines.append(f"Success: {analysis['success']}")

    if analysis["success"]:
        lines.append(f"Status Code: {analysis['status_code']}")
        lines.append(f"Response Time: {analysis['response_time']:.3f} seconds")
        lines.append(f"Response Size: {analysis['response_size']} bytes")
        lines.append(f"Auth Headers Present: {analysis['auth_headers_present']}")
        lines.append(
            f"Recommendations Injected: {analysis['recommendations_injected']}"
        )

        if args.show_headers:
            lines.append("\nResponse Headers:")
            for header, value in result.get("headers", {}).items():
                lines.append(f"  {header}: {value}")

        if args.dump_response and result.get("response"):
            lines.append("\nResponse Body:")
            lines.append(json.dumps(result["response"], indent=2))
    else:
        lines.append(f"Error: {analysis['error']}")

    return "\n".join(lines)


def main():
    """Main entry point for the diagnostic tool."""
    args = parse_args()

    print(f"Running proxy diagnostics against {args.url}...")

    result = make_request(args)
    analysis = analyze_result(result)

    print(format_output(analysis, result, args))

    # Return non-zero exit code on failure
    return 0 if analysis["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
