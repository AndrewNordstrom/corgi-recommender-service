# Elk Integration Guide

This guide explains how to integrate Corgi's recommendation engine with the Elk Mastodon client.

## Overview

Elk is a Mastodon web client built with Vue.js/Nuxt.js. Corgi can enhance Elk by:

1. Acting as a transparent proxy between Elk and any Mastodon instance
2. Injecting personalized recommendations into the timeline
3. Enhancing post display with additional information
4. Providing a better "cold start" experience for new users

## Setup Options

You have multiple options for integrating Corgi with Elk, from simplest to most customized:

### Option 1: Point Elk to Corgi's API

The simplest approach is to configure Elk to use Corgi's API endpoint instead of connecting directly to a Mastodon instance:

1. Start Corgi:
   ```bash
   cd /path/to/corgi-recommender-service
   ./scripts/start_corgi.sh
   ```

2. In Elk, set the server to `localhost:5004` (without `https://` prefix)

3. Sign in with your Mastodon account credentials

Corgi will proxy all requests to your Mastodon instance while adding recommendations.

### Option 2: Use Our Automated Script

We provide a convenience script that starts both Corgi and Elk configured to work together:

```bash
cd /path/to/corgi-recommender-service
./scripts/start_elk_with_corgi.sh --with-corgi --elk-path /path/to/elk
```

This script:
1. Starts Corgi if not already running
2. Configures Elk environment variables to use Corgi
3. Launches the Elk development server

### Option 3: Browser Injection for UI Enhancements

To enhance the UI without modifying Elk's code:

1. Start Elk with Corgi backend (using Option 1 or 2)
2. Open the browser console in developer tools
3. Paste the script from `/integrations/browser_injection/simple_elk_integration.js`

This will add:
- Recommendation badges on recommended posts
- Clickable profile pictures and usernames
- Enhanced visual styling for recommendations

See [Browser Injection README](/integrations/browser_injection/README.md) for more details.

### Option 4: Full Component Integration

For permanent integration, you can add our custom Vue components to your Elk codebase:

1. Copy the components from `/integrations/elk/components/` to your Elk project
2. Import and register them in your Elk application
3. Modify StatusCard.vue to use these components

This provides the most seamless integration but requires code changes to Elk.

## Configuration Options

When integrating with Elk, you can customize Corgi's behavior:

### Environment Variables for Elk

These environment variables control how Elk connects to Corgi:

- `NUXT_PUBLIC_DEFAULT_SERVER="localhost:5004"` - Sets Corgi as the default server
- `NUXT_PUBLIC_DISABLE_SERVER_SIDE_AUTH=true` - Disables server-side authentication
- `NUXT_PUBLIC_PREFER_WSS=false` - Disables WebSocket secure connection preference

### Corgi Configuration for Elk

These options affect how Corgi handles Elk requests:

- `--port 5004` - The port Corgi listens on
- `--no-https` - Disable HTTPS (for development)
- `--host localhost` - Host to bind to

## Troubleshooting

### Common Issues

1. **Certificate Warnings**: By default, Corgi uses self-signed certificates. You can:
   - Accept the risk in your browser
   - Use `--no-https` for development
   - Configure Corgi with proper certificates

2. **Authentication Failures**: If Elk can't authenticate, check:
   - The Corgi logs for token-related errors
   - That you're using the correct server URL format 
   - That you have `NUXT_PUBLIC_DISABLE_SERVER_SIDE_AUTH=true` set

3. **UI Enhancement Issues**: If recommendation badges or profile links don't appear:
   - Check browser console for errors
   - Verify that Corgi is adding `is_recommendation` flags to posts
   - Make sure `account.url` is being included in post data

### Diagnosing Problems

Use these commands to check the integration:

```bash
# Check if Corgi is running
curl -k https://localhost:5004/api/v1/proxy/status

# Check a timeline response (with your token)
curl -k -H "Authorization: Bearer YOUR_TOKEN" https://localhost:5004/api/v1/timelines/home | jq
```

## Advanced: Custom Elk Builds

If you're maintaining your own fork of Elk with Corgi integration:

1. Add types in `/types/mastodon.d.ts`:
   ```typescript
   // Extend the Status interface with our custom properties
   declare module 'masto' {
     namespace mastodon {
       namespace v1 {
         interface Status {
           is_recommendation?: boolean
           recommendation_reason?: string
         }
       }
     }
   }
   ```

2. Add UI components for recommendations:
   - `RecommendationBadge.vue` for displaying recommendation status
   - `StatusAccountHeader.vue` for enhanced profile displays

3. Update the locale files to include recommendation text:
   ```json
   "status": {
     "recommended": "Recommended for you"
   }
   ```

## Resources

- [Elk Documentation](https://github.com/elk-zone/elk/tree/main/docs)
- [Corgi Proxy Documentation](proxy.md)
- [Mastodon API Documentation](https://docs.joinmastodon.org/client/intro/)