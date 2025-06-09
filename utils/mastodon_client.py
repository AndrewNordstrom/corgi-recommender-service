#!/usr/bin/env python3
"""
Mastodon API Client Utility for Active Content Crawling

Provides a simple, rate-limit aware client for accessing Mastodon instance APIs
to crawl public timelines and trending content.

Features:
- Multi-instance support
- Rate limiting compliance
- Error handling and retries
- Public timeline access
- Trending hashtags and posts
"""

import requests
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class MastodonPost:
    """Represents a Mastodon post with relevant fields for crawling."""
    id: str
    content: str
    created_at: datetime
    author_id: str
    author_username: str
    favourites_count: int
    reblogs_count: int
    replies_count: int
    language: Optional[str] = None
    tags: List[str] = None
    url: str = ""
    # Rich content fields
    media_attachments: List[Dict[str, Any]] = None
    card: Optional[Dict[str, Any]] = None
    poll: Optional[Dict[str, Any]] = None
    mentions: List[Dict[str, Any]] = None
    emojis: List[Dict[str, Any]] = None
    visibility: str = "public"
    in_reply_to_id: Optional[str] = None
    in_reply_to_account_id: Optional[str] = None
    # Author details
    author_acct: Optional[str] = None
    author_display_name: Optional[str] = None
    author_avatar: Optional[str] = None
    author_note: Optional[str] = None
    author_followers_count: int = 0
    author_following_count: int = 0
    author_statuses_count: int = 0

@dataclass
class MastodonProfile:
    """Represents a Mastodon user profile with opt-out information."""
    id: str
    username: str
    acct: str  # Full acct (username@instance.domain or just username for local)
    display_name: str
    note: str  # Profile bio/description
    fields: List[Dict[str, str]]  # Profile metadata fields
    bot: bool
    locked: bool
    url: str
    avatar: str = ""
    header: str = ""
    followers_count: int = 0
    following_count: int = 0
    statuses_count: int = 0

