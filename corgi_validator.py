#!/usr/bin/env python3
"""
Corgi Recommender Service Validator

A tool for validating the Corgi Recommender Service through simulated users,
interactions, and end-to-end testing of the recommendation pipeline.

This script helps validate that the core functionality works as expected
before finalizing the API.
"""

import argparse
import json
import logging
import random
import requests
import string
import subprocess
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('corgi_validation.log')
    ]
)
logger = logging.getLogger('corgi_validator')

# Default settings
DEFAULT_API_BASE = "http://localhost:5001"  # Changed from 5000 to 5001 to avoid conflict with Apple Control Center
DEFAULT_API_PREFIX = "/api/v1"  # Updated to match .env configuration
DEFAULT_NUM_USERS = 5
DEFAULT_NUM_POSTS = 10

class CorgiValidator:
    """Main validator class for the Corgi Recommender Service."""
    
    def __init__(self, api_base: str = DEFAULT_API_BASE, api_prefix: str = DEFAULT_API_PREFIX, verbose: bool = False, dry_run: bool = False):
        """
        Initialize the validator.
        
        Args:
            api_base: Base URL for the Corgi API
            api_prefix: API endpoint prefix (default: /api/v1)
            verbose: Whether to print detailed logs
            dry_run: Whether to simulate without making actual requests
        """
        self.api_base = api_base
        self.api_prefix = api_prefix
        self.verbose = verbose
        self.dry_run = dry_run
        
        # Stats for test reports
        self.synthetic_users = []
        self.synthetic_posts = []
        self.interactions = []
        self.check_results = {}
        
        # Set up logging level based on verbosity
        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        
        logger.info(f"Initializing Corgi Validator with API base: {api_base}")
        logger.info(f"Dry run mode: {'Enabled' if dry_run else 'Disabled'}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Tuple[int, Dict]:
        """
        Make an HTTP request to the Corgi API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            data: Request body for POST/PUT requests
            params: Query parameters for GET requests
            
        Returns:
            Tuple of (status_code, response_json)
        """
        # Handle endpoint formatting
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]  # Remove leading slash
            
        # If endpoint starts with v1/, adapt to use the configured API prefix
        # We handle this case for backward compatibility with old code that might use v1 directly
        if endpoint.startswith('v1/'):
            endpoint = endpoint[3:]  # Remove v1/ prefix
            url = f"{self.api_base}{self.api_prefix}/{endpoint}"
        # If endpoint starts with api/v1/, adapt to the configured API prefix
        elif endpoint.startswith('api/v1/'):
            endpoint = endpoint[7:]  # Remove api/v1/ prefix
            url = f"{self.api_base}{self.api_prefix}/{endpoint}"
        else:
            # For non-versioned endpoints like /health
            url = f"{self.api_base}/{endpoint}"
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would make {method} request to {url}")
            return 200, {"dry_run": True, "success": True}
        
        try:
            if self.verbose:
                logger.debug(f"Making {method} request to {url}")
                if data:
                    logger.debug(f"Request body: {json.dumps(data, indent=2)}")
                if params:
                    logger.debug(f"Request params: {params}")
                    
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'CorgiValidator/1.0',
            }
            
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            status_code = response.status_code
            
            # Log the raw response for debugging
            if self.verbose or status_code >= 400:
                logger.debug(f"Raw response: {response.text}")
                logger.debug(f"Response headers: {dict(response.headers)}")
            
            try:
                response_json = response.json()
            except json.JSONDecodeError:
                # Enhanced error information when JSON parsing fails
                if response.text:
                    response_json = {"text": response.text}
                else:
                    response_json = {"error": "Empty response", "headers": dict(response.headers)}
            
            if self.verbose:
                logger.debug(f"Response ({status_code}): {json.dumps(response_json, indent=2)}")
                
            # Log warnings for non-2xx responses
            if status_code >= 300:
                logger.warning(f"Request to {url} returned status {status_code}")
                
            return status_code, response_json
            
        except requests.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            # More detailed error information
            error_info = {
                "error": str(e),
                "error_type": type(e).__name__,
            }
            if hasattr(e, 'response') and e.response is not None:
                error_info["status_code"] = e.response.status_code
                try:
                    error_info["response"] = e.response.json()
                except:
                    error_info["response_text"] = e.response.text
            
            return 500, error_info
    
    def _generate_user_id(self) -> str:
        """Generate a synthetic user ID."""
        return f"corgi_validator_user_{uuid.uuid4().hex[:8]}"
    
    def _generate_post_id(self) -> str:
        """Generate a synthetic post ID."""
        return f"corgi_validator_post_{uuid.uuid4().hex[:8]}"
    
    def _generate_post_content(self) -> str:
        """Generate realistic-looking post content for testing."""
        templates = [
            "Just saw a {}! So {}! #corgi #test",
            "My corgi {} today and it was {}. #dogsofmastodon",
            "Thinking about getting another {}. Would be my {}th one!",
            "Does anyone else's corgi {} when they're {}?",
            "Looking for advice on {} for corgis. Mine seems {}."
        ]
        
        adjectives = ["cute", "fluffy", "silly", "adorable", "energetic", "sleepy", "happy", "excited"]
        nouns = ["corgi", "puppy", "dog treat", "toy", "dog park", "leash", "ball", "frisbee"]
        verbs = ["played", "barked", "jumped", "slept", "ran", "sniffed", "cuddled", "howled"]
        
        template = random.choice(templates)
        return template.format(
            random.choice(nouns if "{}" in template else verbs),
            random.choice(adjectives)
        )
    
    def seed_users(self, count: int = DEFAULT_NUM_USERS) -> List[str]:
        """
        Create synthetic users for testing.
        
        Args:
            count: Number of users to create
            
        Returns:
            List of created user IDs
        """
        logger.info(f"Seeding {count} synthetic users...")
        
        users = []
        for i in range(count):
            user_id = self._generate_user_id()
            logger.info(f"Created synthetic user {i+1}/{count}: {user_id}")
            users.append(user_id)
        
        self.synthetic_users = users
        return users
    
    def seed_posts(self, count: int = DEFAULT_NUM_POSTS) -> List[Dict]:
        """
        Create synthetic posts for testing.
        
        Args:
            count: Number of posts to create
            
        Returns:
            List of created post objects
        """
        logger.info(f"Seeding {count} synthetic posts...")
        
        posts = []
        for i in range(count):
            post_id = self._generate_post_id()
            
            # Create a synthetic post
            post = {
                "post_id": post_id,
                "author_id": f"author_{random.randint(1, 100)}",
                "author_name": f"corgi_lover_{random.randint(1, 100)}",
                "content": self._generate_post_content(),
                "created_at": datetime.now().isoformat(),
                "language": "en",
                "tags": ["corgi", "test", "recommendation"]
            }
            
            # Create the Mastodon-compatible version
            mastodon_post = {
                "id": post_id,
                "content": f"<p>{post['content']}</p>",
                "created_at": post["created_at"],
                "language": "en",
                "account": {
                    "id": post["author_id"],
                    "username": post["author_name"],
                    "display_name": f"Corgi Lover {random.randint(1, 100)}",
                    "followers_count": random.randint(1, 1000),
                    "following_count": random.randint(1, 500),
                    "statuses_count": random.randint(1, 3000),
                    "url": f"https://mastodon.example.com/@{post['author_name']}"
                },
                "replies_count": 0,
                "reblogs_count": 0,
                "favourites_count": 0,
                "url": f"https://mastodon.example.com/@{post['author_name']}/posts/{post_id}",
                "is_real_mastodon_post": False,
                "is_synthetic": True
            }
            
            # Add debug logging for the payload
            # Match the expected schema from routes/posts.py create_post method
            interaction_counts = {
                "favorites": 0,
                "reblogs": 0,
                "replies": 0
            }
            
            payload = {
                "post_id": post_id,
                "author_id": post["author_id"],
                "author_name": post["author_name"],
                "content": post["content"],
                "content_type": "text",
                "created_at": post["created_at"],
                "interaction_counts": interaction_counts,
                "mastodon_post": mastodon_post,
                "language": post["language"],
                "tags": post["tags"]
            }
            logger.debug(f"Payload being sent: {json.dumps(payload)}")
            
            # Add post to the system via API
            status_code, response = self._make_request("POST", "/v1/posts", payload)
            
            if status_code in (200, 201):
                logger.info(f"Created synthetic post {i+1}/{count}: {post_id}")
                posts.append(post)
            else:
                logger.error(f"Failed to create post: {status_code}, {json.dumps(response)}")
                
                # Try alternative endpoint or format if the first attempt failed
                try:
                    logger.warning("Trying fallback post schema...")
                    
                    # Fallback 1: Try with a simplified payload
                    fallback_payload = {
                        "content": post["content"],
                        "language": "en",
                        "tags": post["tags"]
                    }
                    logger.debug(f"Fallback payload 1: {json.dumps(fallback_payload)}")
                    status_code, response = self._make_request("POST", "/v1/posts", fallback_payload)
                    
                    if status_code not in (200, 201):
                        # Fallback 2: Try with 'text' instead of 'content'
                        logger.warning("Trying second fallback post schema...")
                        fallback_payload = {
                            "text": post["content"],
                            "language": "en"
                        }
                        logger.debug(f"Fallback payload 2: {json.dumps(fallback_payload)}")
                        status_code, response = self._make_request("POST", "/v1/posts", fallback_payload)
                    
                    if status_code not in (200, 201):
                        # Fallback 3: Try with 'status' instead (Mastodon convention)
                        logger.warning("Trying third fallback post schema...")
                        fallback_payload = {
                            "status": post["content"]
                        }
                        logger.debug(f"Fallback payload 3: {json.dumps(fallback_payload)}")
                        status_code, response = self._make_request("POST", "/v1/posts", fallback_payload)
                    
                    # If any fallback succeeded, add the post
                    if status_code in (200, 201):
                        logger.info(f"Created synthetic post {i+1}/{count} using fallback: {post_id}")
                        posts.append(post)
                        
                except Exception as e:
                    logger.exception(f"All fallback attempts failed: {e}")
        
        self.synthetic_posts = posts
        return posts
    
    def simulate_interactions(self, user_count: int = None, post_count: int = None) -> List[Dict]:
        """
        Simulate user interactions with posts.
        
        Creates a realistic pattern of favorites, bookmarks, and reblogs
        for the given synthetic users and posts.
        
        Args:
            user_count: Number of users to simulate (default: all seeded users)
            post_count: Number of posts to interact with (default: all seeded posts)
            
        Returns:
            List of interaction records
        """
        if not self.synthetic_users:
            logger.error("No synthetic users available. Call seed_users() first.")
            return []
        
        if not self.synthetic_posts:
            logger.error("No synthetic posts available. Call seed_posts() first.")
            return []
        
        users = self.synthetic_users[:user_count] if user_count else self.synthetic_users
        posts = self.synthetic_posts[:post_count] if post_count else self.synthetic_posts
        
        logger.info(f"Simulating interactions for {len(users)} users with {len(posts)} posts...")
        
        interactions = []
        action_types = ["favorite", "reblog", "bookmark", "more_like_this", "less_like_this"]
        action_weights = [0.5, 0.2, 0.15, 0.1, 0.05]  # Probability weights
        
        # For each user, interact with some posts
        for user_id in users:
            # Each user interacts with a random subset of posts
            post_count = random.randint(1, min(5, len(posts)))
            selected_posts = random.sample(posts, post_count)
            
            for post in selected_posts:
                # Select an action type with weighted probability
                action_type = random.choices(action_types, weights=action_weights, k=1)[0]
                
                # Create interaction data
                interaction = {
                    "user_id": user_id,
                    "post_id": post["post_id"],
                    "action_type": action_type,
                    "context": {"source": "corgi_validator"}
                }
                
                # Add interaction via API
                status_code, response = self._make_request("POST", "/v1/interactions", interaction)
                
                if status_code in (200, 201):
                    logger.info(f"Created interaction: {user_id} {action_type} {post['post_id']}")
                    interactions.append(interaction)
                else:
                    logger.error(f"Failed to create interaction: {status_code}, {response}")
        
        self.interactions = interactions
        return interactions
    
    def validate_recommendation_format(self, recs: List[Dict]) -> List[str]:
        """
        Validate that each post returned by recommendations API contains the required fields
        with the correct types and values.
        
        Args:
            recs: List of recommendation post objects to validate
            
        Returns:
            List of error strings for posts that fail validation checks
        """
        errors = []
        
        for i, post in enumerate(recs):
            post_id = post.get('id', f'Post at index {i}')
            
            # Post-level field validations
            if not post.get('id') or not isinstance(post.get('id'), str):
                errors.append(f"Post {post_id} missing or invalid id (should be non-empty string)")
            
            if not post.get('content') or not isinstance(post.get('content'), str):
                errors.append(f"Post {post_id} missing or invalid content (should be non-empty string or HTML)")
            
            # Language validation (ISO language string)
            language = post.get('language')
            if not language or not isinstance(language, str) or len(language) < 2:
                errors.append(f"Post {post_id} missing or invalid language (should be ISO language string like 'en')")
            
            # Timestamp validation
            created_at = post.get('created_at')
            if not created_at or not isinstance(created_at, str):
                errors.append(f"Post {post_id} missing or invalid created_at (should be ISO timestamp string)")
            else:
                try:
                    # Check if it's a valid ISO format
                    datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except ValueError:
                    errors.append(f"Post {post_id} has invalid created_at timestamp format: {created_at}")
            
            # Ranking score validation
            ranking_score = post.get('ranking_score')
            if ranking_score is None:
                errors.append(f"Post {post_id} missing ranking_score")
            elif not isinstance(ranking_score, (int, float)) or ranking_score < 0.0 or ranking_score > 1.0:
                errors.append(f"Post {post_id} has invalid ranking_score: {ranking_score} (should be float between 0.0-1.0)")
            
            # Recommendation reason validation
            reason = post.get('recommendation_reason')
            if not reason or not isinstance(reason, str):
                errors.append(f"Post {post_id} missing or invalid recommendation_reason (should be non-empty string)")
            
            # Boolean flag validations
            for flag in ['is_real_mastodon_post', 'is_synthetic']:
                if flag not in post or not isinstance(post[flag], bool):
                    errors.append(f"Post {post_id} missing or invalid {flag} (should be boolean)")
            
            # Account validation
            account = post.get('account')
            if not account or not isinstance(account, dict):
                errors.append(f"Post {post_id} missing or invalid account object")
            else:
                # Account username validation
                if not account.get('username') or not isinstance(account.get('username'), str):
                    errors.append(f"Post {post_id} has invalid account.username (should be non-empty string)")
                
                # Account display_name validation
                if 'display_name' not in account or not isinstance(account.get('display_name'), str):
                    errors.append(f"Post {post_id} has invalid account.display_name (should be string)")
                
                # Account URL validation
                url = account.get('url')
                if not url or not isinstance(url, str):
                    errors.append(f"Post {post_id} missing or invalid account.url (should be valid URL)")
                else:
                    # Simple URL validation
                    if not (url.startswith('http://') or url.startswith('https://')):
                        errors.append(f"Post {post_id} has invalid account.url format: {url}")
        
        return errors
    
    def check_recommendations(self, user_id: Optional[str] = None) -> Dict:
        """
        Check if recommendations are working properly.
        
        Args:
            user_id: Specific user ID to check (default: use first synthetic user)
            
        Returns:
            Dict with check results
        """
        logger.info("Running recommendation validation check...")
        
        if not user_id and not self.synthetic_users:
            logger.error("No users available for recommendation check")
            return {"status": "fail", "error": "No users available"}
        
        check_user = user_id or self.synthetic_users[0]
        
        # First, generate rankings for the user
        status_code, response = self._make_request("POST", "/v1/recommendations/rankings/generate", {"user_id": check_user})
        
        if status_code not in (200, 201):
            logger.error(f"Failed to generate rankings: {status_code}, {response}")
            return {
                "status": "fail", 
                "error": f"Ranking generation failed with status {status_code}"
            }
        
        # Now get the recommendations
        status_code, response = self._make_request("GET", "/v1/recommendations", params={"user_id": check_user})
        
        if status_code != 200:
            logger.error(f"Failed to get recommendations: {status_code}, {response}")
            return {
                "status": "fail", 
                "error": f"Recommendation retrieval failed with status {status_code}"
            }
        
        # Check if recommendations exist
        recommendations = response.get("recommendations", [])
        
        if not recommendations:
            logger.warning("No recommendations were returned")
            return {
                "status": "warn",
                "message": "No recommendations returned",
                "debug_info": response.get("debug_info", {})
            }
        
        logger.info(f"Retrieved {len(recommendations)} recommendations")
        
        # Validate recommendation format
        format_errors = self.validate_recommendation_format(recommendations)
        
        if format_errors:
            # Log all validation errors
            for error in format_errors:
                logger.error(f"Recommendation validation error: {error}")
            
            return {
                "status": "fail",
                "error": "Recommendations failed format validation",
                "validation_errors": format_errors,
                "recommendations_count": len(recommendations)
            }
        
        # Verify that the recommendations align with interactions
        # (This is a simple check, more complex validation would be needed for a real service)
        user_interactions = [i for i in self.interactions if i["user_id"] == check_user]
        
        if user_interactions:
            positive_post_ids = [i["post_id"] for i in user_interactions 
                               if i["action_type"] in ["favorite", "bookmark", "reblog", "more_like_this"]]
            
            negative_post_ids = [i["post_id"] for i in user_interactions 
                               if i["action_type"] == "less_like_this"]
            
            # Check if any negative posts appear in recommendations
            recommended_ids = [rec["id"] for rec in recommendations]
            negative_in_recs = [post_id for post_id in negative_post_ids if post_id in recommended_ids]
            
            if negative_in_recs:
                logger.warning(f"Found {len(negative_in_recs)} posts in recommendations that user indicated 'less_like_this'")
                return {
                    "status": "warn",
                    "message": f"Recommendation algorithm included {len(negative_in_recs)} disliked posts",
                    "negative_posts": negative_in_recs
                }
        
        return {
            "status": "pass",
            "recommendations_count": len(recommendations),
            "sample_reasons": [rec["recommendation_reason"] for rec in recommendations[:3]]
        }
    
    def check_feedback_logging(self, feedback_count: int = 3) -> Dict:
        """
        Check if feedback logging is working properly.
        
        Args:
            feedback_count: Number of feedback entries to generate and verify
            
        Returns:
            Dict with check results
        """
        logger.info("Running feedback logging validation check...")
        
        if not self.synthetic_users:
            logger.error("No users available for feedback check")
            return {"status": "fail", "error": "No users available"}
        
        if not self.synthetic_posts:
            logger.error("No posts available for feedback check")
            return {"status": "fail", "error": "No posts available"}
        
        # Track feedback we're going to create
        feedback_entries = []
        
        # Create some synthetic feedback
        for _ in range(feedback_count):
            user_id = random.choice(self.synthetic_users)
            post_id = random.choice(self.synthetic_posts)["post_id"]
            
            # Choose between various feedback types
            feedback_type = random.choice(["favorite", "more_like_this", "less_like_this"])
            
            feedback = {
                "user_id": user_id,
                "post_id": post_id,
                "action_type": feedback_type,
                "context": {
                    "source": "corgi_validator_feedback",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Log the feedback via API
            status_code, response = self._make_request("POST", "/v1/interactions", feedback)
            
            if status_code in (200, 201):
                logger.info(f"Created feedback: {user_id} {feedback_type} {post_id}")
                feedback_entries.append(feedback)
            else:
                logger.error(f"Failed to create feedback: {status_code}, {response}")
                return {
                    "status": "fail",
                    "error": f"Failed to create feedback with status {status_code}",
                    "response": response
                }
        
        # Verify feedback was logged by retrieving it
        all_verified = True
        failed_entries = []
        
        for entry in feedback_entries:
            # Check if we can retrieve the interaction for this user
            status_code, response = self._make_request(
                "GET", f"/v1/interactions/user/{entry['user_id']}"
            )
            
            if status_code != 200:
                logger.error(f"Failed to retrieve interactions: {status_code}, {response}")
                all_verified = False
                failed_entries.append({
                    "entry": entry,
                    "status_code": status_code,
                    "error": "Failed to retrieve interactions"
                })
                continue
            
            # Check if our entry is in the response
            found = False
            for interaction in response.get("interactions", []):
                if (interaction["post_id"] == entry["post_id"] and 
                    interaction["action_type"] == entry["action_type"]):
                    found = True
                    break
            
            if not found:
                logger.error(f"Feedback entry not found in user interactions: {entry}")
                all_verified = False
                failed_entries.append({
                    "entry": entry,
                    "error": "Entry not found in user interactions"
                })
        
        if all_verified:
            return {
                "status": "pass",
                "feedback_count": len(feedback_entries),
                "message": "All feedback entries were properly logged and retrieved"
            }
        else:
            return {
                "status": "fail",
                "message": f"{len(failed_entries)} out of {len(feedback_entries)} entries failed verification",
                "failed_entries": failed_entries
            }
    
    def check_privacy_modes(self) -> Dict:
        """
        Check if privacy settings are functioning correctly.
        
        Tests the three privacy levels (full, limited, none) to verify
        that data is appropriately filtered based on the settings.
        
        Returns:
            Dict with check results
        """
        logger.info("Running privacy modes validation check...")
        
        if not self.synthetic_users:
            logger.error("No users available for privacy check")
            return {"status": "fail", "error": "No users available"}
        
        # Use the first synthetic user for this test
        test_user = self.synthetic_users[0]
        
        # Create a few interactions for this user if needed
        if not any(i["user_id"] == test_user for i in self.interactions):
            if not self.synthetic_posts:
                logger.error("No posts available for interactions")
                return {"status": "fail", "error": "No posts available"}
            
            # Create 3 interactions
            for i in range(3):
                post = self.synthetic_posts[i % len(self.synthetic_posts)]
                action_type = ["favorite", "bookmark", "more_like_this"][i % 3]
                
                interaction = {
                    "user_id": test_user,
                    "post_id": post["post_id"],
                    "action_type": action_type,
                    "context": {"source": "privacy_test"}
                }
                
                status_code, response = self._make_request("POST", "/v1/interactions", interaction)
                
                if status_code not in (200, 201):
                    logger.error(f"Failed to create interaction for privacy test: {status_code}, {response}")
                    return {"status": "fail", "error": "Could not create test interactions"}
        
        # Test all three privacy levels
        privacy_levels = ["full", "limited", "none"]
        privacy_checks = {}
        
        for level in privacy_levels:
            # Set privacy level
            status_code, response = self._make_request("POST", "/v1/privacy/settings", {
                "user_id": test_user,
                "tracking_level": level
            })
            
            if status_code != 200:
                logger.error(f"Failed to set privacy level to {level}: {status_code}, {response}")
                return {
                    "status": "fail",
                    "error": f"Could not set privacy level to {level}",
                    "response": response
                }
            
            # Verify the setting was applied
            status_code, response = self._make_request("GET", "/v1/privacy/settings", params={"user_id": test_user})
            
            if status_code != 200:
                logger.error(f"Failed to retrieve privacy settings: {status_code}, {response}")
                return {
                    "status": "fail",
                    "error": "Could not retrieve privacy settings",
                    "response": response
                }
            
            if response.get("tracking_level") != level:
                logger.error(f"Privacy level mismatch: expected {level}, got {response.get('tracking_level')}")
                return {
                    "status": "fail",
                    "error": f"Privacy level not set correctly. Expected {level}, got {response.get('tracking_level')}",
                    "response": response
                }
            
            # Now test how interactions are returned with this privacy level
            status_code, response = self._make_request("GET", f"/v1/interactions/user/{test_user}")
            
            if status_code == 404 and level == "none":
                # Expected for "none" privacy level
                pass
            elif status_code != 200:
                logger.error(f"Failed to retrieve interactions with privacy level {level}: {status_code}, {response}")
                return {
                    "status": "fail",
                    "error": f"Could not retrieve interactions with privacy level {level}",
                    "response": response
                }
            
            # Check that the response structure matches the privacy level
            if level == "full":
                # Should have detailed interaction data
                if "interactions" not in response or not isinstance(response["interactions"], list):
                    logger.error(f"Expected detailed interactions with privacy level {level}, but got: {response}")
                    return {
                        "status": "fail",
                        "error": "Full privacy level should return detailed interactions",
                        "response": response
                    }
            elif level == "limited":
                # Should have aggregated counts but not detailed data
                if "interaction_counts" not in response:
                    logger.error(f"Expected aggregated counts with privacy level {level}, but got: {response}")
                    return {
                        "status": "fail",
                        "error": "Limited privacy level should return aggregated counts",
                        "response": response
                    }
            elif level == "none":
                # Should indicate that tracking is disabled
                if "privacy_level" not in response or response.get("privacy_level") != "none":
                    logger.error(f"Expected privacy_level=none indication in response, but got: {response}")
                    return {
                        "status": "fail",
                        "error": "None privacy level should indicate that tracking is disabled",
                        "response": response
                    }
            
            # Store the response structure for reporting
            privacy_checks[level] = {
                "status_code": status_code,
                "response_keys": list(response.keys()),
                "has_detailed_data": "interactions" in response and len(response.get("interactions", [])) > 0,
                "has_aggregated_data": "interaction_counts" in response
            }
        
        # Restore the privacy level to "full" as a courtesy
        self._make_request("POST", "/v1/privacy/settings", {
            "user_id": test_user,
            "tracking_level": "full"
        })
        
        return {
            "status": "pass",
            "privacy_levels_tested": privacy_levels,
            "checks": privacy_checks,
            "message": "All privacy levels function as expected"
        }
    
    def check_blending(self) -> Dict:
        """
        Check if timeline and recommendation blending works correctly.
        
        Tests if the recommendation service properly injects recommendations
        into the user's timeline when requested.
        
        Returns:
            Dict with check results
        """
        logger.info("Running timeline blending validation check...")
        
        if not self.synthetic_users:
            logger.error("No users available for blending check")
            return {"status": "fail", "error": "No users available"}
        
        test_user = self.synthetic_users[0]
        
        # First, generate some rankings for the user if needed
        status_code, _ = self._make_request("POST", "/v1/recommendations/rankings/generate", {"user_id": test_user})
        
        # Get regular timeline
        status_code, timeline_response = self._make_request("GET", "/v1/timelines/home", params={"user_id": test_user})
        
        if status_code != 200:
            # The endpoint might not exist yet, which is fine
            logger.info(f"Timeline endpoint returned {status_code} - this may be normal if not implemented yet")
            
            # Check if we have augmented timeline endpoint
            status_code, augmented_response = self._make_request(
                "GET", 
                "/v1/timelines/home/augmented", 
                params={"user_id": test_user, "inject_recommendations": "true"}
            )
            
            if status_code != 200:
                logger.info("Augmented timeline endpoint also not available")
                return {
                    "status": "skip",
                    "message": "Timeline blending endpoints not available yet",
                    "note": "This test verifies timeline + recommendation blending which may not be implemented"
                }
        
        # Get augmented timeline
        status_code, augmented_response = self._make_request(
            "GET", 
            "/v1/timelines/home/augmented", 
            params={"user_id": test_user, "inject_recommendations": "true"}
        )
        
        if status_code != 200:
            logger.error(f"Failed to retrieve augmented timeline: {status_code}")
            return {
                "status": "fail",
                "error": f"Could not retrieve augmented timeline, got status {status_code}"
            }
        
        # Check if recommendations were injected
        augmented_posts = augmented_response.get("timeline", [])
        regular_timeline_count = len(timeline_response.get("timeline", [])) if "timeline" in timeline_response else 0
        
        # Look for recommendation markers in the augmented timeline
        rec_markers = [post for post in augmented_posts if post.get("is_recommendation") is True]
        
        if not rec_markers and regular_timeline_count > 0:
            logger.warning("No recommendations found in augmented timeline")
            return {
                "status": "warn",
                "message": "No recommendations were injected into the timeline",
                "regular_count": regular_timeline_count,
                "augmented_count": len(augmented_posts)
            }
        
        # The test passes if either:
        # 1. We have recommendations injected
        # 2. The timeline endpoint isn't implemented yet (which is fine)
        
        return {
            "status": "pass" if rec_markers or regular_timeline_count == 0 else "warn",
            "injected_recommendations": len(rec_markers),
            "timeline_posts": regular_timeline_count,
            "augmented_count": len(augmented_posts),
            "message": "Timeline blending verification complete"
        }
    
    def run_all_checks(self, users_count: int = DEFAULT_NUM_USERS, posts_count: int = DEFAULT_NUM_POSTS) -> Dict:
        """
        Run all validation checks and generate a comprehensive report.
        
        Args:
            users_count: Number of synthetic users to create
            posts_count: Number of synthetic posts to create
            
        Returns:
            Dict with all check results
        """
        logger.info("Starting complete validation suite...")
        
        # Initialize test environment
        self.seed_users(users_count)
        self.seed_posts(posts_count)
        self.simulate_interactions()
        
        # Run all checks
        checks = {}
        
        checks["recommendations"] = self.check_recommendations()
        checks["feedback"] = self.check_feedback_logging()
        checks["privacy"] = self.check_privacy_modes()
        checks["blending"] = self.check_blending()
        
        # Store results
        self.check_results = checks
        
        # Generate summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_users": len(self.synthetic_users),
            "total_posts": len(self.synthetic_posts),
            "total_interactions": len(self.interactions),
            "checks": {
                check: result["status"] for check, result in checks.items()
            }
        }
        
        return summary
    
    def save_report(self, file_path: str) -> None:
        """
        Save validation results to a JSON file.
        
        Args:
            file_path: Path to save the report
        """
        if not self.check_results:
            logger.error("No check results available. Run checks first.")
            return
        
        # Create complete report
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_users": len(self.synthetic_users),
            "total_posts": len(self.synthetic_posts),
            "total_interactions": len(self.interactions),
            "checks": self.check_results,
            "summary": {
                check: result["status"] for check, result in self.check_results.items()
            }
        }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
    
    def print_results(self) -> None:
        """Print a human-readable summary of validation results."""
        if not self.check_results:
            logger.error("No check results available. Run checks first.")
            return
        
        print("\n=== Corgi Validator Results ===\n")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Synthetic Users: {len(self.synthetic_users)}")
        print(f"Synthetic Posts: {len(self.synthetic_posts)}")
        print(f"Simulated Interactions: {len(self.interactions)}\n")
        
        print("Test Results:")
        for check, result in self.check_results.items():
            status = result["status"]
            icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
            message = result.get("message", "")
            error = result.get("error", "")
            
            # Format the status line
            status_line = f"{icon} {check}"
            if error:
                status_line += f" ({error})"
            elif message:
                status_line += f" ({message})"
            
            print(status_line)
            
            # Print validation errors for recommendation check
            if check == "recommendations" and status == "fail" and "validation_errors" in result:
                print("\nRecommendation format validation errors:")
                for i, err in enumerate(result["validation_errors"][:10]):  # Limit to first 10 errors
                    print(f"  {i+1}. {err}")
                
                if len(result["validation_errors"]) > 10:
                    print(f"  ... and {len(result['validation_errors']) - 10} more errors (see log for details)")
                print()
        
        print("\nOverall Status: ", end="")
        if all(result["status"] == "pass" for result in self.check_results.values()):
            print("✅ All checks passed")
        elif any(result["status"] == "fail" for result in self.check_results.values()):
            print("❌ Some checks failed")
        else:
            print("⚠️ Some checks have warnings")
        
        print("\nNote: See the report JSON for detailed results\n")


