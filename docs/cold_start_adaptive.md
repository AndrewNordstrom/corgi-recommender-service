# Adaptive Cold Start System

The Adaptive Cold Start System is an enhancement to Corgi's basic cold start strategy that transforms the initial onboarding experience into a personalized recommendation bootloader. This system learns from a user's first interactions to gradually shift them into meaningful, personalized recommendations.

## How It Works

The adaptive cold start system extends the basic [cold start strategy](cold_start_strategy.md) with the following improvements:

1. **Rich Content Metadata**: Each cold start post is tagged with detailed metadata including tags, category, vibe, tone, account type, and post type.

2. **User Signal Tracking**: The system tracks how users interact with different content types to build a preference profile.

3. **Weighted Content Selection**: As users interact with content, the system gradually shifts from providing diverse content to content matching their demonstrated preferences.

4. **Adaptive Content Ratio**: The ratio of diverse vs. weighted content evolves based on user interaction history.

5. **Automatic Promotion**: Users exit cold start mode after sufficient interactions and tag diversity.

6. **Re-entry Detection**: Users who become inactive for an extended period (14+ days) can re-enter cold start mode to refresh their recommendations.

## Signal Tracking and Preference Mapping

The system tracks multiple dimensions of user preferences:

| Signal Type | Description | Example Values |
|-------------|-------------|----------------|
| Tags | Topic labels associated with content | "art", "technology", "politics" |
| Categories | Broader content categories | "news", "entertainment", "education" |
| Vibes | Content emotional qualities | "funny", "serious", "inspirational" |
| Tones | Content presentation style | "informative", "casual", "provocative" |
| Account Types | Types of accounts creating content | "individual", "organization", "official" |
| Post Types | Structural content types | "text", "image", "video", "poll" |

User preferences are tracked across these dimensions using different interaction types, with varying weights:

| Interaction | Weight | Description |
|-------------|--------|-------------|
| Favorite | 1.0 | Standard weight for liking content |
| Reblog | 1.5 | Higher weight indicating stronger endorsement |
| Bookmark | 1.2 | Indicates intention to revisit content |
| Reply | 1.3 | Active engagement with the content |

## Content Selection Algorithm

The adaptive content selection works through the following process:

1. **Signal Collection**: User interactions with cold start posts are tracked and stored in a signal profile.

2. **Content Scoring**: Each potential cold start post is scored against the user's signal profile.

3. **Weighted Random Selection**: Posts are selected using a combination of:
   - Random diverse content (initially 70%)
   - Preference-weighted content (initially 30%)

4. **Adaptive Ratio Evolution**: As users interact more, the ratio shifts toward weighted content, reinforcing their preferences.

## Promotion Criteria

Users exit cold start mode when they meet ALL of the following conditions:

- At least 5 total interactions with cold start posts
- Interactions with at least 3 unique tags
- At least 1 of each primary interaction type (favorite, reblog, or reply)

Upon promotion, users receive primarily content from accounts they follow, supplemented with personalized recommendations.

## Cold Start Re-entry

If a user becomes inactive for more than 14 days, they are eligible for cold start re-entry. This helps:

- Reacquaint returning users with the platform
- Refresh their recommendations if their interests have changed
- Provide fresh content discovery opportunities

## Configuration

The adaptive cold start system can be configured through `config/cold_start_weights.json`:

```json
{
  "random_ratio": 0.7,       // Initial ratio of random diverse content
  "weighted_ratio": 0.3,     // Initial ratio of preference-weighted content
  "evolution_rate": 0.1,     // How quickly ratios shift toward personalization
  "min_weighted_ratio": 0.3, // Minimum weighted content ratio
  "max_weighted_ratio": 1.0  // Maximum weighted content ratio
}
```

## Analyzing User Signal Profiles

You can analyze user signal profiles using the CLI tool:

```bash
python scripts/view_cold_profile.py --user user123
```

This displays a visualization of the user's preferences across different signal dimensions, showing:

- Top tags by interaction count
- Category distribution
- Vibe preferences
- Interaction history timeline
- Promotion status

## Technical Implementation

The adaptive cold start system is implemented through these components:

- `utils/user_signals.py`: Core logic for signal tracking and weighted selection
- `data/cold_start_posts.json`: Enhanced post data with rich metadata
- `config/cold_start_weights.json`: Configuration for content selection ratios
- `routes/proxy.py`: Integration with the timeline API endpoints

## Privacy Considerations

All user signal data is:

- Pseudonymized using the same privacy-preserving techniques as the main recommender
- Stored securely with the same retention policies as other user data
- Subject to the same deletion/reset requests as the main recommendation engine
- Never shared with third parties

## Logging and Diagnostics

The adaptive cold start system provides detailed logging:

- `COLD-START-SIGNAL-*`: Logs signal updates from user interactions
- `COLD-START-SELECT-*`: Logs post selection decisions
- `COLD-START-PROMOTE-*`: Logs promotion status changes
- `COLD-START-REENTRY-*`: Logs cold start re-entry events

These logs help analyze system performance and troubleshoot issues while maintaining user privacy.