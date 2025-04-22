# Proxy Architecture

The transparent proxy is Corgi's most powerful feature, allowing any standard Mastodon client to benefit from personalized recommendations without any code changes.

## How the Proxy Works

Corgi's proxy middleware sits between your Mastodon client and server, intercepting and enhancing API requests:

<div class="corgi-callout">
  <div class="corgi-callout-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM11 7h2v2h-2V7zm0 4h2v6h-2v-6z"/></svg>
    Interactive Diagrams
  </div>
  <p>All diagrams are interactive! Click on any diagram to view a larger version.</p>
</div>

```mermaid
sequenceDiagram
    autonumber
    participant Client as Mastodon Client<br/>(Elk, Ivory, etc)
    participant Corgi as Corgi Proxy Service
    participant RecEngine as Recommendation<br/>Engine
    participant Instance as Mastodon Instance<br/>(e.g., mastodon.social)
    
    rect rgb(230, 242, 255)
    note right of Client: Timeline Enhancement Flow
    Client->>+Corgi: GET /api/v1/timelines/home<br/>[Authorization: Bearer TOKEN]
    activate Corgi
    
    Corgi->>Corgi: Extract OAuth token
    Corgi->>Corgi: Identify user's instance
    
    Corgi->>+Instance: Forward request<br/>[Authorization: Bearer TOKEN]
    activate Instance
    Instance-->>-Corgi: Return original timeline
    deactivate Instance
    
    Corgi->>+RecEngine: Request recommendations<br/>for user
    activate RecEngine
    RecEngine-->>-Corgi: Return personalized<br/>recommendations
    deactivate RecEngine
    
    Corgi->>Corgi: Blend recommendations<br/>into timeline
    Corgi->>Corgi: Add recommendation<br/>metadata
    
    Corgi-->>-Client: Return enhanced timeline<br/>[X-Corgi-Enhanced: true]
    deactivate Corgi
    end
    
    rect rgb(232, 245, 233)
    note right of Client: Standard Pass-through Flow
    Client->>+Corgi: GET /api/v1/notifications
    activate Corgi
    Corgi->>+Instance: Forward unchanged
    activate Instance
    Instance-->>-Corgi: Return notifications
    deactivate Instance
    Corgi-->>-Client: Pass through unchanged
    deactivate Corgi
    end
    
    rect rgb(255, 243, 224)
    note right of Client: Public Timeline Enhancement (Optional)
    Client->>+Corgi: GET /api/v1/timelines/public?<br/>local=true&enhanced=true
    activate Corgi
    Corgi->>+Instance: GET /api/v1/timelines/public?local=true
    activate Instance
    Instance-->>-Corgi: Return public timeline
    deactivate Instance
    
    Corgi->>+RecEngine: Get trending content<br/>recommendations
    activate RecEngine
    RecEngine-->>-Corgi: Return topic-based<br/>recommendations
    deactivate RecEngine
    
    Corgi->>Corgi: Inject recommendations<br/>if enhanced=true
    Corgi-->>-Client: Return (optionally) enhanced timeline
    deactivate Corgi
    end
    
    style Client fill:#e3f2fd,stroke:#0277bd,color:black
    style Corgi fill:#ffb300,stroke:#ff8f00,color:#000000,font-weight:bold
    style RecEngine fill:#ffecb3,stroke:#ffa000,color:#000000,font-weight:bold
    style Instance fill:#e8f5e9,stroke:#2e7d32,color:black
```

### Key Benefits

1. **Zero client changes** - Works with any Mastodon client
2. **Seamless integration** - Recommendations appear naturally in the timeline
3. **Selective enhancement** - Only modifies timeline endpoints
4. **Preservation of features** - All Mastodon features work normally
5. **Authentication pass-through** - No additional authentication needed

## Instance Resolution

One of the proxy's critical functions is determining which Mastodon instance to forward requests to. Corgi uses a multi-tiered approach:

### Resolution Process

When a request arrives, Corgi determines the target instance in this order:

1. Check for `X-Mastodon-Instance` header
   ```
   X-Mastodon-Instance: mastodon.social
   ```

2. Look for an `instance` query parameter
   ```
   /api/v1/timelines/home?instance=mastodon.social
   ```

3. If authenticated, lookup the user's linked instance in the database
   (Using the OAuth token to find a previously established link)

4. Fall back to the default instance from configuration
   ```
   DEFAULT_MASTODON_INSTANCE = "mastodon.social"
   ```

<div class="corgi-callout">
  <div class="corgi-callout-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM11 7h2v2h-2V7zm0 4h2v6h-2v-6z"/></svg>
    Instance Linking
  </div>
  <p>For best results, users should explicitly link their Mastodon account using the account linking API. This ensures the proxy always forwards to the correct instance.</p>
</div>

## Authentication Handling

The proxy passes through authentication between clients and Mastodon instances:

### OAuth Flow

1. Client sends a request with an OAuth bearer token
   ```
   Authorization: Bearer abc123...
   ```

2. Corgi extracts the token for instance resolution and user identification

3. Corgi forwards the exact same token to the Mastodon instance
   ```
   Authorization: Bearer abc123...
   ```

4. Mastodon accepts the token and processes the request as normal

