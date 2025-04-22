# Corgi Recommender Agent Framework

A modular, Claude-powered agent framework for simulating real users interacting with the Corgi Recommender system.

## Overview

This framework provides tools to create synthetic users that interact with the Corgi Recommender UI through Claude's computer_use tool. These agents can:

- Simulate real Mastodon users navigating the UI and proxy
- Interact with posts (favorite, bookmark, scroll)
- Provide natural language feedback on recommendations
- Test privacy features and observe changes in recommendations
- Log actions and submit feedback to the API

## Phase 3 Features

Phase 3 enhances the framework with several key features:

### Secure API Key Management
- API keys are loaded from `.env` file using `python-dotenv`
- Connectivity validation with Claude API at startup
- Proper error handling for missing or invalid API keys

### Token Usage Monitoring
- Tracks tokens used per request and per session
- Estimates costs based on current Claude pricing
- Supports token usage limits to control API costs
- Provides detailed usage logs and summaries

### Selective Tool Access
- Enables browser tools only when needed
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

## Getting Started

### Prerequisites

- Python 3.6+
- Claude API key (requires access to the computer_use tool)
- Running instance of the Corgi Recommender service

### Setup

1. Set up your environment:
   ```
   # Copy the example .env file and edit with your credentials
   cp .env.example .env
   # Edit the .env file to include your Claude API key
   ```

2. Verify your setup:
   ```
   # Run the test_all_features.py script to verify all Phase 3 features
   python agents/test_all_features.py
   ```

3. Run with a specific profile:
   ```
   # List available profiles
   python agents/test_runner.py --list-profiles
   
   # Run with a specific profile
   python agents/test_runner.py --profile tech_fan --tools-enabled
   ```

## Available Profiles

### User Profiles
- `tech_fan`: A user who is interested in technology-related content (formerly linux_fan)
- `news_skeptic`: A user who is skeptical of news content and prefers factual, verified information
- `meme_lover`: A user who enjoys humorous, light-hearted content and memes
- `privacy_tester`: A user who tests privacy features and observes recommendation changes
- `text_only`: A user who interacts via text only (no browser required)

Each profile includes:
- A list of preferred topics
- Behavior that adapts based on time of day
- Ability to provide natural language feedback on posts
- Privacy setting test capabilities
- Options for browser interaction or text-only mode

## Advanced Usage

### Time of Day Context

Agents can adapt their behavior based on the time of day:

```bash
# Specify time context explicitly
python agents/test_runner.py --profile meme_lover --time-of-day evening
```

### Privacy Level Testing

Test specific privacy levels:

```bash
# Test with limited privacy mode
python agents/test_runner.py --profile privacy_tester --privacy-level limited
```

### Feedback Analysis

Analyze recent feedback from agent sessions:

```bash
python agents/test_runner.py --profile tech_fan --analyze-feedback
```

### Custom Testing Goals

Provide custom test goals:

```bash
python agents/test_runner.py --profile tech_fan --goal "Find and bookmark posts about AI"
```

### Cost Control

The framework provides several mechanisms for controlling API costs:

1. `--max-tokens`: Stop after using a specified number of tokens
2. `--no-llm`: Run agents without calling the Claude API
3. `--max-interactions`: Limit the number of browser interactions
4. `--tools-enabled`: Only activate tools when explicitly needed

Token usage is logged to `logs/token_usage.log` for monitoring, and you can view usage statistics with:
```
python agents/test_runner.py --show-usage
```

## Implementation Details

### New Modules (Phase 3)

- `claude_interface.py`: Secure Claude API wrapper with usage tracking
- `token_tracker.py`: Token and cost monitoring
- `docs/phase3.md`: Detailed documentation of Phase 3 features

### Modified Components

- `browser_agent.py`: Now supports interaction limits, token tracking, and batch processing
- `test_runner.py`: Enhanced CLI with new flags for Phase 3 features
- `user_profiles.py`: Added `use_browser` property and batch processing support

## Directory Structure

- `browser_agent.py`: Main Claude agent interface with computer_use tool support
- `claude_interface.py`: Secure wrapper for Claude API with token tracking
- `token_tracker.py`: Token usage monitoring and cost estimation
- `user_profiles.py`: Different types of synthetic users with preference-based feedback
- `test_runner.py`: CLI to invoke agents with advanced options
- `feedback_module.py`: Agent-generated feedback handler with API integration
- `interaction_logger.py`: Logs actions taken during the session
- `test_all_features.py`: Verification script for Phase 3 features
- `docs/`: Documentation for the agent framework
- `prompts/`: Example prompt templates for agent instructions

## Logs and Results

Agent session logs are stored in:
- `logs/agent_sessions/`: Detailed log files for each session
- `logs/agent_feedback/`: Agent-generated feedback about the system
- `logs/token_usage.log`: Token usage tracking for API calls

## Adding New Profiles

To create a new user profile, add a new class to `user_profiles.py` that inherits from `UserProfile` and implements the required methods. Use the `use_browser` parameter to control whether browser tooling is required:

```python
class FashionEnthusiastUser(UserProfile):
    def __init__(self):
        preferred_topics = [
            "fashion", "style", "clothing", "accessories", 
            "trends", "outfits", "designer"
        ]
        super().__init__(
            name="fashion_fan",
            description="A user interested in fashionable corgis",
            preferred_topics=preferred_topics,
            use_browser=True  # Requires browser tooling
        )
    
    # ... other methods ...
    
    # Optional: Implement batch processing for efficiency
    def handle_post_batch(self, post_contents: List[str]) -> Dict[str, str]:
        """Process a batch of posts for fashion content."""
        results = {}
        for post in post_contents:
            if any(topic in post.lower() for topic in self.preferred_topics):
                results[post] = "Love this fashion content! Totally my style!"
            else:
                results[post] = "This doesn't seem fashion-related. I'm looking for stylish content."
        return results
```

Then register the new profile in the `get_profile_by_name()` function.

## Running Multiple Tests

For benchmarking or large-scale testing, you can run multiple agents in no-LLM mode:

```bash
# Run 5 fast agents without using Claude API
for p in tech_fan news_skeptic meme_lover privacy_tester tech_fan; do
  python agents/test_runner.py --profile $p --no-llm
done
```