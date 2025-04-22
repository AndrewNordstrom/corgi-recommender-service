# Proxy API

The Proxy API provides endpoints for monitoring and configuring Corgi's transparent proxy functionality. These endpoints help you understand how the proxy is working and troubleshoot any issues.

## Endpoints

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/proxy/status</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Returns the current status of the proxy service.</p>
    
    <h4>Response</h4>
    <p>Returns basic information about the proxy's status and configuration.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "status": "ok",
  "proxy": "active",
  "default_instance": "https://mastodon.social",
  "version": "1.2.0",
  "uptime": "3d 4h 12m",
  "recommendation_blend_ratio": 0.3,
  "proxy_timeout": 10
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/proxy/instance</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Shows what Mastodon instance would be detected for the current request. This is useful for debugging instance resolution issues.</p>
    
    <h4>Response</h4>
    <p>Returns information about the detected instance and how it was determined.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "detected_instance": "https://mastodon.social",
  "detection_method": "oauth_token_lookup",
  "user_id": "pseudonymized_id_123",
  "headers": {
    "authorization": "[REDACTED]",
    "user-agent": "Elk/1.0"
  },
  "args": {
    "limit": "20"
  }
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/proxy/metrics</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Returns metrics about proxy usage and performance.</p>
    
    <h4>Query Parameters</h4>
    <table class="corgi-param-table">
      <thead>
        <tr>
          <th>Parameter</th>
          <th>Type</th>
          <th>Default</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>reset</td>
          <td>string</td>
          <td>"false"</td>
          <td>If "true", resets metrics after retrieval</td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns detailed metrics about proxy usage.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "total_requests": 12483,
  "successful_requests": 12450,
  "failed_requests": 33,
  "timeline_requests": 2841,
  "enriched_timelines": 2418,
  "total_recommendations": 7254,
  "avg_latency_seconds": 0.328,
  "enrichment_rate": 0.851,
  "uptime_seconds": 259243,
  "instance_distribution": {
    "mastodon.social": 7890,
    "fosstodon.org": 2145,
    "hachyderm.io": 1203,
    "other": 1245
  },
  "recent_errors": [
    {
      "timestamp": "2025-03-15T15:23:45.000Z",
      "path": "/api/v1/timelines/home",
      "status_code": 500,
      "error": "Timeout connecting to instance",
      "instance": "slow.instance.example"
    }
  ]
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method post">POST</span>
    <span class="corgi-endpoint-path">/api/v1/proxy/accounts/link</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Links a user's Mastodon account to Corgi for instance resolution.</p>
    
    <h4>Request Body</h4>
    <table class="corgi-param-table">
      <thead>
        <tr>
          <th>Parameter</th>
          <th>Type</th>
          <th>Required</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>user_id</td>
          <td>string</td>
          <td><span class="corgi-param-required">Required</span></td>
          <td>User ID to link the account for</td>
        </tr>
        <tr>
          <td>instance</td>
          <td>string</td>
          <td><span class="corgi-param-required">Required</span></td>
          <td>Mastodon instance URL (e.g., "mastodon.social")</td>
        </tr>
        <tr>
          <td>access_token</td>
          <td>string</td>
          <td><span class="corgi-param-required">Required</span></td>
          <td>OAuth access token for the Mastodon account</td>
        </tr>
      </tbody>
    </table>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Request</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "instance": "mastodon.social",
  "access_token": "abc123def456ghi789"
}</code></pre>
    </div>
    
    <h4>Response</h4>
    <p>Returns confirmation of the account linking.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "status": "ok",
  "user_id": "user_12345",
  "instance": "https://mastodon.social",
  "username": "@user",
  "message": "Account successfully linked"
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/proxy/accounts</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Lists all linked accounts for a user.</p>
    
    <h4>Query Parameters</h4>
    <table class="corgi-param-table">
      <thead>
        <tr>
          <th>Parameter</th>
          <th>Type</th>
          <th>Default</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>user_id</td>
          <td>string</td>
          <td>null</td>
          <td>The user ID to list accounts for <span class="corgi-param-required">Required</span></td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns the list of linked Mastodon accounts.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "linked_accounts": [
    {
      "instance": "https://mastodon.social",
      "username": "@user",
      "linked_at": "2025-02-15T10:30:00.000Z",
      "last_used": "2025-03-15T14:22:11.000Z"
    },
    {
      "instance": "https://fosstodon.org",
      "username": "@user",
      "linked_at": "2025-03-01T08:15:00.000Z",
      "last_used": "2025-03-10T09:45:00.000Z"
    }
  ]
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method delete">DELETE</span>
    <span class="corgi-endpoint-path">/api/v1/proxy/accounts/unlink</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Unlinks a Mastodon account from Corgi.</p>
    
    <h4>Request Body</h4>
    <table class="corgi-param-table">
      <thead>
        <tr>
          <th>Parameter</th>
          <th>Type</th>
          <th>Required</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>user_id</td>
          <td>string</td>
          <td><span class="corgi-param-required">Required</span></td>
          <td>User ID to unlink the account for</td>
        </tr>
        <tr>
          <td>instance</td>
          <td>string</td>
          <td><span class="corgi-param-required">Required</span></td>
          <td>Mastodon instance URL to unlink</td>
        </tr>
      </tbody>
    </table>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Request</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "instance": "mastodon.social"
}</code></pre>
    </div>
    
    <h4>Response</h4>
    <p>Returns confirmation of the account unlinking.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "status": "ok",
  "message": "Account successfully unlinked",
  "user_id": "user_12345",
  "instance": "https://mastodon.social"
}</code></pre>
    </div>
  </div>
