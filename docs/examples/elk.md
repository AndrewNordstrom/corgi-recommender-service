# Elk Integration Guide

This guide walks you through integrating Corgi with [Elk](https://elk.zone), a popular Mastodon web client. Elk is a great choice for Corgi integration because it allows custom API endpoints.

## Overview

Integrating Corgi with Elk involves:

1. Setting up an Elk account connected to your Mastodon instance
2. Changing Elk's API URL to point to Corgi
3. Linking your Mastodon account to Corgi for proper instance resolution
4. Enjoying enhanced timelines with personalized recommendations

## Step-by-Step Integration

### 1. Create or Access Your Elk Account

If you don't already have an Elk account:

1. Visit [elk.zone](https://elk.zone)
2. Click "Sign in"
3. Enter your Mastodon instance (e.g., `mastodon.social`)
4. Complete the authentication process

If you already have an Elk account, simply sign in.

### 2. Obtain Your Mastodon Access Token

You'll need your Mastodon access token to link your account with Corgi:

1. In Elk, click on your profile picture in the bottom left
2. Select "Settings"
3. Scroll down to "Advanced"
4. Find your access token (it looks like `abc123def456ghi789`)
5. Copy this token for the next step

<div class="corgi-callout">
  <div class="corgi-callout-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM11 7h2v2h-2V7zm0 4h2v6h-2v-6z"/></svg>
    Security Note
  </div>
  <p>Your access token is sensitive information. Never share it publicly and be careful with how you store it.</p>
</div>

### 3. Link Your Mastodon Account to Corgi

Before changing Elk's settings, link your Mastodon account to Corgi using our provided tool:

```bash
# Link a user to a Mastodon instance
./tools/link_user.py --user-id your_user_id --instance mastodon.social --token "YOUR_MASTODON_ACCESS_TOKEN"
```

Replace:
- `your_user_id` with your Corgi user ID
- `mastodon.social` with your actual Mastodon instance
- `YOUR_MASTODON_ACCESS_TOKEN` with the token you copied in step 2

Alternatively, you can use the API directly:

```bash
curl -X POST "https://api.corgi-recs.io/api/v1/proxy/accounts/link" \
  -H "Authorization: Bearer YOUR_CORGI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your_user_id",
    "instance": "mastodon.social",
    "access_token": "YOUR_MASTODON_ACCESS_TOKEN"
  }'
```

A successful response looks like:

```json
{
  "status": "ok",
  "user_id": "your_user_id",
  "instance": "https://mastodon.social",
  "username": "@yourusername",
  "message": "Account successfully linked"
}
```

### 4. Configure Elk to Use Corgi

Now change Elk's API URL:

1. In Elk, click on your profile picture in the bottom left
2. Select "Settings"
3. Scroll down to "Advanced"
4. Change "API URL" from your Mastodon instance to:
   ```
   https://api.corgi-recs.io
   ```
5. Leave the access token unchanged
6. Click "Save"
7. Refresh the page

<div class="corgi-card">
  <h3 style="margin-top: 0;">📸 Screenshot Example</h3>
  <p>Here's what the Elk settings should look like after configuration:</p>
  <img src="../../assets/elk-settings-example.png" alt="Elk Settings Example" style="max-width: 100%; border-radius: 8px; border: 1px solid #ddd;" />
</div>

### 5. Verify the Integration

To check that Corgi is working correctly:

1. Visit your home timeline in Elk
2. Look for recommendations with reason badges
3. Favorite or boost some posts to start building your preference profile
4. Refresh after a few interactions to see updated recommendations

## Understanding Recommendations in Elk

When browsing your timeline, you'll notice recommendations are seamlessly integrated with regular posts. They include a small badge indicating why they were recommended:

![Recommendation Badge Example](../assets/recommendation-badge.png)

Common recommendation reasons include:
- "From an author you might like"
- "Popular with other users"
- "Recently posted"

As you interact with more content, recommendations will improve based on your preferences.

## Customizing the Experience

### Using Augmented Timeline

For the most control over recommendation injection, use the augmented timeline endpoint:

```bash
curl "https://api.corgi-recs.io/api/v1/timelines/home/augmented?inject_recommendations=true" \
  -H "Authorization: Bearer YOUR_MASTODON_TOKEN" \
  -H "X-Mastodon-Instance: mastodon.social"
```

By explicitly setting `inject_recommendations=true`, you control when recommendations are included.

### Adjusting Server Configuration

If you're running your own Corgi instance, you can configure the recommendation ratio in the environment:

```bash
# In your .env file or environment variables
RECOMMENDATION_BLEND_RATIO=0.4
```

Or using the command line when starting the server:

```bash
./run_server.py --no-ssl --debug-cors
```

The `--debug-cors` flag is useful during development to allow requests from localhost clients.

### Updating Privacy Settings

To change how much data Corgi collects:

```bash
curl -X POST "https://api.corgi-recs.io/api/v1/privacy" \
  -H "Authorization: Bearer YOUR_CORGI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your_user_id",
    "tracking_level": "limited"
  }'
```

Available tracking levels:
- `full`: Maximum personalization (stores all interactions)
- `limited`: Balanced approach (stores aggregate data only)
- `none`: Maximum privacy (no personalization)

## Troubleshooting

### Timeline Not Loading

If your timeline doesn't load after switching to Corgi:

1. Check that you entered the correct API URL (`https://api.corgi-recs.io`)
2. Verify that your account is properly linked using the `tools/link_user.py` script
3. Ensure that the Corgi server is running with the correct SSL setup (try with `--no-ssl` during development)
4. Try clearing your browser cache and refreshing
5. Check the logs at `logs/proxy.log` for detailed error information
6. If problems persist, temporarily switch back to your direct Mastodon instance URL

### No Recommendations Appearing

If you don't see any recommendations:

1. Check if recommendations are explicitly enabled with `inject_recommendations=true` in the augmented timeline
2. Verify your privacy settings - if set to `none`, no recommendations will be shown
3. Try using the `/api/v1/recommendations/timelines/recommended` endpoint directly to check if recommendations are being generated
4. Check that your instance is properly detected using the `/api/v1/proxy/instance` endpoint
5. Give it some time - recommendations appear after you've interacted with some content

### Performance Issues

If you notice slow performance:

1. Check the proxy metrics with `curl http://localhost:5002/api/v1/proxy/metrics`
2. Consider increasing the `PROXY_TIMEOUT` if your Mastodon instance is slow to respond
3. Verify that your Mastodon instance is responsive
4. Try running the server without SSL in development (`--no-ssl` flag)
5. Check the logs for timeout or connection errors
6. For development environments, ensure CORS is properly configured with `--debug-cors`

## Reverting to Direct Mastodon Connection

If you want to disable Corgi and connect directly to Mastodon again:

1. In Elk, click on your profile picture in the bottom left
2. Select "Settings"
3. Scroll down to "Advanced"
4. Change "API URL" back to your Mastodon instance URL (e.g., `https://mastodon.social`)
5. Click "Save"
6. Refresh the page

## Alternative Clients

While this guide focuses on Elk, similar steps apply to other Mastodon clients:

- **Ivory**: Settings → Advanced → Custom Server
- **Ice Cubes**: Settings → Accounts → Edit → Advanced → Custom API Base URL
- **Toot!**: Settings → Advanced → API URL

## Next Steps

- Try the [Python Client Example](python.md) for direct API integration
- Learn about [building a CLI tool](cli.md) with Corgi
- Explore the [Recommendation Engine](../concepts/recommendations.md) to understand how it works