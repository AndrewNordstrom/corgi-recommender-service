# Architecture

This document outlines the architecture of the Corgi Recommender Service, explaining its components, data flow, and design decisions.

## System Overview

The Corgi Recommender Service is a modern web service that provides personalized content recommendations for Mastodon users. It tracks user interactions, analyzes preferences, and delivers tailored content suggestions while maintaining user privacy.

### Key Components

![Architecture Diagram](assets/architecture-diagram.png)

The system consists of these main components:

1. **API Layer**: Web routes handling client requests
2. **Database Layer**: SQLAlchemy ORM for database abstraction and persistence
3. **Core Engine**: Ranking algorithm and recommendation logic
4. **Utility Services**: Privacy controls, logging, and validation

## Component Details

### API Layer

The API layer uses modular route organization by functionality:

- **Interactions API**: Logs and queries user interactions with posts
- **Recommendations API**: Provides personalized content suggestions
- **Privacy API**: Manages user privacy settings
- **Timeline API**: Delivers and augments timeline data

Each component is defined in its own module within the `routes/` directory, promoting code organization and maintainability.

### Database Layer

The service uses SQLAlchemy ORM for database abstraction, supporting both SQLite (development) and PostgreSQL (production) with these primary models:

- **PostMetadata**: Stores post content and metadata
- **UserInteraction**: Records user engagement with posts
- **UserAlias**: Maps pseudonymized user identifiers
- **AuthorPreference**: Tracks user preferences for authors
- **RecommendationLog**: Records recommendation history

Database access is handled through SQLAlchemy sessions, providing efficient connection management, query execution, and database portability. The database interface is cleanly abstracted through the `db.interface` module.

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

User IDs are hashed with HMAC-SHA256 before storage to enhance privacy. This allows the system to track user preferences without storing raw identifiers, implemented in the `db.privacy` module.

### 2. Database Abstraction with SQLAlchemy

SQLAlchemy ORM provides database portability, allowing the system to work seamlessly with both SQLite and PostgreSQL. This enables easier development, testing, and deployment across different environments.

### 3. Modular API Design

The API is designed in a modular way, with clear separation of concerns between routes, database access, and business logic, making the codebase easier to maintain and extend.

### 4. Mastodon-Compatible Response Format

Responses follow Mastodon API conventions, enabling direct integration with existing clients while adding recommendation-specific metadata.

### 5. Three-Tier Privacy Model

The system offers three privacy levels (FULL, LIMITED, NONE) represented as an enum, giving users control over data collection while balancing recommendation quality.

## Scalability Considerations

### Current Limitations

- Single server deployment
- In-memory recommendation processing
- No distributed caching
- Limited batch processing capabilities

### Potential Improvements

- Introduce worker queues for asynchronous ranking generation
- Implement Redis-based caching for recommendations
- Add database sharding for high-volume deployments
- Support for distributed processing with Celery or similar tools

## Security Considerations

The service implements several security measures:

- User data pseudonymization with HMAC-SHA256
- Configurable CORS policies
- Robust input validation and sanitization
- Request ID tracking for audit trails
- SQLAlchemy ORM to prevent SQL injection
- Exception handling that prevents information leakage

## Development and Testing

The service includes:

- Comprehensive testing framework with pytest
- Validation tool for end-to-end testing
- Environment-specific configuration
- Support for SQLite in development environments
- Database migration tools for versioning schema changes

## References

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Mastodon API Reference](https://docs.joinmastodon.org/api/)
- [Content Recommendation Best Practices](https://www.example.org/recommendations)