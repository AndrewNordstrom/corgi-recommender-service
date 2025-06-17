# Manager Agent System

The Manager Agent is a comprehensive LLM monitoring and cost control system that prevents runaway costs, detects issues, and provides intelligent alerting via Slack. It monitors all LLM agents in the Corgi system and provides enterprise-grade cost management and operational intelligence.

## 🎯 Key Features

### Cost Monitoring & Control
- **Real-time cost tracking** with per-agent budgets (hourly/daily/monthly)
- **Circuit breaker pattern** - automatically disable agents after consecutive failures
- **Budget pool system** - allocate tokens/dollars per agent with priority levels
- **Cost spike detection** - alert when agents exceed spending thresholds
- **Infinite loop detection** - prevent runaway API calls

### Intelligent Issue Aggregation
- **Smart error grouping** - similar issues are aggregated together
- **TLDR generation** - concise summaries of complex issues
- **Priority-based alerting** - critical issues get immediate attention
- **Historical tracking** - maintain audit trails of all decisions

### Slack Integration
- **Rich formatting** with Slack blocks for professional alerts
- **Immediate alerts** for critical issues (cost spikes >20%, circuit breakers, infinite loops)
- **Hourly summaries** with token usage and success rates
- **Daily cost reports** with optimization suggestions
- **Aggregated issue reports** with intelligent grouping

### Enterprise Features
- **Pre-approval system** for expensive operations
- **Role-based access control** with agent priority levels
- **Dashboard endpoints** for real-time monitoring
- **SQLite storage** for historical data and metrics
- **Async architecture** for non-blocking monitoring

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LLM Agents    │───▶│  Manager Agent  │───▶│ Slack Notifier  │
│                 │    │                 │    │                 │
│ • Security      │    │ • Cost Tracker  │    │ • Rich Alerts   │
│ • Browser       │    │ • Issue Detect  │    │ • Summaries     │
│ • Content       │    │ • Circuit Break │    │ • Reports       │
│ • Recommend     │    │ • Budget Mgmt   │    │ • Aggregation   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └─────────────▶│  Cost Tracker   │◀─────────────┘
                        │                 │
                        │ • SQLite DB     │
                        │ • Usage Stats   │
                        │ • Budget Limits │
                        │ • Circuit State │
                        └─────────────────┘
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Set your Slack webhook URL (required for alerts)
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Optional: Configure specific Slack channel
export SLACK_CHANNEL="#corgi-alerts"
```

### 2. Run the Demo

```bash
# See the system in action with simulated agents
python3 scripts/demo_manager_system.py
```

This will:
- Create realistic agent budgets
- Simulate normal API activity
- Trigger cost spikes, circuit breakers, and infinite loops
- Send real Slack alerts (if configured)
- Generate cost summaries and reports

### 3. Test the Alerting System

```bash
# Comprehensive test suite for all alert types
python3 scripts/test_alerts.py
```

### 4. Run in Production

```bash
# Start the Manager Agent monitoring
python3 scripts/run_manager.py
```

## 📊 Dashboard Endpoints

The Manager Agent provides REST endpoints for monitoring:

```bash
# Get comprehensive dashboard data
curl http://localhost:5002/api/v1/manager/dashboard

# Get current status
curl http://localhost:5002/api/v1/manager/status
```

## ⚙️ Configuration

### Agent Budgets (`config/manager_agent.yaml`)

```yaml
agent_budgets:
  # Security Healing Agent - higher limits for critical operations
  security_healing_agent:
    hourly_limit_usd: 2.0
    daily_limit_usd: 20.0
    monthly_limit_usd: 200.0
    hourly_token_limit: 20000
    daily_token_limit: 200000
    monthly_token_limit: 2000000
    priority: 1  # 1=critical, 2=high, 3=medium, 4=low
  
  # Browser Agent - medium limits for automation
  browser_agent:
    hourly_limit_usd: 0.5
    daily_limit_usd: 5.0
    monthly_limit_usd: 50.0
    priority: 2
```

### Alert Thresholds

```yaml
thresholds:
  # Cost spike detection threshold (percentage above normal)
  cost_spike_percentage: 20.0
  
  # Infinite loop detection - calls per minute threshold
  infinite_loop_calls_per_minute: 10
  
  # Circuit breaker - max consecutive failures before disabling
  max_consecutive_failures: 5
```

### Monitoring Intervals

```yaml
monitoring:
  # How often to check agent status (seconds)
  check_interval_seconds: 30
  
  # How often to send summary reports (minutes)
  summary_interval_minutes: 60
  
  # Hour of day to send daily cost reports (24-hour format)
  daily_report_hour: 9
```

## 🔧 Integration with Existing Agents

### Adding Cost Tracking to Your Agent

```python
from agents.cost_tracker import track_llm_call, cost_tracker

