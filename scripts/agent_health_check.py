#!/usr/bin/env python3
"""
Agent Health Check Script

Comprehensive analysis of all agents in the system to assess:
- Operational status
- Code quality
- Integration patterns
- Risk assessment
- DevOps readiness
"""

import ast
import importlib
import inspect
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json
import subprocess
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class AgentAnalyzer:
    """Comprehensive agent analysis system"""
    
    def __init__(self):
        self.agents_dir = project_root / "agents"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "summary": {},
            "critical_issues": [],
            "recommendations": []
        }
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for the analyzer"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def analyze_all_agents(self) -> Dict[str, Any]:
        """Analyze all agents in the system"""
        self.logger.info("Starting comprehensive agent analysis...")
        
        # Find all Python files in agents directory
        agent_files = list(self.agents_dir.glob("*.py"))
        agent_files = [f for f in agent_files if not f.name.startswith("__")]
        
        self.logger.info(f"Found {len(agent_files)} potential agent files")
        
        for agent_file in agent_files:
            try:
                self.logger.info(f"Analyzing {agent_file.name}...")
                analysis = self.analyze_agent_file(agent_file)
                self.results["agents"][agent_file.stem] = analysis
            except Exception as e:
                self.logger.error(f"Failed to analyze {agent_file.name}: {e}")
                self.results["agents"][agent_file.stem] = {
                    "status": "analysis_failed",
                    "error": str(e)
                }
        
        # Generate summary and recommendations
        self.generate_summary()
        self.generate_recommendations()
        
        return self.results
    
    def analyze_agent_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single agent file"""
        analysis = {
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            "status": "unknown",
            "classes": [],
            "functions": [],
            "imports": [],
            "dependencies": [],
            "code_quality": {},
            "integration_status": {},
            "risk_assessment": {},
            "devops_readiness": {}
        }
        
        # Read and parse the file
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            # Analyze AST
            self.analyze_ast(tree, analysis)
            
            # Try to import and analyze runtime
            self.analyze_runtime(file_path, analysis)
            
            # Analyze code quality
            self.analyze_code_quality(content, analysis)
            
            # Analyze integration patterns
            self.analyze_integration(content, analysis)
            
            # Assess risks
            self.assess_risks(content, analysis)
            
            # Check DevOps readiness
            self.check_devops_readiness(content, analysis)
            
            analysis["status"] = "analyzed"
            
        except SyntaxError as e:
            analysis["status"] = "syntax_error"
            analysis["error"] = str(e)
        except Exception as e:
            analysis["status"] = "error"
            analysis["error"] = str(e)
            
        return analysis
    
    def analyze_ast(self, tree: ast.AST, analysis: Dict[str, Any]):
        """Analyze the Abstract Syntax Tree"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "bases": [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases],
                    "methods": [],
                    "decorators": [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list],
                    "docstring": ast.get_docstring(node),
                    "line_number": node.lineno
                }
                
                # Analyze methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = {
                            "name": item.name,
                            "args": [arg.arg for arg in item.args.args],
                            "is_async": isinstance(item, ast.AsyncFunctionDef),
                            "decorators": [d.id if isinstance(d, ast.Name) else str(d) for d in item.decorator_list],
                            "docstring": ast.get_docstring(item),
                            "line_number": item.lineno
                        }
                        class_info["methods"].append(method_info)
                
                analysis["classes"].append(class_info)
                
            elif isinstance(node, ast.FunctionDef) and not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree) if hasattr(parent, 'body') and node in getattr(parent, 'body', [])):
                # Top-level functions only
                func_info = {
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "decorators": [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list],
                    "docstring": ast.get_docstring(node),
                    "line_number": node.lineno
                }
                analysis["functions"].append(func_info)
                
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis["imports"].append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "type": "import"
                    })
                    
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    analysis["imports"].append({
                        "module": f"{module}.{alias.name}" if module else alias.name,
                        "alias": alias.asname,
                        "type": "from_import",
                        "from_module": module
                    })
    
    def analyze_runtime(self, file_path: Path, analysis: Dict[str, Any]):
        """Try to import and analyze runtime behavior"""
        module_name = f"agents.{file_path.stem}"
        
        try:
            # Try to import the module
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                analysis["integration_status"]["importable"] = True
                
                # Find agent classes
                agent_classes = []
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if name.endswith('Agent') or 'Agent' in name:
                        agent_classes.append({
                            "name": name,
                            "instantiable": self.test_instantiation(obj),
                            "methods": [method for method in dir(obj) if not method.startswith('_')],
                            "has_health_check": hasattr(obj, 'health_check'),
                            "has_execute": hasattr(obj, 'execute'),
                            "base_classes": [base.__name__ for base in obj.__bases__]
                        })
                
                analysis["agent_classes"] = agent_classes
                
        except Exception as e:
            analysis["integration_status"]["importable"] = False
            analysis["integration_status"]["import_error"] = str(e)
    
    def test_instantiation(self, cls) -> bool:
        """Test if a class can be instantiated"""
        try:
            # Try with no arguments first
            instance = cls()
            return True
        except:
            try:
                # Try with common agent patterns
                instance = cls(agent_id="test", name="test")
                return True
            except:
                try:
                    # Try with minimal config
                    instance = cls("test")
                    return True
                except:
                    return False
    
    def analyze_code_quality(self, content: str, analysis: Dict[str, Any]):
        """Analyze code quality metrics"""
        lines = content.split('\n')
        
        quality = {
            "total_lines": len(lines),
            "code_lines": len([line for line in lines if line.strip() and not line.strip().startswith('#')]),
            "comment_lines": len([line for line in lines if line.strip().startswith('#')]),
            "docstring_lines": content.count('"""') + content.count("'''"),
            "has_error_handling": "try:" in content and "except" in content,
            "error_handling_blocks": content.count("try:"),
            "has_logging": any(log_level in content for log_level in ["logger.", "logging.", ".info(", ".error(", ".warning(", ".debug("]),
            "has_type_hints": "typing" in content or ":" in content and "->" in content,
            "has_dataclasses": "@dataclass" in content,
            "has_async": "async def" in content or "await " in content,
            "todo_comments": content.count("TODO") + content.count("FIXME") + content.count("XXX"),
            "complexity_indicators": {
                "nested_loops": content.count("for ") * content.count("while ") if "for " in content and "while " in content else 0,
                "conditional_complexity": content.count("if ") + content.count("elif ") + content.count("else:"),
                "function_count": len(analysis["functions"]) + sum(len(cls["methods"]) for cls in analysis["classes"])
            }
        }
        
        # Calculate quality score
        score = 0
        if quality["has_error_handling"]: score += 20
        if quality["has_logging"]: score += 20
        if quality["has_type_hints"]: score += 15
        if quality["docstring_lines"] > 0: score += 15
        if quality["has_dataclasses"]: score += 10
        if quality["comment_lines"] / max(quality["code_lines"], 1) > 0.1: score += 10
        if quality["todo_comments"] == 0: score += 10
        
        quality["quality_score"] = min(score, 100)
        analysis["code_quality"] = quality
    
    def analyze_integration(self, content: str, analysis: Dict[str, Any]):
        """Analyze integration patterns"""
        integration = {
            "uses_cost_tracker": "CostTracker" in content or "cost_tracker" in content,
            "uses_token_tracker": "TokenTracker" in content or "token_tracker" in content,
            "uses_manager_agent": "ManagerAgent" in content or "manager_agent" in content,
            "uses_slack_notifier": "SlackNotifier" in content or "slack_notifier" in content,
            "uses_claude_api": "claude" in content.lower() or "anthropic" in content.lower(),
            "uses_database": any(db in content.lower() for db in ["sqlite", "postgresql", "mysql", "database", "db."]),
            "uses_config_files": any(config in content for config in ["yaml", "json", "config"]),
            "has_health_endpoint": "/health" in content or "health_check" in content,
            "has_metrics": "metrics" in content.lower() or "prometheus" in content.lower(),
            "api_integrations": [],
            "external_dependencies": []
        }
        
        # Check for API integrations
        if "requests." in content or "aiohttp" in content:
            integration["api_integrations"].append("HTTP_CLIENT")
        if "anthropic" in content.lower():
            integration["api_integrations"].append("ANTHROPIC_API")
        if "openai" in content.lower():
            integration["api_integrations"].append("OPENAI_API")
        if "slack" in content.lower():
            integration["api_integrations"].append("SLACK_API")
            
        # Check for external dependencies
        for imp in analysis["imports"]:
            module = imp["module"].split(".")[0]
            if module not in ["os", "sys", "json", "logging", "datetime", "typing", "pathlib", "asyncio", "traceback"]:
                integration["external_dependencies"].append(module)
        
        analysis["integration_status"].update(integration)
    
    def assess_risks(self, content: str, analysis: Dict[str, Any]):
        """Assess potential risks"""
        risks = {
            "high_cost_risk": False,
            "security_risks": [],
            "infinite_loop_risk": False,
            "file_system_risk": False,
            "network_risk": False,
            "privilege_escalation_risk": False,
            "data_exposure_risk": False,
            "circuit_breaker_missing": False
        }
        
        # High cost risk (expensive API calls without limits)
        if ("claude-3-opus" in content or "gpt-4" in content) and "budget" not in content.lower():
            risks["high_cost_risk"] = True
        
        # Security risks
        if "subprocess" in content and "shell=True" in content:
            risks["security_risks"].append("SHELL_INJECTION")
        if "eval(" in content or "exec(" in content:
            risks["security_risks"].append("CODE_INJECTION")
        if "os.system" in content:
            risks["security_risks"].append("SYSTEM_COMMAND")
        if "pickle" in content:
            risks["security_risks"].append("UNSAFE_DESERIALIZATION")
            
        # Infinite loop risk
        if ("while True:" in content or "for" in content) and "break" not in content:
            risks["infinite_loop_risk"] = True
            
        # File system operations
        if any(op in content for op in ["os.remove", "shutil.rmtree", "delete", "unlink"]):
            risks["file_system_risk"] = True
            
        # Network operations without error handling
        if ("requests." in content or "urllib" in content) and "timeout" not in content:
            risks["network_risk"] = True
            
        # Check for missing circuit breakers on API calls
        if ("anthropic" in content.lower() or "openai" in content.lower()) and "circuit" not in content.lower():
            risks["circuit_breaker_missing"] = True
            
        analysis["risk_assessment"] = risks
    
    def check_devops_readiness(self, content: str, analysis: Dict[str, Any]):
        """Check DevOps and production readiness"""
        devops = {
            "has_health_check": "health_check" in content or "/health" in content,
            "has_metrics": "metrics" in content.lower(),
            "has_logging": "logger" in content or "logging" in content,
            "has_config_management": "config" in content.lower() and ("yaml" in content or "json" in content),
            "has_error_recovery": "retry" in content.lower() or "fallback" in content.lower(),
            "has_graceful_shutdown": "signal" in content or "shutdown" in content,
            "containerizable": False,
            "monitoring_ready": False,
            "scalable": False
        }
        
        # Check for containerization readiness
        dockerfile_exists = (project_root / "agents" / "Dockerfile").exists()
        devops["containerizable"] = dockerfile_exists or "docker" in content.lower()
        
        # Check monitoring readiness
        devops["monitoring_ready"] = devops["has_health_check"] and devops["has_metrics"]
        
        # Check scalability indicators
        devops["scalable"] = "async" in content and devops["has_config_management"]
        
        analysis["devops_readiness"] = devops
    
    def generate_summary(self):
        """Generate summary statistics"""
        agents = self.results["agents"]
        
        summary = {
            "total_agents": len(agents),
            "operational_agents": len([a for a in agents.values() if a.get("status") == "analyzed"]),
            "broken_agents": len([a for a in agents.values() if a.get("status") in ["error", "syntax_error", "analysis_failed"]]),
            "importable_agents": len([a for a in agents.values() if a.get("integration_status", {}).get("importable", False)]),
            "agents_with_cost_tracking": len([a for a in agents.values() if a.get("integration_status", {}).get("uses_cost_tracker", False)]),
            "high_risk_agents": len([a for a in agents.values() if self.is_high_risk(a)]),
            "production_ready_agents": len([a for a in agents.values() if self.is_production_ready(a)]),
            "average_quality_score": self.calculate_average_quality_score(),
            "critical_issues_count": 0
        }
        
        # Calculate system health score
        if summary["total_agents"] > 0:
            health_score = (
                (summary["operational_agents"] / summary["total_agents"]) * 40 +
                (summary["importable_agents"] / summary["total_agents"]) * 30 +
                (summary["production_ready_agents"] / summary["total_agents"]) * 30
            )
            summary["system_health_score"] = round(health_score, 1)
        else:
            summary["system_health_score"] = 0
        
        self.results["summary"] = summary
    
    def is_high_risk(self, agent_analysis: Dict[str, Any]) -> bool:
        """Determine if an agent is high risk"""
        risks = agent_analysis.get("risk_assessment", {})
        return (
            risks.get("high_cost_risk", False) or
            len(risks.get("security_risks", [])) > 0 or
            risks.get("infinite_loop_risk", False)
        )
    
    def is_production_ready(self, agent_analysis: Dict[str, Any]) -> bool:
        """Determine if an agent is production ready"""
        devops = agent_analysis.get("devops_readiness", {})
        quality = agent_analysis.get("code_quality", {})
        
        return (
            devops.get("has_health_check", False) and
            devops.get("has_logging", False) and
            devops.get("has_error_recovery", False) and
            quality.get("has_error_handling", False) and
            quality.get("quality_score", 0) >= 70
        )
    
    def calculate_average_quality_score(self) -> float:
        """Calculate average quality score across all agents"""
        scores = [
            agent.get("code_quality", {}).get("quality_score", 0)
            for agent in self.results["agents"].values()
            if agent.get("code_quality", {}).get("quality_score") is not None
        ]
        return round(sum(scores) / len(scores), 1) if scores else 0
    
    def generate_recommendations(self):
        """Generate prioritized recommendations"""
        recommendations = {
            "CRITICAL": [],
            "HIGH": [],
            "MEDIUM": [],
            "LOW": []
        }
        
        agents = self.results["agents"]
        
        for agent_name, analysis in agents.items():
            # Critical issues
            if analysis.get("status") in ["error", "syntax_error"]:
                recommendations["CRITICAL"].append(f"Fix broken agent: {agent_name} - {analysis.get('error', 'Unknown error')}")
            
            if analysis.get("risk_assessment", {}).get("high_cost_risk"):
                recommendations["CRITICAL"].append(f"Add cost controls to {agent_name} - uses expensive models without budget limits")
            
            security_risks = analysis.get("risk_assessment", {}).get("security_risks", [])
            if security_risks:
                recommendations["CRITICAL"].append(f"Fix security vulnerabilities in {agent_name}: {', '.join(security_risks)}")
            
            # High priority issues
            if not analysis.get("integration_status", {}).get("uses_cost_tracker") and analysis.get("integration_status", {}).get("uses_claude_api"):
                recommendations["HIGH"].append(f"Add cost tracking to {agent_name} - makes API calls without monitoring")
            
            if not analysis.get("code_quality", {}).get("has_error_handling"):
                recommendations["HIGH"].append(f"Add error handling to {agent_name}")
            
            if analysis.get("risk_assessment", {}).get("circuit_breaker_missing"):
                recommendations["HIGH"].append(f"Add circuit breaker to {agent_name} - API calls without failure protection")
            
            # Medium priority issues
            if not analysis.get("code_quality", {}).get("has_logging"):
                recommendations["MEDIUM"].append(f"Add logging to {agent_name}")
            
            if not analysis.get("devops_readiness", {}).get("has_health_check"):
                recommendations["MEDIUM"].append(f"Add health check endpoint to {agent_name}")
            
            quality_score = analysis.get("code_quality", {}).get("quality_score", 0)
            if quality_score < 50:
                recommendations["MEDIUM"].append(f"Improve code quality in {agent_name} (score: {quality_score}/100)")
            
            # Low priority issues
            if not analysis.get("code_quality", {}).get("has_type_hints"):
                recommendations["LOW"].append(f"Add type hints to {agent_name}")
            
            if analysis.get("code_quality", {}).get("todo_comments", 0) > 0:
                recommendations["LOW"].append(f"Address TODO comments in {agent_name}")
        
        self.results["recommendations"] = recommendations
        
        # Count critical issues for summary
        self.results["summary"]["critical_issues_count"] = len(recommendations["CRITICAL"])

