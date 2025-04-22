# Connecting Elk to Corgi Recommendation Service

This guide explains how to connect the Elk Mastodon client to the Corgi Recommendation Service for local testing.

## Prerequisites

- Elk client installed and running locally (http://localhost:5314)
- Corgi service set up with a demo account in the database

## Step 1: Start the Corgi Proxy Server

Run the specialized proxy server that handles the integration:

```bash
cd /path/to/corgi-recommender-service
python3 special_proxy.py
```

This will start the proxy server on port 5003.

## Step 2: Configure Elk to Use the Proxy

1. Open Elk in your browser (usually at http://localhost:5314)
2. When asked for a server, enter: `https://localhost:5003`
   - **IMPORTANT:** Include the full HTTPS URL
   - Do NOT include any path like /api/v1/proxy here
3. Click "Sign in"
4. You may need to accept the self-signed certificate warning in your browser

If Elk shows OAuth screens that don't work, you'll need to:
1. Find where the Elk configuration is stored (usually in browser local storage)
2. Manually set the API URL to `https://localhost:5003/api/v1/proxy`
3. Add the authorization header: `Bearer _Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc`

The token is a special demo token that Corgi recognizes and connects to the demo_user account.

## Alternative: Use the Test Client

If you're having trouble configuring Elk, we've included a simple test client:

1. Open the file `/Users/andrewnordstrom/corgi-recommender-service/test_client.html` in your browser
2. The base URL and token are pre-configured
3. Click "Test Status", "Test Instance", and "Test Timeline" to verify connectivity
4. You should see recommendations injected into the timeline

This test client demonstrates that the Corgi proxy is working correctly.

## Step 3: Test the Integration

After successfully logging in:

1. Go to the Home timeline in Elk
2. You should see posts from the Mastodon API
3. You should also see recommendation posts from Corgi (they'll be labeled as "recommendations")

## Step 4: Test Cold Start Feature

The Cold Start feature is designed to show curated content to users who don't follow anyone yet:

### Testing with a New User

1. Create a new test user on a Mastodon instance
2. Configure Elk to connect to Corgi using this new user's credentials
3. The home timeline will automatically display the cold start content
4. You'll see diverse posts from various categories (tech, art, science, etc.)

### Testing with Force Mode

To test the cold start feature with an existing user account:

1. Modify the URL in Elk to include the `cold_start=true` parameter:
   - From: `http://localhost:5314/home`
   - To: `http://localhost:5314/home?cold_start=true`
2. This will force the cold start mode even for users who already follow accounts
3. You should see the curated cold start posts instead of your regular timeline

### Reverting to Normal Timeline

To return to your regular timeline:

1. Remove the `cold_start=true` parameter from the URL
2. Or simply navigate to the home timeline normally within Elk

## Troubleshooting

If you encounter issues:

- Check that the proxy server is running (`python3 special_proxy.py`)
- Verify the database is properly set up (`python3 simplified_setup.py`)
- Ensure the token is correct (`_Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc`)
- Visit the test client in your browser: https://localhost:5003/test-client
- Test the API directly with curl (ignore SSL certificate warnings):

```bash
curl -k -H "Authorization: Bearer _Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc" https://localhost:5003/api/v1/timelines/home
```

This should return a timeline with interspersed recommendations.

### SSL Certificate Warning

You'll likely see warnings about the self-signed certificate. This is expected in a development environment. In your browser:
- Click "Advanced" or "Details" 
- Select "Proceed to localhost (unsafe)" or similar option

For curl, use the `-k` flag to ignore SSL certificate validation.

## How It Works

The special proxy server:

1. Authenticates users using a token from the SQLite database 
2. Forwards most API requests to the real Mastodon API
3. Intercepts specific endpoints like the home timeline
4. Injects custom recommendation posts into the timeline
5. Returns the enhanced data to Elk in Mastodon-compatible format

This allows Elk to interact with both Mastodon's real API and Corgi's recommendation system.