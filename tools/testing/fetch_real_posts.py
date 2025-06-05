#!/usr/bin/env python3
"""
Script to fetch real posts from Mastodon public timeline and save them for cold start.
"""

import os
import json
import time
import random
import requests
import logging
from datetime import datetime
from urllib.parse import quote_plus

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("fetch_posts")

# Define file paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "data", "cold_start_posts.json")

# Define popular Mastodon instances to fetch from
INSTANCES = [
    "mastodon.social",
    "mastodon.online",
    "hachyderm.io",
    "techhub.social",
    "mstdn.social",
    "fosstodon.org",
]

# Tags to look for to ensure diverse content
TOPIC_TAGS = [
    "technology",
    "tech",
    "programming",
    "coding",
    "developer",
    "art",
    "photography",
    "design",
    "illustration",
    "creative",
    "science",
    "space",
    "research",
    "nature",
    "climate",
    "books",
    "reading",
    "writing",
    "literature",
    "publishing",
    "music",
    "movies",
    "film",
    "tv",
    "entertainment",
    "gaming",
    "games",
    "videogames",
    "boardgames",
    "rpg",
    "food",
    "cooking",
    "baking",
    "recipe",
    "cuisine",
    "health",
    "fitness",
    "wellness",
    "mentalhealth",
    "running",
    "history",
    "philosophy",
    "politics",
    "economics",
    "culture",
    "travel",
    "adventure",
    "outdoors",
    "hiking",
    "backpacking",
]


def fetch_public_timeline(instance, max_id=None, limit=40):
    """Fetch posts from a Mastodon instance's public timeline."""
    base_url = f"https://{instance}/api/v1/timelines/public"

    params = {
        "limit": limit,
    }

    if max_id:
        params["max_id"] = max_id

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching timeline from {instance}: {e}")
        return []


def fetch_trending_tags(instance):
    """Fetch trending tags from a Mastodon instance."""
    base_url = f"https://{instance}/api/v1/trends/tags"

    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching trending tags from {instance}: {e}")
        return []


