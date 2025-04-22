# Privacy API

The Privacy API allows users to control how much data is collected and used for personalization. It provides endpoints for viewing and updating privacy settings, giving users control over their recommendation experience.

## Endpoints

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/privacy</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Retrieves the current privacy settings for a user.</p>
    
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
          <td>The user ID to get privacy settings for <span class="corgi-param-required">Required</span></td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns the user's current privacy settings.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "tracking_level": "limited",
  "created_at": "2025-02-10T12:00:00.000Z",
  "updated_at": "2025-03-15T09:30:00.000Z"
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method post">POST</span>
    <span class="corgi-endpoint-path">/api/v1/privacy</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Updates a user's privacy settings, controlling how much data is collected and how it's used for recommendations.</p>
    
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
          <td>The user ID to update privacy settings for</td>
        </tr>
        <tr>
          <td>tracking_level</td>
          <td>string</td>
          <td><span class="corgi-param-required">Required</span></td>
          <td>Privacy level: "full", "limited", or "none"</td>
        </tr>
      </tbody>
    </table>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Request</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "tracking_level": "full"
}</code></pre>
    </div>
    
    <h4>Response</h4>
    <p>Returns the updated privacy settings.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "tracking_level": "full",
  "status": "ok",
  "updated_at": "2025-03-15T14:45:00.000Z"
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method get">GET</span>
    <span class="corgi-endpoint-path">/api/v1/privacy/data</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Retrieves all data collected for a user, providing transparency about what's being stored.</p>
    
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
          <td>The user ID to get data for <span class="corgi-param-required">Required</span></td>
        </tr>
        <tr>
          <td>format</td>
          <td>string</td>
          <td>"json"</td>
          <td>Response format: "json" or "csv"</td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns all data stored for the user, including interactions, recommendations, and settings.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "user_id": "user_12345",
  "privacy": {
    "tracking_level": "full",
    "created_at": "2025-02-10T12:00:00.000Z",
    "updated_at": "2025-03-15T14:45:00.000Z"
  },
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
    // Additional interactions...
  ],
  "recommendations": [
    {
      "post_id": "post_24680",
      "ranking_score": 0.87,
      "recommendation_reason": "From an author you might like",
      "created_at": "2025-03-15T15:00:00.000Z"
    },
    // Additional recommendations...
  ]
}</code></pre>
    </div>
  </div>
</div>

<div class="corgi-endpoint">
  <div class="corgi-endpoint-header">
    <span class="corgi-endpoint-method delete">DELETE</span>
    <span class="corgi-endpoint-path">/api/v1/privacy/data</span>
  </div>
  <div class="corgi-endpoint-body">
    <p>Deletes all data associated with a user.</p>
    
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
          <td>The user ID to delete data for <span class="corgi-param-required">Required</span></td>
        </tr>
        <tr>
          <td>confirm</td>
          <td>boolean</td>
          <td>false</td>
          <td>Confirmation flag, must be set to true <span class="corgi-param-required">Required</span></td>
        </tr>
      </tbody>
    </table>
    
    <h4>Response</h4>
    <p>Returns confirmation of data deletion.</p>
    
    <div class="corgi-response-example">
      <div class="corgi-response-example-header">Example Response</div>
      <pre><code class="language-json">{
  "status": "ok",
  "message": "All user data has been deleted",
  "deleted_items": {
    "interactions": 42,
    "recommendations": 15,
    "settings": 1
  },
  "deletion_time": "2025-03-15T16:00:00.000Z"
}</code></pre>
    </div>
  </div>
</div>

## Privacy Levels

Corgi offers three privacy levels, each providing different balances between personalization and data collection:

### Full Tracking

```json
{
  "tracking_level": "full"
}
```

With full tracking enabled:
- All interactions (favorites, boosts, etc.) are stored
- Detailed content preferences are tracked
- Maximum personalization is provided
- Individual interactions are stored with timestamps
- Data is retained according to the configured retention period

### Limited Tracking

```json
{
  "tracking_level": "limited"
}
```

With limited tracking (the default):
- Only aggregated statistics are stored
- Individual interactions are not retained after aggregation
- Basic personalization is still possible
- Users can still receive recommendations, but they may be less personalized
- Aggregate data is retained until account deletion

### No Tracking

```json
{
  "tracking_level": "none"
}
```

With no tracking:
- No user data is collected or stored
- No personalization is provided
- Timeline requests pass through without enhancement
- Ensures maximum privacy at the expense of personalization

