# Corgi Agent Framework Guide

The Corgi Agent Framework provides a flexible, modular system for simulating synthetic users interacting with the Corgi Recommender service. This document covers how to use, customize, and extend the framework.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Running Agents](#running-agents)
3. [Available User Profiles](#available-user-profiles)
4. [Security Features](#security-features)
5. [Creating Custom Profiles](#creating-custom-profiles)
6. [Analyzing Results](#analyzing-results)
7. [Advanced Features](#advanced-features)
8. [Deployment Options](#deployment-options)

## Getting Started

### Prerequisites

- Python 3.9+
- Claude API key with access to the computer_use tool
- Running instance of the Corgi Recommender service

### Setup

1. **Environment Configuration**

   Copy the example environment file and add your API key:

   ```bash
   cp .env.example .env
   # Edit .env to add your Claude API key
   ```

2. **Required Libraries**

   Install the required libraries:

   ```bash
   pip install -r agents/requirements.txt
   ```

3. **Verify Setup**

   Run a test to verify your setup:

   ```bash
   python agents/test_all_features.py --feature no_llm
   ```

## Running Agents

### Command Line

The simplest way to run an agent is via the command line:

```bash
python agents/test_runner.py --profile tech_fan --tools-enabled
```

### Helper Script

For convenience, use the `run-agent.sh` script:

```bash
./run-agent.sh profile=tech_fan tools_enabled=true
```

### Makefile Target

Use the make target for even simpler execution:

```bash
make run-agent profile=tech_fan tools_enabled=true
```

### Docker Container

For isolated, reproducible environments, use Docker:

```bash
make agent-docker profile=tech_fan tools_enabled=true
```

Or directly with Docker:

```bash
docker build -t corgi-agent -f agents/Dockerfile .
docker run -it --rm -v $PWD/.env:/app/.env:ro -v $PWD/logs:/app/logs corgi-agent --profile tech_fan
```

### Common Options

| Option | Script Format | CLI Format | Description |
|--------|---------------|------------|-------------|
| Profile | `profile=NAME` | `--profile NAME` | User profile to simulate |
| Max Tokens | `max_tokens=50000` | `--max-tokens 50000` | Token usage limit |
| Browser Tools | `tools_enabled=true` | `--tools-enabled` | Enable browser tooling |
| Fast Mode | `no_llm=true` | `--no-llm` | Run without Claude API |
| Interaction Limit | `limit_interactions=15` | `--max-interactions 15` | Browser interactions limit |
| Privacy Testing | `privacy_level=limited` | `--privacy-level limited` | Privacy level to test |
| Custom Goal | `goal="Find corgis"` | `--goal "Find corgis"` | Custom test goal |
| Headless Mode | `headless=true` | `--headless` | Simulated UI with no real browser |

## Available User Profiles

The framework includes several built-in user profiles:

### tech_fan
A user interested in technology and technical content.
- Prefers: linux, programming, coding, open source
- Behavior: Seeks technical content, favoriting tech-related posts

### news_skeptic
A user who is skeptical of news content and prefers factual information.
- Prefers: verified news, fact checking, research, data journalism
- Behavior: Evaluates content critically, distrusts sensationalism

### meme_lover
A user who enjoys humorous, light-hearted content.
- Prefers: memes, funny, humor, jokes, cute animals
- Behavior: Rapidly scrolls, seeking entertainment, loves corgis

### privacy_tester
A user who tests different privacy settings and observes impacts.
- Prefers: privacy, security, data protection
- Behavior: Methodically tests and evaluates privacy settings

### text_only
A user who interacts via text without browser capabilities.
- Prefers: general content
- Behavior: Simple text-based interactions, no browser UI

## Security Features

The agent framework includes several security features:

### Network Isolation

By default, Docker containers run with network isolation. You can configure:

```bash
# Disable internet access entirely
./run-agent.sh profile=tech_fan disable_internet=true

# Allow only specific domains
./run-agent.sh profile=tech_fan allowed_domains="localhost,corgi-api.example.com"
```

### Headless Mode

For security and reproducibility, run in headless mode:

```bash
./run-agent.sh profile=tech_fan headless=true
```

This simulates the browser UI without requiring actual browser access.

### Sandbox Options

For testing in a completely isolated environment:

```bash
make agent-docker profile=tech_fan disable_internet=true headless=true
```

## Creating Custom Profiles

### Basic Profile Structure

Create a new profile by adding a class in `agents/user_profiles.py`:

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
            use_browser=True  # Set to False for text-only profiles
        )
    
    def get_behavior_prompt(self, time_of_day=None, test_goal=None) -> str:
        # Add time-of-day and goal-specific customization
        base_prompt = (
            "You are a fashion enthusiast browsing the Corgi Recommender. "
            "Your goal is to find and interact with posts about stylish corgis."
        )
        
        # Adapt based on time of day
        if time_of_day == "morning":
            base_prompt += " It's morning, so you're looking for the day's trends."
        
        return base_prompt
    
    def rate_recommendation(self, post_content: str) -> str:
        # Generate feedback based on post content
        if "fashion" in post_content.lower() or "style" in post_content.lower():
            return "Love this fashion content! Totally my style!"
        else:
            return "This doesn't seem fashion-related. I'm looking for stylish content."
```

### Optimized Batch Processing

For efficiency, implement batch processing:

```python
def handle_post_batch(self, post_contents: List[str]) -> Dict[str, str]:
    """Process multiple posts in one go."""
    results = {}
    for post in post_contents:
        post_lower = post.lower()
        if "fashion" in post_lower or "style" in post_lower:
            results[post] = "Love this fashion content! Totally my style!"
        else:
            results[post] = "This doesn't seem fashion-related. I'm looking for stylish content."
    return results
```

### Heuristic Decision Making

For no-LLM mode, implement heuristic decision making:

```python
def make_heuristic_decision(self, action_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Make decisions without calling Claude API."""
    if action_type == "rating":
        post_content = context.get("post_content", "").lower()
        if "fashion" in post_content or "style" in post_content:
            return {"decision": "favorite", "reason": "fashion content"}
        else:
            return {"decision": "skip", "reason": "not fashion-related"}
    elif action_type == "privacy":
        return {"decision": "limited", "reason": "balanced privacy"}
    else:
        return {"decision": "scroll"}
```

### Registering Your Profile

After creating your profile class, add it to the registry in `get_profile_by_name()` function:

```python
def get_profile_by_name(profile_name: str) -> UserProfile:
    profiles = {
        "tech_fan": TechFan(),
        "news_skeptic": NewsSkeptic(),
        "meme_lover": MemeLover(),
        "privacy_tester": PrivacyTester(),
        "text_only": TextOnlyUser(),
        "fashion_fan": FashionEnthusiastUser(),  # Add your new profile here
    }
    # ...
```

## Analyzing Results

### Single Run Analysis

After each run, the framework automatically logs and displays results:

```bash
./run-agent.sh profile=tech_fan output_dir=logs/my_test
```

This will create detailed logs in `logs/my_test/` including:
- `results.json`: Complete test results
- `run.log`: Console output log

### Multiple Run Analysis

To analyze results across multiple runs:

```bash
./run-agent.sh report=true
```

This generates:
- Summary statistics across all runs
- Per-profile performance metrics
- Token usage and cost estimates

### Token Usage Statistics

View token usage statistics:

```bash
python agents/test_runner.py --show-usage
```

Or with the helper script:

```bash
./run-agent.sh report=true
```

## Advanced Features

### Multi-Agent Testing

Run multiple agents in parallel:

```bash
make multi-agent profiles="tech_fan news_skeptic meme_lover"
```

This launches each profile in parallel (in no-llm mode for performance).

### Webhook Notifications

Configure webhook notifications for test completion:

```bash
./run-agent.sh profile=tech_fan webhook_url="https://your-webhook-endpoint.com"
```

### Batch Processing

For large-scale testing:

```bash
# Create a batch job script
for profile in tech_fan news_skeptic meme_lover privacy_tester; do
  for privacy in full limited none; do
    ./run-agent.sh profile=$profile privacy_level=$privacy no_llm=true headless=true &
  done
done
wait
```

## Deployment Options

### Docker Deployment

The included Dockerfile is production-ready:

```bash
# Build image
docker build -t corgi-agent -f agents/Dockerfile .

# Run with security features enabled
docker run -it --rm \
  -v $PWD/.env:/app/.env:ro \
  -v $PWD/logs:/app/logs \
  -e CLAUDE_DISABLE_INTERNET=true \
  -e HEADLESS_MODE=true \
  corgi-agent --profile tech_fan --no-llm
```

### Cloud Deployment

For scheduled test runs, set up a cloud environment:

1. Push the Docker image to a container registry
2. Set up a scheduled job (e.g., Kubernetes CronJob)
3. Configure webhook notifications for results reporting
4. Mount a shared volume for logs or send to a logging service

Example Kubernetes CronJob:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: corgi-agent-test
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: corgi-agent
            image: your-registry/corgi-agent:latest
            args:
            - "--profile"
            - "tech_fan"
            - "--no-llm"
            - "--headless"
            volumeMounts:
            - name: env-file
              mountPath: /app/.env
              subPath: .env
            - name: logs
              mountPath: /app/logs
          volumes:
          - name: env-file
            secret:
              secretName: corgi-agent-env
          - name: logs
            persistentVolumeClaim:
              claimName: corgi-agent-logs
          restartPolicy: OnFailure
```

### CI/CD Integration

For continuous testing, integrate with your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
name: Run Agent Tests
on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Build Docker image
      run: docker build -t corgi-agent -f agents/Dockerfile .
    - name: Run agent tests
      run: |
        docker run --rm \
          -v ${{ github.workspace }}/.env.ci:/app/.env \
          -v ${{ github.workspace }}/logs:/app/logs \
          corgi-agent --profile tech_fan --no-llm --headless
```