class OptOutStatus:
    """Represents a user's opt-out status with caching information."""
    
    def __init__(self, user_acct: str, opted_out: bool, 
                 checked_at: datetime = None, opt_out_tags_found: List[str] = None):
        self.user_acct = user_acct
        self.opted_out = opted_out
        self.checked_at = checked_at or datetime.now(timezone.utc)
        self.opt_out_tags_found = opt_out_tags_found or []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for caching."""
        return {
            'user_acct': self.user_acct,
            'opted_out': self.opted_out,
            'checked_at': self.checked_at.isoformat(),
            'opt_out_tags_found': self.opt_out_tags_found
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OptOutStatus':
        """Create from dictionary (for cache loading)."""
        return cls(
            user_acct=data['user_acct'],
            opted_out=data['opted_out'],
            checked_at=datetime.fromisoformat(data['checked_at']),
            opt_out_tags_found=data.get('opt_out_tags_found', [])
        )

class MastodonAPIClient:
    """
    Simple Mastodon API client for public timeline crawling.
    
    This client respects rate limits and handles common errors gracefully.
    Only accesses public endpoints - no authentication required.
    """
    
    def __init__(self, instance_url: str):
        """
        Initialize client for a specific Mastodon instance.
        
        Args:
            instance_url: The base URL of the Mastodon instance (e.g., "https://mastodon.social")
        """
        self.instance_url = instance_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Corgi-Recommender-Crawler/1.0',
            'Accept': 'application/json'
        })
        self.rate_limit_remaining = 300  # Default Mastodon rate limit
        self.rate_limit_reset = time.time()
        self.last_response_headers = {}  # Track last response headers
        
        logger.debug(f"Initialized Mastodon client for {self.instance_url}")

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Make a request to the Mastodon API with rate limiting.
        
        Args:
            endpoint: API endpoint (e.g., "/api/v1/timelines/public")
            params: Query parameters
            
        Returns:
            JSON response data or None if failed
        """
        url = f"{self.instance_url}{endpoint}"
        
        # Check rate limit
        if self.rate_limit_remaining <= 1 and time.time() < self.rate_limit_reset:
            sleep_time = self.rate_limit_reset - time.time() + 1
            logger.warning(f"Rate limit reached for {self.instance_url}, sleeping for {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        try:
            response = self.session.get(url, params=params or {}, timeout=10)
            
            # Update rate limit info from headers
            if 'X-RateLimit-Remaining' in response.headers:
                try:
                    self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
                except (ValueError, TypeError):
                    logger.debug(f"Could not parse rate limit remaining: {response.headers['X-RateLimit-Remaining']}")
                    
            if 'X-RateLimit-Reset' in response.headers:
                try:
                    # Try parsing as Unix timestamp first
                    self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
                except (ValueError, TypeError):
                    # If that fails, try parsing as ISO format and convert to timestamp
                    try:
                        reset_dt = datetime.fromisoformat(response.headers['X-RateLimit-Reset'].replace('Z', '+00:00'))
                        self.rate_limit_reset = reset_dt.timestamp()
                    except (ValueError, TypeError):
                        logger.debug(f"Could not parse rate limit reset: {response.headers['X-RateLimit-Reset']}")
                        # Default to 15 minutes from now
                        self.rate_limit_reset = time.time() + 900
            
            response.raise_for_status()
            self.last_response_headers = dict(response.headers)  # Store headers
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {url}: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid JSON response from {url}: {e}")
            return None

    def get_timeline(self, timeline_type: str = "public", limit: int = 40, local: bool = False) -> List[MastodonPost]:
        """
        Fetch posts from a timeline (alias for get_public_timeline for compatibility).
        
        Args:
            timeline_type: Type of timeline (currently only "public" supported)
            limit: Number of posts to fetch (max 40)
            local: If True, fetch only local posts; if False, fetch federated timeline
            
        Returns:
            List of MastodonPost objects
        """
        return self.get_public_timeline(limit=limit, local=local)

    def get_public_timeline(self, limit: int = 40, local: bool = False) -> List[MastodonPost]:
        """
        Fetch posts from the public timeline.
        
        Args:
            limit: Number of posts to fetch (max 40)
            local: If True, fetch only local posts; if False, fetch federated timeline
            
        Returns:
            List of MastodonPost objects
        """
        endpoint = "/api/v1/timelines/public"
        params = {
            'limit': min(limit, 40),  # Mastodon API limit
            'local': 'true' if local else 'false'
        }
        
        logger.debug(f"Fetching public timeline from {self.instance_url} (limit={limit}, local={local})")
        
        data = self._make_request(endpoint, params)
        if not data:
            return []
        
        posts = []
        for post_data in data:
            try:
                post = self._parse_post(post_data)
                if post:
                    posts.append(post)
            except Exception as e:
                logger.warning(f"Failed to parse post {post_data.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Fetched {len(posts)} posts from {self.instance_url}")
        return posts

    def get_trending_hashtags(self, limit: int = 20) -> List[Dict]:
        """
        Fetch trending hashtags from the instance.
        
        Args:
            limit: Number of hashtags to fetch
            
        Returns:
            List of hashtag data dictionaries
        """
        endpoint = "/api/v1/trends/tags"
        params = {'limit': limit}
        
        data = self._make_request(endpoint, params)
        return data or []

    def get_hashtag_timeline(self, hashtag: str, limit: int = 20) -> List[MastodonPost]:
        """
        Fetch posts from a specific hashtag timeline.
        
        Args:
            hashtag: Hashtag name (without #)
            limit: Number of posts to fetch
            
        Returns:
            List of MastodonPost objects
        """
        endpoint = f"/api/v1/timelines/tag/{hashtag}"
        params = {'limit': min(limit, 40)}  # Mastodon API limit
        
        logger.debug(f"Fetching hashtag timeline #{hashtag} from {self.instance_url} (limit={limit})")
        
        data = self._make_request(endpoint, params)
        if not data:
            return []
        
        posts = []
        for post_data in data:
            try:
                post = self._parse_post(post_data)
                if post:
                    posts.append(post)
            except Exception as e:
                logger.warning(f"Failed to parse hashtag post {post_data.get('id', 'unknown')}: {e}")
                continue
        
        logger.debug(f"Fetched {len(posts)} posts from #{hashtag} on {self.instance_url}")
        return posts

    def get_account_statuses(self, account_id: str, limit: int = 20) -> List[MastodonPost]:
        """
        Fetch recent posts from a specific account.
        
        Args:
            account_id: Account ID to fetch posts from
            limit: Number of posts to fetch
            
        Returns:
            List of MastodonPost objects
        """
        endpoint = f"/api/v1/accounts/{account_id}/statuses"
        params = {
            'limit': min(limit, 40),  # Mastodon API limit
            'exclude_replies': 'true',  # Focus on original content
            'exclude_reblogs': 'true'   # Focus on original content
        }
        
        logger.debug(f"Fetching account statuses for {account_id} from {self.instance_url} (limit={limit})")
        
        data = self._make_request(endpoint, params)
        if not data:
            return []
        
        posts = []
        for post_data in data:
            try:
                post = self._parse_post(post_data)
                if post:
                    posts.append(post)
            except Exception as e:
                logger.warning(f"Failed to parse account post {post_data.get('id', 'unknown')}: {e}")
                continue
        
        logger.debug(f"Fetched {len(posts)} posts from account {account_id} on {self.instance_url}")
        return posts

    def get_account_by_username(self, username: str) -> Optional[MastodonProfile]:
        """
        Fetch account profile information by username.
        
        Args:
            username: Username to look up (without @ prefix)
            
        Returns:
            MastodonProfile object or None if not found/error
        """
        # Try to lookup the account
        endpoint = "/api/v1/accounts/lookup"
        params = {'acct': username}
        
        logger.debug(f"Looking up account @{username} on {self.instance_url}")
        
        data = self._make_request(endpoint, params)
        if not data:
            return None
        
        return self._parse_profile(data)

    def get_account_by_id(self, account_id: str) -> Optional[MastodonProfile]:
        """
        Fetch account profile information by account ID.
        
        Args:
            account_id: Account ID to fetch
            
        Returns:
            MastodonProfile object or None if not found/error
        """
        endpoint = f"/api/v1/accounts/{account_id}"
        
        logger.debug(f"Fetching account profile for ID {account_id} on {self.instance_url}")
        
        data = self._make_request(endpoint)
        if not data:
            return None
        
        return self._parse_profile(data)

    def check_user_opt_out(self, user_acct: str, opt_out_tags: List[str]) -> OptOutStatus:
        """
        Check if a user has opted out of content crawling based on their profile.
        
        This method fetches the user's profile and checks their bio and metadata
        fields for any of the recognized opt-out tags.
        
        Args:
            user_acct: Full user account (username@instance or just username)
            opt_out_tags: List of opt-out tags to check for (case-insensitive)
            
        Returns:
            OptOutStatus object with the user's opt-out preference
        """
        logger.debug(f"Checking opt-out status for {user_acct}")
        
        # Extract username from acct (remove @ prefix if present)
        username = user_acct.lstrip('@').split('@')[0]
        
        try:
            # Fetch the user's profile
            profile = self.get_account_by_username(username)
            if not profile:
                logger.warning(f"Could not fetch profile for {user_acct}, assuming not opted out")
                return OptOutStatus(user_acct, opted_out=False)
            
            # Check for opt-out tags in profile
            opt_out_tags_found = self._find_opt_out_tags(profile, opt_out_tags)
            
            opted_out = len(opt_out_tags_found) > 0
            
            if opted_out:
                logger.info(f"User {user_acct} has opted out - found tags: {opt_out_tags_found}")
            else:
                logger.debug(f"User {user_acct} has not opted out")
            
            return OptOutStatus(
                user_acct=user_acct,
                opted_out=opted_out,
                opt_out_tags_found=opt_out_tags_found
            )
            
        except Exception as e:
            logger.error(f"Error checking opt-out status for {user_acct}: {e}")
            # In case of error, assume not opted out to avoid false blocking
            return OptOutStatus(user_acct, opted_out=False)

    def _find_opt_out_tags(self, profile: MastodonProfile, opt_out_tags: List[str]) -> List[str]:
        """
        Find opt-out tags in a user's profile.
        
        Args:
            profile: User's profile data
            opt_out_tags: List of opt-out tags to search for
            
        Returns:
            List of found opt-out tags
        """
        found_tags = []
        
        # Normalize opt-out tags to lowercase for case-insensitive matching
        normalized_opt_out_tags = [tag.lower().lstrip('#') for tag in opt_out_tags]
        
        # Text to search through
        search_texts = [
            profile.note or "",  # Profile bio
            profile.display_name or "",  # Display name
        ]
        
        # Add metadata fields (name-value pairs)
        for field in profile.fields:
            search_texts.append(field.get('name', ''))
            search_texts.append(field.get('value', ''))
        
        # Search through all text fields
        for text in search_texts:
            if not text:
                continue
                
            # Remove HTML tags for cleaner matching
            clean_text = re.sub(r'<[^>]+>', '', text).lower()
            
            # Check for each opt-out tag
            for opt_out_tag in normalized_opt_out_tags:
                # Check with and without # prefix
                patterns = [
                    f"#{opt_out_tag}",  # With hashtag
                    opt_out_tag,  # Without hashtag
                    f" {opt_out_tag} ",  # Word boundary
                    f"#{opt_out_tag}\\b",  # Word boundary with hashtag
                ]
                
                for pattern in patterns:
                    if re.search(pattern, clean_text):
                        # Add back the # prefix for consistency
                        tag_with_hash = f"#{opt_out_tag}" if not opt_out_tag.startswith('#') else opt_out_tag
                        if tag_with_hash not in found_tags:
                            found_tags.append(tag_with_hash)
                        break
        
        return found_tags

    def _parse_profile(self, profile_data: Dict) -> Optional[MastodonProfile]:
        """
        Parse raw profile data from Mastodon API into MastodonProfile object.
        
        Args:
            profile_data: Raw profile data from API
            
        Returns:
            MastodonProfile object or None if parsing failed
        """
        try:
            # Parse metadata fields
            fields = []
            if 'fields' in profile_data:
                for field in profile_data['fields']:
                    if isinstance(field, dict):
                        fields.append({
                            'name': field.get('name', ''),
                            'value': field.get('value', ''),
                            'verified_at': field.get('verified_at')
                        })
            
            profile = MastodonProfile(
                id=profile_data.get('id', ''),
                username=profile_data.get('username', ''),
                acct=profile_data.get('acct', ''),
                display_name=profile_data.get('display_name', ''),
                note=profile_data.get('note', ''),  # This is the bio/description
                fields=fields,
                bot=profile_data.get('bot', False),
                locked=profile_data.get('locked', False),
                url=profile_data.get('url', ''),
                avatar=profile_data.get('avatar', ''),
                header=profile_data.get('header', ''),
                followers_count=int(profile_data.get('followers_count', 0)),
                following_count=int(profile_data.get('following_count', 0)),
                statuses_count=int(profile_data.get('statuses_count', 0))
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Error parsing profile data: {e}")
            return None

    def _parse_post(self, post_data: Dict) -> Optional[MastodonPost]:
        """
        Parse raw post data from Mastodon API into MastodonPost object.
        
        Args:
            post_data: Raw post data from API
            
        Returns:
            MastodonPost object or None if parsing failed
        """
        try:
            # Skip reblogs/boosts - we want original content
            if post_data.get('reblog'):
                return None
            
            # Parse creation time
            created_at_str = post_data.get('created_at', '')
            try:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                logger.warning(f"Invalid created_at format: {created_at_str}")
                created_at = datetime.now(timezone.utc)
            
            # Extract hashtags
            tags = []
            if 'tags' in post_data:
                tags = [tag['name'] for tag in post_data['tags'] if isinstance(tag, dict)]
            
            # Get account info
            account = post_data.get('account', {})
            
            # Extract rich content
            media_attachments = post_data.get('media_attachments', [])
            card = post_data.get('card', None)
            poll = post_data.get('poll', None)
            mentions = post_data.get('mentions', [])
            emojis = post_data.get('emojis', [])
            
            post = MastodonPost(
                id=post_data.get('id', ''),
                content=post_data.get('content', ''),
                created_at=created_at,
                author_id=account.get('id', ''),
                author_username=account.get('username', ''),
                favourites_count=int(post_data.get('favourites_count', 0)),
                reblogs_count=int(post_data.get('reblogs_count', 0)),
                replies_count=int(post_data.get('replies_count', 0)),
                language=post_data.get('language'),
                tags=tags,
                url=post_data.get('url', ''),
                # Rich content fields
                media_attachments=media_attachments,
                card=card,
                poll=poll,
                mentions=mentions,
                emojis=emojis,
                visibility=post_data.get('visibility', 'public'),
                in_reply_to_id=post_data.get('in_reply_to_id'),
                in_reply_to_account_id=post_data.get('in_reply_to_account_id'),
                # Author details
                author_acct=account.get('acct', ''),
                author_display_name=account.get('display_name', ''),
                author_avatar=account.get('avatar', ''),
                author_note=account.get('note', ''),
                author_followers_count=int(account.get('followers_count', 0)),
                author_following_count=int(account.get('following_count', 0)),
                author_statuses_count=int(account.get('statuses_count', 0))
            )
            
            return post
            
        except Exception as e:
            logger.error(f"Error parsing post data: {e}")
            return None

def create_mastodon_client(instance_url: str) -> MastodonAPIClient:
    """
    Factory function to create a Mastodon API client.
    
    Args:
        instance_url: The Mastodon instance URL
        
    Returns:
        Configured MastodonAPIClient instance
    """
    # Ensure URL has proper protocol
    if not instance_url.startswith(('http://', 'https://')):
        instance_url = f"https://{instance_url}"
    
    return MastodonAPIClient(instance_url)

# For testing
if __name__ == "__main__":
    # Test the client with mastodon.social
    print("🧪 Testing Mastodon API client...")
    
    client = create_mastodon_client("https://mastodon.social")
    posts = client.get_public_timeline(limit=5)
    
    print(f"✅ Fetched {len(posts)} posts from mastodon.social")
    for i, post in enumerate(posts[:3]):
        print(f"{i+1}. @{post.author_username}: {post.content[:50]}...")
        print(f"   Created: {post.created_at}, Favs: {post.favourites_count}, Boosts: {post.reblogs_count}")
        
    # Test trending hashtags
    hashtags = client.get_trending_hashtags(limit=5)
    print(f"✅ Fetched {len(hashtags)} trending hashtags")
    for hashtag in hashtags[:3]:
        if isinstance(hashtag, dict):
            print(f"   #{hashtag.get('name', 'unknown')}") 