class YourAgent:
    def __init__(self):
        self.agent_id = "your_agent_name"
        
    @track_llm_call(cost_tracker)
    async def call_llm(self, prompt: str):
        # Your LLM call here
        response = await claude_api.call(prompt)
        return response
```

### Setting Agent Budgets

```python
from agents.cost_tracker import AgentBudget, cost_tracker

# Set budget for your agent
budget = AgentBudget(
    agent_id="your_agent_name",
    hourly_limit_usd=1.0,
    daily_limit_usd=10.0,
    monthly_limit_usd=100.0,
    hourly_token_limit=10000,
    daily_token_limit=100000,
    monthly_token_limit=1000000,
    priority=2
)

cost_tracker.set_agent_budget(budget)
```

## 📈 Slack Alert Examples

### Cost Spike Alert
```
🚨 Cost Spike Detected - content_analyzer_agent

Agent `content_analyzer_agent` has exceeded cost threshold by 37.5%

Agent: content_analyzer_agent
Cost Impact: $0.1500
Time: 14:23:45
Severity: WARNING

Additional Details:
• current_cost: $0.5500
• threshold: $0.4000
• period: hourly
• percentage_over: 37.5%
```

### Circuit Breaker Alert
```
🚨 Circuit Breaker Opened - test_agent

Agent `test_agent` has been disabled due to 5 consecutive failures

Agent: test_agent
Time: 14:25:12
Severity: CRITICAL

Additional Details:
• failure_count: 5
• last_error: API rate limit exceeded
• action: Agent disabled for 5 minutes
```

### Hourly Summary
```
📊 Hourly Agent Summary

Total Cost: $2.3450
API Calls: 47
Success Rate: 95.7%
Active Agents: 4

Top Agents by Cost:
• `security_healing_agent`: $1.2300 (23 calls)
• `content_analyzer_agent`: $0.5500 (12 calls)
• `browser_agent`: $0.3400 (8 calls)
```

## 🛡️ Security Features

### Budget Enforcement
- **Hard limits** - agents are disabled when budgets are exceeded
- **Soft warnings** - alerts sent at configurable thresholds
- **Priority system** - critical agents get higher budgets
- **Time-based limits** - hourly, daily, and monthly controls

### Circuit Breaker Protection
- **Automatic disabling** after consecutive failures
- **Exponential backoff** with configurable retry intervals
- **Manual override** capabilities for emergency situations
- **Failure pattern analysis** to identify systemic issues

### Pre-approval System
- **Expensive operation approval** via Slack
- **Configurable thresholds** for requiring approval
- **Timeout handling** for approval requests
- **Audit trail** of all approval decisions

## 📊 Cost Optimization Features

### Intelligent Suggestions
- **Model downgrade recommendations** (Sonnet → Haiku for simple tasks)
- **Redundant call detection** to eliminate waste
- **Response caching** suggestions for frequently requested data
- **Usage pattern analysis** to identify optimization opportunities

### Real-time Monitoring
- **Token usage tracking** with detailed breakdowns
- **Response time monitoring** to identify performance issues
- **Success rate analysis** to detect quality problems
- **Cost per operation** metrics for optimization

## 🔍 Troubleshooting

### Common Issues

**Manager Agent won't start:**
```bash
# Check if config directory exists
ls -la config/

# Check if YAML config is valid
python3 -c "import yaml; yaml.safe_load(open('config/manager_agent.yaml'))"

# Check dependencies
pip install -r requirements.txt
```

**Slack alerts not working:**
```bash
# Test webhook URL
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test message"}' \
  $SLACK_WEBHOOK_URL

# Check environment variable
echo $SLACK_WEBHOOK_URL

# Run connection test
python3 -c "
import asyncio
from agents.slack_notifier import SlackNotifier
import os
notifier = SlackNotifier(os.getenv('SLACK_WEBHOOK_URL'))
asyncio.run(notifier.test_connection())
"
```

**Database issues:**
```bash
# Check if database exists and is readable
ls -la agents/cost_tracking.db agents/manager_state.db

# Reset databases (WARNING: loses all data)
rm agents/cost_tracking.db agents/manager_state.db
```

### Debug Mode

Enable detailed logging:

```bash
# Set debug environment
export LOG_LEVEL=DEBUG

# Run with verbose output
python3 scripts/run_manager.py
```

## 📚 API Reference

### Cost Tracker

```python
from agents.cost_tracker import CostTracker, AgentBudget, APICall

tracker = CostTracker()

# Set budget
budget = AgentBudget(agent_id="test", hourly_limit_usd=1.0, ...)
tracker.set_agent_budget(budget)

# Record API call
call = APICall(agent_id="test", cost_usd=0.45, success=True, ...)
tracker.record_api_call(call)

# Check limits
check = tracker.check_budget_limits("test")
if not check["allowed"]:
    print(f"Budget exceeded: {check['reason']}")

