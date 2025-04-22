# Architecture

This document outlines the architecture of the Corgi Recommender Service, explaining its components, data flow, and design decisions.

## System Overview

The Corgi Recommender Service is a Flask-based microservice that provides personalized content recommendations for Mastodon users. It tracks user interactions, analyzes preferences, and delivers tailored content suggestions.

### Key Components

![Architecture Diagram](assets/architecture-diagram.png)

The system consists of these main components:

1. **API Layer**: Flask routes handling client requests
2. **Database Layer**: PostgreSQL database for data persistence
3. **Core Engine**: Ranking algorithm and recommendation logic
4. **Utility Services**: Privacy controls, logging, and validation

## Component Details

### API Layer

The API layer uses Flask blueprints to organize endpoints by functionality:

- **Interactions API**: Logs and queries user interactions with posts
- **Recommendations API**: Provides personalized content suggestions
- **Privacy API**: Manages user privacy settings

Each blueprint is defined in its own module within the `routes/` directory, promoting code organization and maintainability.

### Database Layer

The service uses PostgreSQL for data storage, with these primary tables:

- **post_metadata**: Stores post content and metadata
- **interactions**: Records user engagement with posts
- **post_rankings**: Stores personalized ranking scores
- **privacy_settings**: Manages user privacy preferences

Database access is handled through a connection pool (using `psycopg2`), providing efficient connection management and query execution.

### Core Engine

The recommendation engine consists of:

- **Ranking Algorithm**: Analyzes user behavior and post characteristics to compute personalized relevance scores
- **Feature Extractors**: Calculate individual feature scores (e.g., author preference, content engagement, recency)
- **Post Processor**: Formats recommendations in Mastodon-compatible format

The algorithm uses a weighted combination of features, allowing for easy tuning of recommendation priorities.

### Utility Services

Supporting components include:

- **Privacy Manager**: Enforces data collection policies based on user preferences
- **Logging System**: Provides detailed request logging with request IDs
- **Validator**: Tests system functionality and recommendation quality

## Data Flow

### User Interaction Flow

1. User interacts with content (e.g., favorites a post)
2. Client sends interaction to `/api/v1/interactions` endpoint
3. System pseudonymizes user ID for privacy
4. Interaction is stored in the database
5. Post interaction counts are updated

### Recommendation Flow

1. Client requests recommendations for a user
2. System checks for existing rankings (cached from previous generation)
3. If needed, recommendation algorithm is triggered:
   - Retrieves user's past interactions
   - Gathers candidate posts
   - Calculates ranking scores for each post
   - Stores rankings in the database
4. Recommended posts are formatted and returned to the client

## Design Decisions

### 1. Pseudonymization of User IDs

User IDs are hashed with a salt before storage to enhance privacy. This allows the system to track user preferences without storing raw identifiers.

### 2. Database Connection Pooling

Connection pooling is used to efficiently manage database connections, reducing the overhead of establishing new connections for each request.

### 3. Blueprint-Based API Design

Flask blueprints provide a modular approach to API design, allowing clear separation of concerns and easier maintenance.

### 4. Mastodon-Compatible Response Format

Responses follow Mastodon API conventions, enabling direct integration with existing clients while adding recommendation-specific metadata.

### 5. Three-Tier Privacy Model

The system offers three privacy levels (full, limited, none) to give users control over data collection while balancing recommendation quality.

## Scalability Considerations

### Current Limitations

- Single server deployment
- In-memory recommendation processing
- No distributed caching

### Potential Improvements

- Introduce worker queues for asynchronous ranking generation
- Implement Redis-based caching for recommendations
- Add database sharding for high-volume deployments

## Security Considerations

The service implements several security measures:

- User data pseudonymization
- Configurable CORS policies
- Robust input validation
- Request ID tracking for audit trails

## Development and Testing

The service includes:

- Comprehensive testing framework
- Validation tool for end-to-end testing
- Environment-specific configuration

## References

- [Flask Documentation](https://flask.palletsprojects.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Mastodon API Reference](https://docs.joinmastodon.org/api/)
- [Content Recommendation Best Practices](https://www.example.org/recommendations)