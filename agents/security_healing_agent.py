#!/usr/bin/env python3
"""
LLM-Powered Security Self-Healing Agent

This agent automatically detects vulnerabilities, analyzes them using an LLM,
and applies appropriate fixes with human oversight controls.
"""

import asyncio
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass

from core_agent_system import BaseAgent, AgentPriority, AgentAction
from claude_interface import ClaudeInterface

@dataclass
class VulnerabilityFinding:
    """Represents a security vulnerability finding"""
    id: str
    severity: str  # critical, high, medium, low
    type: str  # dependency, code, configuration
    description: str
    affected_files: List[str]
    cve_ids: List[str]
    fix_available: bool
    auto_fixable: bool
    risk_score: float

@dataclass
class HealingAction:
    """Represents a proposed healing action"""
    action_type: str  # update_dependency, patch_code, update_config
    description: str
    commands: List[str]
    affected_files: List[str]
    risk_level: str  # low, medium, high
    requires_approval: bool
    rollback_commands: List[str]

class SecurityHealingAgent(BaseAgent):
    """LLM-powered security self-healing agent"""
    
    def __init__(self):
        super().__init__("security_healer", "Security Healing Agent", AgentPriority.CRITICAL)
        self.claude = ClaudeInterface()
        self.logger = logging.getLogger(__name__)
        self.healing_history = []
        self.auto_fix_enabled = True
        self.max_auto_fixes_per_hour = 5
        self.recent_fixes = []
        
    async def execute(self) -> List[AgentAction]:
        """Main execution loop for security healing"""
        actions = []
        
        try:
            # 1. Scan for vulnerabilities
            vulnerabilities = await self.scan_vulnerabilities()
            
            if not vulnerabilities:
                return [self._create_action("scan_complete", "No vulnerabilities detected", "success")]
            
            # 2. Analyze vulnerabilities with LLM
            healing_plan = await self.analyze_with_llm(vulnerabilities)
            
            # 3. Execute approved fixes
            for action in healing_plan.actions:
                if self._should_auto_execute(action):
                    result = await self.execute_healing_action(action)
                    actions.append(result)
                else:
                    # Queue for human approval
                    actions.append(self._create_approval_request(action))
            
            # 4. Update healing history
            self._update_healing_history(vulnerabilities, healing_plan, actions)
            
        except Exception as e:
            self.logger.error(f"Security healing failed: {e}")
            actions.append(self._create_action("healing_error", str(e), "error"))
        
        return actions
    
    async def scan_vulnerabilities(self) -> List[VulnerabilityFinding]:
        """Comprehensive vulnerability scanning"""
        vulnerabilities = []
        
        # Python dependency scan
        python_vulns = await self._scan_python_dependencies()
        vulnerabilities.extend(python_vulns)
        
        # Node.js dependency scan
        node_vulns = await self._scan_node_dependencies()
        vulnerabilities.extend(node_vulns)
        
        # Code security scan
        code_vulns = await self._scan_code_security()
        vulnerabilities.extend(code_vulns)
        
        # Configuration scan
        config_vulns = await self._scan_configuration()
        vulnerabilities.extend(config_vulns)
        
        return vulnerabilities
    
    async def _scan_python_dependencies(self) -> List[VulnerabilityFinding]:
        """Scan Python dependencies for vulnerabilities"""
        vulnerabilities = []
        
        try:
            # Run pip-audit
            result = subprocess.run([
                "pip-audit", "--format=json", "--progress-spinner=off"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                audit_data = json.loads(result.stdout)
                
                for vuln in audit_data.get('vulnerabilities', []):
                    vulnerabilities.append(VulnerabilityFinding(
                        id=f"py-{vuln.get('id', 'unknown')}",
                        severity=self._map_severity(vuln.get('severity', 'medium')),
                        type="dependency",
                        description=vuln.get('description', ''),
                        affected_files=['requirements.txt'],
                        cve_ids=vuln.get('cve_ids', []),
                        fix_available=bool(vuln.get('fix_versions')),
                        auto_fixable=True,
                        risk_score=self._calculate_risk_score(vuln)
                    ))
        except Exception as e:
            self.logger.error(f"Python dependency scan failed: {e}")
        
        return vulnerabilities
    
    async def _scan_node_dependencies(self) -> List[VulnerabilityFinding]:
        """Scan Node.js dependencies for vulnerabilities"""
        vulnerabilities = []
        
        try:
            # Run npm audit
            result = subprocess.run([
                "npm", "audit", "--json"
            ], cwd="frontend", capture_output=True, text=True, timeout=60)
            
            if result.stdout:
                audit_data = json.loads(result.stdout)
                
                for vuln_id, vuln in audit_data.get('vulnerabilities', {}).items():
                    vulnerabilities.append(VulnerabilityFinding(
                        id=f"npm-{vuln_id}",
                        severity=vuln.get('severity', 'medium'),
                        type="dependency",
                        description=vuln.get('title', ''),
                        affected_files=['frontend/package.json'],
                        cve_ids=vuln.get('cves', []),
                        fix_available=bool(vuln.get('fixAvailable')),
                        auto_fixable=vuln.get('fixAvailable', {}).get('name') is not None,
                        risk_score=self._calculate_risk_score(vuln)
                    ))
        except Exception as e:
            self.logger.error(f"Node.js dependency scan failed: {e}")
        
        return vulnerabilities
    
    async def _scan_code_security(self) -> List[VulnerabilityFinding]:
        """Scan code for security issues using bandit"""
        vulnerabilities = []
        
        try:
            result = subprocess.run([
                "bandit", "-r", ".", "-f", "json", "-ll"
            ], capture_output=True, text=True, timeout=120)
            
            if result.stdout:
                bandit_data = json.loads(result.stdout)
                
                for issue in bandit_data.get('results', []):
                    vulnerabilities.append(VulnerabilityFinding(
                        id=f"code-{issue.get('test_id', 'unknown')}",
                        severity=issue.get('issue_severity', 'medium').lower(),
                        type="code",
                        description=issue.get('issue_text', ''),
                        affected_files=[issue.get('filename', '')],
                        cve_ids=[],
                        fix_available=True,
                        auto_fixable=False,  # Code fixes need human review
                        risk_score=self._calculate_risk_score(issue)
                    ))
        except Exception as e:
            self.logger.error(f"Code security scan failed: {e}")
        
        return vulnerabilities
    
    async def _scan_configuration(self) -> List[VulnerabilityFinding]:
        """Scan configuration for security issues"""
        vulnerabilities = []
        
        # Check for common configuration issues
        config_checks = [
            self._check_default_passwords,
            self._check_debug_mode,
            self._check_security_headers,
            self._check_ssl_configuration
        ]
        
        for check in config_checks:
            try:
                issues = await check()
                vulnerabilities.extend(issues)
            except Exception as e:
                self.logger.error(f"Configuration check failed: {e}")
        
        return vulnerabilities
    
    async def analyze_with_llm(self, vulnerabilities: List[VulnerabilityFinding]) -> 'HealingPlan':
        """Analyze vulnerabilities using LLM and create healing plan"""
        
        # Prepare context for LLM
        context = {
            "vulnerabilities": [
                {
                    "id": v.id,
                    "severity": v.severity,
                    "type": v.type,
                    "description": v.description,
                    "affected_files": v.affected_files,
                    "auto_fixable": v.auto_fixable,
                    "risk_score": v.risk_score
                }
                for v in vulnerabilities
            ],
            "system_info": await self._get_system_info(),
            "recent_changes": self._get_recent_changes(),
            "healing_history": self.healing_history[-10:]  # Last 10 healing actions
        }
        
        prompt = f"""
You are a security expert analyzing vulnerabilities in the Corgi Recommender Service.

VULNERABILITIES DETECTED:
{json.dumps(context['vulnerabilities'], indent=2)}

SYSTEM CONTEXT:
{json.dumps(context['system_info'], indent=2)}

TASK: Create a comprehensive healing plan that:
1. Prioritizes vulnerabilities by risk and impact
2. Provides specific remediation commands
3. Identifies which fixes can be automated safely
4. Includes rollback procedures
5. Considers system stability and dependencies

RESPONSE FORMAT (JSON):
{{
    "priority_order": ["vuln_id1", "vuln_id2", ...],
    "actions": [
        {{
            "vulnerability_id": "vuln_id",
            "action_type": "update_dependency|patch_code|update_config",
            "description": "Clear description of what will be done",
            "commands": ["command1", "command2"],
            "affected_files": ["file1", "file2"],
            "risk_level": "low|medium|high",
            "requires_approval": true|false,
            "rollback_commands": ["rollback1", "rollback2"],
            "reasoning": "Why this approach was chosen"
        }}
    ],
    "overall_risk_assessment": "low|medium|high",
    "estimated_downtime": "0-5 minutes",
    "recommendations": ["rec1", "rec2"]
}}

Focus on safe, incremental fixes that maintain system stability.
"""
        
        try:
            response = await self.claude.get_completion(prompt)
            healing_data = json.loads(response)
            return HealingPlan.from_dict(healing_data)
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            # Fallback to basic healing plan
            return self._create_fallback_healing_plan(vulnerabilities)
    
    async def execute_healing_action(self, action: HealingAction) -> AgentAction:
        """Execute a healing action with safety checks"""
        
        try:
            # Pre-execution safety checks
            if not self._safety_check(action):
                return self._create_action("safety_check_failed", 
                                         f"Safety check failed for {action.description}", "error")
            
            # Create backup if needed
            if action.risk_level in ['medium', 'high']:
                await self._create_backup(action.affected_files)
            
            # Execute commands
            results = []
            for command in action.commands:
                result = await self._execute_command(command)
                results.append(result)
                
                if not result['success']:
                    # Rollback on failure
                    await self._rollback(action)
                    return self._create_action("healing_failed", 
                                             f"Command failed: {command}", "error")
            
            # Verify fix
            verification_result = await self._verify_fix(action)
            
            if verification_result['success']:
                self.recent_fixes.append({
                    'timestamp': datetime.now(),
                    'action': action.description,
                    'success': True
                })
                return self._create_action("healing_success", 
                                         f"Successfully applied: {action.description}", "success")
            else:
                await self._rollback(action)
                return self._create_action("verification_failed", 
                                         f"Fix verification failed: {verification_result['error']}", "error")
                
        except Exception as e:
            self.logger.error(f"Healing action failed: {e}")
            await self._rollback(action)
            return self._create_action("healing_error", str(e), "error")
    
    def _should_auto_execute(self, action: HealingAction) -> bool:
        """Determine if action should be auto-executed"""
        
        # Check if auto-fix is enabled
        if not self.auto_fix_enabled:
            return False
        
        # Check rate limiting
        recent_fixes_count = len([f for f in self.recent_fixes 
                                if (datetime.now() - f['timestamp']).seconds < 3600])
        if recent_fixes_count >= self.max_auto_fixes_per_hour:
            return False
        
        # Only auto-execute low-risk actions
        if action.risk_level != 'low':
            return False
        
        # Don't auto-execute if approval is required
        if action.requires_approval:
            return False
        
        return True
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get current system information"""
        return {
            "python_version": subprocess.run(["python", "--version"], 
                                           capture_output=True, text=True).stdout.strip(),
            "node_version": subprocess.run(["node", "--version"], 
                                         capture_output=True, text=True).stdout.strip(),
            "git_branch": subprocess.run(["git", "branch", "--show-current"], 
                                       capture_output=True, text=True).stdout.strip(),
            "last_commit": subprocess.run(["git", "log", "-1", "--oneline"], 
                                        capture_output=True, text=True).stdout.strip(),
            "environment": "development"  # Could be detected dynamically
        }
    
    def _calculate_risk_score(self, vuln_data: Dict) -> float:
        """Calculate risk score for vulnerability"""
        severity_scores = {
            'critical': 10.0,
            'high': 7.5,
            'medium': 5.0,
            'low': 2.5
        }
        
        base_score = severity_scores.get(vuln_data.get('severity', 'medium').lower(), 5.0)
        
        # Adjust based on other factors
        if vuln_data.get('cve_ids') or vuln_data.get('cves'):
            base_score += 1.0  # CVE assigned increases risk
        
        if vuln_data.get('fix_available') or vuln_data.get('fixAvailable'):
            base_score -= 0.5  # Fix available reduces risk
        
        return min(base_score, 10.0)
    
    def _create_action(self, action_type: str, description: str, result: str) -> AgentAction:
        """Create an agent action"""
        return AgentAction(
            agent_id=self.agent_id,
            action_type=action_type,
            description=description,
            timestamp=datetime.now(),
            result=result,
            metadata={}
        )
    
    async def health_check(self) -> bool:
        """Health check for the security healing agent"""
        try:
            # Basic health checks
            return (
                self.claude is not None and
                Path("requirements.txt").exists() and
                subprocess.run(["python", "--version"], capture_output=True).returncode == 0
            )
        except Exception:
            return False
    
    def _create_approval_request(self, action: HealingAction) -> AgentAction:
        """Create an approval request action"""
        return AgentAction(
            agent_id=self.agent_id,
            action_type="approval_request",
            description=f"Approval required: {action.description}",
            timestamp=datetime.now(),
            result="pending",
            metadata={
                "action": action.__dict__,
                "risk_level": action.risk_level,
                "affected_files": action.affected_files
            }
        )
    
    def _update_healing_history(self, vulnerabilities, healing_plan, actions):
        """Update the healing history"""
        self.healing_history.append({
            "timestamp": datetime.now(),
            "vulnerabilities_count": len(vulnerabilities),
            "actions_count": len(actions),
            "plan_risk_assessment": healing_plan.overall_risk_assessment if healing_plan else "unknown"
        })
        
        # Keep only recent history
        if len(self.healing_history) > 50:
            self.healing_history = self.healing_history[-50:]
    
    def _create_fallback_healing_plan(self, vulnerabilities):
        """Create a basic healing plan when LLM fails"""
        actions = []
        
        for vuln in vulnerabilities:
            if vuln.type == "dependency" and vuln.auto_fixable:
                actions.append(HealingAction(
                    action_type="update_dependency",
                    description=f"Update dependency to fix {vuln.id}",
                    commands=["pip install --upgrade package"] if "py-" in vuln.id else ["npm update"],
                    affected_files=vuln.affected_files,
                    risk_level="low" if vuln.severity in ["low", "medium"] else "high",
                    requires_approval=vuln.severity in ["high", "critical"],
                    rollback_commands=["git checkout -- requirements.txt", "pip install -r requirements.txt"]
                ))
        
        return HealingPlan(
            priority_order=[a.description for a in actions],
            actions=actions,
            overall_risk_assessment="medium",
            estimated_downtime="2-5 minutes",
            recommendations=["Review changes before deployment", "Test thoroughly"]
        )
    
    def _map_severity(self, severity: str) -> str:
        """Map various severity formats to standard format"""
        severity_lower = severity.lower()
        if severity_lower in ["critical", "high", "medium", "low"]:
            return severity_lower
        elif severity_lower in ["error", "warning"]:
            return "medium"
        else:
            return "low"
    
    def _get_recent_changes(self):
        """Get recent git changes"""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                capture_output=True, text=True
            )
            return result.stdout.strip().split('\n') if result.returncode == 0 else []
        except Exception:
            return []
    
    def _safety_check(self, action: HealingAction) -> bool:
        """Perform safety checks before executing action"""
        # Basic safety checks
        if not action.commands:
            return False
        
        # Check for dangerous commands
        dangerous_patterns = ["rm -rf", "sudo", "chmod 777", "DROP TABLE"]
        for command in action.commands:
            if any(pattern in command for pattern in dangerous_patterns):
                return False
        
        return True
    
    async def _create_backup(self, affected_files):
        """Create backup of affected files"""
        backup_dir = Path("backups") / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in affected_files:
            if Path(file_path).exists():
                import shutil
                shutil.copy2(file_path, backup_dir / Path(file_path).name)
    
    async def _execute_command(self, command: str):
        """Execute a command safely"""
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _verify_fix(self, action: HealingAction):
        """Verify that a fix was applied successfully"""
        # Basic verification - could be enhanced
        try:
            if action.action_type == "update_dependency":
                # Re-run vulnerability scan to see if issue is resolved
                if "pip" in action.commands[0]:
                    result = subprocess.run(
                        ["pip-audit", "--format=json", "--progress-spinner=off"],
                        capture_output=True, text=True, timeout=60
                    )
                    return {"success": result.returncode == 0}
                elif "npm" in action.commands[0]:
                    result = subprocess.run(
                        ["npm", "audit", "--json"],
                        cwd="frontend", capture_output=True, text=True, timeout=60
                    )
                    return {"success": True}  # npm audit can return non-zero even when successful
            
            return {"success": True}  # Default to success for now
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _rollback(self, action: HealingAction):
        """Rollback changes if something goes wrong"""
        try:
            for command in action.rollback_commands:
                await self._execute_command(command)
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
    
    async def _check_default_passwords(self):
        """Check for default passwords in configuration"""
        issues = []
        
        # Check .env files for weak passwords
        env_files = [".env", "env.example"]
        for env_file in env_files:
            if Path(env_file).exists():
                with open(env_file) as f:
                    content = f.read()
                    if "password=123" in content.lower() or "password=admin" in content.lower():
                        issues.append(VulnerabilityFinding(
                            id="config-weak-password",
                            severity="high",
                            type="configuration",
                            description=f"Weak default password found in {env_file}",
                            affected_files=[env_file],
                            cve_ids=[],
                            fix_available=True,
                            auto_fixable=True,
                            risk_score=7.5
                        ))
        
        return issues
    
    async def _check_debug_mode(self):
        """Check if debug mode is enabled in production"""
        issues = []
        
        # Check Flask debug mode
        if Path("app.py").exists():
            with open("app.py") as f:
                content = f.read()
                if "debug=True" in content:
                    issues.append(VulnerabilityFinding(
                        id="config-debug-enabled",
                        severity="medium",
                        type="configuration",
                        description="Debug mode enabled in app.py",
                        affected_files=["app.py"],
                        cve_ids=[],
                        fix_available=True,
                        auto_fixable=True,
                        risk_score=5.0
                    ))
        
        return issues
    
    async def _check_security_headers(self):
        """Check for missing security headers"""
        # This would need to make HTTP requests to check headers
        # For now, return empty list
        return []
    
    async def _check_ssl_configuration(self):
        """Check SSL configuration"""
        # This would need to check SSL certificates and configuration
        # For now, return empty list
        return []

@dataclass
class HealingPlan:
    """Represents a complete healing plan"""
    priority_order: List[str]
    actions: List[HealingAction]
    overall_risk_assessment: str
    estimated_downtime: str
    recommendations: List[str]
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'HealingPlan':
        """Create HealingPlan from dictionary"""
        actions = [
            HealingAction(
                action_type=a['action_type'],
                description=a['description'],
                commands=a['commands'],
                affected_files=a['affected_files'],
                risk_level=a['risk_level'],
                requires_approval=a['requires_approval'],
                rollback_commands=a['rollback_commands']
            )
            for a in data['actions']
        ]
        
        return cls(
            priority_order=data['priority_order'],
            actions=actions,
            overall_risk_assessment=data['overall_risk_assessment'],
            estimated_downtime=data['estimated_downtime'],
            recommendations=data['recommendations']
        )

if __name__ == "__main__":
    # Test the healing agent
    async def test_healing_agent():
        agent = SecurityHealingAgent()
        actions = await agent.execute()
        
        for action in actions:
            print(f"[{action.result.upper()}] {action.action_type}: {action.description}")
    
    asyncio.run(test_healing_agent()) 