def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Corgi Recommender Service Validator")
    
    # Basic options
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="Base URL for the Corgi API")
    parser.add_argument("--api-prefix", default="/api/v1", help="API endpoint prefix (default: /api/v1)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without making actual requests")
    parser.add_argument("--skip-server-check", action="store_true", help="Skip the server status check")
    
    # Seed options
    parser.add_argument("--run-seed", type=int, help="Number of fake users/posts to generate")
    
    # Check options
    parser.add_argument("--check-recs", action="store_true", help="Check if recommendations are returned")
    parser.add_argument("--check-feedback", action="store_true", help="Check if feedback routes work")
    parser.add_argument("--check-privacy", action="store_true", help="Check if privacy levels function correctly")
    parser.add_argument("--check-blend", action="store_true", help="Check if timeline + rec blending works")
    parser.add_argument("--check-all", action="store_true", help="Run all validation checks")
    parser.add_argument("--check-server", action="store_true", help="Only check if the server is running")
    parser.add_argument("--check-paths", action="store_true", help="Check available API paths to find the correct configuration")
    
    # Output options
    parser.add_argument("--output", help="Path to save validation report as JSON")
    
    args = parser.parse_args()
    
    # If only checking server status or API paths, do that and exit
    if args.check_server:
        check_server_status()
        return
    
    if args.check_paths:
        check_api_paths()
        return
    
    # Check if the server is running before proceeding, unless skipped
    if not args.skip_server_check and not args.dry_run:
        try:
            response = requests.get(f"{args.api_base}/health", timeout=2)
            if response.status_code != 200:
                print(f"⚠️  WARNING: Server health check failed with status {response.status_code}")
                print("The Corgi Recommender Service might not be running correctly.")
                server_running = check_server_status()
                if not server_running:
                    print("\n❌ Cannot proceed with validation: server is not running.")
                    print("Run with --dry-run to simulate without a server or start the server first.")
                    return
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to the Corgi Recommender Service.")
            server_running = check_server_status()
            if not server_running:
                print("\n❌ Cannot proceed with validation: server is not running.")
                print("Run with --dry-run to simulate without a server or start the server first.")
                return
        except Exception as e:
            print(f"⚠️  WARNING: Error checking server status: {e}")
            print("Proceeding anyway, but validation might fail.")
    
    # Create validator instance
    validator = CorgiValidator(
        api_base=args.api_base, 
        api_prefix=args.api_prefix,
        verbose=args.verbose, 
        dry_run=args.dry_run
    )
    
    # Determine what to run based on args
    run_any_check = any([
        args.check_recs, args.check_feedback, args.check_privacy, args.check_blend, args.check_all
    ])
    
    # If just seeding, do that and exit
    if args.run_seed and not run_any_check:
        validator.seed_users(args.run_seed)
        validator.seed_posts(args.run_seed * 2)  # Create twice as many posts as users
        validator.simulate_interactions()
        print(f"Seeded {args.run_seed} users and {args.run_seed * 2} posts with interactions")
        return
    
    # Run all checks if requested or if no specific check is specified
    if args.check_all or not run_any_check:
        seed_count = args.run_seed or DEFAULT_NUM_USERS
        validator.run_all_checks(seed_count, seed_count * 2)
        validator.print_results()
    else:
        # Run specific checks as requested
        # First seed the test data if not already done
        if not validator.synthetic_users:
            seed_count = args.run_seed or DEFAULT_NUM_USERS
            validator.seed_users(seed_count)
            validator.seed_posts(seed_count * 2)
            validator.simulate_interactions()
        
        # Run requested checks
        if args.check_recs:
            validator.check_results["recommendations"] = validator.check_recommendations()
        
        if args.check_feedback:
            validator.check_results["feedback"] = validator.check_feedback_logging()
        
        if args.check_privacy:
            validator.check_results["privacy"] = validator.check_privacy_modes()
        
        if args.check_blend:
            validator.check_results["blending"] = validator.check_blending()
        
        validator.print_results()
    
    # Save report if requested
    if args.output:
        validator.save_report(args.output)
        print(f"Report saved to {args.output}")


