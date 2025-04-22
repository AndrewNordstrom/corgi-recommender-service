# Timelines API

The Timelines API provides access to both standard Mastodon timelines and enhanced timelines with personalized recommendations. These endpoints return posts in a Mastodon-compatible format for easy integration with existing clients.

## Endpoints

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/timelines/home</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Retrieves the user's home timeline with seamlessly blended recommendations. For real users, the request is proxied to their Mastodon instance. For test/synthetic users, returns mock data.</p>
    
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
          <td>limit</td>
          <td>integer</td>
          <td>20</td>
          <td>Maximum number of posts to return (max: 40). Example: <code>30</code></td>
        </tr>
        <tr>
          <td>max_id</td>
          <td>string</td>
          <td>null</td>
          <td>Return results older than this ID. Example: <code>109876543211234567</code></td>
        </tr>
        <tr>
          <td>since_id</td>
          <td>string</td>
          <td>null</td>
          <td>Return results newer than this ID. Example: <code>109876543211234567</code></td>
        </tr>
        <tr>
          <td>min_id</td>
          <td>string</td>
          <td>null</td>
          <td>Return results immediately newer than this ID. Example: <code>109876543211234567</code></td>
        </tr>
        <tr>
          <td>instance</td>
          <td>string</td>
          <td>null</td>
          <td>Mastodon instance to proxy the request to (if not using OAuth). Example: <code>mastodon.social</code></td>
        </tr>
      </tbody>
    </table>

    <h4>Code Examples</h4>

    === "curl"

        ```bash
        # Basic usage - get enhanced home timeline
        curl -X GET "https://api.corgi-recs.io/api/v1/timelines/home" \
          -H "Authorization: Bearer YOUR_MASTODON_TOKEN" \
          -H "X-Mastodon-Instance: mastodon.social"

        # With pagination (get older posts)
        curl -X GET "https://api.corgi-recs.io/api/v1/timelines/home?max_id=109876543211234567&limit=30" \
          -H "Authorization: Bearer YOUR_MASTODON_TOKEN" \
          -H "X-Mastodon-Instance: mastodon.social"
        ```

    === "Python"

        ```python
        import requests

        # Basic usage - get enhanced home timeline
        def get_home_timeline(token, instance="mastodon.social", limit=20):
            response = requests.get(
                "https://api.corgi-recs.io/api/v1/timelines/home",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Mastodon-Instance": instance
                },
                params={"limit": limit}
            )
            
            if response.status_code == 200:
                timeline = response.json().get("timeline", [])
                
                # Count recommendations
                recommendations = [post for post in timeline if post.get("is_recommendation")]
                print(f"Timeline contains {len(recommendations)} recommendations out of {len(timeline)} posts")
                
                return timeline
            else:
                print(f"Error: {response.status_code}")
                return None

        # With pagination (get older posts)
        def get_older_posts(token, max_id, instance="mastodon.social", limit=20):
            response = requests.get(
                "https://api.corgi-recs.io/api/v1/timelines/home",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Mastodon-Instance": instance
                },
                params={
                    "max_id": max_id,
                    "limit": limit
                }
            )
            
            return response.json().get("timeline", []) if response.status_code == 200 else None
        ```

    === "JavaScript"

        ```javascript
        // Basic usage - get enhanced home timeline
        async function getHomeTimeline(token, instance = "mastodon.social", limit = 20) {
          const response = await fetch(`https://api.corgi-recs.io/api/v1/timelines/home?limit=${limit}`, {
            headers: {
              "Authorization": `Bearer ${token}`,
              "X-Mastodon-Instance": instance
            }
          });
          
          if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
          }
          
          const data = await response.json();
          const timeline = data.timeline || [];
          
          // Count recommendations
          const recommendationCount = timeline.filter(post => post.is_recommendation).length;
          console.log(`Timeline contains ${recommendationCount} recommendations out of ${timeline.length} posts`);
          
          return timeline;
        }

        // With pagination (get older posts)
        async function getOlderPosts(token, maxId, instance = "mastodon.social", limit = 20) {
          const response = await fetch(
            `https://api.corgi-recs.io/api/v1/timelines/home?max_id=${maxId}&limit=${limit}`, 
            {
              headers: {
                "Authorization": `Bearer ${token}`,
                "X-Mastodon-Instance": instance
              }
            }
          );
          
          return response.ok ? (await response.json()).timeline || [] : null;
        }
        ```
    
    <h4>Response</h4>
    <p>Returns an object with the timeline as a property containing an array of Mastodon-compatible status objects. Recommended posts include additional fields to identify and explain them.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "timeline": [
    {
      "id": "109876543211234567",
      "created_at": "2025-03-15T14:22:11.000Z",
      "in_reply_to_id": null,
      "in_reply_to_account_id": null,
      "sensitive": false,
      "spoiler_text": "",
      "visibility": "public",
      "language": "en",
      "uri": "https://mastodon.social/users/techblogger/statuses/109876543211234567",
      "url": "https://mastodon.social/@techblogger/109876543211234567",
      "replies_count": 12,
      "reblogs_count": 28,
      "favourites_count": 43,
      "content": "<p>Just published a new blog post about sustainable tech!</p>",
      "account": {
        "id": "12345",
        "username": "techblogger",
        "acct": "techblogger@mastodon.social",
        "display_name": "Tech Sustainability Blog",
        "locked": false,
        "bot": false,
        "created_at": "2024-01-15T00:00:00.000Z",
        "note": "<p>Writing about sustainable technology and ethical tech practices.</p>",
        "url": "https://mastodon.social/@techblogger",
        "avatar": "https://files.mastodon.social/accounts/avatars/000/012/345/original/avatar.jpg",
        "avatar_static": "https://files.mastodon.social/accounts/avatars/000/012/345/original/avatar.jpg",
        "header": "https://files.mastodon.social/accounts/headers/000/012/345/original/header.jpg",
        "header_static": "https://files.mastodon.social/accounts/headers/000/012/345/original/header.jpg",
        "followers_count": 1524,
        "following_count": 342,
        "statuses_count": 857,
        "last_status_at": "2025-03-15T00:00:00.000Z",
        "emojis": [],
        "fields": []
      },
      "media_attachments": [],
      "mentions": [],
      "tags": [],
      "emojis": [],
      "card": null,
      "poll": null,
      "is_recommendation": true,
      "recommendation_reason": "From an author you might like"
    },
    {
      "id": "109876987654321123",
      "created_at": "2025-03-15T13:45:22.000Z",
      "content": "<p>Check out our latest open source contribution to the Fediverse!</p>",
      "account": {
        "id": "67890",
        "username": "fediversedev",
        "display_name": "Fediverse Developers",
        "followers_count": 3201,
        "following_count": 129,
        "statuses_count": 1432
        // Additional account fields omitted for brevity
      },
      "is_recommendation": false
      // Additional status fields omitted for brevity
    }
  ]
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/timelines/home/augmented</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Returns the user's home timeline with personalized recommendations explicitly injected. This enhanced timeline blends regular posts with personalized recommendations based on user preferences.</p>
    
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
          <td>User ID for recommendations (inferred from auth token if not provided)</td>
        </tr>
        <tr>
          <td>limit</td>
          <td>integer</td>
          <td>20</td>
          <td>Maximum number of posts to return (max: 40)</td>
        </tr>
        <tr>
          <td>max_id</td>
          <td>string</td>
          <td>null</td>
          <td>Return results older than this ID</td>
        </tr>
        <tr>
          <td>inject_recommendations</td>
          <td>boolean</td>
          <td>false</td>
          <td>Whether to inject personalized recommendations into the timeline</td>
        </tr>
        <tr>
          <td>instance</td>
          <td>string</td>
          <td>null</td>
          <td>Mastodon instance to proxy the request to (if not using OAuth)</td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns an object with the timeline and metadata about the augmentation.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "timeline": [
    {
      "id": "109876543211234567",
      "content": "<p>Just published a new blog post about sustainable tech!</p>",
      "created_at": "2025-03-15T14:22:11.000Z",
      "account": {
        "id": "12345",
        "username": "techblogger",
        "display_name": "Tech Sustainability Blog"
        // Additional account fields omitted for brevity
      },
      "is_recommendation": true,
      "recommendation_reason": "From an author you might like"
      // Additional status fields omitted for brevity
    },
    {
      "id": "109876987654321123",
      "content": "<p>Check out our latest open source contribution to the Fediverse!</p>",
      "created_at": "2025-03-15T13:45:22.000Z",
      "account": {
        "id": "67890",
        "username": "fediversedev",
        "display_name": "Fediverse Developers"
        // Additional account fields omitted for brevity
      },
      "is_recommendation": false
      // Additional status fields omitted for brevity
    }
  ],
  "injected_count": 8
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/recommendations/timelines/recommended</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Returns a timeline consisting entirely of personalized recommendations. This endpoint provides recommendations in a Mastodon-compatible format.</p>
    
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
          <td>User ID to get recommendations for <span class="corgi-param-required">Required</span></td>
        </tr>
        <tr>
          <td>limit</td>
          <td>integer</td>
          <td>20</td>
          <td>Maximum number of recommendations to return (max: 40)</td>
        </tr>
        <tr>
          <td>exclude_seen</td>
          <td>boolean</td>
          <td>true</td>
          <td>Exclude posts the user has already interacted with</td>
        </tr>
        <tr>
          <td>include_reasons</td>
          <td>boolean</td>
          <td>true</td>
          <td>Include recommendation reasons in the response</td>
        </tr>
        <tr>
          <td>languages</td>
          <td>string</td>
          <td>null</td>
          <td>Comma-separated list of language codes to filter by (e.g., "en,es")</td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns an array of Mastodon-compatible status objects with additional recommendation metadata.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">[
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
      // Additional account fields omitted for brevity
    },
    "replies_count": 12,
    "reblogs_count": 28,
    "favourites_count": 43,
    "is_recommendation": true,
    "recommendation_reason": "From an author you might like",
    "ranking_score": 0.87,
    "is_real_mastodon_post": true,
    "is_synthetic": false
    // Additional status fields omitted for brevity
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
      // Additional account fields omitted for brevity
    },
    "is_recommendation": true,
    "recommendation_reason": "Popular with other users",
    "ranking_score": 0.82,
    "is_real_mastodon_post": false,
    "is_synthetic": true
    // Additional status fields omitted for brevity
  }
]</code></pre>
    </div>
  </div>
</div>

## Integration Tips

### Timeline Headers

When using the augmented timeline, look for these response headers:

```
X-Corgi-Proxy: true
X-Corgi-Instance: mastodon.social
X-Corgi-Enhanced: true
X-Corgi-Recommendations: 5
```

These headers indicate that the timeline has been enhanced with recommendations and provide additional metadata.

### Displaying Recommendation Reasons

For recommended posts, display the `recommendation_reason` to help users understand why a post was recommended:

```html
<div class="post">
  <div class="post-content">
    <!-- Post content here -->
  </div>
  
  <div class="recommendation-badge" v-if="post.is_recommendation">
    <span class="reason">{{ post.recommendation_reason }}</span>
  </div>
