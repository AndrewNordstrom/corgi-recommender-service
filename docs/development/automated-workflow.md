# Automated Development Workflow

This document describes the automated development workflow that eliminates the need for manual browser checking and provides real-time feedback on your development environment.

## Overview

The automated workflow addresses common developer pain points:

- ❌ **Before**: Manually checking browser for 503 errors
- ❌ **Before**: Manually checking console for JavaScript errors  
- ❌ **Before**: Manually verifying API endpoints work
- ❌ **Before**: Switching between terminal and browser constantly

- ✅ **After**: Automated health monitoring every 10 seconds
- ✅ **After**: Automated browser testing every 30 seconds
- ✅ **After**: Real-time alerts for issues
- ✅ **After**: Automatic screenshot capture on errors

## Quick Start

### 1. Install Dependencies

```bash
# Install development workflow dependencies
make dev-install

# Or manually:
pip install aiohttp selenium
```

### 2. Start the Automated Workflow

```bash
# Start everything with monitoring
make dev

# Or using the direct script:
./dev-monitor start
```

This will:
- Start your backend API server (Flask)
- Start your frontend server (Next.js)
- Begin automated health monitoring
- Begin automated browser testing
- Display real-time status updates

### 3. Monitor Your Development

The workflow will automatically:
- Check API endpoints every 10 seconds
- Test frontend pages every 30 seconds
- Alert you immediately to any 503 errors
- Capture screenshots when issues are detected
- Log all issues to `logs/` directory

## Commands

### Basic Commands

```bash
# Start full development workflow
make dev

# Check current status
make dev-status

# Stop all services
make dev-stop

# Run health check once
make dev-health

# Run browser check once
make dev-browser
```

### Advanced Usage

```bash
# Start with verbose output
./dev-monitor start --verbose

# Use custom ports
./dev-monitor start --backend-port 8000 --frontend-port 4000

# Run health check only
./dev-monitor health --verbose

# Run browser check with visible browser (for debugging)
./dev-monitor browser --show-browser
```

## What Gets Monitored

### Backend Health Checks

The system automatically checks these endpoints:
- `/health` - Basic health check
- `/api/v1/health` - API health check
- `/api/v1/recommendations` - Core recommendation functionality
- `/api/v1/posts` - Post management functionality

### Frontend Browser Checks

The system automatically tests these pages:
- `/` - Home page
- `/dashboard` - Dashboard functionality
- `/explore` - Explore page
- `/metrics` - Metrics page
- `/docs` - Documentation

For each page, it checks:
- Page load times
- Console errors (JavaScript errors)
- Network errors (failed API calls)
- HTTP status codes
- Page content for error indicators

## Output and Logs

### Real-time Display

The workflow shows a live status dashboard:

```
================================================================================
Development Workflow Status - 2024-01-15 14:30:22
================================================================================

✅ Backend API         running    PID: 12345   Port: 5000   URL: http://localhost:5000
✅ Frontend            running    PID: 12346   Port: 3000   URL: http://localhost:3000
✅ Health Monitor      running    PID: 12347
✅ Browser Monitor     running    PID: 12348

📊 Quick Status:
✅ Both services are running - ready for development!

💡 Monitoring active - press Ctrl+C to stop
📁 Logs: logs/health_monitor.log, logs/browser_monitor.log
🌐 Backend: http://localhost:5000
🎨 Frontend: http://localhost:3000
```

### Log Files

All monitoring data is saved to:
- `logs/health_monitor.log` - Health check logs
- `logs/browser_monitor.log` - Browser testing logs
- `logs/latest_health_check.json` - Latest health check results
- `logs/latest_browser_check.json` - Latest browser check results
- `logs/screenshots/` - Screenshots when issues are detected

### Issue Detection

When issues are detected, you'll see immediate alerts:

```
🚨 3 health issues detected - check logs/latest_health_check.json
🚨 2 browser issues detected - check logs/latest_browser_check.json
```

## Troubleshooting

### Common Issues

#### "Selenium not available"
```bash
pip install selenium
# Also install ChromeDriver:
brew install chromedriver  # macOS
```

#### "Could not connect to service"
- Check if ports 5000 (backend) and 3000 (frontend) are available
- Verify your backend and frontend are configured correctly
- Try `make dev-status` to see what's running

#### "Browser automation fails"
- Install ChromeDriver: https://chromedriver.chromium.org/
- Try running with `--show-browser` to see what's happening
- Check Chrome is installed and up to date

### Debugging

```bash
# Run with verbose output to see detailed logs
./dev-monitor start --verbose

# Run health check in isolation
./dev-monitor health --verbose

# Run browser check with visible browser
./dev-monitor browser --show-browser

# Check individual scripts
python3 scripts/development/health_monitor.py --once --verbose
python3 scripts/development/browser_monitor.py --once --show-browser
```

## Integration with Existing Workflow

### VS Code Integration

Add this to your VS Code tasks (`.vscode/tasks.json`):

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start Dev Workflow",
            "type": "shell",
            "command": "make dev",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "new"
            },
            "problemMatcher": []
        }
    ]
}
```

### Git Hooks

Add a pre-commit hook to ensure health checks pass:

```bash
#!/bin/sh
# .git/hooks/pre-commit
echo "Running health check before commit..."
./dev-monitor health
if [ $? -ne 0 ]; then
    echo "Health check failed! Fix issues before committing."
    exit 1
fi
```

## Customization

### Adding New Endpoints

Edit `scripts/development/health_monitor.py`:

```python
self.endpoints = {
    'backend': [
        '/health',
        '/api/v1/health',
        '/api/v1/recommendations',
        '/api/v1/posts',
        '/api/v1/your-new-endpoint',  # Add here
    ],
    # ...
}
```

### Adding New Pages

Edit `scripts/development/browser_monitor.py`:

```python
self.pages_to_check = [
    '/',
    '/dashboard',
    '/explore',
    '/metrics',
    '/docs',
    '/your-new-page',  # Add here
]
```

### Custom Check Intervals

```bash
# Health checks every 5 seconds, browser checks every 60 seconds
python3 scripts/development/dev_workflow.py --health-interval 5 --browser-interval 60
```

## Benefits

- **🚀 Faster Development**: No more manual browser checking
- **🔍 Early Detection**: Catch issues immediately when they occur
- **📊 Data-Driven**: Historical logs help identify patterns
- **🎯 Focus**: Spend time coding, not debugging deployment issues
- **📸 Evidence**: Screenshots provide visual proof of issues
- **⚡ Automation**: Set it and forget it monitoring

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Backend API   │    │    Frontend     │
│   (Flask)       │    │   (Next.js)     │
│   Port 5000     │    │   Port 3000     │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌─────────────────┐
         │  Dev Workflow   │
         │    Manager      │
         └─────────────────┘
                     │
         ┌─────────────────┬─────────────────┐
         │                 │                 │
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Health Monitor  │ │ Browser Monitor │ │   Log Manager   │
│   (API Tests)   │ │ (UI Tests)      │ │  (Reporting)    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

This workflow transforms your development experience from reactive manual checking to proactive automated monitoring, letting you focus on building features instead of hunting down deployment issues. 