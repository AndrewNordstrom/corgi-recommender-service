#!/usr/bin/env python3
"""
Manager Agent Audit Module

Provides audit functionality for the Manager Agent to perform periodic
system health checks, agent analysis, and automated reporting.
"""

import asyncio
import json
import logging
import os
import sys
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.slack_notifier import SlackNotifier

class ManagerAgentAudit:
    """Audit functionality for Manager Agent"""
    
    def __init__(self, slack_notifier: Optional[SlackNotifier] = None):
        self.logger = logging.getLogger(__name__)
        self.slack_notifier = slack_notifier
        self.agents_dir = project_root / "agents"
        self.config_dir = project_root / "config"
        self.reports_dir = project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Load agent registry
        self.agent_registry = self.load_agent_registry()
        
    def load_agent_registry(self) -> Dict[str, Any]:
        """Load the agent registry configuration"""
        registry_path = self.config_dir / "agent_registry.yaml"
        
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            self.logger.warning("Agent registry not found, using empty registry")
            return {"agents": {}}
    
    async def run_full_audit(self) -> Dict[str, Any]:
        """Run a comprehensive audit of all agents"""
        self.logger.info("Starting full agent audit...")
        
        audit_results = {
            "timestamp": datetime.now().isoformat(),
            "audit_type": "full_system_audit",
            "results": {}
        }
        
        # Run health check script
        health_results = await self.run_health_check()
        audit_results["results"]["health_check"] = health_results
        
        # Check agent status
        status_results = await self.check_agent_status()
        audit_results["results"]["agent_status"] = status_results
        
        # Security audit
        security_results = await self.run_security_audit()
        audit_results["results"]["security_audit"] = security_results
        
        # Cost analysis
        cost_results = await self.analyze_cost_risks()
        audit_results["results"]["cost_analysis"] = cost_results
        
        # Integration check
        integration_results = await self.check_integrations()
        audit_results["results"]["integration_check"] = integration_results
        
        # Generate recommendations
        recommendations = self.generate_recommendations(audit_results)
        audit_results["recommendations"] = recommendations
        
        # Save audit report
        report_path = await self.save_audit_report(audit_results)
        audit_results["report_path"] = str(report_path)
        
        # Send Slack notification if configured
        if self.slack_notifier:
            await self.send_audit_notification(audit_results)
        
        self.logger.info(f"Full audit completed. Report saved to: {report_path}")
        return audit_results
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run the agent health check script"""
        self.logger.info("Running agent health check...")
        
        try:
            # Run the health check script
            result = subprocess.run([
                sys.executable, 
                str(project_root / "scripts" / "agent_health_check.py")
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Try to find the latest health check report
                latest_report = self.find_latest_health_report()
                if latest_report:
                    with open(latest_report, 'r') as f:
                        health_data = json.load(f)
                    return {
                        "status": "success",
                        "data": health_data,
                        "report_file": str(latest_report)
                    }
                else:
                    return {
                        "status": "success",
                        "data": {"summary": {"system_health_score": "unknown"}},
                        "stdout": result.stdout
                    }
            else:
                return {
                    "status": "failed",
                    "error": result.stderr,
                    "stdout": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": "Health check script timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def find_latest_health_report(self) -> Optional[Path]:
        """Find the most recent health check report"""
        report_files = list(self.reports_dir.glob("agent_health_check_*.json"))
        if report_files:
            return max(report_files, key=lambda f: f.stat().st_mtime)
        return None
    
    async def check_agent_status(self) -> Dict[str, Any]:
        """Check the operational status of all agents"""
        self.logger.info("Checking agent operational status...")
        
        agent_status = {
            "total_agents": 0,
            "operational": 0,
            "broken": 0,
            "high_risk": 0,
            "details": {}
        }
        
        if "agents" in self.agent_registry:
            for agent_name, agent_info in self.agent_registry["agents"].items():
                agent_status["total_agents"] += 1
                
                status = agent_info.get("status", "unknown")
                if status == "operational":
                    agent_status["operational"] += 1
                elif status == "broken":
                    agent_status["broken"] += 1
                
                # Check for high risk indicators
                issues = agent_info.get("issues", [])
                if any("cost risk" in issue.lower() for issue in issues):
                    agent_status["high_risk"] += 1
                
                agent_status["details"][agent_name] = {
                    "status": status,
                    "priority": agent_info.get("priority", "unknown"),
                    "api_usage": agent_info.get("api_usage", False),
                    "cost_tracking": agent_info.get("cost_tracking", False),
                    "health_check": agent_info.get("health_check", False),
                    "issues": issues
                }
        
        return agent_status
    
    async def run_security_audit(self) -> Dict[str, Any]:
        """Run security audit checks"""
        self.logger.info("Running security audit...")
        
        security_results = {
            "vulnerabilities_found": 0,
            "security_risks": [],
            "recommendations": []
        }
        
        # Check for common security issues in agent registry
        if "agents" in self.agent_registry:
            for agent_name, agent_info in self.agent_registry["agents"].items():
                issues = agent_info.get("issues", [])
                
                for issue in issues:
                    if "security" in issue.lower():
                        security_results["vulnerabilities_found"] += 1
                        security_results["security_risks"].append({
                            "agent": agent_name,
                            "issue": issue,
                            "severity": "high" if "critical" in issue.lower() else "medium"
                        })
        
        # Check for shell command usage
        await self.check_shell_command_usage(security_results)
        
        # Check for API key exposure
        await self.check_api_key_exposure(security_results)
        
        return security_results
    
    async def check_shell_command_usage(self, security_results: Dict[str, Any]):
        """Check for potentially dangerous shell command usage"""
        dangerous_patterns = ["subprocess", "os.system", "shell=True"]
        
        for agent_file in self.agents_dir.glob("*.py"):
            try:
                content = agent_file.read_text()
                for pattern in dangerous_patterns:
                    if pattern in content:
                        security_results["security_risks"].append({
                            "agent": agent_file.stem,
                            "issue": f"Uses {pattern} - potential security risk",
                            "severity": "medium"
                        })
                        security_results["vulnerabilities_found"] += 1
            except Exception as e:
                self.logger.warning(f"Could not scan {agent_file}: {e}")
    
    async def check_api_key_exposure(self, security_results: Dict[str, Any]):
        """Check for potential API key exposure in code"""
        key_patterns = ["api_key", "API_KEY", "secret", "SECRET", "token"]
        
        for agent_file in self.agents_dir.glob("*.py"):
            try:
                content = agent_file.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    for pattern in key_patterns:
                        if pattern in line and "=" in line and not line.strip().startswith("#"):
                            # Check if it's hardcoded (not from environment)
                            if "os.getenv" not in line and "os.environ" not in line:
                                security_results["security_risks"].append({
                                    "agent": agent_file.stem,
                                    "issue": f"Potential hardcoded API key on line {i}",
                                    "severity": "high"
                                })
                                security_results["vulnerabilities_found"] += 1
            except Exception as e:
                self.logger.warning(f"Could not scan {agent_file}: {e}")
    
    async def analyze_cost_risks(self) -> Dict[str, Any]:
        """Analyze cost-related risks across agents"""
        self.logger.info("Analyzing cost risks...")
        
        cost_analysis = {
            "high_cost_agents": [],
            "untracked_api_usage": [],
            "missing_budget_controls": [],
            "total_risk_score": 0
        }
        
        if "agents" in self.agent_registry:
            for agent_name, agent_info in self.agent_registry["agents"].items():
                api_usage = agent_info.get("api_usage", False)
                cost_tracking = agent_info.get("cost_tracking", False)
                issues = agent_info.get("issues", [])
                
                # Check for high cost risk
                if any("cost risk" in issue.lower() for issue in issues):
                    cost_analysis["high_cost_agents"].append({
                        "agent": agent_name,
                        "issues": [i for i in issues if "cost" in i.lower()]
                    })
                    cost_analysis["total_risk_score"] += 10
                
                # Check for untracked API usage
                if api_usage and not cost_tracking:
                    cost_analysis["untracked_api_usage"].append(agent_name)
                    cost_analysis["total_risk_score"] += 5
                
                # Check for missing budget controls
                if api_usage and any("budget" in issue.lower() for issue in issues):
                    cost_analysis["missing_budget_controls"].append(agent_name)
                    cost_analysis["total_risk_score"] += 7
        
        return cost_analysis
    
    async def check_integrations(self) -> Dict[str, Any]:
        """Check integration status across agents"""
        self.logger.info("Checking agent integrations...")
        
        integration_status = {
            "manager_agent_connected": 0,
            "slack_integration": 0,
            "cost_tracking_integrated": 0,
            "health_checks_available": 0,
            "orphaned_agents": []
        }
        
        if "agents" in self.agent_registry:
            for agent_name, agent_info in self.agent_registry["agents"].items():
                # Check Manager Agent integration
                dependencies = agent_info.get("dependencies", [])
                if "manager_agent" in dependencies or "cost_tracker" in dependencies:
                    integration_status["manager_agent_connected"] += 1
                
                # Check Slack integration
                if agent_info.get("class") == "SlackNotifier" or "slack" in dependencies:
                    integration_status["slack_integration"] += 1
                
                # Check cost tracking
                if agent_info.get("cost_tracking", False):
                    integration_status["cost_tracking_integrated"] += 1
                
                # Check health checks
                if agent_info.get("health_check", False):
                    integration_status["health_checks_available"] += 1
                
                # Check for orphaned agents (no dependencies, no integrations)
                if (not dependencies and 
                    not agent_info.get("cost_tracking", False) and 
                    not agent_info.get("health_check", False) and
                    agent_info.get("api_usage", False)):
                    integration_status["orphaned_agents"].append(agent_name)
        
        return integration_status
    
    def generate_recommendations(self, audit_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate prioritized recommendations based on audit results"""
        recommendations = []
        
        # Critical recommendations
        health_data = audit_results["results"]["health_check"].get("data", {})
        if health_data.get("summary", {}).get("critical_issues_count", 0) > 0:
            recommendations.append({
                "priority": "CRITICAL",
                "category": "System Stability",
                "title": "Fix Broken Core Agents",
                "description": "Multiple core agents are non-functional",
                "impact": "System instability and monitoring gaps",
                "effort": "High",
                "timeline": "Immediate (24 hours)"
            })
        
        # High priority recommendations
        cost_risks = audit_results["results"]["cost_analysis"]["high_cost_agents"]
        if cost_risks:
            recommendations.append({
                "priority": "HIGH",
                "category": "Cost Control",
                "title": "Implement Budget Controls",
                "description": f"{len(cost_risks)} agents have high cost risk",
                "impact": "Prevent runaway API costs",
                "effort": "Medium",
                "timeline": "This week"
            })
        
        security_risks = audit_results["results"]["security_audit"]["vulnerabilities_found"]
        if security_risks > 0:
            recommendations.append({
                "priority": "HIGH",
                "category": "Security",
                "title": "Address Security Vulnerabilities",
                "description": f"{security_risks} security issues detected",
                "impact": "Reduce security attack surface",
                "effort": "Medium",
                "timeline": "This week"
            })
        
        # Medium priority recommendations
        untracked_usage = audit_results["results"]["cost_analysis"]["untracked_api_usage"]
        if untracked_usage:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Monitoring",
                "title": "Add Cost Tracking Integration",
                "description": f"{len(untracked_usage)} agents lack cost tracking",
                "impact": "Improve cost visibility and control",
                "effort": "Low",
                "timeline": "This month"
            })
        
        orphaned_agents = audit_results["results"]["integration_check"]["orphaned_agents"]
        if orphaned_agents:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Integration",
                "title": "Connect Orphaned Agents",
                "description": f"{len(orphaned_agents)} agents lack integration",
                "impact": "Improve system coordination",
                "effort": "Medium",
                "timeline": "This month"
            })
        
        return recommendations
    
    async def save_audit_report(self, audit_results: Dict[str, Any]) -> Path:
        """Save the audit report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"manager_agent_audit_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(audit_results, f, indent=2, default=str)
        
        return report_path
    
    async def send_audit_notification(self, audit_results: Dict[str, Any]):
        """Send audit results notification to Slack"""
        if not self.slack_notifier:
            return
        
        # Extract key metrics
        health_data = audit_results["results"]["health_check"].get("data", {})
        health_score = health_data.get("summary", {}).get("system_health_score", "Unknown")
        critical_issues = health_data.get("summary", {}).get("critical_issues_count", 0)
        
        agent_status = audit_results["results"]["agent_status"]
        cost_analysis = audit_results["results"]["cost_analysis"]
        security_audit = audit_results["results"]["security_audit"]
        
        # Create Slack message
        message = f"""
