# Manager Agent Testing Guide

## Overview

The Manager Agent system is designed to monitor LLM agents, prevent runaway costs, and provide intelligent alerting. This guide explains what we test and why each test is critical for production deployment.

## Testing Categories

### 1. 🧮 Cost Tracking Accuracy Tests

**What we test:**
- Pricing calculations for different Claude models (Haiku, Sonnet, Opus)
- Token counting accuracy against actual API responses
- Cost aggregation over different time periods (hourly, daily, monthly)
- Currency conversion and rounding precision

**Why it matters:**
- Inaccurate cost tracking can lead to budget overruns
- Different models have different pricing structures
- Token counting errors compound over time
- Financial reporting requires precision

**Test Examples:**
```python
# Verify pricing calculations match Anthropic's rates
haiku_cost = cost_tracker.calculate_cost("claude-3-haiku", 100, 50)
assert haiku_cost == 0.000087  # $0.25/1M input + $1.25/1M output

# Test aggregation accuracy
daily_total = cost_tracker.get_cost_summary("day")["total_cost_usd"]
hourly_sum = sum(cost_tracker.get_hourly_costs(24))
assert abs(daily_total - hourly_sum) < 0.000001
```

### 2. 💰 Budget Enforcement Tests

**What we test:**
- Hourly, daily, and monthly budget limits
- Token-based rate limiting
- Priority-based agent handling
- Budget violation detection and blocking

**Why it matters:**
- Prevents agents from exceeding allocated budgets
- Ensures fair resource allocation among agents
- Protects against unexpected cost spikes
- Enables predictable cost management

**Test Scenarios:**
- Agent within budget limits → Allow
- Agent exceeding hourly limit → Block
- High-priority agent vs low-priority → Priority handling
- Budget reset at time boundaries → Proper reset logic

### 3. 🔌 Circuit Breaker Logic Tests

**What we test:**
- Failure counting and threshold detection
- Circuit state transitions (closed → open → half-open)
- Recovery timing and automatic reset
- Cascade failure prevention

**Why it matters:**
- Prevents infinite retry loops that burn money
- Protects downstream services from overload
- Enables graceful degradation under failures
- Reduces operational noise from repeated failures

**Test Flow:**
```
Failure 1-4: Circuit CLOSED (normal operation)
Failure 5: Circuit OPEN (blocking all requests)
After timeout: Circuit HALF-OPEN (testing recovery)
Success: Circuit CLOSED (normal operation restored)
```

### 4. 📱 Slack Alert System Tests

**What we test:**
- Different alert severity levels (info, warning, critical)
- Message formatting and rich content display
- Rate limiting and alert aggregation
- Webhook connectivity and error handling

**Why it matters:**
- Ensures timely notification of issues
- Prevents alert fatigue through intelligent aggregation
- Provides actionable information for quick response
- Maintains communication during system failures

**Alert Types Tested:**
- Budget limit alerts
- Cost spike notifications
- Circuit breaker triggers
- System health summaries
- Emergency shutdown alerts

### 5. 🏃 Runaway Agent Scenario Tests

**What we test:**
- Rapid API call detection
- Budget exhaustion prevention
- Automatic agent shutdown
- Alert escalation chains

**Why it matters:**
- Prevents the #1 cause of unexpected LLM costs
- Demonstrates the system's core value proposition
- Tests emergency response procedures
- Validates real-world failure scenarios

**Simulation:**
```python
# Simulate agent making rapid expensive calls
for i in range(10):
    expensive_call = make_api_call(model="claude-3-opus", tokens=1000)
    # System should detect and stop this before budget exhaustion
```

### 6. 📈 Cost Spike Detection Tests

**What we test:**
- Usage pattern analysis and baseline establishment
- Anomaly detection algorithms
- Threshold-based alerting
- Historical comparison accuracy

**Why it matters:**
- Early warning system for cost anomalies
- Helps identify inefficient agent behavior
- Enables proactive cost management
- Supports capacity planning

**Detection Logic:**
- Establish baseline from historical usage
- Compare current usage to baseline
- Trigger alerts when usage exceeds threshold percentage
- Account for normal usage variations

### 7. 👥 Multi-Agent Monitoring Tests

**What we test:**
- Concurrent agent tracking without interference
- Resource allocation fairness
- System-wide cost aggregation
- Priority-based scheduling

**Why it matters:**
- Production systems have multiple agents
- Ensures system scales with agent count
- Validates fair resource sharing
- Tests system performance under load

**Scenarios:**
- 4 agents with different usage patterns
- Mixed priority levels
- Concurrent budget checks
- System-wide reporting accuracy

### 8. 🚨 Emergency Scenario Tests

**What we test:**
- System-wide budget breaches
- Cascade failure handling
- Emergency shutdown procedures
- Critical alert escalation

**Why it matters:**
- Tests worst-case scenario handling
- Validates emergency response procedures
- Ensures system fails safely
- Protects against catastrophic costs

**Emergency Triggers:**
- Total system cost exceeds emergency threshold
- Multiple agents simultaneously failing
- Critical infrastructure failures
- Runaway cost acceleration

### 9. 🌐 Real API Integration Tests

**What we test:**
- Live Anthropic API monitoring
- Token usage validation against actual responses
- Cost tracking accuracy with real data
- Error handling and retry logic

**Why it matters:**
- Validates system works with real API
- Ensures cost calculations match actual charges
- Tests error handling with real failure modes
- Confirms integration reliability