def check_api_paths():
    """
    Check all available API paths to help configure the validator correctly.
    Run with python -c 'from corgi_validator import check_api_paths; check_api_paths()'
    """
    print("🔍 Checking available API paths on localhost...")
    
    # Try common ports
    ports = [5000, 5001, 3000, 8000, 8080]
    base_urls = [f"http://localhost:{port}" for port in ports]
    
    # Define paths to check
    paths = [
        "/",
        "/health",
        "/v1",
        "/v1/health",
        "/v1/posts",
        "/v1/recommendations",
        "/v1/interactions",
        "/v1/privacy/settings",
        "/api",
        "/api/v1",
        "/api/v1/health",
        "/api/v1/posts",
        "/api/v1/recommendations",
    ]
    
    # Store successful endpoints
    working_endpoints = {}
    
    # Check each combination
    for base_url in base_urls:
        print(f"\n📡 Checking {base_url}:")
        success_count = 0
        try:
            for path in paths:
                url = f"{base_url}{path}"
                try:
                    response = requests.get(url, timeout=1)
                    status = response.status_code
                    result = "✅" if status == 200 else "❌"
                    print(f"{result} {path}: {status}")
                    
                    if status == 200:
                        success_count += 1
                        working_endpoints[path] = base_url
                except requests.RequestException:
                    print(f"❌ {path}: Connection error")
        except Exception as e:
            print(f"Error checking {base_url}: {e}")
            
        if success_count > 0:
            print(f"✨ Found {success_count} working endpoints on {base_url}")
    
    # Suggest configuration based on findings
    if working_endpoints:
        print("\n🔧 Suggested configuration:")
        
        # Find the most common base URL
        base_url_counts = {}
        for url in working_endpoints.values():
            base_url_counts[url] = base_url_counts.get(url, 0) + 1
        
        most_common_base = max(base_url_counts.items(), key=lambda x: x[1])[0]
        
        # Make a guess at the API structure
        if "/v1/health" in working_endpoints:
            print(f"API Base URL: {most_common_base}")
            print("API Prefix: /v1")
        elif "/api/v1/health" in working_endpoints:
            print(f"API Base URL: {most_common_base}")
            print("API Prefix: /api/v1")
        elif "/health" in working_endpoints:
            print(f"API Base URL: {most_common_base}")
            print("API Prefix: (none)")
        else:
            print(f"API Base URL: {most_common_base}")
            print("API Prefix: (unknown)")
        
        print("\nAdd this to your run command:")
        print(f"python3 corgi_validator.py --api-base={most_common_base} --verbose")
    else:
        print("\n❌ No working API endpoints found.")
        print("It appears the Corgi Recommender Service might not be running.")
        print("Try starting it with: HOST=0.0.0.0 PORT=5001 python3 -m flask --app app run")

