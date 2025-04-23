# Database CLI Guide

The Corgi Recommender Service includes a command-line interface (CLI) for managing the database. This tool is useful for setup, maintenance, and debugging tasks.

## Installation

The CLI is included in the Corgi Recommender Service package. No additional installation is required.

## Basic Usage

To see all available commands:

```bash
python cli.py --help
```

Each command has its own help information:

```bash
python cli.py <command> --help
```

## Available Commands

### Database Setup

#### `setup`

Set up the database schema and optionally seed it with sample data.

```bash
# Set up the database
python cli.py setup

# Reset the database (WARNING: destroys all data)
python cli.py setup --reset

# Seed the database with sample data
python cli.py setup --seed
```

#### `seed_users`

Seed the database with sample users.

```bash
python cli.py seed_users
```

### Data Viewing

#### `view_interactions`

View user interactions.

```bash
# View interactions for a user
python cli.py view_interactions --alias <alias_id>

# Limit the number of interactions
python cli.py view_interactions --alias <alias_id> --limit 10
```

#### `view_recommendations`

View recommendations for a user.

```bash
# View personalized recommendations
python cli.py view_recommendations --alias <alias_id>

# View cold start recommendations
python cli.py view_recommendations --cold-start

# Limit the number of recommendations
python cli.py view_recommendations --alias <alias_id> --limit 5

# Don't log recommendations
python cli.py view_recommendations --alias <alias_id> --no-log
```

#### `db_info`

Display database information.

```bash
python cli.py db_info
```

Example output:

```json
{
  "db_type": "sqlite",
  "tables": [
    "user_aliases",
    "post_metadata",
    "user_interactions",
    "author_preferences",
    "recommendation_logs"
  ],
  "table_counts": {
    "user_aliases": 3,
    "post_metadata": 10,
    "user_interactions": 15,
    "author_preferences": 5,
    "recommendation_logs": 8
  },
  "in_memory": false,
  "url": "sqlite:///data/corgi_recommender.db"
}
```

### Privacy Management

#### `view_privacy`

View privacy report for a user.

```bash
python cli.py view_privacy --alias <alias_id>
```

#### `update_privacy`

Update privacy settings for a user.

```bash
# Update privacy level to limited
python cli.py update_privacy --alias <alias_id> --level limited

# Available levels: none, limited, full
```

### Data Management

#### `import_posts`

Import posts from a JSON file.

```bash
python cli.py import_posts --file <path_to_json_file>
```

The JSON file should contain an array of post objects or an object with a `posts` key containing an array of post objects.

```json
[
  {
    "post_id": "post1",
    "author_id": "author1",
    "author_name": "Corgi Lover",
    "content": "Look at my cute corgi!",
    "created_at": "2025-04-22T12:00:00Z",
    "tags": ["corgi", "pets", "cute"]
  },
  {
    "post_id": "post2",
    "author_id": "author1",
    "content": "Another cute corgi pic!",
    "tags": ["corgi", "pets"]
  }
]
```

#### `add_interaction`

Add an interaction for a user.

```bash
# Add a favorite
python cli.py add_interaction --alias <alias_id> --post <post_id> --type favorite

# Add a boost with context
python cli.py add_interaction --alias <alias_id> --post <post_id> --type boost --context '{"source": "timeline"}'

# Available types: favorite, boost, reply, view, bookmark
```

#### `wipe_database`

Wipe the database. This deletes all data and recreates the schema.

```bash
# Show warning
python cli.py wipe_database

# Confirm and wipe
python cli.py wipe_database --confirm
```

## Examples

### Setting Up a Development Environment

```bash
# Create the database schema
python cli.py setup

# Seed with sample data
python cli.py seed_users --seed

# Verify setup
python cli.py db_info
```

### Importing Real Data

```bash
# Import posts from a JSON file
python cli.py import_posts --file real_posts.json

# Check the database
python cli.py db_info
```

### Testing Recommendations

```bash
# Add some interactions
python cli.py add_interaction --alias user1 --post post1 --type favorite
python cli.py add_interaction --alias user1 --post post2 --type boost

# View recommendations
python cli.py view_recommendations --alias user1
```

### Managing User Privacy

```bash
# View current privacy settings
python cli.py view_privacy --alias user1

# Update privacy level
python cli.py update_privacy --alias user1 --level limited

# Verify changes
python cli.py view_privacy --alias user1
```

## Error Handling

The CLI provides user-friendly error messages when something goes wrong. Most commands will exit with a non-zero status code if they encounter an error.

## Using the CLI in Scripts

The CLI is designed to be used in scripts as well as interactively. Each command returns a consistent exit code that can be checked in scripts.

Example shell script:

```bash
#!/bin/bash
set -e

# Set up the database
python cli.py setup --reset --seed

# Import data
python cli.py import_posts --file data/posts.json

# Check database status
python cli.py db_info

echo "Setup complete!"
```

## Environment Variable Support

The CLI respects the same environment variables as the main application, including `CORGI_DB_URL` for database configuration. You can set these variables before running the CLI:

```bash
# Use a specific database
CORGI_DB_URL=sqlite:///data/test.db python cli.py db_info
```

## Advanced Usage

### JSON Output

Most commands output JSON-formatted data, which can be piped to other tools like `jq` for further processing:

```bash
# Get recommendations and extract post IDs
python cli.py view_recommendations --alias user1 | jq '.[].post_id'
```

### Database Maintenance

The CLI can be used for database maintenance tasks like rebuilding indexes:

```bash
# Reset and rebuild the database
python cli.py setup --reset

# Import data from backups
python cli.py import_posts --file backup.json
```

## Troubleshooting

If you encounter issues with the CLI, try these steps:

1. Check that the database URL is correct
2. Ensure the database exists and is accessible
3. Check the Corgi log files for error messages
4. Try running with `--reset` to recreate the database schema

For persistent issues, consult the error messages and logs for more details.