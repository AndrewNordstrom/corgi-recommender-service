# Frequently Asked Questions

## General Questions

### What is Corgi?

Corgi is a privacy-aware recommendation engine for the Fediverse. It works as a middleware layer between any Mastodon client and server, enhancing timelines with personalized recommendations while respecting user privacy.

### Why is it called "Corgi"?

The name reflects our philosophy: **Co**nnected **R**ecommendations for the **G**lobal **I**nternet. Plus, like the dog breed, our service has a small footprint but big impact—portable recommendations that follow you anywhere in the Fediverse.

### Does Corgi work with all Mastodon clients?

Yes! Corgi works with any Mastodon client that allows changing the API base URL. This includes popular clients like Elk, Ivory, Ice Cubes, and many others.

### Is Corgi open source?

Yes, Corgi is fully open source and available on [GitHub](https://github.com/andrewnordstrom/corgi-recommender-service). We welcome contributions from the community.

## Technical Questions

### How does Corgi work?

Corgi operates as a transparent proxy between your Mastodon client and server:

1. You configure your client to connect to Corgi instead of directly to your Mastodon instance
2. Corgi forwards your requests to your Mastodon instance
3. For timeline requests, Corgi enhances the response with personalized recommendations
4. All other requests (posting, notifications, etc.) pass through unchanged

### How does Corgi know what content to recommend?

Corgi builds a preference profile based on your interactions:

- Posts you favorite or bookmark indicate content you like
- Authors whose content you regularly engage with are weighted more heavily
- Content engagement metrics from the wider community are also considered
- Post recency ensures freshness

Corgi combines these factors to deliver personalized recommendations.

### Do I need to create a separate account for Corgi?

No, Corgi works with your existing Mastodon account. You simply point your Mastodon client to Corgi's API URL and use your normal Mastodon authentication.

### How does instance resolution work?

Corgi determines which Mastodon instance to forward requests to using this sequence:

1. `X-Mastodon-Instance` header (if provided by the client)
2. `instance` query parameter (if included in the request)
3. Database lookup based on your OAuth token (if you've linked your account)
4. Default instance from configuration

For best results, you should link your Mastodon account using the account linking API.

### Can I use Corgi with multiple Mastodon accounts?

Yes! Corgi supports multiple linked accounts. Each account will have its own separate preference profile and recommendations.

## Privacy Questions

### What data does Corgi collect?

Corgi offers three privacy levels:

- **Full**: Stores interaction data (favorites, boosts, etc.) with pseudonymized IDs
- **Limited** (default): Stores only aggregated statistics, not individual interactions
- **None**: Minimal data collection with no personalization

You can change your privacy level at any time.

### How is my identity protected?

User IDs are pseudonymized using a SHA-256 hash with a salt before being stored. This means:

- Your real identity is never stored directly
- Different Corgi instances generate different pseudonyms for the same user
- The pseudonym can't be reversed to reveal your identity

### Does Corgi see my authentication tokens?

Yes, since Corgi acts as a proxy, it does see your authentication tokens to forward them to your Mastodon instance. However:

- Tokens are never logged
- Tokens are only stored if you explicitly link your account
- If stored, tokens are encrypted at rest

For maximum security, you can self-host your own Corgi instance.

### Can other users see my recommendations?

No. Your recommendations are completely private and only visible to you.

### Can I delete my data?

Yes, you can delete all your data at any time using the Privacy API:

```bash
curl -X DELETE "https://api.corgi-recs.io/api/v1/privacy/data?user_id=your_user_id&confirm=true" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Integration Questions

### How do I integrate Corgi with my Mastodon client?

For most clients, you simply change the API base URL in the settings:

1. Find the server/API URL setting in your client
2. Change it from your Mastodon instance (e.g., `https://mastodon.social`) to Corgi's URL (e.g., `https://api.corgi-recs.io`)
3. Keep your existing Mastodon access token

Check our [Examples](examples/elk.md) section for client-specific guides.

### Can I integrate Corgi directly into my application?

Yes! Besides the proxy approach, you can use Corgi's direct API endpoints:

- For recommendations: `/api/v1/recommendations`
- For logging interactions: `/api/v1/interactions`

See the [API Reference](api/overview.md) for detailed documentation.

### How can I tell which posts are recommendations?

Recommended posts include these additional fields:

```json
{
  "is_recommendation": true,
  "recommendation_reason": "From an author you might like",
  "ranking_score": 0.87
}
```

You can use these fields to display recommendation badges or other UI elements.

### What's the difference between the proxy and direct API integration?

- **Proxy Integration**: Works with any Mastodon client without code changes
- **Direct API Integration**: Requires custom development but provides more control

The proxy is ideal for existing clients, while the direct API is better for custom applications.

## Self-Hosting Questions

### Can I self-host Corgi?

Yes! Corgi is designed to be easily self-hosted. You'll need:

- A server with Docker support
- PostgreSQL database
- Internet connectivity

See our [Self-hosting Guide](concepts/self-hosting.md) for detailed instructions.

### How much server resources does Corgi need?

Corgi is fairly lightweight:

- For personal use: A small VPS with 1 CPU and 1GB RAM is sufficient
- For small communities: 2 CPUs and 2GB RAM recommended
- For larger deployments: Scale as needed, with particular attention to database performance

### Can I contribute to Corgi's development?

Absolutely! We welcome contributions:

- Code contributions via pull requests
- Bug reports and feature requests via issues
- Documentation improvements
- Translations

Visit our [GitHub repository](https://github.com/andrewnordstrom/corgi-recommender-service) to get started.

## Performance Questions

### Will Corgi slow down my Mastodon experience?

Corgi adds a small amount of latency (typically 50-200ms) as requests pass through the proxy. For most users, this is barely noticeable. Timeline enhancements are done asynchronously to minimize delay.

### How does Corgi handle rate limits?

Corgi respects Mastodon's rate limits and will forward any rate-limiting headers from your instance. If you're using Corgi with multiple clients, be aware that all requests count against your instance's rate limits.

### What happens if Corgi goes down?

If Corgi becomes unavailable, you can simply reconfigure your client to connect directly to your Mastodon instance again. No data will be lost, and you can reconnect to Corgi when it's available again.

<div class="corgi-callout">
  <div class="corgi-callout-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16zm-1-5h2v2h-2v-2zm2-1.645V14h-2v-1.5a1 1 0 0 1 1-1 1.5 1.5 0 1 0-1.471-1.794l-1.962-.393A3.501 3.501 0 1 1 13 13.355z"/></svg>
    Have a question not answered here?
  </div>
  <p>You can reach us through <a href="https://github.com/andrewnordstrom/corgi-recommender-service/issues">GitHub issues</a> or email us at support@corgi-recs.io</p>
</div>