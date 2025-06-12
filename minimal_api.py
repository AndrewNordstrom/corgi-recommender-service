#!/usr/bin/env python3
from flask import Flask, jsonify, request
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app, origins=['http://localhost:5314', 'http://localhost:3000'])

def create_full_account(username="test_user", display_name="Test User"):
    """Create a full Mastodon-compatible account object"""
    return {
        "id": f"account_{username}",
        "username": username,
        "acct": username,
        "display_name": display_name,
        "locked": False,
        "bot": False,
        "discoverable": True,
        "group": False,
        "created_at": "2023-01-01T00:00:00.000Z",
        "note": f"<p>Account for {display_name}</p>",
        "url": f"https://mastodon.social/@{username}",
        "avatar": "https://via.placeholder.com/100x100/4A9EFF/FFFFFF?text=T",
        "avatar_static": "https://via.placeholder.com/100x100/4A9EFF/FFFFFF?text=T",
        "header": "https://via.placeholder.com/1500x500/E1E8ED/000000?text=Header",
        "header_static": "https://via.placeholder.com/1500x500/E1E8ED/000000?text=Header",
        "followers_count": 150,
        "following_count": 75,
        "statuses_count": 42,
        "last_status_at": "2024-01-01",
        "emojis": [],
        "fields": []
    }