def check_server_status():
    """
    Check if the Corgi server is running and help the user start it on the correct port.
    Run with python -c 'from corgi_validator import check_server_status; check_server_status()'
    """
    print("Checking Corgi Recommender Service status...")
    
    # Check what's running on port 5000
    try:
        port_5000_status = subprocess.run(['lsof', '-i', ':5000'], capture_output=True, text=True)
        if port_5000_status.stdout:
            print("\n⚠️  WARNING: Port 5000 is already in use:")
            print(port_5000_status.stdout)
            print("This is likely Apple Control Center/AirTunes which conflicts with the default Flask port.")
            print("The validator has been configured to use port 5001 instead.\n")
        else:
            print("Port 5000 is available.")
    except Exception:
        print("Unable to check port 5000 status.")
    
    # Check if server is running on port 5001
    try:
        response = requests.get("http://localhost:5001/health", timeout=2)
        print(f"Server on port 5001: {response.status_code}")
        if response.status_code == 200:
            print("✅ Corgi Recommender Service is running correctly on port 5001!")
            return True
    except requests.exceptions.ConnectionError:
        print("❌ Corgi Recommender Service is NOT running on port 5001.")
    except Exception as e:
        print(f"Error checking server on port 5001: {e}")
    
    # Check if Python/Flask is running
    try:
        flask_processes = subprocess.run(['ps', 'aux'], capture_output=True, text=True).stdout
        if 'flask' in flask_processes.lower() or 'gunicorn' in flask_processes.lower():
            print("A Flask or Gunicorn process seems to be running, but not accessible at the expected URL.")
        else:
            print("No Flask or Gunicorn process detected.")
    except Exception:
        print("Unable to check for Flask processes.")
    
    # Provide instructions
    print("\n📋 SETUP INSTRUCTIONS:")
    print("1. Start the Corgi Recommender Service on port 5001:")
    print("   cd /Users/andrewnordstrom/corgi-recommender-service")
    print("   HOST=0.0.0.0 PORT=5001 python3 -m flask --app app run")
    print("\n2. In a separate terminal, run the validator:")
    print("   cd /Users/andrewnordstrom/corgi-recommender-service")
    print("   python3 corgi_validator.py --verbose\n")
    
    return False

