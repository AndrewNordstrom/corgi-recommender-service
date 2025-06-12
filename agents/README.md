# 🐕 Corgi Agent System

**Cutting-Edge Multi-Agent Website Management System**

A comprehensive, intelligent agent ecosystem that ensures your Corgi Recommender Service website meets all requirements and operates at peak performance.

## 🚀 Quick Start

```bash
# Start the complete agent system
cd agents
python3 agent_launcher.py
```

Access the system:
- **Agent Dashboard**: http://localhost:5001
- **Main Website**: http://localhost:3000
- **API Endpoint**: http://localhost:9999

## 🤖 Intelligent Agents

### 1. **Website Health Agent** 🌐
- **Purpose**: Monitors website performance and availability
- **Features**:
  - Real-time endpoint monitoring
  - Response time analysis
  - SSL certificate validation
  - Uptime tracking
  - Error rate monitoring
- **Thresholds**: 
  - Response time: <2.0s
  - Availability: >99%
  - Error rate: <5%

### 2. **Security Agent** 🔒
- **Purpose**: Comprehensive security monitoring and threat detection
- **Features**:
  - Vulnerability scanning
  - Dependency security checks
  - Security header validation
  - Port scanning
  - SSL/TLS certificate monitoring
  - Unauthorized access detection
- **Checks**: 
  - NPM audit for vulnerabilities
  - Security headers (CSP, HSTS, etc.)
  - SSL certificate expiration

### 3. **Performance Optimization Agent** ⚡
- **Purpose**: Automatically optimizes website performance
- **Features**:
  - System resource monitoring
  - Database query optimization
  - Frontend asset optimization
  - Cache management
  - Memory and CPU optimization
- **Targets**:
  - Response time: <1.0s
  - CPU usage: <70%
  - Memory usage: <80%

### 4. **User Experience Agent** 👥
- **Purpose**: Monitors and improves user experience metrics
- **Features**:
  - Core Web Vitals analysis
  - Accessibility compliance checking
  - Mobile optimization
  - User behavior analytics
  - Interface optimization
- **Metrics**:
  - Largest Contentful Paint (LCP)
  - First Input Delay (FID)
  - Cumulative Layout Shift (CLS)

### 5. **Content Management Agent** 📝
- **Purpose**: Manages content quality and freshness
- **Features**:
  - Content freshness monitoring
  - SEO optimization
  - Link validation
  - Image optimization
  - Documentation updates
- **Automation**:
  - Outdated content detection
  - Broken link identification
  - SEO improvements

### 6. **ML Model Agent** 🧠
- **Purpose**: Optimizes machine learning model performance
- **Features**:
  - Model performance monitoring
  - Drift detection
  - A/B testing coordination
  - Model selection optimization
  - Performance metric tracking
- **Models Managed**:
  - Collaborative Filtering
  - Content-Based
  - Hybrid Ensemble
  - Neural Collaborative
  - Multi-Armed Bandit
  - Graph Neural Network

### 7. **Deployment Agent** 🚀
- **Purpose**: Manages infrastructure and deployment operations
- **Features**:
  - Infrastructure monitoring
  - Auto-scaling management
  - Backup operations
  - Health check coordination
  - Resource optimization
- **Capabilities**:
  - Automated backups
  - Scaling decisions
  - Resource allocation

## 📊 Web Dashboard

The cutting-edge web dashboard provides:

### Real-Time Monitoring
- **System Overview**: Total agents, active status, error tracking
- **Agent Status**: Individual agent health and activity
- **Performance Metrics**: Response times, success rates, task completion
- **Recent Actions**: Live feed of agent activities

### Interactive Features
- **Manual Agent Cycles**: Trigger immediate system checks
- **Configuration Management**: Adjust agent settings
- **Report Export**: Download comprehensive system reports
- **Auto-Refresh**: 30-second updates with pause/resume

### Visual Design
- Modern, responsive interface
- Color-coded status indicators
- Interactive charts and metrics
- Mobile-friendly layout

## ⚙️ Configuration

### Configuration File
```yaml
# agents/config.yaml
log_level: "INFO"
dashboard_port: 5001
data_retention_days: 90

website_health:
  enabled: true
  execution_interval: 300
  response_time_threshold: 2.0

security:
  enabled: true
  vulnerability_scan_interval: 1800
  dependency_check: true

performance:
  enabled: true
  cpu_threshold: 70.0
  memory_threshold: 80.0

# ... additional agent configurations
```

### Environment Variables
```bash
# Override configuration via environment
export AGENT_LOG_LEVEL=DEBUG
export AGENT_DASHBOARD_PORT=5001
export AGENT_DATA_RETENTION_DAYS=90
export AGENT_NOTIFICATION_WEBHOOK=https://your-webhook.com
```

### Agent-Specific Configuration
Each agent can be individually configured:
- **Execution intervals**
- **Performance thresholds**
- **Alert conditions**
- **Optimization targets**

## 🛠️ Architecture

### System Components
```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                Agent Scheduler                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐     │
│  │ Website   │ │ Security  │ │Performance│ │    UX     │     │
│  │  Health   │ │   Agent   │ │   Agent   │ │  Agent    │     │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘     │
│                                                                 │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐                   │
│  │ Content   │ │ ML Model  │ │Deployment │                   │
│  │   Agent   │ │   Agent   │ │   Agent   │                   │
│  └───────────┘ └───────────┘ └───────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │     Web Dashboard       │
                    │    (Port 5001)         │
                    └─────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │     SQLite Database     │
                    │   (agents/agent_data.db)│
                    └─────────────────────────┘
```

