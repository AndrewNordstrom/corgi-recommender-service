# API Overview

Corgi provides a comprehensive RESTful API for integrating personalized recommendations into your applications. This page provides a high-level overview of the API structure and common usage patterns.

## API Base URL

All API requests should be made to:

```
https://api.corgi-recs.io
```

For self-hosted instances, this will be your own domain.

## Authentication

Corgi uses API keys for authentication. Include your API key in all requests:

```bash
curl -X GET "https://api.corgi-recs.io/api/v1/timelines/recommended" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

<div class="corgi-callout">
  <div class="corgi-callout-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM11 7h2v2h-2V7zm0 4h2v6h-2v-6z"/></svg>
    API Key Security
  </div>
  <p>API keys should be kept secure and never exposed in client-side code. For browser-based applications, use a backend service to proxy requests to Corgi.</p>
</div>

## Versioning

The API is versioned to ensure backward compatibility. The current version is `v1`:

```
/api/v1/...
```

## Response Format

All API responses are returned as JSON:

```json
{
  "status": "ok",
  "data": {
    "key": "value"
  }
}
```

Error responses include error details:

```json
{
  "error": "Invalid request parameters",
  "details": "Missing required parameter: user_id",
  "status_code": 400
}
```

## Pagination

Endpoints that return multiple items support pagination:

```bash
curl -X GET "https://api.corgi-recs.io/api/v1/posts?limit=20&page=2" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Pagination parameters:

- `limit` - Number of items per page (default: 20, max: 100)
- `page` - Page number (default: 1)
- `max_id` - Return results older than this ID
- `since_id` - Return results newer than this ID

Paginated responses include metadata:

```json
{
  "data": [...],
  "pagination": {
    "total_items": 157,
    "total_pages": 8,
    "current_page": 2,
    "prev_page": 1,
    "next_page": 3,
    "has_more": true
  }
}
```

## Rate Limiting

API requests are rate-limited to ensure fair usage:

- 300 requests per minute per API key
- 10,000 requests per day per API key

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 297
X-RateLimit-Reset: 1617981600
```

When a rate limit is exceeded, a 429 error is returned:

```json
{
  "error": "Rate limit exceeded",
  "retry_after": 30,
  "status_code": 429
}
```

## Core Endpoints

The API is organized around these key resource areas:

### Timelines

Timeline endpoints provide Mastodon-compatible timelines with recommendations:

- `GET /api/v1/timelines/home` - Get regular home timeline (proxy to Mastodon)
- `GET /api/v1/timelines/home/augmented` - Get home timeline with injected recommendations
- `GET /api/v1/timelines/recommended` - Get a timeline of only recommended posts

[View Timeline API Reference →](../endpoints/timelines.md)

### Interactions

Interaction endpoints track user engagement with posts:

- `POST /api/v1/interactions` - Log a user interaction with a post
- `GET /api/v1/interactions/user/{user_id}` - Get a user's interactions
- `GET /api/v1/interactions/counts/batch` - Get interaction counts for multiple posts

[View Interaction API Reference →](../endpoints/feedback.md)

### Privacy

Privacy endpoints allow users to control data collection:

- `GET /api/v1/privacy` - Get current privacy settings
- `POST /api/v1/privacy` - Update privacy settings
- `DELETE /api/v1/privacy/data` - Delete all user data

[View Privacy API Reference →](../endpoints/privacy.md)

### Recommendations

Recommendation endpoints provide direct access to the recommendation engine:

- `GET /api/v1/recommendations` - Get personalized recommendations
- `POST /api/v1/recommendations/generate` - Generate fresh recommendations
- `GET /api/v1/recommendations/reasons` - Get explanation for recommendations

[View Recommendations API Reference →](../endpoints/recommendations.md)

### Proxy

Proxy endpoints provide information about the transparent proxy:

- `GET /api/v1/proxy/status` - Get proxy status
- `GET /api/v1/proxy/metrics` - Get proxy metrics
- `GET /api/v1/proxy/instance` - Debug instance detection

[View Proxy API Reference →](../endpoints/proxy.md)

## API Clients

We provide official client libraries for easy integration:

=== "Python"

    ```python
    import corgi
    
    client = corgi.Client(api_key="YOUR_API_KEY")
    
    # Get recommendations
    recommendations = client.timelines.recommended(user_id="user123")
    
    # Log an interaction
    client.interactions.create(
        user_id="user123",
        post_id="post456",
        action_type="favorite"
    )
    ```

=== "JavaScript"

    ```javascript
    import { CorgiClient } from '@corgi/client';
    
    const client = new CorgiClient({
      apiKey: 'YOUR_API_KEY'
    });
    
    // Get recommendations
    const recommendations = await client.timelines.recommended({
      userId: 'user123'
    });
    
    // Log an interaction
    await client.interactions.create({
      userId: 'user123',
      postId: 'post456',
      actionType: 'favorite'
    });
    ```

=== "Ruby"

    ```ruby
    require 'corgi'
    
    client = Corgi::Client.new(api_key: 'YOUR_API_KEY')
    
    # Get recommendations
    recommendations = client.timelines.recommended(user_id: 'user123')
    
    # Log an interaction
    client.interactions.create(
      user_id: 'user123',
      post_id: 'post456',
      action_type: 'favorite'
    )
    ```

## OpenAPI Specification

The complete API is documented in OpenAPI format and available at:

```
https://api.corgi-recs.io/openapi.yaml
```

You can also explore the API using our interactive Swagger UI:

```
https://api.corgi-recs.io/docs/
```

## Error Handling

Corgi uses standard HTTP status codes to indicate the success or failure of requests:

| Code | Description |
|------|-------------|
| 200  | Success |
| 201  | Created |
| 400  | Bad Request - Invalid parameters |
| 401  | Unauthorized - Invalid API key |
| 403  | Forbidden - Insufficient permissions |
| 404  | Not Found - Resource doesn't exist |
| 429  | Too Many Requests - Rate limit exceeded |
| 500  | Server Error - Something went wrong on our end |

Error responses include detailed information:

```json
{
  "error": "Resource not found",
  "message": "The requested post could not be found",
  "status_code": 404,
  "request_id": "req_123abc456def"
}
```

<div class="corgi-card">
  <h3 style="margin-top: 0;">🪵 Request IDs</h3>
  <p>All responses include a <code>X-Request-ID</code> header that can be used to track requests in logs. Include this ID when reporting issues.</p>
</div>

## Next Steps

- Explore specific endpoint documentation:
  - [Timelines API](../endpoints/timelines.md)
  - [Recommendations API](../endpoints/recommendations.md)
  - [Feedback API](../endpoints/feedback.md)
  - [Privacy API](../endpoints/privacy.md)
  - [Proxy API](../endpoints/proxy.md)
- Check out integration examples:
  - [Python Client](../examples/python.md)
  - [Elk Integration](../examples/elk.md)
  - [CLI Tool](../examples/cli.md)