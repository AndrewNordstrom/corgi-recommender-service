import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import threading


class TokenTracker:
    """Track token usage and costs for Claude API calls."""

    # Current Claude pricing (subject to change)
    PRICING = {
        # Claude 4 models
        "claude-sonnet-4-20250514": {
            "input": 3.0,
            "output": 15.0,
        },  # $3/$15 per million tokens
        # Claude 3 models
        "claude-3-opus-20240229": {
            "input": 15.0,
            "output": 75.0,
        },  # $15/$75 per million tokens
        "claude-3-sonnet-20240229": {
            "input": 3.0,
            "output": 15.0,
        },  # $3/$15 per million tokens
        "claude-3-haiku-20240307": {
            "input": 0.25,
            "output": 1.25,
        },  # $0.25/$1.25 per million tokens
        # Claude 2 models
        "claude-2.0": {"input": 8.0, "output": 24.0},  # $8/$24 per million tokens
        "claude-2.1": {"input": 8.0, "output": 24.0},  # $8/$24 per million tokens
        # Claude Instant models
        "claude-instant-1.2": {
            "input": 1.63,
            "output": 5.51,
        },  # $1.63/$5.51 per million tokens
        # Default fallback (use Opus pricing as a conservative estimate)
        "default": {"input": 15.0, "output": 75.0},  # $15/$75 per million tokens
    }

    def __init__(
        self, max_tokens: Optional[int] = None, log_file: Optional[str] = None
    ):
        """Initialize token tracker.

        Args:
            max_tokens: Optional maximum token limit (triggers warning when reached)
            log_file: Path to log file (defaults to logs/token_usage.log)
        """
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.request_count = 0
        self.start_time = time.time()
        self.max_tokens = max_tokens
        self.token_limit_reached = False

        # Set up logging
        self.log_file = log_file or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "logs", "token_usage.log"
        )
        self._setup_logging()

        # Dictionary to track usage by model
        self.usage_by_model = {}

        # Use a lock for thread safety
        self.lock = threading.Lock()

        # Log initial state
        self.logger.info(f"Token tracker initialized with max_tokens={max_tokens}")

    def _setup_logging(self) -> None:
        """Set up logging for token usage."""
        # Ensure the log directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # Set up logger
        self.logger = logging.getLogger("token_tracker")
        self.logger.setLevel(logging.INFO)

        # Remove any existing handlers to avoid duplicates
        if self.logger.handlers:
            for handler in self.logger.handlers:
                self.logger.removeHandler(handler)

        # Add file handler with weekly rotation
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Create a new file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost based on token usage and model pricing.

        Args:
            model: Claude model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Get pricing for the specified model, or use default if not found
        pricing = self.PRICING.get(model, self.PRICING["default"])

        # Calculate cost (price per million tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        request_duration: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Record token usage for a request.

        Args:
            model: Claude model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            request_duration: Optional duration of the request in seconds

        Returns:
            Dictionary with usage statistics
        """
        with self.lock:
            # Calculate cost
            cost = self._calculate_cost(model, input_tokens, output_tokens)

            # Update totals
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost += cost
            self.request_count += 1

            # Update model-specific tracking
            if model not in self.usage_by_model:
                self.usage_by_model[model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                    "requests": 0,
                }

            self.usage_by_model[model]["input_tokens"] += input_tokens
            self.usage_by_model[model]["output_tokens"] += output_tokens
            self.usage_by_model[model]["cost"] += cost
            self.usage_by_model[model]["requests"] += 1

            # Prepare usage stats
            usage_stats = {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": cost,
                "timestamp": datetime.now().isoformat(),
                "request_duration": request_duration,
            }

            # Log the usage
            self.logger.info(
                f"API request: {model}, in={input_tokens}, out={output_tokens}, "
                f"cost=${cost:.6f}, total=${self.total_cost:.6f}"
            )

            # Check if we've reached the token limit
            total_tokens = self.total_input_tokens + self.total_output_tokens
            if (
                self.max_tokens
                and total_tokens >= self.max_tokens
                and not self.token_limit_reached
            ):
                self.token_limit_reached = True
                self.logger.warning(
                    f"⚠️ TOKEN LIMIT REACHED: {total_tokens}/{self.max_tokens}"
                )
                # Also log a detailed summary
                self.log_summary()

            return usage_stats

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get a summary of token usage and costs.

        Returns:
            Dictionary with usage summary
        """
        with self.lock:
            total_tokens = self.total_input_tokens + self.total_output_tokens
            elapsed_time = time.time() - self.start_time

            return {
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_tokens": total_tokens,
                "total_cost": self.total_cost,
                "request_count": self.request_count,
                "elapsed_seconds": elapsed_time,
                "token_limit": self.max_tokens,
                "token_limit_reached": self.token_limit_reached,
                "usage_by_model": self.usage_by_model,
                "timestamp": datetime.now().isoformat(),
            }

    def log_summary(self) -> None:
        """Log a summary of token usage."""
        summary = self.get_usage_summary()

        self.logger.info("===== TOKEN USAGE SUMMARY =====")
        self.logger.info(f"Total input tokens: {summary['total_input_tokens']}")
        self.logger.info(f"Total output tokens: {summary['total_output_tokens']}")
        self.logger.info(f"Total tokens: {summary['total_tokens']}")
        self.logger.info(f"Total requests: {summary['request_count']}")
        self.logger.info(f"Total cost: ${summary['total_cost']:.6f}")

        if summary["token_limit"]:
            percent = (summary["total_tokens"] / summary["token_limit"]) * 100
            self.logger.info(
                f"Token limit: {summary['total_tokens']}/{summary['token_limit']} ({percent:.1f}%)"
            )

        self.logger.info("===== MODEL BREAKDOWN =====")
        for model, stats in summary["usage_by_model"].items():
            self.logger.info(
                f"{model}: {stats['requests']} requests, "
                f"in={stats['input_tokens']}, out={stats['output_tokens']}, "
                f"cost=${stats['cost']:.6f}"
            )

        self.logger.info(f"Elapsed time: {summary['elapsed_seconds']:.2f} seconds")
        self.logger.info("=============================")

    def save_usage_to_file(self, file_path: Optional[str] = None) -> str:
        """Save usage statistics to a JSON file.

        Args:
            file_path: Path to save the file (defaults to logs/token_usage_{timestamp}.json)

        Returns:
            Path to the saved file
        """
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(
                os.path.dirname(self.log_file), f"token_usage_{timestamp}.json"
            )

        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Get the summary and save it
        summary = self.get_usage_summary()
        with open(file_path, "w") as f:
            json.dump(summary, f, indent=2)

        self.logger.info(f"Saved token usage summary to {file_path}")
        return file_path

    def reset(self) -> None:
        """Reset all token usage statistics."""
        with self.lock:
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self.total_cost = 0.0
            self.request_count = 0
            self.start_time = time.time()
            self.token_limit_reached = False
            self.usage_by_model = {}

            self.logger.info("Token tracker reset")
