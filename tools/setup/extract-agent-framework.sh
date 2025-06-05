#!/bin/bash

# Script to extract the Agent Framework to a standalone repository
# Usage: ./extract-agent-framework.sh /path/to/destination

set -e

DEST_DIR=${1:-"../corgi-agent-framework"}

if [ -d "$DEST_DIR" ]; then
    echo "Error: Destination directory already exists: $DEST_DIR"
    echo "Please provide a path to a non-existent directory, or remove the existing one."
    exit 1
fi

echo "Extracting Corgi Agent Framework to: $DEST_DIR"

# Create target directory structure
mkdir -p "$DEST_DIR"/agents
mkdir -p "$DEST_DIR"/logs/{agent_sessions,agent_feedback,token_usage,multi_runs,runs}
mkdir -p "$DEST_DIR"/docs

# Copy agent code
cp -r agents/* "$DEST_DIR"/agents/
cp -r docs/agent_guide.md "$DEST_DIR"/docs/

# Copy utility scripts
cp run-agent.sh "$DEST_DIR"/
cp agents/test_all_features.py "$DEST_DIR"/

# Copy dockerization
cp agents/Dockerfile "$DEST_DIR"/
cp agents/requirements.txt "$DEST_DIR"/

# Create a standalone docker-compose.yml 
cat > "$DEST_DIR"/docker-compose.yml << 'EOF'
version: '3.8'

services:
  # Agent Framework
  agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: corgi-agent
    environment:
      - CLAUDE_DISABLE_INTERNET=${CLAUDE_DISABLE_INTERNET:-true}
      - CLAUDE_ALLOWED_DOMAINS=${CLAUDE_ALLOWED_DOMAINS:-localhost}
      - HEADLESS_MODE=${HEADLESS_MODE:-true}
      - CORGI_SERVICE_URL=${CORGI_SERVICE_URL:-http://localhost:5000}
      - DEFAULT_MAX_TOKENS=${DEFAULT_MAX_TOKENS:-500000}
    volumes:
      - ./.env:/app/.env:ro
      - ./logs:/app/logs
    command: >
      --profile ${AGENT_PROFILE:-tech_fan}
      ${AGENT_ARGS}
      
  # Multi-agent runner
  multi-agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: corgi-multi-agent
    environment:
      - CLAUDE_DISABLE_INTERNET=${CLAUDE_DISABLE_INTERNET:-true}
      - CLAUDE_ALLOWED_DOMAINS=${CLAUDE_ALLOWED_DOMAINS:-localhost}
      - HEADLESS_MODE=${HEADLESS_MODE:-true}
      - CORGI_SERVICE_URL=${CORGI_SERVICE_URL:-http://localhost:5000}
      - DEFAULT_MAX_TOKENS=${DEFAULT_MAX_TOKENS:-500000}
    volumes:
      - ./.env:/app/.env:ro
      - ./logs:/app/logs
    entrypoint: ["/bin/bash", "-c"]
    command: >
      "
      echo 'Running multiple agents for testing...' &&
      for profile in tech_fan news_skeptic meme_lover privacy_tester; do
        timestamp=$$(date +%Y%m%d_%H%M%S) &&
        echo \"Starting agent: $${profile}\" &&
        python /app/agents/test_runner.py --profile $${profile} --no-llm --headless --output /app/logs/multi_runs/$${profile}_$${timestamp}.json --host $${CORGI_SERVICE_URL} &
      done &&
      wait
      "
EOF

# Create a sample README.md
cat > "$DEST_DIR"/README.md << 'EOF'
# Corgi Agent Framework

A modular, Claude-powered agent framework for simulating real users interacting with the Corgi Recommender system.

## Overview

This framework provides tools to create synthetic users that interact with recommendation systems through Claude's computer_use tool. These agents can:

- Simulate real users navigating recommendation UIs
- Interact with posts (favorite, bookmark, scroll)
- Provide natural language feedback on recommendations
- Test privacy features and observe changes in recommendations
- Log actions and submit feedback to APIs

## Features

- Multiple user profiles with different interests and behaviors
- Token usage monitoring and cost controls
- Headless operation for CI/CD environments
- Docker-based deployment with security features
- Detailed logging and analytics

## Quick Start

1. Set up environment:
   ```bash
   cp .env.example .env
   # Edit .env to add your Claude API key
   ```

2. Run a test:
   ```bash
   ./run-agent.sh profile=tech_fan
   ```

3. Run in Docker:
   ```bash
   docker-compose up agent
   ```

For detailed documentation, see [Agent Guide](docs/agent_guide.md).

## Extracted from Corgi Recommender Service

This framework was originally part of the Corgi Recommender Service and has been extracted to make it reusable across multiple projects.
EOF

# Create a sample .env.example file
cat > "$DEST_DIR"/.env.example << 'EOF'
# Corgi Agent Framework Environment Variables

# Claude API configuration
ANTHROPIC_API_KEY=your_claude_api_key_here
# or
# CLAUDE_API_KEY=your_claude_api_key_here

# Target service URL
CORGI_SERVICE_URL=http://localhost:5000

# Optional - set default token limit
DEFAULT_MAX_TOKENS=500000

# Network isolation (security)
CLAUDE_DISABLE_INTERNET=true
CLAUDE_ALLOWED_DOMAINS=localhost,example.com

# Headless mode
HEADLESS_MODE=true
EOF

# Make scripts executable
chmod +x "$DEST_DIR"/run-agent.sh

echo "Extraction complete!"
echo "The Agent Framework is now available at: $DEST_DIR"
echo ""
echo "Next steps:"
echo "1. Navigate to the directory: cd $DEST_DIR"
echo "2. Set up your environment: cp .env.example .env"
echo "3. Edit the .env file to add your Claude API key"
echo "4. Run a test: ./run-agent.sh profile=tech_fan no_llm=true"