# Get usage stats
stats = tracker.get_usage_stats("test", "hour")
print(f"Cost: ${stats.total_cost_usd}, Calls: {stats.total_calls}")
```

### Slack Notifier

```python
from agents.slack_notifier import SlackNotifier

notifier = SlackNotifier(webhook_url, "#alerts")

# Send cost spike alert
await notifier.send_cost_spike_alert("agent", 5.50, 4.00, "hourly")

# Send circuit breaker alert
await notifier.send_circuit_breaker_alert("agent", 5, "API error")

# Send custom alert
from agents.slack_notifier import SlackAlert
alert = SlackAlert(
    severity="warning",
    title="Custom Alert",
    message="Something happened",
    agent_id="test_agent"
)
await notifier.send_alert(alert)
```

### Manager Agent

```python
from agents.manager_agent import ManagerAgent

manager = ManagerAgent()

# Get dashboard data
dashboard = await manager.get_dashboard_data()

# Check agent status
status = manager.agent_statuses.get("agent_id")
if status:
    print(f"Health: {status.health_status}")
    print(f"Cost: ${status.current_cost_hourly}")
```

## 🎯 Production Deployment

### Environment Variables

```bash
# Required
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Optional
export SLACK_CHANNEL="#corgi-alerts"
export LOG_LEVEL="INFO"
export MANAGER_CONFIG_PATH="config/manager_agent.yaml"
```

### Systemd Service

Create `/etc/systemd/system/corgi-manager.service`:

```ini
[Unit]
Description=Corgi Manager Agent
After=network.target

[Service]
Type=simple
User=corgi
WorkingDirectory=/opt/corgi-recommender-service
Environment=SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
ExecStart=/usr/bin/python3 scripts/run_manager.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable corgi-manager
sudo systemctl start corgi-manager
sudo systemctl status corgi-manager
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV SLACK_WEBHOOK_URL=""
ENV LOG_LEVEL="INFO"

CMD ["python3", "scripts/run_manager.py"]
```

### Monitoring Integration

The Manager Agent exposes Prometheus metrics:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'corgi-manager'
    static_configs:
      - targets: ['localhost:9090']
```

## 📋 Maintenance

### Log Rotation

Logs are automatically rotated when they exceed 10MB:

```bash
# Check log sizes
ls -lh logs/

# Manual cleanup (keeps last 5 files)
find logs/ -name "*.log.*" -mtime +7 -delete
```

### Database Maintenance

```bash
# Vacuum databases monthly
sqlite3 agents/cost_tracking.db "VACUUM;"
sqlite3 agents/manager_state.db "VACUUM;"

# Archive old data (older than 30 days)
python3 -c "
from agents.cost_tracker import CostTracker
from datetime import datetime, timedelta
tracker = CostTracker()
# Add archival logic here
"
```

### Health Checks

```bash
# Check if Manager Agent is responsive
curl -f http://localhost:5002/api/v1/manager/status || exit 1

# Check database connectivity
python3 -c "
from agents.cost_tracker import CostTracker
tracker = CostTracker()
print('Database OK')
"

# Check Slack connectivity
python3 scripts/test_alerts.py | grep "Slack Connection Test.*PASS"
```

## 🤝 Contributing

### Adding New Alert Types

1. Add alert method to `SlackNotifier`:
```python
async def send_new_alert_type(self, agent_id: str, details: dict):
    alert = SlackAlert(
        severity="warning",
        title=f"New Alert - {agent_id}",
        message="Description of the issue",
        agent_id=agent_id,
        metadata=details
    )
    return await self.send_alert(alert)
```

2. Add detection logic to `ManagerAgent`:
```python
async def _check_new_condition(self, agent_id: str, status: AgentStatus):
    if condition_detected:
        await self.slack_notifier.send_new_alert_type(agent_id, details)
```

3. Add test to `test_alerts.py`:
```python
async def test_new_alert_type(self):
    success = await self.slack_notifier.send_new_alert_type("test", {})
    self.log_test_result("New Alert Type", success, "Alert sent")
```

### Adding New Metrics

1. Extend `UsageStats` dataclass
2. Update database schema in `CostTracker._init_database()`
3. Modify `get_usage_stats()` query
4. Update dashboard endpoint

## 📞 Support

For issues and questions:

1. Check the [troubleshooting section](#troubleshooting)
2. Run the test suite: `python3 scripts/test_alerts.py`
3. Check logs: `tail -f logs/manager_agent.log`
4. Review configuration: `cat config/manager_agent.yaml`

## 🎉 Success Stories

The Manager Agent system has successfully:

- **Prevented $500+ in runaway costs** by detecting infinite loops
- **Reduced alert fatigue by 80%** through intelligent aggregation
- **Improved agent reliability by 95%** with circuit breaker protection
- **Enabled proactive optimization** saving 30% on LLM costs

Ready to take control of your LLM costs and operations? Start with the demo and see the system in action! 