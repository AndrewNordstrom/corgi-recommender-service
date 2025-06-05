# Migration Guide: From Elk-Integrated to Standalone Service

This document provides guidance on how this microservice was extracted from the Elk monorepo and how to integrate it with frontend applications using the new client libraries.

## Extraction Process

The Corgi Recommender Service was extracted from the Elk monorepo to operate as a standalone microservice. The extraction involved:

1. Copying all the necessary files to a new directory
2. Removing any dependencies on the parent monorepo
3. Ensuring all configurations properly reflect standalone operation
4. Creating a new Git repository for the service
5. Creating a client integration library to simplify frontend integration

## Client Integration Library

The service now includes a client integration library in the `/client` directory that provides middleware-style utilities for tracking interactions, logging posts, and configuring API endpoints.

### Key Features

- Framework-agnostic design (works with Vue, React, or vanilla JS)
- DOM mutation observers for tracking posts in the UI
- Interaction interceptors for logging user actions
- API configuration utilities for consistent endpoint usage
- Privacy controls for user consent management
- Diagnostics tools for debugging and monitoring

## Frontend Integration

There are several ways to integrate the service with your frontend:

### Method 1: Using Environment Variables

Update your frontend's `.env` file to point to the new microservice endpoint:

```
# Development
NUXT_PUBLIC_RECOMMENDER_SERVICE_URL=http://localhost:5000

# Production 
NUXT_PUBLIC_RECOMMENDER_SERVICE_URL=https://your-deployed-service-url
```

### Method 2: Using the Client Library with Vue/Nuxt

1. Copy the `client` directory into your project or install it as a local package
2. Create a plugin file (e.g., `plugins/corgi.js`):

```javascript
import { useApiConfig, useStatusActions } from '@/corgi-recommender-service/client'

export default defineNuxtPlugin({
  setup() {
    // Configure API endpoints
    const apiConfig = useApiConfig()
    apiConfig.setApiBaseUrl(process.env.NUXT_PUBLIC_RECOMMENDER_SERVICE_URL)
    
    // Provide utilities to the app
    return {
      provide: {
        corgiConfig: apiConfig,
        useCorgiStatusActions: useStatusActions
      }
    }
  }
})
```

3. Use it in components:

```vue
<script setup>
const { useCorgiStatusActions } = useNuxtApp()
const { toggleFavourite, toggleReblog } = useCorgiStatusActions({
  status: props.status,
  client,
  getUserId: () => currentUser.value?.id
})
</script>
```

### Method 3: Using the Client Library with Vanilla JS

For non-Vue applications, use the standalone utilities:

```javascript
import { 
  createStatusMiddleware, 
  createDomObserver 
} from './corgi-recommender-service/client'

// Initialize middleware
const statusMiddleware = createStatusMiddleware({
  apiBaseUrl: 'https://api.example.com',
  getUserId: () => localStorage.getItem('userId')
})

// Wrap Mastodon client
const wrappedClient = statusMiddleware.wrapMastodonClient(mastodonClient)

// For DOM-based tracking
const observer = createDomObserver({
  apiBaseUrl: 'https://api.example.com',
  getUserId: () => localStorage.getItem('userId')
})

observer.start()
```

### Migrating from Elk-Integrated Code

If you were using the Elk-integrated version, here are the key changes:

#### Old (Elk-integrated)
```javascript
import { useApiConfig } from 'composables/use-api-config'
import { useStatusActions } from 'composables/masto/status'
import { logTimelinePosts } from 'composables/post-logger'

// API config
const { interactionsApiUrl } = useApiConfig()

// Status actions
const { toggleFavourite, toggleReblog } = useStatusActions({ status })

// Log posts
logTimelinePosts(posts)
```

#### New (Standalone)
```javascript
import { 
  useApiConfig, 
  useStatusActions,
  logTimelinePosts 
} from '@/corgi-recommender-service/client'

// API config
const { interactionsApiUrl } = useApiConfig()

// Status actions
const { toggleFavourite, toggleReblog } = useStatusActions({
  status,
  client, // Mastodon API client
  getUserId: () => currentUser.value?.id
})

// Log posts
logTimelinePosts(posts, {
  consentToPostLogging: true,
  apiBaseUrl: 'https://api.example.com'
})
```

