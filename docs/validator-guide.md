# Validator Guide

The Corgi Recommender Service includes a built-in validation tool (`corgi_validator.py`) for testing the core functionality of the service. This guide explains how to use the validator and interpret its results.

## Purpose of the Validator

The validator performs end-to-end testing of the service by:

1. Creating synthetic users and posts
2. Simulating user interactions with content
3. Testing the recommendation generation
4. Validating privacy controls and data handling
5. Checking response formats and API adherence

This helps ensure that all components of the service are working correctly before deployment or after making changes.

## Running the Validator

### Basic Usage

To run the validator with default settings:

```bash
python corgi_validator.py
```

This will:
- Create 5 synthetic users
- Create 10 synthetic posts
- Generate interactions between users and posts
- Run all validation checks

### Options and Flags

The validator supports several command-line arguments:

```
usage: corgi_validator.py [-h] [--api-base API_BASE] [--verbose] [--dry-run]
                         [--skip-server-check] [--run-seed RUN_SEED]
                         [--check-recs] [--check-feedback] [--check-privacy]
                         [--check-blend] [--check-all] [--check-server]
                         [--check-paths] [--output OUTPUT]
```

Common options include:

| Option | Description |
|--------|-------------|
| `--verbose` | Enable detailed logging |
| `--dry-run` | Simulate validation without making real API calls |
| `--check-recs` | Only run recommendation validation |
| `--check-privacy` | Only run privacy settings validation |
| `--check-all` | Run all validation checks |
| `--output FILE` | Save validation report to a JSON file |

### Example Commands

Test only the recommendation functionality:

```bash
python corgi_validator.py --check-recs --verbose
```

Run the validator against a custom API endpoint:

```bash
python corgi_validator.py --api-base=http://myserver:5001 --verbose
```

Generate a validation report:

```bash
python corgi_validator.py --check-all --output=validation_report.json
```

## Understanding Validation Checks

The validator runs several core checks:

### 1. Recommendations Check

Verifies that the recommendation engine generates valid personalized content:

- Checks if recommendations are returned
- Validates recommendation format (correct fields, valid values)
- Verifies that posts disliked by users don't appear in recommendations

### 2. Feedback Logging Check

Tests the interaction logging functionality:

- Logs synthetic user feedback (favorites, etc.)
- Verifies that interactions are properly stored
- Confirms that interactions can be retrieved

### 3. Privacy Modes Check

Validates that privacy settings are respected:

- Tests each privacy level (full, limited, none)
- Verifies that data visibility changes appropriately
- Checks that privacy settings persist

### 4. Timeline Blending Check

Tests the integration of recommendations into timelines:

- Checks timeline endpoints
- Verifies recommendation injection
- Validates blending parameters

## Interpreting Results

The validator produces a report with a status for each check:

- ✅ **Pass**: The feature works as expected
- ⚠️ **Warning**: Minor issues detected, but not critical
- ❌ **Fail**: Critical problems found

Here's an example report:

```
=== Corgi Validator Results ===

Timestamp: 2025-03-15T14:32:18
Synthetic Users: 5
Synthetic Posts: 10
Simulated Interactions: 17

Test Results:
✅ recommendations (Generated 8 recommendations)
✅ feedback (All feedback entries were properly logged and retrieved)
⚠️ privacy (Privacy level transition from 'none' to 'full' has delay)
✅ blending (Timeline blending verification complete)

Overall Status: ⚠️ Some checks have warnings
```

## Common Issues and Solutions

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| Recommendation check fails | Missing post data or ranking algorithm error | Check database connection and algorithm inputs |
| Feedback logging check fails | Interaction API endpoint not working | Verify API path and request format |
| Privacy check fails | Privacy settings not being stored correctly | Check database schema or API implementation |
| Connectivity errors | Service not running or wrong port | Start the service or use correct API base URL |

## Using the Validator in CI/CD

The validator can be integrated into continuous integration workflows:

```bash
# In your CI script
python corgi_validator.py --dry-run --check-all --output=validation_report.json

# Check exit code
if [ $? -ne 0 ]; then
  echo "Validation failed!"
  exit 1
fi
```

For environments without a running database, use the `--dry-run` flag to simulate API calls.