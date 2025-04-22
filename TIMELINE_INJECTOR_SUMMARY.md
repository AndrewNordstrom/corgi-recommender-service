# Timeline Injector Module

This module provides functionality to inject posts into a timeline based on various configurable strategies. It's designed to facilitate a seamless integration of recommended or synthetic posts into a real chronological timeline.

## Features

- **Flexible Injection Strategies**: Multiple configurable strategies for post injection
  - Uniform distribution
  - After every N real posts
  - Only in the first portion of a timeline
  - Tag matching for contextually relevant injections
  
- **Timeline Order Preservation**: All posts (real and injected) are properly sorted by timestamp

- **Timestamp Harmonization**: Injected posts get realistic timestamps based on adjacent posts

- **Metadata Tagging**: Injected posts are marked with `"injected": true` for frontend identification

- **Time Gap Awareness**: Can require minimum time gaps for injection to avoid clumping

- **Hashtag Matching**: Can inject based on matching hashtags for content relevance

- **Configurable Limits**: Control maximum number of injections

## Implementation

The core function `inject_into_timeline()` takes:
- A list of real posts
- A list of injectable posts
- A strategy configuration dictionary

It returns a merged timeline with the injected posts placed according to the specified strategy and all posts in chronological order.

## Usage

```python
from utils.timeline_injector import inject_into_timeline

# Get real and injectable posts
real_posts = get_real_posts_from_mastodon()
injectable_posts = get_synthetic_posts()

# Define injection strategy
strategy = {
    "type": "tag_match",
    "max_injections": 5,
    "shuffle_injected": True,
    "inject_only_if_gap_minutes": 10
}

# Merge the timeline
merged_timeline = inject_into_timeline(real_posts, injectable_posts, strategy)

# Use the merged timeline in your app
display_timeline(merged_timeline)
```

## Testing

The module comes with comprehensive unit tests that cover:
- Basic functionality (timestamp extraction, sorting, tag extraction)
- All injection strategies
- Edge cases (empty inputs, maximum injection limits)
- Timestamp harmonization
- Gap requirements

## Example

An example usage script is provided in `examples/timeline_injection_example.py` that demonstrates all the available strategies with sample data.

## Integration with Mastodon

This module works with standard Mastodon post format and can be easily integrated into any Mastodon-compatible application.