🔍 **AGENT SYSTEM AUDIT COMPLETE**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **SYSTEM HEALTH:** {health_score}/100
🤖 **AGENTS:** {agent_status['operational']}/{agent_status['total_agents']} Operational
🚨 **CRITICAL ISSUES:** {critical_issues}
💰 **COST RISKS:** {len(cost_analysis['high_cost_agents'])} agents
🔒 **SECURITY:** {security_audit['vulnerabilities_found']} vulnerabilities

**IMMEDIATE ACTIONS NEEDED:**
"""
        
        # Add top recommendations
        recommendations = audit_results.get("recommendations", [])
        critical_recs = [r for r in recommendations if r["priority"] == "CRITICAL"]
        high_recs = [r for r in recommendations if r["priority"] == "HIGH"]
        
        for rec in critical_recs[:2]:  # Top 2 critical
            message += f"\n🔴 **{rec['title']}** - {rec['description']}"
        
        for rec in high_recs[:2]:  # Top 2 high priority
            message += f"\n🟡 **{rec['title']}** - {rec['description']}"
        
        message += f"\n\n📋 **Full Report:** {audit_results.get('report_path', 'Available in reports/')}"
        
        # Send notification
        alert = {
            "severity": "critical" if critical_issues > 0 else "warning",
            "title": "Agent System Audit Complete",
            "message": message,
            "timestamp": datetime.now(),
            "metadata": {
                "health_score": health_score,
                "critical_issues": critical_issues,
                "audit_type": "full_system_audit"
            }
        }
        
        await self.slack_notifier.send_alert(alert)
    
    async def run_quick_health_check(self) -> Dict[str, Any]:
        """Run a quick health check without full analysis"""
        self.logger.info("Running quick health check...")
        
        quick_results = {
            "timestamp": datetime.now().isoformat(),
            "audit_type": "quick_health_check",
            "agent_count": 0,
            "operational_count": 0,
            "issues": []
        }
        
        if "agents" in self.agent_registry:
            for agent_name, agent_info in self.agent_registry["agents"].items():
                quick_results["agent_count"] += 1
                
                if agent_info.get("status") == "operational":
                    quick_results["operational_count"] += 1
                elif agent_info.get("status") == "broken":
                    quick_results["issues"].append(f"{agent_name}: broken")
                
                # Check for critical issues
                issues = agent_info.get("issues", [])
                critical_issues = [i for i in issues if "critical" in i.lower() or "cost risk" in i.lower()]
                for issue in critical_issues:
                    quick_results["issues"].append(f"{agent_name}: {issue}")
        
        quick_results["health_percentage"] = (
            (quick_results["operational_count"] / max(quick_results["agent_count"], 1)) * 100
        )
        
        return quick_results

# Integration with existing Manager Agent
async def integrate_audit_with_manager(manager_agent, audit_interval_hours: int = 24):
    """Integrate audit functionality with existing Manager Agent"""
    
    audit_system = ManagerAgentAudit(slack_notifier=manager_agent.slack_notifier)
    
    async def periodic_audit():
        """Run periodic audits"""
        while True:
            try:
                # Run full audit
                audit_results = await audit_system.run_full_audit()
                
                # Log results
                manager_agent.logger.info(f"Periodic audit completed with {len(audit_results.get('recommendations', []))} recommendations")
                
                # Wait for next audit
                await asyncio.sleep(audit_interval_hours * 3600)
                
            except Exception as e:
                manager_agent.logger.error(f"Periodic audit failed: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour on error
    
    # Start periodic audit task
    asyncio.create_task(periodic_audit())
    
    return audit_system

if __name__ == "__main__":
    # Standalone audit execution
    async def main():
        audit_system = ManagerAgentAudit()
        results = await audit_system.run_full_audit()
        print(f"Audit completed. Results saved to: {results.get('report_path')}")
    
    asyncio.run(main()) 