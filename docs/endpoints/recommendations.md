# Recommendations API

The Recommendations API provides access to Corgi's personalized content suggestions. These endpoints allow you to retrieve tailored recommendations based on user preferences and behavior.

## Endpoints

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/recommendations</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Get personalized recommendations for a user with detailed metadata.</p>
    
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
          <td>The user ID to get recommendations for <span class="corgi-param-required">Required</span></td>
        </tr>
        <tr>
          <td>limit</td>
          <td>integer</td>
          <td>10</td>
          <td>Maximum number of recommendations to return (max: 40)</td>
        </tr>
        <tr>
          <td>exclude_seen</td>
          <td>boolean</td>
          <td>true</td>
          <td>Exclude posts the user has already interacted with</td>
        </tr>
        <tr>
          <td>debug</td>
          <td>boolean</td>
          <td>false</td>
          <td>Include detailed scoring information in response</td>
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
    <p>Returns an object with user_id, recommendations, and optional debug info.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "recommendations": [
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
      "ranking_score": 0.87,
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
      "ranking_score": 0.82,
      "recommendation_reason": "Popular with other users"
    }
  ],
  "debug_info": {
    "user_interactions_count": 47,
    "candidates_evaluated": 183,
    "factor_weights": {
      "author_preference": 0.4,
      "content_engagement": 0.3,
      "recency": 0.3
    },
    "score_distribution": {
      "min": 0.12,
      "max": 0.91,
      "mean": 0.42,
      "median": 0.37
    }
  }
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method post">POST</span>
    <span class="corgi-endpoint-path">/api/v1/recommendations/generate</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Generate fresh personalized rankings for a user. This is useful when you want to force a refresh of recommendations or generate initial recommendations for a new user.</p>
    
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
          <td>The user ID to generate rankings for</td>
        </tr>
        <tr>
          <td>force_refresh</td>
          <td>boolean</td>
          <td>Optional</td>
          <td>Force recalculation even if recent rankings exist (default: false)</td>
        </tr>
      </tbody>
    </table>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Request</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "force_refresh": true
}</code></pre>
    </div>
    
    <h4>Response</h4>
    <p>Returns a confirmation with the number of rankings generated.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response (New Rankings)</div>
      <pre><code class="language-json">{
  "message": "New rankings generated",
  "count": 42,
  "status_code": 201
}</code></pre>
    </div>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response (Using Existing Rankings)</div>
      <pre><code class="language-json">{
  "message": "Using existing rankings (less than 1 hour old)",
  "count": 38,
  "status_code": 200
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/recommendations/real-posts</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Get only real Mastodon posts without any synthetic or recommended content. This is useful for getting a baseline of genuine Mastodon content.</p>
    
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
          <td>Maximum number of posts to return</td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns an object with real Mastodon posts.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "posts": [
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
      "is_real_mastodon_post": true,
      "is_synthetic": false
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
      "is_real_mastodon_post": true,
      "is_synthetic": false
    }
  ],
  "count": 2,
  "message": "Retrieved 2 real Mastodon posts"
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/recommendations/reasons</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Get detailed explanations for why specific posts were recommended to a user. This is useful for transparency and helping users understand their recommendations.</p>
    
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
          <td>The user ID to get recommendation reasoning for <span class="corgi-param-required">Required</span></td>
        </tr>
        <tr>
          <td>post_id</td>
          <td>string</td>
          <td>null</td>
          <td>The post ID to get reasoning for (if omitted, returns reasons for recent recommendations)</td>
        </tr>
        <tr>
          <td>limit</td>
          <td>integer</td>
          <td>10</td>
          <td>Maximum number of recommendation reasons to return</td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns detailed reasoning for recommendations.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "reasons": [
    {
      "post_id": "109876543211234567",
      "author_id": "12345",
      "author_name": "techblogger",
      "ranking_score": 0.87,
      "short_reason": "From an author you might like",
      "detailed_reason": "You've favorited 3 posts from this author in the past week",
      "scores": {
        "author_preference": 0.92,
        "content_engagement": 0.76,
        "recency": 0.85
      }
    },
    {
      "post_id": "109876987654321123",
      "author_id": "67890",
      "author_name": "fediversedev",
      "ranking_score": 0.82,
      "short_reason": "Popular with other users",
      "detailed_reason": "This post has received significant engagement from the community",
      "scores": {
        "author_preference": 0.31,
        "content_engagement": 0.95,
        "recency": 0.80
      }
    }
  ]
}</code></pre>
    </div>
  </div>