5. Corgi receives the authenticated response and enhances it if needed

This transparent handling means users don't need separate authentication for Corgi and their Mastodon instance.

## Timeline Enhancement

When processing a home timeline request, Corgi enhances the response with personalized recommendations:

### Enhancement Process

1. Forward the timeline request to the Mastodon instance
2. Receive the original timeline response
3. Fetch personalized recommendations for the user
4. Blend recommendations into the timeline based on the configured ratio
5. Add metadata to identify recommended posts:
   ```json
   {
     "is_recommendation": true,
     "recommendation_reason": "From an author you might like"
   }
   ```
6. Return the enhanced timeline to the client

### Recommendation Headers

Corgi adds custom headers to enhanced responses:

```
X-Corgi-Enhanced: true
X-Corgi-Recommendations: 3
X-Corgi-Recommendation-Score: 0.87
```

These headers allow clients to detect and display information about the enhancements.

## Selective Enhancement

Not all endpoints receive enhancements:

| Endpoint | Enhancement |
|----------|-------------|
| `/api/v1/timelines/home` | ✅ Recommendations blended into timeline |
| `/api/v1/timelines/public` | ✅ Optional enhancement (query param) |
| `/api/v1/timelines/tag/:hashtag` | ✅ Optional enhancement (query param) |
| `/api/v1/timelines/list/:list_id` | ❌ Passed through unchanged |
| `/api/v1/notifications` | ❌ Passed through unchanged |
| All other endpoints | ❌ Passed through unchanged |

## Configuring the Proxy

The proxy can be configured through environment variables:

```bash
# Default Mastodon instance for unlinked users
DEFAULT_MASTODON_INSTANCE=mastodon.social

# Ratio of recommendations to include (0.0-1.0)
RECOMMENDATION_BLEND_RATIO=0.3

# Timeout for proxy requests in seconds
PROXY_TIMEOUT=10

# Enable additional logging
DEBUG_PROXY=true
```

## Client Configuration

To use Corgi with a Mastodon client, you need to point the client to your Corgi instance instead of directly to Mastodon:

### Elk Configuration

```
API Base URL: https://api.corgi-recs.io
Access Token: [your Mastodon access token]
```

### Ivory Configuration

```
Custom Server URL: https://api.corgi-recs.io
Access Token: [your Mastodon access token]
```

### curl Example

```bash
# Standard Mastodon request
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://mastodon.social/api/v1/timelines/home

# Using Corgi proxy
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.corgi-recs.io/api/v1/timelines/home
```

<div class="corgi-card">
  <h3 style="margin-top: 0;">🔗 Account Linking</h3>
  <p>For best results, link your Mastodon account to Corgi before using the proxy:</p>
  <pre><code>curl -X POST "https://api.corgi-recs.io/api/v1/accounts/link" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your_user_id",
    "instance": "mastodon.social",
    "access_token": "YOUR_MASTODON_ACCESS_TOKEN"
  }'</code></pre>
</div>

## Debugging the Proxy

For troubleshooting proxy issues, Corgi provides several debug endpoints:

### Status Endpoint

```bash
curl https://api.corgi-recs.io/api/v1/proxy/status
```

Response:
```json
{
  "status": "ok",
  "proxy": "active",
  "default_instance": "mastodon.social",
  "version": "1.2.0",
  "uptime": "3d 4h 12m"
}
```

### Instance Detection

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.corgi-recs.io/api/v1/proxy/instance
```

Response:
```json
{
  "detected_instance": "mastodon.social",
  "detection_method": "oauth_token_lookup",
  "user_id": "pseudonymized_id_123",
  "headers": {
    "authorization": "[REDACTED]",
    "user-agent": "Elk/1.0"
  }
}
```

### Metrics Endpoint

```bash
curl https://api.corgi-recs.io/api/v1/proxy/metrics
```

Response:
```json
{
  "total_requests": 12483,
  "successful_requests": 12450,
  "failed_requests": 33,
  "timeline_requests": 2841,
  "enriched_timelines": 2418,
  "total_recommendations": 7254,
  "avg_latency_seconds": 0.328,
  "enrichment_rate": 0.851,
  "uptime_seconds": 259243
}
```

## Proxy Limitations

While the proxy is powerful, it has some limitations:

1. **Latency** - Adds a small processing overhead to requests
2. **Rate Limiting** - Counts against your Mastodon instance's rate limits
3. **Instance Support** - Some specialized Mastodon instances may have compatibility issues
4. **Client Compatibility** - Some clients hardcode their instance URL and cannot use the proxy
5. **Trust Requirement** - Users must trust the Corgi instance with their authentication tokens

<div class="corgi-callout">
  <div class="corgi-callout-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM11 7h2v2h-2V7zm0 4h2v6h-2v-6z"/></svg>
    Security Considerations
  </div>
  <p>Because the proxy handles authentication tokens, it's essential to use a trusted Corgi instance. For maximum security, consider self-hosting your own instance.</p>
</div>

## Additional Resources

For more information about the proxy implementation:

- [API Reference: Proxy Endpoints](../endpoints/proxy.md)
- [Example: Elk Integration](../examples/elk.md)
- [Self-hosting Guide](../concepts/self-hosting.md)