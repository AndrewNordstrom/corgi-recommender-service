# Database Documentation

Welcome to the database documentation for the Corgi Recommender Service. This section provides detailed information about the database layer, including schema design, configuration options, and programmatic interfaces.

## Overview

The Corgi Recommender Service uses a carefully designed database schema to store user interactions, post metadata, and recommendation data. The database layer is built on SQLAlchemy and supports both SQLite (for development) and PostgreSQL (for production).

## Key Features

- **Privacy by Design**: User IDs are pseudonymized with HMAC-SHA256 hashing
- **Flexible Storage**: Works with both SQLite and PostgreSQL
- **Clean Interface**: High-level API that hides implementation details
- **Performance Optimized**: Proper indexes and query optimization
- **Command-line Tools**: CLI for database management and maintenance

## Documentation Sections

| Section | Description |
|---------|-------------|
| [Schema](schema.md) | Database schema design and entity relationships |
| [Configuration](configuration.md) | Database configuration options |
| [Interface](interface.md) | Programmatic interface for database operations |
| [CLI](cli.md) | Command-line interface for database management |

## Quick Start

To get started with the database, follow these steps:

1. Configure your database in the `.env` file:
   ```bash
   # For development (SQLite)
   CORGI_DB_URL=sqlite:///data/corgi_recommender.db
   
   # For production (PostgreSQL)
   # CORGI_DB_URL=postgresql://username:password@localhost:5432/corgi_recommender
   ```

2. Initialize the database:
   ```bash
   python cli.py setup --seed
   ```

3. Verify the setup:
   ```bash
   python cli.py db_info
   ```

## Design Principles

The database layer follows these design principles:

1. **Separation of Concerns**: The interface layer separates business logic from database implementation
2. **Privacy First**: User identities are protected through pseudonymization
3. **Performance Optimized**: Indexes and database structure designed for recommendation workloads
4. **Simplicity**: Easy to understand and maintain database schema

## Data Flow

The typical data flow through the database layer is:

1. User interactions are recorded with pseudonymized IDs
2. Interactions are used to build user preferences and author scores
3. Recommendations are generated based on preferences, content metrics, and recency
4. Recommendations are logged for analysis and improvement

## Common Tasks

Here are some common tasks you might want to perform:

- **Record a user interaction**: `python cli.py add_interaction --alias <alias_id> --post <post_id> --type favorite`
- **View interactions**: `python cli.py view_interactions --alias <alias_id>`
- **View recommendations**: `python cli.py view_recommendations --alias <alias_id>`
- **Reset the database**: `python cli.py setup --reset`