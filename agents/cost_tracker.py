#!/usr/bin/env python3
"""
Cost Tracker Module

Tracks token usage, API calls, and costs across all LLM agents
with budget controls and circuit breaker patterns.
"""

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from functools import wraps
import logging
from contextlib import asynccontextmanager

@dataclass
class APICall:
    """Represents a single API call"""
    agent_id: str
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    duration_ms: int
    success: bool
    error_message: Optional[str] = None

@dataclass
class AgentBudget:
    """Budget allocation for an agent"""
    agent_id: str
    hourly_limit_usd: float
    daily_limit_usd: float
    monthly_limit_usd: float
    hourly_token_limit: int
    daily_token_limit: int
    monthly_token_limit: int
    priority: int  # 1=critical, 2=high, 3=medium, 4=low

@dataclass
class UsageStats:
    """Usage statistics for an agent"""
    agent_id: str
    period: str  # 'hour', 'day', 'month'
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_tokens: int
    total_cost_usd: float
    avg_response_time_ms: float
    last_call: Optional[datetime] = None

class CostTracker:
    """Comprehensive cost tracking and budget management"""
    
    # Claude pricing (as of 2025)
    PRICING = {
        'claude-sonnet-4': {
            'input': 0.003,     # per 1K tokens ($3/million)
            'output': 0.015     # per 1K tokens ($15/million)
        },
        'claude-3-haiku': {
            'input': 0.00025,   # per 1K tokens
            'output': 0.00125   # per 1K tokens
        },
        'claude-3-sonnet': {
            'input': 0.003,     # per 1K tokens
            'output': 0.015     # per 1K tokens
        },
        'claude-3-opus': {
            'input': 0.015,     # per 1K tokens
            'output': 0.075     # per 1K tokens
        }
    }
    
    def __init__(self, db_path: str = "agents/cost_tracking.db"):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self.budgets: Dict[str, AgentBudget] = {}
        self.circuit_breakers: Dict[str, Dict] = {}
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for cost tracking"""
        self.db_path.parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_budgets (
                    agent_id TEXT PRIMARY KEY,
                    hourly_limit_usd REAL NOT NULL,
                    daily_limit_usd REAL NOT NULL,
                    monthly_limit_usd REAL NOT NULL,
                    hourly_token_limit INTEGER NOT NULL,
                    daily_token_limit INTEGER NOT NULL,
                    monthly_token_limit INTEGER NOT NULL,
                    priority INTEGER NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_timestamp 
                ON api_calls(agent_id, timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON api_calls(timestamp)
            """)
    
    def set_agent_budget(self, budget: AgentBudget):
        """Set budget limits for an agent"""
        self.budgets[budget.agent_id] = budget
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agent_budgets 
                (agent_id, hourly_limit_usd, daily_limit_usd, monthly_limit_usd,
                 hourly_token_limit, daily_token_limit, monthly_token_limit, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                budget.agent_id, budget.hourly_limit_usd, budget.daily_limit_usd,
                budget.monthly_limit_usd, budget.hourly_token_limit,
                budget.daily_token_limit, budget.monthly_token_limit, budget.priority
            ))
    
    def load_budgets(self):
        """Load agent budgets from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM agent_budgets")
            for row in cursor.fetchall():
                budget = AgentBudget(
                    agent_id=row[0],
                    hourly_limit_usd=row[1],
                    daily_limit_usd=row[2],
                    monthly_limit_usd=row[3],
                    hourly_token_limit=row[4],
                    daily_token_limit=row[5],
                    monthly_token_limit=row[6],
                    priority=row[7]
                )
                self.budgets[budget.agent_id] = budget
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for API call"""
        if model not in self.PRICING:
            self.logger.warning(f"Unknown model {model}, using sonnet pricing")
            model = 'claude-sonnet-4'
        
        pricing = self.PRICING[model]
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        
        return input_cost + output_cost
    
    def record_api_call(self, call: APICall):
        """Record an API call in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO api_calls 
                (agent_id, timestamp, model, input_tokens, output_tokens, 
                 total_tokens, cost_usd, duration_ms, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                call.agent_id, call.timestamp.isoformat(), call.model,
                call.input_tokens, call.output_tokens, call.total_tokens,
                call.cost_usd, call.duration_ms, call.success, call.error_message
            ))
    
    def check_budget_limits(self, agent_id: str, estimated_cost: float = 0) -> Dict[str, Any]:
        """Check if agent is within budget limits"""
        if agent_id not in self.budgets:
            return {"allowed": True, "reason": "no_budget_set"}
        
        budget = self.budgets[agent_id]
        now = datetime.now()
        
        # Get current usage
        hourly_usage = self.get_usage_stats(agent_id, 'hour')
        daily_usage = self.get_usage_stats(agent_id, 'day')
        monthly_usage = self.get_usage_stats(agent_id, 'month')
        
        # Check cost limits
        if hourly_usage.total_cost_usd + estimated_cost > budget.hourly_limit_usd:
            return {
                "allowed": False,
                "reason": "hourly_cost_limit",
                "current": hourly_usage.total_cost_usd,
                "limit": budget.hourly_limit_usd,
                "estimated": estimated_cost
            }
        
        if daily_usage.total_cost_usd + estimated_cost > budget.daily_limit_usd:
            return {
                "allowed": False,
                "reason": "daily_cost_limit",
                "current": daily_usage.total_cost_usd,
                "limit": budget.daily_limit_usd,
                "estimated": estimated_cost
            }
        
        if monthly_usage.total_cost_usd + estimated_cost > budget.monthly_limit_usd:
            return {
                "allowed": False,
                "reason": "monthly_cost_limit",
                "current": monthly_usage.total_cost_usd,
                "limit": budget.monthly_limit_usd,
                "estimated": estimated_cost
            }
        
        # Check token limits (estimate tokens from cost)
        estimated_tokens = int(estimated_cost / 0.003 * 1000)  # Rough estimate
        
        if hourly_usage.total_tokens + estimated_tokens > budget.hourly_token_limit:
            return {
                "allowed": False,
                "reason": "hourly_token_limit",
                "current": hourly_usage.total_tokens,
                "limit": budget.hourly_token_limit,
                "estimated": estimated_tokens
            }
        
        return {"allowed": True}
    
    def get_usage_stats(self, agent_id: str, period: str) -> UsageStats:
        """Get usage statistics for an agent in a time period"""
        now = datetime.now()
        
        if period == 'hour':
            start_time = now - timedelta(hours=1)
        elif period == 'day':
            start_time = now - timedelta(days=1)
        elif period == 'month':
            start_time = now - timedelta(days=30)
        else:
            raise ValueError(f"Invalid period: {period}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_calls,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost_usd) as total_cost,
                    AVG(duration_ms) as avg_duration,
                    MAX(timestamp) as last_call
                FROM api_calls 
                WHERE agent_id = ? AND timestamp >= ?
            """, (agent_id, start_time.isoformat()))
            
            row = cursor.fetchone()
            
            return UsageStats(
                agent_id=agent_id,
                period=period,
                total_calls=row[0] or 0,
                successful_calls=row[1] or 0,
                failed_calls=row[2] or 0,
                total_tokens=row[3] or 0,
                total_cost_usd=row[4] or 0.0,
                avg_response_time_ms=row[5] or 0.0,
                last_call=datetime.fromisoformat(row[6]) if row[6] else None
            )
    
    def get_all_agents_usage(self, period: str) -> List[UsageStats]:
        """Get usage stats for all agents"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT DISTINCT agent_id FROM api_calls")
            agent_ids = [row[0] for row in cursor.fetchall()]
        
        return [self.get_usage_stats(agent_id, period) for agent_id in agent_ids]
    
    def check_circuit_breaker(self, agent_id: str) -> Dict[str, Any]:
        """Check if agent should be circuit broken due to failures"""
        if agent_id not in self.circuit_breakers:
            self.circuit_breakers[agent_id] = {
                "consecutive_failures": 0,
                "last_failure": None,
                "is_open": False,
                "last_opened": None
            }
        
        breaker = self.circuit_breakers[agent_id]
        
        # If circuit is open, check if we should try again
        if breaker["is_open"]:
            if breaker["last_opened"]:
                time_since_open = datetime.now() - breaker["last_opened"]
                if time_since_open > timedelta(minutes=5):  # Try again after 5 minutes
                    breaker["is_open"] = False
                    breaker["consecutive_failures"] = 0
                    return {"allowed": True, "reason": "circuit_reset"}
            
            return {
                "allowed": False,
                "reason": "circuit_breaker_open",
                "failures": breaker["consecutive_failures"],
                "last_opened": breaker["last_opened"]
            }
        
        return {"allowed": True}
    
    def record_failure(self, agent_id: str):
        """Record a failure for circuit breaker logic"""
        if agent_id not in self.circuit_breakers:
            self.circuit_breakers[agent_id] = {
                "consecutive_failures": 0,
                "last_failure": None,
                "is_open": False,
                "last_opened": None
            }
        
        breaker = self.circuit_breakers[agent_id]
        breaker["consecutive_failures"] += 1
        breaker["last_failure"] = datetime.now()
        
        # Open circuit after 5 consecutive failures
        if breaker["consecutive_failures"] >= 5:
            breaker["is_open"] = True
            breaker["last_opened"] = datetime.now()
            self.logger.warning(f"Circuit breaker opened for agent {agent_id}")
    
    def record_success(self, agent_id: str):
        """Record a success for circuit breaker logic"""
        if agent_id in self.circuit_breakers:
            self.circuit_breakers[agent_id]["consecutive_failures"] = 0
    
    def get_cost_summary(self, period: str = 'day') -> Dict[str, Any]:
        """Get comprehensive cost summary"""
        all_usage = self.get_all_agents_usage(period)
        
        total_cost = sum(usage.total_cost_usd for usage in all_usage)
        total_tokens = sum(usage.total_tokens for usage in all_usage)
        total_calls = sum(usage.total_calls for usage in all_usage)
        
        # Sort by cost descending
        top_agents = sorted(all_usage, key=lambda x: x.total_cost_usd, reverse=True)
        
        return {
            "period": period,
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "total_calls": total_calls,
            "agent_count": len(all_usage),
            "top_agents": top_agents[:5],  # Top 5 by cost
            "timestamp": datetime.now().isoformat()
        }

def track_llm_call(cost_tracker: CostTracker):
    """Decorator to track LLM API calls"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            agent_id = getattr(self, 'agent_id', 'unknown')
            start_time = time.time()
            
            # Check budget and circuit breaker before call
            budget_check = cost_tracker.check_budget_limits(agent_id)
            if not budget_check["allowed"]:
                raise Exception(f"Budget limit exceeded: {budget_check['reason']}")
            
            circuit_check = cost_tracker.check_circuit_breaker(agent_id)
            if not circuit_check["allowed"]:
                raise Exception(f"Circuit breaker open: {circuit_check['reason']}")
            
            try:
                # Make the API call
                result = await func(self, *args, **kwargs)
                
                # Extract usage info from result (this would need to be adapted)
                # For now, we'll estimate based on response
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Estimate tokens (would need actual token counting)
                estimated_input = len(str(args) + str(kwargs)) // 4
                estimated_output = len(str(result)) // 4
                estimated_cost = cost_tracker.calculate_cost(
                    'claude-sonnet-4', estimated_input, estimated_output
                )
                
                # Record successful call
                call = APICall(
                    agent_id=agent_id,
                    timestamp=datetime.now(),
                    model='claude-sonnet-4',
                    input_tokens=estimated_input,
                    output_tokens=estimated_output,
                    total_tokens=estimated_input + estimated_output,
                    cost_usd=estimated_cost,
                    duration_ms=duration_ms,
                    success=True
                )
                
                cost_tracker.record_api_call(call)
                cost_tracker.record_success(agent_id)
                
                return result
                
            except Exception as e:
                # Record failed call
                duration_ms = int((time.time() - start_time) * 1000)
                
                call = APICall(
                    agent_id=agent_id,
                    timestamp=datetime.now(),
                    model='claude-sonnet-4',
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    cost_usd=0.0,
                    duration_ms=duration_ms,
                    success=False,
                    error_message=str(e)
                )
                
                cost_tracker.record_api_call(call)
                cost_tracker.record_failure(agent_id)
                
                raise
        
        return wrapper
    return decorator

# Global cost tracker instance
cost_tracker = CostTracker()

if __name__ == "__main__":
    # Test the cost tracker
    tracker = CostTracker()
    
    # Set up test budget
    budget = AgentBudget(
        agent_id="test_agent",
        hourly_limit_usd=1.0,
        daily_limit_usd=10.0,
        monthly_limit_usd=100.0,
        hourly_token_limit=10000,
        daily_token_limit=100000,
        monthly_token_limit=1000000,
        priority=2
    )
    tracker.set_agent_budget(budget)
    
    # Test API call recording
    call = APICall(
        agent_id="test_agent",
        timestamp=datetime.now(),
        model="claude-sonnet-4",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        cost_usd=0.45,
        duration_ms=1500,
        success=True
    )
    tracker.record_api_call(call)
    
    # Get usage stats
    stats = tracker.get_usage_stats("test_agent", "hour")
    print(f"Usage stats: {stats}")
    
    # Get cost summary
    summary = tracker.get_cost_summary("day")
    print(f"Cost summary: {summary}") 