#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.recommendations import ensure_elk_compatibility

# Test data that exactly matches what build_simple_posts_from_rows creates
test_post = {
    "id": "114669420247619504",
    "created_at": "2024-06-25T12:00:00.000Z",
    "content": "Test content",
    "account": {
        "id": "110473514437222729",
        "username": "onet",
        "acct": "onet@mastodon.social",
        "display_name": "Onet",
        "url": "https://mastodon.social/@onet",
        "avatar": "https://files.mastodon.social/accounts/avatars/110/473/514/437/222/729/original/a5e7d666dc6c2ce8.png",
        "avatar_static": "https://files.mastodon.social/accounts/avatars/110/473/514/437/222/729/original/a5e7d666dc6c2ce8.png",
        "note": "",
        "bot": False,
        "locked": False,
        "verified": False,
        "fields": []
    },
    "favourites_count": 5,
    "reblogs_count": 2,
    "replies_count": 1,
    "url": "https://mastodon.social/@onet/114669420247619504",
    "uri": "https://mastodon.social/@onet/114669420247619504",
    "language": "en",
    "tags": [],
    "media_attachments": [],
    "mentions": [],
    "emojis": [],
    "visibility": "public",
    "is_recommendation": True,
    "is_real_mastodon_post": True,
    "is_synthetic": False,
    "source_instance": "mastodon.social",
    "_corgi_external": True,
    "_corgi_cached": True,
    "_corgi_source_instance": "mastodon.social"
}

print("=== BEFORE ensure_elk_compatibility ===")
print(f"URI: '{test_post.get('uri')}'")
print(f"URL: '{test_post.get('url')}'")
print(f"_corgi_external: {test_post.get('_corgi_external')}")
print(f"_corgi_external type: {type(test_post.get('_corgi_external'))}")

# Test the condition manually
is_external = test_post.get('_corgi_external', False)
print(f"\n=== CONDITION TESTING ===")
print(f"is_external = test_post.get('_corgi_external', False): {is_external}")
print(f"type(is_external): {type(is_external)}")
print(f"bool(is_external): {bool(is_external)}")
print(f"is_external == True: {is_external == True}")
print(f"is_external is True: {is_external is True}")

# Test URI conditions
uri_value = test_post.get('uri')
print(f"\nURI conditions:")
print(f"post_data.get('uri'): '{uri_value}'")
print(f"not post_data.get('uri'): {not uri_value}")
print(f"bool(uri_value): {bool(uri_value)}")

result = ensure_elk_compatibility(test_post.copy())

print(f"\n=== AFTER ensure_elk_compatibility ===")
print(f"URI: '{result.get('uri')}'")
print(f"URL: '{result.get('url')}'")
print(f"_corgi_external: {result.get('_corgi_external')}") 