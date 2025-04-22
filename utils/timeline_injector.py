"""
Timeline injector module for corgi-recommender-service.

This module provides functionality to inject posts into a timeline
based on various configurable strategies.
"""

import logging
import random
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from copy import deepcopy

logger = logging.getLogger(__name__)

def get_post_timestamp(post: Dict) -> datetime:
    """Extract datetime object from post's created_at field."""
    if isinstance(post["created_at"], datetime):
        # Make sure it's timezone-aware
        if post["created_at"].tzinfo is None:
            from datetime import timezone
            return post["created_at"].replace(tzinfo=timezone.utc)
        return post["created_at"]
    return datetime.fromisoformat(post["created_at"].replace("Z", "+00:00"))

def sort_posts_by_timestamp(posts: List[Dict]) -> List[Dict]:
    """Sort posts by created_at descending (most recent first)."""
    return sorted(posts, key=get_post_timestamp, reverse=True)

def extract_tags(post: Dict) -> List[str]:
    """Extract hashtags from a post."""
    tags = []
    # Handle Mastodon API format where tags are in a 'tags' array
    if "tags" in post and isinstance(post["tags"], list):
        tags = [tag["name"].lower() for tag in post["tags"] if "name" in tag]
    return tags

def harmonize_timestamp(
    injected_post: Dict, 
    before_post: Optional[Dict] = None, 
    after_post: Optional[Dict] = None,
    gap_ratio: float = 0.6  # Default to placing closer to the more recent post
) -> Dict:
    """
    Assign a realistic timestamp to an injected post based on adjacent posts.
    
    Args:
        injected_post: The post to modify with a new timestamp
        before_post: The post that appears before (more recent) in the timeline
        after_post: The post that appears after (less recent) in the timeline
        gap_ratio: Where to place the post in the time gap (0.0 = at after_post time, 
                  1.0 = at before_post time, 0.5 = exactly in the middle)
    
    Returns:
        The modified post with an updated created_at timestamp
    """
    result = deepcopy(injected_post)
    
    # If we have posts on both sides
    if before_post and after_post:
        before_time = get_post_timestamp(before_post)
        after_time = get_post_timestamp(after_post)
        time_diff = (before_time - after_time).total_seconds()
        gap_seconds = time_diff * gap_ratio
        new_time = after_time + timedelta(seconds=gap_seconds)
        result["created_at"] = new_time.isoformat().replace("+00:00", "Z")
    # If we only have a post before (we're injecting at the end)
    elif before_post:
        before_time = get_post_timestamp(before_post)
        # Place it 2-5 minutes after the last post
        random_minutes = random.uniform(2, 5)
        new_time = before_time - timedelta(minutes=random_minutes)
        result["created_at"] = new_time.isoformat().replace("+00:00", "Z")
    # If we only have a post after (we're injecting at the beginning)
    elif after_post:
        after_time = get_post_timestamp(after_post)
        # Place it 2-5 minutes before the first post
        random_minutes = random.uniform(2, 5)
        new_time = after_time + timedelta(minutes=random_minutes)
        result["created_at"] = new_time.isoformat().replace("+00:00", "Z")
    
    return result

def tag_as_injected(post: Dict) -> Dict:
    """
    Mark a post as injected for frontend identification and add metadata.
    
    This adds the required 'injected' flag and 'injection_metadata' fields
    for transparency in clients like Elk.
    """
    result = deepcopy(post)
    result["injected"] = True
    
    # Skip if metadata is already present (e.g., from recommendation engine)
    if "injection_metadata" not in result:
        # Add default metadata fields
        result["injection_metadata"] = {
            "source": "timeline_injector", 
            "strategy": "general_recommendation",
            "explanation": "Suggested content we think you might find interesting"
        }
    
    return result

def check_time_gap(
    before_post: Dict, 
    after_post: Dict, 
    min_gap_minutes: int
) -> bool:
    """
    Check if there's enough time gap between posts for injection.
    
    Args:
        before_post: The post that appears before (more recent) in the timeline
        after_post: The post that appears after (less recent) in the timeline
        min_gap_minutes: Minimum gap in minutes required for injection
        
    Returns:
        True if gap is large enough for injection, False otherwise
    """
    before_time = get_post_timestamp(before_post)
    after_time = get_post_timestamp(after_post)
    gap_minutes = (before_time - after_time).total_seconds() / 60
    
    meets_requirement = gap_minutes >= min_gap_minutes
    if meets_requirement:
        logger.debug(f"Gap of {gap_minutes:.1f} minutes is sufficient for injection (min: {min_gap_minutes})")
    return meets_requirement

