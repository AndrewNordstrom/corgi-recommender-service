#!/usr/bin/env python3
"""
Weekly Spending Circuit Breaker

Monitors total LLM spending across all agents and automatically pauses
agent execution when weekly spending exceeds the configured threshold.
Provides manual override capabilities for resuming operations.
"""

import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class SpendingThreshold:
    """Weekly spending threshold configuration"""
    weekly_limit_usd: float
    warning_threshold_percent: float = 80.0  # Warn at 80% of limit
    auto_pause: bool = True
    manual_override_required: bool = True

class WeeklySpendingBreaker:
    """
    Circuit breaker that monitors weekly LLM spending and automatically
    pauses agents when spending exceeds configured thresholds.
    """
    
    def __init__(self, 
                 weekly_limit_usd: float = 2.0,
                 cost_tracker_db: str = "agents/cost_tracking.db",
                 breaker_state_file: str = "agents/weekly_breaker_state.json"):
        
        self.weekly_limit_usd = weekly_limit_usd
        self.cost_tracker_db = Path(cost_tracker_db)
        self.state_file = Path(breaker_state_file)
        self.logger = logging.getLogger(__name__)
        
        # Circuit breaker state
        self.is_paused = False
        self.pause_reason = None
        self.pause_timestamp = None
        self.manual_override_active = False
        self.last_warning_sent = None
        
        # Load existing state
        self._load_state()
        
        # Ensure state file directory exists
        self.state_file.parent.mkdir(exist_ok=True)
    
    def _load_state(self):
        """Load circuit breaker state from file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                self.is_paused = state.get('is_paused', False)
                self.pause_reason = state.get('pause_reason')
                self.pause_timestamp = state.get('pause_timestamp')
                self.manual_override_active = state.get('manual_override_active', False)
                self.last_warning_sent = state.get('last_warning_sent')
                
                if self.pause_timestamp:
                    self.pause_timestamp = datetime.fromisoformat(self.pause_timestamp)
                if self.last_warning_sent:
                    self.last_warning_sent = datetime.fromisoformat(self.last_warning_sent)
                    
                self.logger.info(f"Loaded circuit breaker state: paused={self.is_paused}")
        except Exception as e:
            self.logger.error(f"Failed to load circuit breaker state: {e}")
    
    def _save_state(self):
        """Save circuit breaker state to file"""
        try:
            state = {
                'is_paused': self.is_paused,
                'pause_reason': self.pause_reason,
                'pause_timestamp': self.pause_timestamp.isoformat() if self.pause_timestamp else None,
                'manual_override_active': self.manual_override_active,
                'last_warning_sent': self.last_warning_sent.isoformat() if self.last_warning_sent else None,
                'weekly_limit_usd': self.weekly_limit_usd,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save circuit breaker state: {e}")
    
    def get_weekly_spending(self) -> Dict[str, Any]:
        """Get total spending for the current week"""
        try:
            # Calculate start of current week (Monday)
            now = datetime.now()
            days_since_monday = now.weekday()
            week_start = now - timedelta(days=days_since_monday, 
                                       hours=now.hour, 
                                       minutes=now.minute, 
                                       seconds=now.second, 
                                       microseconds=now.microsecond)
            
            if not self.cost_tracker_db.exists():
                return {
                    'total_cost': 0.0,
                    'week_start': week_start.isoformat(),
                    'calls_count': 0,
                    'agents': {}
                }
            
            with sqlite3.connect(self.cost_tracker_db) as conn:
                # Get total spending this week
                cursor = conn.execute("""
                    SELECT 
                        SUM(cost_usd) as total_cost,
                        COUNT(*) as total_calls,
                        agent_id,
                        SUM(cost_usd) as agent_cost,
                        COUNT(*) as agent_calls
                    FROM api_calls 
                    WHERE timestamp >= ? 
                    GROUP BY agent_id
                """, (week_start.isoformat(),))
                
                results = cursor.fetchall()
                
                total_cost = 0.0
                total_calls = 0
                agents = {}
                
                for row in results:
                    if row[0]:  # total_cost is not None
                        total_cost += row[3]  # agent_cost
                        total_calls += row[4]  # agent_calls
                        agents[row[2]] = {  # agent_id
                            'cost': row[3],
                            'calls': row[4]
                        }
                
                return {
                    'total_cost': total_cost,
                    'week_start': week_start.isoformat(),
                    'calls_count': total_calls,
                    'agents': agents,
                    'limit': self.weekly_limit_usd,
                    'percentage_used': (total_cost / self.weekly_limit_usd) * 100 if self.weekly_limit_usd > 0 else 0
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get weekly spending: {e}")
            return {
                'total_cost': 0.0,
                'week_start': datetime.now().isoformat(),
                'calls_count': 0,
                'agents': {},
                'error': str(e)
            }
    
    def should_allow_execution(self, agent_id: str) -> Dict[str, Any]:
        """Check if agent execution should be allowed"""
        # If manual override is active, allow execution
        if self.manual_override_active:
            return {
                'allowed': True,
                'reason': 'manual_override_active',
                'message': 'Execution allowed due to manual override'
            }
        
        # If circuit breaker is paused, deny execution
        if self.is_paused:
            return {
                'allowed': False,
                'reason': 'circuit_breaker_paused',
                'message': f'Agent execution paused: {self.pause_reason}',
                'pause_timestamp': self.pause_timestamp.isoformat() if self.pause_timestamp else None
            }
        
        # Check current spending status
        spending = self.get_weekly_spending()
        total_cost = spending['total_cost']
        percentage_used = spending['percentage_used']
        
        # Check if limit exceeded
        if total_cost >= self.weekly_limit_usd:
            # Trigger circuit breaker
            reason = f"Weekly spending limit exceeded: ${total_cost:.2f} >= ${self.weekly_limit_usd}"
            self._trigger_pause(reason)
            return {
                'allowed': False,
                'reason': 'spending_limit_exceeded',
                'message': f'Weekly spending limit of ${self.weekly_limit_usd} exceeded',
                'spending': spending
            }
        
        # Check if warning threshold exceeded (80% by default)
        if percentage_used >= 80.0:
            self._send_warning_if_needed(spending)
        
        return {
            'allowed': True,
            'reason': 'within_limits',
            'spending': spending
        }
    
    def _trigger_pause(self, reason: str):
        """Trigger circuit breaker pause"""
        self.is_paused = True
        self.pause_reason = reason
        self.pause_timestamp = datetime.now()
        self._save_state()
        
        self.logger.critical(f"🚨 CIRCUIT BREAKER TRIGGERED: {reason}")
        
        # Send immediate notification
        self._send_critical_notification(reason)
    
    def _send_warning_if_needed(self, spending: Dict[str, Any]):
        """Send warning notification if not sent recently"""
        now = datetime.now()
        
        # Only send warning once per hour
        if (self.last_warning_sent is None or 
            now - self.last_warning_sent > timedelta(hours=1)):
            
            self.last_warning_sent = now
            self._save_state()
            
            message = (f"⚠️ Weekly LLM spending warning: "
                      f"${spending['total_cost']:.2f} / ${self.weekly_limit_usd} "
                      f"({spending['percentage_used']:.1f}%)")
            
            self.logger.warning(message)
            self._send_warning_notification(message, spending)
    
    def _send_critical_notification(self, reason: str):
        """Send critical notification when circuit breaker triggers"""
        message = f"""
