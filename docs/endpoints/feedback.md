# Feedback API

The Feedback API allows you to log user interactions with posts, which are essential for building personalized recommendations. These interactions shape the recommendation engine's understanding of user preferences.

## Endpoints

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method post">POST</span>
    <span class="corgi-endpoint-path">/api/v1/interactions</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Log a user interaction with a post. This endpoint records actions like favorites, bookmarks, or explicit feedback.</p>
    
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
          <td>user_alias</td>
          <td>string</td>
          <td><span class="corgi-param-required">Required</span></td>
          <td>Pseudonymized identifier for the user</td>
        </tr>
        <tr>
          <td>post_id</td>
          <td>string</td>
          <td><span class="corgi-param-required">Required</span></td>
          <td>Unique identifier for the post</td>
        </tr>
        <tr>
          <td>action_type</td>
          <td>string</td>
          <td><span class="corgi-param-required">Required</span></td>
          <td>The type of interaction: "favorite", "bookmark", "reblog", "more_like_this", "less_like_this"</td>
        </tr>
        <tr>
          <td>context</td>
          <td>object</td>
          <td>Optional</td>
          <td>Additional context about the interaction</td>
        </tr>
      </tbody>
    </table>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Request</div>
      <pre><code class="language-json">{
  "user_alias": "user_12345",
  "post_id": "post_67890",
  "action_type": "favorite",
  "context": {
    "source": "timeline_home"
  }
}</code></pre>
    </div>
    
    <h4>Response</h4>
    <p>Returns a confirmation with the logged interaction ID.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "status": "ok",
  "interaction_id": "interaction_12345"
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/interactions/{post_id}</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Get all interactions for a specific post.</p>
    
    <h4>Path Parameters</h4>
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
          <td>post_id</td>
          <td>string</td>
          <td><span class="corgi-param-required">Required</span></td>
          <td>The ID of the post to retrieve interactions for</td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns an object with the post ID and counts of different interaction types.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "post_id": "post_67890",
  "interaction_counts": {
    "favorites": 42,
    "reblogs": 12,
    "replies": 8,
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
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method post">POST</span>
    <span class="corgi-endpoint-path">/api/v1/interactions/counts/batch</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Get interaction counts for multiple posts in a single request.</p>
    
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
          <td>post_ids</td>
          <td>array</td>
          <td><span class="corgi-param-required">Required</span></td>
          <td>Array of post IDs to get counts for</td>
        </tr>
      </tbody>
    </table>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Request</div>
      <pre><code class="language-json">{
  "post_ids": ["post_12345", "post_67890", "post_24680"]
}</code></pre>
    </div>
    
    <h4>Response</h4>
    <p>Returns an object with counts for each requested post ID.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "counts": {
    "post_12345": {
      "favorites": 27,
      "reblogs": 8,
      "replies": 4,
      "bookmarks": 2
    },
    "post_67890": {
      "favorites": 42,
      "reblogs": 12,
      "replies": 8,
      "bookmarks": 5
    },
    "post_24680": {
      "favorites": 15,
      "reblogs": 3,
      "replies": 1,
      "bookmarks": 0
    }
  }
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/interactions/user/{user_id}</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Get all interactions for a specific user.</p>
    
    <h4>Path Parameters</h4>
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
          <td>The ID of the user to retrieve interactions for</td>
        </tr>
      </tbody>
    </table>
    
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
          <td>50</td>
          <td>Maximum number of interactions to return</td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns an object with the user ID and list of interactions.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "interactions": [
    {
      "id": "interaction_98765",
      "post_id": "post_67890",
      "action_type": "favorite",
      "created_at": "2025-03-15T14:30:00.000Z",
      "context": {
        "source": "timeline_home"
      }
    },
    {
      "id": "interaction_98764",
      "post_id": "post_13579",
      "action_type": "bookmark",
      "created_at": "2025-03-15T13:45:00.000Z",
      "context": {
        "source": "timeline_public"
      }
    }
  ]
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/interactions/favourites</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Get all posts favorited by a specific user.</p>
    
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
          <td>The ID of the user to retrieve favorites for <span class="corgi-param-required">Required</span></td>
        </tr>
        <tr>
          <td>limit</td>
          <td>integer</td>
          <td>20</td>
          <td>Maximum number of favorites to return</td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns an object with the user ID and list of favorited posts.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "favorites": [
    {
      "id": "post_67890",
      "content": "<p>Just published a new blog post about sustainable tech!</p>",
      "created_at": "2025-03-15T14:22:11.000Z",
      "account": {
        "id": "12345",
        "username": "techblogger",
        "display_name": "Tech Sustainability Blog"
      },
      "favorited_at": "2025-03-15T14:30:00.000Z"
    },
    {
      "id": "post_13579",
      "content": "<p>Check out our latest open source contribution to the Fediverse!</p>",
      "created_at": "2025-03-15T13:45:22.000Z",
      "account": {
        "id": "67890",
        "username": "fediversedev",
        "display_name": "Fediverse Developers"
      },
      "favorited_at": "2025-03-15T13:50:00.000Z"
    }
  ]
}</code></pre>
    </div>
  </div>
</div>

## Interaction Types

The feedback API supports these interaction types:

