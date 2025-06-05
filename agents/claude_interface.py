import os
import json
import requests
import logging
import time
from typing import Dict, List, Any, Optional, Union
from dotenv import load_dotenv


class ClaudeInterface:
    """Interface for interacting with Claude API with usage monitoring and error handling."""

    def __init__(self, token_tracker=None):
        """Initialize the Claude API interface.

        Args:
            token_tracker: Optional TokenTracker for monitoring usage
        """
        # Load API key from environment
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No Claude API key found in environment variables. "
                "Please set ANTHROPIC_API_KEY or CLAUDE_API_KEY in your .env file."
            )

        # Set up logging
        self.logger = logging.getLogger("claude_interface")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # API configuration
        self.base_url = "https://api.anthropic.com/v1"
        self.api_version = "2023-06-01"  # Update as needed
        self.default_model = "claude-3-opus-20240229"  # Default model

        # Associate with token tracker if provided
        self.token_tracker = token_tracker

        # Validate API connection on startup
        if not self._validate_api_connection():
            raise ConnectionError(
                "Could not connect to Claude API. Please check your API key and internet connection."
            )

    def _validate_api_connection(self) -> bool:
        """Validate connection to Claude API.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Send a minimal ping message to verify API key and connection
            response = self.send_message(
                "Claude API ready",
                system="Respond with 'Ready' if you receive this message.",
                max_tokens=10,
            )

            # Check for successful response
            if "Ready" in response.get("content", []):
                self.logger.info("Claude API connection successful")
                return True
            else:
                self.logger.warning(
                    "Claude API connection validation failed: unexpected response"
                )
                return False

        except Exception as e:
            self.logger.error(f"Claude API connection validation failed: {str(e)}")
            return False

    def send_message(
        self,
        message: str,
        system: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send a message to Claude API.

        Args:
            message: The user message to send
            system: Optional system prompt
            messages: Optional list of previous messages (overrides message if provided)
            model: Claude model to use (defaults to claude-3-opus)
            max_tokens: Maximum tokens for the response
            temperature: Sampling temperature (0.0 to 1.0)
            tools: Optional list of tools to enable

        Returns:
            The API response
        """
        # Configure API headers
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": self.api_version,
        }

        # Configure the message payload
        if messages is None:
            # Start a new conversation
            messages = []
            if system:
                # If we have a system prompt, add it
                pass  # System prompt is handled in the payload directly, not in messages

            # Add the user message
            messages = [{"role": "user", "content": message}]

        # Prepare the payload
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add system prompt if provided
        if system:
            payload["system"] = system

        # Add tools if provided
        if tools:
            payload["tools"] = tools

        # Log the request (excluding API key)
        safe_payload = payload.copy()
        self.logger.debug(f"Sending request to Claude API: {json.dumps(safe_payload)}")

        # Record starting timestamp for metrics
        start_time = time.time()

        try:
            # Make the API request
            response = requests.post(
                f"{self.base_url}/messages", headers=headers, json=payload
            )

            # Record request duration
            request_duration = time.time() - start_time

            # Handle non-200 responses
            if response.status_code != 200:
                error_msg = (
                    f"Claude API error: {response.status_code} - {response.text}"
                )
                self.logger.error(error_msg)
                return {"error": error_msg, "status_code": response.status_code}

            # Parse and return the successful response
            response_data = response.json()

            # Track token usage if token tracker is available
            if self.token_tracker and "usage" in response_data:
                usage = response_data.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                self.token_tracker.record_usage(
                    model=payload["model"],
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    request_duration=request_duration,
                )

            return response_data

        except Exception as e:
            error_details = {"error": str(e), "type": type(e).__name__}
            self.logger.error(f"Claude API request failed: {error_details}")
            return error_details

    def process_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Process a conversation with tools enabled.

        Args:
            messages: List of message objects for the conversation
            tools: List of tool configurations to enable
            system: Optional system prompt
            model: Claude model to use (defaults to default_model)
            max_tokens: Maximum response tokens

        Returns:
            Claude's API response
        """
        # Configure API headers
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": self.api_version,
        }

        # Prepare the payload
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "tools": tools,
        }

        # Add system prompt if provided
        if system:
            payload["system"] = system

        # Log the request (excluding API key)
        safe_payload = payload.copy()
        self.logger.debug(
            f"Sending tool-enabled request to Claude API: {json.dumps(safe_payload)}"
        )

        # Record starting timestamp for metrics
        start_time = time.time()

        try:
            # Make the API request
            response = requests.post(
                f"{self.base_url}/messages", headers=headers, json=payload
            )

            # Record request duration
            request_duration = time.time() - start_time

            # Handle non-200 responses
            if response.status_code != 200:
                error_msg = (
                    f"Claude API error: {response.status_code} - {response.text}"
                )
                self.logger.error(error_msg)
                return {"error": error_msg, "status_code": response.status_code}

            # Parse the successful response
            response_data = response.json()

            # Track token usage if token tracker is available
            if self.token_tracker and "usage" in response_data:
                usage = response_data.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                self.token_tracker.record_usage(
                    model=payload["model"],
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    request_duration=request_duration,
                )

            return response_data

        except Exception as e:
            error_details = {"error": str(e), "type": type(e).__name__}
            self.logger.error(f"Claude API request failed: {error_details}")
            return error_details

    def get_response_text(self, response: Dict[str, Any]) -> str:
        """Extract text content from a Claude API response.

        Args:
            response: The Claude API response

        Returns:
            Extracted text content
        """
        # Check for error response
        if "error" in response:
            return f"Error: {response.get('error')}"

        # Handle different response formats
        if "content" in response:
            content = response["content"]
            if isinstance(content, list):
                # Content is a list of blocks
                text_parts = []
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "text"
                        and "text" in block
                    ):
                        text_parts.append(block["text"])
                return "".join(text_parts)
            elif isinstance(content, str):
                # Content is a simple string
                return content
            else:
                return f"Unexpected content format: {type(content)}"
        else:
            return f"No content found in response: {response}"