def has_matching_tags(real_post: Dict, injected_post: Dict) -> bool:
    """Check if posts share any hashtags."""
    real_tags = extract_tags(real_post)
    injected_tags = extract_tags(injected_post)
    
    return bool(set(real_tags) & set(injected_tags))

def uniform_injection_points(
    num_real_posts: int, 
    num_injections: int
) -> List[int]:
    """
    Calculate uniformly distributed injection points.
    
    Args:
        num_real_posts: Total number of real posts
        num_injections: Number of posts to inject
        
    Returns:
        List of indices where injected posts should be inserted
    """
    # If we have no real posts, this function shouldn't be called
    # but if it is, return an empty list
    if num_real_posts == 0:
        logger.debug("Called uniform_injection_points with num_real_posts=0, returning empty list")
        return []
        
    # If we have more injections than real posts, place one after each real post
    if num_injections >= num_real_posts:
        return list(range(num_real_posts))
    
    # Calculate evenly spaced insertion points
    spacing = max(1, num_real_posts // (num_injections + 1))
    return [i * spacing for i in range(1, num_injections + 1) if i * spacing < num_real_posts]

def inject_into_timeline(
    real_posts: List[Dict], 
    injectable_posts: List[Dict], 
    strategy: Dict
) -> List[Dict]:
    """
    Inject posts into a timeline according to the specified strategy.
    
    Args:
        real_posts: List of real Mastodon posts, will be sorted by created_at
        injectable_posts: List of posts to inject into the timeline
        strategy: Dictionary specifying injection strategy and parameters:
            - type: Strategy type ('uniform', 'after_n', 'first_only', 'tag_match')
            - max_injections: Maximum number of posts to inject
            - n: Used with 'after_n' strategy to inject after every nth post
            - shuffle_injected: Whether to shuffle the injectable posts
            - inject_only_if_gap_minutes: Minimum time gap required for injection
            
    Returns:
        List of posts with injected posts merged in, ordered by created_at
    
    Note:
        This function has robust error handling to ensure it always returns a valid list
        even if specific operations fail.
    """
    # Input validation to prevent crashes
    if real_posts is None:
        real_posts = []
    if injectable_posts is None:
        injectable_posts = []
    if strategy is None:
        strategy = {"type": "uniform", "max_injections": 3}
    
    # Ensure strategy has a type
    if 'type' not in strategy:
        strategy['type'] = 'uniform'
        
    # Ensure max_injections is present
    if 'max_injections' not in strategy:
        strategy['max_injections'] = min(3, len(injectable_posts))
    # Debug log the inputs
    logger.debug(f"inject_into_timeline called with: {len(real_posts)} real posts, {len(injectable_posts)} injectable posts, strategy={strategy.get('type', 'unknown')}")
    
    # If no injectable posts, just return the real posts (sorted)
    if not injectable_posts:
        logger.debug("No injectable posts provided, returning only real posts")
        return sort_posts_by_timestamp(real_posts)
    
    # Special case: If no real posts or only a stub post and we have injectable posts, 
    # just return the injectable posts as the timeline
    if not real_posts or (len(real_posts) == 1 and real_posts[0].get("stub_for_injection", False)):
        logger.debug("No real posts or only stub post but have injectable posts, returning only injectable posts")
        # Tag all injectable posts
        result = []
        max_to_inject = strategy.get("max_injections", len(injectable_posts))
        logger.debug(f"Adding {max_to_inject} injectable posts directly to timeline")
        
        # Use random selection if shuffle is enabled
        posts_to_inject = injectable_posts
        if strategy.get("shuffle_injected", False):
            posts_to_inject = random.sample(injectable_posts, min(max_to_inject, len(injectable_posts)))
        else:
            posts_to_inject = injectable_posts[:max_to_inject]
        
        # Tag and add the posts
        for post in posts_to_inject:
            tagged_post = tag_as_injected(post)
            result.append(tagged_post)
            logger.debug(f"Added post {post.get('id', 'unknown')} directly to timeline")
        
        return sort_posts_by_timestamp(result)
    
    # Sort real posts (most recent first)
    sorted_real_posts = sort_posts_by_timestamp(real_posts)
    
    # Prepare injectable posts
    available_injections = deepcopy(injectable_posts)
    if strategy.get("shuffle_injected", False):
        random.shuffle(available_injections)
    
    max_injections = strategy.get("max_injections", len(available_injections))
    max_injections = min(max_injections, len(available_injections))
    
    # Setup for injection
    merged_timeline = []
    injection_count = 0
    injection_points = []
    
    # Determine injection points based on strategy
    strategy_type = strategy.get("type", "uniform")
    
    if strategy_type == "uniform":
        injection_points = uniform_injection_points(
            len(sorted_real_posts), 
            max_injections
        )
    
    elif strategy_type == "after_n":
        n = strategy.get("n", 3)
        injection_points = list(range(n-1, len(sorted_real_posts), n))
    
    elif strategy_type == "first_only":
        # Only consider first 10 posts (or fewer if we have fewer)
        max_first = min(10, len(sorted_real_posts))
        injection_points = uniform_injection_points(
            max_first, 
            max_injections
        )
    
    # For tag_match strategy, we'll determine points during timeline construction
    
    # Maintain a pointer to the current injectable post
    injectable_idx = 0
    min_gap_minutes = strategy.get("inject_only_if_gap_minutes", 0)
    
    # Special handling for first_only strategy to ensure injections happen early
    if strategy_type == "first_only":
        # Only use first 10 posts for injection points
        max_first = min(10, len(sorted_real_posts))
        # Force injection points to be within the first 5 positions
        injection_points = list(range(1, max_first // 2 + 1))
        # Limit to max_injections
        injection_points = injection_points[:max_injections]
    
    # Special handling for tag_match strategy
    if strategy_type == "tag_match":
        # Build timeline with tag matching logic
        for i, real_post in enumerate(sorted_real_posts):
            merged_timeline.append(real_post)
            
            # Don't exceed max injections
            if injection_count >= max_injections:
                continue
                
            # Try to find a post with matching tags
            matched_idx = None
            for j, injectable in enumerate(available_injections):
                if has_matching_tags(real_post, injectable):
                    matched_idx = j
                    break
            
            # If we found a match and we're not at the end of the list
            if matched_idx is not None and i < len(sorted_real_posts) - 1:
                next_post = sorted_real_posts[i + 1]
                
                # Check if there's enough gap (if required)
                if min_gap_minutes > 0 and not check_time_gap(real_post, next_post, min_gap_minutes):
                    continue
                
                # Inject the post
                injectable = available_injections.pop(matched_idx)
                
                # Harmonize timestamp and tag as injected
                injectable = harmonize_timestamp(injectable, real_post, next_post)
                injectable = tag_as_injected(injectable)
                
                merged_timeline.append(injectable)
                injection_count += 1
                
                if injectable.get("created_at"):
                    post_id = injectable.get("id", "unknown")
                    logger.debug(
                        f"Injected post {post_id} between 2 real posts with "
                        f"tag match and {min_gap_minutes} min gap"
                    )
    else:
        # For all other strategies, use pre-calculated injection points
        for i, real_post in enumerate(sorted_real_posts):
            merged_timeline.append(real_post)
            
            # If this is an injection point and we haven't hit the limit
            if i in injection_points and injection_count < max_injections and injectable_idx < len(available_injections):
                # Check if we're not at the end of the list
                if i < len(sorted_real_posts) - 1:
                    next_post = sorted_real_posts[i + 1]
                    
                    # Check if there's enough gap (if required)
                    if min_gap_minutes > 0 and not check_time_gap(real_post, next_post, min_gap_minutes):
                        continue
                    
                    # Inject the post
                    injectable = available_injections[injectable_idx]
                    injectable_idx += 1
                    
                    # Harmonize timestamp and tag as injected
                    injectable = harmonize_timestamp(injectable, real_post, next_post)
                    injectable = tag_as_injected(injectable)
                    
                    merged_timeline.append(injectable)
                    injection_count += 1
                    
                    if injectable.get("created_at"):
                        post_id = injectable.get("id", "unknown")
                        before_time = get_post_timestamp(real_post)
                        after_time = get_post_timestamp(next_post)
                        gap_minutes = (before_time - after_time).total_seconds() / 60
                        
                        logger.debug(
                            f"Injected post {post_id} between 2 real posts with "
                            f"{gap_minutes:.1f} min gap"
                        )
    
    # Final sort to ensure chronological order
    return sort_posts_by_timestamp(merged_timeline)