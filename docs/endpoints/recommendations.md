# Recommendations API

The Recommendations API provides personalized post suggestions based on user preferences and interaction history. These endpoints deliver content that's likely to interest the user, formatted in a way that's compatible with Mastodon clients.

## How Recommendations Work

The Corgi Recommender Service analyzes several factors to generate personalized recommendations:

- **User interactions**: Favorites, bookmarks, reblogs, and explicit feedback
- **Content engagement**: Overall popularity and interaction rates
- **Recency**: How recently posts were created
- **Author preference**: User's history with specific content creators

These factors are combined using a weighted algorithm to produce a ranking score between 0 and 1 for each potential recommendation.

## Get Recommended Timeline

Retrieve a personalized timeline of recommended posts.

### Endpoint

```
GET /api/v1/timelines/recommended
```

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_id` | String | Yes | - | The user to generate recommendations for |
| `limit` | Integer | No | 20 | Maximum number of recommendations to return (1-40) |

### Response

The response is an array of posts in Mastodon-compatible format:

```json
[
  {
    "id": "post123",
    "content": "<p>This is a sample post content</p>",
    "created_at": "2025-03-15T14:32:18Z",
    "account": {
      "id": "user456",
      "username": "corgi_lover",
      "display_name": "Corgi Enthusiast",
      "url": "https://mastodon.example.com/@corgi_lover"
    },
    "language": "en",
    "replies_count": 3,
    "reblogs_count": 7,
    "favourites_count": 25,
    "url": "https://mastodon.example.com/@corgi_lover/post123",
    "ranking_score": 0.87,
    "recommendation_reason": "From an author you might like",
    "is_real_mastodon_post": true,
    "is_synthetic": false
  },
  // Additional posts...
]
```

### Key Response Fields

| Field | Description |
|-------|-------------|
| `ranking_score` | Confidence score between 0-1 indicating recommendation strength |
| `recommendation_reason` | Human-readable explanation for why this post was recommended |
| `is_real_mastodon_post` | Whether this is from the actual Mastodon network |
| `is_synthetic` | Whether this is a generated/synthetic post |

### Usage Example

```bash
curl "http://localhost:5001/api/v1/timelines/recommended?user_id=user123&limit=10"
```

## Generate Rankings (Advanced)

Trigger the generation of new rankings for a user. Normally, this happens automatically, but this endpoint allows manual control.

### Endpoint

```
POST /api/v1/recommendations/rankings/generate
```

### Request

```json
{
  "user_id": "user123",
  "force_refresh": true
}
```

### Response

```json
{
  "message": "Rankings generated successfully",
  "count": 25
}
```

## Technical Details

### Ranking Algorithm

The ranking algorithm (found in `core/ranking_algorithm.py`) uses a weighted scoring system:

1. **Author preference score**: Based on user's history with the author
2. **Content engagement score**: Based on overall engagement metrics
3. **Recency score**: Favors more recent content

These are combined using configurable weights to produce a final ranking score.

### Mastodon Compatibility

The recommendations are returned in a format that's compatible with the Mastodon API, allowing seamless integration with clients. Additional recommendation-specific fields are included to provide more context.

### Caching and Performance

Generated rankings are cached for one hour by default. Requests within this period will return the cached rankings unless `force_refresh` is specified.

## Common Issues

| Issue | Solution |
|-------|----------|
| No recommendations | Ensure the user has some recorded interactions first |
| Low quality recommendations | More user interactions lead to better recommendations |
| Missing recommendation fields | Check that posts have the required metadata |