| Type | Description | Impact on Recommendations |
|------|-------------|---------------------------|
| `favorite` | User favorites/likes a post | Strong positive signal |
| `bookmark` | User bookmarks a post | Strong positive signal |
| `reblog` | User boosts/reblogs a post | Medium positive signal |
| `more_like_this` | User explicitly requests similar content | Very strong positive signal |
| `less_like_this` | User explicitly requests less similar content | Strong negative signal |

## Context Object

The optional `context` object provides additional information about the interaction:

```json
{
  "context": {
    "source": "timeline_home",  // Where the interaction occurred
    "position": 3,              // Position in the timeline
    "session_id": "abc123",     // Tracks interactions in a single session
    "recommendation": true      // Whether this was a recommended post
  }
}
```

Common source values:
- `timeline_home` - Regular home timeline
- `timeline_recommended` - Recommended timeline
- `timeline_public` - Public timeline
- `profile` - User profile view
- `search` - Search results

## Bulk Logging

For efficient logging of multiple interactions, you can use the batch endpoint:

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method post">POST</span>
    <span class="corgi-endpoint-path">/api/v1/interactions/batch</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Log multiple user interactions in a single request.</p>
    
    <h4>Request Body</h4>
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Request</div>
      <pre><code class="language-json">{
  "user_alias": "user_12345",
  "interactions": [
    {
      "post_id": "post_67890",
      "action_type": "favorite",
      "created_at": "2025-03-15T14:30:00.000Z",
      "context": {
        "source": "timeline_home"
      }
    },
    {
      "post_id": "post_13579",
      "action_type": "bookmark",
      "created_at": "2025-03-15T13:45:00.000Z",
      "context": {
        "source": "timeline_recommended"
      }
    }
  ]
}</code></pre>
    </div>
    
    <h4>Response</h4>
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "status": "ok",
  "processed": 2,
  "interaction_ids": [
    "interaction_98765",
    "interaction_98764"
  ]
}</code></pre>
    </div>
  </div>
</div>

## Privacy Considerations

The Feedback API respects user privacy settings:

- For users with `full` tracking level, all interactions are stored and used for recommendations
- For users with `limited` tracking level, only aggregated interaction data is stored
- For users with `none` tracking level, interaction logging requests are still accepted, but data is discarded

<div class="corgi-callout">
  <div class="corgi-callout-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM11 7h2v2h-2V7zm0 4h2v6h-2v-6z"/></svg>
    Privacy Impact
  </div>
  <p>When logging interactions, always make sure your users understand how this data is being used. Provide clear privacy settings and respect user choices about data collection.</p>
</div>

## Client Integration Example

Here's an example of integrating the Feedback API in a client application:

```javascript
// Set up interaction logger
class InteractionLogger {
  constructor(apiKey, userId) {
    this.apiKey = apiKey;
    this.userId = userId;
    this.queue = [];
    this.processingInterval = 5000; // Process every 5 seconds
    
    // Start processing queue periodically
    setInterval(() => this.processQueue(), this.processingInterval);
  }
  
  // Log a single interaction
  async logInteraction(postId, actionType, context = {}) {
    // Add to queue
    this.queue.push({
      post_id: postId,
      action_type: actionType,
      context: {
        ...context,
        timestamp: new Date().toISOString()
      }
    });
    
    // If queue is getting large, process immediately
    if (this.queue.length >= 10) {
      this.processQueue();
    }
  }
  
  // Process the queue in batch
  async processQueue() {
    if (this.queue.length === 0) return;
    
    const interactions = [...this.queue];
    this.queue = [];
    
    try {
      // For single interaction
      if (interactions.length === 1) {
        const interaction = interactions[0];
        await fetch('https://api.corgi-recs.io/api/v1/interactions', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            user_alias: this.userId,
            post_id: interaction.post_id,
            action_type: interaction.action_type,
            context: interaction.context
          })
        });
      } 
      // For multiple interactions
      else {
        await fetch('https://api.corgi-recs.io/api/v1/interactions/batch', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            user_alias: this.userId,
            interactions: interactions
          })
        });
      }
    } catch (error) {
      console.error('Failed to log interactions:', error);
      
      // Re-add to queue on failure
      this.queue = [...interactions, ...this.queue].slice(0, 100);
    }
  }
}

// Usage
const logger = new InteractionLogger('YOUR_API_KEY', 'user_12345');

// Log interactions
document.querySelectorAll('.post').forEach(post => {
  // Favorite button
  post.querySelector('.favorite-button').addEventListener('click', () => {
    const postId = post.dataset.postId;
    logger.logInteraction(postId, 'favorite', { 
      source: 'timeline_home',
      position: Array.from(post.parentNode.children).indexOf(post)
    });
  });
  
  // Bookmark button
  post.querySelector('.bookmark-button').addEventListener('click', () => {
    const postId = post.dataset.postId;
    logger.logInteraction(postId, 'bookmark', { 
      source: 'timeline_home',
      position: Array.from(post.parentNode.children).indexOf(post)
    });
  });
});
```

## Related Resources

- [Privacy API](privacy.md) - Manage user privacy settings
- [Recommendations API](recommendations.md) - Retrieve personalized recommendations
- [Concepts: Recommendation Engine](../concepts/recommendations.md) - Learn how user feedback informs recommendations