#!/usr/bin/env python3
"""
Demo Content Population Script

Manually triggers the content crawler to populate the database with demo-ready content.
Uses the existing ContentDiscoveryEngine to crawl from multiple Mastodon instances.
"""

import os
import sys
import argparse
import asyncio
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks.content_crawler import ContentDiscoveryEngine
from db.connection import get_db_connection
from utils.privacy import generate_user_alias
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Popular Mastodon instances with diverse content
DEMO_INSTANCES = [
    'mastodon.social',      # General, largest instance
    'fosstodon.org',        # FOSS/tech community  
    'mastodon.world',       # General, diverse content
    'techhub.social',       # Tech-focused
    'mas.to',               # General
    'mstdn.social',         # General
    'toot.cafe',            # Creative/arts community
    'scholar.social'        # Academic community
]

# Popular hashtags for diverse content
DEMO_HASHTAGS = [
    'ai', 'machinelearning', 'technology', 'programming',
    'science', 'art', 'photography', 'music',
    'news', 'politics', 'climate', 'opensource',
    'gamedev', 'design', 'writing', 'books',
    'nature', 'travel', 'food', 'cats'
]

class DemoContentPopulator:
    def __init__(self, target_posts=1000, min_engagement=10):
        self.target_posts = target_posts
        self.min_engagement = min_engagement
        self.session_id = f"demo_populate_{int(datetime.now().timestamp())}"
        self.discovery_engine = ContentDiscoveryEngine(session_id=self.session_id)
        self.crawled_count = 0
        
    async def populate_content(self):
        """Main content population method"""
        logger.info(f"🚀 Starting demo content population")
        logger.info(f"Target: {self.target_posts} posts with min {self.min_engagement} engagement")
        
        # Check current post count
        initial_count = self.get_current_post_count()
        logger.info(f"Current database has {initial_count} posts")
        
        if initial_count >= self.target_posts:
            logger.info(f"✅ Database already has sufficient posts ({initial_count} >= {self.target_posts})")
            return
            
        needed_posts = self.target_posts - initial_count
        logger.info(f"Need to crawl {needed_posts} more posts")
        
        # Strategy 1: Crawl from multiple instance timelines
        await self.crawl_instance_timelines()
        
        # Strategy 2: Crawl popular hashtags
        await self.crawl_hashtag_content()
        
        # Strategy 3: Discover from trending content
        await self.crawl_trending_content()
        
        final_count = self.get_current_post_count()
        added = final_count - initial_count
        logger.info(f"🎉 Demo population complete! Added {added} posts ({initial_count} → {final_count})")
        
    async def crawl_instance_timelines(self):
        """Crawl public timelines from multiple instances"""
        logger.info("📡 Crawling instance public timelines...")
        
        for instance in DEMO_INSTANCES:
            if self.crawled_count >= self.target_posts:
                break
                
            logger.info(f"Crawling {instance}...")
            try:
                # Use discovery engine to crawl instance timeline
                posts_found = await self.discovery_engine.discover_from_timeline(
                    instance_url=f"https://{instance}",
                    timeline_type="public",
                    limit=100  # Get 100 posts per instance
                )
                
                # Filter for high engagement
                high_engagement = [
                    post for post in posts_found 
                    if (post.get('favourites_count', 0) + post.get('reblogs_count', 0)) >= self.min_engagement
                ]
                
                logger.info(f"Found {len(high_engagement)} high-engagement posts from {instance}")
                self.crawled_count += len(high_engagement)
                
                # Short delay between instances
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"Error crawling {instance}: {e}")
                continue
                
    async def crawl_hashtag_content(self):
        """Crawl popular hashtags for diverse content"""
        logger.info("🏷️ Crawling hashtag content...")
        
        for hashtag in DEMO_HASHTAGS:
            if self.crawled_count >= self.target_posts:
                break
                
            logger.info(f"Crawling #{hashtag}...")
            try:
                # Crawl hashtag from mastodon.social (largest instance)
                posts_found = await self.discovery_engine.discover_from_hashtag(
                    hashtag=hashtag,
                    instance_url="https://mastodon.social",
                    limit=50
                )
                
                # Filter for engagement and recency
                recent_cutoff = datetime.now() - timedelta(days=7)
                good_posts = [
                    post for post in posts_found 
                    if (post.get('favourites_count', 0) + post.get('reblogs_count', 0)) >= self.min_engagement
                    and datetime.fromisoformat(post.get('created_at', '').replace('Z', '+00:00')) > recent_cutoff
                ]
                
                logger.info(f"Found {len(good_posts)} quality posts for #{hashtag}")
                self.crawled_count += len(good_posts)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"Error crawling #{hashtag}: {e}")
                continue
                
    async def crawl_trending_content(self):
        """Discover trending content across instances"""
        logger.info("📈 Discovering trending content...")
        
        for instance in DEMO_INSTANCES[:3]:  # Use top 3 instances for trending
            if self.crawled_count >= self.target_posts:
                break
                
            try:
                # Use discovery engine's trending discovery
                trending_posts = await self.discovery_engine.discover_trending_content(
                    instance_url=f"https://{instance}",
                    limit=50
                )
                
                logger.info(f"Found {len(trending_posts)} trending posts from {instance}")
                self.crawled_count += len(trending_posts)
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"Error getting trending from {instance}: {e}")
                continue
                
    def get_current_post_count(self):
        """Get current number of posts in database"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Check if we're using PostgreSQL or SQLite
                    from db.connection import USE_IN_MEMORY_DB
                    
                    if USE_IN_MEMORY_DB:
                        cur.execute("SELECT COUNT(*) FROM posts")
                    else:
                        cur.execute("SELECT COUNT(*) FROM crawled_posts WHERE lifecycle_stage IN ('fresh', 'relevant')")
                    
                    return cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Error counting posts: {e}")
            return 0
            
def main():
    parser = argparse.ArgumentParser(description='Populate database with demo content')
    parser.add_argument('--posts', type=int, default=1000, help='Target number of posts (default: 1000)')
    parser.add_argument('--min-engagement', type=int, default=10, help='Minimum engagement (likes + boosts) (default: 10)')
    parser.add_argument('--fast', action='store_true', help='Fast mode: lower targets for quick testing')
    
    args = parser.parse_args()
    
    if args.fast:
        target_posts = min(args.posts, 100)
        min_engagement = 5
        logger.info("🏃 Fast mode enabled: lower targets for quick testing")
    else:
        target_posts = args.posts
        min_engagement = args.min_engagement
    
    # Create and run the populator
    populator = DemoContentPopulator(target_posts=target_posts, min_engagement=min_engagement)
    
    try:
        asyncio.run(populator.populate_content())
        logger.info("✅ Demo content population completed successfully!")
    except KeyboardInterrupt:
        logger.info("⏹️ Population interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error during population: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 