### Data Flow
1. **Agent Execution**: Agents run on scheduled intervals
2. **Action Logging**: All actions stored in SQLite database
3. **Metrics Collection**: Performance data aggregated
4. **Dashboard Updates**: Real-time data via REST API
5. **Alert Generation**: Notifications for critical issues

### Integration
- **Seamless Integration**: Works alongside existing `make dev` workflow
- **Port Management**: Integrates with `manage_server_port.sh`
- **Monitoring Bridge**: Connects with existing health monitoring
- **Non-Intrusive**: Runs in parallel without affecting main services

## 📈 Monitoring & Alerting

### Automatic Monitoring
- **Continuous Health Checks**: Every 5 minutes
- **Performance Monitoring**: Real-time metrics
- **Security Scans**: Every 30 minutes
- **Resource Monitoring**: CPU, memory, disk usage

### Alert Conditions
- High response times (>2s)
- Security vulnerabilities detected
- Resource usage thresholds exceeded
- Service failures or errors
- Model performance degradation

### Notification Options
- **Web Dashboard**: Real-time visual alerts
- **Webhook Integration**: Custom notification endpoints
- **Email Notifications**: Configurable email alerts
- **Log Files**: Detailed logging for all events

## 🔧 Development & Customization

### Adding New Agents
```python
from agents.core_agent_system import BaseAgent, AgentAction

class CustomAgent(BaseAgent):
    def __init__(self):
        super().__init__("custom_agent", "Custom Agent")
    
    async def execute(self):
        # Your agent logic here
        action = AgentAction(
            agent_id=self.agent_id,
            action_type="custom_check",
            description="Performed custom check",
            timestamp=datetime.now(),
            result="success"
        )
        return [action]
    
    async def health_check(self):
        return True
```

### Custom Configurations
```python
@dataclass
class CustomAgentConfig(AgentConfig):
    custom_threshold: float = 1.0
    custom_enabled: bool = True
```

### Database Schema
```sql
-- Agent actions table
CREATE TABLE agent_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT,
    action_type TEXT,
    description TEXT,
    timestamp TEXT,
    result TEXT,
    metadata TEXT
);

-- Agent metrics table
CREATE TABLE agent_metrics (
    agent_id TEXT PRIMARY KEY,
    tasks_completed INTEGER,
    errors_encountered INTEGER,
    average_response_time REAL,
    performance_score REAL,
    last_activity TEXT
);
```

## 🚦 Usage Examples

### Manual Agent Execution
```python
from agents.core_agent_system import AgentOrchestrator

orchestrator = AgentOrchestrator()
await orchestrator.run_agent_cycle()
```

### Configuration Updates
```python
from agents.agent_config import update_agent_config

update_agent_config('website_health', {
    'response_time_threshold': 1.5,
    'execution_interval': 180
})
```

### Custom Monitoring
```bash
# Monitor specific metrics
curl http://localhost:5001/api/status
curl http://localhost:5001/api/recent-actions
```

## 📊 Performance Impact

### Resource Usage
- **CPU**: <5% additional usage
- **Memory**: ~100MB for all agents
- **Disk**: Minimal (logs + database)
- **Network**: Lightweight health checks only

### Benefits
- **Proactive Issue Detection**: Catch problems before users
- **Automated Optimization**: Continuous performance improvements
- **Security Hardening**: Real-time vulnerability detection
- **User Experience**: Better UX through continuous monitoring
- **ML Optimization**: Better recommendation performance

## 🔄 Integration with Existing Workflow

### Compatibility
- **Works with `make dev`**: Full compatibility with existing development workflow
- **Port Management**: Integrates with `manage_server_port.sh`
- **Monitoring Bridge**: Connects with existing health monitoring
- **Non-Disruptive**: Runs in parallel without conflicts

### Workflow Enhancement
```bash
# Start main development workflow
make dev

# In parallel, start agent system
cd agents && python3 agent_launcher.py
```

## 🛡️ Security & Privacy

### Data Security
- **Local Storage**: All data stored locally in SQLite
- **No External Connections**: Except for configured webhooks
- **Encrypted Communications**: HTTPS for all external requests
- **Access Control**: Dashboard requires local access

### Privacy Protection
- **No User Data Collection**: Monitors system, not user behavior
- **Anonymized Metrics**: No personally identifiable information
- **Configurable Logging**: Control what gets logged

## 📚 API Reference

### REST Endpoints
- `GET /api/status` - System status overview
- `GET /api/recent-actions` - Recent agent actions
- `POST /api/run-cycle` - Trigger manual agent cycle
- `GET /api/export-report` - Export system report

### Response Formats
```json
{
  "total_agents": 7,
  "active_agents": 7,
  "error_agents": 0,
  "agents": {
    "health_monitor": {
      "name": "Website Health Agent",
      "status": "idle",
      "priority": "CRITICAL",
      "metrics": {
        "tasks_completed": 42,
        "performance_score": 98.5
      }
    }
  }
}
```

## 🔄 Continuous Improvement

The Corgi Agent System is designed for continuous evolution:

### Adaptive Learning
- **Performance Pattern Recognition**: Learns from historical data
- **Threshold Optimization**: Automatically adjusts based on patterns
- **Predictive Analytics**: Anticipates issues before they occur

### Self-Optimization
- **Resource Usage**: Optimizes its own resource consumption
- **Execution Timing**: Adjusts scheduling based on system load
- **Alert Tuning**: Reduces false positives over time

---

## 🎉 Get Started Now!

Transform your Corgi Recommender Service into a self-managing, optimized, and secure application with cutting-edge agent technology.

```bash
cd agents
python3 agent_launcher.py
```

**Experience the future of automated website management!** 🚀