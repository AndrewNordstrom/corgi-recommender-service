# Interactions API

The Interactions API allows you to log and retrieve user interactions with posts. These interactions are crucial for the recommendation system to understand user preferences and generate personalized content suggestions.

## What are Interactions?

Interactions represent a user's engagement with content. They can be:

- **Explicit user actions**: Favorites, bookmarks, reblogs
- **Preference signals**: "More like this" or "Less like this" feedback
- **Context information**: Where the interaction happened (e.g., home timeline, profile page)

The system uses these interactions to build a preference profile for each user, which helps the recommendation algorithm prioritize content that matches their interests.

## Log an Interaction

Record a user's interaction with a post.

### Endpoint

```
POST /api/v1/interactions
```

### Request Format

```json
{
  "user_alias": "abc123",
  "post_id": "xyz789",
  "action_type": "favorite",
  "context": {
    "source": "timeline_home"
  }
}
```

#### Parameters

| Field | Type | Description |
|-------|------|-------------|
| `user_alias` | String | Unique identifier for the user |
| `post_id` | String | Identifier of the post being interacted with |
| `action_type` | String | Type of interaction: `favorite`, `bookmark`, `reblog`, `more_like_this`, `less_like_this` |
| `context` | Object | Optional additional information about the interaction |

### Response

```json
{
  "status": "ok"
}
```

### Usage Examples

#### Log a Favorite

```bash
curl -X POST http://localhost:5001/api/v1/interactions \
  -H "Content-Type: application/json" \
  -d '{
    "user_alias": "user123",
    "post_id": "post456",
    "action_type": "favorite",
    "context": {
      "source": "timeline_home"
    }
  }'
```

#### Log "More Like This" Feedback

```bash
curl -X POST http://localhost:5001/api/v1/interactions \
  -H "Content-Type: application/json" \
  -d '{
    "user_alias": "user123",
    "post_id": "post789",
    "action_type": "more_like_this",
    "context": {
      "source": "recommendations"
    }
  }'
```

## Get Interactions for a Post

Retrieve all interactions recorded for a specific post.

### Endpoint

```
GET /api/v1/interactions/{post_id}
```

### Response

```json
{
  "post_id": "post456",
  "interaction_counts": {
    "favorites": 42,
    "reblogs": 12,
    "replies": 7,
    "bookmarks": 5
  },
  "interactions": [
    {
      "action_type": "favorite",
      "count": 42
    },
    {
      "action_type": "reblog",
      "count": 12
    },
    {
      "action_type": "bookmark",
      "count": 5
    }
  ]
}
```

### Usage Example

```bash
curl http://localhost:5001/api/v1/interactions/post456
```

## Technical Details

### Action Type Normalization

The API automatically normalizes action types for consistency:

- `favourite`, `favourited` → `favorite`
- `bookmarked` → `bookmark`
- `unfavourite` → `unfavorite`

### Conflict Resolution

Certain action types are mutually exclusive. For example, if a user indicates "less_like_this" after previously indicating "more_like_this", the previous interaction will be removed.

### Database Impact

When a user interacts with a post:

1. The interaction is recorded in the `interactions` table
2. For certain action types (favorites, reblogs, bookmarks), the `interaction_counts` field in the `post_metadata` table is incremented

### Privacy Considerations

User IDs are pseudonymized using a hashing algorithm before storage. The privacy level set by the user (see [Privacy API](privacy.md)) affects how interactions are stored and used.

## Common Issues

| Issue | Solution |
|-------|----------|
| Missing required fields | Ensure `user_alias`, `post_id`, and `action_type` are provided |
| Invalid action type | Use one of the supported action types |
| Post not found | Verify the post exists in the system before logging interactions |