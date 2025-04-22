"""
Example usage of the timeline injector module.

This script demonstrates how to use the timeline injector to merge
real posts with injectable posts using different strategies.
"""

import json
import logging
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path so we can import the utils module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.timeline_injector import inject_into_timeline

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_posts():
    """Create sample posts for demonstration."""
    now = datetime.now()
    
    # Create 10 real posts with descending timestamps (most recent first)
    real_posts = []
    for i in range(10):
        created_at = now - timedelta(minutes=i*15)
        tags = []
        if i % 3 == 0:
            tags = [{"name": "tech"}, {"name": "programming"}]
        elif i % 3 == 1:
            tags = [{"name": "news"}, {"name": "politics"}]
        else:
            tags = [{"name": "general"}]
            
        real_posts.append({
            "id": f"real_{i}",
            "created_at": created_at.isoformat() + "Z",
            "content": f"This is real post {i} about {'tech' if i % 3 == 0 else 'news' if i % 3 == 1 else 'general topics'}",
            "tags": tags,
            "account": {
                "id": "user123",
                "username": "testuser",
                "display_name": "Test User"
            }
        })
    
    # Create 5 injectable posts
    injectable_posts = []
    for i in range(5):
        tags = []
        if i % 2 == 0:
            tags = [{"name": "tech"}, {"name": "ai"}]
        else:
            tags = [{"name": "news"}, {"name": "trending"}]
            
        injectable_posts.append({
            "id": f"inject_{i}",
            "created_at": (now - timedelta(hours=24)).isoformat() + "Z",  # Old timestamp that will be replaced
            "content": f"This is injectable post {i} about {'AI and tech' if i % 2 == 0 else 'trending news'}",
            "tags": tags,
            "account": {
                "id": "injected_account",
                "username": "recommender",
                "display_name": "Recommended Content"
            },
            "is_synthetic": True,
            "category": "recommendation"
        })
    
    return real_posts, injectable_posts

def print_timeline(timeline, name="Timeline"):
    """Print a timeline in a readable format."""
    print(f"\n{name} ({len(timeline)} posts):")
    print("-" * 50)
    
    for i, post in enumerate(timeline):
        created_at = post["created_at"]
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat() + "Z"
            
        is_injected = post.get("injected", False)
        post_type = "INJECTED" if is_injected else "REAL"
        
        tag_str = ", ".join([tag["name"] for tag in post.get("tags", [])])
        
        print(f"{i+1}. [{post_type}] ID: {post['id']}")
        print(f"   Time: {created_at}")
        print(f"   Tags: {tag_str}")
        print(f"   Content: {post['content'][:50]}...")
        print()

def main():
    """Run various injection strategies on sample data."""
    real_posts, injectable_posts = create_sample_posts()
    
    # Print the original posts
    print_timeline(real_posts, "Original Real Posts")
    print_timeline(injectable_posts, "Injectable Posts")
    
    # Strategy 1: Uniform distribution
    strategy_uniform = {
        "type": "uniform",
        "max_injections": 3,
        "shuffle_injected": True
    }
    
    timeline_uniform = inject_into_timeline(real_posts, injectable_posts, strategy_uniform)
    print_timeline(timeline_uniform, "Uniform Strategy Timeline")
    
    # Strategy 2: After N posts
    strategy_after_n = {
        "type": "after_n",
        "n": 2,
        "max_injections": 4
    }
    
    timeline_after_n = inject_into_timeline(real_posts, injectable_posts, strategy_after_n)
    print_timeline(timeline_after_n, "After N Strategy Timeline")
    
    # Strategy 3: First only
    strategy_first_only = {
        "type": "first_only",
        "max_injections": 2
    }
    
    timeline_first_only = inject_into_timeline(real_posts, injectable_posts, strategy_first_only)
    print_timeline(timeline_first_only, "First Only Strategy Timeline")
    
    # Strategy 4: Tag matching
    strategy_tag_match = {
        "type": "tag_match",
        "max_injections": 3
    }
    
    timeline_tag_match = inject_into_timeline(real_posts, injectable_posts, strategy_tag_match)
    print_timeline(timeline_tag_match, "Tag Match Strategy Timeline")
    
    # Strategy 5: With time gap requirement
    strategy_with_gap = {
        "type": "uniform",
        "max_injections": 3,
        "inject_only_if_gap_minutes": 20
    }
    
    timeline_with_gap = inject_into_timeline(real_posts, injectable_posts, strategy_with_gap)
    print_timeline(timeline_with_gap, "With Gap Requirement Timeline")

if __name__ == "__main__":
    main()