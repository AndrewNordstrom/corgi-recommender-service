# Privacy API

The Privacy API allows users to control how their data is collected, stored, and used by the recommendation service. It provides transparency and user control over personal data usage.

## Understanding Privacy Levels

The Corgi Recommender Service offers three privacy levels:

1. **Full (Default)**: All interaction data is collected and used for personalized recommendations. This provides the best recommendation quality but stores the most user data.

2. **Limited**: Only aggregated statistics are stored (e.g., counts of favorites by category rather than individual posts). Provides moderate personalization with reduced data storage.

3. **None**: Minimal data collection. Only essential data is stored, and no personalized recommendations are generated. The service functions with basic features only.

## Get Privacy Settings

Retrieve the current privacy settings for a user.

### Endpoint

```
GET /api/v1/privacy
```

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | String | Yes | The user ID to retrieve privacy settings for |

### Response

```json
{
  "user_id": "user123",
  "tracking_level": "full"
}
```

The `tracking_level` field will be one of: `"full"`, `"limited"`, or `"none"`.

### Usage Example

```bash
curl "http://localhost:5001/api/v1/privacy?user_id=user123"
```

## Update Privacy Settings

Change a user's privacy and tracking preferences.

### Endpoint

```
POST /api/v1/privacy
```

### Request Format

```json
{
  "user_id": "user123",
  "tracking_level": "limited"
}
```

#### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | String | Yes | User ID to update settings for |
| `tracking_level` | String | Yes | Privacy level: `"full"`, `"limited"`, or `"none"` |

### Response

```json
{
  "user_id": "user123",
  "tracking_level": "limited",
  "status": "ok"
}
```

### Usage Example

```bash
curl -X POST http://localhost:5001/api/v1/privacy \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "tracking_level": "limited"
  }'
```

## Impact of Privacy Levels

The selected privacy level affects the behavior of other API endpoints:

### Full (Default)

- Interactions API: All interactions are stored with full details
- Recommendations API: Fully personalized recommendations based on all user activity

### Limited

- Interactions API: Only aggregate interaction counts are stored
- Recommendations API: Moderately personalized recommendations based on general preferences

### None

- Interactions API: Only essential data is stored with minimal detail
- Recommendations API: Generic recommendations not personalized to the user

## Technical Details

### Data Storage

Privacy settings are stored in the `privacy_settings` table:

```sql
CREATE TABLE IF NOT EXISTS privacy_settings (
    user_id TEXT PRIMARY KEY,
    tracking_level TEXT CHECK (tracking_level IN ('full', 'limited', 'none')) DEFAULT 'full',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### User ID Pseudonymization

For additional privacy protection, user IDs are pseudonymized using a salted hash before storage. This applies regardless of the privacy level setting.

## Common Issues

| Issue | Solution |
|-------|----------|
| Invalid tracking level | Use only `"full"`, `"limited"`, or `"none"` |
| Missing user ID | Ensure user ID is provided in requests |
| No settings found | If no settings exist, default (`"full"`) is assumed |

## Research & Educational Use

For researchers and educators using this system, the privacy API allows configuring appropriate data collection levels in accordance with institutional requirements and data handling policies.

### Recommended Settings

- Educational demos: `"none"` for minimal data collection
- Research with IRB approval: `"limited"` or `"full"` based on protocol requirements
- User studies: Obtain explicit user consent for `"full"` tracking