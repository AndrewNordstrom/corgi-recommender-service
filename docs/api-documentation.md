# API Documentation Guide

The Corgi Recommender Service provides comprehensive API documentation through multiple interfaces to help developers integrate with the service.

## Available Documentation Interfaces

### Swagger UI

Swagger UI provides an interactive experience for exploring and testing the API. It's the best choice when you want to try out API calls directly from your browser.

**Access URL:** `/api/v1/docs`

![Swagger UI Screenshot](https://swagger.io/swagger/media/assets/images/swagger-ui3.png)

Features:
- Interactive "Try it out" functionality
- Detailed schema information
- Request/response examples
- Authentication support

### ReDoc

ReDoc offers a clean, responsive, and easy-to-read documentation interface that's ideal for understanding the API structure.

**Access URL:** `/api/v1/docs/redoc`

Features:
- Clean, three-panel layout
- Excellent readability
- Response examples
- Search functionality

### OpenAPI Specification

The raw OpenAPI specification is available in JSON format for integration with other tools.

**Access URL:** `/api/v1/docs/spec`

## Understanding the API Structure

The API is organized into several functional areas:

### Interactions API

Endpoints for logging and retrieving user interactions with posts:
- `POST /api/v1/interactions`: Log a user interaction
- `GET /api/v1/interactions/{post_id}`: Get interactions for a post
- `POST /api/v1/interactions/counts/batch`: Get counts for multiple posts
- `GET /api/v1/interactions/user/{user_id}`: Get all interactions for a user
- `GET /api/v1/interactions/favourites`: Get user's favorite posts

### Timelines API

Mastodon-compatible timeline endpoints with recommendation integration:
- `GET /api/v1/timelines/recommended`: Get personalized recommended posts
- `GET /api/v1/timelines/home`: Get home timeline (proxied to Mastodon)
- `GET /api/v1/timelines/home/augmented`: Get home timeline with injected recommendations

### Recommendations API

Endpoints specific to the recommendation engine:
- `GET /api/v1/recommendations`: Get personalized post recommendations
- `GET /api/v1/recommendations/real-posts`: Get only real Mastodon posts
- `POST /api/v1/rankings/generate`: Generate personalized rankings for a user

### Privacy API

User privacy settings management:
- `GET /api/v1/privacy`: Get user privacy settings
- `POST /api/v1/privacy`: Update user privacy settings

### Posts API

Post management endpoints:
- `GET /api/v1/posts`: Get a list of posts
- `POST /api/v1/posts`: Create or update a post
- `GET /api/v1/posts/{post_id}`: Get a specific post
- `GET /api/v1/posts/author/{author_id}`: Get posts by an author
- `GET /api/v1/posts/trending`: Get trending posts

### Proxy API

Transparent Mastodon proxy functionality:
- `GET /api/v1/proxy/status`: Check proxy status
- `GET /api/v1/proxy/instance`: Debug instance detection
- `GET /api/v1/proxy/metrics`: Get proxy usage metrics

## Authentication

Most API endpoints require authentication. The service supports:

1. **Bearer Token Authentication**:
   ```
   Authorization: Bearer <token>
   ```

2. **User ID Parameter** (for testing only):
   ```
   ?user_id=<user_id>
   ```

## Common Data Structures

### MastodonPost

The core post object follows the Mastodon API format with additional fields for recommendations:

```json
{
  "id": "123456",
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
  "ranking_score": 0.87,
  "recommendation_reason": "Based on your interest in dogs",
  "is_real_mastodon_post": true,
  "is_synthetic": false
}
```

### Interaction

User interactions with posts:

```json
{
  "user_alias": "user_12345",
  "post_id": "post_67890",
  "action_type": "favorite",
  "context": {
    "source": "timeline_home"
  }
}
```

### Privacy Settings

User privacy configuration:

```json
{
  "user_id": "user_12345",
  "tracking_level": "limited"
}
```

## Pagination

For endpoints that return lists, pagination is supported through these parameters:

- `limit`: Maximum number of items to return
- `page`: Page number for pagination
- `since_id`: Return items newer than this ID
- `max_id`: Return items older than this ID

## Error Handling

The API uses standard HTTP status codes and returns error details in a consistent format:

```json
{
  "error": "Description of what went wrong",
  "received": {
    "parameter_name": "invalid_value"
  },
  "request_id": "req_abc123"
}
```

## Implementing with FastAPI

For developers interested in implementing a similar API documentation system using FastAPI, check out the example code in `routes/fastapi_example.py`.