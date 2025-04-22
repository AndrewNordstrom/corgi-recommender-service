# Quickstart Guide

This guide will help you get started with Corgi in minutes, whether you want to use our hosted service or run your own instance.

## API Key Setup

To use Corgi, you'll need an API key for authentication.

<div class="corgi-card">
  <h3 style="margin-top: 0;">✨ Get Your API Key</h3>
  
  <p>Visit <a href="https://dashboard.corgi-recs.io/signup">dashboard.corgi-recs.io/signup</a> to create an account and generate your API key.</p>
  
  <p>You'll receive a key in this format:</p>
  <pre><code>corgi_sk_3f17abd92ec68f1ce86543290a1dc2a2ff</code></pre>
  
  <p><em>Keep this key secure! It provides access to your recommendation data.</em></p>
</div>

## Quick Example: Get Recommendations

Here's a simple example of how to retrieve personalized recommendations using Corgi:

=== "curl"

    ```bash
    curl -X GET "https://api.corgi-recs.io/api/v1/timelines/recommended?user_id=your_user_id" \
      -H "Authorization: Bearer YOUR_API_KEY" \
      -H "Content-Type: application/json"
    ```

=== "Python"

    ```python
    import requests
    
    api_key = "YOUR_API_KEY"
    user_id = "your_user_id"
    
    url = f"https://api.corgi-recs.io/api/v1/timelines/recommended?user_id={user_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    recommendations = response.json()
    
    # Print the recommendations
    for post in recommendations:
        print(f"- {post['account']['display_name']}: {post['content'][:50]}...")
    ```

### Example Response

<div class="corgi-response-example">
  <div class="corgi-response-example-header">JSON Response</div>
  <pre><code class="language-json">{
  "timeline": [
    {
      "id": "109876543211234567",
      "content": "<p>Just published a new blog post about sustainable tech!</p>",
      "created_at": "2025-03-15T14:22:11.000Z",
      "account": {
        "id": "12345",
        "username": "techblogger",
        "display_name": "Tech Sustainability Blog",
        "followers_count": 1524,
        "following_count": 342,
        "statuses_count": 857
      },
      "replies_count": 12,
      "reblogs_count": 28,
      "favourites_count": 43,
      "is_recommendation": true,
      "recommendation_reason": "From an author you might like"
    },
    {
      "id": "109876987654321123",
      "content": "<p>Check out our latest open source contribution to the Fediverse!</p>",
      "created_at": "2025-03-15T13:45:22.000Z",
      "account": {
        "id": "67890",
        "username": "fediversedev",
        "display_name": "Fediverse Developers",
        "followers_count": 3201,
        "following_count": 129,
        "statuses_count": 1432
      },
      "replies_count": 7,
      "reblogs_count": 41,
      "favourites_count": 62,
      "is_recommendation": true,
      "recommendation_reason": "Popular with other users"
    }
  ]
}</code></pre>
</div>

## Transparent Proxy Setup

For the fullest Corgi experience, set up the transparent proxy to enhance any Mastodon client:

### 1. Connect Your Mastodon Account

Link your Mastodon account to Corgi:

```bash
curl -X POST "https://api.corgi-recs.io/api/v1/accounts/link" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your_user_id",
    "instance": "mastodon.social",
    "access_token": "YOUR_MASTODON_ACCESS_TOKEN"
  }'
```

### 2. Configure Your Mastodon Client

Update your client to use Corgi as a proxy:

=== "Elk App"

    In Elk's settings page:
    
    1. Go to "Advanced Settings"
    2. Change "API Base URL" to: `https://api.corgi-recs.io`
    3. Keep your existing Mastodon access token

=== "Other Clients"

    For other clients that allow custom API endpoints:
    
    1. Find the API or server settings
    2. Replace your instance URL with: `https://api.corgi-recs.io`
    3. Keep your existing access token

<div class="corgi-callout">
  <div class="corgi-callout-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16zm-1-5h2v2h-2v-2zm2-1.645V14h-2v-1.5a1 1 0 0 1 1-1 1.5 1.5 0 1 0-1.471-1.794l-1.962-.393A3.501 3.501 0 1 1 13 13.355z"/></svg>
    What happens behind the scenes
  </div>
  <p>When configured as a proxy, Corgi intercepts timeline requests, fetches the original timeline from your Mastodon instance, and then enhances it with personalized recommendations before sending it back to your client.</p>
  <p>All other API requests (posting, notifications, etc.) are passed through unchanged.</p>
</div>

## Logging Interactions Manually

If you're building a custom client or can't use the proxy, you can manually log interactions:

```python
import requests

api_key = "YOUR_API_KEY"
user_id = "your_user_id"

url = "https://api.corgi-recs.io/api/v1/interactions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
data = {
    "user_alias": user_id,
    "post_id": "post_67890",
    "action_type": "favorite",
    "context": {
        "source": "timeline_home"
    }
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

## Self-hosting Corgi

Want to run your own Corgi instance? It's easy with Docker:

```bash
# Clone the repository
git clone https://github.com/andrewnordstrom/corgi-recommender-service.git
cd corgi-recommender-service

# Start with Docker Compose
docker-compose up -d
```

For detailed self-hosting instructions, including database setup and configuration options, see our [Self-hosting Guide](concepts/self-hosting.md).

## Next Steps

Now that you have Corgi up and running, check out these resources:

- [Core Concepts](concepts.md) - Learn how Corgi works under the hood
- [API Reference](api/overview.md) - Explore the full API
- [Privacy Design](concepts/privacy.md) - Understand how Corgi protects user data
- [Integration Examples](examples/elk.md) - See detailed client integration guides