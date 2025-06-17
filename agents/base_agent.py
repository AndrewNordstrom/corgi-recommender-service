#!/usr/bin/env python3
"""
Base Agent Class

Standardized base class for all agents in the optimized Corgi system.
Provides common functionality for health checks, logging, and metrics.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AgentResult:
    """Standard result format for agent operations"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    execution_time_ms: Optional[float] = None

class BaseAgent(ABC):
    """Base class for all agents in the optimized system"""
    
    def __init__(self, agent_id: str, name: str, description: str = ""):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"Agent.{name}")
        self.last_execution = None
        self.execution_count = 0
        self.error_count = 0
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup agent-specific logging"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.name} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    @abstractmethod
    async def execute(self) -> AgentResult:
        """Execute the agent's main logic"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Perform health check for the agent"""
        pass
    
    async def run_with_monitoring(self) -> AgentResult:
        """Execute agent with monitoring and error handling"""
        start_time = datetime.now()
        
        try:
            # Check circuit breaker before execution
            circuit_check = self._check_circuit_breaker()
            if not circuit_check['allowed']:
                return AgentResult(
                    success=False,
                    message=f"Agent execution blocked by circuit breaker: {circuit_check['message']}",
                    data={'circuit_breaker': circuit_check},
                    timestamp=start_time,
                    execution_time_ms=0
                )
            
            self.logger.info(f"Starting execution")
            result = await self.execute()
            
            # Update metrics
            self.execution_count += 1
            self.last_execution = start_time
            
            if not result.success:
                self.error_count += 1
                self.logger.warning(f"Execution failed: {result.message}")
            else:
                self.logger.info(f"Execution successful: {result.message}")
            
            # Add timing information
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            result.timestamp = start_time
            result.execution_time_ms = execution_time
            
            return result
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Execution error: {str(e)}")
            
            return AgentResult(
                success=False,
                message=f"Agent execution failed: {str(e)}",
                timestamp=start_time,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and metrics"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.execution_count, 1),
            "status": "healthy" if self.error_count == 0 else "degraded"
        }
    
    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def log_error(self, message: str):
        """Log error message"""
        self.logger.error(message)
    
    def _check_circuit_breaker(self) -> Dict[str, Any]:
        """Check weekly spending circuit breaker"""
        try:
            from agents.weekly_spending_breaker import WeeklySpendingBreaker
            breaker = WeeklySpendingBreaker()
            return breaker.should_allow_execution(self.agent_id)
        except Exception as e:
            self.logger.warning(f"Circuit breaker check failed: {e}")
            # If circuit breaker check fails, allow execution (fail open)
            return {
                'allowed': True,
                'reason': 'circuit_breaker_error',
                'message': f'Circuit breaker check failed: {e}'
            } 