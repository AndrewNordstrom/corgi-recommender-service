import json
import os
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

class FeedbackModule:
    """Module for handling agent-generated feedback about the Corgi Recommender."""
    
    def __init__(self, feedback_dir: str = None, api_base_url: str = None):
        """Initialize the feedback module.
        
        Args:
            feedback_dir: Directory to store feedback files (defaults to 'logs/agent_feedback')
            api_base_url: Base URL for the Corgi Recommender API
        """
        self.feedback_dir = feedback_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "logs", "agent_feedback"
        )
        os.makedirs(self.feedback_dir, exist_ok=True)
        
        # Set up API URL
        self.api_base_url = api_base_url or os.environ.get("CORGI_SERVICE_URL", "http://localhost:5000")
        
        # Set up logging
        self.logger = logging.getLogger("agent_feedback")
        self.logger.setLevel(logging.DEBUG)
        
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def record_feedback(self, 
                        session_id: str, 
                        user_id: str, 
                        post_id: str, 
                        feedback_text: str, 
                        submit_to_api: bool = False) -> Dict[str, Any]:
        """Record feedback from an agent session.
        
        Args:
            session_id: ID of the agent session that generated this feedback
            user_id: ID of the user profile providing feedback
            post_id: ID of the post being rated
            feedback_text: Natural language feedback about the post
            submit_to_api: Whether to submit feedback to the API (default: False)
            
        Returns:
            Dictionary containing feedback record and submission status
        """
        timestamp = datetime.now().isoformat()
        
        # Create complete feedback record
        feedback_record = {
            "session_id": session_id,
            "user_id": user_id,
            "post_id": post_id,
            "timestamp": timestamp,
            "feedback_text": feedback_text,
            "submitted_to_api": False,
            "api_response": None
        }
        
        # Log the feedback
        self.logger.info(f"Feedback from {user_id} on post {post_id}: {feedback_text}")
        
        # Optionally submit to the API
        if submit_to_api:
            try:
                submission_result = self.submit_feedback_to_api(user_id, post_id, feedback_text)
                feedback_record["submitted_to_api"] = True
                feedback_record["api_response"] = submission_result
            except Exception as e:
                self.logger.error(f"Error submitting feedback to API: {str(e)}")
                feedback_record["api_error"] = str(e)
        
        # Save to file
        self._save_feedback_to_file(feedback_record)
        
        return feedback_record
    
    def submit_feedback_to_api(self, user_id: str, post_id: str, feedback_text: str) -> Dict[str, Any]:
        """Submit feedback to the Corgi Recommender API.
        
        Args:
            user_id: ID of the user providing feedback
            post_id: ID of the post being rated
            feedback_text: Natural language feedback text
            
        Returns:
            API response data
        """
        endpoint = f"{self.api_base_url}/api/v1/interactions"
        
        # Determine action type based on feedback sentiment (simplified implementation)
        action_type = "more_like_this"
        if any(negative in feedback_text.lower() for negative in ["not", "don't", "dislike", "irrelevant"]):
            action_type = "less_like_this"
        
        # Prepare payload
        payload = {
            "user_alias": user_id,
            "post_id": post_id,
            "action_type": action_type,
            "context": {
                "source": "agent_feedback",
                "feedback_text": feedback_text
            }
        }
        
        # Log the API call attempt
        self.logger.info(f"Submitting feedback to {endpoint}: {json.dumps(payload)}")
        
        # Submit to API
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Process response
        if response.status_code == 200:
            self.logger.info(f"Successfully submitted feedback: {response.status_code}")
            return response.json()
        else:
            error_msg = f"Error submitting feedback: {response.status_code} - {response.text}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _save_feedback_to_file(self, feedback_record: Dict[str, Any]) -> str:
        """Save a feedback record to a JSON file.
        
        Args:
            feedback_record: Dictionary containing the feedback data
            
        Returns:
            Path to the saved file
        """
        session_id = feedback_record["session_id"]
        timestamp = feedback_record["timestamp"].replace(":", "-")
        
        # Generate unique filename
        filename = f"feedback_{session_id}_{timestamp}.json"
        filepath = os.path.join(self.feedback_dir, filename)
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(feedback_record, f, indent=2)
        
        self.logger.info(f"Saved feedback to {filepath}")
        return filepath
    
    def update_privacy_settings(self, user_id: str, tracking_level: str) -> Dict[str, Any]:
        """Update a user's privacy settings.
        
        Args:
            user_id: ID of the user to update settings for
            tracking_level: New privacy level ('full', 'limited', or 'none')
            
        Returns:
            API response data
        """
        if tracking_level not in ["full", "limited", "none"]:
            raise ValueError(f"Invalid tracking level: {tracking_level}. Must be 'full', 'limited', or 'none'.")
        
        endpoint = f"{self.api_base_url}/api/v1/privacy"
        
        # Prepare payload
        payload = {
            "user_id": user_id,
            "tracking_level": tracking_level
        }
        
        # Log the API call attempt
        self.logger.info(f"Updating privacy settings for {user_id} to {tracking_level}")
        
        # Submit to API
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Process response
        if response.status_code == 200:
            response_data = response.json()
            self.logger.info(f"Successfully updated privacy settings: {response.status_code}")
            
            # Log the privacy change
            self._log_privacy_change(user_id, tracking_level, response_data)
            
            return response_data
        else:
            error_msg = f"Error updating privacy settings: {response.status_code} - {response.text}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_privacy_settings(self, user_id: str) -> Dict[str, Any]:
        """Get a user's current privacy settings.
        
        Args:
            user_id: ID of the user to get settings for
            
        Returns:
            Dictionary with user's privacy settings
        """
        endpoint = f"{self.api_base_url}/api/v1/privacy?user_id={user_id}"
        
        # Log the API call attempt
        self.logger.info(f"Getting privacy settings for {user_id}")
        
        # Submit to API
        response = requests.get(endpoint)
        
        # Process response
        if response.status_code == 200:
            response_data = response.json()
            self.logger.info(f"Got privacy settings for {user_id}: {response_data['tracking_level']}")
            return response_data
        else:
            error_msg = f"Error getting privacy settings: {response.status_code} - {response.text}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _log_privacy_change(self, user_id: str, new_level: str, response_data: Dict[str, Any]) -> None:
        """Log a privacy setting change.
        
        Args:
            user_id: ID of the user whose settings were changed
            new_level: New privacy level
            response_data: API response data
        """
        timestamp = datetime.now().isoformat()
        
        # Create privacy change record
        privacy_record = {
            "user_id": user_id,
            "timestamp": timestamp,
            "new_tracking_level": new_level,
            "api_response": response_data
        }
        
        # Generate unique filename
        filename = f"privacy_change_{user_id}_{timestamp.replace(':', '-')}.json"
        filepath = os.path.join(self.feedback_dir, filename)
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(privacy_record, f, indent=2)
        
        self.logger.info(f"Logged privacy change to {filepath}")
    
    def analyze_recent_feedback(self, limit: int = 10) -> Dict[str, Any]:
        """Analyze recent feedback to extract patterns and insights.
        
        Args:
            limit: Maximum number of recent feedback entries to analyze
            
        Returns:
            Analysis results as a dictionary
        """
        # Get recent feedback files
        feedback_files = []
        for filename in os.listdir(self.feedback_dir):
            if filename.startswith("feedback_") and filename.endswith(".json"):
                filepath = os.path.join(self.feedback_dir, filename)
                feedback_files.append((filepath, os.path.getmtime(filepath)))
        
        # Sort by modification time (newest first) and limit
        feedback_files.sort(key=lambda x: x[1], reverse=True)
        feedback_files = feedback_files[:limit]
        
        # Load feedback records
        feedback_records = []
        for filepath, _ in feedback_files:
            try:
                with open(filepath, 'r') as f:
                    record = json.load(f)
                    feedback_records.append(record)
            except Exception as e:
                self.logger.error(f"Error loading feedback file {filepath}: {str(e)}")
        
        # Basic analysis (could be extended with more sophisticated techniques)
        positive_count = 0
        negative_count = 0
        topics_mentioned = {}
        
        for record in feedback_records:
            feedback_text = record.get("feedback_text", "").lower()
            
            # Simple sentiment analysis
            if any(positive in feedback_text for positive in ["great", "good", "like", "excellent", "love"]):
                positive_count += 1
            elif any(negative in feedback_text for negative in ["bad", "poor", "don't like", "irrelevant"]):
                negative_count += 1
            
            # Basic topic extraction
            common_topics = ["tech", "news", "programming", "linux", "privacy", "meme", "funny", "corgi"]
            for topic in common_topics:
                if topic in feedback_text:
                    topics_mentioned[topic] = topics_mentioned.get(topic, 0) + 1
        
        # Compile results
        analysis_results = {
            "total_feedback_analyzed": len(feedback_records),
            "positive_feedback": positive_count,
            "negative_feedback": negative_count,
            "neutral_feedback": len(feedback_records) - positive_count - negative_count,
            "topics_mentioned": topics_mentioned,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"Analyzed {len(feedback_records)} recent feedback entries")
        return analysis_results
    
    def get_feedback_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all feedback records for a particular session.
        
        Args:
            session_id: ID of the session to retrieve feedback for
            
        Returns:
            List of feedback records for the session
        """
        feedback_records = []
        
        # Attempt to find all feedback files for this session
        for filename in os.listdir(self.feedback_dir):
            if session_id in filename and filename.endswith('.json'):
                filepath = os.path.join(self.feedback_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        feedback_record = json.load(f)
                        feedback_records.append(feedback_record)
                except Exception as e:
                    self.logger.error(f"Error loading feedback file {filepath}: {str(e)}")
        
        return feedback_records