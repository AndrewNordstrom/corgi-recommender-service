# Database Interface

The Corgi Recommender Service provides a clean, high-level interface for interacting with the database. This interface abstracts away the implementation details of the ORM and SQL queries, making it easy to work with the database from other parts of the application.

## Overview

The database interface is defined in the `db.interface` module and provides functions for:

- Recording user interactions
- Storing post metadata
- Getting personalized recommendations
- Managing user privacy settings
- Bulk importing/exporting data

## Key Functions

### User Interactions

#### `record_interaction(user_id, post_id, interaction_type, instance_url=None, context=None)`

Records a user interaction with a post.

```python
from db.interface import record_interaction

# Record a favorite
record_interaction(
    user_id="user123",
    post_id="post456",
    interaction_type="favorite",
    context={"source": "timeline", "position": 3}
)
```

#### `get_user_interaction_history(user_id, instance_url=None, limit=50)`

Gets a user's interaction history.

```python
from db.interface import get_user_interaction_history

# Get recent interactions
interactions = get_user_interaction_history(
    user_id="user123",
    limit=10
)

for interaction in interactions:
    print(f"{interaction['interaction_type']} on {interaction['post_id']}")
```

### Post Management

#### `store_post_metadata(post_data)`

Stores metadata for a post.

```python
from db.interface import store_post_metadata

# Store post metadata
store_post_metadata({
    "post_id": "post456",
    "author_id": "author789",
    "author_name": "Corgi Lover",
    "content": "Look at my cute corgi!",
    "created_at": "2025-04-22T12:00:00Z",
    "language": "en",
    "favorites": 10,
    "boosts": 5,
    "replies": 2,
    "tags": ["corgi", "pets", "cute"]
})
```

#### `get_recent_posts(limit=20, offset=0, language=None, tag=None)`

Gets a list of recent posts.

```python
from db.interface import get_recent_posts

# Get recent posts in English tagged with "corgi"
posts = get_recent_posts(
    limit=10,
    language="en",
    tag="corgi"
)

for post in posts:
    print(f"{post['author_name']}: {post['content']}")
```

### Recommendations

#### `get_personalized_recommendations(user_id, instance_url=None, limit=10, log_results=True)`

Gets personalized recommendations for a user.

```python
from db.interface import get_personalized_recommendations

# Get recommendations for a user
recommendations = get_personalized_recommendations(
    user_id="user123",
    limit=5
)

for rec in recommendations:
    print(f"{rec['post_id']} - {rec['reason']}")
```

#### `get_starter_recommendations(limit=10, language="en")`

Gets starter recommendations for new or anonymous users.

```python
from db.interface import get_starter_recommendations

# Get recommendations for a new user
recommendations = get_starter_recommendations(
    limit=5,
    language="en"
)

for rec in recommendations:
    print(f"{rec['post_id']} - {rec['reason']}")
```

#### `log_recommendation(user_id, post_id, reason, instance_url=None, model_version="1.0.0")`

Logs a recommendation made to a user.

```python
from db.interface import log_recommendation

# Log a recommendation
log_recommendation(
    user_id="user123",
    post_id="post456",
    reason="Based on your interest in corgis",
    model_version="1.0.0"
)
```

### Author Preferences

#### `get_author_preference_scores(user_id, instance_url=None)`

Gets preference scores for authors a user has interacted with.

```python
from db.interface import get_author_preference_scores

# Get author preferences
preferences = get_author_preference_scores(
    user_id="user123"
)

for author_id, score in preferences.items():
    print(f"Author {author_id}: {score}")
```

### Privacy Management

#### `update_privacy_settings(user_id, privacy_level, instance_url=None)`

Updates privacy settings for a user.

```python
from db.interface import update_privacy_settings

# Update privacy settings
update_privacy_settings(
    user_id="user123",
    privacy_level="limited"
)
```

#### `get_privacy_report(user_id, instance_url=None)`

Gets a privacy report for a user.

```python
from db.interface import get_privacy_report

# Get privacy report
report = get_privacy_report(
    user_id="user123"
)

print(f"Privacy level: {report['privacy_level']}")
print(f"Data count: {report['interaction_count']}")
```

### Bulk Operations

#### `bulk_import_posts(posts)`

Bulk imports a list of posts.

```python
from db.interface import bulk_import_posts

# Import multiple posts
posts = [
    {
        "post_id": "post1",
        "author_id": "author1",
        "content": "Post 1 content"
    },
    {
        "post_id": "post2",
        "author_id": "author1",
        "content": "Post 2 content"
    }
]

success, errors = bulk_import_posts(posts)
print(f"Imported {success} posts, {errors} failures")
```

#### `bulk_record_interactions(interactions)`

Bulk records a list of interactions.

```python
from db.interface import bulk_record_interactions

# Record multiple interactions
interactions = [
    {
        "user_id": "user1",
        "post_id": "post1",
        "interaction_type": "favorite"
    },
    {
        "user_id": "user1",
        "post_id": "post2",
        "interaction_type": "boost"
    }
]

success, errors = bulk_record_interactions(interactions)
print(f"Recorded {success} interactions, {errors} failures")
```

## Integration with APIs

The database interface is designed to be easily integrated with API endpoints. For example, here's how you might implement an API endpoint for recording interactions:

```python
@app.route("/api/v1/interactions", methods=["POST"])
def record_interaction_endpoint():
    data = request.json
    
    result = record_interaction(
        user_id=data["user_id"],
        post_id=data["post_id"],
        interaction_type=data["interaction_type"],
        context=data.get("context")
    )
    
    if result:
        return {"status": "success"}
    else:
        return {"status": "error", "message": "Failed to record interaction"}, 500
```

## Privacy Considerations

The database interface automatically handles privacy concerns:

- User IDs are pseudonymized using HMAC-SHA256 hashing
- Privacy levels are respected when retrieving data
- Data retention policies are applied automatically

This ensures that the application maintains user privacy without requiring explicit handling in business logic.

## Error Handling

The database interface functions handle errors gracefully and log them appropriately. Most functions return `False` or an empty collection on error, making it safe to use them without extensive try/except blocks in your code.

However, for critical operations, it's still a good practice to check the return values and handle errors explicitly.

## Thread Safety

The database interface is thread-safe and can be used from multiple threads concurrently. It uses SQLAlchemy's scoped session management to ensure that each thread gets its own session.

This makes it suitable for use in multi-threaded web servers like Gunicorn or uWSGI.