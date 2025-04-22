# Timeline Injector Module

This module provides functionality to inject posts into a Mastodon timeline based on various configurable strategies. It's designed to blend injectable posts seamlessly into a real timeline while preserving chronological order and realistic time gaps.

## Core Function

```python
def inject_into_timeline(
    real_posts: List[Dict], 
    injectable_posts: List[Dict], 
    strategy: Dict
) -> List[Dict]
```

### Parameters

- `real_posts`: List of real Mastodon posts (will be sorted by created_at)
- `injectable_posts`: List of posts to inject into the timeline
- `strategy`: Dictionary specifying injection strategy and parameters

### Strategy Configuration

The `strategy` parameter controls how posts are injected. It accepts the following fields:

- `type`: Strategy type (required)
  - `"uniform"`: Evenly distribute injected posts across the timeline
  - `"after_n"`: Insert an injected post after every N real posts
  - `"first_only"`: Only inject in first 10 posts
  - `"tag_match"`: Insert only after real posts that have matching hashtags

- `max_injections`: Maximum number of posts to inject (optional, defaults to all available injectable posts)
- `n`: Used with 'after_n' strategy to inject after every nth post (optional, defaults to 3)
- `shuffle_injected`: Whether to shuffle the injectable posts (optional, defaults to False)
- `inject_only_if_gap_minutes`: Minimum time gap required for injection (optional, defaults to 0 - no gap requirement)

### Example Strategy Configurations

```python
# Uniform distribution with shuffling
strategy_uniform = {
    "type": "uniform",
    "max_injections": 3,
    "shuffle_injected": True
}

# After every 2 posts, maximum 4 injections
strategy_after_n = {
    "type": "after_n",
    "n": 2,
    "max_injections": 4
}

# Only in first 10 posts, maximum 2 injections
strategy_first_only = {
    "type": "first_only",
    "max_injections": 2
}

# Tag matching with at most 3 injections
strategy_tag_match = {
    "type": "tag_match",
    "max_injections": 3
}

# With time gap requirement of 20 minutes
strategy_with_gap = {
    "type": "uniform",
    "max_injections": 3,
    "inject_only_if_gap_minutes": 20
}
```

## Post Format

Both real posts and injectable posts should follow the standard Mastodon JSON format, including at least:

- `id`: Post identifier
- `created_at`: ISO format timestamp
- `content`: Post content
- `account`: User account information

For tag matching, posts should include a `tags` array with tag objects:

```python
"tags": [
    {"name": "tech"},
    {"name": "programming"}
]
```

## Features

- **Timeline Order Preservation**: All posts (real and injected) are properly sorted by timestamp
- **Timestamp Harmonization**: Injected posts get realistic timestamps based on adjacent posts
- **Metadata Tagging**: Injected posts are marked with `"injected": true`
- **Time Gap Awareness**: Can require minimum time gaps for injection
- **Tag Matching**: Can inject based on matching hashtags
- **Configurable Limits**: Control maximum number of injections

## Usage Example

```python
from utils.timeline_injector import inject_into_timeline

# Get your real and injectable posts from your data source
real_posts = get_real_posts()
injectable_posts = get_injectable_posts()

# Define your injection strategy
strategy = {
    "type": "uniform",
    "max_injections": 5,
    "shuffle_injected": True
}

# Merge the timeline
merged_timeline = inject_into_timeline(real_posts, injectable_posts, strategy)

# Use the merged timeline
for post in merged_timeline:
    # Special rendering for injected posts if needed
    if post.get("injected", False):
        render_as_recommendation(post)
    else:
        render_as_normal_post(post)
```

See `examples/timeline_injection_example.py` for a complete example with various strategies.