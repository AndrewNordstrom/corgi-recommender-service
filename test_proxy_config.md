# Corgi Proxy Configuration for Elk with Mastodon Token

This guide explains how to set up the Corgi Recommender Service to work with Elk using a manually linked Mastodon token.

## Overview

1. Start the Corgi proxy server
2. Configure Elk to use the proxy server
3. Test authentication with the Mastodon token

## Setup Steps

### 1. Start the Corgi proxy server

```bash
# From the corgi-recommender-service directory
python3 run_proxy_server.py
```

The server will start on port 8000. You should see output indicating that the server is running.

### 2. Configure Elk to use the proxy

In Elk, go to Settings and configure the following:

- Custom API URL: `http://localhost:8000/api/v1/proxy`
- In the Headers section, add:
  - `Authorization: Bearer _Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc`

### 3. Test the token configuration

You can test that the token is properly recognized using this script:

```bash
python3 test_token.py
```

This will send requests to the debug endpoints with the token and show if it is properly recognized.

## Expected Behavior

- The Corgi server will recognize the token and identify the user as `demo_user`
- Proxy requests from Elk will be forwarded to mastodon.social
- The authenticated requests will include the bearer token
- You should be able to see your Mastodon timeline via Elk

## Troubleshooting

If you encounter issues:

1. Check the server logs for errors related to token recognition
2. Verify the SQLite database has the user_identities entry
3. Ensure the token value in Elk headers matches exactly what's in the database
4. Check CORS settings if you get cross-origin errors

## Technical Implementation

This setup uses:

- SQLite database to store the user identity and token
- Custom Flask middleware to recognize the token
- Proxy forwarding to mastodon.social

The token `_Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc` is linked to the user `demo_user` on `mastodon.social`.