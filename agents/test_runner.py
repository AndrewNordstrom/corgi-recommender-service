#!/usr/bin/env python3

import argparse
import json
import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Add the parent directory to the path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.browser_agent import BrowserAgent
from agents.user_profiles import (
    get_profile_by_name,
    list_available_profiles,
    get_time_of_day,
)
from agents.interaction_logger import InteractionLogger
from agents.feedback_module import FeedbackModule

# Import Phase 3 modules
try:
    from agents.token_tracker import TokenTracker

    TOKEN_TRACKING_AVAILABLE = True
except ImportError:
    TOKEN_TRACKING_AVAILABLE = False


def setup_logging() -> logging.Logger:
    """Set up logging for the test runner."""
    logger = logging.getLogger("agent_test_runner")
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run a synthetic agent test against the Corgi Recommender."
    )

    parser.add_argument(
        "--profile",
        type=str,
        help="User profile to simulate (e.g., tech_fan, news_skeptic, meme_lover, privacy_tester)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost:5000",
        help="Host URL for the Corgi Recommender service",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        help="Claude API key (defaults to ANTHROPIC_API_KEY environment variable)",
    )

    parser.add_argument(
        "--max-turns", type=int, default=10, help="Maximum number of interaction turns"
    )

    parser.add_argument(
        "--time-of-day",
        type=str,
        choices=["morning", "afternoon", "evening", "night", "auto"],
        default="auto",
        help="Time of day context for behavior adaptation (default: auto)",
    )

    parser.add_argument(
        "--goal",
        type=str,
        help="Custom test goal to override the default profile behavior",
    )

    parser.add_argument(
        "--privacy-level",
        type=str,
        choices=["full", "limited", "none"],
        help="Test with a specific privacy level",
    )

    parser.add_argument(
        "--submit-feedback",
        action="store_true",
        help="Submit feedback to the API rather than just logging locally",
    )

    parser.add_argument(
        "--output", type=str, help="Path to save the session output JSON"
    )

    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List available user profiles and exit",
    )

    parser.add_argument(
        "--analyze-feedback",
        action="store_true",
        help="Analyze recent feedback instead of running a test",
    )

    # Phase 3 arguments
    parser.add_argument(
        "--max-tokens", type=int, help="Maximum token usage limit (default: no limit)"
    )

    parser.add_argument(
        "--max-interactions",
        type=int,
        default=10,
        help="Maximum number of browser interactions (default: 10)",
    )

    parser.add_argument(
        "--tools-enabled",
        action="store_true",
        help="Enable browser tooling for interaction if the user profile supports it",
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Run in heuristic mode without using Claude API (faster, no API costs)",
    )

    parser.add_argument(
        "--show-usage",
        action="store_true",
        help="Display token usage statistics and exit",
    )

    # Network & browser options
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode with a mock browser (simulated UI)",
    )

    parser.add_argument(
        "--allowed-domains",
        type=str,
        help="Comma-separated list of allowed domains (e.g., 'localhost,example.com')",
    )

    parser.add_argument(
        "--disable-internet",
        action="store_true",
        help="Disable internet access for Claude (except allowed domains)",
    )

    parser.add_argument(
        "--simulation-mode",
        choices=["normal", "injection", "adversarial"],
        default="normal",
        help="Simulation mode for testing robustness (normal, injection, adversarial)",
    )

    # Reporting
    parser.add_argument(
        "--analyze-logs",
        action="store_true",
        help="Analyze logs across multiple runs and generate a report",
    )

    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs/agent_sessions",
        help="Directory containing logs to analyze",
    )

    parser.add_argument(
        "--webhook-url",
        type=str,
        help="Webhook URL to send notifications when tests complete",
    )

    return parser.parse_args()


