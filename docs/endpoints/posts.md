# Posts API

The Posts API provides endpoints for managing and retrieving posts within the Corgi Recommender Service. These endpoints allow you to access posts in a Mastodon-compatible format.

## Endpoints

### Get Posts List

```
GET /api/v1/posts
```

Retrieves a list of posts with optional filtering.

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| `limit` | integer | query | Maximum number of posts to return (default: 100) |

#### Response

```json
[
  {
    "id": "post_12345",
    "content": "<p>This is a post about corgis!</p>",
    "created_at": "2025-03-15T14:30:00Z",
    "account": {
      "id": "user_789",
      "username": "corgi_lover",
      "display_name": "Corgi Enthusiast"
    },
    "favourites_count": 42,
    "reblogs_count": 12,
    "replies_count": 5
  },
  // More posts...
]
```

### Create or Update Post

```
POST /api/v1/posts
```

Creates a new post or updates an existing one.

#### Request Body

```json
{
  "content": "<p>Just added a new post about corgis!</p>",
  "author_id": "user_789",
  "author_name": "corgi_lover",
  "language": "en",
  "tags": ["corgi", "dogs", "pets"],
  "sensitive": false
}
```

#### Response (New Post)

```json
{
  "post_id": "post_12345",
  "status": "created"
}
```

#### Response (Updated Post)

```json
{
  "post_id": "post_12345",
  "status": "updated"
}
```

### Get Specific Post

```
GET /api/v1/posts/{post_id}
```

Retrieves a single post by its unique identifier.

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| `post_id` | string | path | The ID of the post to retrieve |

#### Response

```json
{
  "id": "post_12345",
  "content": "<p>This is a post about corgis!</p>",
  "created_at": "2025-03-15T14:30:00Z",
  "account": {
    "id": "user_789",
    "username": "corgi_lover",
    "display_name": "Corgi Enthusiast"
  },
  "favourites_count": 42,
  "reblogs_count": 12,
  "replies_count": 5,
  "language": "en",
  "tags": ["corgi", "dogs", "pets"],
  "sensitive": false
}
```

### Get Posts by Author

```
GET /api/v1/posts/author/{author_id}
```

Retrieves all posts created by a single author.

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| `author_id` | string | path | The ID of the author to retrieve posts for |
| `limit` | integer | query | Maximum number of posts to return (default: 20) |

#### Response

```json
[
  {
    "id": "post_12345",
    "content": "<p>This is a post about corgis!</p>",
    "created_at": "2025-03-15T14:30:00Z",
    "account": {
      "id": "user_789",
      "username": "corgi_lover",
      "display_name": "Corgi Enthusiast"
    },
    "favourites_count": 42,
    "reblogs_count": 12,
    "replies_count": 5
  },
  // More posts by this author...
]
```

### Get Trending Posts

```
GET /api/v1/posts/trending
```

Retrieves posts with the highest interaction counts.

#### Parameters

| Name | Type | In | Description |
|------|------|-------|------------|
| `limit` | integer | query | Maximum number of posts to return (default: 10) |

#### Response

```json
[
  {
    "id": "post_56789",
    "content": "<p>This trending post about corgis has lots of interactions!</p>",
    "created_at": "2025-03-14T09:15:00Z",
    "account": {
      "id": "user_123",
      "username": "corgi_expert",
      "display_name": "Corgi Expert"
    },
    "favourites_count": 250,
    "reblogs_count": 75,
    "replies_count": 42
  },
  // More trending posts...
]
```

## Post Object

Posts are returned in a Mastodon-compatible format with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the post |
| `content` | string | HTML content of the post |
| `created_at` | string | Creation timestamp in ISO 8601 format |
| `account` | object | Author information including id, username, and display_name |
| `favourites_count` | integer | Number of favorites for this post |
| `reblogs_count` | integer | Number of reblogs of this post |
| `replies_count` | integer | Number of replies to this post |
| `language` | string | ISO language code (e.g., "en") |
| `tags` | array | Hashtags associated with the post |
| `sensitive` | boolean | Whether the post contains sensitive content |
| `ranking_score` | number | Recommendation ranking score (0.0 to 1.0) |
| `is_real_mastodon_post` | boolean | Whether this is a real Mastodon post (vs synthetic) |
| `is_synthetic` | boolean | Whether this is a synthetic/generated post |

## Usage Examples

### JavaScript

```javascript
// Get trending posts
fetch('http://api.example.com/api/v1/posts/trending?limit=5')
  .then(response => response.json())
  .then(posts => console.log(posts));

// Get posts by a specific author
fetch('http://api.example.com/api/v1/posts/author/user_789')
  .then(response => response.json())
  .then(posts => console.log(posts));

// Create a new post
fetch('http://api.example.com/api/v1/posts', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: JSON.stringify({
    content: '<p>New post about corgis!</p>',
    author_id: 'user_789',
    author_name: 'corgi_lover',
    language: 'en',
    tags: ['corgi', 'dogs']
  })
})
.then(response => response.json())
.then(result => console.log(result));
```

### Python

```python
import requests

# Get trending posts
response = requests.get(
    'http://api.example.com/api/v1/posts/trending',
    params={'limit': 5}
)
trending_posts = response.json()

# Get a specific post
response = requests.get(
    'http://api.example.com/api/v1/posts/post_12345'
)
post = response.json()

# Create a new post
response = requests.post(
    'http://api.example.com/api/v1/posts',
    headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_TOKEN'
    },
    json={
        'content': '<p>New post about corgis!</p>',
        'author_id': 'user_789',
        'author_name': 'corgi_lover',
        'language': 'en',
        'tags': ['corgi', 'dogs']
    }
)
result = response.json()
```