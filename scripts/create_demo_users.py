#!/usr/bin/env python3
"""
Create demo users for the Corgi Recommender Service demo.

This script creates two example users with different preferences:
1. Alice: A tech-savvy user who likes open source posts
2. Bob: A privacy-focused user who disables all tracking
"""

import sys
import os
import logging
import random
from datetime import datetime, timedelta
import json
import psycopg2
import hashlib

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_CONFIG, USER_HASH_SALT
from db.connection import get_db_connection

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('demo_users')

# Define users
USERS = [
    {
        "user_id": "alice_tech",
        "name": "Alice",
        "description": "Tech-savvy user who likes open source posts",
        "privacy_level": "full",
        "interests": ["linux", "opensource", "programming", "technology", "ai"]
    },
    {
        "user_id": "bob_privacy",
        "name": "Bob",
        "description": "Privacy-focused user who disables all tracking",
        "privacy_level": "none",
        "interests": ["privacy", "security", "encryption", "anonymity", "self-hosting"]
    }
]

# Define sample posts with topics
POSTS = [
    # Tech and open source posts (Alice would like)
    {
        "post_id": "post_tech_1",
        "author_id": "tech_author_1",
        "author_name": "linux_fan_42",
        "content": "Just released a new open source plugin for managing containers! Check it out at github.com/example/container-manager #opensource #linux",
        "language": "en",
        "tags": ["opensource", "linux", "containers"],
        "topics": ["opensource", "linux", "technology"]
    },
    {
        "post_id": "post_tech_2",
        "author_id": "tech_author_2",
        "author_name": "code_wizard",
        "content": "My analysis of how Linux kernel 6.0 improves memory management for enterprise applications. Bookmark for later! #linux #programming",
        "language": "en",
        "tags": ["linux", "programming", "enterprise"],
        "topics": ["linux", "programming", "technology"]
    },
    {
        "post_id": "post_tech_3",
        "author_id": "tech_author_3", 
        "author_name": "ai_researcher",
        "content": "Our team just open-sourced the entire codebase for our latest ML model. Free for non-commercial use! #ai #opensource",
        "language": "en",
        "tags": ["ai", "opensource", "machinelearning"],
        "topics": ["ai", "opensource", "technology"]
    },
    
    # Privacy posts (Bob would like)
    {
        "post_id": "post_privacy_1",
        "author_id": "privacy_author_1",
        "author_name": "privacy_advocate",
        "content": "Guide: Setting up a secure, self-hosted email server that preserves your privacy. No third-party services needed! #privacy #selfhosting",
        "language": "en", 
        "tags": ["privacy", "selfhosting", "security"],
        "topics": ["privacy", "security", "self-hosting"]
    },
    {
        "post_id": "post_privacy_2",
        "author_id": "privacy_author_2",
        "author_name": "encrypt_everything",
        "content": "New tutorial: End-to-end encryption for your personal cloud storage that even the provider can't access. #encryption #privacy",
        "language": "en",
        "tags": ["encryption", "privacy", "security"],
        "topics": ["privacy", "security", "encryption"]
    },
    {
        "post_id": "post_privacy_3",
        "author_id": "privacy_author_3",
        "author_name": "anon_user",
        "content": "Comparing the privacy policies of popular social networks - who's tracking you the most? Results are shocking. #privacy #tracking #anonymity",
        "language": "en",
        "tags": ["privacy", "anonymity", "socialmedia"],
        "topics": ["privacy", "anonymity"]
    },
    
    # Neutral posts
    {
        "post_id": "post_neutral_1",
        "author_id": "neutral_author_1",
        "author_name": "news_reporter",
        "content": "Weather forecast for the weekend: Sunny with a chance of clouds. Perfect for outdoor activities! #weather #weekend",
        "language": "en",
        "tags": ["weather", "weekend", "forecast"],
        "topics": ["weather", "general"]
    },
    {
        "post_id": "post_neutral_2",
        "author_id": "neutral_author_2",
        "author_name": "food_lover",
        "content": "My homemade pizza recipe! The secret is in the dough fermentation. #food #recipe #pizza",
        "language": "en",
        "tags": ["food", "recipe", "pizza"],
        "topics": ["food", "general"]
    }
]

def generate_user_alias(user_id):
    """Generate a pseudonym for a user to preserve privacy."""
    salt = USER_HASH_SALT.encode('utf-8')
    user_bytes = user_id.encode('utf-8')
    
    # Create a salted hash
    hash_obj = hashlib.sha256(salt + user_bytes)
    # Use the first 16 characters of the hash
    return f"user_{hash_obj.hexdigest()[:16]}"