🚨 **CRITICAL: LLM Agent Circuit Breaker Triggered**

**Reason**: {reason}
**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Weekly Limit**: ${self.weekly_limit_usd}

**All LLM agents have been automatically paused.**

To resume operations:
1. Review spending and adjust limits if needed
2. Run: `python3 agents/weekly_spending_breaker.py resume`
3. Or wait until next Monday for automatic reset

**Spending Details**:
{json.dumps(self.get_weekly_spending(), indent=2)}
"""
        
        self.logger.critical(message)
        print(f"\n{'='*60}")
        print("🚨 CRITICAL: LLM CIRCUIT BREAKER TRIGGERED")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
        
        # Send Slack notification
        self._send_slack_alert(
            title="🚨 LLM Circuit Breaker Triggered",
            message=f"Weekly spending limit of ${self.weekly_limit_usd} exceeded. All agents paused.",
            severity="critical"
        )
    
    def _send_warning_notification(self, message: str, spending: Dict[str, Any]):
        """Send warning notification"""
        detailed_message = f"""
⚠️ **LLM Spending Warning**

{message}

**Spending by Agent**:
"""
        for agent_id, agent_data in spending.get('agents', {}).items():
            detailed_message += f"• {agent_id}: ${agent_data['cost']:.2f} ({agent_data['calls']} calls)\n"
        
        self.logger.warning(detailed_message)
        print(f"\n⚠️ WARNING: {message}")
        
        # Send Slack warning
        self._send_slack_alert(
            title="⚠️ LLM Spending Warning",
            message=message,
            severity="warning"
        )
    
    def _send_slack_alert(self, title: str, message: str, severity: str):
        """Send Slack alert for circuit breaker events"""
        try:
            import os
            from agents.slack_notifier import SlackNotifier, SlackAlert
            
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            if not webhook_url:
                return  # No Slack configured
            
            notifier = SlackNotifier(webhook_url=webhook_url, verify_ssl=False)
            
            alert = SlackAlert(
                severity=severity,
                title=title,
                message=message,
                agent_id="circuit_breaker",
                timestamp=datetime.now()
            )
            
            # Use asyncio to send the alert
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(notifier.send_alert(alert))
            except RuntimeError:
                # No event loop running, create one
                asyncio.run(notifier.send_alert(alert))
                
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
    
    def manual_resume(self, override_reason: str = "Manual override by user"):
        """Manually resume agent execution with override"""
        self.is_paused = False
        self.manual_override_active = True
        self.pause_reason = None
        self.pause_timestamp = None
        self._save_state()
        
        message = f"✅ Circuit breaker manually resumed: {override_reason}"
        self.logger.info(message)
        print(message)
        
        return {
            'success': True,
            'message': message,
            'override_active': True
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        spending = self.get_weekly_spending()
        
        return {
            'is_paused': self.is_paused,
            'pause_reason': self.pause_reason,
            'pause_timestamp': self.pause_timestamp.isoformat() if self.pause_timestamp else None,
            'manual_override_active': self.manual_override_active,
            'weekly_limit_usd': self.weekly_limit_usd,
            'spending': spending,
            'next_reset': self._get_next_monday().isoformat()
        }
    
    def _get_next_monday(self) -> datetime:
        """Get the next Monday (when the weekly cycle resets)"""
        now = datetime.now()
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:  # If today is Monday
            days_until_monday = 7
        
        next_monday = now + timedelta(days=days_until_monday)
        return next_monday.replace(hour=0, minute=0, second=0, microsecond=0)

# Convenience functions for CLI usage
def get_breaker_status():
    """Get current circuit breaker status (CLI helper)"""
    breaker = WeeklySpendingBreaker()
    status = breaker.get_status()
    print(json.dumps(status, indent=2))
    return status

def manual_resume():
    """Manually resume agents (CLI helper)"""
    breaker = WeeklySpendingBreaker()
    result = breaker.manual_resume()
    return result

def check_spending():
    """Check current spending (CLI helper)"""
    breaker = WeeklySpendingBreaker()
    spending = breaker.get_weekly_spending()
    print(f"Weekly spending: ${spending['total_cost']:.2f} / ${breaker.weekly_limit_usd}")
    print(f"Percentage used: {spending['percentage_used']:.1f}%")
    return spending

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "status":
            get_breaker_status()
        elif command == "resume":
            manual_resume()
        elif command == "spending":
            check_spending()
        else:
            print("Usage: python3 weekly_spending_breaker.py [status|resume|spending]")
    else:
        print("Usage: python3 weekly_spending_breaker.py [status|resume|spending]") 