def show_token_usage() -> None:
    """Show token usage statistics from log files."""
    logger = setup_logging()

    if not TOKEN_TRACKING_AVAILABLE:
        logger.error(
            "Token tracking module not available. Make sure token_tracker.py is properly installed."
        )
        sys.exit(1)

    # Create token tracker to access log files
    token_tracker = TokenTracker()

    # Look for token usage log files
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    token_logs = os.path.join(log_dir, "token_usage.log")

    if not os.path.exists(token_logs):
        logger.error(f"No token usage logs found at {token_logs}")
        sys.exit(1)

    # Parse log file to extract usage information
    total_tokens = 0
    total_cost = 0.0
    usage_by_model = {}
    session_count = 0

    try:
        with open(token_logs, "r") as f:
            for line in f:
                if "API request:" in line:
                    session_count += 1
                    parts = line.split(", ")
                    if len(parts) >= 4:
                        model = parts[0].split(": ")[-1]
                        in_tokens = int(parts[1].split("=")[-1])
                        out_tokens = int(parts[2].split("=")[-1])
                        cost = float(parts[3].split("$")[-1].split(",")[0])

                        total_tokens += in_tokens + out_tokens
                        total_cost += cost

                        if model not in usage_by_model:
                            usage_by_model[model] = {
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "cost": 0.0,
                                "requests": 0,
                            }

                        usage_by_model[model]["input_tokens"] += in_tokens
                        usage_by_model[model]["output_tokens"] += out_tokens
                        usage_by_model[model]["cost"] += cost
                        usage_by_model[model]["requests"] += 1
    except Exception as e:
        logger.error(f"Error parsing token usage logs: {str(e)}")
        sys.exit(1)

    # Print usage summary
    print("\n=== Token Usage Summary ===")
    print(f"Total API Requests: {session_count}")
    print(f"Total Tokens: {total_tokens}")
    print(f"Total Cost: ${total_cost:.6f}")

    print("\n=== Model Usage Breakdown ===")
    for model, stats in usage_by_model.items():
        print(f"Model: {model}")
        print(f"  Requests: {stats['requests']}")
        print(f"  Input Tokens: {stats['input_tokens']}")
        print(f"  Output Tokens: {stats['output_tokens']}")
        print(f"  Total Tokens: {stats['input_tokens'] + stats['output_tokens']}")
        print(f"  Cost: ${stats['cost']:.6f}")
        print()

    sys.exit(0)


