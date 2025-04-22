from typing import Dict, Any, List, Optional, Set
import os
import json
import random
from datetime import datetime

class UserProfile:
    """Base class for synthetic user profiles that interact with the Corgi Recommender."""
    
    def __init__(self, name: str, description: str, preferred_topics: Optional[List[str]] = None, use_browser: bool = True):
        """Initialize a user profile.
        
        Args:
            name: Name identifier for this user profile
            description: Human-readable description of this user's behavior
            preferred_topics: List of topics this user is interested in
            use_browser: Whether this profile requires browser tooling
        """
        self.name = name
        self.description = description
        self.preferred_topics = preferred_topics or []
        self.user_id = f"{name}_{random.randint(1000, 9999)}"
        self.use_browser = use_browser
        
    def get_behavior_prompt(self, time_of_day: Optional[str] = None, test_goal: Optional[str] = None) -> str:
        """Return the prompt that guides this user's behavior.
        
        Args:
            time_of_day: Optional time context (morning, afternoon, evening, night)
            test_goal: Optional specific test goal for this session
            
        Returns:
            A string prompt describing how this user should behave
        """
        raise NotImplementedError("Subclasses must implement get_behavior_prompt()")
    
    def rate_recommendation(self, post_content: str) -> str:
        """Generate a natural language feedback response to a post.
        
        Args:
            post_content: Content of the post to rate
            
        Returns:
            Natural language feedback about the recommendation
        """
        raise NotImplementedError("Subclasses must implement rate_recommendation()")
    
    def get_session_config(self, time_of_day: Optional[str] = None, test_goal: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration parameters for a session with this user.
        
        Args:
            time_of_day: Optional time context
            test_goal: Optional specific test goal
            
        Returns:
            Dictionary of configuration parameters
        """
        return {
            "profile_name": self.name,
            "profile_description": self.description,
            "preferred_topics": self.preferred_topics,
            "user_id": self.user_id,
            "use_browser": self.use_browser,
            "behavior_prompt": self.get_behavior_prompt(time_of_day, test_goal)
        }
    
    def handle_post_batch(self, post_contents: List[str]) -> Dict[str, str]:
        """Process a batch of posts and provide feedback.
        
        Args:
            post_contents: List of post contents to evaluate
            
        Returns:
            Dictionary mapping post content to feedback
        """
        # Default implementation processes posts one by one
        # Subclasses can override for more efficient batch processing
        return {post: self.rate_recommendation(post) for post in post_contents}
    
    def make_heuristic_decision(self, action_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Make a decision using heuristics instead of LLM (for no-llm mode).
        
        Args:
            action_type: Type of action to decide on (e.g., 'rating', 'privacy', 'interact')
            context: Contextual information for the decision
            
        Returns:
            Decision result
        """
        # Default implementation based on simple rules (should be overridden by subclasses)
        if action_type == "rating":
            post_content = context.get("post_content", "")
            return {"decision": "like" if any(topic in post_content.lower() for topic in self.preferred_topics) else "skip"}
        
        elif action_type == "privacy":
            # Default to middle privacy setting
            return {"decision": "limited"}
        
        elif action_type == "interact":
            # Randomly decide to interact or not
            return {"decision": random.choice(["scroll", "favorite", "bookmark", "view_details"])}
        
        return {"decision": "no_action"}


class TechFan(UserProfile):
    """A synthetic user who is interested in technology-related content."""
    
    def __init__(self):
        preferred_topics = [
            "linux", "programming", "coding", "open source", "development", 
            "technology", "ai", "machine learning", "data science", "computers"
        ]
        super().__init__(
            name="tech_fan",
            description="A user who loves technology and is interested in tech-related content",
            preferred_topics=preferred_topics,
            use_browser=True  # Requires browser for UI interactions
        )
    
    def get_behavior_prompt(self, time_of_day: Optional[str] = None, test_goal: Optional[str] = None) -> str:
        """Generate a behavior prompt for the tech fan.
        
        Args:
            time_of_day: Optional time context
            test_goal: Optional specific test goal
            
        Returns:
            Behavior prompt for the tech fan
        """
        # Default prompt
        base_prompt = (
            "You are a technology enthusiast browsing the Corgi Recommender service. "
            "Your goal is to find and interact with tech-related content, especially posts about:\n"
            "- Programming and coding\n"
            "- Linux and open source software\n"
            "- AI and machine learning\n"
            "- New gadgets and hardware\n\n"
        )
        
        # Modify based on time of day
        if time_of_day == "morning":
            base_prompt += "It's morning, and you're looking for quick tech news updates to start your day.\n\n"
        elif time_of_day == "evening":
            base_prompt += "It's evening, and you have time to deeply engage with technical content.\n\n"
        
        # Modify based on specific test goal
        if test_goal:
            base_prompt += f"Your specific goal for this session is: {test_goal}\n\n"
        else:
            base_prompt += (
                "For this session:\n"
                "1. Scroll through the timeline looking for tech-related posts\n"
                "2. Favorite at least 2 posts that mention programming, coding, or technology\n"
                "3. Bookmark any post that specifically mentions Linux or open source\n"
                "4. Provide feedback on at least 1 recommendation\n"
                "5. Ignore posts about fashion, sports, or entertainment\n\n"
            )
        
        base_prompt += (
            "Be authentic in your browsing - take time to read posts, don't just rapidly click. "
            "React to the content naturally, and provide thoughtful feedback when prompted."
        )
        
        return base_prompt
    
    def rate_recommendation(self, post_content: str) -> str:
        """Generate feedback for a post based on tech preferences.
        
        Args:
            post_content: Content of the post to rate
            
        Returns:
            Natural language feedback
        """
        # Check if the post contains any preferred topics
        post_lower = post_content.lower()
        matching_topics = [topic for topic in self.preferred_topics if topic in post_lower]
        
        if matching_topics:
            # Positive feedback for matching topics
            topic_match = matching_topics[0]
            positive_responses = [
                f"Great recommendation! I love content about {topic_match}.",
                f"This is exactly the kind of {topic_match} content I'm looking for!",
                f"Excellent {topic_match} post. More like this, please!",
                f"This {topic_match} post is quite informative, nice suggestion."
            ]
            return random.choice(positive_responses)
        else:
            # Negative feedback for non-matching content
            negative_responses = [
                "This isn't really what I'm interested in. I prefer tech-related content.",
                "Not very relevant to my tech interests. Could use better targeting.",
                "I'd prefer to see more posts about programming and technology.",
                "This seems off-topic for me. I'm mainly here for tech content."
            ]
            return random.choice(negative_responses)
    
    def handle_post_batch(self, post_contents: List[str]) -> Dict[str, str]:
        """Process multiple tech posts efficiently.
        
        Args:
            post_contents: List of post contents to evaluate
            
        Returns:
            Dictionary mapping post content to feedback
        """
        results = {}
        tech_posts = []
        non_tech_posts = []
        
        # Classify posts
        for post in post_contents:
            post_lower = post.lower()
            if any(topic in post_lower for topic in self.preferred_topics):
                tech_posts.append(post)
            else:
                non_tech_posts.append(post)
        
        # Generate feedback for tech posts
        for post in tech_posts:
            post_lower = post.lower()
            matching_topics = [topic for topic in self.preferred_topics if topic in post_lower]
            topic_match = matching_topics[0] if matching_topics else "technology"
            
            positive_responses = [
                f"Great recommendation! I love content about {topic_match}.",
                f"This is exactly the kind of {topic_match} content I'm looking for!",
                f"Excellent {topic_match} post. More like this, please!",
                f"This {topic_match} post is quite informative, nice suggestion."
            ]
            results[post] = random.choice(positive_responses)
        
        # Generate feedback for non-tech posts
        for post in non_tech_posts:
            negative_responses = [
                "This isn't really what I'm interested in. I prefer tech-related content.",
                "Not very relevant to my tech interests. Could use better targeting.",
                "I'd prefer to see more posts about programming and technology.",
                "This seems off-topic for me. I'm mainly here for tech content."
            ]
            results[post] = random.choice(negative_responses)
        
        return results
    
    def make_heuristic_decision(self, action_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Make tech-fan decisions using heuristics.
        
        Args:
            action_type: Type of action to decide on
            context: Contextual information for the decision
            
        Returns:
            Decision result
        """
        if action_type == "rating":
            post_content = context.get("post_content", "").lower()
            
            # Check for tech-related keywords
            if any(topic in post_content for topic in self.preferred_topics):
                # Decide to favorite tech posts with 80% probability
                if random.random() < 0.8:
                    return {"decision": "favorite", "reason": "tech content"}
                # Sometimes bookmark instead (20% of tech posts)
                else:
                    return {"decision": "bookmark", "reason": "tech content for later"}
            else:
                # Skip non-tech content with 90% probability
                if random.random() < 0.9:
                    return {"decision": "skip", "reason": "not tech-related"}
                else:
                    return {"decision": "view", "reason": "exploring different content"}
        
        elif action_type == "privacy":
            # Tech fans typically prefer full data collection for better recommendations
            return {"decision": "full", "reason": "better tech recommendations"}
        
        elif action_type == "interact":
            # Tech fans spend more time reading technical content
            actions = ["scroll", "scroll", "scroll", "favorite", "bookmark", "view_details"]
            return {"decision": random.choice(actions)}
        
        return {"decision": "no_action"}


class NewsSkeptic(UserProfile):
    """A synthetic user who is skeptical of news content and prefers factual, verified information."""
    
    def __init__(self):
        preferred_topics = [
            "verified news", "fact checking", "research", "data journalism",
            "science", "education", "analysis", "critical thinking"
        ]
        super().__init__(
            name="news_skeptic",
            description="A user who is skeptical of news content and prefers factual, verified information",
            preferred_topics=preferred_topics,
            use_browser=True  # Requires browser for UI interactions
        )
        
        # Define topics that this user is skeptical about
        self.skeptical_topics = [
            "politics", "opinion", "sensational", "clickbait", "unverified",
            "rumor", "conspiracy", "anonymous sources"
        ]
    
    def get_behavior_prompt(self, time_of_day: Optional[str] = None, test_goal: Optional[str] = None) -> str:
        """Generate a behavior prompt for the news skeptic.
        
        Args:
            time_of_day: Optional time context
            test_goal: Optional specific test goal
            
        Returns:
            Behavior prompt for the news skeptic
        """
        # Default prompt
        base_prompt = (
            "You are a news-skeptic user browsing the Corgi Recommender service. "
            "You highly value factual, verified information and are skeptical of sensationalist content. "
            "You're especially interested in:\n"
            "- Fact-checked news\n"
            "- Data-driven analysis\n"
            "- Science and research content\n"
            "- Educational material\n\n"
            "You actively avoid:\n"
            "- Political opinion pieces\n"
            "- Sensationalist headlines\n"
            "- Content with unverified claims\n"
            "- Posts with emotional language but few facts\n\n"
        )
        
        # Modify based on time of day
        if time_of_day == "morning":
            base_prompt += "It's morning, and you're checking for factual news updates while being wary of misinformation.\n\n"
        elif time_of_day == "evening":
            base_prompt += "It's evening, and you want to review the day's news with a critical eye for accuracy.\n\n"
        
        # Modify based on specific test goal
        if test_goal:
            base_prompt += f"Your specific goal for this session is: {test_goal}\n\n"
        else:
            base_prompt += (
                "For this session:\n"
                "1. Scroll through the timeline looking for fact-based, educational content\n"
                "2. Be skeptical of posts that make strong claims without evidence\n"
                "3. Favorite posts that present balanced, well-researched information\n"
                "4. Provide critical feedback on recommendations that seem sensationalist\n"
                "5. Try switching privacy settings and observe if recommendations improve\n\n"
            )
        
        base_prompt += (
            "Be thorough in your assessment - take time to read and evaluate posts. "
            "Your feedback should explain why you find content trustworthy or suspicious."
        )
        
        return base_prompt
    
    def rate_recommendation(self, post_content: str) -> str:
        """Generate feedback for a post based on skeptical assessment.
        
        Args:
            post_content: Content of the post to rate
            
        Returns:
            Natural language feedback with skeptical analysis
        """
        post_lower = post_content.lower()
        
        # Check if post contains preferred topics
        matching_preferred = [topic for topic in self.preferred_topics if topic in post_lower]
        
        # Check if post contains skeptical topics
        matching_skeptical = [topic for topic in self.skeptical_topics if topic in post_lower]
        
        if matching_preferred and not matching_skeptical:
            # Positive feedback for trustworthy content
            positive_responses = [
                "This is good, factual content. I appreciate well-researched information.",
                "Solid information with proper context. This is the kind of content I trust.",
                "Clear, factual reporting without sensationalism. Exactly what I look for.",
                "Good balance of facts and analysis. More recommendations like this, please."
            ]
            return random.choice(positive_responses)
        
        elif matching_skeptical:
            # Negative feedback for content that triggers skepticism
            topic = matching_skeptical[0]
            negative_responses = [
                f"Too much {topic} content with not enough verified information.",
                f"This seems to contain {topic} elements that I find questionable.",
                f"I prefer more factual content and less {topic}-focused material.",
                f"This recommendation seems too focused on {topic} rather than facts."
            ]
            return random.choice(negative_responses)
        
        else:
            # Neutral feedback
            neutral_responses = [
                "This content seems neutral, but I'd prefer more fact-based information.",
                "Not bad, but could use more data and research to back up the claims.",
                "Acceptable content, though I typically look for more in-depth analysis.",
                "Neither particularly factual nor sensationalist. Somewhat relevant to my interests."
            ]
            return random.choice(neutral_responses)
    
    def handle_post_batch(self, post_contents: List[str]) -> Dict[str, str]:
        """Process multiple news posts with skeptical assessment.
        
        Args:
            post_contents: List of post contents to evaluate
            
        Returns:
            Dictionary mapping post content to feedback
        """
        results = {}
        
        # Categorize posts
        factual_posts = []
        skeptical_posts = []
        neutral_posts = []
        
        for post in post_contents:
            post_lower = post.lower()
            matching_preferred = [topic for topic in self.preferred_topics if topic in post_lower]
            matching_skeptical = [topic for topic in self.skeptical_topics if topic in post_lower]
            
            if matching_preferred and not matching_skeptical:
                factual_posts.append(post)
            elif matching_skeptical:
                skeptical_posts.append(post)
            else:
                neutral_posts.append(post)
        
        # Generate feedback for factual posts
        for post in factual_posts:
            positive_responses = [
                "This is good, factual content. I appreciate well-researched information.",
                "Solid information with proper context. This is the kind of content I trust.",
                "Clear, factual reporting without sensationalism. Exactly what I look for.",
                "Good balance of facts and analysis. More recommendations like this, please."
            ]
            results[post] = random.choice(positive_responses)
        
        # Generate feedback for skeptical posts
        for post in skeptical_posts:
            post_lower = post.lower()
            matching_skeptical = [topic for topic in self.skeptical_topics if topic in post_lower]
            topic = matching_skeptical[0] if matching_skeptical else "sensationalism"
            
            negative_responses = [
                f"Too much {topic} content with not enough verified information.",
                f"This seems to contain {topic} elements that I find questionable.",
                f"I prefer more factual content and less {topic}-focused material.",
                f"This recommendation seems too focused on {topic} rather than facts."
            ]
            results[post] = random.choice(negative_responses)
        
        # Generate feedback for neutral posts
        for post in neutral_posts:
            neutral_responses = [
                "This content seems neutral, but I'd prefer more fact-based information.",
                "Not bad, but could use more data and research to back up the claims.",
                "Acceptable content, though I typically look for more in-depth analysis.",
                "Neither particularly factual nor sensationalist. Somewhat relevant to my interests."
            ]
            results[post] = random.choice(neutral_responses)
        
        return results
    
    def make_heuristic_decision(self, action_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Make skeptical-news decisions using heuristics.
        
        Args:
            action_type: Type of action to decide on
            context: Contextual information for the decision
            
        Returns:
            Decision result
        """
        if action_type == "rating":
            post_content = context.get("post_content", "").lower()
            
            # Check for factual and skeptical keywords
            matching_preferred = [topic for topic in self.preferred_topics if topic in post_content]
            matching_skeptical = [topic for topic in self.skeptical_topics if topic in post_content]
            
            if matching_preferred and not matching_skeptical:
                # High chance to like factual content
                return {"decision": "favorite", "reason": "factual content"}
            elif matching_skeptical:
                # Almost always skip content with skeptical topics
                return {"decision": "skip", "reason": f"contains {matching_skeptical[0]}"}
            else:
                # Neutral content gets a mixed response
                return {"decision": random.choice(["view", "skip"]), "reason": "neutral content"}
        
        elif action_type == "privacy":
            # News skeptics prefer high privacy
            return {"decision": random.choice(["limited", "none"]), "reason": "privacy concerns"}
        
        elif action_type == "interact":
            # Skeptics read carefully but interact less
            return {"decision": random.choice(["scroll", "scroll", "scroll", "view_details"])}
        
        return {"decision": "no_action"}


class MemeLover(UserProfile):
    """A synthetic user who enjoys humorous, light-hearted content and memes."""
    
    def __init__(self):
        preferred_topics = [
            "memes", "funny", "humor", "jokes", "comedy", "entertainment",
            "cute animals", "wholesome", "viral", "trending"
        ]
        super().__init__(
            name="meme_lover",
            description="A user who enjoys humorous, light-hearted content and memes",
            preferred_topics=preferred_topics,
            use_browser=True  # Requires browser for UI interactions
        )
    
    def get_behavior_prompt(self, time_of_day: Optional[str] = None, test_goal: Optional[str] = None) -> str:
        """Generate a behavior prompt for the meme lover.
        
        Args:
            time_of_day: Optional time context
            test_goal: Optional specific test goal
            
        Returns:
            Behavior prompt for the meme lover
        """
        # Default prompt
        base_prompt = (
            "You are a meme enthusiast browsing the Corgi Recommender service. "
            "You're looking for fun, entertaining, and light-hearted content that makes you laugh. "
            "You particularly enjoy:\n"
            "- Clever memes and funny images\n"
            "- Cute animal content (especially corgis!)\n"
            "- Witty jokes and humorous posts\n"
            "- Trending and viral content\n\n"
            "You tend to skip over:\n"
            "- Serious news and politics\n"
            "- Technical or complex content\n"
            "- Long, text-heavy posts\n\n"
        )
        
        # Modify based on time of day
        if time_of_day == "morning":
            base_prompt += "It's morning, and you're looking for some humor to start your day with a smile.\n\n"
        elif time_of_day == "evening":
            base_prompt += "It's evening, and you want to unwind with some light-hearted, funny content.\n\n"
        
        # Modify based on specific test goal
        if test_goal:
            base_prompt += f"Your specific goal for this session is: {test_goal}\n\n"
        else:
            base_prompt += (
                "For this session:\n"
                "1. Scroll looking for funny and entertaining posts\n"
                "2. Favorite at least 3 posts that make you laugh\n"
                "3. Bookmark especially good memes or cute animal content\n"
                "4. Share your reaction to recommendations (what you find funny)\n"
                "5. Try different privacy settings to see if you get better humor content\n\n"
            )
        
        base_prompt += (
            "Be enthusiastic and spontaneous in your browsing - react with genuine amusement "
            "to content you find funny, and don't spend too long on serious content."
        )
        
        return base_prompt
    
    def rate_recommendation(self, post_content: str) -> str:
        """Generate feedback for a post based on humor preferences.
        
        Args:
            post_content: Content of the post to rate
            
        Returns:
            Natural language feedback with humor assessment
        """
        post_lower = post_content.lower()
        
        # Check if post contains preferred topics
        matching_preferred = [topic for topic in self.preferred_topics if topic in post_lower]
        
        # Special case for corgi content (always positive)
        if "corgi" in post_lower:
            corgi_responses = [
                "LOVE this corgi content! Absolutely perfect recommendation!",
                "Corgis are the best! This recommendation made my day!",
                "This corgi post is exactly what I'm here for! More please!",
                "OMG such a cute corgi! This recommendation is spot on!"
            ]
            return random.choice(corgi_responses)
        
        if matching_preferred:
            # Positive feedback for funny content
            topic = matching_preferred[0]
            positive_responses = [
                f"Haha! This {topic} content is hilarious! Great recommendation!",
                f"This {topic} post actually made me laugh out loud. More like this!",
                f"Perfect {topic} recommendation - exactly the kind of humor I enjoy.",
                f"This {topic} content is super entertaining! Keep 'em coming!"
            ]
            return random.choice(positive_responses)
        
        else:
            # Negative feedback for non-humorous content
            negative_responses = [
                "This is too serious for my mood. I'm here for the funny stuff!",
                "Not really entertaining or humorous. Looking for more memes and jokes.",
                "This recommendation doesn't match my interest in light-hearted content.",
                "Too dry for my taste. I prefer recommendations that make me laugh."
            ]
            return random.choice(negative_responses)
    
    def handle_post_batch(self, post_contents: List[str]) -> Dict[str, str]:
        """Process multiple posts for humor content.
        
        Args:
            post_contents: List of post contents to evaluate
            
        Returns:
            Dictionary mapping post content to feedback
        """
        results = {}
        
        # Categorize posts
        corgi_posts = []
        funny_posts = []
        serious_posts = []
        
        for post in post_contents:
            post_lower = post.lower()
            
            if "corgi" in post_lower:
                corgi_posts.append(post)
            elif any(topic in post_lower for topic in self.preferred_topics):
                funny_posts.append(post)
            else:
                serious_posts.append(post)
        
        # Generate feedback for corgi posts
        for post in corgi_posts:
            corgi_responses = [
                "LOVE this corgi content! Absolutely perfect recommendation!",
                "Corgis are the best! This recommendation made my day!",
                "This corgi post is exactly what I'm here for! More please!",
                "OMG such a cute corgi! This recommendation is spot on!"
            ]
            results[post] = random.choice(corgi_responses)
        
        # Generate feedback for funny posts
        for post in funny_posts:
            post_lower = post.lower()
            matching_preferred = [topic for topic in self.preferred_topics if topic in post_lower]
            topic = matching_preferred[0] if matching_preferred else "funny"
            
            positive_responses = [
                f"Haha! This {topic} content is hilarious! Great recommendation!",
                f"This {topic} post actually made me laugh out loud. More like this!",
                f"Perfect {topic} recommendation - exactly the kind of humor I enjoy.",
                f"This {topic} content is super entertaining! Keep 'em coming!"
            ]
            results[post] = random.choice(positive_responses)
        
        # Generate feedback for serious posts
        for post in serious_posts:
            negative_responses = [
                "This is too serious for my mood. I'm here for the funny stuff!",
                "Not really entertaining or humorous. Looking for more memes and jokes.",
                "This recommendation doesn't match my interest in light-hearted content.",
                "Too dry for my taste. I prefer recommendations that make me laugh."
            ]
            results[post] = random.choice(negative_responses)
        
        return results
    
    def make_heuristic_decision(self, action_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Make humor-based decisions using heuristics.
        
        Args:
            action_type: Type of action to decide on
            context: Contextual information for the decision
            
        Returns:
            Decision result
        """
        if action_type == "rating":
            post_content = context.get("post_content", "").lower()
            
            # Special case for corgi content
            if "corgi" in post_content:
                return {"decision": random.choice(["favorite", "bookmark"]), "reason": "corgi content!"}
            
            # Check for humor-related keywords
            elif any(topic in post_content for topic in self.preferred_topics):
                # High chance to like humor content
                if random.random() < 0.9:
                    return {"decision": "favorite", "reason": "funny content"}
                else:
                    return {"decision": "bookmark", "reason": "funny content for later"}
            else:
                # Skip serious content
                return {"decision": "skip", "reason": "too serious"}
        
        elif action_type == "privacy":
            # Meme lovers typically don't care much about privacy
            return {"decision": "full", "reason": "better humor recommendations"}
        
        elif action_type == "interact":
            # Meme lovers scroll quickly looking for funny content
            # Higher chance of scrolling to find more content
            actions = ["scroll", "scroll", "scroll", "favorite", "favorite", "bookmark"]
            return {"decision": random.choice(actions)}
        
        return {"decision": "no_action"}


class PrivacyTester(UserProfile):
    """A synthetic user who tests privacy features and observes recommendation changes."""
    
    def __init__(self):
        preferred_topics = [
            "privacy", "security", "data protection", "digital rights",
            "encryption", "anonymity", "tech ethics", "surveillance"
        ]
        super().__init__(
            name="privacy_tester",
            description="A privacy-conscious user who tests privacy settings and observes how they affect recommendations",
            preferred_topics=preferred_topics,
            use_browser=True  # Requires browser for UI interactions
        )
        
        # Track privacy setting changes
        self.initial_recommendations = []
        self.post_privacy_change_recommendations = []
        self.current_privacy_level = "full"  # Default level
    
    def get_behavior_prompt(self, time_of_day: Optional[str] = None, test_goal: Optional[str] = None) -> str:
        """Generate a behavior prompt for the privacy tester.
        
        Args:
            time_of_day: Optional time context
            test_goal: Optional specific test goal
            
        Returns:
            Behavior prompt for the privacy tester
        """
        privacy_level = test_goal.split("privacy_level=")[1] if test_goal and "privacy_level=" in test_goal else None
        
        # Default prompt
        base_prompt = (
            "You are a privacy-conscious user testing the Corgi Recommender service. "
            "Your goal is to evaluate how privacy settings affect content recommendations. "
            "You're particularly interested in:\n"
            "- How personal data influences recommendations\n"
            "- The difference between various privacy levels\n"
            "- Transparency in data collection\n"
            "- Effectiveness of privacy controls\n\n"
        )
        
        # Specific test for a privacy level
        if privacy_level:
            base_prompt += f"For this session, you'll be testing the '{privacy_level}' privacy level:\n\n"
            
            if privacy_level == "full":
                base_prompt += (
                    "Testing FULL privacy level:\n"
                    "1. Browse normally with full tracking enabled\n"
                    "2. Note how personalized the recommendations seem\n"
                    "3. Observe how quickly recommendations adapt to your interactions\n"
                    "4. Record your observations about tracking behavior\n\n"
                )
            elif privacy_level == "limited":
                base_prompt += (
                    "Testing LIMITED privacy level:\n"
                    "1. First, browse normally and note what types of posts are recommended\n"
                    "2. Switch privacy settings to 'limited' mode\n"
                    "3. Continue browsing and observe how recommendations change\n"
                    "4. Note any differences in personalization quality\n\n"
                )
            elif privacy_level == "none":
                base_prompt += (
                    "Testing NONE privacy level:\n"
                    "1. First, browse normally and note what types of posts are recommended\n"
                    "2. Switch privacy settings to 'none' mode (highest privacy)\n"
                    "3. Continue browsing and observe how recommendations change\n"
                    "4. Note the lack of personalization and tracking\n\n"
                )
        else:
            # Default privacy testing behavior
            base_prompt += (
                "For this session:\n"
                "1. First, browse the timeline normally and note what types of posts are recommended\n"
                "2. Find and access the privacy settings\n"
                "3. Change your privacy level to 'limited' (or another level if specified)\n"
                "4. Return to the timeline and observe any changes in recommendations\n"
                "5. Document specific differences before and after the privacy change\n\n"
            )
        
        base_prompt += (
            "Be methodical in your testing - carefully document what types of posts you see "
            "before and after changing settings. Look for subtle changes in content categories, "
            "not just obvious ones. Provide detailed feedback on your observations."
        )
        
        return base_prompt
    
    def rate_recommendation(self, post_content: str) -> str:
        """Generate feedback focusing on privacy implications of recommendations.
        
        Args:
            post_content: Content of the post to rate
            
        Returns:
            Natural language feedback with privacy assessment
        """
        # Different responses based on current privacy level
        if self.current_privacy_level == "full":
            full_responses = [
                "This recommendation seems highly personalized, suggesting detailed tracking of my preferences.",
                "Interesting how this matches my recent interactions. Clear evidence of full tracking.",
                "With full tracking enabled, I notice this content aligns with my demonstrated interests.",
                "The targeting accuracy here indicates comprehensive data collection about my behavior."
            ]
            return random.choice(full_responses)
            
        elif self.current_privacy_level == "limited":
            limited_responses = [
                "With limited privacy, this recommendation seems less personalized but still somewhat relevant.",
                "I notice the recommendations are more general since switching to limited privacy mode.",
                "The limited tracking seems to impact recommendation quality - less tailored but still reasonable.",
                "Interesting balance of privacy and personalization with the limited setting."
            ]
            return random.choice(limited_responses)
            
        elif self.current_privacy_level == "none":
            none_responses = [
                "With maximum privacy enabled, this recommendation appears completely generic.",
                "No sign of personalization here - exactly what I'd expect with 'none' privacy setting.",
                "This content seems random rather than based on my interests, consistent with high privacy.",
                "The recommendation quality has noticeably decreased, but that's the privacy tradeoff I selected."
            ]
            return random.choice(none_responses)
        
        # Default response if privacy level is unknown
        return "Interesting recommendation. I'm evaluating how it relates to my privacy settings."
    
    def handle_post_batch(self, post_contents: List[str]) -> Dict[str, str]:
        """Process a batch of posts with privacy focus.
        
        Args:
            post_contents: List of post contents to evaluate
            
        Returns:
            Dictionary mapping post content to feedback
        """
        results = {}
        
        # Just use the current privacy level for all posts
        privacy_level = self.current_privacy_level
        
        for post in post_contents:
            if privacy_level == "full":
                full_responses = [
                    "This recommendation seems highly personalized, suggesting detailed tracking of my preferences.",
                    "Interesting how this matches my recent interactions. Clear evidence of full tracking.",
                    "With full tracking enabled, I notice this content aligns with my demonstrated interests.",
                    "The targeting accuracy here indicates comprehensive data collection about my behavior."
                ]
                results[post] = random.choice(full_responses)
                
            elif privacy_level == "limited":
                limited_responses = [
                    "With limited privacy, this recommendation seems less personalized but still somewhat relevant.",
                    "I notice the recommendations are more general since switching to limited privacy mode.",
                    "The limited tracking seems to impact recommendation quality - less tailored but still reasonable.",
                    "Interesting balance of privacy and personalization with the limited setting."
                ]
                results[post] = random.choice(limited_responses)
                
            elif privacy_level == "none":
                none_responses = [
                    "With maximum privacy enabled, this recommendation appears completely generic.",
                    "No sign of personalization here - exactly what I'd expect with 'none' privacy setting.",
                    "This content seems random rather than based on my interests, consistent with high privacy.",
                    "The recommendation quality has noticeably decreased, but that's the privacy tradeoff I selected."
                ]
                results[post] = random.choice(none_responses)
            
            else:
                results[post] = "Interesting recommendation. I'm evaluating how it relates to my privacy settings."
        
        return results
    
    def make_heuristic_decision(self, action_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Make privacy-focused decisions using heuristics.
        
        Args:
            action_type: Type of action to decide on
            context: Contextual information for the decision
            
        Returns:
            Decision result
        """
        if action_type == "rating":
            # Privacy testers are more interested in the system behavior than content
            return {"decision": random.choice(["view", "favorite"]), "reason": "testing recommendation behavior"}
        
        elif action_type == "privacy":
            # Privacy testers systematically test different levels
            current_level = context.get("current_level", "full")
            
            if current_level == "full":
                return {"decision": "limited", "reason": "testing limited privacy mode"}
            elif current_level == "limited":
                return {"decision": "none", "reason": "testing maximum privacy"}
            else:
                return {"decision": "full", "reason": "resetting to full tracking to compare"}
        
        elif action_type == "interact":
            # Privacy testers methodically explore the interface
            # Higher chance of accessing settings
            actions = ["scroll", "view_details", "settings", "privacy"]
            return {"decision": random.choice(actions)}
        
        return {"decision": "no_action"}
        

# TextOnlyUser profile for non-browsing use cases
class TextOnlyUser(UserProfile):
    """A synthetic user who only interacts via text without requiring browser tools."""
    
    def __init__(self):
        preferred_topics = [
            "general", "news", "updates", "community", "information",
            "discussions", "questions", "help", "support"
        ]
        super().__init__(
            name="text_only",
            description="A general user who interacts via text commands without using the browser interface",
            preferred_topics=preferred_topics,
            use_browser=False  # Does not require browser tooling
        )
    
    def get_behavior_prompt(self, time_of_day: Optional[str] = None, test_goal: Optional[str] = None) -> str:
        """Generate a behavior prompt for the text-only user.
        
        Args:
            time_of_day: Optional time context
            test_goal: Optional specific test goal
            
        Returns:
            Behavior prompt for the text-only user
        """
        base_prompt = (
            "You are a general user of the Corgi Recommender service who interacts via text commands. "
            "You're interested in getting recommendations and information without using the browser interface. "
            "Your interactions will be simple text requests and responses.\n\n"
        )
        
        if test_goal:
            base_prompt += f"Your specific goal for this session is: {test_goal}\n\n"
        else:
            base_prompt += (
                "For this session:\n"
                "1. Request recommendations based on general interests\n"
                "2. Provide feedback on the recommendations received\n"
                "3. Ask about different categories of content\n"
                "4. Request information about how the recommendation system works\n\n"
            )
        
        return base_prompt
    
    def rate_recommendation(self, post_content: str) -> str:
        """Generate simple text feedback for a recommendation.
        
        Args:
            post_content: Content to rate
            
        Returns:
            Text feedback
        """
        # Simple feedback for text-only interactions
        responses = [
            "Thanks for the recommendation. I found it somewhat interesting.",
            "This recommendation is relevant to my interests.",
            "I appreciate this type of content.",
            "This seems like a reasonable suggestion.",
            "I'd be interested in seeing more content like this."
        ]
        return random.choice(responses)
    
    def make_heuristic_decision(self, action_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Make text-based decisions using heuristics.
        
        Args:
            action_type: Type of action to decide on
            context: Contextual information for the decision
            
        Returns:
            Decision result
        """
        # Text-only users have simpler interactions
        if action_type == "rating":
            return {"decision": "acknowledge", "reason": "acknowledged recommendation"}
        
        elif action_type == "request":
            # Random topics to request
            topics = ["general", "news", "entertainment", "technology", "science", "art"]
            return {"decision": "request", "topic": random.choice(topics)}
        
        return {"decision": "acknowledge"}


def get_profile_by_name(profile_name: str) -> UserProfile:
    """Factory function to get a user profile by name.
    
    Args:
        profile_name: The identifier for the desired profile
        
    Returns:
        A UserProfile instance
        
    Raises:
        ValueError: If the profile name is not recognized
    """
    profiles = {
        "tech_fan": TechFan(),
        "news_skeptic": NewsSkeptic(),
        "meme_lover": MemeLover(),
        "privacy_tester": PrivacyTester(),
        "text_only": TextOnlyUser(),
    }
    
    if profile_name not in profiles:
        valid_profiles = ", ".join(profiles.keys())
        raise ValueError(f"Unknown profile '{profile_name}'. Valid profiles: {valid_profiles}")
    
    return profiles[profile_name]


def list_available_profiles() -> List[Dict[str, Any]]:
    """List all available user profiles.
    
    Returns:
        List of dictionaries with profile information
    """
    profiles = [
        TechFan(),
        NewsSkeptic(),
        MemeLover(),
        PrivacyTester(),
        TextOnlyUser(),
    ]
    
    return [{
        "name": profile.name,
        "description": profile.description,
        "preferred_topics": profile.preferred_topics,
        "use_browser": profile.use_browser
    } for profile in profiles]


def get_time_of_day() -> str:
    """Get the current time of day period.
    
    Returns:
        String indicating time of day (morning, afternoon, evening, night)
    """
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 22:
        return "evening"
    else:
        return "night"