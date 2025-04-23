# Database Schema

The Corgi Recommender Service uses a carefully designed database schema to ensure privacy, performance, and flexibility. This document provides details on the database structure and how it supports the service's functionality.

## Overview

The Corgi Recommender Service database is designed with privacy and performance in mind. It uses SQLAlchemy ORM to interact with the database, which supports both SQLite (for development) and PostgreSQL (for production).

The database is designed with these key principles:

1. **Privacy by Design**: User identities are pseudonymized with HMAC-SHA256 hashing
2. **Data Minimization**: Only essential data is stored for recommendations
3. **Performance Optimization**: Indexes on frequently queried columns
4. **Flexibility**: Supports both SQLite and PostgreSQL with minimal changes

## Schema Diagram

The following diagram shows the relationships between the main database tables:

```mermaid
erDiagram
    UserAlias {
        string alias_id PK
        datetime created_at
        datetime last_seen
        enum privacy_level
    }
    
    PostMetadata {
        string post_id PK
        string author_id
        string author_name
        text content
        string language
        datetime created_at
        int favorites
        int boosts
        int replies
        boolean sensitive
        json tags
    }
    
    UserInteraction {
        int id PK
        string alias_id FK
        string post_id FK
        enum interaction_type
        datetime timestamp
        float score_weight
        json context
    }
    
    AuthorPreference {
        int id PK
        string alias_id FK
        string author_id
        int interaction_count
        datetime last_interaction_at
        float preference_score
    }
    
    RecommendationLog {
        int id PK
        string alias_id FK
        string post_id FK
        datetime recommended_at
        string reason
        string model_version
    }
    
    UserAlias ||--o{ UserInteraction : "has"
    UserAlias ||--o{ AuthorPreference : "has"
    UserAlias ||--o{ RecommendationLog : "receives"
    PostMetadata ||--o{ UserInteraction : "receives"
    PostMetadata ||--o{ RecommendationLog : "included in"
```

## Tables

### UserAlias

The `UserAlias` table stores pseudonymized user identifiers and privacy preferences.

| Column         | Type                                | Description                                           |
|----------------|-------------------------------------|-------------------------------------------------------|
| alias_id       | String(64), Primary Key             | Pseudonymized user identifier (HMAC-SHA256 hash)      |
| created_at     | DateTime                            | When the user alias was first created                 |
| last_seen      | DateTime                            | When the user was last active                         |
| privacy_level  | Enum('NONE', 'LIMITED', 'FULL')     | User's privacy preference level                       |

**Indexes:**
- Primary key on `alias_id`

The `privacy_level` determines how user data is handled:

- **FULL**: All data is stored and used for recommendations
- **LIMITED**: Data is anonymized after a retention period
- **NONE**: Minimal data is stored, only used for basic functionality

### PostMetadata

The `PostMetadata` table stores information about posts from Mastodon/fediverse.

| Column         | Type                                | Description                                           |
|----------------|-------------------------------------|-------------------------------------------------------|
| post_id        | String(64), Primary Key             | Unique identifier for the post                        |
| author_id      | String(64), Not Null                | Author's identifier                                   |
| author_name    | String(255)                         | Display name of the author                            |
| content        | Text                                | Post content                                          |
| language       | String(10), Default 'en'            | Language code                                         |
| created_at     | DateTime, Not Null                  | When the post was created                             |
| favorites      | Integer, Default 0                  | Number of favorites/likes                             |
| boosts         | Integer, Default 0                  | Number of boosts/reblogs                              |
| replies        | Integer, Default 0                  | Number of replies                                     |
| sensitive      | Boolean, Default False              | Whether the post contains sensitive content           |
| tags           | JSON                                | List of tags associated with the post                 |

**Indexes:**
- Primary key on `post_id`
- Index on `author_id`
- Index on `created_at`
- Index on `language`
- Index on `tags` (GIN index in PostgreSQL)

### UserInteraction

The `UserInteraction` table tracks user interactions with posts.

| Column         | Type                                | Description                                           |
|----------------|-------------------------------------|-------------------------------------------------------|
| id             | Integer, Primary Key, Autoincrement | Unique identifier for the interaction                 |
| alias_id       | String(64), Foreign Key             | Reference to UserAlias                                |
| post_id        | String(64), Foreign Key             | Reference to PostMetadata                             |
| interaction_type | Enum('FAVORITE', 'BOOST', 'REPLY', 'VIEW', 'BOOKMARK') | Type of interaction             |
| timestamp      | DateTime, Default Now               | When the interaction occurred                         |
| score_weight   | Float, Default 1.0                  | Weight for scoring this interaction                   |
| context        | JSON                                | Additional context for the interaction                |