def run_agent_test(args) -> Dict[str, Any]:
    """Run an agent test with the specified parameters.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary containing test results
    """
    logger = setup_logging()

    # Handle --list-profiles flag
    if args.list_profiles:
        profiles = list_available_profiles()
        print("Available user profiles:")
        for profile in profiles:
            print(f"  - {profile['name']}: {profile['description']}")
            print(f"    Preferred topics: {', '.join(profile['preferred_topics'])}")
            print(
                f"    Browser tooling: {'Required' if profile['use_browser'] else 'Not required'}"
            )
            print()
        sys.exit(0)

    # Handle --show-usage flag
    if args.show_usage:
        show_token_usage()
        # Function above will exit

    # Get user profile
    try:
        if not args.profile:
            logger.error(
                "Profile is required unless using --list-profiles or --show-usage flags"
            )
            sys.exit(1)

        profile = get_profile_by_name(args.profile)
        logger.info(f"Using profile: {profile.name} - {profile.description}")
        logger.info(f"User ID: {profile.user_id}")
        logger.info(f"Preferred topics: {', '.join(profile.preferred_topics)}")
        logger.info(
            f"Browser tooling: {'Required' if profile.use_browser else 'Not required'}"
        )
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Determine time of day
    if args.time_of_day == "auto":
        time_of_day = get_time_of_day()
        logger.info(f"Automatically determined time of day: {time_of_day}")
    else:
        time_of_day = args.time_of_day
        logger.info(f"Using specified time of day: {time_of_day}")

    # Construct test goal if privacy level specified
    test_goal = args.goal
    if args.privacy_level:
        if test_goal:
            test_goal = f"{test_goal} with privacy_level={args.privacy_level}"
        else:
            test_goal = (
                f"Test the Corgi Recommender with privacy_level={args.privacy_level}"
            )
        logger.info(f"Testing with privacy level: {args.privacy_level}")

    # Create interaction logger
    interaction_logger = InteractionLogger()

    # Create feedback module
    feedback_module = FeedbackModule(api_base_url=args.host)

    # Initialize token tracker if max_tokens specified
    token_tracker = None
    if args.max_tokens and TOKEN_TRACKING_AVAILABLE:
        token_tracker = TokenTracker(max_tokens=args.max_tokens)
        logger.info(f"Token usage limited to {args.max_tokens} tokens")

    # Create agent with Phase 3 features
    agent = BrowserAgent(
        api_key=args.api_key,
        base_url=args.host,
        logger=interaction_logger,
        feedback_module=feedback_module,
        max_tokens=args.max_tokens,
        max_interactions=args.max_interactions,
        token_tracker=token_tracker,
        tools_enabled=args.tools_enabled,
        no_llm=args.no_llm,
    )

    # Log agent configuration
    logger.info(f"Starting agent test for profile '{profile.name}' on {args.host}")
    logger.info(f"Mode: {'Heuristic (no-LLM)' if args.no_llm else 'Claude API'}")
    logger.info(f"Browser tools: {'Enabled' if args.tools_enabled else 'Disabled'}")
    logger.info(f"Max interactions: {args.max_interactions}")

    # Run the agent
    results = agent.run_interaction(
        goal=test_goal or "Test the Corgi Recommender",
        max_turns=args.max_turns,
        user_profile=profile,
        time_of_day=time_of_day,
        test_goal=test_goal,
    )

    # Save results if output path provided
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Saved results to {args.output}")

    return results


def analyze_feedback(args) -> Dict[str, Any]:
    """Analyze recent feedback instead of running a test.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary containing analysis results
    """
    logger = setup_logging()
    logger.info("Analyzing recent feedback...")

    # Create feedback module
    feedback_module = FeedbackModule(api_base_url=args.host)

    # Analyze feedback
    results = feedback_module.analyze_recent_feedback(limit=20)

    # Save results if output path provided
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Saved feedback analysis to {args.output}")

    return results