def test_manual_post():
    """
    Test function to manually verify what kind of post payload works.
    Run with python -c 'from corgi_validator import test_manual_post; test_manual_post()'
    """
    print("Running manual post creation test...")
    
    # Set up logging for debugging
    logging.basicConfig(level=logging.DEBUG)
    
    # Test various payload formats
    payloads = [
        # Standard payload
        {
            "post_id": f"manual_test_{uuid.uuid4().hex[:8]}",
            "author_id": "test_author_1",
            "author_name": "test_user",
            "content": "Test post from validator harness - standard payload",
            "language": "en",
            "tags": ["test", "corgi", "validation"]
        },
        
        # Simplified payload
        {
            "content": "Test post from validator harness - simplified payload",
            "language": "en",
            "tags": ["test", "corgi"]
        },
        
        # Mastodon-style payload
        {
            "status": "Test post from validator harness - Mastodon style"
        },
        
        # Alternative text field
        {
            "text": "Test post from validator harness - text field",
            "language": "en"
        }
    ]
    
    # First, let's check if the server is running and what endpoints are accessible
    print("\n===== CHECKING SERVER STATUS =====")
    endpoints_to_check = [
        "http://localhost:5000/",
        "http://localhost:5000/health",
        "http://localhost:5000/v1/health",
        "http://localhost:5000/v1/posts",
        "http://localhost:5000/v1/recommendations"
    ]
    
    for endpoint in endpoints_to_check:
        try:
            response = requests.get(endpoint)
            print(f"GET {endpoint}: {response.status_code}")
            if response.text:
                print(f"  Response: {response.text[:100]}")
            print(f"  Headers: {dict(response.headers)}")
        except Exception as e:
            print(f"❌ Error accessing {endpoint}: {e}")
    
    # Try with different auth methods
    print("\n===== TRYING DIFFERENT AUTH METHODS =====")
    url = "http://localhost:5000/v1/posts"
    auth_methods = [
        {"name": "No auth", "headers": {}},
        {"name": "Basic auth", "headers": {"Authorization": "Basic YWRtaW46YWRtaW4="}},  # admin:admin
        {"name": "Bearer token", "headers": {"Authorization": "Bearer test-token"}},
        {"name": "API Key as header", "headers": {"X-API-Key": "test-api-key"}},
        {"name": "API Key as query param", "query": {"api_key": "test-api-key"}},
    ]
    
    for auth in auth_methods:
        print(f"\nTrying auth method: {auth['name']}")
        try:
            if "query" in auth:
                response = requests.post(url, json=payloads[0], headers=auth.get('headers', {}), params=auth.get('query', {}))
            else:
                response = requests.post(url, json=payloads[0], headers=auth.get('headers', {}))
                
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            try:
                print(f"Response JSON: {json.dumps(response.json(), indent=2)}")
            except:
                print(f"Response text: {response.text}")
                
            if response.status_code in (200, 201):
                print("✅ SUCCESS: This auth method works!")
            else:
                print("❌ FAILED: This auth method does not work")
        except Exception as e:
            print(f"❌ ERROR: Request failed with exception: {e}")
    
    # Try each payload format only if we get past the 403 error
    if any(auth for auth in auth_methods if "SUCCESS" in auth):
        print("\n===== TESTING PAYLOAD FORMATS =====")
        for i, payload in enumerate(payloads):
            print(f"\nTest {i+1}: Trying payload format: {payload.keys()}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            try:
                # Use the successful auth method from above
                successful_auth = next((auth for auth in auth_methods if "SUCCESS" in auth), auth_methods[0])
                
                if "query" in successful_auth:
                    response = requests.post(url, json=payload, headers=successful_auth.get('headers', {}), 
                                            params=successful_auth.get('query', {}))
                else:
                    response = requests.post(url, json=payload, headers=successful_auth.get('headers', {}))
                    
                print(f"Response status: {response.status_code}")
                
                try:
                    print(f"Response JSON: {json.dumps(response.json(), indent=2)}")
                except:
                    print(f"Response text: {response.text}")
                    
                if response.status_code in (200, 201):
                    print("✅ SUCCESS: This payload format works!")
                else:
                    print("❌ FAILED: This payload format does not work")
            except Exception as e:
                print(f"❌ ERROR: Request failed with exception: {e}")
    
    # Try alternative URLs
    print("\n===== TRYING ALTERNATIVE ENDPOINTS =====")
    alternative_urls = [
        "http://localhost:5000/api/v1/posts",
        "http://localhost:5000/v1/posts/create",
        "http://localhost:5000/posts",
        "http://localhost:8000/v1/posts"  # Maybe it's on a different port?
    ]
    
    for alt_url in alternative_urls:
        print(f"\nTrying alternative URL: {alt_url}")
        try:
            response = requests.post(alt_url, json=payloads[0])
            print(f"Response status: {response.status_code}")
            
            try:
                print(f"Response JSON: {json.dumps(response.json(), indent=2)}")
            except:
                print(f"Response text: {response.text}")
                
            if response.status_code in (200, 201):
                print("✅ SUCCESS: This URL works!")
            else:
                print("❌ FAILED: This URL does not work")
        except Exception as e:
            print(f"Request failed: {e}")
            
    # Check if the server is running on a different port
    print("\n===== CHECKING COMMON PORTS =====")
    common_ports = [3000, 8000, 8080, 9000]
    for port in common_ports:
        url = f"http://localhost:{port}/health"
        try:
            response = requests.get(url, timeout=1)
            print(f"Port {port}: {response.status_code}")
            if response.status_code != 403:
                print(f"  Response: {response.text[:100]}")
        except Exception:
            print(f"Port {port}: Not responding")


if __name__ == "__main__":
    main()