</div>

## Instance Resolution

The proxy determines which Mastodon instance to forward requests to using this sequence:

1. `X-Mastodon-Instance` header in the request
   ```
   X-Mastodon-Instance: mastodon.social
   ```

2. `instance` query parameter 
   ```
   ?instance=mastodon.social
   ```

3. Database lookup based on the OAuth token (using account linking)

4. Default instance from configuration
   ```
   DEFAULT_MASTODON_INSTANCE = "mastodon.social"
   ```

<div class="corgi-callout">
  <div class="corgi-callout-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM11 7h2v2h-2V7zm0 4h2v6h-2v-6z"/></svg>
    Best Practice
  </div>
  <p>For reliable instance resolution, users should be encouraged to link their Mastodon accounts using the <code>/api/v1/proxy/accounts/link</code> endpoint. This ensures the proxy always forwards to the correct instance, even when using multiple Mastodon clients.</p>
</div>

## Configuration

### Environment Variables

The proxy's behavior can be configured through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEFAULT_MASTODON_INSTANCE` | Fallback Mastodon instance URL | https://mastodon.social |
| `RECOMMENDATION_BLEND_RATIO` | Ratio of recommendations to include (0.0-1.0) | 0.3 |
| `PROXY_TIMEOUT` | Timeout for proxy requests in seconds | 10 |
| `DEBUG_PROXY` | Enable additional logging | false |

### Configuration API

You can also adjust some settings through the API:

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method post">POST</span>
    <span class="corgi-endpoint-path">/api/v1/proxy/config</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Update proxy configuration settings.</p>
    
    <h4>Request Body</h4>
    <table class="corgi-param-table">
      <thead>
        <tr>
          <th>Parameter</th>
          <th>Type</th>
          <th>Required</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>recommendation_blend_ratio</td>
          <td>float</td>
          <td>Optional</td>
          <td>Ratio of recommendations to include (0.0-1.0)</td>
        </tr>
        <tr>
          <td>proxy_timeout</td>
          <td>integer</td>
          <td>Optional</td>
          <td>Timeout for proxy requests in seconds</td>
        </tr>
        <tr>
          <td>default_instance</td>
          <td>string</td>
          <td>Optional</td>
          <td>Default Mastodon instance URL</td>
        </tr>
      </tbody>
    </table>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Request</div>
      <pre><code class="language-json">{
  "recommendation_blend_ratio": 0.4,
  "proxy_timeout": 15
}</code></pre>
    </div>
    
    <h4>Response</h4>
    <p>Returns the updated configuration.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "status": "ok",
  "config": {
    "recommendation_blend_ratio": 0.4,
    "proxy_timeout": 15,
    "default_instance": "https://mastodon.social"
  }
}</code></pre>
    </div>
  </div>
</div>

## Testing the Proxy

You can test the proxy using `curl`:

```bash
# Test proxy status
curl -i http://localhost:5000/api/v1/proxy/status

# Test instance detection
curl -i -H "X-Mastodon-Instance: mastodon.social" http://localhost:5000/api/v1/proxy/instance

# Test timeline (will be anonymous without auth)
curl -i -H "X-Mastodon-Instance: mastodon.social" http://localhost:5000/api/v1/timelines/home

# Test timeline with auth token
curl -i -H "Authorization: Bearer YOUR_TOKEN" -H "X-Mastodon-Instance: mastodon.social" http://localhost:5000/api/v1/timelines/home

# Check proxy metrics
curl -i http://localhost:5000/api/v1/proxy/metrics
```

## Debugging Tips

### Common Issues

1. **Instance Not Detected**: If the instance isn't being properly detected, check that:
   - The `X-Mastodon-Instance` header is correctly formatted (no `https://` prefix)
   - The account is properly linked using the `/api/v1/proxy/accounts/link` endpoint
   - The OAuth token is valid and properly formatted

2. **Authentication Failures**: If authentication is failing:
   - Verify the token is valid for the intended instance
   - Check that the token has the necessary scopes (usually `read:statuses`)
   - Ensure the instance URL is correct

3. **Timeout Errors**: If requests are timing out:
   - Check the instance's health
   - Increase the `PROXY_TIMEOUT` setting
   - Verify network connectivity

### Proxy Headers

The proxy adds these headers to responses:

```
X-Corgi-Proxy: true
X-Corgi-Instance: mastodon.social
X-Corgi-Enhanced: true (for enhanced timelines)
X-Corgi-Recommendations: 5 (number of recommendations added)
```

These headers can help you debug issues by showing whether a request passed through the proxy and what enhancements were made.

## Client Configuration

### Configuring Elk

```javascript
// In Elk's settings.js
export default {
  apiUrl: 'https://api.corgi-recs.io',  // Use Corgi proxy URL
  token: 'YOUR_MASTODON_TOKEN',         // Your normal Mastodon token
  instance: 'mastodon.social'           // Your Mastodon instance
}
```

### Configuring Ivory

In Ivory's Settings:
1. Go to "Advanced" > "Custom Server"
2. Enter `https://api.corgi-recs.io` as the server URL
3. Keep your existing Mastodon access token

## Related Resources

- [Timelines API](timelines.md) - Get enhanced timelines with recommendations
- [Concepts: Proxy Architecture](../concepts/proxy.md) - Learn how the proxy works in detail
- [Example: Elk Integration](../examples/elk.md) - Step-by-step guide for Elk