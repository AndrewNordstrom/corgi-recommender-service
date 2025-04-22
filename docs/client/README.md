# Corgi Recommender Service - Client Integration

This directory contains client-side integration code for the Corgi Recommender Service. These modules provide middleware and utility functions that can be used to integrate the recommender service with frontend applications.

## Modules

- `status.js` - Middleware for intercepting and logging user interactions with posts (likes, reblogs, etc.)
- `post-logger.js` - Utilities for logging post views and timeline content
- `api-config.js` - Configuration for the Corgi Recommender Service API endpoints
- `dom-observer.js` - DOM mutation observer for capturing post interactions when direct API interception isn't possible

## Integration

These modules are designed to be integrated with Vue/Nuxt applications, but can be adapted for use with other frameworks.

For Mastodon clients, the `status.js` module provides a drop-in replacement for Mastodon API interaction functions that add logging capabilities.

See each module's documentation for detailed integration instructions.