def create_mastodon_post(post):
    """Create a Mastodon-compatible post object."""
    return {
        "id": post["post_id"],
        "content": f"<p>{post['content']}</p>",
        "created_at": datetime.now().isoformat(),
        "language": post["language"],
        "account": {
            "id": post["author_id"],
            "username": post["author_name"],
            "display_name": post["author_name"].replace('_', ' ').title(),
            "followers_count": random.randint(50, 5000),
            "following_count": random.randint(50, 1000),
            "statuses_count": random.randint(100, 5000),
            "url": f"https://mastodon.example.com/@{post['author_name']}"
        },
        "replies_count": random.randint(0, 10),
        "reblogs_count": random.randint(0, 20),
        "favourites_count": random.randint(0, 30),
        "url": f"https://mastodon.example.com/@{post['author_name']}/posts/{post['post_id']}",
        "is_real_mastodon_post": False,
        "is_synthetic": True
    }

def create_users_and_posts():
    """Create users, posts, and interactions in the database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Create users with privacy settings
                for user in USERS:
                    user_id = user["user_id"]
                    user_alias = generate_user_alias(user_id)
                    privacy_level = user["privacy_level"]
                    
                    # Add user privacy settings
                    cur.execute(
                        """
                        INSERT INTO privacy_settings (user_id, tracking_level)
                        VALUES (%s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET tracking_level = EXCLUDED.tracking_level
                        """,
                        (user_id, privacy_level)
                    )
                    
                    logger.info(f"Created/updated user {user['name']} (ID: {user_id}) with privacy level: {privacy_level}")
                
                # Create posts
                for post in POSTS:
                    # Convert to Mastodon-compatible format
                    mastodon_post = create_mastodon_post(post)
                    
                    # Create interaction counts
                    interaction_counts = {
                        "favorites": mastodon_post["favourites_count"],
                        "reblogs": mastodon_post["reblogs_count"],
                        "replies": mastodon_post["replies_count"]
                    }
                    
                    # Insert post metadata
                    cur.execute(
                        """
                        INSERT INTO post_metadata 
                        (post_id, author_id, author_name, content, language, tags, sensitive, mastodon_post, interaction_counts)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (post_id) DO UPDATE SET 
                            mastodon_post = EXCLUDED.mastodon_post,
                            interaction_counts = EXCLUDED.interaction_counts
                        """,
                        (
                            post["post_id"],
                            post["author_id"],
                            post["author_name"],
                            post["content"],
                            post["language"],
                            post["tags"],
                            False,  # not sensitive
                            json.dumps(mastodon_post),
                            json.dumps(interaction_counts)
                        )
                    )
                    
                    logger.info(f"Created/updated post {post['post_id']}")
                
                # Create interactions for Alice (who has full tracking enabled)
                alice = USERS[0]
                alice_id = alice["user_id"]
                alice_alias = generate_user_alias(alice_id)
                alice_interests = set(alice["interests"])
                
                # Alice interacts with posts that match her interests
                for post in POSTS:
                    post_topics = set(post.get("topics", []))
                    
                    # If there's overlap in interests and post topics
                    if alice_interests.intersection(post_topics):
                        # Determine interaction type based on overlap
                        overlap = len(alice_interests.intersection(post_topics))
                        
                        # Strong overlap = favorite and bookmark
                        if overlap >= 2:
                            actions = ["favorite", "bookmark"]
                        # Weak overlap = just favorite
                        else:
                            actions = ["favorite"]
                        
                        # Create interactions
                        for action in actions:
                            context = {
                                "source": "timeline_home",
                                "timestamp": (datetime.now() - timedelta(days=random.randint(1, 5))).isoformat()
                            }
                            
                            cur.execute(
                                """
                                INSERT INTO interactions 
                                (user_alias, post_id, action_type, context)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (user_alias, post_id, action_type) 
                                DO UPDATE SET context = EXCLUDED.context
                                """,
                                (alice_alias, post["post_id"], action, json.dumps(context))
                            )
                            
                            logger.info(f"Created/updated interaction: {alice_id} {action} {post['post_id']}")
                
                # Generate rankings for Alice
                cur.execute(
                    """
                    INSERT INTO rankings (user_id, rankings, created_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        rankings = EXCLUDED.rankings,
                        created_at = EXCLUDED.created_at
                    """,
                    (
                        alice_id,
                        json.dumps([
                            {"post_id": post["post_id"], "score": 0.9 if set(post.get("topics", [])).intersection(alice_interests) else 0.1}
                            for post in POSTS
                        ]),
                        datetime.now().isoformat()
                    )
                )
                
                logger.info(f"Generated rankings for {alice_id}")
                
                # Bob has no interactions because he has privacy level "none"
                
                # Commit all changes
                conn.commit()
                logger.info("Successfully created demo users, posts, and interactions")
    
    except Exception as e:
        logger.error(f"Error creating demo data: {e}")
        raise

if __name__ == "__main__":
    try:
        # First, check that we can connect to the database
        logger.info("Testing database connection...")
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                logger.info("Database connection successful")
        
        # Create users, posts, and interactions
        create_users_and_posts()
        logger.info("Demo setup complete!")
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)