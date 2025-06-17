#!/usr/bin/env python3
"""
Browser Automation with Manager Agent Escalation

Example of how simple scripts escalate issues to the Manager Agent
when they encounter problems beyond their scope.
"""

import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BrowserAutomationWithEscalation:
    """Simple browser automation that escalates complex issues"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.max_retries = 3
        self.manager_agent = None  # Will be injected by system
        
    def test_corgi_interaction(self, profile_name: str, goal: str) -> Dict[str, Any]:
        """Test interaction with escalation on complex failures"""
        
        try:
            # Simple automation logic
            result = self._perform_basic_test(profile_name, goal)
            
            # Check if we need to escalate
            if self._should_escalate(result):
                return self._escalate_to_manager(result, profile_name, goal)
            
            return result
            
        except Exception as e:
            # Always escalate exceptions
            return self._escalate_to_manager({
                "error": str(e),
                "type": "exception"
            }, profile_name, goal)
    
    def _perform_basic_test(self, profile_name: str, goal: str) -> Dict[str, Any]:
        """Perform basic automation without AI"""
        results = {
            "profile": profile_name,
            "goal": goal,
            "success": True,
            "actions": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Test health endpoint
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            action_result = {
                "action": "health_check",
                "status": response.status_code,
                "success": response.status_code == 200
            }
            results["actions"].append(action_result)
            
            # Check for suspicious responses that might need security analysis
            if response.status_code in [403, 401, 429]:
                results["security_concern"] = f"Received {response.status_code} status"
                
        except requests.exceptions.Timeout:
            results["actions"].append({
                "action": "health_check",
                "error": "timeout",
                "success": False
            })
            results["escalation_reason"] = "service_timeout"
            
        except requests.exceptions.ConnectionError:
            results["actions"].append({
                "action": "health_check", 
                "error": "connection_failed",
                "success": False
            })
            results["escalation_reason"] = "service_unavailable"
        
        # Test recommendations endpoint
        try:
            response = requests.get(f"{self.base_url}/api/v1/recommendations", timeout=5)
            results["actions"].append({
                "action": "get_recommendations",
                "status": response.status_code,
                "success": response.status_code == 200
            })
            
        except Exception as e:
            results["actions"].append({
                "action": "get_recommendations",
                "error": str(e),
                "success": False
            })
            results["escalation_reason"] = "api_failure"
        
        # Determine overall success
        successful_actions = [a for a in results["actions"] if a.get("success", False)]
        results["success"] = len(successful_actions) > 0
        
        return results
    
    def _should_escalate(self, result: Dict[str, Any]) -> bool:
        """Determine if issue needs Manager Agent intervention"""
        
        # Always escalate if explicitly marked
        if "escalation_reason" in result:
            return True
            
        # Escalate security concerns
        if "security_concern" in result:
            return True
            
        # Escalate if all actions failed
        if not result.get("success", False):
            return True
            
        # Escalate if we got unexpected status codes
        for action in result.get("actions", []):
            status = action.get("status")
            if status and status >= 500:  # Server errors
                return True
                
        return False
    
    def _escalate_to_manager(self, issue_data: Dict[str, Any], profile: str, goal: str) -> Dict[str, Any]:
        """Escalate issue to Manager Agent for intelligent handling"""
        
        escalation_request = {
            "source": "browser_automation",
            "issue_type": issue_data.get("escalation_reason", "unknown"),
            "profile": profile,
            "goal": goal,
            "issue_data": issue_data,
            "timestamp": datetime.now().isoformat(),
            "suggested_actions": self._suggest_basic_actions(issue_data)
        }
        
        logger.warning(f"Escalating to Manager Agent: {escalation_request['issue_type']}")
        
        # In real implementation, this would call the Manager Agent
        if self.manager_agent:
            return self.manager_agent.handle_escalation(escalation_request)
        else:
            # Fallback behavior when Manager Agent not available
            return {
                "success": False,
                "escalated": True,
                "issue": escalation_request,
                "fallback_message": "Manager Agent not available, logged for manual review"
            }
    
    def _suggest_basic_actions(self, issue_data: Dict[str, Any]) -> list:
        """Suggest basic actions the Manager Agent might consider"""
        suggestions = []
        
        escalation_reason = issue_data.get("escalation_reason")
        
        if escalation_reason == "service_timeout":
            suggestions.extend([
                "Check service health",
                "Increase timeout values",
                "Implement retry with exponential backoff"
            ])
            
        elif escalation_reason == "service_unavailable":
            suggestions.extend([
                "Verify service is running",
                "Check network connectivity", 
                "Alert operations team"
            ])
            
        elif escalation_reason == "api_failure":
            suggestions.extend([
                "Check API endpoint status",
                "Verify authentication",
                "Review API rate limits"
            ])
            
        elif "security_concern" in issue_data:
            suggestions.extend([
                "Route to Security Agent for analysis",
                "Check for potential attacks",
                "Review access logs"
            ])
            
        return suggestions

# Example Manager Agent escalation handler
class ManagerAgentEscalationHandler:
    """Example of how Manager Agent handles escalations from scripts"""
    
    def __init__(self):
        self.security_agent = None
        self.monitoring_agent = None
        self.claude_interface = None
        
    def handle_escalation(self, escalation_request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle escalation with AI-powered decision making"""
        
        issue_type = escalation_request["issue_type"]
        issue_data = escalation_request["issue_data"]
        
        logger.info(f"Manager Agent handling escalation: {issue_type}")
        
        # Route based on issue type
        if "security" in issue_type or "security_concern" in issue_data:
            return self._route_to_security_agent(escalation_request)
            
        elif issue_type in ["service_timeout", "service_unavailable"]:
            return self._handle_service_issue(escalation_request)
            
        elif issue_type == "api_failure":
            return self._handle_api_issue(escalation_request)
            
        else:
            return self._handle_generic_issue(escalation_request)
    
    def _route_to_security_agent(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route security concerns to Security Agent"""
        if self.security_agent:
            # AI-powered security analysis
            return self.security_agent.analyze_security_concern(request)
        else:
            return {
                "success": False,
                "action": "security_analysis_needed",
                "message": "Security Agent required but not available"
            }
    
    def _handle_service_issue(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle service availability issues"""
        # Manager Agent uses built-in logic for common issues
        return {
            "success": True,
            "action": "service_recovery_initiated",
            "message": "Implementing retry strategy with exponential backoff",
            "retry_strategy": {
                "max_retries": 5,
                "base_delay": 2,
                "max_delay": 30
            }
        }
    
    def _handle_api_issue(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API-related issues"""
        if self.monitoring_agent:
            # Check if this is a cost/rate limiting issue
            return self.monitoring_agent.analyze_api_issue(request)
        else:
            return {
                "success": True,
                "action": "api_monitoring_enabled",
                "message": "Increased API monitoring and alerting"
            }

def run_browser_test_with_escalation(profile: str = "tech_fan", goal: str = "test_functionality"):
    """Run browser test with full escalation support"""
    
    # Create automation with escalation
    automation = BrowserAutomationWithEscalation()
    
    # In real system, Manager Agent would be injected
    manager = ManagerAgentEscalationHandler()
    automation.manager_agent = manager
    
    # Run test
    result = automation.test_corgi_interaction(profile, goal)
    
    print(f"Test result: {result}")
    return result

if __name__ == "__main__":
    run_browser_test_with_escalation() 