@app.route("/api/v1/recommendations/timeline")
def timeline():
    user_id = request.args.get('user_id', 'anonymous')
    limit = int(request.args.get('limit', 10))
    
    # Super simple personalization - different posts for different users
    if 'account1' in user_id or user_id == 'elk_user_account1':
        posts = [
            {
                "id": "post_1_for_account1",
                "uri": "https://mastodon.social/posts/post_1_for_account1",
                "url": "https://mastodon.social/@test_user/post_1_for_account1",
                "content": "<p>🎉 This is personalized content for Account 1!</p>",
                "created_at": "2024-01-01T12:00:00.000Z",
                "edited_at": None,
                "in_reply_to_id": None,
                "in_reply_to_account_id": None,
                "sensitive": False,
                "spoiler_text": "",
                "visibility": "public",
                "language": "en",
                "favourited": True,
                "reblogged": False,
                "muted": False,
                "bookmarked": False,
                "pinned": False,
                "favourites_count": 10,
                "reblogs_count": 2,
                "replies_count": 3,
                "favouritesCount": 10,
                "reblogsCount": 2,
                "repliesCount": 3,
                "account": create_full_account("test_user", "Test User"),
                "media_attachments": [],
                "mentions": [],
                "tags": [],
                "emojis": [],
                "card": None,
                "poll": None,
                "reblog": None
            },
            {
                "id": "post_2_for_account1",
                "uri": "https://mastodon.social/posts/post_2_for_account1",
                "url": "https://mastodon.social/@test_user/post_2_for_account1",
                "content": "<p>🚀 Account 1, here's another personalized recommendation!</p>",
                "created_at": "2024-01-01T11:30:00.000Z",
                "edited_at": None,
                "in_reply_to_id": None,
                "in_reply_to_account_id": None,
                "sensitive": False,
                "spoiler_text": "",
                "visibility": "public",
                "language": "en",
                "favourited": False,
                "reblogged": True,
                "muted": False,
                "bookmarked": True,
                "pinned": False,
                "favourites_count": 25,
                "reblogs_count": 8,
                "replies_count": 12,
                "favouritesCount": 25,
                "reblogsCount": 8,
                "repliesCount": 12,
                "account": create_full_account("awesome_user", "Awesome User"),
                "media_attachments": [],
                "mentions": [],
                "tags": [],
                "emojis": [],
                "card": None,
                "poll": None,
                "reblog": None
            },
            {
                "id": "post_3_for_account1",
                "uri": "https://mastodon.social/posts/post_3_for_account1",
                "url": "https://mastodon.social/@tech_user/post_3_for_account1",
                "content": "<p>💡 Account 1 loves tech content - here's a special recommendation!</p>",
                "created_at": "2024-01-01T11:00:00.000Z",
                "edited_at": None,
                "in_reply_to_id": None,
                "in_reply_to_account_id": None,
                "sensitive": False,
                "spoiler_text": "",
                "visibility": "public",
                "language": "en",
                "favourited": True,
                "reblogged": False,
                "muted": False,
                "bookmarked": False,
                "pinned": False,
                "favourites_count": 42,
                "reblogs_count": 15,
                "replies_count": 8,
                "favouritesCount": 42,
                "reblogsCount": 15,
                "repliesCount": 8,
                "account": create_full_account("tech_user", "Tech Enthusiast"),
                "media_attachments": [],
                "mentions": [],
                "tags": [],
                "emojis": [],
                "card": None,
                "poll": None,
                "reblog": None
            }
        ]
    elif 'account2' in user_id or user_id == 'elk_user_account2':
        posts = [
            {
                "id": "post_1_for_account2",
                "uri": "https://mastodon.social/posts/post_1_for_account2",  
                "url": "https://mastodon.social/@cool_user/post_1_for_account2",
                "content": "<p>🌟 This is personalized content for Account 2!</p>",
                "created_at": "2024-01-01T13:00:00.000Z",
                "edited_at": None,
                "in_reply_to_id": None,
                "in_reply_to_account_id": None,
                "sensitive": False,
                "spoiler_text": "",
                "visibility": "public",
                "language": "en",
                "favourited": False,
                "reblogged": True,
                "muted": False,
                "bookmarked": False,
                "pinned": False,
                "favourites_count": 5,
                "reblogs_count": 8,
                "replies_count": 1,
                "favouritesCount": 5,
                "reblogsCount": 8,
                "repliesCount": 1,
                "account": create_full_account("cool_user", "Cool User"),
                "media_attachments": [],
                "mentions": [],
                "tags": [],
                "emojis": [],
                "card": None,
                "poll": None,
                "reblog": None
            },
            {
                "id": "post_2_for_account2",
                "uri": "https://mastodon.social/posts/post_2_for_account2",
                "url": "https://mastodon.social/@art_lover/post_2_for_account2",
                "content": "<p>🎨 Account 2, check out this amazing art recommendation!</p>",
                "created_at": "2024-01-01T12:45:00.000Z",
                "edited_at": None,
                "in_reply_to_id": None,
                "in_reply_to_account_id": None,
                "sensitive": False,
                "spoiler_text": "",
                "visibility": "public",
                "language": "en",
                "favourited": True,
                "reblogged": False,
                "muted": False,
                "bookmarked": True,
                "pinned": False,
                "favourites_count": 33,
                "reblogs_count": 12,
                "replies_count": 7,
                "favouritesCount": 33,
                "reblogsCount": 12,
                "repliesCount": 7,
                "account": create_full_account("art_lover", "Art Lover"),
                "media_attachments": [],
                "mentions": [],
                "tags": [],
                "emojis": [],
                "card": None,
                "poll": None,
                "reblog": None
            }
        ]
    else:
        # Default posts for other users - provide several options
        posts = [
            {
                "id": f"post_1_for_{user_id}",
                "uri": f"https://mastodon.social/posts/post_1_for_{user_id}",
                "url": f"https://mastodon.social/@default_user/post_1_for_{user_id}",
                "content": f"<p>📝 Welcome {user_id}! Here's your first personalized recommendation.</p>",
                "created_at": "2024-01-01T14:00:00.000Z",
                "edited_at": None,
                "in_reply_to_id": None,
                "in_reply_to_account_id": None,
                "sensitive": False,
                "spoiler_text": "",
                "visibility": "public",
                "language": "en",
                "favourited": False,
                "reblogged": False,
                "muted": False,
                "bookmarked": False,
                "pinned": False,
                "favourites_count": 3,
                "reblogs_count": 1,
                "replies_count": 0,
                "favouritesCount": 3,
                "reblogsCount": 1,
                "repliesCount": 0,
                "account": create_full_account("default_user", "Default User"),
                "media_attachments": [],
                "mentions": [],
                "tags": [],
                "emojis": [],
                "card": None,
                "poll": None,
                "reblog": None
            },
            {
                "id": f"post_2_for_{user_id}",
                "uri": f"https://mastodon.social/posts/post_2_for_{user_id}",
                "url": f"https://mastodon.social/@friendly_bot/post_2_for_{user_id}",
                "content": f"<p>🤖 Hi {user_id}! Here's another recommendation just for you.</p>",
                "created_at": "2024-01-01T13:30:00.000Z",
                "edited_at": None,
                "in_reply_to_id": None,
                "in_reply_to_account_id": None,
                "sensitive": False,
                "spoiler_text": "",
                "visibility": "public",
                "language": "en",
                "favourited": True,
                "reblogged": True,
                "muted": False,
                "bookmarked": False,
                "pinned": False,
                "favourites_count": 18,
                "reblogs_count": 6,
                "replies_count": 4,
                "favouritesCount": 18,
                "reblogsCount": 6,
                "repliesCount": 4,
                "account": create_full_account("friendly_bot", "Friendly Bot"),
                "media_attachments": [],
                "mentions": [],
                "tags": [],
                "emojis": [],
                "card": None,
                "poll": None,
                "reblog": None
            }
        ]
    
    # Apply limit
    posts = posts[:limit]
    
    print(f"📊 Request from user: {user_id} -> returning {len(posts)} posts")
    return jsonify(posts)

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    print("🚀 Starting minimal API on port 9999...")
    app.run(host="0.0.0.0", port=9999, debug=False, threaded=True) 