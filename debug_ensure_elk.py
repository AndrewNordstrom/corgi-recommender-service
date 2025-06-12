#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.recommendations import ensure_elk_compatibility

# Test data that mimics what build_simple_posts_from_rows creates
test_post = {
    "id": "114669420247619504",
    "url": "https://mastodon.social/@onet/114669420247619504",
    "uri": "https://mastodon.social/@onet/114669420247619504",
    "_corgi_external": True,
    "_corgi_cached": True,
    "_corgi_source_instance": "mastodon.social",
    "account": {
        "username": "onet",
        "acct": "onet@mastodon.social",
        "display_name": "Onet"
    }
}

print("Before ensure_elk_compatibility:")
print(f"  URI: {test_post.get('uri')}")
print(f"  URL: {test_post.get('url')}")
print(f"  _corgi_external: {test_post.get('_corgi_external')}")

result = ensure_elk_compatibility(test_post)

print("\nAfter ensure_elk_compatibility:")
print(f"  URI: {result.get('uri')}")
print(f"  URL: {result.get('url')}")
print(f"  _corgi_external: {result.get('_corgi_external')}")

# Test the condition logic
is_external = test_post.get('_corgi_external', False)
print(f"\nCondition check:")
print(f"  is_external: {is_external}")
print(f"  not post_data.get('uri'): {not test_post.get('uri')}")
print(f"  uri value: '{test_post.get('uri')}'")
print(f"  uri bool: {bool(test_post.get('uri'))}") 