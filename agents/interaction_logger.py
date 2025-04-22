import json
import time
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

class InteractionLogger:
    """Logger for tracking agent interactions with the Corgi Recommender."""
    
    def __init__(self, log_dir: str = None):
        """Initialize the interaction logger.
        
        Args:
            log_dir: Directory to store log files (defaults to 'logs/agent_sessions')
        """
        self.log_dir = log_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "agent_sessions")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Initialize the logger
        self.logger = logging.getLogger("agent_interactions")
        self.logger.setLevel(logging.DEBUG)
        
        # Ensure we don't add duplicate handlers on reinitialization
        if not self.logger.handlers:
            # Console handler for immediate visibility
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # In-memory storage of logs by session
        self.sessions = {}
    
    def start_session(self, session_id: str, goal: str) -> None:
        """Initialize a new logging session.
        
        Args:
            session_id: Unique identifier for this session
            goal: The objective for this session
        """
        timestamp = datetime.now().isoformat()
        
        # Create session log file
        session_log_path = os.path.join(self.log_dir, f"{session_id}.log")
        file_handler = logging.FileHandler(session_log_path)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Initialize in-memory session storage
        self.sessions[session_id] = {
            "session_id": session_id,
            "goal": goal,
            "start_time": timestamp,
            "actions": []
        }
        
        self.logger.info(f"Started session {session_id} with goal: {goal}")
    
    def log_action(self, action_type: str, details: Dict[str, Any], session_id: Optional[str] = None) -> None:
        """Log an action taken by the agent.
        
        Args:
            action_type: Type of action (e.g., 'click', 'scroll', 'favorite')
            details: Dictionary with action details
            session_id: Optional session ID (uses current session if None)
        """
        timestamp = datetime.now().isoformat()
        
        # Use the provided session_id or the last one if available
        if session_id is None and hasattr(self, 'session_id') and self.session_id:
            session_id = self.session_id
        elif session_id is None and self.sessions:
            # Fall back to the most recent session if we have any
            session_id = list(self.sessions.keys())[-1]
        
        if not session_id or session_id not in self.sessions:
            self.logger.warning(f"No active session for logging action {action_type}")
            return
        
        # Create the log entry
        log_entry = {
            "timestamp": timestamp,
            "action_type": action_type,
            "details": details
        }
        
        # Add to in-memory storage
        self.sessions[session_id]["actions"].append(log_entry)
        
        # Log to the file and console
        log_message = f"Session {session_id} - {action_type}: {json.dumps(details)}"
        self.logger.info(log_message)
    
    def end_session(self, session_id: str, summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """End a logging session and return the complete log.
        
        Args:
            session_id: ID of the session to end
            summary: Optional summary information about the session
            
        Returns:
            The complete session log dictionary
        """
        if session_id not in self.sessions:
            self.logger.warning(f"Cannot end nonexistent session {session_id}")
            return {}
        
        timestamp = datetime.now().isoformat()
        
        # Update session with end time and summary
        self.sessions[session_id]["end_time"] = timestamp
        if summary:
            self.sessions[session_id]["summary"] = summary
        
        # Calculate session duration
        start_time = datetime.fromisoformat(self.sessions[session_id]["start_time"])
        end_time = datetime.fromisoformat(timestamp)
        duration = (end_time - start_time).total_seconds()
        self.sessions[session_id]["duration_seconds"] = duration
        
        # Log completion
        self.logger.info(
            f"Ended session {session_id}. "
            f"Duration: {duration:.2f}s. "
            f"Actions: {len(self.sessions[session_id]['actions'])}"
        )
        
        # Save complete log to JSON file
        self._save_session_json(session_id)
        
        # Return the complete log
        return self.sessions[session_id]
    
    def get_session_logs(self, session_id: str) -> Dict[str, Any]:
        """Get the complete logs for a session.
        
        Args:
            session_id: ID of the session to retrieve
            
        Returns:
            Dictionary containing the session logs
        """
        if session_id not in self.sessions:
            self.logger.warning(f"Requested logs for nonexistent session {session_id}")
            return {}
        
        return self.sessions[session_id]
    
    def _save_session_json(self, session_id: str) -> str:
        """Save a session's logs to a JSON file.
        
        Args:
            session_id: ID of the session to save
            
        Returns:
            Path to the saved JSON file
        """
        if session_id not in self.sessions:
            self.logger.warning(f"Cannot save nonexistent session {session_id}")
            return ""
        
        json_path = os.path.join(self.log_dir, f"{session_id}.json")
        
        with open(json_path, 'w') as f:
            json.dump(self.sessions[session_id], f, indent=2)
        
        self.logger.info(f"Saved session logs to {json_path}")
        return json_path