</div>
```

### Handling Pagination

Timeline pagination follows the Mastodon standard:

```javascript
// Initial request
const timeline = await fetch('/api/v1/timelines/home');
const data = await response.json();

// Pagination using max_id (get older posts)
const olderPosts = await fetch(`/api/v1/timelines/home?max_id=${data.timeline[data.timeline.length-1].id}`);

// Pagination using since_id (for newer posts)
const newerPosts = await fetch(`/api/v1/timelines/home?since_id=${data.timeline[0].id}`);
```

## Example Integration

Here's a complete example of fetching and displaying an augmented timeline:

```javascript
async function fetchAugmentedTimeline(token, instance = "mastodon.social", limit = 20) {
  const response = await fetch(`https://api.corgi-recs.io/api/v1/timelines/home/augmented?limit=${limit}&inject_recommendations=true`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Mastodon-Instance': instance,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error(`Error fetching timeline: ${response.status}`);
  }
  
  const data = await response.json();
  
  // Log enhancement metadata
  const recommendCount = data.injected_count || 0;
  console.log(`Timeline enhanced with ${recommendCount} recommendations`);
  
  return data.timeline;
}

// Render the timeline
async function renderTimeline() {
  const timeline = await fetchAugmentedTimeline('YOUR_TOKEN', 'mastodon.social');
  const timelineElement = document.getElementById('timeline');
  
  timelineElement.innerHTML = '';
  
  timeline.forEach(post => {
    const postElement = document.createElement('div');
    postElement.className = 'post';
    
    // Add recommendation badge if applicable
    if (post.is_recommendation) {
      postElement.classList.add('recommended');
      
      const badge = document.createElement('div');
      badge.className = 'recommendation-badge';
      badge.textContent = post.recommendation_reason || 'Recommended for you';
      postElement.appendChild(badge);
    }
    
    // Add post content
    const content = document.createElement('div');
    content.className = 'content';
    content.innerHTML = post.content;
    postElement.appendChild(content);
    
    // Add author info
    const author = document.createElement('div');
    author.className = 'author';
    author.textContent = post.account.display_name;
    postElement.appendChild(author);
    
    timelineElement.appendChild(postElement);
  });
}

renderTimeline();
```

## Related Resources

- [Recommendations API](recommendations.md) - Get detailed recommendations with metadata
- [Feedback API](feedback.md) - Log user interactions with posts
- [Proxy Endpoints](proxy.md) - Configure and monitor the proxy middleware
- [Elk Integration Guide](../examples/elk.md) - Step-by-step guide for integrating with Elk app
- [Concepts: Timeline Blending](../concepts/recommendations.md#timeline-blending) - Learn how recommendations are blended into timelines