**Real API Tests:**
```python
# Make actual API call and track costs
response = anthropic_client.messages.create(
    model="claude-3-sonnet",
    messages=[{"role": "user", "content": "Hello"}]
)
# Verify our tracking matches actual usage
assert tracked_tokens == response.usage.input_tokens + response.usage.output_tokens
```

### 10. 📊 Dashboard & Reporting Tests

**What we test:**
- Real-time metrics display accuracy
- Historical data visualization
- Export and reporting features
- API endpoint functionality

**Why it matters:**
- Provides visibility into system operation
- Enables cost analysis and optimization
- Supports compliance and auditing
- Facilitates troubleshooting

## Testing Approaches

### Unit Tests
- Individual component functionality
- Pure function testing
- Mock external dependencies
- Fast execution for CI/CD

### Integration Tests
- Component interaction testing
- Database persistence validation
- API endpoint functionality
- Service-to-service communication

### Scenario Tests
- Real-world use case simulation
- End-to-end workflow validation
- User story verification
- Business logic testing

### Load Tests
- Performance under concurrent load
- Memory usage and scaling
- Database performance
- Alert system throughput

### Security Tests
- Budget enforcement under attack
- Input validation and sanitization
- Authentication and authorization
- Data privacy protection

### Reliability Tests
- Failure handling and recovery
- Data consistency under failures
- Service degradation behavior
- Monitoring system reliability

## Key Testing Goals

### Primary Objectives
1. **Prevent runaway LLM costs** - Core value proposition
2. **Ensure accurate cost tracking** - Financial reliability
3. **Validate budget enforcement** - Cost control
4. **Test alert reliability** - Operational awareness
5. **Verify system resilience** - Production readiness
6. **Confirm monitoring accuracy** - Trust in metrics

### Success Criteria
- ✅ Cost tracking accuracy within 0.1%
- ✅ Budget enforcement blocks 100% of violations
- ✅ Circuit breaker prevents runaway failures
- ✅ Alerts delivered within 30 seconds
- ✅ System handles 10+ concurrent agents
- ✅ Zero false negatives on cost spikes
- ✅ Recovery from all failure scenarios

## Running the Tests

### Quick Demo
```bash
# See what can be tested
python3 scripts/demo_manager_testing.py
```

### Interactive Test Suite
```bash
# Full interactive test menu
python3 scripts/test_manager_agent_scenarios.py
```

### Specific Test Categories
```bash
# Test cost tracking accuracy
python3 scripts/test_manager_agent_scenarios.py
# Choose option 1

# Test runaway agent prevention
python3 scripts/test_manager_agent_scenarios.py
# Choose option 5

# Test real API integration
python3 scripts/test_simple_api_tracking.py
```

### Automated Test Suite
```bash
# Run all tests automatically
python3 scripts/test_manager_agent_scenarios.py
# Choose 'all'
```

## Test Configuration

### Environment Setup
```bash
# Required environment variables
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional test configuration
MANAGER_AGENT_CONFIG_PATH=config/manager_agent.yaml
```

### Sensitivity Configuration
The system can be configured for different sensitivity levels:
- **Production**: Normal thresholds for real usage
- **Development**: Lower thresholds for testing
- **Ultra-sensitive**: Immediate alerts for any usage

## Interpreting Test Results

### Success Indicators
- ✅ All cost calculations match expected values
- ✅ Budget violations are properly blocked
- ✅ Alerts are sent to Slack successfully
- ✅ Circuit breakers open after threshold failures
- ✅ Runaway agents are stopped automatically

### Failure Patterns
- ❌ Cost calculations differ from expected
- ❌ Budget enforcement allows violations
- ❌ Alerts fail to send or are delayed
- ❌ Circuit breakers don't open properly
- ❌ Runaway agents continue unchecked

### Common Issues
1. **Slack webhook not configured** → Alerts fail silently
2. **API key missing** → Real API tests skipped
3. **Database permissions** → Persistence tests fail
4. **Network connectivity** → Integration tests timeout
5. **Configuration errors** → System initialization fails

## Production Deployment Checklist

Before deploying the Manager Agent system:

- [ ] All unit tests pass
- [ ] Integration tests with real API succeed
- [ ] Slack alerts are received and formatted correctly
- [ ] Budget enforcement blocks violations reliably
- [ ] Circuit breaker prevents runaway failures
- [ ] Dashboard displays accurate real-time data
- [ ] Emergency shutdown procedures tested
- [ ] Monitoring and alerting configured
- [ ] Documentation updated and accessible
- [ ] Team trained on alert response procedures

## Continuous Testing

### Automated Testing
- Run tests in CI/CD pipeline
- Nightly integration tests with real API
- Performance regression testing
- Security vulnerability scanning

### Manual Testing
- Monthly runaway agent simulations
- Quarterly emergency response drills
- Annual budget enforcement validation
- Ongoing alert effectiveness review

## Conclusion

The Manager Agent testing suite provides comprehensive validation of all system components, from basic cost calculations to complex emergency scenarios. By running these tests regularly, you can ensure the system reliably prevents runaway LLM costs while providing accurate monitoring and timely alerts.

The testing approach balances thoroughness with practicality, providing both automated tests for continuous integration and manual scenarios for validation of complex business logic. This ensures the system is production-ready and maintains reliability over time. 