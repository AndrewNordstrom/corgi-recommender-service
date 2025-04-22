import os
import requests
import json
import logging
import random
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from .interaction_logger import InteractionLogger
from .feedback_module import FeedbackModule
from .user_profiles import UserProfile

# Import our new Claude interface
try:
    from .claude_interface import ClaudeInterface
    from .token_tracker import TokenTracker
    CLAUDE_INTERFACE_AVAILABLE = True
except ImportError:
    CLAUDE_INTERFACE_AVAILABLE = False

class BrowserAgent:
    def __init__(self, 
                 api_key: Optional[str] = None, 
                 base_url: str = None, 
                 logger: Optional[InteractionLogger] = None,
                 feedback_module: Optional[FeedbackModule] = None,
                 max_tokens: Optional[int] = None,
                 max_interactions: int = 10,
                 token_tracker: Optional[TokenTracker] = None,
                 tools_enabled: bool = False,
                 no_llm: bool = False):
        """Initialize a browser agent that uses Claude's computer_use tool to interact with the Corgi Recommender.
        
        Args:
            api_key: Claude API key (defaults to ANTHROPIC_API_KEY env var if not provided)
            base_url: The base URL for the Corgi Recommender service
            logger: Optional custom logger for tracking interactions
            feedback_module: Optional feedback module for submitting recommendations feedback
            max_tokens: Maximum number of tokens to use
            max_interactions: Maximum number of browser interactions
            token_tracker: Optional token usage tracker
            tools_enabled: Whether to enable tool usage (e.g., computer_use)
            no_llm: Run in heuristic mode without using Claude
        """
        # Default from environment if not set
        if max_tokens is None and 'DEFAULT_MAX_TOKENS' in os.environ:
            try:
                max_tokens = int(os.environ['DEFAULT_MAX_TOKENS'])
            except (ValueError, TypeError):
                pass
        
        # Initialize base properties
        self.base_url = base_url or os.environ.get("CORGI_SERVICE_URL", "http://localhost:5000")
        self.logger = logger or InteractionLogger()
        self.feedback_module = feedback_module or FeedbackModule(api_base_url=self.base_url)
        self.session_id = None
        self.user_profile = None
        self.max_interactions = max_interactions
        self.interaction_count = 0
        self.tools_enabled = tools_enabled
        self.no_llm = no_llm
        
        # Set up token tracking
        self.token_tracker = token_tracker
        if max_tokens and not token_tracker:
            self.token_tracker = TokenTracker(max_tokens=max_tokens)
        
        # Initialize Claude API interface if not in no_llm mode
        self.claude = None
        if not no_llm and CLAUDE_INTERFACE_AVAILABLE:
            try:
                self.claude = ClaudeInterface(token_tracker=self.token_tracker)
                self.api_key = self.claude.api_key
            except (ValueError, ConnectionError) as e:
                if not no_llm:
                    raise e
        elif not no_llm:
            # Fall back to legacy API access if Claude interface not available
            self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
            if not self.api_key:
                raise ValueError("No Claude API key found in environment variables. "
                               "Please set ANTHROPIC_API_KEY or CLAUDE_API_KEY in your .env file.")
        
        # Track privacy settings
        self.current_privacy_level = "full"  # Default level
        
        # Add memory cache for post processing
        self.post_cache = {}
        
        # Simulated post IDs for testing (would come from actual API in production)
        self.simulated_posts = [
            {"id": f"post_{i}", "content": self._generate_random_post_content()} 
            for i in range(1, 21)
        ]
    
    def start_session(self, 
                      goal: str, 
                      user_profile: Optional[UserProfile] = None,
                      system_prompt: Optional[str] = None) -> str:
        """Start a new agent session with a specific goal.
        
        Args:
            goal: The objective for the agent (e.g., "scroll timeline, favorite 2 corgi posts")
            user_profile: Optional UserProfile to use for this session
            system_prompt: Optional additional system instructions
            
        Returns:
            session_id: Identifier for the current agent session
        """
        self.session_id = self._generate_session_id()
        self.user_profile = user_profile
        self.logger.start_session(self.session_id, goal)
        
        # Reset interaction counter
        self.interaction_count = 0
        
        # Default system prompt if none provided
        if not system_prompt:
            system_prompt = (
                "You are a synthetic user testing the Corgi Recommender service. "
                "Your goal is to accomplish the specified task naturally, as a real user would."
            )
            
        # Log session initialization
        session_info = {
            "goal": goal,
            "base_url": self.base_url,
            "system_prompt": system_prompt,
            "max_interactions": self.max_interactions,
            "tools_enabled": self.tools_enabled,
            "no_llm_mode": self.no_llm
        }
        
        # Add user profile information if available
        if user_profile:
            session_info["user_profile_name"] = user_profile.name
            session_info["user_profile_description"] = user_profile.description
            session_info["user_id"] = user_profile.user_id
            session_info["use_browser"] = user_profile.use_browser
        
        self.logger.log_action("session_start", session_info)
        
        return self.session_id
    
    def run_interaction(self, 
                        goal: str, 
                        max_turns: int = 10, 
                        user_profile: Optional[UserProfile] = None,
                        time_of_day: Optional[str] = None,
                        test_goal: Optional[str] = None) -> Dict[str, Any]:
        """Execute a goal-directed interaction with the Corgi UI.
        
        Args:
            goal: The objective for the agent
            max_turns: Maximum number of interaction turns to allow
            user_profile: Optional UserProfile to use for this session
            time_of_day: Optional time context for behavior adaptation
            test_goal: Optional specific test goal
            
        Returns:
            results: Dictionary containing session results and logs
        """
        self.user_profile = user_profile
        
        if not self.session_id:
            self.start_session(goal, user_profile)
        
        # Check if we should use the browser
        use_browser = self.tools_enabled and (user_profile and user_profile.use_browser)
        
        # Set up the computer_use tool configuration if needed
        computer_use_tool = None
        if use_browser:
            computer_use_tool = {
                "name": "computer_use",
                "description": "Interact with a web UI to accomplish tasks. Use this tool to browse and navigate web pages."
            }
        
        # Initialize conversation with system prompt and user instruction
        system_prompt = (
            "You are a synthetic user testing the Corgi Recommender service. "
            "Your goal is to accomplish the specified task naturally, as a real user would."
        )
        
        # Use the user profile's behavior prompt if available
        if user_profile:
            behavior_prompt = user_profile.get_behavior_prompt(time_of_day, test_goal)
        else:
            behavior_prompt = goal
        
        # Log the start of the interaction
        self.logger.log_action("interaction_start", {
            "goal": goal,
            "max_turns": max_turns,
            "base_url": self.base_url,
            "user_profile": user_profile.name if user_profile else "none",
            "time_of_day": time_of_day,
            "test_goal": test_goal,
            "use_browser": use_browser
        })
        
        # Run in no-LLM mode using heuristics if requested
        if self.no_llm:
            return self._run_heuristic_interaction(goal, max_turns, user_profile, time_of_day, test_goal)
        
        # Set up initial messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please {'visit ' + self.base_url + ' and ' if use_browser else ''}accomplish this goal: {behavior_prompt}"}
        ]
        
        # Initialize success status and message
        success = False
        message = "Interaction did not complete"
        
        # Execute conversation turns
        try:
            turn_count = 0
            while (turn_count < max_turns and 
                   self.interaction_count < self.max_interactions and
                   (not self.token_tracker or not self.token_tracker.token_limit_reached)):
                turn_count += 1
                
                # Log the turn
                self.logger.log_action("interaction_turn", {
                    "turn_number": turn_count,
                    "max_turns": max_turns,
                    "interaction_count": self.interaction_count,
                    "max_interactions": self.max_interactions
                })
                
                # Make the API call to Claude
                if self.claude and not use_browser:
                    # Use the Claude interface for non-browser interactions
                    response = self.claude.send_message(
                        message="",  # Not used when messages are provided
                        messages=messages,
                        system=system_prompt
                    )
                    
                    # Extract assistant's response text
                    assistant_text = self.claude.get_response_text(response)
                    assistant_message = [{"type": "text", "text": assistant_text}]
                    
                    # No tool usage here
                    tool_use = None
                elif self.claude and use_browser:
                    # Use tools interface for browser interactions
                    response = self.claude.process_with_tools(
                        messages=messages,
                        tools=[computer_use_tool],
                        system=system_prompt
                    )
                    
                    # Extract the assistant's message
                    assistant_message = response.get("content", [])
                    assistant_text = ""
                    tool_use = None
                    
                    # Process the response parts
                    for part in assistant_message:
                        if part.get("type") == "text":
                            assistant_text = part.get("text", "")
                        elif part.get("type") == "tool_use" and part.get("name") == "computer_use":
                            tool_use = part.get("input", {})
                else:
                    # Legacy Claude API call
                    response = self.execute_claude_request(
                        messages=messages,
                        tools=[computer_use_tool] if use_browser else []
                    )
                    
                    # Extract the assistant's message
                    assistant_message = response.get("content", [])
                    assistant_text = ""
                    tool_use = None
                    
                    # Process the response parts
                    for part in assistant_message:
                        if part.get("type") == "text":
                            assistant_text = part.get("text", "")
                        elif part.get("type") == "tool_use" and part.get("name") == "computer_use":
                            tool_use = part.get("input", {})
                
                # Log the assistant's message and tool use
                self.logger.log_action("assistant_message", {
                    "turn": turn_count,
                    "text": assistant_text
                })
                
                if tool_use:
                    self.logger.log_action("tool_use", {
                        "turn": turn_count,
                        "input": tool_use
                    })
                    
                    # Increment interaction count when using tools
                    self.interaction_count += 1
                    
                    # Check if we've reached the interaction limit
                    if self.interaction_count >= self.max_interactions:
                        self.logger.log_action("interaction_limit_reached", {
                            "interaction_count": self.interaction_count,
                            "max_interactions": self.max_interactions
                        })
                        message = f"Reached maximum interactions ({self.max_interactions})"
                        break
                    
                    # Process tool use commands for special actions
                    tool_result = self._process_tool_use(tool_use)
                    
                    # Log the tool response
                    self.logger.log_action("tool_response", {
                        "turn": turn_count,
                        "response": tool_result
                    })
                    
                    # Add messages to the conversation
                    messages.append({"role": "assistant", "content": assistant_message})
                    messages.append({"role": "user", "content": [
                        {"type": "tool_result", "tool_use_id": tool_use.get("id", "simulated_id"), "content": tool_result}
                    ]})
                else:
                    # If no tool use, just add the assistant's message and end the conversation
                    messages.append({"role": "assistant", "content": assistant_message})
                    success = True
                    message = "Interaction completed successfully"
                    break
                
                # Check if we've reached the goal (this would need more sophisticated logic in a real implementation)
                if "completed" in assistant_text.lower() or "finished" in assistant_text.lower():
                    success = True
                    message = "Goal appears to be completed"
                    break
                
                # Check if we've reached the token limit
                if self.token_tracker and self.token_tracker.token_limit_reached:
                    message = f"Reached token limit ({self.token_tracker.max_tokens})"
                    break
            
            # Check if we ran out of turns
            if turn_count >= max_turns and not success:
                message = f"Reached maximum turns ({max_turns}) without completing goal"
        
        except Exception as e:
            # Log the error
            self.logger.log_action("interaction_error", {
                "error": str(e),
                "type": type(e).__name__
            })
            message = f"Error during interaction: {str(e)}"
        
        # Log the end of the interaction
        self.logger.log_action("interaction_end", {
            "success": success,
            "message": message,
            "turns_used": turn_count,
            "interactions_used": self.interaction_count
        })
        
        # Print token usage summary if available
        if self.token_tracker:
            self.token_tracker.log_summary()
        
        # Create and return the results
        results = {
            "session_id": self.session_id,
            "goal": goal,
            "success": success,
            "message": message,
            "turns_used": turn_count,
            "interactions_used": self.interaction_count,
            "user_profile": user_profile.name if user_profile else "none",
            "logs": self.logger.get_session_logs(self.session_id)
        }
        
        # Add token usage if available
        if self.token_tracker:
            results["token_usage"] = self.token_tracker.get_usage_summary()
        
        return results
    
    def _run_heuristic_interaction(self,
                                  goal: str,
                                  max_turns: int = 10,
                                  user_profile: Optional[UserProfile] = None,
                                  time_of_day: Optional[str] = None,
                                  test_goal: Optional[str] = None) -> Dict[str, Any]:
        """Run an interaction using rules-based heuristics instead of Claude LLM.
        
        Args:
            goal: The objective for the agent
            max_turns: Maximum number of interaction turns
            user_profile: Optional UserProfile for this session
            time_of_day: Optional time context
            test_goal: Optional specific test goal
            
        Returns:
            Dictionary with results
        """
        self.logger.log_action("heuristic_mode_start", {
            "goal": goal,
            "user_profile": user_profile.name if user_profile else "none"
        })
        
        # Set up initial state
        success = False
        message = "Heuristic interaction completed"
        turn_count = 0
        
        # Simulate conversation turns
        try:
            # First, browse some posts
            num_posts_to_browse = min(5, len(self.simulated_posts))
            posts_to_browse = random.sample(self.simulated_posts, num_posts_to_browse)
            
            for post in posts_to_browse:
                if self.interaction_count >= self.max_interactions:
                    break
                    
                turn_count += 1
                self.interaction_count += 1
                
                # Log the post viewing
                self.logger.log_action("heuristic_post_view", {
                    "post_id": post["id"],
                    "post_content": post["content"]
                })
                
                # Make a decision based on the user profile
                if user_profile:
                    decision_context = {"post_content": post["content"]}
                    decision = user_profile.make_heuristic_decision("rating", decision_context)
                    
                    # Execute the decision
                    decision_type = decision.get("decision", "skip")
                    reason = decision.get("reason", "")
                    
                    if decision_type == "favorite":
                        self.logger.log_action("heuristic_favorite", {
                            "post_id": post["id"],
                            "reason": reason
                        })
                    elif decision_type == "bookmark":
                        self.logger.log_action("heuristic_bookmark", {
                            "post_id": post["id"],
                            "reason": reason
                        })
                    elif decision_type == "view":
                        self.logger.log_action("heuristic_view_details", {
                            "post_id": post["id"],
                            "reason": reason
                        })
                    
                    # Generate feedback
                    feedback = user_profile.rate_recommendation(post["content"])
                    self.logger.log_action("heuristic_feedback", {
                        "post_id": post["id"],
                        "feedback": feedback
                    })
                    
                    # Submit feedback to API
                    try:
                        self.feedback_module.record_feedback(
                            session_id=self.session_id,
                            user_id=user_profile.user_id,
                            post_id=post["id"],
                            feedback_text=feedback,
                            submit_to_api=True
                        )
                    except Exception as e:
                        self.logger.log_action("heuristic_feedback_error", {
                            "error": str(e)
                        })
            
            # Simulate privacy settings change if user is a privacy tester
            if user_profile and user_profile.name == "privacy_tester":
                # Make privacy decision
                privacy_context = {"current_level": self.current_privacy_level}
                privacy_decision = user_profile.make_heuristic_decision("privacy", privacy_context)
                new_level = privacy_decision.get("decision", "limited")
                
                # Log the decision
                self.logger.log_action("heuristic_privacy_change", {
                    "old_level": self.current_privacy_level,
                    "new_level": new_level,
                    "reason": privacy_decision.get("reason", "")
                })
                
                # Update privacy settings
                try:
                    result = self.feedback_module.update_privacy_settings(
                        user_profile.user_id,
                        new_level
                    )
                    self.current_privacy_level = new_level
                    if hasattr(user_profile, 'current_privacy_level'):
                        user_profile.current_privacy_level = new_level
                except Exception as e:
                    self.logger.log_action("heuristic_privacy_error", {
                        "error": str(e)
                    })
            
            # Interaction succeeded
            success = True
            
        except Exception as e:
            self.logger.log_action("heuristic_error", {
                "error": str(e),
                "type": type(e).__name__
            })
            message = f"Error during heuristic interaction: {str(e)}"
        
        # Log the end of interaction
        self.logger.log_action("heuristic_mode_end", {
            "success": success,
            "message": message,
            "interactions_used": self.interaction_count
        })
        
        # Return results
        return {
            "session_id": self.session_id,
            "goal": goal,
            "success": success,
            "message": message,
            "mode": "heuristic",
            "turns_used": turn_count,
            "interactions_used": self.interaction_count,
            "user_profile": user_profile.name if user_profile else "none",
            "logs": self.logger.get_session_logs(self.session_id)
        }
    
    def _process_tool_use(self, tool_use: Dict[str, Any]) -> Dict[str, Any]:
        """Process special commands from the computer_use tool.
        
        Args:
            tool_use: The computer_use tool input
            
        Returns:
            Tool response with observations
        """
        input_text = str(tool_use.get("input", "")).lower()
        
        # Check if this is a privacy settings change request
        if "privacy" in input_text and any(level in input_text for level in ["full", "limited", "none"]):
            return self._handle_privacy_change(input_text)
        
        # Check if this is a recommendation rating
        elif "rate" in input_text and "recommendation" in input_text:
            return self._handle_recommendation_rating(input_text)
        
        # Default browser interaction (simulated)
        else:
            return self._simulate_browser_interaction(input_text)
    
    def _handle_privacy_change(self, input_text: str) -> Dict[str, Any]:
        """Handle a privacy setting change request.
        
        Args:
            input_text: The tool use input text
            
        Returns:
            Tool response with privacy change results
        """
        # Determine the requested privacy level
        if "limited" in input_text:
            requested_level = "limited"
        elif "none" in input_text:
            requested_level = "none"
        elif "full" in input_text:
            requested_level = "full"
        else:
            requested_level = None
        
        if not requested_level:
            return {
                "type": "tool_result",
                "status": "error",
                "observation": "Unable to determine requested privacy level. Please specify 'full', 'limited', or 'none'."
            }
        
        # Log the current settings before change
        if self.user_profile:
            try:
                # Get current settings
                current_settings = self.feedback_module.get_privacy_settings(self.user_profile.user_id)
                self.logger.log_action("privacy_before_change", current_settings)
                
                # Update settings
                new_settings = self.feedback_module.update_privacy_settings(
                    self.user_profile.user_id, 
                    requested_level
                )
                
                # Update local tracking
                self.current_privacy_level = requested_level
                if hasattr(self.user_profile, 'current_privacy_level'):
                    self.user_profile.current_privacy_level = requested_level
                
                # Update successful
                return {
                    "type": "tool_result",
                    "status": "success",
                    "observation": f"Privacy settings updated to '{requested_level}'. You may now notice changes in the recommendations you receive."
                }
                
            except Exception as e:
                # Error updating settings
                self.logger.log_action("privacy_change_error", {"error": str(e)})
                return {
                    "type": "tool_result",
                    "status": "error",
                    "observation": f"Error updating privacy settings: {str(e)}"
                }
        else:
            # Simulate update for testing when no user profile is available
            self.current_privacy_level = requested_level
            self.logger.log_action("privacy_change_simulated", {
                "old_level": "unknown",
                "new_level": requested_level
            })
            
            return {
                "type": "tool_result",
                "status": "success",
                "observation": f"(SIMULATED) Privacy settings updated to '{requested_level}'. You may now notice changes in the recommendations you receive."
            }
    
    def _handle_recommendation_rating(self, input_text: str) -> Dict[str, Any]:
        """Handle a request to rate a recommendation.
        
        Args:
            input_text: The tool use input text
            
        Returns:
            Tool response with rating results
        """
        # Extract post ID (simulated)
        post_id = None
        post_content = None
        
        # Check if we need to handle a batch of posts
        if "rate multiple posts" in input_text.lower() or "batch" in input_text.lower():
            return self._handle_batch_recommendation_rating(input_text)
        
        for post in self.simulated_posts:
            if post["id"] in input_text:
                post_id = post["id"]
                post_content = post["content"]
                break
        
        if not post_id:
            # If no specific post ID found, pick a random one
            post = random.choice(self.simulated_posts)
            post_id = post["id"]
            post_content = post["content"]
        
        # Check if we already have a cached response for this post
        cache_key = f"{post_id}_{self.user_profile.name if self.user_profile else 'anonymous'}"
        if cache_key in self.post_cache:
            feedback_text = self.post_cache[cache_key]
            self.logger.log_action("cached_feedback_used", {
                "post_id": post_id,
                "feedback": feedback_text
            })
        else:
            # Generate feedback from the user profile
            if self.user_profile:
                feedback_text = self.user_profile.rate_recommendation(post_content)
            else:
                # Default feedback if no user profile
                sentiments = ["I like this post!", "Not really what I'm looking for.", 
                            "Great recommendation!", "This is somewhat interesting."]
                feedback_text = random.choice(sentiments)
            
            # Store in cache
            self.post_cache[cache_key] = feedback_text
        
        # Log and record the feedback
        user_id = self.user_profile.user_id if self.user_profile else f"anonymous_user_{random.randint(1000, 9999)}"
        
        # Submit feedback
        try:
            # Submit to feedback module
            feedback_result = self.feedback_module.record_feedback(
                session_id=self.session_id,
                user_id=user_id,
                post_id=post_id,
                feedback_text=feedback_text,
                submit_to_api=True  # Try to submit to the API
            )
            
            return {
                "type": "tool_result",
                "status": "success",
                "observation": f"Thank you for your feedback on post {post_id}. You said: \"{feedback_text}\""
            }
            
        except Exception as e:
            self.logger.log_action("feedback_error", {"error": str(e)})
            
            # Still log locally even if API submission failed
            self.feedback_module.record_feedback(
                session_id=self.session_id,
                user_id=user_id,
                post_id=post_id,
                feedback_text=feedback_text,
                submit_to_api=False
            )
            
            return {
                "type": "tool_result",
                "status": "warning",
                "observation": f"Your feedback was recorded locally but could not be submitted to the API. Your feedback was: \"{feedback_text}\""
            }
    
    def _handle_batch_recommendation_rating(self, input_text: str) -> Dict[str, Any]:
        """Handle a request to rate multiple recommendations at once.
        
        Args:
            input_text: The tool use input text
            
        Returns:
            Tool response with batch rating results
        """
        # Select a batch of posts to rate
        batch_size = min(3, len(self.simulated_posts))
        posts_to_rate = random.sample(self.simulated_posts, batch_size)
        post_contents = [post["content"] for post in posts_to_rate]
        
        if not self.user_profile:
            # Generate simple feedback for each post
            feedback_texts = {
                post["content"]: f"I {'like' if random.random() > 0.5 else 'dislike'} this post." 
                for post in posts_to_rate
            }
        else:
            # Use the batch processing method for efficiency
            feedback_texts = self.user_profile.handle_post_batch(post_contents)
        
        # Record all feedback
        user_id = self.user_profile.user_id if self.user_profile else f"anonymous_user_{random.randint(1000, 9999)}"
        success_count = 0
        
        for i, post in enumerate(posts_to_rate):
            post_id = post["id"]
            post_content = post["content"]
            feedback_text = feedback_texts.get(post_content, "No specific feedback.")
            
            # Cache the feedback
            cache_key = f"{post_id}_{self.user_profile.name if self.user_profile else 'anonymous'}"
            self.post_cache[cache_key] = feedback_text
            
            try:
                # Submit to feedback module
                self.feedback_module.record_feedback(
                    session_id=self.session_id,
                    user_id=user_id,
                    post_id=post_id,
                    feedback_text=feedback_text,
                    submit_to_api=True
                )
                success_count += 1
            except Exception as e:
                self.logger.log_action("batch_feedback_error", {
                    "post_id": post_id,
                    "error": str(e)
                })
                
                # Log locally if API fails
                self.feedback_module.record_feedback(
                    session_id=self.session_id,
                    user_id=user_id,
                    post_id=post_id,
                    feedback_text=feedback_text,
                    submit_to_api=False
                )
        
        # Summarize the batch operation
        return {
            "type": "tool_result",
            "status": "success",
            "observation": f"Processed feedback for {batch_size} posts. Successfully submitted {success_count}/{batch_size} feedback items."
        }
    
    def _simulate_browser_interaction(self, input_text: str) -> Dict[str, Any]:
        """Simulate a browser interaction.
        
        Args:
            input_text: The tool use input text
            
        Returns:
            Simulated browser response
        """
        # Log the action
        action_type = "unknown"
        if "scroll" in input_text:
            action_type = "scroll"
        elif "click" in input_text:
            action_type = "click"
        elif "favorite" in input_text or "like" in input_text:
            action_type = "favorite"
        elif "bookmark" in input_text:
            action_type = "bookmark"
        elif "search" in input_text:
            action_type = "search"
        
        self.logger.log_action(f"simulated_{action_type}", {"input": input_text})
        
        # Different responses based on action type
        if action_type == "scroll":
            # Simulate scrolling to reveal posts
            post_sample = random.sample(self.simulated_posts, min(3, len(self.simulated_posts)))
            posts_html = "\n".join([f"<div class='post' id='{p['id']}'>{p['content']}</div>" for p in post_sample])
            
            return {
                "type": "tool_result",
                "status": "success",
                "observation": f"Scrolled down the page. Showing posts:\n{posts_html}"
            }
        
        elif action_type in ["favorite", "bookmark"]:
            # Simulate liking or bookmarking a post
            post = random.choice(self.simulated_posts)
            
            return {
                "type": "tool_result",
                "status": "success",
                "observation": f"You {action_type}d the post: {post['id']}\nPost content: {post['content']}"
            }
        
        elif action_type == "click":
            # Simulate clicking on various elements
            if "settings" in input_text or "privacy" in input_text:
                privacy_html = (
                    "<h2>Privacy Settings</h2>\n"
                    "<form>\n"
                    "  <input type='radio' name='privacy' value='full'> Full tracking (personalized recommendations)\n"
                    "  <input type='radio' name='privacy' value='limited'> Limited tracking (moderate personalization)\n"
                    "  <input type='radio' name='privacy' value='none'> No tracking (generic recommendations)\n"
                    "  <button type='submit'>Save Settings</button>\n"
                    "</form>"
                )
                
                return {
                    "type": "tool_result",
                    "status": "success",
                    "observation": f"Navigated to Privacy Settings page. Current level: {self.current_privacy_level}\n{privacy_html}"
                }
            else:
                # Simulate clicking on a post or other element
                post = random.choice(self.simulated_posts)
                
                return {
                    "type": "tool_result",
                    "status": "success",
                    "observation": f"Clicked on {post['id']}. Showing detailed view:\n<div class='post-detail'>{post['content']}</div>"
                }
        
        else:
            # Generic interaction
            return {
                "type": "tool_result",
                "status": "success",
                "observation": f"Performed browser action: {input_text}"
            }
    
    def execute_claude_request(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a request to Claude API with computer_use tools.
        
        Args:
            messages: List of message objects for the conversation
            tools: List of tool configurations to enable
            
        Returns:
            Claude's API response
        """
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"  # Update to latest version as needed
        }
        
        payload = {
            "model": "claude-3-opus-20240229",  # Use appropriate model
            "messages": messages,
            "max_tokens": 4096
        }
        
        # Add tools if provided
        if tools:
            payload["tools"] = tools
        
        # Log the request (excluding API key)
        safe_payload = payload.copy()
        safe_payload["api_key"] = "[REDACTED]"
        self.logger.log_action("claude_request", safe_payload)
        
        # Record starting timestamp for metrics
        start_time = time.time()
        
        try:
            # Make the API request
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )
            
            # Record request duration
            request_duration = time.time() - start_time
            
            response_data = response.json()
            
            # Log the response
            self.logger.log_action("claude_response", {
                "status_code": response.status_code,
                "content": response_data
            })
            
            # Track token usage if token tracker is available
            if self.token_tracker and "usage" in response_data:
                usage = response_data.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                self.token_tracker.record_usage(
                    model=payload["model"],
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    request_duration=request_duration
                )
            
            return response_data
            
        except Exception as e:
            error_details = {"error": str(e), "type": type(e).__name__}
            self.logger.log_action("claude_request_error", error_details)
            raise
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        import uuid
        import time
        
        # Create a unique ID based on time and a random component
        timestamp = int(time.time())
        random_id = str(uuid.uuid4())[:8]
        
        return f"session_{timestamp}_{random_id}"
    
    def _generate_random_post_content(self) -> str:
        """Generate random post content for testing.
        
        Returns:
            Simulated post content
        """
        topics = [
            "Linux enthusiasts! Just discovered a hidden corgi feature in the latest kernel update. #OpenSourceCorgis",
            "Check out this cute corgi learning to code Python! #CodingPets",
            "Morning news: Studies show corgis make excellent tech support animals. #FactChecked",
            "OPINION: Are corgis the most politically neutral pets? Our analysis says YES! #ControversialTake",
            "Just posted a new privacy guide featuring my corgi as the mascot. #DigitalPrivacy",
            "LOL this corgi meme about debugging code is too accurate 😂 #DevHumor",
            "Breaking: New research confirms corgis are 74% floof, 26% attitude. #ScienceFacts",
            "My corgi just made the most hilarious face when the compiler threw an error! #ProgrammingWithPets",
            "10 privacy tips every corgi owner should know about online data collection. #PrivacyMatters",
            "This corgi playing in the snow is EVERYTHING! Most wholesome content you'll see today. #CorgiJoy"
        ]
        
        return random.choice(topics)