def fetch_tag_timeline(instance, tag, limit=20):
    """Fetch posts for a specific tag."""
    encoded_tag = quote_plus(tag)
    base_url = f"https://{instance}/api/v1/timelines/tag/{encoded_tag}"

    params = {
        "limit": limit,
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching tag timeline from {instance}: {e}")
        return []


def convert_post_to_cold_start_format(post, source_instance):
    """Convert a Mastodon post to the cold start format we use."""
    # Extract basic post information
    post_id = f"real_{post['id']}"
    content = post["content"]
    created_at = post["created_at"]
    language = post.get("language", "en")

    # Extract account information
    account = {
        "id": post["account"].get("id", "unknown"),
        "username": post["account"].get("username", "unknown"),
        "display_name": post["account"].get(
            "display_name", post["account"].get("username", "Unknown User")
        ),
        "url": post["account"].get(
            "url",
            f"https://{source_instance}/@{post['account'].get('username', 'unknown')}",
        ),
        "avatar": post["account"].get(
            "avatar", "https://mastodon.social/avatars/original/missing.png"
        ),
        "avatar_static": post["account"].get(
            "avatar_static",
            post["account"].get(
                "avatar", "https://mastodon.social/avatars/original/missing.png"
            ),
        ),
        "header": post["account"].get(
            "header", "https://mastodon.social/headers/original/missing.png"
        ),
        "header_static": post["account"].get(
            "header_static",
            post["account"].get(
                "header", "https://mastodon.social/headers/original/missing.png"
            ),
        ),
        "note": post["account"].get("note", ""),
        "followers_count": post["account"].get("followers_count", 0),
        "following_count": post["account"].get("following_count", 0),
        "statuses_count": post["account"].get("statuses_count", 0),
    }

    # Extract media attachments if any
    media_attachments = post.get("media_attachments", [])

    # Extract tags
    tags = [tag["name"] for tag in post.get("tags", [])]

    # Guess category based on tags
    category = "general"
    for tag in tags:
        tag_lower = tag.lower()
        if any(
            topic in tag_lower
            for topic in ["tech", "code", "program", "develop", "software"]
        ):
            category = "technology"
            break
        elif any(
            topic in tag_lower
            for topic in ["art", "photo", "design", "creative", "illustration"]
        ):
            category = "art"
            break
        elif any(
            topic in tag_lower for topic in ["science", "space", "research", "nature"]
        ):
            category = "science"
            break
        elif any(
            topic in tag_lower for topic in ["book", "read", "write", "literature"]
        ):
            category = "books"
            break
        elif any(
            topic in tag_lower
            for topic in ["music", "movie", "film", "tv", "entertainment"]
        ):
            category = "entertainment"
            break
        elif any(topic in tag_lower for topic in ["game", "gaming", "video"]):
            category = "gaming"
            break
        elif any(topic in tag_lower for topic in ["food", "cook", "bake", "recipe"]):
            category = "food"
            break
        elif any(
            topic in tag_lower for topic in ["health", "fitness", "wellness", "mental"]
        ):
            category = "health"
            break

    # Create the cold start post format
    cold_start_post = {
        "id": post_id,
        "content": content,
        "created_at": created_at,
        "account": account,
        "language": language,
        "favourites_count": post.get("favourites_count", 0),
        "reblogs_count": post.get("reblogs_count", 0),
        "replies_count": post.get("replies_count", 0),
        "tags": tags,
        "category": category,
        "source_instance": source_instance,
        "is_real_mastodon_post": True,
        "url": post.get("url", ""),
        "uri": post.get("uri", post.get("url", "")),
        "mentions": post.get("mentions", []),
        "sensitive": post.get("sensitive", False),
        "visibility": post.get("visibility", "public"),
        "card": post.get("card", None),
    }

    # Add media information if present
    if media_attachments:
        # Keep the full media attachments structure for compatibility with Mastodon clients
        cold_start_post["media_attachments"] = media_attachments

        # For backward compatibility, also provide the simple media_urls array
        media_urls = []
        for media in media_attachments:
            if media.get("preview_url"):
                media_urls.append(media.get("preview_url"))
            elif media.get("url"):
                media_urls.append(media.get("url"))

        if media_urls:
            cold_start_post["media_urls"] = media_urls

    return cold_start_post


def filter_posts(posts):
    """Filter posts for quality and suitability."""
    filtered_posts = []

    for post in posts:
        # Skip posts with no content
        if not post.get("content"):
            continue

        # Skip posts with few interactions
        if post.get("favourites_count", 0) < 5 and post.get("reblogs_count", 0) < 2:
            continue

        # Skip posts from suspended accounts
        if post.get("account", {}).get("suspended", False):
            continue

        # Skip posts with sensitive content
        if post.get("sensitive", False):
            continue

        filtered_posts.append(post)

    return filtered_posts


def fetch_diverse_posts(count=100):
    """Fetch a diverse set of posts from various instances and topics."""
    all_posts = []

    # Step 1: Fetch from public timelines of different instances
    for instance in INSTANCES:
        logger.info(f"Fetching public timeline from {instance}")
        posts = fetch_public_timeline(instance, limit=40)
        filtered_posts = filter_posts(posts)

        # Convert posts to our format
        for post in filtered_posts[:10]:  # Limit to top 10 per instance
            all_posts.append(convert_post_to_cold_start_format(post, instance))

        # Respect rate limits
        time.sleep(2)

    # Step 2: Fetch trending tags from instances
    trending_tags = []
    for instance in INSTANCES[:2]:  # Just use a couple of instances for trends
        logger.info(f"Fetching trending tags from {instance}")
        tags = fetch_trending_tags(instance)
        for tag in tags[:5]:  # Top 5 trending tags
            if tag.get("name"):
                trending_tags.append(tag.get("name"))

        # Respect rate limits
        time.sleep(2)

    # Ensure we have a diverse set by adding some known topics
    if len(trending_tags) < 10:
        trending_tags.extend(random.sample(TOPIC_TAGS, 10 - len(trending_tags)))

    # Step 3: Fetch posts for trending and diverse tags
    for tag in set(trending_tags):  # Use set to remove duplicates
        instance = random.choice(INSTANCES)
        logger.info(f"Fetching tag '{tag}' timeline from {instance}")
        posts = fetch_tag_timeline(instance, tag, limit=20)
        filtered_posts = filter_posts(posts)

        # Convert posts to our format
        for post in filtered_posts[:5]:  # Limit to top 5 per tag
            all_posts.append(convert_post_to_cold_start_format(post, instance))

        # Respect rate limits
        time.sleep(2)

        # Break if we have enough posts
        if len(all_posts) >= count:
            break

    # Deduplicate posts by ID
    unique_posts = {}
    for post in all_posts:
        if post["id"] not in unique_posts:
            unique_posts[post["id"]] = post

    # Convert back to list
    final_posts = list(unique_posts.values())

    # Sort posts by favorites and reblogs (best first)
    final_posts.sort(
        key=lambda x: (x.get("favourites_count", 0) + x.get("reblogs_count", 0) * 2),
        reverse=True,
    )

    # Limit to requested count
    return final_posts[:count]


def save_posts_to_file(posts, output_file):
    """Save posts to a JSON file."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(posts)} posts to {output_file}")


def main():
    logger.info("Starting fetch of real Mastodon posts")

    # Fetch posts
    posts = fetch_diverse_posts(count=50)
    logger.info(f"Fetched {len(posts)} diverse posts")

    # Create a backup of the existing file if it exists
    if os.path.exists(OUTPUT_FILE):
        backup_file = f"{OUTPUT_FILE}.bak.{int(time.time())}"
        logger.info(f"Creating backup of existing file: {backup_file}")
        os.rename(OUTPUT_FILE, backup_file)

    # Save posts to file
    save_posts_to_file(posts, OUTPUT_FILE)

    logger.info("Fetch and save completed successfully")


if __name__ == "__main__":
    main()