def print_agent_test_summary(results: Dict[str, Any]) -> None:
    """Print a summary of the agent test results.

    Args:
        results: Dictionary containing test results
    """
    print("\n=== Test Execution Summary ===")
    print(f"Session ID: {results.get('session_id', 'unknown')}")
    print(f"User Profile: {results.get('user_profile', 'unknown')}")
    print(f"Success: {results.get('success', False)}")
    print(f"Message: {results.get('message', '')}")
    print(f"Turns Used: {results.get('turns_used', 0)}/{results.get('max_turns', '?')}")
    print(
        f"Interactions Used: {results.get('interactions_used', 0)}/{results.get('max_interactions', '?')}"
    )

    # Print token usage if available
    if "token_usage" in results:
        usage = results["token_usage"]
        print("\n=== Token Usage ===")
        print(f"Total Tokens: {usage.get('total_tokens', 0)}")
        print(f"Input Tokens: {usage.get('total_input_tokens', 0)}")
        print(f"Output Tokens: {usage.get('total_output_tokens', 0)}")
        print(f"Requests: {usage.get('request_count', 0)}")
        print(f"Cost: ${usage.get('total_cost', 0.0):.6f}")

        # Show token limit if set
        if usage.get("token_limit"):
            percent = (usage.get("total_tokens", 0) / usage.get("token_limit", 1)) * 100
            print(
                f"Token Limit: {usage.get('total_tokens', 0)}/{usage.get('token_limit')} ({percent:.1f}%)"
            )

    # Get action counts by type
    if "logs" in results and "actions" in results["logs"]:
        action_types = {}
        privacy_actions = []
        feedback_actions = []

        for action in results["logs"]["actions"]:
            action_type = action.get("action_type", "unknown")
            action_types[action_type] = action_types.get(action_type, 0) + 1

            # Collect privacy-related actions
            if "privacy" in action_type:
                privacy_actions.append(action)

            # Collect feedback-related actions
            if action_type in ["tool_use", "tool_response"] and "details" in action:
                details = action["details"]
                if isinstance(details, dict) and "input" in details:
                    input_text = str(details.get("input", "")).lower()
                    if "rate" in input_text and "recommendation" in input_text:
                        feedback_actions.append(action)
                elif isinstance(details, dict) and "response" in details:
                    response = details.get("response", {})
                    if isinstance(response, dict) and "observation" in response:
                        observation = str(response.get("observation", "")).lower()
                        if "feedback" in observation or "said:" in observation:
                            feedback_actions.append(action)

        print("\n=== Action Summary ===")
        for action_type, count in sorted(
            action_types.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  - {action_type}: {count}")

        print("\n=== Privacy Changes ===")
        if privacy_actions:
            for action in privacy_actions:
                details = action.get("details", {})
                timestamp = action.get("timestamp", "").split("T")[0]

                if action["action_type"] == "privacy_before_change":
                    print(
                        f"  - Before change: {details.get('tracking_level', 'unknown')} ({timestamp})"
                    )
                elif action["action_type"] in [
                    "privacy_change_simulated",
                    "heuristic_privacy_change",
                ]:
                    print(
                        f"  - Changed from {details.get('old_level', 'unknown')} to {details.get('new_level', 'unknown')} ({timestamp})"
                    )
        else:
            print("  No privacy changes detected")

        print("\n=== Feedback Provided ===")
        if feedback_actions:
            for action in feedback_actions:
                if (
                    action["action_type"] == "tool_response"
                    or action["action_type"] == "heuristic_feedback"
                ):
                    if action["action_type"] == "tool_response":
                        response = action.get("details", {}).get("response", {})
                        if isinstance(response, dict) and "observation" in response:
                            observation = response.get("observation", "")
                            if (
                                "feedback" in observation.lower()
                                or "said:" in observation.lower()
                            ):
                                print(f"  - {observation}")
                    else:
                        # Handle heuristic feedback
                        details = action.get("details", {})
                        if "feedback" in details:
                            print(
                                f"  - [Heuristic] Post {details.get('post_id', 'unknown')}: {details.get('feedback', '')}"
                            )
        else:
            print("  No feedback provided")


def print_feedback_analysis_summary(results: Dict[str, Any]) -> None:
    """Print a summary of the feedback analysis results.

    Args:
        results: Dictionary containing analysis results
    """
    print("\n=== Feedback Analysis Summary ===")
    print(f"Total Feedback Analyzed: {results.get('total_feedback_analyzed', 0)}")
    print(f"Positive Feedback: {results.get('positive_feedback', 0)}")
    print(f"Negative Feedback: {results.get('negative_feedback', 0)}")
    print(f"Neutral Feedback: {results.get('neutral_feedback', 0)}")

    print("\n=== Topics Mentioned ===")
    topics = results.get("topics_mentioned", {})
    if topics:
        for topic, count in sorted(topics.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {topic}: {count}")
    else:
        print("  No topics detected")


def analyze_logs(args) -> Dict[str, Any]:
    """Analyze logs across multiple agent runs and generate a report.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary containing analysis results
    """
    logger = setup_logging()
    logger.info(f"Analyzing logs in {args.log_dir}...")

    # Find all log files
    log_dir = args.log_dir
    if not os.path.exists(log_dir):
        logger.error(f"Log directory {log_dir} not found")
        sys.exit(1)

    # Find all result files (JSON)
    result_files = []
    for root, _, files in os.walk(log_dir):
        for file in files:
            if file.endswith(".json") and "results" in file:
                result_files.append(os.path.join(root, file))

    if not result_files:
        logger.error(f"No result files found in {log_dir}")
        sys.exit(1)

    logger.info(f"Found {len(result_files)} result files")

    # Aggregate data
    runs_by_profile = {}
    total_runs = 0
    successful_runs = 0
    total_interactions = 0
    total_tokens = 0
    total_cost = 0.0

    for result_file in result_files:
        try:
            with open(result_file, "r") as f:
                run_data = json.load(f)

            profile = run_data.get("user_profile", "unknown")
            success = run_data.get("success", False)
            interactions = run_data.get("interactions_used", 0)

            # Initialize profile entry if not exists
            if profile not in runs_by_profile:
                runs_by_profile[profile] = {
                    "total_runs": 0,
                    "successful_runs": 0,
                    "total_interactions": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "avg_success_rate": 0.0,
                    "avg_interactions": 0.0,
                    "run_files": [],
                }

            # Update profile stats
            runs_by_profile[profile]["total_runs"] += 1
            if success:
                runs_by_profile[profile]["successful_runs"] += 1
            runs_by_profile[profile]["total_interactions"] += interactions
            runs_by_profile[profile]["run_files"].append(result_file)

            # Update token usage if available
            if "token_usage" in run_data:
                token_usage = run_data["token_usage"]
                token_count = token_usage.get("total_tokens", 0)
                cost = token_usage.get("total_cost", 0.0)

                total_tokens += token_count
                total_cost += cost

                runs_by_profile[profile]["total_tokens"] += token_count
                runs_by_profile[profile]["total_cost"] += cost

            # Update global stats
            total_runs += 1
            if success:
                successful_runs += 1
            total_interactions += interactions

        except Exception as e:
            logger.warning(f"Error processing {result_file}: {str(e)}")

    # Calculate averages
    for profile, stats in runs_by_profile.items():
        if stats["total_runs"] > 0:
            stats["avg_success_rate"] = (
                stats["successful_runs"] / stats["total_runs"]
            ) * 100
            stats["avg_interactions"] = (
                stats["total_interactions"] / stats["total_runs"]
            )

    # Prepare results
    results = {
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "success_rate": (successful_runs / total_runs * 100) if total_runs > 0 else 0,
        "total_interactions": total_interactions,
        "avg_interactions_per_run": (
            total_interactions / total_runs if total_runs > 0 else 0
        ),
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "profiles": runs_by_profile,
        "timestamp": datetime.now().isoformat(),
    }

    # Save results if output path provided
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Saved log analysis to {args.output}")

        # Generate a human-readable report as well
        report_path = os.path.join(os.path.dirname(args.output), "report.txt")
        with open(report_path, "w") as f:
            f.write("=== CORGI AGENT FRAMEWORK ANALYSIS REPORT ===\n\n")
            f.write(
                f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
            f.write(f"Total runs: {total_runs}\n")
            f.write(f"Success rate: {results['success_rate']:.1f}%\n")
            f.write(f"Total interactions: {total_interactions}\n")
            f.write(
                f"Average interactions per run: {results['avg_interactions_per_run']:.1f}\n"
            )
            if total_tokens > 0:
                f.write(f"Total tokens used: {total_tokens}\n")
                f.write(f"Total estimated cost: ${total_cost:.6f}\n")
            f.write("\n=== PROFILE BREAKDOWN ===\n\n")

            for profile, stats in sorted(
                runs_by_profile.items(), key=lambda x: x[1]["total_runs"], reverse=True
            ):
                f.write(f"Profile: {profile}\n")
                f.write(f"  Runs: {stats['total_runs']}\n")
                f.write(f"  Success rate: {stats['avg_success_rate']:.1f}%\n")
                f.write(f"  Avg interactions: {stats['avg_interactions']:.1f}\n")
                if stats.get("total_tokens", 0) > 0:
                    f.write(f"  Total tokens: {stats['total_tokens']}\n")
                    f.write(f"  Total cost: ${stats['total_cost']:.6f}\n")
                f.write("\n")

        logger.info(f"Saved human-readable report to {report_path}")

    # Send webhook notification if configured
    if args.webhook_url:
        try:
            import requests

            webhook_data = {
                "type": "agent_report",
                "summary": {
                    "total_runs": total_runs,
                    "success_rate": results["success_rate"],
                    "total_cost": total_cost,
                    "timestamp": results["timestamp"],
                },
            }
            response = requests.post(
                args.webhook_url,
                json=webhook_data,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                logger.info(f"Sent webhook notification successfully")
            else:
                logger.warning(
                    f"Webhook notification failed: {response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.warning(f"Error sending webhook notification: {str(e)}")

    return results


def print_log_analysis_summary(results: Dict[str, Any]) -> None:
    """Print a summary of the log analysis results.

    Args:
        results: Dictionary containing analysis results
    """
    print("\n=== Agent Framework Analysis Summary ===")
    print(f"Total Runs: {results.get('total_runs', 0)}")
    print(f"Success Rate: {results.get('success_rate', 0):.1f}%")
    print(f"Total Interactions: {results.get('total_interactions', 0)}")
    print(f"Avg Interactions/Run: {results.get('avg_interactions_per_run', 0):.1f}")

    if results.get("total_tokens", 0) > 0:
        print(f"Total Tokens: {results.get('total_tokens', 0)}")
        print(f"Total Cost: ${results.get('total_cost', 0.0):.6f}")

    print("\n=== Profile Breakdown ===")
    for profile, stats in sorted(
        results.get("profiles", {}).items(),
        key=lambda x: x[1]["total_runs"],
        reverse=True,
    ):
        print(f"Profile: {profile}")
        print(f"  Runs: {stats.get('total_runs', 0)}")
        print(f"  Success Rate: {stats.get('avg_success_rate', 0):.1f}%")
        print(f"  Avg Interactions: {stats.get('avg_interactions', 0):.1f}")
        if stats.get("total_tokens", 0) > 0:
            print(f"  Total Tokens: {stats.get('total_tokens', 0)}")
            print(f"  Total Cost: ${stats.get('total_cost', 0.0):.6f}")
        print()


def main():
    """Main entry point for the test runner."""
    args = parse_arguments()

    # Handle headless mode
    if args.headless:
        os.environ["HEADLESS_MODE"] = "true"

    # Handle network restrictions
    if args.disable_internet:
        os.environ["CLAUDE_DISABLE_INTERNET"] = "true"

    if args.allowed_domains:
        os.environ["CLAUDE_ALLOWED_DOMAINS"] = args.allowed_domains

    # Handle simulation mode
    if args.simulation_mode != "normal":
        os.environ["SIMULATION_MODE"] = args.simulation_mode

    # Process based on the command
    if args.analyze_logs:
        results = analyze_logs(args)
        print_log_analysis_summary(results)
    elif args.analyze_feedback:
        results = analyze_feedback(args)
        print_feedback_analysis_summary(results)
    else:
        results = run_agent_test(args)
        print_agent_test_summary(results)

        # Send webhook notification if configured
        if args.webhook_url:
            try:
                import requests

                webhook_data = {
                    "type": "agent_run",
                    "summary": {
                        "profile": results.get("user_profile", "unknown"),
                        "success": results.get("success", False),
                        "interactions": results.get("interactions_used", 0),
                        "timestamp": datetime.now().isoformat(),
                    },
                }
                requests.post(
                    args.webhook_url,
                    json=webhook_data,
                    headers={"Content-Type": "application/json"},
                )
            except Exception as e:
                print(f"Error sending webhook notification: {str(e)}")


if __name__ == "__main__":
    main()
