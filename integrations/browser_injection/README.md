# Browser Injection for Elk Integration

This directory contains scripts and tools for injecting custom functionality into the Elk frontend without modifying its codebase. This approach is useful for testing or for users who don't want to maintain a fork of Elk.

## Quick Start

To quickly set up the entire system and test the integration:

```bash
cd /Users/andrewnordstrom/corgi-recommender-service
./START_END_TO_END.sh
```

This script will:
1. Start Corgi if it's not already running
2. Verify the Corgi API is responding
3. Start the Elk frontend configured to use Corgi
4. Provide instructions for injecting the enhancement script

## Contents

- **simple_elk_integration.js**: A standalone JavaScript file that enhances the Elk UI with support for:
  - Recommendation badges
  - Clickable profile avatars
  - Clickable usernames linking to user profiles

- **elk_integration.html**: A helper page with instructions for injecting the script

## Manual Setup Instructions

If you prefer to set things up manually:

1. Make sure your Corgi backend is running:
   ```bash
   cd /Users/andrewnordstrom/corgi-recommender-service
   ./scripts/start_corgi.sh
   ```

2. Start Elk pointing to your Corgi backend:
   ```bash
   cd /Users/andrewnordstrom/corgi-recommender-service
   ./scripts/start_elk_with_corgi.sh
   ```

3. Open the Elk frontend in your browser:
   http://localhost:3013

4. Open the browser's developer console (F12 or Cmd+Option+I)

5. Copy and paste the contents of `simple_elk_integration.js` into the console and press Enter

6. The enhanced UI features should now be active

## Alternative: Browser Extensions

For a more permanent solution, you can use a browser extension to automatically inject the script:

### Chrome/Edge

1. Install the [User JavaScript and CSS](https://chrome.google.com/webstore/detail/user-javascript-and-css/nbhcbdghjpllgmfilhnhkllmkecfmpld) extension
2. Navigate to your Elk instance (e.g., http://localhost:3013)
3. Click the extension icon and add a new script
4. Paste the contents of `simple_elk_integration.js`
5. Save and refresh the page

### Firefox

1. Install [Tampermonkey](https://addons.mozilla.org/en-US/firefox/addon/tampermonkey/)
2. Create a new script
3. Paste the contents of `simple_elk_integration.js`, wrapped in the appropriate userscript header:
   ```javascript
   // ==UserScript==
   // @name         Elk Corgi Integration
   // @namespace    http://tampermonkey.net/
   // @version      0.1
   // @description  Enhances Elk with Corgi recommendation features
   // @author       You
   // @match        http://localhost:3013/*
   // @grant        none
   // ==/UserScript==

   (function() {
     // Contents of simple_elk_integration.js here
   })();
   ```
4. Save and refresh the page

## How It Works

This script:

1. Scans the DOM for posts/statuses
2. For each post, it:
   - Checks if the post has the `is_recommendation` flag
   - If true, adds a visual badge
   - Makes avatar images and usernames link to the user's profile

## Limitations

- Must be reinjected each time the page is reloaded (unless using a browser extension)
- May break if Elk's internal DOM structure changes
- Doesn't modify the underlying Vue components
- Some styling may not perfectly match Elk's design system

## For Production Use

This approach is meant for development and testing. For production use, consider:

1. Forking Elk and making proper component modifications
2. Creating a browser extension that users can install
3. Contributing your changes back to the Elk project