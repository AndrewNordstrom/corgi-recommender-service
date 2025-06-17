#!/usr/bin/env python3
"""
Slack Notifier Module

Sends intelligent alerts and reports to Slack with rich formatting
and smart aggregation of issues.
"""

import asyncio
import json
import logging
import aiohttp
import ssl
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SlackAlert:
    """Represents a Slack alert"""
    severity: str  # 'critical', 'warning', 'info'
    title: str
    message: str
    agent_id: Optional[str] = None
    cost_impact: Optional[float] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class SlackNotifier:
    """Comprehensive Slack notification system"""
    
    SEVERITY_COLORS = {
        'critical': '#FF0000',  # Red
        'warning': '#FFA500',   # Orange
        'info': '#36A64F'       # Green
    }
    
    SEVERITY_EMOJIS = {
        'critical': '🚨',
        'warning': '⚠️',
        'info': 'ℹ️'
    }
    
    def __init__(self, webhook_url: str, channel: str = "#corgi-alerts", verify_ssl: bool = True):
        self.webhook_url = webhook_url
        self.channel = channel
        self.verify_ssl = verify_ssl
        self.logger = logging.getLogger(__name__)
        self.alert_history: List[SlackAlert] = []
        self.last_summary_sent = datetime.now()
        
        # Create SSL context
        if not verify_ssl:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
            self.logger.warning("SSL verification disabled for Slack notifications")
        else:
            self.ssl_context = None
        
    async def send_alert(self, alert: SlackAlert) -> bool:
        """Send an immediate alert to Slack"""
        try:
            blocks = self._build_alert_blocks(alert)
            
            payload = {
                "channel": self.channel,
                "username": "Corgi Manager",
                "icon_emoji": ":dog:",
                "blocks": blocks
            }
            
            connector = aiohttp.TCPConnector(ssl=self.ssl_context) if not self.verify_ssl else None
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Alert sent successfully: {alert.title}")
                        self.alert_history.append(alert)
                        return True
                    else:
                        self.logger.error(f"Failed to send alert: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error sending Slack alert: {e}")
            return False
    
    def _build_alert_blocks(self, alert: SlackAlert) -> List[Dict]:
        """Build Slack blocks for an alert"""
        emoji = self.SEVERITY_EMOJIS.get(alert.severity, '📢')
        color = self.SEVERITY_COLORS.get(alert.severity, '#36A64F')
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {alert.title}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": alert.message
                }
            }
        ]
        
        # Add context fields
        fields = []
        
        if alert.agent_id:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Agent:*\n{alert.agent_id}"
            })
        
        if alert.cost_impact:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Cost Impact:*\n${alert.cost_impact:.4f}"
            })
        
        if alert.timestamp:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Time:*\n{alert.timestamp.strftime('%H:%M:%S')}"
            })
        
        fields.append({
            "type": "mrkdwn",
            "text": f"*Severity:*\n{alert.severity.upper()}"
        })
        
        if fields:
            blocks.append({
                "type": "section",
                "fields": fields
            })
        
        # Add metadata if present
        if alert.metadata:
            metadata_text = "\n".join([
                f"• {k}: {v}" for k, v in alert.metadata.items()
            ])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Additional Details:*\n```{metadata_text}```"
                }
            })
        
        # Add divider
        blocks.append({"type": "divider"})
        
        return blocks
    
    async def send_cost_spike_alert(self, agent_id: str, current_cost: float, 
                                  threshold: float, period: str) -> bool:
        """Send alert for cost spike"""
        percentage_increase = ((current_cost - threshold) / threshold) * 100
        
        alert = SlackAlert(
            severity='critical' if percentage_increase > 50 else 'warning',
            title=f"Cost Spike Detected - {agent_id}",
            message=f"Agent `{agent_id}` has exceeded cost threshold by {percentage_increase:.1f}%",
            agent_id=agent_id,
            cost_impact=current_cost - threshold,
            timestamp=datetime.now(),
            metadata={
                "current_cost": f"${current_cost:.4f}",
                "threshold": f"${threshold:.4f}",
                "period": period,
                "percentage_over": f"{percentage_increase:.1f}%"
            }
        )
        
        return await self.send_alert(alert)
    
    async def send_circuit_breaker_alert(self, agent_id: str, failure_count: int,
                                       last_error: str) -> bool:
        """Send alert when circuit breaker opens"""
        alert = SlackAlert(
            severity='critical',
            title=f"Circuit Breaker Opened - {agent_id}",
            message=f"Agent `{agent_id}` has been disabled due to {failure_count} consecutive failures",
            agent_id=agent_id,
            timestamp=datetime.now(),
            metadata={
                "failure_count": failure_count,
                "last_error": last_error[:200] + "..." if len(last_error) > 200 else last_error,
                "action": "Agent disabled for 5 minutes"
            }
        )
        
        return await self.send_alert(alert)
    
    async def send_budget_limit_alert(self, agent_id: str, limit_type: str,
                                    current: float, limit: float) -> bool:
        """Send alert when budget limit is reached"""
        alert = SlackAlert(
            severity='warning',
            title=f"Budget Limit Reached - {agent_id}",
            message=f"Agent `{agent_id}` has reached its {limit_type} budget limit",
            agent_id=agent_id,
            timestamp=datetime.now(),
            metadata={
                "limit_type": limit_type,
                "current_usage": f"${current:.4f}" if 'cost' in limit_type else f"{int(current)} tokens",
                "limit": f"${limit:.4f}" if 'cost' in limit_type else f"{int(limit)} tokens",
                "utilization": f"{(current/limit)*100:.1f}%"
            }
        )
        
        return await self.send_alert(alert)
    
    async def send_infinite_loop_alert(self, agent_id: str, call_count: int,
                                     time_window: int) -> bool:
        """Send alert for potential infinite loop"""
        alert = SlackAlert(
            severity='critical',
            title=f"Infinite Loop Detected - {agent_id}",
            message=f"Agent `{agent_id}` made {call_count} API calls in {time_window} seconds - possible infinite loop",
            agent_id=agent_id,
            timestamp=datetime.now(),
            metadata={
                "call_count": call_count,
                "time_window_seconds": time_window,
                "calls_per_second": f"{call_count/time_window:.2f}",
                "action": "Agent temporarily disabled"
            }
        )
        
        return await self.send_alert(alert)
    
    async def send_hourly_summary(self, usage_stats: List[Any]) -> bool:
        """Send hourly usage summary"""
        if not usage_stats:
            return True
        
        total_cost = sum(stat.total_cost_usd for stat in usage_stats)
        total_calls = sum(stat.total_calls for stat in usage_stats)
        total_failures = sum(stat.failed_calls for stat in usage_stats)
        
        success_rate = ((total_calls - total_failures) / total_calls * 100) if total_calls > 0 else 0
        
        # Build summary blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Hourly Agent Summary"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Cost:*\n${total_cost:.4f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*API Calls:*\n{total_calls}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Success Rate:*\n{success_rate:.1f}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Active Agents:*\n{len(usage_stats)}"
                    }
                ]
            }
        ]
        
        # Add top agents by cost
        top_agents = sorted(usage_stats, key=lambda x: x.total_cost_usd, reverse=True)[:3]
        if top_agents:
            agent_text = "\n".join([
                f"• `{agent.agent_id}`: ${agent.total_cost_usd:.4f} ({agent.total_calls} calls)"
                for agent in top_agents
            ])
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Top Agents by Cost:*\n{agent_text}"
                }
            })
        
        blocks.append({"type": "divider"})
        
        payload = {
            "channel": self.channel,
            "username": "Corgi Manager",
            "icon_emoji": ":dog:",
            "blocks": blocks
        }
        
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context) if not self.verify_ssl else None
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info("Hourly summary sent successfully")
                        return True
                    else:
                        self.logger.error(f"Failed to send hourly summary: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"Error sending hourly summary: {e}")
            return False
    
    async def send_daily_cost_report(self, cost_summary: Dict[str, Any],
                                   optimization_suggestions: List[str]) -> bool:
        """Send comprehensive daily cost report"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📈 Daily Cost Report"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Total Daily Spend:* ${cost_summary['total_cost_usd']:.4f}\n"
                           f"*Total API Calls:* {cost_summary['total_calls']:,}\n"
                           f"*Total Tokens:* {cost_summary['total_tokens']:,}\n"
                           f"*Active Agents:* {cost_summary['agent_count']}"
                }
            }
        ]
        
        # Add top agents
        if cost_summary.get('top_agents'):
            agent_details = []
            for agent in cost_summary['top_agents']:
                success_rate = (agent.successful_calls / agent.total_calls * 100) if agent.total_calls > 0 else 0
                agent_details.append(
                    f"• `{agent.agent_id}`: ${agent.total_cost_usd:.4f} "
                    f"({agent.total_calls} calls, {success_rate:.1f}% success)"
                )
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Top Agents by Cost:*\n" + "\n".join(agent_details)
                }
            })
        
        # Add optimization suggestions
        if optimization_suggestions:
            suggestions_text = "\n".join([f"• {suggestion}" for suggestion in optimization_suggestions])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💡 Optimization Suggestions:*\n{suggestions_text}"
                }
            })
        
        blocks.append({"type": "divider"})
        
        payload = {
            "channel": self.channel,
            "username": "Corgi Manager",
            "icon_emoji": ":dog:",
            "blocks": blocks
        }
        
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context) if not self.verify_ssl else None
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info("Daily cost report sent successfully")
                        return True
                    else:
                        self.logger.error(f"Failed to send daily report: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"Error sending daily report: {e}")
            return False
    
    async def send_aggregated_issues(self, issues: List[Dict[str, Any]]) -> bool:
        """Send aggregated issues with TLDR summaries"""
        if not issues:
            return True
        
        # Group issues by type
        issue_groups = {}
        for issue in issues:
            issue_type = issue.get('type', 'unknown')
            if issue_type not in issue_groups:
                issue_groups[issue_type] = []
            issue_groups[issue_type].append(issue)
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔍 Aggregated Issues Report"
                }
            }
        ]
        
        for issue_type, group_issues in issue_groups.items():
            count = len(group_issues)
            
            # Create TLDR for this group
            tldr = self._generate_issue_tldr(group_issues)
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{issue_type.title()} Issues ({count}):*\n{tldr}"
                }
            })
            
            # Add details for critical issues
            critical_issues = [issue for issue in group_issues if issue.get('severity') == 'critical']
            if critical_issues:
                details = "\n".join([
                    f"• `{issue.get('agent_id', 'unknown')}`: {issue.get('message', 'No details')[:100]}..."
                    for issue in critical_issues[:3]  # Show top 3
                ])
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Critical Details:*\n{details}"
                    }
                })
        
        blocks.append({"type": "divider"})
        
        payload = {
            "channel": self.channel,
            "username": "Corgi Manager",
            "icon_emoji": ":dog:",
            "blocks": blocks
        }
        
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context) if not self.verify_ssl else None
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info("Aggregated issues report sent successfully")
                        return True
                    else:
                        self.logger.error(f"Failed to send issues report: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"Error sending issues report: {e}")
            return False
    
    def _generate_issue_tldr(self, issues: List[Dict[str, Any]]) -> str:
        """Generate a TLDR summary for a group of issues"""
        if not issues:
            return "No issues to report."
        
        # Simple aggregation logic (in production, this could use Claude Haiku)
        agent_counts = {}
        error_types = {}
        
        for issue in issues:
            agent_id = issue.get('agent_id', 'unknown')
            agent_counts[agent_id] = agent_counts.get(agent_id, 0) + 1
            
            error_type = issue.get('error_type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Build TLDR
        tldr_parts = []
        
        # Most affected agent
        if agent_counts:
            top_agent = max(agent_counts.items(), key=lambda x: x[1])
            tldr_parts.append(f"Most affected: `{top_agent[0]}` ({top_agent[1]} issues)")
        
        # Most common error
        if error_types:
            top_error = max(error_types.items(), key=lambda x: x[1])
            tldr_parts.append(f"Common error: {top_error[0]} ({top_error[1]} occurrences)")
        
        return " | ".join(tldr_parts) if tldr_parts else "Multiple issues detected"
    
    async def send_message(self, message: str, channel: str = None) -> bool:
        """Send a simple message to Slack (compatibility method)"""
        alert = SlackAlert(
            severity='info',
            title='Corgi Notification',
            message=message,
            timestamp=datetime.now()
        )
        
        # Override channel if specified
        if channel:
            original_channel = self.channel
            self.channel = channel
            try:
                result = await self.send_alert(alert)
                return result
            finally:
                self.channel = original_channel
        else:
            return await self.send_alert(alert)
    
    async def test_connection(self) -> bool:
        """Test Slack webhook connection"""
        test_alert = SlackAlert(
            severity='info',
            title='Corgi Manager Test',
            message='This is a test message to verify Slack integration is working.',
            timestamp=datetime.now()
        )
        
        return await self.send_alert(test_alert)

# Example usage and testing
if __name__ == "__main__":
    import os
    
    # Test with environment variable
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        print("Please set SLACK_WEBHOOK_URL environment variable")
        exit(1)
    
    async def test_notifications():
        notifier = SlackNotifier(webhook_url)
        
        # Test connection
        print("Testing connection...")
        success = await notifier.test_connection()
        print(f"Connection test: {'✓' if success else '✗'}")
        
        # Test cost spike alert
        print("Testing cost spike alert...")
        await notifier.send_cost_spike_alert("test_agent", 5.50, 4.00, "hourly")
        
        # Test circuit breaker alert
        print("Testing circuit breaker alert...")
        await notifier.send_circuit_breaker_alert("test_agent", 5, "API rate limit exceeded")
        
        print("All tests completed!")
    
    # Run tests
    asyncio.run(test_notifications()) 