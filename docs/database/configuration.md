# Database Configuration

The Corgi Recommender Service provides a flexible database configuration system that supports both SQLite (for development) and PostgreSQL (for production) with minimal code changes.

## Configuration Options

You can configure the database connection using environment variables in your `.env` file:

```bash
# Primary database URL - use one of these options:

# SQLite (development)
CORGI_DB_URL=sqlite:///data/corgi_recommender.db

# PostgreSQL (production)
# CORGI_DB_URL=postgresql://username:password@localhost:5432/corgi_recommender

# Legacy PostgreSQL configuration (used if CORGI_DB_URL not specified)
POSTGRES_HOST=localhost
DB_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=corgi_recommender

# Database options
USE_IN_MEMORY_DB=false   # Use in-memory SQLite database for testing
SQL_ECHO=false           # Enable SQLAlchemy query logging
```

## SQLite vs. PostgreSQL

The Corgi Recommender Service uses SQLAlchemy to abstract the database layer, making it compatible with both SQLite and PostgreSQL. Here's a comparison of the two options:

### SQLite

- **Pros**: No server setup required, simpler for development, file-based
- **Cons**: Limited concurrent access, not ideal for high-throughput production
- **Best for**: Development, testing, small deployments, single-user scenarios

### PostgreSQL

- **Pros**: Better performance, concurrent access, robust ACID compliance, advanced features
- **Cons**: Requires server setup, more complex configuration
- **Best for**: Production environments, multi-user scenarios, high-throughput deployments

## Database Initialization

To initialize the database, you can use the built-in CLI:

```bash
# Initialize with default settings
python cli.py setup

# Initialize and seed with sample data
python cli.py setup --seed

# Reset the database (WARNING: destroys all data)
python cli.py setup --reset
```

## In-Memory Database for Testing

For testing, you can use an in-memory SQLite database that doesn't persist to disk:

```bash
# Set environment variable
export USE_IN_MEMORY_DB=true

# Run with in-memory database
python cli.py setup --seed
```

## Connection Pooling

The PostgreSQL configuration uses connection pooling to efficiently manage database connections:

- Default pool size: 5 connections
- Maximum overflow: 10 connections
- Connection timeout: 30 seconds

This configuration is suitable for most deployments but can be adjusted for higher traffic scenarios.

## Environment-Specific Configuration

We recommend using different database configurations for different environments:

### Development

```bash
CORGI_DB_URL=sqlite:///data/corgi_recommender.db
SQL_ECHO=true  # Enable query logging for debugging
```

### Testing

```bash
USE_IN_MEMORY_DB=true
```

### Production

```bash
CORGI_DB_URL=postgresql://username:password@localhost:5432/corgi_recommender
```

## Monitoring Database Performance

You can monitor database performance using the built-in CLI:

```bash
# View database information
python cli.py db_info
```

This command shows information about the database connection, tables, and row counts, which can be helpful for diagnosing performance issues.

## Advanced: Custom Database Setup

For advanced scenarios, you can manually initialize the database using the Python API:

```python
from db.init_db import init_db, seed_database

# Initialize the database schema
init_db(drop_all=False)

# Optionally seed with sample data
seed_database()
```

This gives you more control over the initialization process and can be useful for scripting complex setups.