### Testing the Integration

1. Start the microservice locally:
   ```
   docker-compose up -d
   ```

2. Start your frontend application with the updated environment variables.

3. Verify that the following functionality works:
   - Post interaction logging (favorites, boosts, etc.)
   - Personalized timeline recommendations
   - API health checks

## API Endpoints

The service provides these key endpoints:

### Health Checks
- `GET /health` - Health check endpoint
- `GET /v1/health` - Versioned health check endpoint

### Interactions
- `POST /v1/interactions` - Log a user interaction with a post
- `GET /v1/interactions` - Get all interactions for a user
- `GET /v1/interactions/{post_id}` - Get interactions for a specific post
- `GET /v1/interactions/counts/batch` - Get interaction counts for multiple posts

### Posts
- `POST /v1/posts` - Add or update post metadata
- `GET /v1/posts/{post_id}` - Get metadata for a specific post
- `GET /v1/posts/author/{author_id}` - Get posts by a specific author
- `GET /v1/posts/trending` - Get trending posts based on interaction counts

### Recommendations
- `GET /v1/recommendations` - Get personalized recommendations for a user
- `GET /v1/recommendations/real-posts` - Get real Mastodon posts
- `POST /v1/recommendations/rankings/generate` - Generate new rankings for a user

### Privacy
- `GET /v1/privacy/settings` - Get privacy settings for a user
- `POST /v1/privacy/settings` - Update privacy settings for a user

### Analytics
- `GET /v1/analytics/interactions` - Get analytics data about interactions
- `GET /v1/analytics/posts` - Get analytics data about posts

## Deployment Considerations

When deploying this microservice:

1. Ensure your database has proper persistence configured
2. Set a strong `USER_HASH_SALT` for user pseudonymization
3. Configure `CORS_ALLOWED_ORIGINS` to match your frontend domains
4. Consider setting up a CDN for better global performance
5. Use environment-specific variables rather than hardcoded values

## Structure Explained

```
/corgi-recommender-service
  ├── app.py                # Main application entry point
  ├── config.py             # Centralized configuration management
  ├── routes/               # API routes organized by function
  │   ├── interactions.py   # Interaction logging endpoints
  │   ├── posts.py          # Post metadata endpoints
  │   ├── recommendations.py # Recommendation endpoints
  │   ├── privacy.py        # Privacy settings endpoints
  │   └── analytics.py      # Analytics data endpoints
  ├── core/                 # Core recommendation algorithm logic
  ├── db/                   # Database connection and models
  ├── utils/                # Helper utilities
  │   ├── logging_decorator.py # Request logging decorator
  │   └── privacy.py        # User pseudonymization utilities
  ├── client/               # Client integration libraries
  │   ├── api-config.js     # API configuration utilities
  │   ├── status.js         # Interaction tracking middleware
  │   ├── post-logger.js    # Post logging utilities
  │   ├── dom-observer.js   # DOM mutation observers
  │   └── utils/            # Additional utilities
  ├── Dockerfile            # Container definition
  ├── docker-compose.yml    # Local development setup
  └── tests/                # Unit and integration tests
```

## Client Library Structure

```
/client
  ├── README.md             # Client library documentation
  ├── index.js              # Main entry point and exports
  ├── api-config.js         # API configuration utilities
  ├── status.js             # Interaction tracking middleware
  ├── post-logger.js        # Post logging utilities
  ├── dom-observer.js       # DOM mutation observers
  ├── utils/                # Additional utilities
  │   └── interaction-diagnostics.js # Interaction tracking diagnostics
  ├── examples/             # Integration examples
  │   ├── vue-integration.js        # Vue/Nuxt integration example
  │   └── vanilla-js-integration.js # Vanilla JS integration example
  └── tests/                # Testing utilities
      ├── interaction-middleware.test.js # Test for interaction middleware
      └── dom-observer.test.html         # Interactive DOM observer test
```

## Testing

We've included comprehensive testing utilities:

1. **Interaction Middleware Tests**: Run with `node client/tests/interaction-middleware.test.js`
2. **DOM Observer Test**: Open `client/tests/dom-observer.test.html` in a browser
3. **Server API Tests**: Run with `pytest`

## Need Help?

If you encounter any issues during migration, please open an issue on GitHub or reach out to the project maintainers.