def main():
    """Main execution function"""
    print("🔍 Starting Comprehensive Agent Audit...")
    print("=" * 60)
    
    analyzer = AgentAnalyzer()
    results = analyzer.analyze_all_agents()
    
    # Save results to file
    reports_dir = project_root / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    report_file = reports_dir / f"agent_health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"📊 Analysis complete! Results saved to: {report_file}")
    print()
    print("📈 SUMMARY:")
    print(f"  Total Agents: {results['summary']['total_agents']}")
    print(f"  Operational: {results['summary']['operational_agents']}")
    print(f"  Broken: {results['summary']['broken_agents']}")
    print(f"  System Health Score: {results['summary']['system_health_score']}/100")
    print(f"  Critical Issues: {results['summary']['critical_issues_count']}")
    print()
    
    if results['recommendations']['CRITICAL']:
        print("🚨 CRITICAL ISSUES:")
        for issue in results['recommendations']['CRITICAL']:
            print(f"  • {issue}")
        print()
    
    if results['recommendations']['HIGH']:
        print("⚠️  HIGH PRIORITY:")
        for issue in results['recommendations']['HIGH'][:5]:  # Show first 5
            print(f"  • {issue}")
        if len(results['recommendations']['HIGH']) > 5:
            print(f"  ... and {len(results['recommendations']['HIGH']) - 5} more")
        print()
    
    return results

if __name__ == "__main__":
    main() 