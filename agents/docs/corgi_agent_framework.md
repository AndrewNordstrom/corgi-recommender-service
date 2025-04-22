# Corgi Agent Framework - Phase 3

## Overview

Phase 3 of the Corgi Agent Framework adds enhanced cost efficiency, API monitoring, and operational controls. These features make the agent framework more robust for production use and provide better visibility into API usage and costs.

## Key Features

### Secure API Key Management

- API keys are loaded from `.env` file using `python-dotenv`
- Connectivity with Claude API is validated at startup
- Proper error handling if API key is missing or invalid

### Token Usage Monitoring

- Tracks tokens used per run and per Claude request
- Estimates costs based on current Claude pricing
- Supports token usage limits to control costs
- Usage logs are stored in `logs/token_usage.log`

### Selective Tool Access

- `computer_use` tool is activated only when needed
- User profiles can specify whether they require browser tooling
- Reduces token usage for simple text-based requests

### API Call Optimization

- Batch evaluation of multiple posts in a single prompt
- In-memory caching to avoid reprocessing identical content
- More efficient conversation structure

### Browser Interaction Controls

- Limits on interaction count to prevent runaway agents
- Graceful shutdown and summary output
- Better control over agent session duration

### Fast Agent Mode (No LLM)

- Heuristic-based agent decisions without Claude API calls
- Perfect for stress testing and multi-user simulations
- Preserves all logging and API interactions

## Command Line Options

```
# Standard run with token monitoring
python agents/test_runner.py --profile news_skeptic --max-tokens 100000

# Enable browser tooling
python agents/test_runner.py --profile tech_fan --tools-enabled

# Limit browser interactions
python agents/test_runner.py --profile meme_lover --max-interactions 10 --tools-enabled

# Fast mode without Claude API
python agents/test_runner.py --profile privacy_tester --no-llm

# View token usage statistics
python agents/test_runner.py --show-usage
```

## Implementation Details

### New Modules

- `claude_interface.py`: Secure Claude API wrapper with usage tracking
- `token_tracker.py`: Token and cost monitoring

### Modified Components

- `browser_agent.py`: Now supports interaction limits and batch processing
- `test_runner.py`: Enhanced CLI with new flags
- `user_profiles.py`: Added `use_browser` property to control tool access

## Environment Variables

Required in `.env` file:

```
# Claude API key (one of these is required)
ANTHROPIC_API_KEY=sk-ant-xxxx
# or
CLAUDE_API_KEY=sk-ant-xxxx

# Optional - set a default token limit
DEFAULT_MAX_TOKENS=500000
```

## Cost Control

The framework provides several mechanisms for controlling API costs:

1. `--max-tokens`: Stop after using a specified number of tokens
2. `--no-llm`: Run agents without calling the Claude API
3. `--max-interactions`: Limit the number of browser interactions
4. `--tools-enabled`: Only activate tools when explicitly needed

Token usage is logged to `logs/token_usage.log` for monitoring.

## Usage Examples

### Running a Cost-Aware Privacy Test

```bash
python agents/test_runner.py \
  --profile privacy_tester \
  --privacy-level limited \
  --max-tokens 50000 \
  --tools-enabled \
  --max-interactions 15
```

### Running Multiple Fast Tests

```bash
# Run 5 fast agents without using Claude API
for p in tech_fan news_skeptic meme_lover privacy_tester tech_fan; do
  python agents/test_runner.py --profile $p --no-llm
done
```

### Analyzing Token Usage

```bash
python agents/test_runner.py --show-usage
```
