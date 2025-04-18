# Corgi Recommender Service

A microservice for handling post recommendations and user interaction tracking for Mastodon clients.

## ✅ Phase 1 Complete (4/17/25) — Next Steps
- [x] Fix validator path prefix to align with /api/v1
- [ ] Run validator against live DB (not dry-run)
- [x] Begin Phase 2: middleware proxy integration for Elk/Mastodon

## 🔄 Phase 2: Middleware Proxy Integration

The service now includes a transparent proxy layer that allows Mastodon clients to connect through Corgi instead of directly to a Mastodon instance. This enables:

- Seamless injection of recommendations into standard Mastodon timelines
- No client-side changes needed for existing Mastodon clients
- Privacy-aware personalization based on user preferences

See [Proxy Documentation](docs/proxy.md) for setup and configuration details.

## Quick Start for New Repository Setup

If you've just extracted this code from the monorepo:

1. **Initialize Git repository**:
   ```bash
   cd corgi-recommender-service
   git init
   ```

2. **Make your first commit**:
   ```bash
   git add .
   git commit -m "Initial commit: Extract Corgi Recommender Service as standalone microservice"
   ```

3. **Connect to GitHub** (if you've already created a new repository):
   ```bash
   git remote add origin https://github.com/yourusername/corgi-recommender-service.git
   git push -u origin main
   ```

## Features

- User interaction logging (favorites, bookmarks, etc.)
- Post metadata storage and retrieval
- Personalized post recommendations using configurable algorithms
- RESTful API with versioned endpoints
- Request tracing and observability
- Docker deployment with PostgreSQL integration
- Ready for cloud deployment (Fly.io, Render, etc.)
- Client-side integration libraries for frontend applications

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 15+
- Docker and Docker Compose (optional, for containerized deployment)

### Local Development Setup

1. **Clone the repository**:
   ```
   git clone https://github.com/yourusername/corgi-recommender.git
   cd corgi-recommender
   ```

2. **Set up a virtual environment**:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```
   cp .env.example .env
   # Edit .env with your environment settings
   ```

5. **Start PostgreSQL**:
   You can use the Docker Compose file to run PostgreSQL:
   ```
   docker-compose up -d postgres
   ```

6. **Run the service**:
   ```
   ./start.sh
   ```

The service will be available at [http://localhost:5000](http://localhost:5000).

### Docker Deployment

To run the complete service with Docker Compose:

```
docker-compose up -d
```

## Client Integration

The service includes client-side libraries for seamlessly integrating interaction tracking and recommendations into frontend applications. These libraries are located in the `/client` directory.

### Features

- Intercept and log user interactions with posts (likes, reblogs, etc.)
- Track post views and timeline content
- DOM mutation observers for non-SPA applications
- Vue/Nuxt composables for reactive integration
- Vanilla JavaScript utilities for any application
- Configuration utilities for API endpoints

### Integration Examples

#### Vue/Nuxt Integration

```javascript
// In your Nuxt plugin
import { 
  useApiConfig, 
  useStatusActions,
  useTimelineLogger 
} from '@/corgi-recommender-service/client';

export default defineNuxtPlugin({
  setup() {
    // Configure API endpoints
    const apiConfig = useApiConfig();
    apiConfig.setApiBaseUrl(process.env.CORGI_API_URL);
    
    // Provide utilities to the app
    return {
      provide: {
        corgiConfig: apiConfig,
        useCorgiStatusActions: useStatusActions
      }
    }
  }
});

// In your Vue component
const { 
  toggleFavourite, 
  toggleReblog 
} = useStatusActions({
  status: props.status,
  client,
  getUserId: () => currentUser.value?.id
});
```

#### Vanilla JavaScript Integration

```javascript
import { 
  createStatusMiddleware, 
  createDomObserver 
} from './corgi-recommender-service/client';

// Initialize middleware
const statusMiddleware = createStatusMiddleware({
  apiBaseUrl: 'https://api.example.com',
  getUserId: () => localStorage.getItem('userId')
});

// Wrap Mastodon client with interaction logging
const wrappedClient = statusMiddleware.wrapMastodonClient(mastodonClient);

// For non-SPA applications, use DOM observer
const observer = createDomObserver({
  apiBaseUrl: 'https://api.example.com',
  getUserId: () => localStorage.getItem('userId')
});

// Start observing
observer.start();
```

See the `/client/examples` directory for complete integration examples.

## API Reference

The API is versioned with a `/v1` prefix for all routes.

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

## Deployment

### Environment Variables

See `.env.example` for all available configuration options. At minimum, you should set:

- `POSTGRES_HOST` - PostgreSQL host
- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password
- `POSTGRES_DB` - PostgreSQL database name
- `USER_HASH_SALT` - Salt for pseudonymizing user IDs (important for privacy)

### Deploying to Fly.io

1. Install the Fly CLI: https://fly.io/docs/hands-on/install-flyctl/

2. Log in to Fly:
   ```
   fly auth login
   ```

3. Launch the app:
   ```
   fly launch
   ```

4. Add a Postgres database:
   ```
   fly postgres create --name corgi-recommender-db
   fly postgres attach corgi-recommender-db
   ```

5. Deploy the app:
   ```
   fly deploy
   ```

### Deploying to Render

1. Fork this repository to your GitHub account.

2. Create a new Web Service on Render.com:
   - Connect your GitHub repository
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `sh ./start.sh`

3. Add the environment variables from `.env.example` in Render's dashboard.

4. Create a PostgreSQL database on Render and link it to your service.

## Testing

Run the test suite:

```
pytest
```

For test coverage:

```
pytest --cov=. --cov-report=html
```

## License

This project is licensed under the MIT License - see the LICENSE file for details