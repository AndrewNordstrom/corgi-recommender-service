#!/usr/bin/env python3
"""
Specialized Agent Scheduler

Orchestrates the execution of specialized agents (Profiler & Optimizer, Tester)
on appropriate schedules and ensures they report to the Manager Agent.

This scheduler:
- Runs Profiler & Optimizer Agent nightly and weekly
- Runs Tester Agent on code changes and scheduled intervals
- Reports all results to Manager Agent
- Sends Slack notifications for important findings
- Handles error recovery and retry logic
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import schedule

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.profiler_optimizer_agent import ProfilerOptimizerAgent
from agents.tester_agent import TesterAgent
from agents.manager_agent import ManagerAgent
from agents.slack_notifier import SlackNotifier

logger = logging.getLogger(__name__)

class SpecializedAgentScheduler:
    """
    Scheduler for specialized agents with intelligent orchestration.
    
    Manages the execution timing and coordination of specialized agents
    to ensure optimal system performance monitoring and test maintenance.
    """
    
    def __init__(self):
        self.setup_logging()
        
        # Initialize agents
        self.profiler_agent = ProfilerOptimizerAgent()
        self.tester_agent = TesterAgent()
        self.manager_agent = ManagerAgent()
        
        # Initialize Slack notifier if webhook URL is available
        slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        if slack_webhook:
            # Disable SSL verification for macOS certificate issues
            self.slack = SlackNotifier(webhook_url=slack_webhook, verify_ssl=False)
        else:
            self.slack = None
            logger.warning("SLACK_WEBHOOK_URL not configured, Slack notifications disabled")
        
        # Execution tracking
        self.execution_history = {}
        self.last_execution_times = {}
        
        # Configuration
        self.config = {
            'profiler_schedule': {
                'nightly': '02:00',  # 2 AM daily
                'weekly_deep': 'sunday 02:30',  # Sunday 2:30 AM
                'on_demand_cooldown_hours': 4  # Minimum hours between on-demand runs
            },
            'tester_schedule': {
                'code_change_check': 300,  # Check for code changes every 5 minutes
                'daily_analysis': '03:00',  # 3 AM daily
                'coverage_check_hours': 6  # Check coverage every 6 hours
            },
            'retry_config': {
                'max_retries': 3,
                'retry_delay_minutes': 15,
                'exponential_backoff': True
            }
        }
        
        logger.info("Specialized Agent Scheduler initialized")
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create file handler
        log_file = log_dir / "specialized_agent_scheduler.log"
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
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    
    def setup_schedules(self):
        """Setup scheduled execution of agents."""
        try:
            # Profiler & Optimizer Agent schedules
            schedule.every().day.at(self.config['profiler_schedule']['nightly']).do(
                self.run_profiler_nightly
            ).tag('profiler', 'nightly')
            
            schedule.every().sunday.at("02:30").do(
                self.run_profiler_weekly_deep
            ).tag('profiler', 'weekly')
            
            # Tester Agent schedules
            schedule.every().day.at(self.config['tester_schedule']['daily_analysis']).do(
                self.run_tester_daily
            ).tag('tester', 'daily')
            
            schedule.every(6).hours.do(
                self.run_tester_coverage_check
            ).tag('tester', 'coverage')
            
            # Code change monitoring (every 5 minutes)
            schedule.every(5).minutes.do(
                self.check_code_changes_and_run_tester
            ).tag('tester', 'code_changes')
            
            # Manager Agent reporting (every hour)
            schedule.every().hour.do(
                self.report_to_manager
            ).tag('manager', 'reporting')
            
            logger.info("All agent schedules configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup schedules: {e}")
            raise
    
    def run_profiler_nightly(self):
        """Run Profiler & Optimizer Agent nightly analysis."""
        asyncio.run(self._execute_agent_with_retry(
            agent=self.profiler_agent,
            execution_type="nightly",
            description="Nightly Performance Analysis"
        ))
    
    def run_profiler_weekly_deep(self):
        """Run Profiler & Optimizer Agent weekly deep analysis."""
        asyncio.run(self._execute_agent_with_retry(
            agent=self.profiler_agent,
            execution_type="weekly_deep",
            description="Weekly Deep Performance Analysis"
        ))
    
    def run_tester_daily(self):
        """Run Tester Agent daily analysis."""
        asyncio.run(self._execute_agent_with_retry(
            agent=self.tester_agent,
            execution_type="daily",
            description="Daily Test Suite Analysis"
        ))
    
    def run_tester_coverage_check(self):
        """Run Tester Agent coverage check."""
        asyncio.run(self._execute_agent_with_retry(
            agent=self.tester_agent,
            execution_type="coverage_check",
            description="Test Coverage Analysis"
        ))
    
    def check_code_changes_and_run_tester(self):
        """Check for recent code changes and run tester if needed."""
        asyncio.run(self._check_and_run_tester_on_changes())
    
    def report_to_manager(self):
        """Report agent status to Manager Agent."""
        asyncio.run(self._report_to_manager())
    
    async def _execute_agent_with_retry(
        self, 
        agent, 
        execution_type: str, 
        description: str,
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute an agent with retry logic and comprehensive error handling."""
        
        if max_retries is None:
            max_retries = self.config['retry_config']['max_retries']
        
        agent_id = agent.agent_id
        execution_id = f"{agent_id}_{execution_type}_{int(time.time())}"
        
        logger.info(f"🚀 Starting {description} (ID: {execution_id})")
        
        # Check circuit breaker before execution
        try:
            from agents.weekly_spending_breaker import WeeklySpendingBreaker
            breaker = WeeklySpendingBreaker()
            circuit_check = breaker.should_allow_execution(agent_id)
            
            if not circuit_check['allowed']:
                error_msg = f"Circuit breaker blocked execution: {circuit_check['message']}"
                logger.warning(f"🚨 {error_msg}")
                await self._notify_circuit_breaker_block(agent_id, execution_type, circuit_check)
                return {'success': False, 'error': error_msg, 'circuit_breaker': circuit_check}
        except Exception as e:
            logger.warning(f"Circuit breaker check failed: {e} - proceeding with execution")
        
        # Check if agent is healthy before execution
        if not await agent.health_check():
            error_msg = f"Agent {agent_id} failed health check, skipping execution"
            logger.error(error_msg)
            await self._notify_execution_failure(agent_id, execution_type, error_msg)
            return {'success': False, 'error': error_msg}
        
        # Execute with retry logic
        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                
                # Execute the agent
                result = await agent.execute()
                
                execution_time = time.time() - start_time
                
                # Record successful execution
                self._record_execution(agent_id, execution_type, {
                    'execution_id': execution_id,
                    'success': True,
                    'execution_time': execution_time,
                    'attempt': attempt + 1,
                    'timestamp': datetime.now().isoformat(),
                    'result': result.data if hasattr(result, 'data') else {}
                })
                
                logger.info(f"✅ {description} completed successfully in {execution_time:.2f}s")
                
                # Report success to Manager Agent
                await self._report_agent_execution(agent_id, execution_type, result, True)
                
                # Send success notification if significant findings
                if result.success and hasattr(result, 'data'):
                    await self._notify_execution_success(agent_id, execution_type, result.data)
                
                return {
                    'success': True,
                    'execution_time': execution_time,
                    'result': result
                }
                
            except Exception as e:
                error_msg = f"Attempt {attempt + 1} failed: {str(e)}"
                logger.error(f"❌ {description} - {error_msg}")
                
                if attempt < max_retries:
                    # Calculate retry delay with exponential backoff
                    if self.config['retry_config']['exponential_backoff']:
                        delay = self.config['retry_config']['retry_delay_minutes'] * (2 ** attempt)
                    else:
                        delay = self.config['retry_config']['retry_delay_minutes']
                    
                    logger.info(f"⏳ Retrying in {delay} minutes...")
                    await asyncio.sleep(delay * 60)
                else:
                    # All retries exhausted
                    self._record_execution(agent_id, execution_type, {
                        'execution_id': execution_id,
                        'success': False,
                        'error': str(e),
                        'attempts': max_retries + 1,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Report failure to Manager Agent
                    await self._report_agent_execution(agent_id, execution_type, None, False, str(e))
                    
                    # Send failure notification
                    await self._notify_execution_failure(agent_id, execution_type, str(e))
                    
                    return {'success': False, 'error': str(e)}
    
    async def _check_and_run_tester_on_changes(self):
        """Check for code changes and run tester if significant changes detected."""
        try:
            # Check if enough time has passed since last code change check
            last_check = self.last_execution_times.get('tester_code_change', datetime.min)
            if datetime.now() - last_check < timedelta(minutes=5):
                return  # Too soon since last check
            
            # Simple git check for recent changes
            import subprocess
            result = subprocess.run([
                'git', 'log', '--since=5 minutes ago', '--name-only', '--pretty=format:'
            ], capture_output=True, text=True, cwd='.')
            
            if result.returncode == 0 and result.stdout.strip():
                # Changes detected
                changed_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                python_files = [f for f in changed_files if f.endswith('.py') and not f.startswith('tests/')]
                
                if python_files:
                    logger.info(f"📝 Code changes detected in {len(python_files)} Python files, running Tester Agent")
                    
                    await self._execute_agent_with_retry(
                        agent=self.tester_agent,
                        execution_type="code_change_triggered",
                        description=f"Test Analysis (triggered by changes in {len(python_files)} files)"
                    )
            
            self.last_execution_times['tester_code_change'] = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to check code changes: {e}")
    
    def _record_execution(self, agent_id: str, execution_type: str, execution_data: Dict[str, Any]):
        """Record execution history for tracking and analysis."""
        if agent_id not in self.execution_history:
            self.execution_history[agent_id] = []
        
        self.execution_history[agent_id].append(execution_data)
        
        # Keep only last 100 executions per agent
        if len(self.execution_history[agent_id]) > 100:
            self.execution_history[agent_id] = self.execution_history[agent_id][-100:]
        
        # Update last execution time
        self.last_execution_times[f"{agent_id}_{execution_type}"] = datetime.now()
    
    async def _report_agent_execution(
        self, 
        agent_id: str, 
        execution_type: str, 
        result: Any, 
        success: bool, 
        error: Optional[str] = None
    ):
        """Report agent execution to Manager Agent."""
        try:
            report_data = {
                'agent_id': agent_id,
                'execution_type': execution_type,
                'success': success,
                'timestamp': datetime.now().isoformat(),
                'scheduler_managed': True
            }
            
            if success and result:
                report_data['result_summary'] = {
                    'message': getattr(result, 'message', 'Execution completed'),
                    'data_keys': list(getattr(result, 'data', {}).keys()) if hasattr(result, 'data') else []
                }
            
            if error:
                report_data['error'] = error
            
            # This would integrate with Manager Agent's reporting system
            logger.info(f"📊 Reported {agent_id} execution to Manager Agent: {success}")
            
        except Exception as e:
            logger.error(f"Failed to report to Manager Agent: {e}")
    
    async def _notify_execution_success(self, agent_id: str, execution_type: str, result_data: Dict[str, Any]):
        """Send Slack notification for successful executions with significant findings."""
        try:
            # Only notify for significant findings
            should_notify = False
            message_parts = []
            
            if agent_id == "profiler_optimizer":
                issues_found = result_data.get('issues_found', 0)
                recommendations = result_data.get('recommendations', 0)
                
                if issues_found > 0:
                    should_notify = True
                    message_parts.append(f"🔍 **Performance Analysis Complete**")
                    message_parts.append(f"• Found {issues_found} performance issues")
                    message_parts.append(f"• Generated {recommendations} optimization recommendations")
                    message_parts.append(f"• Analysis type: {execution_type}")
                
            elif agent_id == "tester":
                tests_generated = result_data.get('tests_generated', 0)
                coverage_percentage = result_data.get('coverage_percentage', 0)
                missing_tests = result_data.get('missing_test_count', 0)
                
                if tests_generated > 0 or coverage_percentage < 80:
                    should_notify = True
                    message_parts.append(f"🧪 **Test Analysis Complete**")
                    message_parts.append(f"• Generated {tests_generated} new tests")
                    message_parts.append(f"• Coverage: {coverage_percentage:.1f}%")
                    message_parts.append(f"• Missing test scenarios: {missing_tests}")
            
            if should_notify and message_parts:
                message = "\n".join(message_parts)
                channel = "#corgi-performance" if agent_id == "profiler_optimizer" else "#corgi-testing"
                if self.slack:
                    await self.slack.send_message(message, channel=channel)
                
        except Exception as e:
            logger.error(f"Failed to send success notification: {e}")
    
    async def _notify_circuit_breaker_block(self, agent_id: str, execution_type: str, circuit_check: Dict[str, Any]):
        """Send notification when circuit breaker blocks execution."""
        try:
            spending = circuit_check.get('spending', {})
            message = f"""
🚨 **Circuit Breaker: Agent Execution Blocked**

**Agent**: {agent_id}
**Execution Type**: {execution_type}
**Reason**: {circuit_check['reason']}
**Message**: {circuit_check['message']}

**Weekly Spending**: ${spending.get('total_cost', 0):.2f} / ${spending.get('limit', 2.0)}
**Usage**: {spending.get('percentage_used', 0):.1f}%

**Next Steps**:
• Check spending: `python3 agents/weekly_spending_breaker.py spending`
• Resume manually: `python3 agents/weekly_spending_breaker.py resume`
• Status check: `python3 agents/weekly_spending_breaker.py status`
"""
            
            if self.slack:
                await self.slack.send_message(message, channel="#corgi-alerts")
                
        except Exception as e:
            logger.error(f"Failed to send circuit breaker notification: {e}")
    
    async def _notify_execution_failure(self, agent_id: str, execution_type: str, error: str):
        """Send Slack notification for agent execution failures."""
        try:
            agent_name = "Profiler & Optimizer" if agent_id == "profiler_optimizer" else "Tester"
            
            message = f"🚨 **{agent_name} Agent Execution Failed**\n"
            message += f"• Agent: {agent_id}\n"
            message += f"• Execution type: {execution_type}\n"
            message += f"• Error: {error[:200]}{'...' if len(error) > 200 else ''}\n"
            message += f"• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            if self.slack:
                await self.slack.send_message(message, channel="#corgi-alerts")
            
        except Exception as e:
            logger.error(f"Failed to send failure notification: {e}")
    
    async def _report_to_manager(self):
        """Generate and send periodic reports to Manager Agent."""
        try:
            # Compile execution statistics
            stats = self._compile_execution_stats()
            
            # Report to Manager Agent (this would integrate with actual Manager Agent)
            logger.info(f"📈 Hourly report: {stats}")
            
        except Exception as e:
            logger.error(f"Failed to generate manager report: {e}")
    
    def _compile_execution_stats(self) -> Dict[str, Any]:
        """Compile execution statistics for reporting."""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'agents': {}
        }
        
        for agent_id, executions in self.execution_history.items():
            recent_executions = [
                e for e in executions 
                if datetime.fromisoformat(e['timestamp']) > datetime.now() - timedelta(hours=24)
            ]
            
            successful = len([e for e in recent_executions if e.get('success', False)])
            failed = len([e for e in recent_executions if not e.get('success', True)])
            
            stats['agents'][agent_id] = {
                'executions_24h': len(recent_executions),
                'successful': successful,
                'failed': failed,
                'success_rate': successful / len(recent_executions) if recent_executions else 0,
                'last_execution': executions[-1]['timestamp'] if executions else None
            }
        
        return stats
    
    def run_scheduler(self):
        """Main scheduler loop."""
        try:
            logger.info("🕐 Starting Specialized Agent Scheduler")
            
            # Setup all schedules
            self.setup_schedules()
            
            # Send startup notification
            if self.slack:
                asyncio.run(self.slack.send_message(
                    "🚀 **Specialized Agent Scheduler Started**\n"
                    "• Profiler & Optimizer Agent: Nightly at 2:00 AM, Weekly deep analysis on Sundays\n"
                    "• Tester Agent: Daily at 3:00 AM, Coverage checks every 6 hours, Code change monitoring\n"
                    "• Manager reporting: Every hour",
                    channel="#corgi-performance"
                ))
            
            # Main scheduling loop
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            # Send error notification
            if self.slack:
                asyncio.run(self.slack.send_message(
                    f"🚨 **Specialized Agent Scheduler Error**\n"
                    f"Scheduler encountered an error: {str(e)}\n"
                    f"Manual intervention may be required.",
                    channel="#corgi-alerts"
                ))
            raise
    
    def run_on_demand(self, agent_type: str, execution_type: str = "on_demand"):
        """Run an agent on-demand for testing or immediate analysis."""
        try:
            if agent_type == "profiler":
                agent = self.profiler_agent
                description = "On-Demand Performance Analysis"
            elif agent_type == "tester":
                agent = self.tester_agent
                description = "On-Demand Test Analysis"
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            logger.info(f"🎯 Running {description} on-demand")
            
            # Create new event loop for synchronous execution
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._execute_agent_with_retry(
                    agent=agent,
                    execution_type=execution_type,
                    description=description
                ))
            finally:
                loop.close()
            
            return result
            
        except Exception as e:
            logger.error(f"On-demand execution failed: {e}")
            return {'success': False, 'error': str(e)}

def main():
    """Main entry point for the scheduler."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Specialized Agent Scheduler")
    parser.add_argument(
        '--mode', 
        choices=['schedule', 'profiler', 'tester'], 
        default='schedule',
        help='Mode: schedule (continuous), profiler (run once), tester (run once)'
    )
    parser.add_argument(
        '--execution-type',
        default='on_demand',
        help='Execution type for on-demand runs'
    )
    
    args = parser.parse_args()
    
    scheduler = SpecializedAgentScheduler()
    
    if args.mode == 'schedule':
        # Run continuous scheduler
        scheduler.run_scheduler()
    elif args.mode in ['profiler', 'tester']:
        # Run single agent on-demand
        result = scheduler.run_on_demand(args.mode, args.execution_type)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()