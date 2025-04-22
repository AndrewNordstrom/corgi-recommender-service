#!/bin/bash

# run-agent.sh - Script to run the Corgi Agent Framework with various options
# Usage: ./run-agent.sh profile=tech_fan headless=true limit_interactions=15

set -e

# Default values
PROFILE=""
MAX_TOKENS=""
MAX_INTERACTIONS="10"
TOOLS_ENABLED="false"
NO_LLM="false"
HEADLESS="false"
OUTPUT_DIR=""
PRIVACY_LEVEL=""
TIME_OF_DAY="auto"
GOAL=""
HOST="http://localhost:5000"
REPORT_MODE="false"

# Config directory
CONFIG_DIR="$(dirname "$(readlink -f "$0")")"
ENV_FILE="${CONFIG_DIR}/.env"

# Parse arguments
for arg in "$@"; do
  case $arg in
    profile=*)
      PROFILE="${arg#*=}"
      ;;
    max_tokens=*)
      MAX_TOKENS="${arg#*=}"
      ;;
    limit_interactions=*|max_interactions=*)
      MAX_INTERACTIONS="${arg#*=}"
      ;;
    tools_enabled=*|tools=*)
      TOOLS_ENABLED="${arg#*=}"
      ;;
    no_llm=*|heuristic=*)
      NO_LLM="${arg#*=}"
      ;;
    headless=*)
      HEADLESS="${arg#*=}"
      ;;
    output=*|output_dir=*)
      OUTPUT_DIR="${arg#*=}"
      ;;
    privacy_level=*|privacy=*)
      PRIVACY_LEVEL="${arg#*=}"
      ;;
    time_of_day=*|time=*)
      TIME_OF_DAY="${arg#*=}"
      ;;
    goal=*|test_goal=*)
      GOAL="${arg#*=}"
      ;;
    host=*|url=*)
      HOST="${arg#*=}"
      ;;
    report=*|report_mode=*)
      REPORT_MODE="${arg#*=}"
      ;;
    help|--help|-h)
      echo "Usage: ./run-agent.sh [options]"
      echo ""
      echo "Options:"
      echo "  profile=NAME             User profile to use (tech_fan, news_skeptic, etc.)"
      echo "  max_tokens=NUMBER        Maximum token limit for Claude API"
      echo "  limit_interactions=NUMBER Maximum browser interactions"
      echo "  tools_enabled=BOOL       Enable browser tools (true/false)"
      echo "  no_llm=BOOL              Run in heuristic mode without Claude API (true/false)"
      echo "  headless=BOOL            Run in headless mode (true/false)"
      echo "  output_dir=PATH          Directory to save logs and results"
      echo "  privacy_level=LEVEL      Privacy level to test (full, limited, none)"
      echo "  time_of_day=TIME         Time context (morning, afternoon, evening, night, auto)"
      echo "  goal=TEXT                Custom test goal"
      echo "  host=URL                 Corgi Recommender service URL"
      echo "  report=BOOL              Generate analytics report from logs (true/false)"
      echo ""
      echo "Examples:"
      echo "  ./run-agent.sh profile=tech_fan"
      echo "  ./run-agent.sh profile=meme_lover headless=true limit_interactions=15"
      echo "  ./run-agent.sh profile=privacy_tester privacy_level=limited"
      echo "  ./run-agent.sh report=true"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Use ./run-agent.sh --help for usage information"
      exit 1
      ;;
  esac
done

# Check for required environment variables
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env file not found at $ENV_FILE"
  echo "Please create one from .env.example"
  exit 1
fi

# Source the environment file
source "$ENV_FILE"

# Check for required API key unless in no-llm mode
if [ "$NO_LLM" != "true" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$CLAUDE_API_KEY" ]; then
  echo "Error: No Claude API key found in environment"
  echo "Please set ANTHROPIC_API_KEY or CLAUDE_API_KEY in your .env file"
  exit 1
fi

# Required profile parameter unless in report mode
if [ "$REPORT_MODE" != "true" ] && [ -z "$PROFILE" ]; then
  echo "Error: profile parameter is required"
  echo "Use ./run-agent.sh --help for usage information"
  exit 1
fi

# Create timestamped output directory if not specified
if [ -z "$OUTPUT_DIR" ]; then
  TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
  if [ -n "$PROFILE" ]; then
    OUTPUT_DIR="${CONFIG_DIR}/logs/runs/${PROFILE}_${TIMESTAMP}"
  else
    OUTPUT_DIR="${CONFIG_DIR}/logs/runs/report_${TIMESTAMP}"
  fi
  mkdir -p "$OUTPUT_DIR"
fi

# Build command arguments
CMD_ARGS=()

if [ "$REPORT_MODE" = "true" ]; then
  # Run in report mode
  CMD_ARGS+=("--analyze-logs")
  CMD_ARGS+=("--output" "$OUTPUT_DIR/report.json")
else
  # Regular agent run
  CMD_ARGS+=("--profile" "$PROFILE")
  CMD_ARGS+=("--host" "$HOST")
  CMD_ARGS+=("--output" "$OUTPUT_DIR/results.json")
  
  # Add optional arguments
  if [ -n "$MAX_TOKENS" ]; then
    CMD_ARGS+=("--max-tokens" "$MAX_TOKENS")
  fi
  
  if [ -n "$MAX_INTERACTIONS" ]; then
    CMD_ARGS+=("--max-interactions" "$MAX_INTERACTIONS")
  fi
  
  if [ "$TOOLS_ENABLED" = "true" ]; then
    CMD_ARGS+=("--tools-enabled")
  fi
  
  if [ "$NO_LLM" = "true" ]; then
    CMD_ARGS+=("--no-llm")
  fi
  
  if [ "$HEADLESS" = "true" ]; then
    export HEADLESS_MODE="true"
  fi
  
  if [ -n "$PRIVACY_LEVEL" ]; then
    CMD_ARGS+=("--privacy-level" "$PRIVACY_LEVEL")
  fi
  
  if [ -n "$TIME_OF_DAY" ] && [ "$TIME_OF_DAY" != "auto" ]; then
    CMD_ARGS+=("--time-of-day" "$TIME_OF_DAY")
  fi
  
  if [ -n "$GOAL" ]; then
    CMD_ARGS+=("--goal" "$GOAL")
  fi
fi

# Print command being executed
echo "Running: python ${CONFIG_DIR}/agents/test_runner.py ${CMD_ARGS[*]}"
echo "Output directory: $OUTPUT_DIR"

# Execute the command
python "${CONFIG_DIR}/agents/test_runner.py" "${CMD_ARGS[@]}" | tee "$OUTPUT_DIR/run.log"

# Check for successful execution
if [ $? -eq 0 ]; then
  echo "Agent run completed successfully"
  echo "Results saved to $OUTPUT_DIR"
else
  echo "Agent run failed"
  exit 1
fi