</div>

## Understanding Recommendation Reasons

Each recommended post includes a human-readable explanation for why it's being shown. These explanations are also available in the `injection_metadata.explanation` field when posts are injected into timelines:

| Reason | Description | Primary Factor |
|--------|-------------|----------------|
| "From an author you might like" | The user has shown interest in content from this author | Author preference |
| "Popular with other users" | The post has received significant engagement | Content engagement |
| "Recently posted" | The content is fresh and timely | Recency |
| "Recommended for you" | Multiple factors contributed equally | Mixed factors |
| "Suggested based on your interests in #tags" | Content matches user's hashtag interests | Tag matching |

## Recommendation Scoring

The recommendation engine calculates scores based on these factors:

### Author Preference (40%)

Measures how much a user interacts with content from specific authors:

```python
def get_author_preference_score(user_interactions, author_id):
    # Count positive and negative interactions with author's content
    # Calculate positive ratio (positive interactions / total interactions)
    # Apply sigmoid function to normalize to 0-1 range
    positive_ratio = author_interactions['positive'] / (author_interactions['total'] + 0.001)
    preference_score = 1 / (1 + math.exp(-5 * (positive_ratio - 0.5)))
    return max(preference_score, 0.1)  # Minimum score is 0.1
```

### Content Engagement (30%)

Evaluates the post's overall popularity:

```python
def get_content_engagement_score(post):
    # Sum favorites, reblogs, and replies
    total = favorites + reblogs + replies
    # Apply logarithmic scaling to prevent very popular posts from dominating
    return math.log(total + 1) / 10.0  # Normalize to 0-1 range
```

### Recency (30%)

Measures how fresh the content is:

```python
def get_recency_score(post):
    # Calculate age in days
    age_days = (now - post['created_at']).total_seconds() / (24 * 3600)
    # Apply exponential decay
    recency_score = math.exp(-age_days / decay_factor)
    return max(recency_score, 0.2)  # Minimum score for older posts
```

## Debugging Recommendations

When using the recommendations endpoint with `debug=true`, you'll receive additional information about how recommendations were generated:

```json
"debug_info": {
  "user_interactions_count": 47,
  "candidates_evaluated": 183,
  "processing_time_ms": 145,
  "factor_weights": {
    "author_preference": 0.4,
    "content_engagement": 0.3,
    "recency": 0.3
  },
  "score_distribution": {
    "min": 0.12,
    "max": 0.91,
    "mean": 0.42,
    "median": 0.37
  },
  "factors": {
    "109876543211234567": {
      "author_preference": 0.92,
      "content_engagement": 0.76,
      "recency": 0.85
    }
  }
}
```

This information is valuable for:
- Understanding why certain posts are recommended
- Diagnosing issues with recommendation quality
- Testing and tuning the recommendation algorithm

## Personalization Controls

The recommendations API respects user privacy settings:

- For users with `full` tracking, recommendations are fully personalized
- For users with `limited` tracking, recommendations use aggregated preferences
- For users with `none` tracking, no personalized recommendations are provided

<div class="corgi-callout">
  <div class="corgi-callout-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM11 7h2v2h-2V7zm0 4h2v6h-2v-6z"/></svg>
    User Consent
  </div>
  <p>Always respect user privacy preferences and make it clear when content is being recommended.</p>
</div>

## Filtering Recommendations

The API provides several ways to filter recommendations:

### Language Filtering

```
/api/v1/recommendations?user_id=user_12345&languages=en,es
```

This returns only recommendations in English and Spanish.

### Sensitive Content Filtering

```
/api/v1/recommendations?user_id=user_12345&hide_sensitive=true
```

This filters out posts marked as sensitive.

### Author Diversity

```
/api/v1/recommendations?user_id=user_12345&author_diversity=0.7
```

This controls how diverse the set of authors is in the recommendations (higher values = more diverse).

## Client Integration Example

Here's an example of fetching and displaying recommendations in a client application:

```javascript
async function fetchRecommendations(userId, limit = 10) {
  const response = await fetch(`https://api.corgi-recs.io/api/v1/recommendations?user_id=${userId}&limit=${limit}`, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error(`Error fetching recommendations: ${response.status}`);
  }
  
  return response.json();
}

