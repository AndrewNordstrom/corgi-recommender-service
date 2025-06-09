# Intelligent Browser Testing for Corgi Recommender Service

## Overview

Say goodbye to the archaic practice of manually checking if your frontend changes work! The Intelligent Browser Testing system automates the entire process of verifying that your changes work correctly, acting like a real user would.

## Quick Start

After making changes to the frontend or API, simply run:

```bash
./test-frontend.sh
```

That's it! The system will:
- ✅ Check if services are running
- ✅ Test API connectivity
- ✅ Verify OAuth flow works
- ✅ Report clear PASS/FAIL results
- ✅ Take screenshots on failure

## Installation

First time setup:

```bash
# Install dependencies
make dev-install

# This will install Playwright and download the browser
```

## Usage Examples

### Basic Test (Headless)
```bash
# Quick test - runs in background, no browser window
./test-frontend.sh

# Or use make command
make dev-test
```

### Watch the Browser (Headed Mode)
```bash
# See the browser in action
./test-frontend.sh --headed

# Or use make command
make dev-test-headed
```

### Continuous Testing
```bash
# Run tests every 30 seconds
./test-frontend.sh --continuous

# Or use make command
make dev-test-continuous
```

## What It Tests

### 1. API Connection Test
**CRITICAL**: This test checks for the dreaded "[Corgi] Running in offline mode" message.

- ✅ **PASS**: API is connected, frontend can communicate with backend
- ❌ **FAIL**: Frontend is in offline mode, API connection is broken

### 2. OAuth Flow Test
Tests the authentication flow:

- Finds and clicks the "Sign in" button
- Verifies navigation to OAuth page
- Checks for Corgi branding

## Understanding Results

### Success Output
```
🤖 Browser Agent Test Results - 2025-01-08 00:30:45
================================================================================

ELK-Corgi API Connection: ✅ PASSED (2.34s)

OAuth Authorization Flow: ✅ PASSED (1.56s)

--------------------------------------------------------------------------------
Summary: 2/2 tests passed
✅ All tests passed!
```

### Failure Output
```
🤖 Browser Agent Test Results - 2025-01-08 00:35:12
================================================================================

ELK-Corgi API Connection: ❌ FAILED (2.45s)
  Error: ❌ API CONNECTION BROKEN: Frontend is running in offline mode!
  Screenshot: logs/screenshots/api_offline_error_20250108_003512.png

--------------------------------------------------------------------------------
Summary: 0/1 tests passed
❌ 1 test(s) failed!
```

## Advanced Features

### Custom Test Configuration

Run the browser agent directly for more control:

```bash
# Test against different URLs
python3 scripts/development/browser_agent.py \
  --frontend-url http://localhost:3001 \
  --api-url http://localhost:5003

# Verbose output
python3 scripts/development/browser_agent.py --verbose

# Run specific test scenarios (future)
python3 scripts/development/browser_agent.py --test oauth-flow
```

### Integration with Development Workflow

The browser agent integrates seamlessly with `make dev`:

```bash
# Start everything and run tests automatically
make dev && sleep 10 && make dev-test
```

### Continuous Integration

Add to your CI/CD pipeline:

```yaml
- name: Run Browser Tests
  run: |
    ./test-frontend.sh
  continue-on-error: false
```

## Troubleshooting

### Common Issues

#### "Playwright not available"
```bash
# Reinstall
pip install playwright
playwright install chromium
```

#### "Browser fails to start"
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install -y \
  libglib2.0-0 libgstreamer-gl1.0-0 libgstreamer-plugins-base1.0-0 \
  libgstreamer1.0-0 libgtk-3-0 libharfbuzz0b libhyphen0 \
  libmanette-0.2-0 libnotify4 libopengl0 libopus0 libsecret-1-0 \
  libwayland-client0 libwayland-egl1 libwayland-server0 \
  libwebpdemux2 libwoff1 libxcomposite1 libxdamage1 \
  libxfixes3 libxkbcommon0 libxrandr2 libxslt1.1

# Or on macOS
brew install --cask chromium
```

#### "Tests pass but I still see issues"
1. Run with `--headed` to watch what happens
2. Check `logs/browser_agent.log` for detailed logs
3. Review screenshots in `logs/screenshots/`
4. Add `--verbose` for more output

### Debug Mode

For maximum visibility:

```bash
# See everything
python3 scripts/development/browser_agent.py \
  --headed \
  --verbose \
  --frontend-url http://localhost:3000
```

## How It Works

The browser agent uses Playwright to:

1. **Launch a real browser** (Chromium)
2. **Navigate to your frontend**
3. **Monitor console messages** for errors
4. **Interact with the page** like a user would
5. **Take screenshots** when things go wrong
6. **Report results** with clear pass/fail status

### Key Components

- **`browser_agent.py`**: The intelligent testing engine
- **`test-frontend.sh`**: User-friendly wrapper script
- **Playwright**: Modern browser automation framework
- **Async Python**: For efficient test execution

## Extending the Tests

The browser agent is designed to be extensible. Add new test methods to `browser_agent.py`:

```python
async def test_custom_feature(self, page: Page) -> TestResult:
    """Test your custom feature"""
    # Your test logic here
    pass
```

## Comparison with Manual Testing

| Manual Testing | Intelligent Browser Testing |
|----------------|---------------------------|
| Open browser manually | `./test-frontend.sh` |
| Navigate to localhost:3000 | Automated |
| Open DevTools Console | Automated monitoring |
| Look for errors | Automated detection |
| Click through UI | Automated interaction |
| Remember what to check | Codified test scenarios |
| 5-10 minutes | 5-10 seconds |

## Future Enhancements

### Coming Soon
- LLM-powered exploratory testing
- Visual regression testing
- Performance metrics
- Accessibility checks
- Multi-browser support

### Anthropic Computer Use Integration
When Anthropic's Computer Use API becomes publicly available, we can upgrade to true AI-driven testing where Claude can:
- Explore the UI naturally
- Find bugs humans might miss
- Generate test scenarios
- Provide detailed reports

## Best Practices

1. **Run tests after every change**: Make it a habit
2. **Use continuous mode during development**: Keep it running in a terminal
3. **Check screenshots on failure**: They show exactly what went wrong
4. **Add custom tests for new features**: Extend the framework
5. **Keep tests fast**: Sub-10 second test runs maintain flow

## Conclusion

This intelligent browser testing system transforms your development workflow from:

❌ **Old Way**: Make changes → Start services → Open browser → Check console → Click around → Hope it works

✅ **New Way**: Make changes → `./test-frontend.sh` → Get instant feedback

Welcome to the future of frontend testing! 🚀 