**Indexes and Constraints:**
- Primary key on `id`
- Index on `alias_id`
- Index on `post_id`
- Index on `interaction_type`
- Index on `timestamp`
- Composite index on `(alias_id, post_id)`
- Unique constraint on `(alias_id, post_id, interaction_type)` to prevent duplicate interactions

### AuthorPreference

The `AuthorPreference` table aggregates user preferences for authors based on interactions.

| Column            | Type                                | Description                                           |
|-------------------|-------------------------------------|-------------------------------------------------------|
| id                | Integer, Primary Key, Autoincrement | Unique identifier                                     |
| alias_id          | String(64), Foreign Key             | Reference to UserAlias                                |
| author_id         | String(64), Not Null                | Author's identifier                                   |
| interaction_count | Integer, Default 0                  | Number of interactions with this author               |
| last_interaction_at | DateTime                          | When the last interaction occurred                    |
| preference_score  | Float, Default 0.0                  | Calculated preference score                           |

**Indexes and Constraints:**
- Primary key on `id`
- Index on `alias_id`
- Index on `author_id`
- Index on `preference_score`
- Unique constraint on `(alias_id, author_id)` to ensure one preference entry per author per user

### RecommendationLog

The `RecommendationLog` table logs recommendations made to users.

| Column          | Type                                | Description                                           |
|-----------------|-------------------------------------|-------------------------------------------------------|
| id              | Integer, Primary Key, Autoincrement | Unique identifier                                     |
| alias_id        | String(64), Foreign Key             | Reference to UserAlias                                |
| post_id         | String(64), Foreign Key             | Reference to PostMetadata                             |
| recommended_at  | DateTime, Default Now               | When the recommendation was made                      |
| reason          | String(255)                         | Reason for the recommendation                         |
| model_version   | String(50)                          | Version of the recommendation model                   |

**Indexes:**
- Primary key on `id`
- Index on `alias_id`
- Index on `post_id`
- Index on `recommended_at`
- Composite index on `(alias_id, post_id)`

## Database Configuration

The database connection is configured via SQLAlchemy's URL format and can be set using environment variables:

```bash
# Use SQLite (development)
CORGI_DB_URL=sqlite:///data/corgi_recommender.db

# Use PostgreSQL (production)
CORGI_DB_URL=postgresql://username:password@localhost:5432/corgi_recommender
```

### SQLite vs PostgreSQL

The SQLAlchemy ORM abstraction allows the system to work with either:

- **SQLite**: Recommended for development, testing, and small deployments
  - Simpler setup with no additional services required
  - File-based storage that's easy to back up
  - Limited concurrency support
  
- **PostgreSQL**: Recommended for production and larger deployments
  - Better performance for concurrent access
  - Advanced indexing capabilities (like GIN indexes for JSON/array data)
  - Better scaling for high-volume deployments

The codebase automatically adapts to the chosen database backend through SQLAlchemy's abstraction layer.

## Command-Line Interface

The Corgi Recommender Service includes a command-line interface (CLI) for managing the database. You can use it to:

- Initialize and seed the database
- View user interactions and recommendations
- Manage user privacy settings
- Import/export data
- Run database migrations

Example usage:

```bash
# Initialize and seed the database
python cli.py setup --seed

# View user interactions
python cli.py view_interactions --alias <alias_id>

# View recommendations
python cli.py view_recommendations --alias <alias_id>

# View database info
python cli.py db_info

# Run database migrations
python cli.py migrate
```

For more information on the CLI, run `python cli.py --help` or see the [CLI Documentation](cli.md).

## Code Integration

To interact with the database from your code, use the `db.interface` module. This provides a clean API that hides the implementation details:

```python
from db.interface import (
    record_interaction, 
    get_personalized_recommendations,
    update_privacy_settings,
    get_privacy_report
)

# Record a user interaction
record_interaction(
    user_id="actual_user_123",
    post_id="post_456",
    interaction_type="favorite",
    instance_url="mastodon.social",
    context={"source": "timeline", "position": 3}
)

# Get personalized recommendations
recommendations = get_personalized_recommendations(
    user_id="actual_user_123",
    instance_url="mastodon.social",
    limit=10
)

# Update privacy settings
update_privacy_settings(
    user_id="actual_user_123",
    privacy_level="LIMITED",
    instance_url="mastodon.social"
)

# Get privacy report
privacy_report = get_privacy_report(
    user_id="actual_user_123",
    instance_url="mastodon.social"
)

# Store post metadata
from db.interface import store_post_metadata

store_post_metadata({
    "post_id": "post_456",
    "author_id": "author_789",
    "author_name": "Jane Smith",
    "content": "This is a sample post",
    "created_at": "2025-04-22T10:30:00",
    "language": "en",
    "tags": ["corgi", "recommendations"]
})
```

This clean interface makes it easy to integrate the Corgi Recommender Service into your application without worrying about the underlying database details. All user IDs are automatically pseudonymized for privacy protection.