<div class="corgi-callout">
  <div class="corgi-callout-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM11 7h2v2h-2V7zm0 4h2v6h-2v-6z"/></svg>
    Default Privacy
  </div>
  <p>All new users start with <code>limited</code> tracking unless they explicitly opt into <code>full</code> tracking.</p>
</div>

## Privacy Settings Middleware

The Corgi API includes middleware that respects user privacy settings when processing requests:

1. User initiates an API request
2. Middleware checks the user's privacy settings
3. Request is processed according to the privacy level:
   - **full**: Complete processing with all features
   - **limited**: Aggregated processing with basic features
   - **none**: Minimal processing with no data storage

This ensures that all parts of Corgi consistently enforce user privacy preferences.

## Client Integration

Here's an example of integrating privacy settings in a client application:

```javascript
// Function to fetch current privacy settings
async function getPrivacySettings(userId) {
  const response = await fetch(`https://api.corgi-recs.io/api/v1/privacy?user_id=${userId}`, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error(`Error fetching privacy settings: ${response.status}`);
  }
  
  return response.json();
}

// Function to update privacy settings
async function updatePrivacySettings(userId, trackingLevel) {
  const response = await fetch('https://api.corgi-recs.io/api/v1/privacy', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user_id: userId,
      tracking_level: trackingLevel
    })
  });
  
  if (!response.ok) {
    throw new Error(`Error updating privacy settings: ${response.status}`);
  }
  
  return response.json();
}

// Example: Privacy settings UI
document.addEventListener('DOMContentLoaded', async () => {
  const userId = 'user_12345';
  const settings = await getPrivacySettings(userId);
  
  // Set initial form state
  const privacyForm = document.getElementById('privacy-form');
  const trackingRadios = privacyForm.querySelectorAll('input[name="tracking"]');
  trackingRadios.forEach(radio => {
    if (radio.value === settings.tracking_level) {
      radio.checked = true;
    }
  });
  
  // Handle form submission
  privacyForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    
    const selectedTracking = privacyForm.querySelector('input[name="tracking"]:checked').value;
    
    try {
      const result = await updatePrivacySettings(userId, selectedTracking);
      showNotification(`Privacy settings updated to ${result.tracking_level}`);
    } catch (error) {
      showError(`Failed to update privacy settings: ${error.message}`);
    }
  });
});
```

## HTML Form Example

Here's a simple privacy settings form you can include in your application:

```html
<form id="privacy-form" class="privacy-settings">
  <h2>Privacy Settings</h2>
  
  <div class="setting">
    <input type="radio" id="tracking-full" name="tracking" value="full">
    <label for="tracking-full">
      <strong>Full Personalization</strong>
      <p>Store all interactions for the best recommendations.</p>
    </label>
  </div>
  
  <div class="setting">
    <input type="radio" id="tracking-limited" name="tracking" value="limited">
    <label for="tracking-limited">
      <strong>Limited Personalization</strong>
      <p>Store only aggregated data for basic recommendations.</p>
    </label>
  </div>
  
  <div class="setting">
    <input type="radio" id="tracking-none" name="tracking" value="none">
    <label for="tracking-none">
      <strong>No Personalization</strong>
      <p>Don't store any data or provide personalized recommendations.</p>
    </label>
  </div>
  
  <div class="actions">
    <button type="submit" class="primary">Save Settings</button>
  </div>
</form>
```

## Data Portability

The Privacy API supports data portability, allowing users to export their data in standard formats:

```javascript
// Function to export user data
async function exportUserData(userId, format = 'json') {
  const response = await fetch(`https://api.corgi-recs.io/api/v1/privacy/data?user_id=${userId}&format=${format}`, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error(`Error exporting data: ${response.status}`);
  }
  
  if (format === 'json') {
    return response.json();
  } else {
    return response.text();
  }
}

// Example: Export button
document.getElementById('export-button').addEventListener('click', async () => {
  const userId = 'user_12345';
  const format = document.getElementById('export-format').value;
  
  try {
    const data = await exportUserData(userId, format);
    
    if (format === 'json') {
      // Create downloadable JSON
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `corgi-data-${userId}.json`;
      a.click();
      
      URL.revokeObjectURL(url);
    } else if (format === 'csv') {
      // Handle CSV format
      const blob = new Blob([data], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `corgi-data-${userId}.csv`;
      a.click();
      
      URL.revokeObjectURL(url);
    }
  } catch (error) {
    showError(`Failed to export data: ${error.message}`);
  }
});
```

## Related Resources

- [Concepts: Privacy Design](../concepts/privacy.md) - Learn about Corgi's privacy architecture
- [Feedback API](feedback.md) - Log user interactions with posts
- [Recommendations API](recommendations.md) - Get personalized recommendations