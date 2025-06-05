# Corgi Recommender Service: Standalone Guide

## Overview

The Corgi Recommender Service has been completely refactored into a standalone microservice with its own client integration libraries. This guide explains how to use it without any dependency on Elk or other Mastodon clients.

## What is the Corgi Recommender Service?

The Corgi Recommender Service is a microservice that provides:

1. User interaction tracking (favorites, boosts, etc.)
2. Post metadata storage
3. Personalized post recommendations
4. Privacy controls for users
5. Analytics for user engagement

It's designed to work with any Mastodon client, not just Elk.

## ✅ Migration Completed

The Corgi Recommender Service has been successfully extracted from the monorepo and converted to a standalone microservice. The following tasks were completed:

### Structure and Files

- [x] Copied all necessary files to new directory
- [x] Removed dependencies on parent monorepo
- [x] Ensured proper directory structure
- [x] Validated all core service files are present
- [x] Updated Docker configuration for standalone operation
- [x] Added client integration libraries

### Configuration Updates

- [x] Updated environment variable examples in `.env.example`
- [x] Modified `docker-compose.yml` for independent operation
- [x] Updated `render.yaml` and removed Elk-specific references
- [x] Updated `README.md` to remove Elk-specific references
- [x] Added setup instructions for new Git repository

### Client Libraries

- [x] Created API configuration utilities
- [x] Implemented status interaction middleware
- [x] Built post logging utilities
- [x] Added DOM observation utilities
- [x] Included interaction diagnostics tools
- [x] Provided examples for Vue/Nuxt and vanilla JS

## Key Advantages

- **Complete Data Ownership**: Host your own recommendation data
- **Privacy-focused**: User pseudonymization and granular privacy controls
- **Framework Agnostic**: Works with any frontend technology
- **Mastodon API Compatible**: Designed to complement the Mastodon API
- **Simple Integration**: Flexible client libraries for easy integration

## Getting Started

### Prerequisites

- Docker (for containerized deployment)
- PostgreSQL database
- Any frontend application that can make API calls

### Quick Start

1. **Start the service with Docker Compose**:
   ```bash
   git clone https://github.com/your-username/corgi-recommender-service.git
   cd corgi-recommender-service
   docker-compose up -d
   ```

2. **Verify the service is running**:
   ```bash
   curl http://localhost:5000/health
   ```

3. **Integrate with your frontend**:
   The service includes client libraries for easy integration.

## Integration Options

The service can be integrated with any frontend in several ways:

### Option 1: Direct API Calls

You can directly call the API endpoints from your application:

```javascript
// Log an interaction
async function logInteraction(userId, postId, actionType) {
  const response = await fetch('http://localhost:5000/v1/interactions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      post_id: postId,
      action_type: actionType
    })
  });
  return response.json();
}

// Get recommendations
async function getRecommendations(userId) {
  const response = await fetch(`http://localhost:5000/v1/recommendations?user_id=${userId}`);
  return response.json();
}
```

### Option 2: Using the Client Library

The service includes client libraries in the `/client` directory:

```javascript
import { useStatusActions, logTimelinePosts } from './corgi-recommender-service/client';

// Log likes, boosts, etc.
const { toggleFavourite, toggleReblog } = useStatusActions({
  status: post,
  client: mastodonClient,
  getUserId: () => userId
});

// Automatically log timeline posts
logTimelinePosts(posts, {
  consentToPostLogging: true,
  apiBaseUrl: 'http://localhost:5000'
});
```

### Option 3: DOM Observation for Non-SPA Apps

For traditional websites or when you can't intercept API calls:

```javascript
import { createDomObserver } from './corgi-recommender-service/client';

// Create and start a DOM observer
const observer = createDomObserver({
  apiBaseUrl: 'http://localhost:5000',
  getUserId: () => localStorage.getItem('userId')
});

observer.start();
```

## Working Without Mastodon

The service can work completely independently of Mastodon, allowing you to:

1. Build a standalone recommendation system
2. Create a content curation platform
3. Develop a personalized feed for any content type

### Using with Non-Mastodon Content

You just need to structure your post data similarly:

```javascript
// Log any kind of content
await fetch('http://localhost:5000/v1/posts', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    post_id: "my-content-123",
    author_id: "content-creator-456",
    content: "This is the content of the post",
    content_type: "article",
    created_at: new Date().toISOString()
  })
});
```

## Core Components

### Backend Server

- Flask-based REST API
- PostgreSQL database for data storage
- Request/response middleware for logging and tracing
- Privacy utilities for user data protection

### Client Library

- API configuration utilities
- Status interaction middleware
- Post logging utilities
- DOM mutation observers
- Diagnostics tools

## 🚀 Next Steps

To complete the migration:

1. Run these commands in the `corgi-recommender-service` directory:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Extract Corgi Recommender Service as standalone microservice"
   ```

2. Create a new repository on GitHub/GitLab/etc.

3. Connect your local repository:
   ```bash
   git remote add origin <YOUR_REMOTE_URL>
   git push -u origin main
   ```

4. Update your frontend's `.env` file to point to the new service:
   ```
   NUXT_PUBLIC_RECOMMENDER_SERVICE_URL=http://localhost:5000
   ```

5. Deploy the standalone service to your preferred platform:
   - Render.com (with `render.yaml`)
   - Fly.io (with `fly.toml`)
   - Or any other container platform

## 📋 Architecture Overview

The standalone service maintains the same core architecture:

- **Flask REST API**: Versioned endpoints with `/v1` prefix
- **PostgreSQL**: For storing interactions, posts, and rankings
- **Privacy-focused**: User pseudonymization for data protection
- **Modularity**: Clear separation of concerns between modules
- **Docker-ready**: Containerized for consistent deployment
- **Observable**: Request tracing and performance monitoring

## 🔄 API Compatibility

The service maintains the same API endpoints as before, ensuring backward compatibility with the frontend:

- `GET /health` - Service health check
- `POST /v1/interactions` - Log user interactions
- `POST /v1/posts` - Store post metadata
- `GET /v1/recommendations` - Get personalized recommendations
- `POST /v1/rankings/generate` - Force regenerate rankings

## Customization

### Recommendation Algorithm

You can customize the recommendation algorithm in `core/ranking_algorithm.py`.

### Privacy Controls

You can adjust privacy settings in `utils/privacy.py`.

### Database Schema

Review and modify the database schema in `db/schema.py` to fit your needs.

## Deployment Examples

### Fly.io Deployment

```bash
fly launch
fly postgres create --name corgi-recommender-db
fly postgres attach corgi-recommender-db
fly deploy
```

### Railway Deployment

```bash
railway init
railway add plugin postgresql
railway up
```

## Monitoring and Management

- Use the `/v1/analytics` endpoints to view interaction and post metrics
- Monitor database growth and performance
- Use the health check endpoint for uptime monitoring

## Need Help?

If you encounter any issues, please open an issue on GitHub or reach out to the project maintainers.