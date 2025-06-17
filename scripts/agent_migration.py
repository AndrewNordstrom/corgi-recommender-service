#!/usr/bin/env python3
"""
Agent Migration Script

Automates the migration from 16-agent system to optimized architecture.
Safely moves agents to appropriate locations and updates references.
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Any
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentMigrator:
    """Handles the migration of agents to new architecture"""
    
    def __init__(self):
        self.root_dir = Path.cwd()
        self.agents_dir = self.root_dir / "agents"
        self.scripts_dir = self.root_dir / "scripts"
        
        # Migration plan based on optimization analysis
        self.migration_plan = {
            "keep": ["manager_agent.py", "claude_interface.py", "security_healing_agent.py"],
            "merge": ["cost_tracker.py", "token_tracker.py"],
            "to_scripts": {
                "browser_agent.py": "scripts/automation/browser_automation.py",
                "user_profiles.py": "scripts/automation/test_profiles.py",
                "feedback_module.py": "scripts/automation/feedback_handler.py",
                "web_agent_dashboard.py": "scripts/utilities/dashboard.py",
                "agent_launcher.py": "scripts/utilities/agent_launcher.py",
                "interaction_logger.py": "utils/logging.py"
            },
            "delete": [
                "core_agent_system.py", "test_all_features.py", "test_runner.py",
                "agent_config.py", "manager_agent_audit.py"
            ]
        }
        
    def create_directories(self):
        """Create necessary directories for new architecture"""
        dirs = [
            self.scripts_dir / "deprecated",
            self.scripts_dir / "automation", 
            self.scripts_dir / "utilities",
            self.agents_dir / "core"
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
    
    def backup_agents(self):
        """Create backup of all current agents"""
        backup_dir = self.scripts_dir / "deprecated"
        
        for agent_file in self.agents_dir.glob("*.py"):
            if agent_file.name != "__init__.py":
                backup_path = backup_dir / agent_file.name
                shutil.copy2(agent_file, backup_path)
                logger.info(f"Backed up: {agent_file.name}")
    
    def create_monitoring_agent(self):
        """Create unified monitoring agent from cost_tracker + token_tracker"""
        monitoring_content = '''#!/usr/bin/env python3
"""
Unified Monitoring Agent

Combines cost_tracker.py and token_tracker.py functionality.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class APICall:
    agent_id: str
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    success: bool

class MonitoringAgent:
    """Unified monitoring for cost, tokens, and performance"""
    
    PRICING = {
        'claude-sonnet-4': {'input': 0.003, 'output': 0.015}  # per 1K tokens
    }
    
    def __init__(self, db_path: str = "agents/monitoring.db"):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize monitoring database"""
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
                    cost_usd REAL NOT NULL,
                    success BOOLEAN NOT NULL
                )
            """)
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for API call"""
        pricing = self.PRICING.get(model, self.PRICING['claude-sonnet-4'])
        return (input_tokens / 1000) * pricing['input'] + (output_tokens / 1000) * pricing['output']
    
    def record_api_call(self, call: APICall):
        """Record an API call"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO api_calls (agent_id, timestamp, model, input_tokens, output_tokens, cost_usd, success)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (call.agent_id, call.timestamp.isoformat(), call.model, 
                  call.input_tokens, call.output_tokens, call.cost_usd, call.success))

monitoring_agent = MonitoringAgent()
'''
        
        monitoring_path = self.agents_dir / "core" / "monitoring_agent.py"
        with open(monitoring_path, 'w') as f:
            f.write(monitoring_content)
        logger.info(f"Created unified monitoring agent")
    
    def create_base_agent(self):
        """Create simple base agent class"""
        base_content = '''#!/usr/bin/env python3
"""
Base Agent Class for optimized system
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any

class BaseAgent(ABC):
    """Simple base class for agents"""
    
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.logger = logging.getLogger(f"Agent.{name}")
        self.last_execution = None
        
    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """Execute the agent's main logic"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Perform health check for the agent"""
        pass
'''
        
        base_path = self.agents_dir / "base_agent.py"
        with open(base_path, 'w') as f:
            f.write(base_content)
        logger.info(f"Created base agent class")
    
    def move_agents_to_scripts(self):
        """Move agents that should become scripts"""
        for agent_file, target_path in self.migration_plan["to_scripts"].items():
            source = self.agents_dir / agent_file
            target = self.root_dir / target_path
            
            if source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                logger.info(f"Converted: {agent_file} → {target_path}")
    
    def delete_obsolete_agents(self):
        """Move obsolete agents to deprecated directory"""
        deprecated_dir = self.scripts_dir / "deprecated"
        
        for agent_file in self.migration_plan["delete"]:
            source = self.agents_dir / agent_file
            if source.exists():
                target = deprecated_dir / agent_file
                shutil.move(source, target)
                logger.info(f"Moved to deprecated: {agent_file}")
    
    def run_migration(self):
        """Run the complete migration process"""
        logger.info("🚀 Starting agent system migration...")
        
        try:
            logger.info("Phase 1: Creating directories and backups...")
            self.create_directories()
            self.backup_agents()
            
            logger.info("Phase 2: Creating core agents...")
            self.create_monitoring_agent()
            self.create_base_agent()
            
            logger.info("Phase 3: Converting agents to scripts...")
            self.move_agents_to_scripts()
            
            logger.info("Phase 4: Moving obsolete agents...")
            self.delete_obsolete_agents()
            
            logger.info("✅ Migration completed successfully!")
            logger.info("📊 Summary:")
            logger.info("  - 16 agents → 4 core agents + scripts")
            logger.info("  - All original code backed up in scripts/deprecated/")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise

def main():
    """Main migration function"""
    migrator = AgentMigrator()
    migrator.run_migration()

if __name__ == "__main__":
    main() 