// Render recommendations
async function displayRecommendations() {
  const recommendationsEl = document.getElementById('recommendations');
  recommendationsEl.innerHTML = '<p>Loading recommendations...</p>';
  
  try {
    const data = await fetchRecommendations('user_12345', 5);
    
    // Clear loading message
    recommendationsEl.innerHTML = '';
    
    // Create heading
    const heading = document.createElement('h2');
    heading.textContent = 'Recommended for You';
    recommendationsEl.appendChild(heading);
    
    // Create recommendation list
    const list = document.createElement('ul');
    list.className = 'recommendation-list';
    
    // Add each recommendation
    data.recommendations.forEach(post => {
      const item = document.createElement('li');
      item.className = 'recommendation';
      item.dataset.postId = post.id;
      
      // Add recommendation badge with reason
      const badge = document.createElement('div');
      badge.className = 'recommendation-badge';
      badge.textContent = post.recommendation_reason;
      item.appendChild(badge);
      
      // Add author info
      const author = document.createElement('div');
      author.className = 'author';
      author.innerHTML = `
        <img src="${post.account.avatar || '/img/default-avatar.png'}" alt="">
        <span>${post.account.display_name}</span>
      `;
      item.appendChild(author);
      
      // Add content
      const content = document.createElement('div');
      content.className = 'content';
      content.innerHTML = post.content;
      item.appendChild(content);
      
      // Add interaction buttons
      const actions = document.createElement('div');
      actions.className = 'actions';
      actions.innerHTML = `
        <button class="favorite" aria-label="Favorite">❤️</button>
        <button class="boost" aria-label="Boost">🔄</button>
        <button class="bookmark" aria-label="Bookmark">🔖</button>
      `;
      item.appendChild(actions);
      
      // Add to list
      list.appendChild(item);
    });
    
    recommendationsEl.appendChild(list);
    
    // Set up interaction tracking
    setupInteractions();
  } catch (error) {
    recommendationsEl.innerHTML = `<p class="error">Error loading recommendations: ${error.message}</p>`;
  }
}

// Track interactions to improve future recommendations
function setupInteractions() {
  const interactionLogger = new InteractionLogger('YOUR_API_KEY', 'user_12345');
  
  document.querySelectorAll('.recommendation').forEach(item => {
    const postId = item.dataset.postId;
    
    // Favorite button
    item.querySelector('.favorite').addEventListener('click', () => {
      interactionLogger.logInteraction(postId, 'favorite', { 
        source: 'recommendations_page'
      });
    });
    
    // Boost button
    item.querySelector('.boost').addEventListener('click', () => {
      interactionLogger.logInteraction(postId, 'reblog', { 
        source: 'recommendations_page'
      });
    });
    
    // Bookmark button
    item.querySelector('.bookmark').addEventListener('click', () => {
      interactionLogger.logInteraction(postId, 'bookmark', { 
        source: 'recommendations_page'
      });
    });
  });
}

// Call when page loads
document.addEventListener('DOMContentLoaded', displayRecommendations);
```

## Timeline Integration

The recommendations engine integrates directly with the timeline injection system to provide a seamless user experience. When a user requests their home timeline, the system:

1. Determines if the user is new (has fewer than 5 interactions) or returning
2. For new users, injects cold start content to bootstrap the recommendation process
3. For returning users, calls `get_ranked_recommendations()` to generate personalized recommendations
4. Injects these recommendations into the timeline with proper metadata

See the [Timeline Injection API](timeline_injection.md) for more details on how recommendations are blended into timelines.

Example of an injected recommendation in a timeline:

```json
{
  "id": "109876543211234567",
  "content": "<p>Just published a new blog post about sustainable tech!</p>",
  "created_at": "2025-03-15T14:22:11.000Z",
  "account": {
    "id": "12345",
    "username": "techblogger",
    "display_name": "Tech Sustainability Blog"
  },
  "injected": true,
  "injection_metadata": {
    "source": "recommendation_engine",
    "strategy": "personalized",
    "explanation": "From an author you might like",
    "score": 0.87
  }
}
```

## Related Resources

- [Timelines API](timelines.md) - Get enhanced timelines with recommendations
- [Timeline Injection API](timeline_injection.md) - Learn how recommendations are injected into timelines
- [Feedback API](feedback.md) - Log user interactions to improve recommendations
- [Privacy API](privacy.md) - Control user privacy settings
- [Concepts: Recommendation Engine](../concepts/recommendations.md) - Learn how the recommendation algorithm works