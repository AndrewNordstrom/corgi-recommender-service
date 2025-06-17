#!/usr/bin/env python3
"""
Manager Agent

Monitors all LLM agents to prevent runaway costs, detect issues,
and provide intelligent alerting via Slack.
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
import yaml
from contextlib import asynccontextmanager

from .cost_tracker import CostTracker, AgentBudget, APICall, UsageStats
from .slack_notifier import SlackNotifier, SlackAlert

@dataclass
class AgentStatus:
    """Current status of an agent"""
    agent_id: str
    is_active: bool
    last_seen: datetime
    health_status: str  # 'healthy', 'warning', 'critical', 'disabled'
    consecutive_failures: int
    circuit_breaker_open: bool
    current_cost_hourly: float
    current_cost_daily: float
    api_calls_last_minute: int
    last_error: Optional[str] = None

@dataclass
class Issue:
    """Represents an issue detected by the manager"""
    issue_id: str
    agent_id: str
    issue_type: str  # 'cost_spike', 'circuit_breaker', 'infinite_loop', 'budget_limit'
    severity: str    # 'critical', 'warning', 'info'
    message: str
    timestamp: datetime
    resolved: bool = False
    metadata: Optional[Dict[str, Any]] = None

class ManagerAgent:
    """Comprehensive agent monitoring and management system"""
    
    def __init__(self, config_path: str = "config/manager_agent.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Initialize components
        self.cost_tracker = CostTracker()
        self.slack_notifier = SlackNotifier(
            webhook_url=self.config['slack']['webhook_url'],
            channel=self.config['slack']['channel']
        )
        
        # State tracking
        self.agent_statuses: Dict[str, AgentStatus] = {}
        self.active_issues: Dict[str, Issue] = {}
        self.issue_counter = 0
        
        # Monitoring intervals
        self.monitoring_interval = self.config['monitoring']['check_interval_seconds']
        self.summary_interval = self.config['monitoring']['summary_interval_minutes'] * 60
        self.daily_report_hour = self.config['monitoring']['daily_report_hour']
        
        # Thresholds
        self.cost_spike_threshold = self.config['thresholds']['cost_spike_percentage']
        self.infinite_loop_calls_per_minute = self.config['thresholds']['infinite_loop_calls_per_minute']
        self.max_consecutive_failures = self.config['thresholds']['max_consecutive_failures']
        
        # Tracking
        self.last_summary_sent = datetime.now()
        self.last_daily_report = datetime.now().date()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Initialize database
        self._init_database()
        
        # Load agent budgets
        self._load_agent_budgets()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            # Create default config
            default_config = {
                'slack': {
                    'webhook_url': os.getenv('SLACK_WEBHOOK_URL', ''),
                    'channel': '#corgi-alerts'
                },
                'monitoring': {
                    'check_interval_seconds': 30,
                    'summary_interval_minutes': 60,
                    'daily_report_hour': 9
                },
                'thresholds': {
                    'cost_spike_percentage': 20.0,
                    'infinite_loop_calls_per_minute': 10,
                    'max_consecutive_failures': 5
                },
                'agent_budgets': {
                    'default': {
                        'hourly_limit_usd': 1.0,
                        'daily_limit_usd': 10.0,
                        'monthly_limit_usd': 100.0,
                        'hourly_token_limit': 10000,
                        'daily_token_limit': 100000,
                        'monthly_token_limit': 1000000,
                        'priority': 3
                    }
                }
            }
            
            self.config_path.parent.mkdir(exist_ok=True)
            with open(self.config_path, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)
            
            return default_config
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create file handler
        log_file = log_dir / "manager_agent.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)
    
    def _init_database(self):
        """Initialize SQLite database for manager state"""
        db_path = Path("agents/manager_state.db")
        db_path.parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_statuses (
                    agent_id TEXT PRIMARY KEY,
                    is_active BOOLEAN NOT NULL,
                    last_seen TEXT NOT NULL,
                    health_status TEXT NOT NULL,
                    consecutive_failures INTEGER NOT NULL,
                    circuit_breaker_open BOOLEAN NOT NULL,
                    current_cost_hourly REAL NOT NULL,
                    current_cost_daily REAL NOT NULL,
                    api_calls_last_minute INTEGER NOT NULL,
                    last_error TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS issues (
                    issue_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    issue_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN NOT NULL,
                    metadata TEXT
                )
            """)
    
    def _load_agent_budgets(self):
        """Load agent budgets from configuration"""
        self.cost_tracker.load_budgets()
        
        # Set default budgets for any agents not configured
        default_budget_config = self.config['agent_budgets']['default']
        default_budget = AgentBudget(
            agent_id='default',
            **default_budget_config
        )
        
        # Apply to any new agents discovered
        for agent_id in self.agent_statuses.keys():
            if agent_id not in self.cost_tracker.budgets:
                budget = AgentBudget(agent_id=agent_id, **default_budget_config)
                self.cost_tracker.set_agent_budget(budget)
    
    async def start_monitoring(self):
        """Start the main monitoring loop"""
        self.logger.info("Starting Manager Agent monitoring...")
        
        # Test Slack connection
        if self.config['slack']['webhook_url']:
            success = await self.slack_notifier.test_connection()
            if success:
                self.logger.info("Slack integration verified")
            else:
                self.logger.warning("Slack integration test failed")
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitoring_loop()),
            asyncio.create_task(self._summary_loop()),
            asyncio.create_task(self._daily_report_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("Shutting down Manager Agent...")
            for task in tasks:
                task.cancel()
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                await self._check_all_agents()
                await self._detect_issues()
                await self._process_alerts()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _summary_loop(self):
        """Send periodic summaries"""
        while True:
            try:
                await asyncio.sleep(self.summary_interval)
                
                # Send hourly summary
                usage_stats = self.cost_tracker.get_all_agents_usage('hour')
                if usage_stats:
                    await self.slack_notifier.send_hourly_summary(usage_stats)
                    self.last_summary_sent = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Error in summary loop: {e}")
    
    async def _daily_report_loop(self):
        """Send daily cost reports"""
        while True:
            try:
                now = datetime.now()
                
                # Check if it's time for daily report
                if (now.hour == self.daily_report_hour and 
                    now.date() > self.last_daily_report):
                    
                    cost_summary = self.cost_tracker.get_cost_summary('day')
                    optimization_suggestions = self._generate_optimization_suggestions(cost_summary)
                    
                    await self.slack_notifier.send_daily_cost_report(
                        cost_summary, optimization_suggestions
                    )
                    
                    self.last_daily_report = now.date()
                
                # Sleep until next hour
                next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                sleep_seconds = (next_hour - now).total_seconds()
                await asyncio.sleep(sleep_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in daily report loop: {e}")
                await asyncio.sleep(3600)  # Sleep 1 hour on error
    
    async def _check_all_agents(self):
        """Check status of all agents"""
        # Get all agents from cost tracker
        all_usage = self.cost_tracker.get_all_agents_usage('hour')
        
        for usage in all_usage:
            agent_id = usage.agent_id
            
            # Update agent status
            status = self._calculate_agent_status(usage)
            self.agent_statuses[agent_id] = status
            
            # Check for issues
            await self._check_agent_issues(agent_id, status, usage)
    
    def _calculate_agent_status(self, usage: UsageStats) -> AgentStatus:
        """Calculate current status for an agent"""
        agent_id = usage.agent_id
        
        # Get circuit breaker status
        circuit_check = self.cost_tracker.check_circuit_breaker(agent_id)
        circuit_open = not circuit_check["allowed"]
        
        # Calculate health status
        if circuit_open:
            health_status = 'disabled'
        elif usage.failed_calls > usage.successful_calls:
            health_status = 'critical'
        elif usage.failed_calls > 0:
            health_status = 'warning'
        else:
            health_status = 'healthy'
        
        # Get daily usage
        daily_usage = self.cost_tracker.get_usage_stats(agent_id, 'day')
        
        # Count recent API calls (last minute)
        recent_calls = self._count_recent_calls(agent_id, 60)  # 60 seconds
        
        return AgentStatus(
            agent_id=agent_id,
            is_active=usage.total_calls > 0,
            last_seen=usage.last_call or datetime.now(),
            health_status=health_status,
            consecutive_failures=self.cost_tracker.circuit_breakers.get(
                agent_id, {}
            ).get('consecutive_failures', 0),
            circuit_breaker_open=circuit_open,
            current_cost_hourly=usage.total_cost_usd,
            current_cost_daily=daily_usage.total_cost_usd,
            api_calls_last_minute=recent_calls,
            last_error=None  # Would need to track this separately
        )
    
    def _count_recent_calls(self, agent_id: str, seconds: int) -> int:
        """Count API calls in the last N seconds"""
        # This would query the cost tracker database
        # For now, return 0 as placeholder
        return 0
    
    async def _check_agent_issues(self, agent_id: str, status: AgentStatus, usage: UsageStats):
        """Check for issues with a specific agent"""
        
        # Check for cost spikes
        await self._check_cost_spike(agent_id, status, usage)
        
        # Check for infinite loops
        await self._check_infinite_loop(agent_id, status)
        
        # Check budget limits
        await self._check_budget_limits(agent_id, status)
        
        # Check circuit breaker
        await self._check_circuit_breaker(agent_id, status)
    
    async def _check_cost_spike(self, agent_id: str, status: AgentStatus, usage: UsageStats):
        """Check for cost spikes"""
        if agent_id not in self.cost_tracker.budgets:
            return
        
        budget = self.cost_tracker.budgets[agent_id]
        
        # Check hourly cost spike
        threshold = budget.hourly_limit_usd * (self.cost_spike_threshold / 100)
        if status.current_cost_hourly > threshold:
            issue_id = f"cost_spike_{agent_id}_{int(time.time())}"
            
            if issue_id not in self.active_issues:
                issue = Issue(
                    issue_id=issue_id,
                    agent_id=agent_id,
                    issue_type='cost_spike',
                    severity='warning' if status.current_cost_hourly < budget.hourly_limit_usd else 'critical',
                    message=f"Cost spike detected: ${status.current_cost_hourly:.4f} in last hour",
                    timestamp=datetime.now(),
                    metadata={
                        'current_cost': status.current_cost_hourly,
                        'threshold': threshold,
                        'budget_limit': budget.hourly_limit_usd
                    }
                )
                
                self.active_issues[issue_id] = issue
                await self.slack_notifier.send_cost_spike_alert(
                    agent_id, status.current_cost_hourly, threshold, 'hourly'
                )
    
    async def _check_infinite_loop(self, agent_id: str, status: AgentStatus):
        """Check for infinite loop patterns"""
        if status.api_calls_last_minute > self.infinite_loop_calls_per_minute:
            issue_id = f"infinite_loop_{agent_id}_{int(time.time())}"
            
            if issue_id not in self.active_issues:
                issue = Issue(
                    issue_id=issue_id,
                    agent_id=agent_id,
                    issue_type='infinite_loop',
                    severity='critical',
                    message=f"Infinite loop detected: {status.api_calls_last_minute} calls in last minute",
                    timestamp=datetime.now(),
                    metadata={
                        'calls_per_minute': status.api_calls_last_minute,
                        'threshold': self.infinite_loop_calls_per_minute
                    }
                )
                
                self.active_issues[issue_id] = issue
                await self.slack_notifier.send_infinite_loop_alert(
                    agent_id, status.api_calls_last_minute, 60
                )
    
    async def _check_budget_limits(self, agent_id: str, status: AgentStatus):
        """Check budget limits"""
        budget_check = self.cost_tracker.check_budget_limits(agent_id)
        
        if not budget_check["allowed"]:
            issue_id = f"budget_limit_{agent_id}_{budget_check['reason']}"
            
            if issue_id not in self.active_issues:
                issue = Issue(
                    issue_id=issue_id,
                    agent_id=agent_id,
                    issue_type='budget_limit',
                    severity='warning',
                    message=f"Budget limit reached: {budget_check['reason']}",
                    timestamp=datetime.now(),
                    metadata=budget_check
                )
                
                self.active_issues[issue_id] = issue
                await self.slack_notifier.send_budget_limit_alert(
                    agent_id, budget_check['reason'],
                    budget_check.get('current', 0),
                    budget_check.get('limit', 0)
                )
    
    async def _check_circuit_breaker(self, agent_id: str, status: AgentStatus):
        """Check circuit breaker status"""
        if status.circuit_breaker_open:
            issue_id = f"circuit_breaker_{agent_id}"
            
            if issue_id not in self.active_issues:
                issue = Issue(
                    issue_id=issue_id,
                    agent_id=agent_id,
                    issue_type='circuit_breaker',
                    severity='critical',
                    message=f"Circuit breaker opened due to {status.consecutive_failures} failures",
                    timestamp=datetime.now(),
                    metadata={
                        'consecutive_failures': status.consecutive_failures,
                        'last_error': status.last_error
                    }
                )
                
                self.active_issues[issue_id] = issue
                await self.slack_notifier.send_circuit_breaker_alert(
                    agent_id, status.consecutive_failures, status.last_error or "Unknown error"
                )
    
    async def _detect_issues(self):
        """Detect and aggregate issues across agents"""
        # Group similar issues
        issue_groups = self._group_issues()
        
        # Send aggregated reports for issue groups
        for group_type, issues in issue_groups.items():
            if len(issues) > 1:  # Only aggregate if multiple similar issues
                await self._send_aggregated_issue_report(group_type, issues)
    
    def _group_issues(self) -> Dict[str, List[Issue]]:
        """Group similar issues together"""
        groups = {}
        
        for issue in self.active_issues.values():
            if not issue.resolved:
                group_key = f"{issue.issue_type}_{issue.severity}"
                if group_key not in groups:
                    groups[group_key] = []
                groups[group_key].append(issue)
        
        return groups
    
    async def _send_aggregated_issue_report(self, group_type: str, issues: List[Issue]):
        """Send aggregated issue report"""
        issue_dicts = []
        for issue in issues:
            issue_dict = asdict(issue)
            issue_dict['timestamp'] = issue.timestamp.isoformat()
            issue_dicts.append(issue_dict)
        
        await self.slack_notifier.send_aggregated_issues(issue_dicts)
    
    async def _process_alerts(self):
        """Process and send any pending alerts"""
        # This could include rate limiting, deduplication, etc.
        pass
    
    def _generate_optimization_suggestions(self, cost_summary: Dict[str, Any]) -> List[str]:
        """Generate optimization suggestions based on cost data"""
        suggestions = []
        
        if cost_summary['total_cost_usd'] > 50:
            suggestions.append("Consider using Claude Haiku for simple tasks to reduce costs")
        
        if cost_summary.get('top_agents'):
            top_agent = cost_summary['top_agents'][0]
            if top_agent.total_cost_usd > cost_summary['total_cost_usd'] * 0.5:
                suggestions.append(f"Agent `{top_agent.agent_id}` accounts for >50% of costs - review its usage")
        
        # Check for high failure rates
        for agent in cost_summary.get('top_agents', []):
            if agent.total_calls > 0:
                failure_rate = agent.failed_calls / agent.total_calls
                if failure_rate > 0.2:
                    suggestions.append(f"Agent `{agent.agent_id}` has {failure_rate*100:.1f}% failure rate - investigate errors")
        
        if not suggestions:
            suggestions.append("All agents operating efficiently - no optimizations needed")
        
        return suggestions
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard endpoint"""
        cost_summary = self.cost_tracker.get_cost_summary('day')
        
        return {
            'timestamp': datetime.now().isoformat(),
            'agent_count': len(self.agent_statuses),
            'active_agents': len([s for s in self.agent_statuses.values() if s.is_active]),
            'total_daily_cost': cost_summary['total_cost_usd'],
            'total_daily_calls': cost_summary['total_calls'],
            'active_issues': len([i for i in self.active_issues.values() if not i.resolved]),
            'agent_statuses': {
                agent_id: {
                    'health_status': status.health_status,
                    'cost_hourly': status.current_cost_hourly,
                    'cost_daily': status.current_cost_daily,
                    'last_seen': status.last_seen.isoformat(),
                    'circuit_breaker_open': status.circuit_breaker_open
                }
                for agent_id, status in self.agent_statuses.items()
            },
            'recent_issues': [
                {
                    'issue_id': issue.issue_id,
                    'agent_id': issue.agent_id,
                    'issue_type': issue.issue_type,
                    'severity': issue.severity,
                    'message': issue.message,
                    'timestamp': issue.timestamp.isoformat(),
                    'resolved': issue.resolved
                }
                for issue in sorted(
                    self.active_issues.values(),
                    key=lambda x: x.timestamp,
                    reverse=True
                )[:10]  # Last 10 issues
            ]
        }

# Global manager instance
manager_agent = None

def get_manager_agent() -> ManagerAgent:
    """Get the global manager agent instance"""
    global manager_agent
    if manager_agent is None:
        manager_agent = ManagerAgent()
    return manager_agent

if __name__ == "__main__":
    # Run the manager agent
    async def main():
        manager = ManagerAgent()
        await manager.start_monitoring()
    
    asyncio.run(main()) 