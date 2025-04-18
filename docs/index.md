# Corgi Recommender Service

Welcome to the Corgi Recommender Service documentation! This service provides personalized post recommendations for Mastodon clients, with a focus on improving user engagement and content discovery.

## Overview

The Corgi Recommender Service is a microservice designed to provide personalized content recommendations for Mastodon users. It tracks user interactions with posts, analyzes preferences, and delivers tailored recommendations that can be integrated into Mastodon-compatible clients.

### Key Features

- **User Interaction Tracking**: Records favorites, bookmarks, and explicit feedback
- **Personalized Recommendations**: Generates tailored post suggestions based on user activity
- **Privacy Controls**: Provides user-configurable privacy settings
- **Mastodon Compatibility**: Returns data in Mastodon-compatible format for easy integration

## Getting Started

To start using the Corgi Recommender Service, follow these steps:

1. Set up your environment (see [Getting Started](getting-started.md))
2. Configure your database
3. Integrate the API with your client application

## API Structure

The service exposes several endpoints organized by functional area:

- [Interactions API](endpoints/interactions.md): For logging user feedback and activity
- [Recommendations API](endpoints/recommendations.md): For retrieving personalized content
- [Privacy API](endpoints/privacy.md): For managing user privacy settings

## Architecture

For information about the service architecture, components, and design decisions, see the [Architecture](architecture.md) page.

## Validation

The service includes a built-in validator to ensure functionality. Learn more in the [Validator Guide](validator-guide.md).